#!/usr/bin/env bash
# 04_joint_snp.sh —— 对当前样本清单中的 CRAM 做联合 SNP calling。
# 正式 SNP 指纹必须使用该多样本 VCF；不要用 variant-only 单样本 VCF 拼矩阵。
# 用法: bash 04_joint_snp.sh
# 产出: vcf/cohort.raw.vcf.gz + cohort.biallelic_snps.vcf.gz
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

REF="$(ref_fasta)"
MAPQ="${MAPQ:-20}"
BASEQ="${BASEQ:-20}"
RAW="$RV_VCF/cohort.raw.vcf.gz"
SNPS="$RV_VCF/cohort.biallelic_snps.vcf.gz"
STATE="$RV_VCF/cohort_calling_state.tsv"
LIST="$RV_TMP/cohort_crams.list"
SPEC="$RV_TMP/cohort_calling_spec.tsv"

[ -s "$REF.fai" ] || die "参考基因组未就绪，请先运行 03_align.sh"
: > "$LIST"
for sid in $(sample_ids); do
  cram="$RV_BAM/$sid.cram"
  [ -s "$cram" ] || die "缺少 CRAM: $cram"
  [ -s "$cram.crai" ] || samtools index -@ 4 "$cram"
  printf '%s\n' "$cram" >> "$LIST"
done
n=$(wc -l < "$LIST")

# cohort 文件名固定，因此必须验证其样本集/输入是否与当前 manifest 一致；
# 否则 smoke5 的 VCF 可能在扩到 Pilot 30 时被错误复用。
ref_sha=$(awk -F'\t' 'NR==2{print $7}' "$RV_REF/reference_record.tsv" 2>/dev/null || true)
[ -n "$ref_sha" ] || ref_sha=$(sha256sum "$REF" | awk '{print $1}')
{
  printf 'reference_sha256\t%s\nmapq\t%s\nbaseq\t%s\n' "$ref_sha" "$MAPQ" "$BASEQ"
  while read -r cram; do
    sid=$(basename "${cram%.cram}")
    printf 'sample\t%s\t%s\t%s\n' "$sid" "$(stat -c%s "$cram")" "$(stat -c%Y "$cram")"
  done < "$LIST"
} > "$SPEC"
signature=$(sha256sum "$SPEC" | awk '{print $1}')
old_signature=$(awk -F'\t' '$1=="signature"{print $2}' "$STATE" 2>/dev/null || true)
if [ "$n" -ge 2 ] && { [ -s "$RAW" ] || [ -s "$SNPS" ]; } && [ "$old_signature" != "$signature" ]; then
  log "当前 cohort 与缓存签名不同，删除旧联合 VCF 后重算"
  rm -f "$RAW" "$RAW.tbi" "$SNPS" "$SNPS.tbi" "$STATE"
fi
if [ "$n" -ge 2 ] && [ -s "$RAW" ] && ! bcftools view -h "$RAW" >/dev/null 2>&1; then
  log "缓存 RAW VCF 不完整，删除后重算"
  rm -f "$RAW" "$RAW.tbi" "$SNPS" "$SNPS.tbi" "$STATE"
fi
if [ "$n" -ge 2 ] && [ -s "$SNPS" ] && ! bcftools view -h "$SNPS" >/dev/null 2>&1; then
  log "缓存 SNP VCF 不完整，删除后重算"
  rm -f "$SNPS" "$SNPS.tbi" "$STATE"
fi

[ "$n" -ge 1 ] || die "当前 manifest 没有样本"
if [ "$n" -lt 2 ]; then
  sid=$(sample_ids | head -n1)
  smoke="$RV_VCF/${sid}.smoke.vcf.gz"
  log "单样本 smoke test：只验证 bcftools 链路，不产出正式 marker/准确率"
  bcftools mpileup -f "$REF" -q "$MAPQ" -Q "$BASEQ" -a FORMAT/AD,FORMAT/DP \
    -Ou --threads "$((THREADS/2))" "$(cat "$LIST")" 2> "$RV_LOG/${sid}.smoke.mpileup.log" \
    | bcftools call -mv -f GQ -Oz --threads "$((THREADS/2))" -o "$smoke" \
    || die "单样本 bcftools smoke test 失败"
  bcftools index -t "$smoke"
  printf 'metric\tvalue\nmode\tsingle_sample_smoke\nsample_count\t1\nvariant_count\t%s\n' \
    "$(bcftools index -n "$smoke")" > "$RV_VCF/cohort_calling_summary.tsv"
  log "单样本 SNP smoke test 完成；正式联合 calling 须使用 >=2 个样本"
  exit 0
fi

log "联合 SNP calling：$n 个样本"
if [ ! -s "$RAW" ]; then
  bcftools mpileup -f "$REF" -q "$MAPQ" -Q "$BASEQ" -a FORMAT/AD,FORMAT/DP \
    -Ou --threads "$((THREADS/2))" -b "$LIST" 2> "$RV_LOG/cohort.mpileup.log" \
    | bcftools call -mv -f GQ -Oz --threads "$((THREADS/2))" -o "$RAW" \
    || die "联合 SNP calling 失败"
  bcftools index -t "$RAW"
elif [ ! -s "$RAW.tbi" ]; then
  bcftools index -t "$RAW"
fi

log "规范化并保留二等位 SNP（其余 QC 在 Pilot 分布审查后执行）"
if [ ! -s "$SNPS" ]; then
  bcftools norm -f "$REF" -m -any -Ou "$RAW" \
    | bcftools view -m2 -M2 -v snps -Oz --threads "$((THREADS/2))" -o "$SNPS" \
    || die "SNP 规范化/筛选失败"
  bcftools index -t "$SNPS"
elif [ ! -s "$SNPS.tbi" ]; then
  bcftools index -t "$SNPS"
fi

{
  printf 'key\tvalue\n'
  printf 'signature\t%s\n' "$signature"
  printf 'sample_count\t%s\n' "$n"
  printf 'manifest\t%s\n' "$(readlink -f "$RV_SAMPLES")"
  printf 'reference_sha256\t%s\n' "$ref_sha"
  printf 'mapq\t%s\nbaseq\t%s\n' "$MAPQ" "$BASEQ"
} > "$STATE"

{
  printf 'metric\tvalue\n'
  printf 'sample_count\t%s\n' "$n"
  printf 'raw_variant_count\t%s\n' "$(bcftools index -n "$RAW")"
  printf 'biallelic_snp_count\t%s\n' "$(bcftools index -n "$SNPS")"
  printf 'reference\t%s\n' "$RV_REF_NAME"
  printf 'mapq\t%s\nbaseq\t%s\n' "$MAPQ" "$BASEQ"
  printf 'cohort_signature\t%s\n' "$signature"
} > "$RV_VCF/cohort_calling_summary.tsv"

log "联合 VCF 完成: $SNPS"
