#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
panel_sources.py —— 生成两个 Panel 的来源文献表

用途：论文的样本表需要说明每份样本来自哪项研究。
      本脚本把 panel 样本的 BioProject 与反查到的候选文献对齐，
      并**标注证据强度**，供人工核验。

产出：data/metadata/candidates/panel_sources.tsv
"""
import csv
from collections import Counter
from pathlib import Path

CAND = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")


def rows(p: Path) -> list[list[str]]:
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.reader(fh, delimiter="\t"))


def main() -> int:
    # BioProject -> 候选文献
    pubs: dict[str, dict[str, str]] = {}
    for r in rows(CAND / "study_publications.tsv")[1:]:
        if len(r) >= 8 and r[2] != "none":
            pubs[r[0]] = {"evidence": r[2], "pmid": r[3], "doi": r[4],
                          "year": r[5], "journal": r[6], "title": r[7]}

    out = []
    for panel, tag in (("pilot_panel.tsv", "pilot"),
                       ("independent_test_panel.tsv", "independent_test")):
        data = rows(CAND / panel)
        h = data[0]
        pi, ci, di, si = (h.index(c) for c in
                          ("BioProject", "canonical_name", "estimated_depth", "sample_id"))
        for r in data[1:]:
            p = r[pi]
            pub = pubs.get(p, {})
            out.append({
                "panel": tag,
                "sample_id": r[si],
                "canonical_name": r[ci],
                "BioProject": p,
                "depth": r[di],
                "has_publication": "yes" if pub else "no",
                "evidence": pub.get("evidence", ""),
                "pmid": pub.get("pmid", ""),
                "doi": pub.get("doi", ""),
                "year": pub.get("year", ""),
                "journal": pub.get("journal", ""),
                "title": pub.get("title", ""),
            })

    dst = CAND / "panel_sources.tsv"
    cols = list(out[0].keys())
    with dst.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in out:
            fh.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")

    print("=" * 74)
    print("Panel 来源文献表")
    print("=" * 74)
    print(f"已写出：{dst}（{len(out)} 行）\n")

    n_yes = sum(1 for r in out if r["has_publication"] == "yes")
    print(f"有候选文献的样本：{n_yes} / {len(out)}"
          f"（{100.0*n_yes/len(out):.1f}%）")
    ev = Counter(r["evidence"] for r in out if r["evidence"])
    print(f"证据类型：{dict(ev)}")
    print()

    print("--- 按 BioProject 汇总（panel 内）---")
    by_proj: dict[str, list[dict]] = {}
    for r in out:
        by_proj.setdefault(r["BioProject"], []).append(r)
    for p, rs in sorted(by_proj.items(), key=lambda x: -len(x[1])):
        pub = pubs.get(p)
        mark = "✓" if pub else "—"
        print(f"\n  {mark} {p:<16} {len(rs):>2} 份样本  "
              f"({', '.join(x['canonical_name'][:18] for x in rs[:3])}"
              f"{'…' if len(rs) > 3 else ''})")
        if pub:
            print(f"      [{pub['year']}] {pub['journal']}")
            print(f"      {pub['title'][:100]}")
            print(f"      PMID {pub['pmid']}  doi:{pub['doi']}"
                  f"   证据={pub['evidence']}")
        else:
            print("      （未反查到候选文献）")

    print()
    print("=" * 74)
    print("★ 证据强度说明")
    print("=" * 74)
    print("  本表所有条目均为 fulltext_mention —— 即该 BioProject 编号")
    print("  **在文献全文中出现**，但 Europe PMC 中**没有**结构化的数据-文献链接")
    print("  （96 个受查项目中 accession_linked 命中为 0）。")
    print()
    print("  因此这些匹配**规模、主题、期刊均吻合，但未经结构化确认**，")
    print("  正式引用前必须逐篇核对论文的 Data Availability 声明。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
