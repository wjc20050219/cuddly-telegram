#!/usr/bin/env bash
# 00_probe.sh —— 服务器环境探测（先跑这个！5 分钟内回答：调度器 / 外网 / 存储 / 软件）
# 用法: bash 00_probe.sh
# 产出: logs/probe_report.txt（人读）+ logs/probe_summary.tsv（机读）
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

REPORT="$RV_LOG/probe_report.txt"
SUMMARY="$RV_LOG/probe_summary.tsv"
TEST_RUN="SRR9696152"          # 用 pilot 里的真实数据做下载测速
TEST_BYTES=30000000            # 每次测速下载 30 MB

: > "$SUMMARY"
kv() { printf '%s\t%s\n' "$1" "$2" >> "$SUMMARY"; }

{
echo "================================================================"
echo " RiceVar-ID 服务器环境探测报告"
echo " 时间: $(date '+%F %T')   主机: $(hostname)   用户: $(whoami)"
echo "================================================================"

echo
echo "### 1. 系统与硬件"
echo "OS        : $( (. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME") || uname -s )"
echo "Kernel    : $(uname -r)   Arch: $(uname -m)"
echo "CPU cores : $(nproc)"
echo "CPU model : $(awk -F: '/model name/{print $2; exit}' /proc/cpuinfo | sed 's/^ //')"
echo "内存      : $(free -h 2>/dev/null | awk '/^Mem:/{print $2" total / "$7" available"}')"
echo "负载      : $(cat /proc/loadavg 2>/dev/null)"
kv nproc "$(nproc)"
kv mem_total "$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')"

echo
echo "### 2. 存储与配额"
df -hP 2>/dev/null | awk 'NR==1 || $6!~/^\/(proc|sys|dev|run)/' | head -n 20
echo "--- 用户配额 ---"
quota -s 2>/dev/null || echo "(无 quota 命令或不适用)"
lfs quota -h -u "$(whoami)" "${RV_ROOT%%/*}" 2>/dev/null || true
echo "--- 关键路径可用空间 ---"
for d in "$HOME" /tmp /scratch "/scratch/$USER" /work "/work/$USER" /data "$RV_ROOT"; do
  [ -d "$d" ] && printf '%-28s %s\n' "$d" "$(df -hP "$d" 2>/dev/null | awk 'NR==2{print $4" 可用 / "$2" 总"}')"
done
kv home_avail "$(df -hP "$HOME" 2>/dev/null | awk 'NR==2{print $4}')"

echo
echo "### 3. 作业调度器"
for s in sbatch squeue qsub bsub; do
  if command -v "$s" >/dev/null 2>&1; then echo "有: $s -> $(command -v $s)"; kv scheduler "$s"; else echo "无: $s"; fi
done
[ -z "$(command -v sbatch 2>/dev/null)$(command -v qsub 2>/dev/null)$(command -v bsub 2>/dev/null)" ] \
  && { echo "=> 判定: 单机模式，用 nohup/tmux + xargs 并行"; kv scheduler "none"; }
command -v sinfo >/dev/null 2>&1 && { echo "--- 队列 ---"; sinfo -s 2>/dev/null | head -n 6; }

echo
echo "### 4. 软件环境"
for c in conda mamba micromamba module singularity apptainer docker; do
  if command -v "$c" >/dev/null 2>&1; then echo "有: $c ($($c --version 2>&1 | head -n1))"; kv soft_$c "yes"; else echo "无: $c"; kv soft_$c "no"; fi
done
echo "--- 生信工具 ---"
for t in bwa-mem2 bwa samtools bcftools bedtools mosdepth fastp fastqc kmc jellyfish snakemake seqkit fasterq-dump prefetch aria2c axel pigz plink2; do
  if command -v "$t" >/dev/null 2>&1; then printf '  %-14s %s\n' "$t" "$(command -v $t)"; kv tool_$t "yes"; else printf '  %-14s MISSING\n' "$t"; kv tool_$t "no"; fi
done

echo
echo "### 5. 外网连通性与下载测速（关键！）"
probe_get() {  # probe_get <名称> <URL>
  local name="$1" url="$2"
  local out
  out=$(curl -sL -m 60 -r 0-$((TEST_BYTES-1)) -o /dev/null \
        -w '%{http_code} %{size_download} %{speed_download} %{time_total}' "$url" 2>/dev/null) || { echo "  $name  失败/超时"; kv "net_${name}_speed" "FAIL"; return; }
  local code size speed t
  code=$(echo "$out" | awk '{print $1}'); size=$(echo "$out" | awk '{print $2}')
  speed=$(echo "$out" | awk '{print $3}'); t=$(echo "$out" | awk '{print $4}')
  local mbs; mbs=$(awk -v s="$speed" 'BEGIN{printf "%.2f", s/1048576}')
  if [ "$size" -lt 1000000 ] 2>/dev/null; then echo "  $name  HTTP=$code 只取到 ${size}B -> 可能被墙/限速"; kv "net_${name}_speed" "$mbs"; return; fi
  echo "  $name  HTTP=$code  ${size} B in ${t}s  =>  ${mbs} MB/s"
  kv "net_${name}_speed" "$mbs"
}

# 5.1 ENA API 是否可达
echo "[ENA API]"
curl -s -m 30 -o /dev/null -w '  www.ebi.ac.uk HTTP=%{http_code} time=%{time_total}s\n' \
  "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${TEST_RUN}&result=read_run&fields=fastq_ftp,fastq_md5,fastq_bytes&format=tsv" \
  2>/dev/null || echo "  不可达"

# 5.2 取真实 FASTQ 地址
FTP_PATH=$(curl -sL -m 30 "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${TEST_RUN}&result=read_run&fields=fastq_ftp&format=tsv" 2>/dev/null | awk -F'\t' 'NR==2{print $2}' | cut -d';' -f1)
if [ -n "${FTP_PATH:-}" ]; then
  echo "[ENA 数据下载] $FTP_PATH"
  probe_get ena "https://${FTP_PATH}"
else
  echo "[ENA 数据下载] 未能解析 FASTQ 地址（API 可能不可达）"; kv net_ena_speed "FAIL"
fi

# 5.3 NCBI 测速
echo "[NCBI FTP]"
probe_get ncbi "https://ftp.ncbi.nlm.nih.gov/refseq/release/complete/complete.1.1.genomic.fna.gz"

echo
echo "### 6. 自动判定建议"
SCHED=$(awk -F'\t' '$1=="scheduler"{print $2}' "$SUMMARY")
ENA=$(awk -F'\t' '$1=="net_ena_speed"{print $2}' "$SUMMARY")
AVAIL=$(awk -F'\t' '$1=="home_avail"{print $2}' "$SUMMARY")
echo "调度器        : ${SCHED:-未知}"
echo "ENA 下载速度  : ${ENA:-未知} MB/s"
echo "HOME 可用空间 : ${AVAIL:-未知}"
case "${ENA:-FAIL}" in
  FAIL) echo "结论: 服务器外网受限 -> 需改走本机下载再上传，或申请网络策略";;
  *)    awk -v s="$ENA" 'BEGIN{ if (s+0 < 1) print "结论: 下载很慢 -> 建议并行下载 + 边下边算，或本机代下";
                                 else if (s+0 < 5) print "结论: 下载速度中等 -> 并行 4-8 线程下载";
                                 else print "结论: 下载速度良好 -> 直接服务器下载" }';;
esac
echo "================================================================"
} 2>&1 | tee "$REPORT"

echo
echo "报告: $REPORT"
echo "机读汇总: $SUMMARY"
