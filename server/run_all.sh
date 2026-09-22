#!/usr/bin/env bash
# run_all.sh —— 流水线编排：自动识别 Slurm / 单机，按阶段顺序执行，支持断点续跑
# 用法:
#   bash run_all.sh              # 从头跑到尾
#   bash run_all.sh 03           # 从阶段 03 开始
#   RV_SAMPLES=~/ricevar/metadata/pilot_manifest.tsv RV_REPS=5 bash run_all.sh 02
# 单机模式建议放进 tmux:  tmux new -s ricevar  →  bash run_all.sh 2>&1 | tee logs/run_all.log
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

FROM="${1:-00}"
STAGES=(00_probe 01_setup_env 02_download 03_align 04_variant_depth 04_joint_snp 05_simulate 06_export 07_identify)

# 阶段先后按数组下标判断，避免字符串比较在 04_variant_depth / 04_joint_snp 上的歧义。
stage_index() {
  local want="$1" i=0 st
  for st in "${STAGES[@]}"; do
    [ "$st" = "$want" ] && { echo "$i"; return 0; }
    i=$((i+1))
  done
  return 1
}

# ---------- 环境激活 ----------
activate_env() {
  if command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)" 2>/dev/null || true
    conda activate ricevar 2>/dev/null || log "警告: conda activate ricevar 失败（01 阶段会创建）"
  elif [ -x "$RV_CONDA_PREFIX/bin/conda" ]; then
    source "$RV_CONDA_PREFIX/etc/profile.d/conda.sh"
    conda activate ricevar 2>/dev/null || true
  fi
  log "工具检查: bwa-mem2=$(command -v bwa-mem2 || echo MISSING)  samtools=$(command -v samtools || echo MISSING)"
}

# ---------- 调度器 ----------
HAVE_SLURM=0
command -v sbatch >/dev/null 2>&1 && HAVE_SLURM=1

SLURM_PART="${SLURM_PART:-}"
SLURM_CPUS="${SLURM_CPUS:-$THREADS}"
SLURM_MEM="${SLURM_MEM:-32G}"
SLURM_TIME="${SLURM_TIME:-72:00:00}"

submit_slurm() {
  local stage="$1" dep="$2" stage_cmd conda_bin conda_root
  local args=(--job-name="rv_$stage" --cpus-per-task="$SLURM_CPUS" --mem="$SLURM_MEM" --time="$SLURM_TIME"
              --output="$RV_LOG/slurm_${stage}_%j.out" --error="$RV_LOG/slurm_${stage}_%j.err")
  [ -n "$SLURM_PART" ] && args+=(--partition="$SLURM_PART")
  stage_cmd="bash '$HERE/${stage}.sh'"
  if [[ "$stage" != 00_probe && "$stage" != 01_setup_env ]]; then
    conda_bin="$(command -v conda 2>/dev/null || echo "$RV_CONDA_PREFIX/bin/conda")"
    conda_root="$(cd "$(dirname "$conda_bin")/.." 2>/dev/null && pwd || echo "$RV_CONDA_PREFIX")"
    stage_cmd="source '$conda_root/etc/profile.d/conda.sh' && conda activate ricevar && bash '$HERE/${stage}.sh'"
  fi
  if [ -n "$dep" ]; then
    # 阶段内脚本自己用 xargs 并行；Slurm 只负责整段的资源与排队
    sbatch "${args[@]}" --dependency="afterok:$dep" --wrap "$stage_cmd" | awk '{print $NF}'
  else
    sbatch "${args[@]}" --wrap "$stage_cmd" | awk '{print $NF}'
  fi
}

# ---------- 主流程 ----------
# ---------- 交付前自检：shell 语法 ----------
log "语法自检…"
_synerr=0
for f in "$HERE"/*.sh; do
  bash -n "$f" 2>/dev/null || { echo "  语法错误: $f"; _synerr=1; }
done
[ "$_synerr" = 0 ] && log "  全部脚本语法通过" || die "存在语法错误，请先修复"

log "=============================================="
log " RiceVar-ID 服务器流水线"
log " 工作区 : $RV_ROOT"
log " 样本表 : $RV_SAMPLES"
log " 并行度 : PAR=$PAR  每样本线程 THREADS=$THREADS"
log " 深度   : $RV_DEPTHS  × $RV_REPS 次重复"
log " 调度器 : $([ "$HAVE_SLURM" = 1 ] && echo Slurm || echo '单机 (nohup/xargs)')"
log " 起始阶段: $FROM"
log "=============================================="

PREV_JOB=""
FROM_STAGE="$FROM"
# 允许用阶段名或编号启动；编号取该前缀的第一个阶段。
if ! stage_index "$FROM_STAGE" >/dev/null 2>&1; then
  for st in "${STAGES[@]}"; do
    case "$st" in "$FROM"*) FROM_STAGE="$st"; break;; esac
  done
fi
FROM_IDX="$(stage_index "$FROM_STAGE")" || die "未知起始阶段: $FROM（可用: ${STAGES[*]}）"

idx=0
for st in "${STAGES[@]}"; do
  [ "$idx" -lt "$FROM_IDX" ] && { idx=$((idx+1)); continue; }

  if [ "$HAVE_SLURM" = 1 ]; then
    job=$(submit_slurm "$st" "$PREV_JOB")
    log "已提交 Slurm 作业: $st  jobid=$job  ${PREV_JOB:+依赖=$PREV_JOB}"
    PREV_JOB="$job"
  else
    log "---- 运行阶段 $st ----"
    # 01 阶段可能刚创建环境；从 02 起每阶段前都重新激活，避免 PATH 没刷新。
    if [[ "$st" != 00_probe && "$st" != 01_setup_env ]]; then
      activate_env
      command -v samtools >/dev/null 2>&1 || die "ricevar 环境未激活，缺少 samtools"
    fi
    t0=$(date +%s)
    if bash "$HERE/${st}.sh"; then
      log "阶段 $st 完成，用时 $(( ($(date +%s)-t0)/60 )) 分钟"
    else
      # 先把退出码存下来再记录：`$?` 只有在条件语句之后、任何其他命令之前
      # 展开才等于被测命令的状态。虽然当前写法恰好正确（then/else 不是命令），
      # 但以后在 log 之前插入任何一行都会**静默**改掉这里报出的退出码，
      # 而这条日志正是服务器上排错时唯一能看到的线索。
      rc=$?
      log "阶段 $st 失败（退出码 $rc），流水线中止。修复后可从本阶段续跑:"
      log "    bash run_all.sh ${st%%_*}"
      exit 1
    fi
  fi
  idx=$((idx+1))
done

if [ "$HAVE_SLURM" = 1 ]; then
  cat <<EOF

已提交全部阶段。查看进度:
    squeue -u \$(whoami)
    tail -f $RV_LOG/slurm_*.out
全部完成后，把 $RV_EXPORT 传回本机:
    rsync -avP user@server:$RV_EXPORT/ /mnt/d/dsh/RiceVar-ID/data/processed/server_export/
EOF
else
  log "全部阶段完成。"
  log "导出目录: $RV_EXPORT ($(du -sh "$RV_EXPORT" 2>/dev/null | cut -f1))"
fi
