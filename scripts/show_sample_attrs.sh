#!/usr/bin/env bash
# show_sample_attrs.sh —— 展开 ENA 样本的 SAMPLE_ATTRIBUTES 段，确认是否有结构化 cultivar 字段
set -uo pipefail
S="SAMEA114006088"
curl -s -L --max-time 60 "https://www.ebi.ac.uk/ena/browser/api/xml/$S" -o /tmp/sattr.xml

echo "===== SAMPLE_ATTRIBUTES 段（完整）====="
sed -n '/<SAMPLE_ATTRIBUTES>/,/<\/SAMPLE_ATTRIBUTES>/p' /tmp/sattr.xml

echo
echo "===== 平铺为 TAG / VALUE 列表 ====="
sed -n '/<SAMPLE_ATTRIBUTES>/,/<\/SAMPLE_ATTRIBUTES>/p' /tmp/sattr.xml \
 | tr -d '\n' | sed 's/<\/SAMPLE_ATTRIBUTE>/\n/g' \
 | sed 's/.*<TAG>\(.*\)<\/TAG>.*<VALUE>\(.*\)<\/VALUE>.*/\1\t=\t\2/' \
 | sed 's/^[[:space:]]*//'

echo
echo "===== 再抽 3 个水稻样本，看 cultivar 字段是否普遍存在 ====="
for s in SAMEA114006088 SAMEA114006089 SAMEA114006091; do
  curl -s -L --max-time 60 "https://www.ebi.ac.uk/ena/browser/api/xml/$s" -o /tmp/s1.xml 2>/dev/null
  printf '  %-16s ' "$s"
  grep -o '<TAG>cultivar</TAG>[[:space:]]*<VALUE>[^<]*</VALUE>' /tmp/s1.xml | head -1 \
    | sed 's/<TAG>cultivar<\/TAG>//; s/<VALUE>//; s/<\/VALUE>//' \
    | sed 's/^[[:space:]]*/cultivar = /' || true
  grep -q '<TAG>cultivar</TAG>' /tmp/s1.xml || echo "（无 cultivar 标签）"
done

echo
echo "===== 测试：ENA Portal API 能否按 sample 结果类型批量拉 cultivar ====="
curl -s -G --max-time 120 "https://www.ebi.ac.uk/ena/portal/api/search" \
  --data-urlencode "result=sample" \
  --data-urlencode 'query=tax_eq(4530)' \
  --data-urlencode "fields=sample_accession,scientific_name,sample_title,description" \
  --data-urlencode "format=tsv" \
  --data-urlencode "limit=5" -o /tmp/sample_bulk.tsv
echo "  返回行数：$(( $(wc -l < /tmp/sample_bulk.tsv) - 1 ))"
head -6 /tmp/sample_bulk.tsv | cut -c1-260 | sed 's/^/    /'
