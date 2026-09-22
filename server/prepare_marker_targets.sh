#!/usr/bin/env bash
# prepare_marker_targets.sh —— 把冻结 marker VCF 转为 bcftools 定点分型目标。
# 用法: bash prepare_marker_targets.sh frozen_markers.vcf.gz [alleles.tsv.gz]
# 输入 marker 必须在 Pilot 内冻结；不得用独立面板结果重选。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

IN="${1:-}"
OUT="${2:-$RV_META/frozen_markers.tsv.gz}"
REGIONS="${OUT%.tsv.gz}.regions.tsv.gz"
[ -n "$IN" ] && [ -s "$IN" ] || die "用法: bash prepare_marker_targets.sh frozen_markers.vcf.gz [alleles.tsv.gz]"

mkdir -p "$(dirname "$OUT")"
tmp="$RV_TMP/frozen_markers.$$.tsv"
bcftools view -m2 -M2 -v snps "$IN" -Ou \
  | bcftools query -f '%CHROM\t%POS\t%REF,%ALT\n' \
  | sort -k1,1V -k2,2n -u > "$tmp"
[ -s "$tmp" ] || die "marker VCF 中没有二等位 SNP"

# bcftools call -C alleles -T 需要 CHROM/POS/REF,ALT 三列；mpileup -R 则使用独立两列 regions，
# 避免把 REF,ALT 错当作区间终点。
bgzip -c "$tmp" > "$OUT"
tabix -f -s 1 -b 2 -e 2 "$OUT"
cut -f1,2 "$tmp" | bgzip -c > "$REGIONS"
tabix -f -s 1 -b 2 -e 2 "$REGIONS"
rm -f "$tmp"

count="$(zcat "$OUT" | wc -l)"
{
  printf 'allele_target\tregions_target\tmarker_count\tallele_sha256\tregions_sha256\tsource_vcf\tsource_vcf_sha256\tcreated\n'
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(basename "$OUT")" "$(basename "$REGIONS")" "$count" \
    "$(sha256sum "$OUT" | awk '{print $1}')" "$(sha256sum "$REGIONS" | awk '{print $1}')" \
    "$IN" "$(sha256sum "$IN" | awk '{print $1}')" "$(date '+%F %T')"
} > "${OUT%.tsv.gz}.record.tsv"
log "冻结 marker targets 已生成: $OUT + $REGIONS ($count SNP)"
