#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
literature_search.py —— 原编号 TASK-011：检索公开研究论文

任务书要求的检索方向：
  rice resequencing / rice diversity / rice cultivar identification /
  rice population genomics / rice pan-genome / rice structural variation

方法：直接查 PubMed E-utilities（esearch + esummary），
      取得**可引用的确切信息**：PMID / 标题 / 作者 / 期刊 / 年份 / DOI。
      不用网页抓取——那样拿不到稳定标识符，也无法追溯。

产出：data/metadata/literature/literature_hits.tsv
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUTDIR = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/literature")
OUTDIR.mkdir(parents=True, exist_ok=True)
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 任务书指定方向 -> PubMed 检索式
TOPICS: list[tuple[str, str]] = [
    ("rice_resequencing",
     '("Oryza sativa"[Title/Abstract] OR rice[Title/Abstract]) '
     'AND resequencing[Title/Abstract] AND (diversity[Title/Abstract] '
     'OR variation[Title/Abstract] OR population[Title/Abstract])'),
    ("rice_cultivar_identification",
     '(rice[Title/Abstract] OR "Oryza sativa"[Title/Abstract]) '
     'AND (cultivar[Title/Abstract] OR variety[Title/Abstract] '
     'OR varietal[Title/Abstract]) AND (identification[Title/Abstract] '
     'OR authentication[Title/Abstract] OR discrimination[Title/Abstract])'),
    ("rice_fingerprint",
     '(rice[Title/Abstract] OR "Oryza sativa"[Title/Abstract]) '
     'AND (fingerprint*[Title/Abstract] OR barcode*[Title/Abstract] '
     'OR "molecular marker*"[Title/Abstract])'),
    ("rice_pangenome",
     '(rice[Title/Abstract] OR "Oryza"[Title/Abstract]) '
     'AND (pan-genome[Title/Abstract] OR pangenome[Title/Abstract] '
     'OR "pan genome"[Title/Abstract] OR "graph genome"[Title/Abstract])'),
    ("rice_structural_variation",
     '(rice[Title/Abstract] OR "Oryza sativa"[Title/Abstract]) '
     'AND ("structural variation*"[Title/Abstract] '
     'OR "presence/absence"[Title/Abstract] OR PAV[Title/Abstract])'),
    ("low_coverage_genotyping",
     '(low-coverage[Title/Abstract] OR "low coverage"[Title/Abstract] '
     'OR "low-pass"[Title/Abstract] OR "ultra-low"[Title/Abstract] '
     'OR "skim sequencing"[Title/Abstract]) '
     'AND (sequencing[Title/Abstract] OR genotyping[Title/Abstract])'),
    ("low_coverage_rice",
     '(rice[Title/Abstract] OR "Oryza sativa"[Title/Abstract]) '
     'AND (low-coverage[Title/Abstract] OR "low coverage"[Title/Abstract] '
     'OR "low-depth"[Title/Abstract] OR "low depth"[Title/Abstract])'),
    ("rice_3k_genomes",
     '"3,010"[All Fields] OR "3000 rice genomes"[All Fields] '
     'OR "3K rice genomes"[All Fields] OR "3K RGP"[All Fields]'),
]


def get(url: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def esearch(term: str, retmax: int = 25) -> list[str]:
    params = {"db": "pubmed", "term": term, "retmax": str(retmax),
              "retmode": "json", "sort": "relevance"}
    url = f"{EUT}/esearch.fcgi?" + urllib.parse.urlencode(params)
    try:
        d = json.loads(get(url))
        return d.get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        print(f"    [esearch 失败] {exc}", file=sys.stderr)
        return []


def esummary(ids: list[str]) -> dict:
    if not ids:
        return {}
    params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
    url = f"{EUT}/esummary.fcgi?" + urllib.parse.urlencode(params)
    try:
        return json.loads(get(url)).get("result", {})
    except Exception as exc:
        print(f"    [esummary 失败] {exc}", file=sys.stderr)
        return {}


def main() -> int:
    print("=" * 78)
    print("原编号 TASK-011：检索公开研究论文（PubMed E-utilities）")
    print("=" * 78)
    print(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"检索方向：{len(TOPICS)} 个\n")

    rows: list[dict[str, str]] = []
    for name, term in TOPICS:
        n = 0
        ids = esearch(term, retmax=25)
        time.sleep(0.5)
        res = esummary(ids)
        time.sleep(0.5)
        for pmid in ids:
            rec = res.get(pmid)
            if not isinstance(rec, dict):
                continue
            authors = rec.get("authors", [])
            first = authors[0]["name"] if authors else ""
            doi = ""
            for aid in rec.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value", "")
                    break
            rows.append({
                "topic": name,
                "pmid": pmid,
                "year": (rec.get("pubdate", "") or "")[:4],
                "journal": rec.get("source", ""),
                "first_author": first,
                "n_authors": str(len(authors)),
                "title": (rec.get("title", "") or "").rstrip("."),
                "doi": doi,
            })
            n += 1
        print(f"  {name:<32} 检索到 {len(ids):>3} 条，解析 {n:>3} 条")

    print(f"\n合计 {len(rows)} 条记录\n")

    cols = ["topic", "pmid", "year", "journal", "first_author",
            "n_authors", "title", "doi"]
    dst = OUTDIR / "literature_hits.tsv"
    with dst.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
    print(f"已写出：{dst}（{len(rows)} 行）\n")

    # ---- 高影响力期刊的命中 ----
    KEY = {"nature", "science", "cell", "nat genet", "nature genetics",
           "nat commun", "nature communications", "genome biol",
           "genome biology", "genome res", "genome research",
           "plant cell", "mol plant", "molecular plant",
           "proc natl acad sci u s a", "nat plants", "cell res"}
    print("--- 顶级期刊命中（可作为核心引用）---")
    seen = set()
    hit = 0
    for r in sorted(rows, key=lambda x: (x["journal"].lower(), x["year"])):
        j = r["journal"].lower()
        if j in KEY and r["pmid"] not in seen:
            seen.add(r["pmid"])
            print(f"  [{r['year']}] {r['journal']}")
            print(f"        {r['title'][:96]}")
            print(f"        {r['first_author']} et al.  PMID {r['pmid']}"
                  + (f"  doi:{r['doi']}" if r["doi"] else ""))
            hit += 1
    if hit == 0:
        print("  （无）")

    print("\n--- 各方向命中数 ---")
    from collections import Counter
    c = Counter(r["topic"] for r in rows)
    for k, v in c.most_common():
        print(f"  {k:<32} {v:>4}")

    print("\n--- 年份分布 ---")
    y = Counter(r["year"] for r in rows if r["year"].isdigit())
    for k in sorted(y, reverse=True)[:12]:
        print(f"  {k}  {y[k]:>4}  {'█' * y[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
