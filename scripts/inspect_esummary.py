#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inspect_esummary.py —— 查看 NCBI SRA esummary JSON 的真实结构，以便修正解析器"""
import json
from pathlib import Path

SRC = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/search/ncbi_sra_esummary.json")
data = json.loads(SRC.read_text(encoding="utf-8", errors="replace"))
result = data.get("result", {})
uids = result.get("uids", [])

print(f"顶层键：{list(data.keys())}")
print(f"result 键（前 15）：{list(result.keys())[:15]}")
print(f"记录数：{len(uids)}")
print()

uid = uids[0]
rec = result[str(uid)]
print(f"=== 记录 {uid} 的字段 ===")
for k, v in rec.items():
    s = str(v)
    print(f"  {k:<22} ({type(v).__name__:<5}) {s[:180]!r}")
print()

# 若含 expxml / runs，打印完整内容
for key in ("expxml", "runs", "extlinks"):
    if key in rec:
        print(f"=== {key} 完整内容 ===")
        v = rec[key]
        print(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)[:1500])
        print()

# 统计：所有记录的 accession 前缀
from collections import Counter
pref = Counter()
for u in uids:
    r = result.get(str(u), {})
    acc = r.get("accession", "")
    if acc:
        pref[acc[:3]] += 1
print("=== accession 前缀分布（前 10）===")
for k, v in pref.most_common(10):
    print(f"  {k}  {v}")
