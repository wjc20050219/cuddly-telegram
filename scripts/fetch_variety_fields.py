#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_variety_fields.py —— 测试 ENA Portal read_run 的品种名字段（TASK-011 取数方案）

背景：
  ENA 有两条取品种名的路：
    路径 A：Portal API 的 read_run 结果直接取 `cultivar` / `variety` 字段（1 次请求拿全部）
    路径 B：批量拉样本 XML，解析 `subspecific genetic lineage name`（50 次请求）
  本脚本先验证路径 A 的字段是否真有值（有字段 ≠ 有值），再决定主用哪条。
"""
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

OUT = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/search")
API = "https://www.ebi.ac.uk/ena/portal/api/search"


def fetch(fields: str, query: str, limit: int = 2000) -> tuple[str, str]:
    params = {
        "result": "read_run",
        "query": query,
        "fields": fields,
        "format": "tsv",
        "limit": str(limit),
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read().decode("utf-8", errors="replace"), url


def main() -> int:
    print("=" * 74)
    print("测试：ENA Portal read_run 能否直接提供品种名")
    print("=" * 74)

    fields = ",".join([
        "run_accession", "sample_accession", "sample_title", "sample_alias",
        "scientific_name", "cultivar", "variety", "ecotype", "strain",
        "country", "instrument_platform", "library_layout", "base_count",
    ])
    query = 'tax_eq(4530) AND library_strategy="WGS"'

    print(f"查询：{query}")
    print(f"字段：{fields}\n")
    try:
        text, url = fetch(fields, query, limit=2000)
    except Exception as exc:
        print(f"[ERROR] 请求失败：{exc}", file=sys.stderr)
        return 1

    lines = text.rstrip("\n").split("\n")
    if len(lines) < 2:
        print("[ERROR] 响应无数据行", file=sys.stderr)
        print(text[:500], file=sys.stderr)
        return 1

    hdr = lines[0].split("\t")
    rows = [l.split("\t") for l in lines[1:]]
    print(f"返回 {len(rows)} 行，{len(hdr)} 列")
    print(f"表头：{hdr}\n")

    def fill(col: str) -> tuple[int, float]:
        if col not in hdr:
            return 0, 0.0
        i = hdr.index(col)
        n = sum(1 for r in rows if i < len(r) and r[i].strip()
                and r[i].strip().lower() not in ("nan", "none", "not applicable",
                                                 "not collected", "missing", ""))
        return n, 100.0 * n / len(rows) if rows else 0.0

    print("--- 字段填写率（关键！有字段 ≠ 有值）---")
    for col in ["cultivar", "variety", "ecotype", "strain",
                "sample_title", "sample_alias", "country"]:
        n, pct = fill(col)
        bar = "█" * int(pct / 3)
        print(f"  {col:<16} {n:>5}/{len(rows)}  {pct:>5.1f}%  {bar}")

    print("\n--- cultivar 字段样例（前 15 个非空）---")
    if "cultivar" in hdr:
        i = hdr.index("cultivar")
        j = hdr.index("sample_accession") if "sample_accession" in hdr else 0
        shown = 0
        for r in rows:
            if i < len(r) and r[i].strip() and r[i].strip().lower() not in ("nan", "none"):
                print(f"    {r[j]:<20} cultivar={r[i][:40]}")
                shown += 1
                if shown >= 15:
                    break
        if shown == 0:
            print("    （无）")

    print("\n--- variety 字段样例（前 15 个非空）---")
    if "variety" in hdr:
        i = hdr.index("variety")
        j = hdr.index("sample_accession") if "sample_accession" in hdr else 0
        shown = 0
        for r in rows:
            if i < len(r) and r[i].strip() and r[i].strip().lower() not in ("nan", "none"):
                print(f"    {r[j]:<20} variety={r[i][:40]}")
                shown += 1
                if shown >= 15:
                    break
        if shown == 0:
            print("    （无）")

    print("\n--- 结论判定 ---")
    nc, pc = fill("cultivar")
    nv, pv = fill("variety")
    if pc + pv >= 20:
        print(f"  ✅ 路径 A 可行：cultivar {pc:.1f}% + variety {pv:.1f}% 有值")
        print("     -> 用 Portal API 一次取全量，无需拉 XML")
    elif pc + pv > 0:
        print(f"  ⚠️ 路径 A 部分可行（{pc:.1f}% + {pv:.1f}%），覆盖率不足")
        print("     -> 建议 A+B 混合：先用 A 取有值的，其余用批量 XML 补齐")
    else:
        print("  ❌ 路径 A 不可行（字段存在但无值）")
        print("     -> 必须用路径 B：批量 XML 解析 subspecific genetic lineage name")

    # 保存原始结果供后续使用
    p = OUT / "probe_variety_fields.tsv"
    p.write_text(text, encoding="utf-8")
    print(f"\n原始结果已存：{p}（{len(rows)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
