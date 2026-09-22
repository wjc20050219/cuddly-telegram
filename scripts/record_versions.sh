#!/usr/bin/env bash
# 将 ricevar 环境内各工具实际版本回填到 software_versions.txt 第五节
# 用法：conda activate ricevar && bash scripts/record_versions.sh
set -euo pipefail
cd "$(dirname "$0")/.."

out="software_versions.txt"
{
  echo ""
  echo "## 五、环境建成后回填区（$(date +%F' '%T) 自动生成）"
  for t in python pip conda mamba R Rscript git fastqc fastp samtools bcftools \
           bedtools bwa-mem2 minimap2 mosdepth kmc jellyfish snakemake fasterq-dump seqkit; do
    if command -v "$t" >/dev/null 2>&1; then
      v=$("$t" --version 2>&1 | head -n1 | tr -s ' ')
      echo "$t: $v"
    else
      echo "$t: NOT FOUND"
    fi
  done
} >> "$out"
echo "已回填到 $out"
