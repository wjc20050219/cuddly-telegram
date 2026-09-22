#!/usr/bin/env bash
# fetch_ncbi_esummary.sh —— 抓取 NCBI SRA 主查询的 run 级摘要（TASK-008）
#
# 注意：esummary 用 GET 传 id 列表，URL 会在 ~200 个 UID 时过长导致失败，
#       故分批（每批 150 个）抓取后合并。
set -uo pipefail
OUTDIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
mkdir -p "$OUTDIR"
EUT="https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TERM='%22Oryza+sativa%22%5BOrganism%5D+AND+WGS%5BStrategy%5D'

echo "===== 抓取 NCBI SRA esummary ====="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "查询：\"Oryza sativa\"[Organism] AND WGS[Strategy]"
echo

echo "--- 1. esearch 取 UID（retmax=300）---"
curl -s --max-time 90 "$EUT/esearch.fcgi?db=sra&term=$TERM&retmax=300&retmode=json&sort=relevance" \
  -o /tmp/ncbi_es.json
N=$(grep -o '"count":"[0-9]*"' /tmp/ncbi_es.json | head -1)
echo "  总命中：$N"
grep -o '"idlist":\[[^]]*\]' /tmp/ncbi_es.json | grep -o '[0-9]\{6,\}' > /tmp/ncbi_uidlist.txt
echo "  取得 UID 数：$(grep -c . /tmp/ncbi_uidlist.txt)"
echo

echo "--- 2. 分批抓取 esummary（每批 150）---"
rm -f /tmp/ncbi_es_parts.txt
BATCH=150
TOTAL=$(grep -c . /tmp/ncbi_uidlist.txt)
IDX=0
while [ "$IDX" -lt "$TOTAL" ]; do
  CHUNK=$(sed -n "$((IDX+1)),$((IDX+BATCH))p" /tmp/ncbi_uidlist.txt | tr '\n' ',' | sed 's/,$//')
  NCHUNK=$(printf '%s' "$CHUNK" | tr ',' '\n' | grep -c .)
  PART="/tmp/ncbi_part_$IDX.json"
  curl -s --max-time 180 "$EUT/esummary.fcgi?db=sra&id=$CHUNK&retmode=json" -o "$PART"
  printf '  批次 %-4s UID 数 %-4s → %s bytes\n' "$IDX" "$NCHUNK" "$(wc -c < "$PART")"
  printf '%s\n' "$PART" >> /tmp/ncbi_es_parts.txt
  IDX=$((IDX+BATCH))
  sleep 1
done

echo
echo "--- 3. 用 Python 合并各批次 ---"
python3 - <<'PY'
import json, glob
from pathlib import Path
parts = sorted(glob.glob("/tmp/ncbi_part_*.json"))
merged = {"header": {"type": "esummary"}, "result": {"uids": []}}
seen = set()
for p in parts:
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        print(f"  跳过 {p}: {e}")
        continue
    r = d.get("result", {})
    for uid in r.get("uids", []):
        if uid in seen:
            continue
        seen.add(uid)
        merged["result"]["uids"].append(uid)
        merged["result"][str(uid)] = r.get(str(uid), {})
out = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/search/ncbi_sra_esummary.json")
out.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
print(f"  合并完成：{len(merged['result']['uids'])} 条 → {out} ({out.stat().st_size} bytes)")
PY

echo
echo "--- 4. 解析为 TSV ---"
cd /mnt/d/dsh/RiceVar-ID && python3 scripts/parse_ncbi_esummary.py
