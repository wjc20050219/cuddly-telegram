#!/usr/bin/env bash
# probe_sample_batch.sh —— 探测 ENA 样本属性的批量获取方式（TASK-011 技术前提）
#
# 动因：TASK-011 需要 variety_name，而该字段在 ENA 样本 XML 的
#       "subspecific genetic lineage name" 里，不在 read_run 的 TSV 中。
#       若逐个请求 10,000 个样本需约 2.4 小时；必须先确认能否批量取。
set -uo pipefail
TSV="/mnt/d/dsh/RiceVar-ID/data/metadata/search/ena_rice_wgs_deep_runs.tsv"
OUTDIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"

echo "===== ENA 样本属性批量获取探测 ====="
echo "时间：$(date '+%F %T')"
echo

# 从 ≥5× 清单取真实 sample accession
ACC_ALL=$(tail -n +2 "$TSV" | cut -f3 | grep -v '^$' | head -250)
echo "可用 sample accession 数：$(printf '%s\n' "$ACC_ALL" | grep -c .)"
echo "样例：$(printf '%s\n' "$ACC_ALL" | head -3 | tr '\n' ' ')"
echo

mklist () { printf '%s\n' "$ACC_ALL" | head -n "$1" | tr '\n' ',' | sed 's/,$//'; }

echo "--- 0. read_run 结果里是否有品种相关字段 ---"
curl -s --max-time 60 "https://www.ebi.ac.uk/ena/portal/api/returnFields?result=read_run&format=tsv" \
  -o /tmp/rf_run.tsv 2>/dev/null
echo "  read_run 字段总数：$(( $(wc -l < /tmp/rf_run.tsv) - 1 ))"
echo "  含 cultivar/variety/strain/lineage 的字段："
grep -iE 'cultivar|variety|strain|lineage|isolate|ecotype' /tmp/rf_run.tsv | sed 's/^/    /' | head -20
echo "  (若为空则 read_run 无法直接给品种名)"
echo

echo "--- 1. returnFields: result=sample 有哪些字段 ---"
curl -s --max-time 60 "https://www.ebi.ac.uk/ena/portal/api/returnFields?result=sample&format=tsv" \
  -o /tmp/rf_sample.tsv 2>/dev/null
echo "  sample 字段总数：$(( $(wc -l < /tmp/rf_sample.tsv) - 1 ))"
echo "  含 cultivar/variety/strain/lineage 的字段："
grep -iE 'cultivar|variety|strain|lineage|isolate|ecotype' /tmp/rf_sample.tsv | sed 's/^/    /' | head -20
echo

echo "--- 2. 单样本 XML（基线）---"
S1=$(printf '%s\n' "$ACC_ALL" | head -1)
T0=$(date +%s.%N)
curl -s -L --max-time 90 -o /tmp/b1.xml -w '  HTTP=%{http_code}\n' \
  "https://www.ebi.ac.uk/ena/browser/api/xml/$S1"
T1=$(date +%s.%N)
echo "  样本数：$(grep -c '<SAMPLE ' /tmp/b1.xml)  bytes=$(wc -c < /tmp/b1.xml)  耗时=$(awk -v a=$T0 -v b=$T1 'BEGIN{printf "%.2f", b-a}')s"
echo

echo "--- 3. 批量 XML（核心问题）---"
for N in 3 50 200; do
  L=$(mklist "$N")
  T0=$(date +%s.%N)
  CODE=$(curl -s -L --max-time 120 -o "/tmp/b$N.xml" -w '%{http_code}' \
    "https://www.ebi.ac.uk/ena/browser/api/xml/$L")
  T1=$(date +%s.%N)
  CNT=$(grep -c '<SAMPLE ' "/tmp/b$N.xml" 2>/dev/null || echo 0)
  printf '  请求 %-4s 个 -> HTTP=%s  返回样本数=%-5s bytes=%-9s 耗时=%ss\n' \
    "$N" "$CODE" "$CNT" "$(wc -c < "/tmp/b$N.xml")" \
    "$(awk -v a=$T0 -v b=$T1 'BEGIN{printf "%.2f", b-a}')"
  # 若返回的是错误页
  head -c 200 "/tmp/b$N.xml" | grep -qi 'error\|whitelabel\|<html' && echo "      ^ 疑似错误页"
done
echo

echo "--- 4. 批量响应中的品种名字段命中情况 ---"
for N in 1 3 50 200; do
  [ -s "/tmp/b$N.xml" ] || continue
  TOT=$(grep -c '<SAMPLE ' "/tmp/b$N.xml" 2>/dev/null || echo 0)
  CUL=$(grep -c '<TAG>subspecific genetic lineage name</TAG>' "/tmp/b$N.xml" 2>/dev/null || echo 0)
  CUL2=$(grep -ci '<TAG>cultivar</TAG>' "/tmp/b$N.xml" 2>/dev/null || echo 0)
  printf '  b%-4s 样本=%-5s  含 lineage name=%-5s  含 cultivar=%s\n' "$N" "$TOT" "$CUL" "$CUL2"
done
echo

echo "--- 5. 品种名样例（从 b200 提取前 15 个）---"
if [ -s /tmp/b200.xml ]; then
  python3 - <<'PY'
import re
from pathlib import Path
x = Path("/tmp/b200.xml").read_text(encoding="utf-8", errors="replace")
blocks = re.findall(r"<SAMPLE\s+accession=\"([^\"]+)\"(.*?)</SAMPLE>", x, re.S)
print(f"  解析出样本块：{len(blocks)}")
shown = 0
for acc, body in blocks:
    name = re.search(r"<TAG>subspecific genetic lineage name</TAG>\s*<VALUE>([^<]*)</VALUE>", body)
    rank = re.search(r"<TAG>subspecific genetic lineage rank</TAG>\s*<VALUE>([^<]*)</VALUE>", body)
    title = re.search(r"<TITLE>([^<]*)</TITLE>", body)
    if name:
        print(f"    {acc:<20} 品种={name.group(1):<24} rank={rank.group(1) if rank else '-':<10} title={title.group(1)[:30] if title else ''}")
        shown += 1
    if shown >= 15:
        break
if shown == 0:
    print("    （本批未提取到 lineage name）")
PY
fi
echo

echo "--- 6. 结论：全量获取 10,000 个样本需要多久 ---"
echo "  若批量 200 个/请求可行 -> 约 $((10000/200)) 次请求"
echo "  若只能单个请求 -> 10,000 次请求（按 ~0.85s/次 估算约 2.4 小时，可用并行加速）"
