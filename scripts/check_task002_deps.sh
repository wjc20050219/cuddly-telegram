#!/usr/bin/env bash
# check_task002_deps.sh —— 核对 TASK-002 规范要求的软件是否齐全，并检查论文方法依赖
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate ricevar

echo "===== 1. 论文 CNVb 方法所需依赖（TASK-004 已确认原文使用 hmmlearn）====="
python - <<'PY'
for m in ("hmmlearn",):
    try:
        mod = __import__(m)
        print(f"  OK   {m}: {getattr(mod, '__version__', '?')}")
    except Exception as e:
        print(f"  --   {m}: 未安装（{type(e).__name__}）")
PY

echo
echo "===== 2. TASK-002 规范要求的工具逐项确认 ====="
for t in python R conda mamba git fastqc fastp samtools bcftools bedtools \
         bwa-mem2 minimap2 mosdepth kmc jellyfish snakemake nextflow; do
  if command -v "$t" >/dev/null 2>&1; then
    printf "  OK   %-11s %s\n" "$t" "$(command -v "$t")"
  else
    printf "  --   %-11s 未找到\n" "$t"
  fi
done

echo
echo "===== 3. conda 层面的包身份（验证 environment.yml 写的是否正确）====="
conda list -n ricevar 2>/dev/null | grep -iE '^(jellyfish|kmer-jellyfish|kmc|snakemake|fastqc|fastp|mosdepth)[[:space:]]' \
  || echo "  无匹配"

echo
echo "===== 4. 附：k-mer CLI 是否真的是可执行程序（而非 Python 绑定）====="
jellyfish --version 2>&1 | head -n1
python -c "import jellyfish; print('  python jellyfish binding:', jellyfish.__version__)" 2>&1 | head -n1
