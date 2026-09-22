#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_fastq_links.py —— 精确统计 ENA ≥5× 清单的 FASTQ 直链可用性"""
import csv
from pathlib import Path

P = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/search/ena_rice_wgs_deep_runs.tsv")
with P.open(encoding="utf-8", errors="replace", newline="") as fh:
    rows = list(csv.reader(fh, delimiter="\t"))

hdr = rows[0]
fi = hdr.index("fastq_ftp")
bi = hdr.index("fastq_bytes")
data = rows[1:]

empty_ftp = [r for r in data if not r[fi].strip() or r[fi].strip() in ("nan", "None")]
empty_bytes = [r for r in data if not r[bi].strip() or r[bi].strip() in ("nan", "None")]
both = [r for r in data if (r[fi].strip() and r[bi].strip())]

print(f"总行数：{len(data)}")
print(f"fastq_ftp 为空：{len(empty_ftp)}")
print(f"fastq_bytes 为空：{len(empty_bytes)}")
print(f"两者都非空：{len(both)}")

if empty_ftp:
    print("\nfastq_ftp 为空的样例：")
    for r in empty_ftp[:5]:
        print(f"  {r[0]}  ftp={r[fi]!r}  bytes={r[bi]!r}")
if empty_bytes:
    print("\nfastq_bytes 为空的样例：")
    for r in empty_bytes[:5]:
        print(f"  {r[0]}  ftp={r[fi][:60]!r}  bytes={r[bi]!r}")

# 抽查第一条的直链格式
r0 = data[0]
print(f"\n样例直链（{r0[0]}）：\n  {r0[fi]}")
print(f"  字节数：{r0[bi]}")
