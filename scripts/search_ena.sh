#!/usr/bin/env bash
# search_ena.sh —— TASK-009：检索 ENA（European Nucleotide Archive）
#
# 数据源：ENA Portal API（公共 API，无需认证）
# 输出：data/metadata/search/ena_*.tsv
#
# 说明：ENA 与 NCBI SRA / DDBJ DRA 同属 INSDC，三方数据互为镜像，
#       故 ENA 是"能一次查到 INSDC 全量"的最便捷入口，也是本项目选定的下载源。
set -uo pipefail

OUTDIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
mkdir -p "$OUTDIR"
API="https://www.ebi.ac.uk/ena/portal/api/search"

echo "===== TASK-009：ENA 检索 ====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "输出目录：$OUTDIR"
echo
echo "⚠️  ENA 是 INSDC 成员库，其 read_run 覆盖 NCBI SRA 与 DDBJ DRA 已同步的全部数据。"
echo "    因此本节的命中数天然包含另外两库，不是独立计数。"
echo

# ---------- 1. 命中数矩阵 ----------
echo "----- 1. 命中数矩阵 -----"
SUMMARY="$OUTDIR/ena_search_summary.tsv"
printf 'query_label\tquery\tresult\tcount\n' > "$SUMMARY"

cnt () {  # $1=label  $2=query  $3=result(默认 read_run)
  local res="${3:-read_run}" n
  n=$(curl -s --max-time 90 -G "$API" \
        --data-urlencode "result=$res" \
        --data-urlencode "query=$2" \
        --data-urlencode "fields=run_accession" \
        --data-urlencode "format=tsv" \
        --data-urlencode "limit=0" 2>/dev/null | tail -n +2 | wc -l)
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$res" "$n" >> "$SUMMARY"
  printf '  %-34s %s\n' "$1" "$n"
  sleep 0.3
}

cnt "OS-WGS"                 'tax_eq(4530) AND library_strategy="WGS"'
cnt "OS-WGS-GENOMIC"         'tax_eq(4530) AND library_strategy="WGS" AND library_source="GENOMIC"'
cnt "OS-any-strategy"        'tax_eq(4530)'
cnt "OS-cultivar-in-title"   'tax_eq(4530) AND library_strategy="WGS" AND sample_title="*cultivar*"'
cnt "Oryza-genus-WGS"        'tax_tree(4527) AND library_strategy="WGS"'
cnt "DRA-submitted-WGS"      'tax_eq(4530) AND library_strategy="WGS" AND center_name="*DDBJ*"'
cnt "OS-WGS-paired"          'tax_eq(4530) AND library_strategy="WGS" AND library_layout="PAIRED"'

echo
echo "  汇总表：$SUMMARY"
echo

# ---------- 2. 主查询：run 级清单（含 FASTQ 链接与数据量）----------
echo "----- 2. 主查询 run 级清单 -----"
FIELDS="run_accession,experiment_accession,sample_accession,study_accession,secondary_study_accession,instrument_platform,instrument_model,library_layout,library_strategy,library_source,read_count,base_count,center_name,first_public,country,sample_title,sample_alias,scientific_name,tax_id,fastq_ftp,fastq_bytes"

echo "  字段：$FIELDS"
echo "  拉取中（limit=5000）..."
curl -s --max-time 300 -G "$API" \
  --data-urlencode "result=read_run" \
  --data-urlencode 'query=tax_eq(4530) AND library_strategy="WGS" AND library_source="GENOMIC"' \
  --data-urlencode "fields=$FIELDS" \
  --data-urlencode "format=tsv" \
  --data-urlencode "limit=5000" \
  -o "$OUTDIR/ena_rice_wgs_runs.tsv"

ROWS=$(( $(wc -l < "$OUTDIR/ena_rice_wgs_runs.tsv" ) - 1 ))
printf '  已保存：%s 行（不含表头），%s bytes\n' "$ROWS" "$(wc -c < "$OUTDIR/ena_rice_wgs_runs.tsv")"

# 行数恰好等于 limit 时，文件很可能是**截断**的，必须显式警告：
# 上文第 2 步用 limit=0 得到了精确总数，若不与之比较，截断会被静默当成全量。
if [ "$ROWS" -eq 5000 ]; then
  echo "  [警告] 行数恰等于 limit=5000，清单**很可能被截断**，不得当作全量统计使用。"
  echo "         真实总数请见上方 limit=0 的计数结果。"
fi

# ---------- 3. 本地概况统计 ----------
echo
echo "----- 3. 本地概况统计 -----"
if [ "$ROWS" -gt 0 ]; then
  echo "  列头："
  head -1 "$OUTDIR/ena_rice_wgs_runs.tsv" | tr '\t' '\n' | nl | sed 's/^/    /'
  echo
  echo "  按测序平台统计："
  awk -F'\t' 'NR>1{p[$6]++} END{for(k in p) printf "    %-24s %d\n", k, p[k]}' \
      "$OUTDIR/ena_rice_wgs_runs.tsv" | sort -k2 -rn
  echo
  echo "  按文库布局统计："
  awk -F'\t' 'NR>1{p[$8]++} END{for(k in p) printf "    %-24s %d\n", k, p[k]}' \
      "$OUTDIR/ena_rice_wgs_runs.tsv" | sort -k2 -rn
  echo
  echo "  数据量（base_count）分布 —— 按推算深度分箱（基因组 375 Mb）："
  awk -F'\t' 'NR>1 && $12!="" {d=$12/375000000; if(d<1)b["<1x"]++; else if(d<5)b["1-5x"]++; else if(d<10)b["5-10x"]++; else if(d<20)b["10-20x"]++; else if(d<30)b["20-30x"]++; else b[">=30x"]++} END{for(k in b) printf "    %-24s %d\n", k, b[k]}' \
      "$OUTDIR/ena_rice_wgs_runs.tsv" | sort
  echo
  echo "  有 FASTQ 直链的 run 数："
  awk -F'\t' 'NR>1 && $20!="" {n++} END{printf "    %d\n", n+0}' "$OUTDIR/ena_rice_wgs_runs.tsv"
fi

echo
echo "===== 检索完成 ====="
ls -la "$OUTDIR"
