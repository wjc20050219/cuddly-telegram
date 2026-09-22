#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_ncbi_esummary.py —— 把 NCBI SRA esummary JSON 解析为 run 级 TSV

TASK-008 辅助工具。

v2 修正：v1 误以为 expxml 是扁平属性串，实际是完整 XML 块，形如：
    <Summary><Title>...</Title><Platform instrument_model="...">...</Platform>
    <Statistics total_runs="..." total_bases="..."/></Summary>
    <Submitter acc="..."/><Experiment acc="..."/><Study acc="..." name="..."/>
    <Organism taxid="..." ScientificName="..."/><Sample acc="..."/>
    <Instrument .../><Library_descriptor>...<LIBRARY_STRATEGY>WGS</...>
    <Bioproject>...</Bioproject><Biosample>...</Biosample>
v2 按真实结构用正则逐字段提取。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

SEARCH = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/search")
SRC = SEARCH / "ncbi_sra_esummary.json"
DST = SEARCH / "ncbi_sra_runs.tsv"
GS = 375_000_000  # IRGSP-1.0 单倍体基因组大小


def g(pattern: str, text: str, group: int = 1, default: str = "") -> str:
    m = re.search(pattern, text)
    return m.group(group) if m else default


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 找不到输入：{SRC}", file=sys.stderr)
        return 1
    data = json.loads(SRC.read_text(encoding="utf-8", errors="replace"))
    result = data.get("result", {})
    uids = result.get("uids", [])
    print(f"esummary 记录数：{len(uids)}")

    rows = []
    for uid in uids:
        rec = result.get(str(uid))
        if not isinstance(rec, dict):
            continue
        x = rec.get("expxml") or ""
        runs = rec.get("runs") or ""

        total_bases = int(g(r'<Statistics[^>]*total_bases="(\d+)"', x, default="0") or 0)

        platform = g(r'<Platform instrument_model="[^"]*">([^<]*)</Platform>', x)
        instrument = g(r'<Platform instrument_model="([^"]*)"', x)
        if not instrument:
            instrument = g(r'<Instrument [^=]+="([^"]*)"', x)

        layout = g(r'<LIBRARY_LAYOUT>\s*<([A-Z]+)/>', x)

        run_accs = re.findall(r'<Run acc="([^"]+)"', runs)

        rows.append({
            "uid": uid,
            "run": ";".join(run_accs[:5]),
            "experiment": g(r'<Experiment acc="([^"]*)"', x),
            "study": g(r'<Study acc="([^"]*)"', x),
            "study_name": g(r'<Study acc="[^"]*"\s+name="([^"]*)"', x),
            "sample": g(r'<Sample acc="([^"]*)"', x),
            "bioproject": g(r'<Bioproject>([^<]*)</Bioproject>', x),
            "biosample": g(r'<Biosample>([^<]*)</Biosample>', x),
            "submitter": g(r'<Submitter acc="([^"]*)"', x),
            "library_strategy": g(r'<LIBRARY_STRATEGY>([^<]*)</LIBRARY_STRATEGY>', x),
            "library_source": g(r'<LIBRARY_SOURCE>([^<]*)</LIBRARY_SOURCE>', x),
            "layout": layout,
            "platform": platform,
            "instrument": instrument,
            "total_bases": total_bases,
            "est_depth": round(total_bases / GS, 2) if total_bases else 0.0,
            "organism": g(r'<Organism[^>]*ScientificName="([^"]*)"', x),
            "title": g(r'<Title>([^<]*)</Title>', x),
        })

    if not rows:
        print("[WARN] 未解析出记录", file=sys.stderr)
        return 1

    cols = list(rows[0].keys())
    with DST.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
    print(f"已写出：{DST}（{len(rows)} 行）\n")

    # ---- 概况 ----
    def dist(key: str, label: str) -> None:
        c = Counter(r[key] or "(空)" for r in rows)
        print(f"--- {label} ---")
        for k, v in c.most_common(8):
            print(f"  {str(k):<34} {v}")
        print()

    dist("library_strategy", "文库策略")
    dist("library_source", "文库来源")
    dist("layout", "文库布局")
    dist("platform", "测序平台")

    # 关键：按提交库统计（accession 前缀）
    pref = Counter()
    for r in rows:
        acc = r["run"] or r["experiment"]
        pref[acc[:3] if acc else "(无)"] += 1
    print("--- ★ 按提交库统计（accession 前缀）---")
    print("  SRR/SRX/SRP = NCBI SRA | ERR/ERX/ERP = ENA | DRR/DRX/DRP = DDBJ DRA")
    for k, v in pref.most_common(10):
        print(f"  {k:<34} {v}")
    print()

    print("--- 深度分布 ---")
    bins = Counter()
    for r in rows:
        d = r["est_depth"]
        bins["<1x" if d < 1 else "1-5x" if d < 5 else "5-10x" if d < 10
             else "10-20x" if d < 20 else "20-30x" if d < 30 else ">=30x"] += 1
    for k in ["<1x", "1-5x", "5-10x", "10-20x", "20-30x", ">=30x"]:
        print(f"  {k:<34} {bins[k]}")

    print("\n--- 样例（前 6 条）---")
    for r in rows[:6]:
        print(f"  {r['run']:<14} {r['experiment']:<14} {r['layout']:<8} "
              f"{r['est_depth']:>7}x  {r['title'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
