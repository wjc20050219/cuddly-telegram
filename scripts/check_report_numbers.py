#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_report_numbers.py —— 核对报告里的数字与数据文件实际值是否一致"""
import csv
from collections import Counter
from pathlib import Path

CAND = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")


def rows(p: Path) -> list[list[str]]:
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.reader(fh, delimiter="\t"))


print("=== 数据文件实际值（权威）===")
al = rows(CAND / "variety_alias.tsv")
ca = rows(CAND / "variety_canonical.tsv")
du = rows(CAND / "duplicate_samples.tsv")
cs = rows(CAND / "candidate_samples.tsv")

print(f"variety_alias.tsv        行数 = {len(al)-1:,}")
print(f"variety_canonical.tsv    行数 = {len(ca)-1:,}  （规范品种数）")
print(f"duplicate_samples.tsv    行数 = {len(du)-1:,}  （重复组数）")
print(f"candidate_samples.tsv    行数 = {len(cs)-1:,}")

print()
print("=== 重复检查分类明细 ===")
ti = du[0].index("duplicate_type")
c = Counter(x[ti] for x in du[1:])
for k, v in c.most_common():
    print(f"  {k:<32} {v:>6,}")
print(f"  {'合计':<32} {sum(c.values()):>6,}")

print()
print("=== 品种名质量分级 ===")
qi = cs[0].index("name_quality")
q = Counter(x[qi] for x in cs[1:])
for k in ["good", "caveat", "code", "unusable"]:
    print(f"  {k:<12} {q[k]:>7,}  {100.0*q[k]/(len(cs)-1):>5.1f}%")
print(f"  {'可用合计':<12} {q['good']+q['caveat']+q['code']:>7,}")

print()
print("=== 发生归并的品种数 ===")
mi = ca[0].index("n_spellings")
print(f"  n_spellings > 1 的品种 = {sum(1 for x in ca[1:] if x[mi].isdigit() and int(x[mi]) > 1):,}")

print()
print("=== 各品种 run 数分布 ===")
ni = ca[0].index("n_runs")
d = Counter()
for x in ca[1:]:
    n = int(x[ni]) if x[ni].isdigit() else 0
    d["1"] += n == 1
    d["2-3"] += 2 <= n <= 3
    d["4-9"] += 4 <= n <= 9
    d[">=10"] += n >= 10
for k in ["1", "2-3", "4-9", ">=10"]:
    print(f"  {k:<8} {d[k]:>6,}  {100.0*d[k]/(len(ca)-1):>5.1f}%")
print(f"  有 ≥2 run 的品种 = {len(ca)-1-d['1']:,}")
