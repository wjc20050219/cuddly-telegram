#!/usr/bin/env bash
# verify_ncbi_counts.sh —— 核验 NCBI 命中数（v2：修正参数传递 bug）
#
# v1 的 bug：函数内用 $2 作查询词，但调用时 $2 是"标签"、$3 才是查询词，
#           导致实际搜的是标签字符串（如 "OS-organism-try1"），全部结果无效。
#
# 目的：同时抓取 count 与 querytranslation，确认"实际搜的是什么"。
#       NCBI E-utilities 会把无法识别的字段限定符静默降级为 All Fields。
set -uo pipefail
OUTDIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
mkdir -p "$OUTDIR"
EUT="https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUT="$OUTDIR/ncbi_count_verification.tsv"

echo "===== NCBI 命中数核验（v2）====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
printf 'database\tlabel\tquery\tcount\tquerytranslation\n' > "$OUT"

v () {  # $1=db  $2=label  $3=urlencoded_term
  local db="$1" label="$2" term="$3"
  local resp count trans
  resp=$(curl -s --max-time 60 "$EUT/esearch.fcgi?db=$db&term=$term&retmax=0&retmode=json")
  count=$(printf '%s' "$resp" | grep -o '"count":"[0-9]*"' | head -1 | grep -o '[0-9]*')
  trans=$(printf '%s' "$resp" | grep -o '"querytranslation":"[^"]*"' | head -1 \
          | sed 's/^"querytranslation":"//; s/"$//')
  printf '%s\t%s\t%s\t%s\t%s\n' "$db" "$label" "$term" "${count:-NA}" "${trans:-NA}" >> "$OUT"
  printf '  %-11s %-26s count=%-9s  %s\n' "$db" "$label" "${count:-NA}" "${trans:-NA}"
  sleep 1
}

OS='%22Oryza+sativa%22%5BOrganism%5D'

echo "--- A. biosample 矛盾复核（同一查询连测 3 次，检验结果是否稳定）---"
for i in 1 2 3; do v biosample "OS-organism-try$i" "$OS"; done

echo
echo "--- B. SRA 字段限定符是否被 NCBI 识别 ---"
echo "  判据：querytranslation 中若出现 [All Fields]，说明限定符被降级，命中数不可信"
v sra "OS+WGS[Strategy]"      "$OS+AND+WGS%5BStrategy%5D"
v sra "OS+WGS(无限定符)"       "$OS+AND+WGS"
v sra "OS-only"               "$OS"
v sra "OS+ILLUMINA[Platform]" "$OS+AND+ILLUMINA%5BPlatform%5D"
v sra "OS+WGS+ILLUMINA"       "$OS+AND+WGS%5BStrategy%5D+AND+ILLUMINA%5BPlatform%5D"

echo
echo "--- C. bioproject / biosample 的正确检索方式 ---"
v bioproject "OS-quoted"      "$OS"
v bioproject "Oryza[Organism]" 'Oryza%5BOrganism%5D'
v biosample  "OS-quoted"      "$OS"
v biosample  "Oryza[Organism]" 'Oryza%5BOrganism%5D'
v nuccore    "OS-quoted"      "$OS"

echo
echo "===== 结果表 ====="
echo "文件：$OUT"
echo
printf '  %-11s %-26s %-9s %s\n' "DATABASE" "LABEL" "COUNT" "QUERY TRANSLATION"
printf '  %s\n' "-------------------------------------------------------------------------------"
tail -n +2 "$OUT" | while IFS=$'\t' read -r db label q c t; do
  printf '  %-11s %-26s %-9s %s\n' "$db" "$label" "$c" "$t"
done
