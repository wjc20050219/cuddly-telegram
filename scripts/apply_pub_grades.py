#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_pub_grades.py —— 把可信度分级写回主表与 panel 来源表

前序脚本产出的 scale_check 分级，需要回写到：
  1. candidate_samples.tsv 的 publication 列（带 [LINKED]/[MATCH]/[PLAUSIBLE]/[WEAK]/[?] 前缀）
  2. panel_sources.tsv（panel 样本的来源文献 + 可信度）
"""
import csv
from pathlib import Path

CAND = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = CAND / "candidate_samples.tsv"
PUB = CAND / "study_publications.tsv"
PANELS = [("pilot_panel.tsv", "pilot"),
          ("independent_test_panel.tsv", "independent_test")]
PANEL_OUT = CAND / "panel_sources.tsv"

# 分级 -> 主表前缀
PREFIX = {
    "match": "[MATCH]",          # run/样本 ≈ 1:1，高度可信
    "plausible": "[PLAUSIBLE]",  # 每样本多次测序，合理
    "runs_fewer": "[PARTIAL]",   # 本表 run 少于论文自述，可能只是一部分数据
    "mismatch": "[WEAK]",        # ★ 差距过大，疑为误匹配
    "unknown": "[?]",            # 摘要未给样本量
    "accession_linked": "[LINKED]",  # 结构化链接（本次为 0）
}


def rows(p: Path) -> list[list[str]]:
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.reader(fh, delimiter="\t"))


def main() -> int:
    # ---- 读文献表 ----
    pr = rows(PUB)
    ph = pr[0]
    idx = {c: ph.index(c) for c in
           ["study_accession", "n_runs", "evidence", "pmid", "doi", "year",
            "journal", "title", "reported_n", "scale_check", "scale_note"]}
    pubs: dict[str, dict[str, str]] = {}
    for r in pr[1:]:
        r += [""] * (len(ph) - len(r))
        d = {c: r[i] for c, i in idx.items()}
        if d["evidence"] != "none":
            pubs[d["study_accession"]] = d

    # ---- 1. 回写主表 ----
    sr = rows(SRC)
    sh = sr[0]
    pi, pubi = sh.index("BioProject"), sh.index("publication")
    n = 0
    for r in sr[1:]:
        d = pubs.get(r[pi])
        if not d:
            r[pubi] = ""
            continue
        pre = PREFIX.get(d["scale_check"] or d["evidence"], "[?]")
        parts = [pre]
        if d["doi"]:
            parts.append(f"doi:{d['doi']}")
        if d["pmid"]:
            parts.append(f"PMID:{d['pmid']}")
        if d["year"]:
            parts.append(d["year"])
        if d["title"]:
            parts.append(d["title"][:100])
        r[pubi] = " | ".join(parts)
        n += 1

    with SRC.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(sh)
        w.writerows(sr)
    print(f"主表 publication 已回写：{n:,} / {len(sr)-1:,} 行"
          f"（{100.0*n/(len(sr)-1):.1f}%）")

    from collections import Counter
    c = Counter(r[pubi].split(" | ")[0] for r in sr[1:] if r[pubi])
    print("  分级分布：")
    for k, v in c.most_common():
        print(f"    {k:<14} {v:>7,} 行")

    # ---- 2. 重建 panel 来源表 ----
    out = []
    for panel, tag in PANELS:
        dr = rows(CAND / panel)
        h = dr[0]
        ci, di, si = (h.index(x) for x in
                      ("canonical_name", "estimated_depth", "sample_id"))
        bpi = h.index("BioProject")
        for r in dr[1:]:
            d = pubs.get(r[bpi], {})
            out.append({
                "panel": tag, "sample_id": r[si], "canonical_name": r[ci],
                "BioProject": r[bpi], "depth": r[di],
                "confidence": d.get("scale_check", "") or ("none" if not d else "unknown"),
                "pmid": d.get("pmid", ""), "doi": d.get("doi", ""),
                "year": d.get("year", ""), "journal": d.get("journal", ""),
                "title": d.get("title", ""),
                "reported_n": d.get("reported_n", ""),
                "scale_note": d.get("scale_note", ""),
            })

    cols = list(out[0].keys())
    with PANEL_OUT.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in out:
            fh.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
    print(f"\n已写出：{PANEL_OUT}（{len(out)} 行）")

    cc = Counter(r["confidence"] for r in out)
    print("  Panel 来源可信度：")
    for k, v in cc.most_common():
        print(f"    {k:<14} {v:>3} 份样本")

    print("\n--- ★ Panel 中可信度最高的来源（match/plausible）---")
    seen = set()
    for r in out:
        if r["confidence"] in ("match", "plausible") and r["BioProject"] not in seen:
            seen.add(r["BioProject"])
            print(f"  {r['BioProject']:<16} {r['canonical_name'][:22]:<24} [{r['confidence']}]")
            print(f"      [{r['year']}] {r['title'][:90]}")
            print(f"      PMID {r['pmid']}  {r['scale_note']}")
    if not seen:
        print("  （无）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
