#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
literature_search2.py —— 原编号 TASK-011 第二轮：精确标题级检索

第一轮用 Title/Abstract 宽检索，噪声大：
  "rice cultivar identification" 返回大量基因家族鉴定论文，
  "rice fingerprint" 返回稻米营养指纹论文——都跑偏了。

第二轮改为**限定标题字段 + 更贴近本项目的问题表述**，
并专门补检几个已知必引的方向（3K RGP 原文、低深度基因分型、种子真实性）。

产出：data/metadata/literature/literature_targeted.tsv
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

OUTDIR = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/literature")
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

TARGETED: list[tuple[str, str]] = [
    # 3K RGP 原始论文——本项目最重要的数据来源文献
    ("3k_rgp_paper",
     '"3,010 diverse accessions"[All Fields] OR "3010 rice"[All Fields] '
     'OR "3000 rice genomes"[All Fields] OR "3K rice genomes"[All Fields]'),
    # 品种/栽培种鉴定（限标题，避免基因家族"鉴定"论文）
    ("variety_id_title",
     '(rice[Title] OR "Oryza sativa"[Title]) '
     'AND (variety[Title] OR varieties[Title] OR cultivar[Title] OR cultivars[Title]) '
     'AND (identification[Title] OR discrimination[Title] '
     'OR authentication[Title] OR purity[Title] OR distinctness[Title])'),
    # 低深度/撇取测序（限标题）
    ("lowpass_title",
     '(skim[Title] OR skimming[Title] OR "low-pass"[Title] '
     'OR "low coverage"[Title] OR "low-coverage"[Title] '
     'OR "low depth"[Title] OR "low-depth"[Title] OR "ultra-low"[Title]) '
     'AND (sequencing[Title] OR genotyping[Title] OR genome[Title])'),
    # 水稻核心种质 / 种质资源重测序
    ("rice_germplasm",
     'rice[Title] AND ("core collection"[Title] OR germplasm[Title] '
     'OR "genetic resources"[Title]) '
     'AND (resequencing[Title] OR sequencing[Title] OR genome[Title])'),
    # 种子真实性与掺假检测
    ("seed_purity",
     '(seed[Title] OR grain[Title] OR rice[Title]) '
     'AND (purity[Title] OR adulteration[Title] OR authenticity[Title] '
     'OR traceability[Title] OR mislabeling[Title])'),
    # 分子指纹 / DNA 条形码用于品种
    ("dna_barcode_crop",
     '("DNA barcode"[Title] OR barcoding[Title] '
     'OR "molecular fingerprint"[Title] OR "DNA fingerprint"[Title]) '
     'AND (crop[Title] OR plant[Title] OR rice[Title] '
     'OR variety[Title] OR cultivar[Title] OR wheat[Title])'),
    # CNV 用于作物鉴定
    ("cnv_crop_marker",
     '("copy number variation"[Title] OR "copy number variations"[Title] '
     'OR CNV[Title] OR CNVs[Title]) '
     'AND (wheat[Title] OR rice[Title] OR crop[Title] OR maize[Title])'),
    # 低深度基因型填补
    ("imputation_lowcov",
     '(imputation[Title] OR imputing[Title]) '
     'AND ("low-coverage"[Title] OR "low coverage"[Title] '
     'OR "low-pass"[Title] OR lowdepth[Title])'),
    # 品种鉴定的机器学习 / 相似度方法
    ("variety_similarity_ml",
     '(variety[Title] OR cultivar[Title] OR accession[Title]) '
     'AND (identification[Title] OR classification[Title]) '
     'AND (machine learning[Title/Abstract] OR deep learning[Title/Abstract] '
     'OR random forest[Title/Abstract] OR similarity[Title/Abstract])'),
]


def get(url: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def esearch(term: str, retmax: int = 20) -> list[str]:
    params = {"db": "pubmed", "term": term, "retmax": str(retmax),
              "retmode": "json", "sort": "relevance"}
    try:
        d = json.loads(get(f"{EUT}/esearch.fcgi?" + urllib.parse.urlencode(params)))
        return d.get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        print(f"    [esearch 失败] {exc}", file=sys.stderr)
        return []


def esummary(ids: list[str]) -> dict:
    if not ids:
        return {}
    params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
    try:
        return json.loads(get(f"{EUT}/esummary.fcgi?" + urllib.parse.urlencode(params))
                          ).get("result", {})
    except Exception as exc:
        print(f"    [esummary 失败] {exc}", file=sys.stderr)
        return {}


def main() -> int:
    print("=" * 78)
    print("原编号 TASK-011 第二轮：精确标题级检索")
    print("=" * 78)
    print(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    rows: list[dict[str, str]] = []
    for name, term in TARGETED:
        ids = esearch(term, retmax=20)
        time.sleep(0.4)
        res = esummary(ids)
        time.sleep(0.4)
        n = 0
        for pmid in ids:
            rec = res.get(pmid)
            if not isinstance(rec, dict):
                continue
            au = rec.get("authors", [])
            doi = ""
            for aid in rec.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value", "")
                    break
            rows.append({
                "topic": name, "pmid": pmid,
                "year": (rec.get("pubdate", "") or "")[:4],
                "journal": rec.get("source", ""),
                "first_author": au[0]["name"] if au else "",
                "title": (rec.get("title", "") or "").rstrip("."),
                "doi": doi,
            })
            n += 1
        print(f"  {name:<24} 命中 {len(ids):>3}，解析 {n:>3}")

    print(f"\n合计 {len(rows)} 条\n")
    cols = ["topic", "pmid", "year", "journal", "first_author", "title", "doi"]
    dst = OUTDIR / "literature_targeted.tsv"
    with dst.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
    print(f"已写出：{dst}（{len(rows)} 行）\n")

    # 每个方向打印前 6 条，便于人工筛选
    for name, _ in TARGETED:
        sub = [r for r in rows if r["topic"] == name]
        if not sub:
            continue
        print(f"--- {name} ---")
        for r in sub[:6]:
            print(f"  [{r['year']}] {r['journal'][:22]:<24} {r['title'][:76]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
