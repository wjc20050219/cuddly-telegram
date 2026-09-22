#!/usr/bin/env bash
# probe_ena_samples.sh —— 测试 ENA 样本属性（cultivar 等）的可获取性
#
# 动机：ENA 的 read_run.sample_title 字段质量差（大量 "Plant sample from Oryza sativa"、
#       育种行编号、"3K RGP mapping to ..."），无法直接当作品种名。
#       TASK-012 需要 variety_name 字段，须确认能否从样本属性中取到 cultivar。
set -uo pipefail
SAMPLE="SAMEA114006088"   # 已知样本：rice_shoot_Caravela_ITQB

echo "===== ENA 样本属性可获取性测试 ====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "测试样本：$SAMPLE"
echo

t () {
  local label="$1"; shift
  local code
  code=$(curl -s -L -o /tmp/ena_s.out -w '%{http_code}|%{time_total}' --max-time 60 "$@" 2>/dev/null)
  printf '  %-34s HTTP %-16s %7s bytes\n' "$label" "$code" "$(wc -c < /tmp/ena_s.out 2>/dev/null || echo 0)"
}

echo "--- A. 样本 XML 的不同获取方式 ---"
t "browser/api/xml (Accept xml)"  -H 'Accept: application/xml' \
    "https://www.ebi.ac.uk/ena/browser/api/xml/$SAMPLE"
cp /tmp/ena_s.out /tmp/ena_a.xml 2>/dev/null

t "browser/api/xml?lineLimit=0"   -H 'Accept: application/xml' \
    "https://www.ebi.ac.uk/ena/browser/api/xml/$SAMPLE?lineLimit=0"
cp /tmp/ena_s.out /tmp/ena_b.xml 2>/dev/null

t "browser/api/xml (无 Accept)"    "https://www.ebi.ac.uk/ena/browser/api/xml/$SAMPLE"
cp /tmp/ena_s.out /tmp/ena_c.xml 2>/dev/null

t "sra-browser API"                "https://www.ebi.ac.uk/ena/browser/api/sra/$SAMPLE"
cp /tmp/ena_s.out /tmp/ena_d.xml 2>/dev/null

echo
echo "--- B. ENA Portal API 的 sample 结果类型 ---"
t "portal result=sample"  -G "https://www.ebi.ac.uk/ena/portal/api/search" \
    --data-urlencode "result=sample" \
    --data-urlencode "query=sample_accession=$SAMPLE" \
    --data-urlencode "fields=sample_accession,scientific_name,sample_title,description" \
    --data-urlencode "format=tsv"
cp /tmp/ena_s.out /tmp/ena_e.tsv 2>/dev/null

echo
echo "--- C. 抽查：XML 中是否含 cultivar 属性 ---"
for f in /tmp/ena_a.xml /tmp/ena_b.xml /tmp/ena_c.xml /tmp/ena_d.xml; do
  [ -s "$f" ] || continue
  if grep -qi 'cultivar' "$f"; then
    printf '  %-22s ★ 含 cultivar\n' "$(basename "$f")"
    grep -io '<TAG>[^<]*</TAG>\|<VALUE>[^<]*</VALUE>' "$f" | head -20 | sed 's/^/      /'
  else
    printf '  %-22s 不含 cultivar（或非 XML）\n' "$(basename "$f")"
  fi
done

echo
echo "--- D. 成功响应的原始内容（前 1500 字符）---"
for f in /tmp/ena_a.xml /tmp/ena_e.tsv; do
  [ -s "$f" ] || continue
  if head -1 "$f" | grep -qi 'whitelabel\|<html'; then continue; fi
  echo "  ---- $(basename "$f") ----"
  head -c 1500 "$f" | sed 's/^/    /'
  echo
done
