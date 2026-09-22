#!/usr/bin/env bash
# search_round2.sh —— 第二轮检索：修正查询 + 按深度取有效样本
#
# 修正的背景：
#   ① NCBI BioProject 用 "%22Oryza+sativa%22[Organism]+AND+WGS" 只命中 1 条 —— 语法与该库字段不匹配
#   ② ENA 默认排序的前 5000 条中 73% 是 <1x 低深度数据，存在有序偏倚
#      → 本项目需要的是深度足够（>=5x）的建库材料，应直接用 base_count 范围过滤
set -uo pipefail

OUTDIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
mkdir -p "$OUTDIR"
EUT="https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ENA="https://www.ebi.ac.uk/ena/portal/api/search"

echo "===== 第二轮检索 ====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo

# ============ A. NCBI BioProject / BioSample 修正查询 ============
echo "----- A. NCBI 修正查询（BioProject / BioSample / nuccore）-----"
R2="$OUTDIR/ncbi_search_summary_round2.tsv"
printf 'database\tquery_label\tquery_term\thit_count\n' > "$R2"

c () {  # $1=db $2=label $3=term
  local n
  n=$(curl -s --max-time 60 "$EUT/esearch.fcgi?db=$1&term=$2&retmax=0&retmode=json" \
      | grep -o '"count":"[0-9]*"' | head -1 | grep -o '[0-9]*')
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "${n:-NA}" >> "$R2"
  printf '  %-12s %-28s %s\n' "$1" "$2" "${n:-NA}"
  sleep 0.4
}

# BioProject：不带 [Organism] 限定的方式（用 text word 检索 project title）
c bioproject "OS-plain"        '%22Oryza+sativa%22'
c bioproject "rice-plain"      'rice'
c bioproject "rice-genome"     'rice+AND+genome'
c bioproject "OS-organism"     '%22Oryza+sativa%22%5BOrganism%5D'
# BioSample
c biosample  "OS-organism"     '%22Oryza+sativa%22%5BOrganism%5D'
c biosample  "OS-cultivar"     '%22Oryza+sativa%22%5BOrganism%5D+AND+cultivar'
c biosample  "OS-indica"       '%22Oryza+sativa%22%5BOrganism%5D+AND+indica'
c biosample  "OS-japonica"     '%22Oryza+sativa%22%5BOrganism%5D+AND+japonica'
# SRA 细分：按平台
c sra        "OS-WGS-ILLUMINA" '%22Oryza+sativa%22%5BOrganism%5D+AND+WGS%5BStrategy%5D+AND+%22ILLUMINA%22%5BPlatform%5D'
c sra        "OS-WGS-PACBIO"   '%22Oryza+sativa%22%5BOrganism%5D+AND+WGS%5BStrategy%5D+AND+%22PACBIO%22%5BPlatform%5D'

echo

# ============ B. ENA 按深度过滤取有效建库材料 ============
echo "----- B. ENA 按 base_count 过滤（有效建库材料）-----"
FIELDS="run_accession,experiment_accession,sample_accession,study_accession,secondary_study_accession,instrument_platform,instrument_model,library_layout,library_strategy,library_source,read_count,base_count,center_name,first_public,country,sample_title,sample_alias,scientific_name,tax_id,fastq_ftp,fastq_bytes"

ena_cnt () {
  local label="$1" q="$2"
  local n
  n=$(curl -s --max-time 120 -G "$ENA" \
        --data-urlencode "result=read_run" \
        --data-urlencode "query=$q" \
        --data-urlencode "fields=run_accession" \
        --data-urlencode "format=tsv" --data-urlencode "limit=0" 2>/dev/null | tail -n +2 | wc -l)
  printf '  %-34s %s\n' "$label" "$n"
  sleep 0.3
}

# base_count 单位是 bp；1x ≈ 3.75e8 bp
ena_cnt ">=1x  (3.75e8 bp)"  'tax_eq(4530) AND library_strategy="WGS" AND base_count>=375000000'
ena_cnt ">=5x  (1.875e9 bp)" 'tax_eq(4530) AND library_strategy="WGS" AND base_count>=1875000000'
ena_cnt ">=10x (3.75e9 bp)"  'tax_eq(4530) AND library_strategy="WGS" AND base_count>=3750000000'
ena_cnt ">=20x (7.5e9 bp)"   'tax_eq(4530) AND library_strategy="WGS" AND base_count>=7500000000'
echo

echo "  拉取 >=5x 的 run 级清单..."
curl -s --max-time 300 -G "$ENA" \
  --data-urlencode "result=read_run" \
  --data-urlencode 'query=tax_eq(4530) AND library_strategy="WGS" AND library_source="GENOMIC" AND base_count>=1875000000' \
  --data-urlencode "fields=$FIELDS" \
  --data-urlencode "format=tsv" \
  --data-urlencode "limit=10000" \
  -o "$OUTDIR/ena_rice_wgs_deep_runs.tsv"
GOT=$(( $(wc -l < "$OUTDIR/ena_rice_wgs_deep_runs.tsv") - 1 ))
printf '  已保存：%s 行，%s bytes\n' \
  "$GOT" "$(wc -c < "$OUTDIR/ena_rice_wgs_deep_runs.tsv")"

# 行数恰好等于 limit 时，文件很可能是**截断**的，必须显式警告：
# 本脚本用 limit=0 单独计数（见上文 ena_cnt），而用 limit=10000 拉取，
# 两者不比较的话，截断会被静默当成全量。
if [ "$GOT" -eq 10000 ]; then
  echo "  [警告] 行数恰等于 limit=10000，清单**很可能被截断**，不得当作全量统计使用。"
  echo "         真实总数请见上方 '>=10x' 的 limit=0 计数，并请存档到文件中。"
fi

echo
echo "===== 第二轮检索完成 ====="
ls -la "$OUTDIR"
