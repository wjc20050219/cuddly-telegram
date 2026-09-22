#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_europepmc.py —— 测试用 BioProject 编号在 Europe PMC 反查文献的可行性

背景：ENA 的 result=study 不提供文献字段（实测 29 个字段里只有 first_public），
      故改用 Europe PMC 按项目编号检索。
"""
import json
import sys
import time
import urllib.parse
import urllib.request

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# 用真实存在、且大概率有配套论文的项目测试
TESTS = [
    ("PRJDB5765", "Pilot 中的 Bekogonomi（日本水稻核心种质）"),
    ("PRJNA795890", "最大项目 9,503 run"),
    ("PRJDB38331", "ZH11 EMS 突变体库 5,344 run"),
    ("PRJNA719383", "ZH11 相关小项目"),
    ("PRJEB53225", "2,837 run"),
    ("PRJNA285384", "Pilot 中的 RP Bio-226（3K RGP 相关）"),
]


def get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def search(query: str, page_size: int = 5) -> dict:
    params = {"query": query, "format": "json", "pageSize": str(page_size),
              "resultType": "core"}
    return json.loads(get(EPMC + "?" + urllib.parse.urlencode(params)))


def main() -> int:
    print("=" * 76)
    print("Europe PMC 按 BioProject 编号反查文献 —— 可行性测试")
    print("=" * 76)
    print()

    for acc, why in TESTS:
        print(f"--- {acc}  （{why}）---")
        # 方式 1：直接当全文词检索
        for q, label in [
            (f'"{acc}"', "全文精确匹配"),
            (f'ACCESSION_ID:"{acc}"', "ACCESSION_ID 字段"),
            (f'"{acc}" AND SRC:MED', "限定 MEDLINE 来源"),
        ]:
            try:
                d = search(q)
                n = d.get("hitCount", 0)
                print(f"    {label:<20} 命中 {n}")
                if n:
                    for r in d.get("resultList", {}).get("result", [])[:2]:
                        print(f"        [{r.get('pubYear','')}] {r.get('journalTitle','')[:26]:<28}"
                              f" {str(r.get('title',''))[:60]}")
                        print(f"          doi:{r.get('doi','')}  PMID:{r.get('pmid','')}")
            except Exception as exc:
                print(f"    {label:<20} 失败：{exc}")
            time.sleep(0.5)
        print()

    print("=" * 76)
    print("判定：若『全文精确匹配』有稳定命中，则可对全部 2,052 个项目批量反查；")
    print("      若普遍为 0，则说明 ENA/INSDC 数据与文献之间没有可靠的自动关联，")
    print("      publication 字段应如实留空，并在论文中说明数据溯源到 accession 为止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
