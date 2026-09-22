#!/usr/bin/env bash
# search_ncbi.sh —— TASK-008：检索 NCBI SRA / BioProject / BioSample / GenBank
#
# v2 修正（2026-09-16）：
#   v1 的 count_db 函数把"标签"($2) 当查询词，而实际查询词是 $3，
#   导致 bioproject/biosample/nuccore 的命中数全部无效。
#   本版统一为 3 参数 (db, label, term)，并抓取 querytranslation 作为执行证据。
#
# 数据源：NCBI E-utilities（公共 API，无 API key 时限 3 请求/秒，故 sleep 1）
# 输出：data/metadata/search/ncbi_*.tsv
set -uo pipefail

OUTDIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
mkdir -p "$OUTDIR"
EUT="https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUT="$OUTDIR/ncbi_search_summary.tsv"

echo "===== TASK-008：NCBI 检索（v2 修正版）====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo
printf 'database\tlabel\tquery_term\tcount\tquerytranslation\n' > "$OUT"

q () {  # $1=db  $2=label  $3=urlencoded_term
  local db="$1" label="$2" term="$3" resp count trans
  resp=$(curl -s --max-time 60 "$EUT/esearch.fcgi?db=$db&term=$term&retmax=0&retmode=json")
  count=$(printf '%s' "$resp" | grep -o '"count":"[0-9]*"' | head -1 | grep -o '[0-9]*')
  # 支持 JSON 转义引号
  trans=$(printf '%s' "$resp" | grep -o '"querytranslation":"\([^"\\]\|\\.\)*"' | head -1 \
          | sed 's/^"querytranslation":"//; s/"$//; s/\\"/"/g')
  printf '%s\t%s\t%s\t%s\t%s\n' "$db" "$label" "$term" "${count:-NA}" "${trans:-NA}" >> "$OUT"
  printf '  %-11s %-30s %-10s\n' "$db" "$label" "${count:-NA}"
  printf '  %-11s   └─ 实际执行：%s\n' "" "${trans:-NA}"
  sleep 1
}

OS='%22Oryza+sativa%22%5BOrganism%5D'
ENC () { printf '%s' "$1" | sed 's/ /+/g'; }

echo "--- A. 任务清单指定的 5 个关键词（对 SRA 自由文本检索）---"
q sra "KW1: Oryza sativa WGS"        "$(ENC 'Oryza sativa WGS')"
q sra "KW2: rice whole genome seq"   "$(ENC 'rice whole genome sequencing')"
q sra "KW3: rice variety WGS"        "$(ENC 'rice variety WGS')"
q sra "KW4: rice cultivar WGS"       "$(ENC 'rice cultivar WGS')"
q sra "KW5: rice genome resequencing" "$(ENC 'rice genome resequencing')"

echo
echo "--- B. 精确检索（按物种 + 文库策略，作为可信基线）---"
q sra       "OS"                   "$OS"
q sra       "OS + WGS[Strategy]"   "$OS+AND+WGS%5BStrategy%5D"
q sra       "OS + WGS + PAIRED"    "$OS+AND+WGS%5BStrategy%5D+AND+paired%5BLayout%5D"
q sra       "OS + WGS + ILLUMINA"  "$OS+AND+WGS%5BStrategy%5D+AND+ILLUMINA%5BPlatform%5D"
q bioproject "OS"                  "$OS"
q biosample  "OS"                  "$OS"
q nuccore    "OS"                  "$OS"
q nuccore    "OS + refseq"         "$OS+AND+srcdb_refseq%5Bprop%5D"

echo
echo "--- C. 主查询 run 级清单 ---"
MAIN="$OS+AND+WGS%5BStrategy%5D"
IDS=$(curl -s --max-time 90 "$EUT/esearch.fcgi?db=sra&term=$MAIN&retmax=500&retmode=json&sort=relevance" \
      | grep -o '"idlist":\[[^]]*\]')
echo "$IDS" | grep -o '[0-9]\{6,\}' | tr '\n' ',' | sed 's/,$//' > /tmp/ncbi_uids.txt
echo "  取得 UID 数：$(printf '%s' "$(cat /tmp/ncbi_uids.txt)" | tr ',' '\n' | grep -c .)"
if [ "$(wc -c < /tmp/ncbi_uids.txt)" -gt 5 ]; then
  curl -s --max-time 180 "$EUT/esummary.fcgi?db=sra&id=$(cat /tmp/ncbi_uids.txt)&retmode=json" \
       -o "$OUTDIR/ncbi_sra_esummary.json"
  printf '  esummary 原始响应：%s bytes\n' "$(wc -c < "$OUTDIR/ncbi_sra_esummary.json")"
fi

echo
echo "===== 汇总 ====="
echo "  结果表：$OUT"
printf '  %-11s %-30s %s\n' "DATABASE" "LABEL" "COUNT"
printf '  %s\n' "-----------------------------------------------------------------"
tail -n +2 "$OUT" | while IFS=$'\t' read -r db label t c tr; do
  printf '  %-11s %-30s %s\n' "$db" "$label" "$c"
done
