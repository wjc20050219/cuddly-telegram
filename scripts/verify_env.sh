#!/usr/bin/env bash
# verify_env.sh —— WSL 恢复后的环境验证（可直接用 wsl.exe 调用，无需引号转义）
echo "============================================================"
echo " RiceVar-ID 环境验证"
echo " 时间: $(date '+%F %T')"
echo "============================================================"
echo
echo "### 1. WSL 资源（检查 .wslconfig 是否生效）"
echo "  内存总量   : $(free -h | awk '/^Mem:/{print $2}')"
echo "  交换区大小 : $(free -h | awk '/^Swap:/{print $2}')"
echo "  CPU 逻辑核 : $(nproc)"
echo "  swap 位置  : $(swapon --show=NAME --noheadings 2>/dev/null | tr -d ' ' || echo '未启用')"
echo "  内核       : $(uname -r)"
echo "  发行版     : $(. /etc/os-release && echo "$PRETTY_NAME")"
echo
echo "### 2. 激活 conda 环境"
if [ ! -f /opt/miniconda3/etc/profile.d/conda.sh ]; then
  echo "  ✗ 找不到 /opt/miniconda3/etc/profile.d/conda.sh"; exit 1
fi
source /opt/miniconda3/etc/profile.d/conda.sh
if conda activate ricevar 2>/dev/null; then
  echo "  ✅ conda activate ricevar 成功"
  echo "     环境路径: $CONDA_PREFIX"
  echo "     Python  : $(python -V 2>&1)"
else
  echo "  ✗ conda activate ricevar 失败"; exit 1
fi
echo
echo "### 3. 关键工具版本"
MISS=0
for t in samtools bcftools bedtools bwa-mem2 minimap2 mosdepth fastp fastqc kmc jellyfish snakemake seqkit Rscript git; do
  if command -v "$t" >/dev/null 2>&1; then
    v=$("$t" --version 2>&1 | head -n1 | cut -c1-70)
    printf "  %-11s %s\n" "$t" "$v"
  else
    printf "  %-11s MISSING\n" "$t"; MISS=$((MISS+1))
  fi
done
echo "  --- 缺失工具数: $MISS ---"
echo
echo "### 4. Python 关键库"
python - <<'PY'
mods = ["numpy","pandas","scipy","pyarrow","pysam","Bio","allel","sklearn","matplotlib","seaborn","pytest"]
bad = []
for m in mods:
    try:
        mod = __import__(m)
        v = getattr(mod, "__version__", "?")
        print(f"  {m:<12} {v}")
    except Exception as e:
        print(f"  {m:<12} MISSING ({type(e).__name__})")
        bad.append(m)
print(f"  --- 缺失库数: {len(bad)} ---")
PY
echo
echo "### 5. samtools → bcftools 实跑链路"
T=$(mktemp -d)
cat > "$T/ref.fa" <<'FA'
>chr1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
FA
samtools faidx "$T/ref.fa" 2>/dev/null && echo "  ✅ samtools faidx"
printf '@r1\nACGTACGTACGTACGTACGTACGTACGTACGT\n+\nIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n' > "$T/r.fq"
if command -v bwa-mem2 >/dev/null 2>&1; then
  ( cd "$T" && bwa-mem2 index ref.fa >/dev/null 2>&1 && \
    bwa-mem2 mem -t 2 ref.fa r.fq 2>/dev/null | samtools sort -o r.bam - 2>/dev/null && \
    samtools index r.bam && echo "  ✅ bwa-mem2 比对 → samtools 排序 → 索引" )
  if [ -s "$T/r.bam" ]; then
    bcftools mpileup -f "$T/ref.fa" "$T/r.bam" 2>/dev/null | bcftools call -mv -Ov 2>/dev/null | head -n 5 | \
      grep -q '^##fileformat' && echo "  ✅ bcftools mpileup → call 链路通畅"
  fi
fi
if command -v mosdepth >/dev/null 2>&1 && [ -s "$T/r.bam" ]; then
  mosdepth -t 2 "$T/d" "$T/r.bam" >/dev/null 2>&1 && echo "  ✅ mosdepth 深度计算"
fi
rm -rf "$T"
echo
echo "### 6. 磁盘可用空间"
df -h / /mnt/c /mnt/d 2>/dev/null | awk 'NR==1 || $6=="/" || $6=="/mnt/c" || $6=="/mnt/d"'
echo
echo "### 7. 项目目录可见性"
P=/mnt/d/dsh/RiceVar-ID
if [ -d "$P" ]; then
  echo "  ✅ $P 可访问（$(ls "$P" | wc -l) 个条目）"
  echo "     server/ 脚本数: $(ls "$P/server"/*.sh 2>/dev/null | wc -l)"
  echo "     Pilot 样本表  : $([ -s "$P/data/metadata/pilot_samples.tsv" ] && echo 存在 || echo 缺失)"
else
  echo "  ✗ 无法访问 $P"
fi
echo
echo "============================================================"
echo " 验证结束"
echo "============================================================"
