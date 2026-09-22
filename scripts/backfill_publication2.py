#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_publication2.py —— 回填 publication 字段（Europe PMC 方案）

为什么不走 ENA：实测 ENA 的 result=study 共 29 个字段，**没有任何文献字段**。

为什么不全查：实测 6 个真实项目里只有 2 个能反查到文献。全量 2,052 个项目
按 1.5s/次 需约 50 分钟，收益有限。故只查 **run 数 ≥ 20** 的项目。

★ 证据分级（关键）：
  accession_linked —— 命中文献的交叉引用里**确实含该 BioProject 编号**（结构化链接，可信）
  fulltext_mention —— 仅全文出现该编号（可能是提及，未必是配套论文，**须人工核验**）
  两者严格分开标注，不混为一谈。
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

CAND = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = CAND / "candidate_samples.tsv"
OUT = CAND / "study_publications.tsv"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MIN_RUNS = 20


def get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def search(acc: str) -> tuple[str, dict | None]:
    """返回 (证据类型, 文献记录)"""
    params = {"query": f'"{acc}"', "format": "json",
              "pageSize": "5", "resultType": "core"}
    try:
        d = json.loads(get(EPMC + "?" + urllib.parse.urlencode(params)))
    except Exception:
        return "error", None
    res = d.get("resultList", {}).get("result", [])
    if not res:
        return "none", None

    # 先找结构化链接：交叉引用里含该编号
    for r in res:
        blob = json.dumps(r.get("dbCrossReferenceList", {})) + \
               json.dumps(r.get("accessionIdList", ""))
        if acc in blob:
            return "accession_linked", r
    # 退而求其次：全文提及
    return "fulltext_mention", res[0]


def main() -> int:
    print("=" * 74)
    print("回填 publication 字段（Europe PMC）")
    print("=" * 74)

    with SRC.open(encoding="utf-8", errors="replace") as fh:
        rdr = csv.reader(fh, delimiter="\t")
        hdr = next(rdr)
        rows = [r + [""] * (len(hdr) - len(r)) for r in rdr]
    pi = hdr.index("BioProject")
    pub_i = hdr.index("publication")
    proj = Counter(r[pi] for r in rows if r[pi])

    targets = [p for p, c in proj.most_common() if c >= MIN_RUNS]
    print(f"BioProject 总数 {len(proj):,}；"
          f"run 数 ≥{MIN_RUNS} 的目标 {len(targets):,} 个")
    print(f"预计耗时约 {len(targets)*1.5/60:.0f} 分钟\n")

    results: dict[str, dict[str, str]] = {}
    t0 = time.time()
    for i, acc in enumerate(targets):
        ev, rec = search(acc)
        d = {"study_accession": acc, "n_runs": str(proj[acc]),
             "evidence": ev, "pmid": "", "doi": "", "year": "",
             "journal": "", "title": ""}
        if rec:
            d.update({
                "pmid": str(rec.get("pmid", "") or ""),
                "doi": str(rec.get("doi", "") or ""),
                "year": str(rec.get("pubYear", "") or ""),
                "journal": str(rec.get("journalTitle", "") or "")[:60],
                "title": str(rec.get("title", "") or "")[:160],
            })
        results[acc] = d
        if (i + 1) % 25 == 0 or i == len(targets) - 1:
            el = time.time() - t0
            n_hit = sum(1 for v in results.values() if v["evidence"] != "none")
            print(f"  {i+1:>4}/{len(targets)}  命中 {n_hit:>3}  "
                  f"用时 {el:>5.0f}s  预计剩余 {(len(targets)-i-1)*el/(i+1):>4.0f}s")
        time.sleep(0.4)

    print()
    cols = ["study_accession", "n_runs", "evidence", "pmid", "doi",
            "year", "journal", "title"]
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for p in targets:
            fh.write("\t".join(results[p].get(c, "") for c in cols) + "\n")
    print(f"已写出：{OUT}")

    # ---- 统计 ----
    ev = Counter(v["evidence"] for v in results.values())
    print("\n--- 证据分级统计 ---")
    for k in ["accession_linked", "fulltext_mention", "none", "error"]:
        n = ev.get(k, 0)
        print(f"  {k:<20} {n:>5,}  {100.0*n/max(1,len(targets)):>5.1f}%")

    linked = {p: v for p, v in results.items() if v["evidence"] == "accession_linked"}
    if linked:
        print(f"\n--- ★ 结构化链接（可信）Top 15 ---")
        for p, v in sorted(linked.items(), key=lambda x: -int(x[1]["n_runs"]))[:15]:
            print(f"  {p:<16} {v['n_runs']:>6} run  [{v['year']}] PMID {v['pmid']}")
            print(f"       {v['title'][:104]}")

    # ---- 回填 ----
    n_filled = 0
    for r in rows:
        v = results.get(r[pi])
        if v and v["evidence"] != "none":
            tag = "LINKED" if v["evidence"] == "accession_linked" else "FULLTEXT?"
            parts = [f"[{tag}]"]
            if v["doi"]:
                parts.append(f"doi:{v['doi']}")
            if v["pmid"]:
                parts.append(f"PMID:{v['pmid']}")
            if v["year"]:
                parts.append(v["year"])
            if v["title"]:
                parts.append(v["title"][:110])
            r[pub_i] = " | ".join(parts)
            n_filled += 1

    with SRC.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(hdr)
        w.writerows(rows)
    print(f"\n★ 回填：{n_filled:,} / {len(rows):,} 行"
          f"（{100.0*n_filled/len(rows):.1f}%）")
    print(f"  说明：其中仅 {sum(1 for r in rows if r[pub_i].startswith('[LINKED]')):,} 行"
          f"是结构化链接，其余 {sum(1 for r in rows if r[pub_i].startswith('[FULLTEXT?]')):,} 行"
          f"标记为 FULLTEXT?（须人工核验）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
