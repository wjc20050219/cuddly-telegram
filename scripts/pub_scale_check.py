#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pub_scale_check.py —— 用"run 数 vs 论文自述样本数"给文献匹配打可信度分

动因：Europe PMC 的 57 个命中全是"全文提及"，无结构化链接。
      人工核验 3 例后发现有对有错，而**规模一致性是个有效的判别信号**：
        PRJNA844290  547 run  ↔ 论文"546 accessions"  -> 1.0x  极可能正确
        PRJNA656900 1137 run  ↔ 论文"517 accessions"  -> 2.2x  合理
        PRJNA743713 1137 run  ↔ 论文"123 varieties"   -> 9.2x  存疑

方法：从摘要里正则抽取样本量，与项目的 run 数比较，给出 4 档判定。
产出：更新 study_publications.tsv，增加 scale_check 相关列。
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CAND = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
PUB = CAND / "study_publications.tsv"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# 从摘要中抽取"样本量"的句式
PATTERNS = [
    r"(\d[\d,]*)\s+(?:rice\s+)?(?:accessions|varieties|variety|cultivars|cultivar|landraces|lines|genomes|samples)",
    r"(?:total|totally|a total of|comprising|consisting of|covering)\s+(\d[\d,]*)",
    r"(\d[\d,]*)\s+(?:diverse\s+)?(?:rice\s+)?germplasm",
]


def get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def abstract_of(pmid: str) -> str:
    if not pmid:
        return ""
    params = {"query": f"EXT_ID:{pmid}", "format": "json",
              "resultType": "core", "pageSize": "1"}
    try:
        d = json.loads(get(EPMC + "?" + urllib.parse.urlencode(params)))
        res = d.get("resultList", {}).get("result", [])
        return (res[0].get("abstractText", "") or "") if res else ""
    except Exception:
        return ""


def extract_n(ab: str) -> tuple[int | None, str]:
    """返回 (抽取到的样本量, 命中的原句片段)"""
    for pat in PATTERNS:
        m = re.search(pat, ab, re.I)
        if m:
            try:
                n = int(m.group(1).replace(",", ""))
            except ValueError:
                continue
            if 5 <= n <= 100000:
                s = max(0, m.start() - 40)
                return n, ab[s:m.end() + 20].replace("\n", " ").strip()
    return None, ""


def grade(runs: int, n: int | None) -> tuple[str, str]:
    if n is None:
        return "unknown", "摘要未给出样本量，无法核验"
    ratio = runs / max(1, n)
    if 0.5 <= ratio <= 1.5:
        return "match", f"run/样本 = {ratio:.2f}（近乎 1:1，高度可信）"
    if ratio < 0.5:
        return "runs_fewer", f"run/样本 = {ratio:.2f}（run 少于自述样本量，可能仅部分数据）"
    if ratio <= 3.0:
        return "plausible", f"run/样本 = {ratio:.2f}（每样本多次测序，合理）"
    return "mismatch", f"run/样本 = {ratio:.2f}（★ 差距过大，疑为误匹配）"


def main() -> int:
    with PUB.open(encoding="utf-8", errors="replace", newline="") as fh:
        rdr = csv.reader(fh, delimiter="\t")
        hdr = next(rdr)
        rows = [r + [""] * (len(hdr) - len(r)) for r in rdr]

    if "scale_check" not in hdr:
        hdr += ["reported_n", "scale_check", "scale_note"]
        rows = [r + ["", "", ""] for r in rows]

    ei = hdr.index("evidence")
    pi = hdr.index("pmid")
    ri = hdr.index("n_runs")
    ti = hdr.index("title")
    sci, rni, sni = hdr.index("scale_check"), hdr.index("reported_n"), hdr.index("scale_note")

    targets = [r for r in rows if r[ei] == "fulltext_mention"]
    print("=" * 74)
    print("文献匹配可信度核验（run 数 vs 论文自述样本量）")
    print("=" * 74)
    print(f"待核验 {len(targets)} 条\n")

    t0 = time.time()
    for i, r in enumerate(targets):
        ab = abstract_of(r[pi])
        n, snippet = extract_n(f"{r[ti]} {ab}")
        g, note = grade(int(r[ri]), n)
        r[sci], r[rni], r[sni] = g, str(n or ""), note
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(targets)}  用时 {time.time()-t0:.0f}s")
        time.sleep(0.35)

    with PUB.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(hdr)
        w.writerows(rows)

    from collections import Counter
    c = Counter(r[sci] for r in targets)
    print("\n--- 可信度分级 ---")
    for k in ["match", "plausible", "unknown", "runs_fewer", "mismatch"]:
        n = c.get(k, 0)
        print(f"  {k:<12} {n:>4}  {100.0*n/max(1,len(targets)):>5.1f}%")

    print("\n--- ★ match / plausible（可信度高）Top 10 ---")
    good = [r for r in targets if r[sci] in ("match", "plausible")]
    for r in sorted(good, key=lambda x: -int(x[ri]))[:10]:
        print(f"  {r[0]:<16} {r[ri]:>6} run ↔ {r[rni]:>5} 样本  [{r[sci]}]")
        print(f"      {r[ti][:96]}")

    print("\n--- ★ mismatch（疑似误匹配）---")
    bad = [r for r in targets if r[sci] == "mismatch"]
    for r in bad[:10]:
        print(f"  {r[0]:<16} {r[ri]:>6} run ↔ {r[rni]:>5} 样本")
        print(f"      {r[ti][:96]}")
    if not bad:
        print("  （无）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
