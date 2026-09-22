#!/usr/bin/env bash
# collect_env_versions.sh - dump installed tool/library versions (ASCII only)
for t in python pip conda R Rscript git fastqc fastp samtools bcftools bedtools bwa-mem2 minimap2 mosdepth kmc jellyfish snakemake fasterq-dump seqkit; do
  if command -v "$t" >/dev/null 2>&1; then
    v=$("$t" --version 2>&1 | head -n1 | tr -s ' ')
    echo "TOOL|$t|$v"
  else
    echo "TOOL|$t|NOT_FOUND"
  fi
done
echo "---PKGS---"
python -m pip list 2>/dev/null | grep -Ei "pysam|scikit-allel|pyarrow|numpy|pandas|scipy|fastapi|qrcode|sqlmodel|pytest|seaborn|biopython|matplotlib|uvicorn|adjustText"
echo "---ENV---"
cat /etc/os-release | grep PRETTY_NAME
uname -r
echo "---CONDAENV---"
conda env list
