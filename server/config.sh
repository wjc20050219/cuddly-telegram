#!/usr/bin/env bash
# RiceVar-ID 服务器端共享配置 —— 所有 server/*.sh 都 source 本文件
# 用法: source config.sh   或   RV_ROOT=/scratch/$USER/ricevar bash 02_download.sh
# 约定: 本文件只定义变量与函数，不执行任何重活。

# ---------- 工作区 ----------
export RV_ROOT="${RV_ROOT:-$HOME/ricevar}"
export RV_META="$RV_ROOT/metadata"
export RV_RAW="$RV_ROOT/raw"            # FASTQ
export RV_QC="$RV_ROOT/qc"              # fastp/fastqc
export RV_BAM="$RV_ROOT/bam"            # CRAM
export RV_VCF="$RV_ROOT/vcf"
export RV_DEPTH="$RV_ROOT/depth"
export RV_KMER="$RV_ROOT/kmer"
export RV_SIM="$RV_ROOT/sim"            # ulcWGS 模拟
export RV_EXPORT="$RV_ROOT/export"      # ★ 唯一需要传回的目录
export RV_LOG="$RV_ROOT/logs"
export RV_REF="$RV_ROOT/reference"
export RV_MARKER="$RV_ROOT/markers"      # 冻结 marker 集（Pilot-only 拟合）
export RV_ANALYSIS="$RV_ROOT/analysis"   # recall / 识别率 / 拒识结果
export RV_TMP="${RV_TMP:-${TMPDIR:-/tmp}/ricevar_tmp}"

# 现行本科版默认使用由冻结 Pilot 面板生成的规范清单。
# 可用 RV_SAMPLES 覆盖为 pilot_smoke1.tsv / pilot_smoke5.tsv。
export RV_SAMPLES="${RV_SAMPLES:-$RV_META/pilot_manifest.tsv}"

# ---------- 资源 ----------
# 默认保守使用 8 线程/2 个并行样本；不要直接采用整节点 nproc，避免在共享节点越过调度配额。
export THREADS="${THREADS:-8}"
export PAR="${PAR:-2}"                   # 同时处理的样本数（内存不够就调小）
export SORT_MEM="${SORT_MEM:-1G}"        # samtools sort -m
export KMC_MEM="${KMC_MEM:-4}"           # KMC -m (GB)

# ---------- 参数 ----------
export RV_REF_URL="${RV_REF_URL:-https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-60/fasta/oryza_sativa/dna/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz}"
export RV_REF_NAME="${RV_REF_NAME:-IRGSP-1.0}"
export RV_WINDOWS="${RV_WINDOWS:-10000 50000 100000 1000000}"   # mosdepth 窗口
# 本科版固定六档；正式论文至少 3 次，优先 5 次重复。
export RV_DEPTHS="${RV_DEPTHS:-0.02 0.05 0.10 0.20 0.50 1.00}"
export RV_REPS="${RV_REPS:-3}"
export RV_KMERS="${RV_KMERS:-21 31 51}"

# ---------- 镜像（国内服务器设 RV_MIRROR=1）----------
export RV_MIRROR="${RV_MIRROR:-0}"
export RV_CONDA_MIRROR_URL="https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
export RV_CONDA_PREFIX="${RV_CONDA_PREFIX:-$HOME/miniconda3}"

# ---------- 函数 ----------
log()  { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
die()  { printf '[%s] FATAL: %s\n' "$(date '+%F %T')" "$*" >&2; exit 1; }

# 幂等标记：done <stage> <id> / is_done <stage> <id>
marker() { echo "$RV_LOG/.done_$1_$2"; }
is_done() { [ -f "$(marker "$1" "$2")" ]; }
mark_done() { mkdir -p "$RV_LOG"; touch "$(marker "$1" "$2")"; }

init_dirs() {
  mkdir -p "$RV_META" "$RV_RAW" "$RV_QC" "$RV_BAM" "$RV_VCF" \
           "$RV_DEPTH" "$RV_KMER" "$RV_SIM" "$RV_EXPORT" "$RV_LOG" "$RV_REF" \
           "$RV_MARKER" "$RV_ANALYSIS" "$RV_TMP"
}

# 样本表按列名读取，不依赖历史表的固定列序。规范列见
# scripts/build_server_manifests.py。
sample_runs() {
  awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} $(h["run_accession"])!=""{print $(h["run_accession"])}' "$RV_SAMPLES"
}
run_to_sid() {
  awk -F'\t' -v r="$1" 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} $(h["run_accession"])==r{print $(h["sample_id"]); exit}' "$RV_SAMPLES"
}
sid_to_run() {
  awk -F'\t' -v s="$1" 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} $(h["sample_id"])==s{print $(h["run_accession"]); exit}' "$RV_SAMPLES"
}
sample_value() {
  awk -F'\t' -v s="$1" -v c="$2" 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} $(h["sample_id"])==s{print $(h[c]); exit}' "$RV_SAMPLES"
}
sample_ids() {
  awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} $(h["sample_id"])!=""{print $(h["sample_id"])}' "$RV_SAMPLES"
}

# 并行执行：par_each <函数名> <参数列表...>，用 xargs -P $PAR
par_each() {
  local fn="$1"; shift
  printf '%s\n' "$@" | xargs -r -P "$PAR" -I{} bash -c "$fn \"\$@\"" _ {}
}

# 参考基因组 FASTA 路径（去 .gz 后）
ref_fasta() { echo "$RV_REF/$(basename "${RV_REF_URL%.gz}")"; }

# par_each 会启动新的 bash；显式导出共享函数，否则子进程找不到 log/is_done 等函数。
export -f log die marker is_done mark_done init_dirs sample_runs run_to_sid sid_to_run \
  sample_value sample_ids par_each ref_fasta
