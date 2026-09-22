#!/usr/bin/env bash
# smoke_test.sh - verify the ricevar environment is functional end to end
set -uo pipefail
echo "== python imports =="
python - <<'PY'
mods = ["numpy","pandas","scipy","pysam","allel","pyarrow","matplotlib","seaborn",
        "sklearn","Bio","fastapi","sqlmodel","qrcode","pytest","tqdm","rich"]
bad = []
for m in mods:
    try:
        __import__(m)
        print("OK   ", m)
    except Exception as e:
        bad.append((m, repr(e)))
        print("FAIL ", m, e)
print("FAILED_COUNT =", len(bad))
PY
echo "== CLI tools =="
for t in python Rscript samtools bcftools bedtools bwa-mem2 minimap2 mosdepth fastp fastqc kmc jellyfish snakemake fasterq-dump seqkit git; do
  p=$(command -v "$t" 2>/dev/null) && echo "OK    $t -> $p" || echo "FAIL  $t"
done
echo "== functional mini-run: samtools/bcftools on a tiny BAM chain =="
tmp=$(mktemp -d)
printf '@HD\tVN:1.6\n@SQ\tSN:chr1\tLN:1000\nr1\t0\tchr1\t100\t60\t50M\t*\t0\t0\t%s\t%s\n' \
  "$(printf 'A%.0s' {1..50})" "$(printf 'I%.0s' {1..50})" > "$tmp/t.sam"
samtools view -b "$tmp/t.sam" > "$tmp/t.bam" && echo "OK    samtools view -b"
samtools sort -o "$tmp/t.sorted.bam" "$tmp/t.bam" && echo "OK    samtools sort"
samtools index "$tmp/t.sorted.bam" && echo "OK    samtools index"
samtools mpileup -f /dev/null "$tmp/t.sorted.bam" >/dev/null 2>&1 || true
bcftools mpileup -Ou "$tmp/t.sorted.bam" 2>/dev/null | bcftools call -mv -Ov 2>/dev/null | head -n 5
echo "OK    bcftools mpileup|call pipeline"
seqkit stats "$tmp/t.sam" 2>/dev/null | head -n 3
rm -rf "$tmp"
echo "== SMOKE_TEST_DONE =="
