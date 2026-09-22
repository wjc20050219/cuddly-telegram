#!/usr/bin/env bash
# probe_ddbj2.sh —— DDBJ 检索多路径探测
#
# 背景：DDBJ Search 的 /db-portal/search 端点连续返回 504 Gateway Time-out
#       （连 /service-info 也是 504），但参数校验类错误可正常返回，
#       说明 nginx 可达、Elasticsearch 后端超时或不可用。
# 目的：找出当前仍可用的 DDBJ 检索路径。
BASE="https://ddbj.nig.ac.jp/search/api"

p () {
  local label="$1" url="$2" out="$3" tmo="$4"
  local code
  code=$(curl -s -L -o "$out" -w '%{http_code}|%{time_total}' --max-time "$tmo" \
              -H 'Accept: application/json' "$url" 2>/dev/null)
  local sz; sz=$(wc -c < "$out" 2>/dev/null || echo 0)
  printf '  %-34s HTTP %-24s %8s bytes\n' "$label" "$code" "$sz"
}

echo "===== DDBJ 检索多路径探测 ====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo
echo "--- A. Search API 各端点 ---"
p "service-info"           "$BASE/service-info" /tmp/p_si.json 120
p "entries/sra-run/DRR771384"  "$BASE/entries/sra-run/DRR771384" /tmp/p_run.json 120
p "entries/biosample/SAMD00000001" "$BASE/entries/biosample/SAMD00000001" /tmp/p_bios.json 120
p "db-portal/search 精确 accession" "$BASE/db-portal/search?db=sra&q=DRR771384&perPage=20" /tmp/p_q1.json 120
p "db-portal/search 窄查询"         "$BASE/db-portal/search?db=biosample&q=cultivar&perPage=20" /tmp/p_q2.json 120
p "db-portal/cross-search"          "$BASE/db-portal/cross-search?q=Oryza&perPage=20" /tmp/p_q3.json 120

echo
echo "--- B. DDBJ 传统资源页（非 Search API）---"
p "resource/sra-run/DRR771384"  "https://ddbj.nig.ac.jp/resource/sra-run/DRR771384" /tmp/p_res.json 120
p "getentry (na)"               "https://getentry.ddbj.nig.ac.jp/getentry/na/DRR771384" /tmp/p_ge.txt 120

echo
echo "--- C. DDBJ Search 前端 API（ddbj-search-front 可能用别的路径）---"
p "search/entry/ddbj/biosample" "https://ddbj.nig.ac.jp/search/entry/sra-run/DRR771384.jsonld" /tmp/p_ld.json 120

echo
echo "===== 响应内容抽样（仅打印非 504 的）====="
for f in /tmp/p_si.json /tmp/p_run.json /tmp/p_bios.json /tmp/p_q1.json /tmp/p_q2.json /tmp/p_q3.json /tmp/p_res.json /tmp/p_ge.txt /tmp/p_ld.json; do
  [ -f "$f" ] || continue
  if grep -q 'Gateway Time-out' "$f" 2>/dev/null; then continue; fi
  if [ ! -s "$f" ]; then continue; fi
  echo "--- $(basename "$f") ---"
  head -c 700 "$f"
  echo; echo
done
