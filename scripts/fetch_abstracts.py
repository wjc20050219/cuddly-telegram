#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_abstracts.py —— 拉取关键文献摘要（原编号 TASK-011 支撑）

目的：写文献综述前，必须看清原文说了什么，不能凭标题猜。
      本脚本用 PubMed efetch 取指定 PMID 的结构化摘要。

产出：data/metadata/literature/key_abstracts.txt
"""
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUTDIR = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/literature")
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 经人工筛选、与本项目**直接相关**的关键文献
KEYS: list[tuple[str, str]] = [
    ("34250668", "超低深度 WGS 用于群体基因组学（综述/指南）"),
    ("35251117", "超低深度 WGS 替代基因分型芯片（GWAS）"),
    ("38216889", "低通量测序 + 填补的单倍型准确性警告"),
    ("41126791", "低覆盖度 skim 测序 + 填补流程（植物/基因组选择）"),
    ("32101292", "NARO 世界水稻核心种质 WGS（数据资源）"),
    ("30992303", "3000 水稻基因组的结构变异"),
    ("33367255", "3004 份水稻微核心种质设计"),
    ("27940610", "RPAN 水稻泛基因组浏览器"),
    ("35396275", "111 个水稻基因组长读组装（泛基因组更大）"),
    ("33543400", "靶向 + 超低通量 WGS 检测拷贝数变异"),
]


def get(url: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> int:
    print("=" * 78)
    print("拉取关键文献摘要")
    print("=" * 78)
    ids = ",".join(p for p, _ in KEYS)
    params = {"db": "pubmed", "id": ids, "retmode": "xml"}
    try:
        xml_text = get(f"{EUT}/efetch.fcgi?" + urllib.parse.urlencode(params), timeout=120)
    except Exception as exc:
        print(f"[ERROR] efetch 失败：{exc}", file=sys.stderr)
        return 1

    root = ET.fromstring(xml_text)
    parsed: dict[str, dict] = {}
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID") or ""
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        journal = art.findtext(".//Journal/ISOAbbreviation") or art.findtext(".//Journal/Title") or ""
        year = (art.findtext(".//JournalIssue/PubDate/Year")
                or art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4]
        # 摘要可能分多段
        abs_parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            txt = "".join(ab.itertext())
            abs_parts.append(f"{label}: {txt}" if label else txt)
        abstract = " ".join(abs_parts)
        # ★ DOI 必须限定在 PubmedData/ArticleIdList 内。
        #   用 .//ArticleId 会搜到参考文献列表里的 ArticleId，
        #   抓到的是**被引文献**的 DOI（曾因此产出系统性错误的 DOI）。
        doi = ""
        pmdata = art.find("PubmedData/ArticleIdList")
        if pmdata is not None:
            for aid in pmdata.findall("ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = (aid.text or "").strip()
                    break
        # ELocationID 是兜底来源
        if not doi:
            for el in art.findall(".//Article/ELocationID"):
                if el.get("EIdType") == "doi":
                    doi = (el.text or "").strip()
                    break
        parsed[pmid] = {"title": title, "journal": journal, "year": year,
                        "doi": doi, "abstract": abstract}

    lines = []
    def w(s: str = "") -> None:
        print(s)
        lines.append(s)

    w("=" * 78)
    w("关键文献摘要（按与本项目的相关度排序）")
    w("=" * 78)
    miss = 0
    for pmid, why in KEYS:
        r = parsed.get(pmid)
        if not r:
            w(f"\n[未取到 PMID {pmid}]")
            miss += 1
            continue
        w()
        w("─" * 78)
        w(f"PMID {pmid}   [{r['year']}] {r['journal']}")
        w(f"为什么重要：{why}")
        w(f"标题：{r['title']}")
        if r["doi"]:
            w(f"DOI：{r['doi']}")
        w()
        ab = r["abstract"] or "（无摘要）"
        # 按句切分换行，便于阅读
        import re
        for sent in re.split(r"(?<=[.;])\s+", ab):
            if sent.strip():
                w(f"  {sent.strip()}")

    w()
    w("=" * 78)
    w(f"共 {len(KEYS)} 篇，取到 {len(KEYS)-miss} 篇")

    dst = OUTDIR / "key_abstracts.txt"
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n已写出：{dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
