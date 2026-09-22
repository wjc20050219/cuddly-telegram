#!/usr/bin/env bash
# probe_ddbj.sh —— 探测 DDBJ Search API（v3：修正 db 枚举 与 perPage 取值）
# 已探明的约束：
#   db        ∈ {ddbj, sra, bioproject, biosample, jga, gea, metabobank, taxonomy}
#   perPage   ∈ {20, 50, 100}
#   subtype   通过查询字段 type: 过滤，如 type:sra-run
# 注意：DDBJ Search 后端较慢，单次请求 50–90 秒
BASE="https://ddbj.nig.ac.jp/search/api"

probe () {
  local label="$1" url="$2" out="$3" tmo="$4"
  local code
  code=$(curl -s -o "$out" -w '%{http_code}|%{time_total}' --max-time "$tmo" "$url" 2>/dev/null)
  printf '  %-32s HTTP %s\n' "$label" "$code"
}

echo "===== 1. DDBJ Search API 连通性（db + perPage 均已修正）====="
probe "db=sra, perPage=20"        "$BASE/db-portal/search?db=sra&q=Oryza+sativa&perPage=20" /tmp/d_sra.json 150
probe "db=sra, type:sra-run"      "$BASE/db-portal/search?db=sra&q=type%3Asra-run+AND+Oryza+sativa&perPage=20" /tmp/d_run.json 150
probe "db=biosample"              "$BASE/db-portal/search?db=biosample&q=Oryza+sativa&perPage=20" /tmp/d_bios.json 150
probe "db=bioproject"             "$BASE/db-portal/search?db=bioproject&q=Oryza+sativa&perPage=20" /tmp/d_bp.json 150

echo
echo "===== 2. db=sra 响应（前 2500 字符）====="
head -c 2500 /tmp/d_sra.json 2>/dev/null
echo
echo
echo "===== 3. 响应体大小 ====="
for f in /tmp/d_sra.json /tmp/d_run.json /tmp/d_bios.json /tmp/d_bp.json; do
  [ -f "$f" ] && printf '  %-22s %s bytes\n' "$(basename "$f")" "$(wc -c < "$f")"
done
