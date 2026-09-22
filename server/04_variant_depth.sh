#!/usr/bin/env bash
# 04_variant_depth.sh —— 逐样本窗口深度（mosdepth，历史文件名保留）。
# 正式 SNP 使用下一阶段 04_joint_snp.sh 联合 calling；不得拼接 variant-only 单样本 VCF。
# 用法: bash 04_variant_depth.sh [sample_id]
# 产出: depth/w<窗口>/<sid>.regions.bed.gz      ← 每样本每窗口一列深度
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

ONLY="${1:-}"
REF="$(ref_fasta)"
do_sample() {
  local sid="$1"
  local cram="$RV_BAM/$sid.cram"
  [ -s "$cram" ] || { log "[$sid] 缺少 CRAM，跳过"; return 1; }
  [ -s "$cram.crai" ] || samtools index -@ 4 "$cram"

  # 窗口深度：每个窗口大小一份（reference-bias/QC 诊断用）
  for W in $RV_WINDOWS; do
    local wdir="$RV_DEPTH/w${W}"
    mkdir -p "$wdir"
    local out="$wdir/$sid"
    if [ ! -s "${out}.regions.bed.gz" ]; then
      log "[$sid] mosdepth 窗口=${W}bp"
      mosdepth -t "$((THREADS/2))" -b "$W" -x "$out" "$cram" 2> "$RV_LOG/$sid.mosdepth.$W.log" \
        || { log "[$sid] mosdepth ${W} 失败"; return 1; }
    fi
  done

  mark_done depth "$sid"
  log "[$sid] ✓ 窗口深度完成"
}

log "=== 阶段 04：窗口深度 ==="
[ -s "$REF.fai" ] || die "参考基因组未就绪，请先运行 03_align.sh"

if [ -n "$ONLY" ]; then
  do_sample "$ONLY"
else
  export -f do_sample; export REF
  par_each do_sample $(sample_ids)
fi

log "=== 04 完成，产物大小 ==="
du -sh "$RV_DEPTH" 2>/dev/null
echo
echo "提示：正式 SNP 联合 calling 请运行 04_joint_snp.sh；depth/ 汇总由 06_export.sh 负责。"
