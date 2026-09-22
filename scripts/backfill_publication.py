#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_publication.py —— 回填 candidate_samples.tsv 的 publication 字段

思路：ENA 的 result=study 通常带 publication_doi / publication_pubmed_id，
      按 BioProject 批量取一次即可覆盖整张表（比逐条 run 查询高效得多）。

产出：
  data/metadata/candidates/study_publications.tsv  BioProject -> 文献
  data/metadata/candidates/candidate_samples.tsv   回填 publication 列（原地更新）
"""
import csv
import io
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

CAND = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = CAND / "candidate_samples.tsv"
PUB = CAND / "study_publications.tsv"
API = "https://www.ebi.ac.uk/ena/portal/api"

BATCH = 80          # 每次查多少个 study


def get(url: str, timeout: int = 180) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> int:
    print("=" * 74)
    print("回填 publication 字段（来源：ENA result=study）")
    print("=" * 74)

    # ---- 0. 先看 study 结果有哪些字段可用 ----
    try:
        fields_raw = get(f"{API}/returnFields?result=study&format=tsv", timeout=90)
        names = [l.split("\t")[0] for l in fields_raw.strip().split("\n")[1:]]
        pub_fields = [n for n in names if "publi" in n.lower() or "doi" in n.lower()
                      or "journal" in n.lower()]
        print(f"study 结果共 {len(names)} 个字段")
        print(f"含文献信息的字段：{pub_fields if pub_fields else '（无！）'}")
        if not pub_fields:
            print("\n[结论] ENA study 结果不提供文献字段，本方案不可行。", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[WARN] returnFields 失败：{exc}", file=sys.stderr)
        pub_fields = ["publication_doi", "publication_pubmed_id"]

    # ---- 1. 读主表，统计 BioProject ----
    with SRC.open(encoding="utf-8", errors="replace") as fh:
        rdr = csv.reader(fh, delimiter="\t")
        hdr = next(rdr)
        rows = [r + [""] * (len(hdr) - len(r)) for r in rdr]
    pi = hdr.index("BioProject")
    proj = Counter(r[pi] for r in rows if r[pi])
    print(f"\n主表 {len(rows):,} 行，涉及 {len(proj):,} 个 BioProject")
    print(f"最大项目：{proj.most_common(3)}")

    # ---- 2. 分批查 study ----
    use = ["study_accession", "secondary_study_accession", "study_title",
           "center_name", "first_public"]
    for f in ["publication_doi", "publication_pubmed_id", "publication_title",
              "publication_journal", "publication_year"]:
        if f in names:
            use.append(f)

    projects = list(proj)
    batches = [projects[i:i + BATCH] for i in range(0, len(projects), BATCH)]
    print(f"\n分 {len(batches)} 批查询（每批 {BATCH} 个）\n")

    info: dict[str, dict[str, str]] = {}
    t0 = time.time()
    for bi, batch in enumerate(batches):
        query = "study_accession=" + ",".join(batch)
        params = {"result": "study", "query": query,
                  "fields": ",".join(use), "format": "tsv", "limit": "0"}
        try:
            text = get(f"{API}/search?" + urllib.parse.urlencode(params))
        except Exception as exc:
            print(f"  批 {bi} 失败：{exc}", file=sys.stderr)
            continue
        lines = text.rstrip("\n").split("\n")
        if len(lines) < 2:
            continue
        # 表头可能因字段顺序不同，逐批解析
        bh = lines[0].split("\t")
        for line in lines[1:]:
            p = line.split("\t")
            p += [""] * (len(bh) - len(p))
            d = dict(zip(bh, p))
            info[d.get("study_accession", "")] = d
        if (bi + 1) % 10 == 0 or bi == len(batches) - 1:
            print(f"  进度 {bi+1}/{len(batches)}  已解析 {len(info):,} 个 study"
                  f"  用时 {time.time()-t0:.0f}s")
        time.sleep(0.2)

    print(f"\n共取到 {len(info):,} 个 study 的信息")

    # ---- 3. 写出 study -> 文献 表 ----
    scols = ["study_accession", "study_title", "center_name", "first_public"] + \
            [f for f in use if f.startswith("publication")]
    with PUB.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(scols) + "\n")
        for p in projects:
            d = info.get(p, {})
            fh.write("\t".join(str(d.get(c, "")).replace("\t", " ") for c in scols) + "\n")
    print(f"已写出：{PUB}")

    # ---- 4. 回填主表 ----
    def pub_of(proj_acc: str) -> str:
        d = info.get(proj_acc, {})
        doi = (d.get("publication_doi") or "").strip()
        pmid = (d.get("publication_pubmed_id") or "").strip()
        title = (d.get("publication_title") or "").strip()
        year = (d.get("publication_year") or "").strip()
        parts = []
        if doi and doi.lower() not in ("nan", "none"):
            parts.append(f"doi:{doi}")
        if pmid and pmid.lower() not in ("nan", "none"):
            parts.append(f"PMID:{pmid}")
        if year and year.lower() not in ("nan", "none"):
            parts.append(year)
        if title and title.lower() not in ("nan", "none"):
            parts.append(title[:120])
        return " | ".join(parts)

    pi_pub = hdr.index("publication")
    n_filled = 0
    for r in rows:
        v = pub_of(r[pi])
        if v:
            r[pi_pub] = v
            n_filled += 1

    with SRC.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(hdr)
        w.writerows(rows)

    print(f"\n★ 回填完成：{n_filled:,} / {len(rows):,} 行"
          f"（{100.0*n_filled/len(rows):.1f}%）有文献信息")

    # ---- 5. 统计 ----
    n_proj_with = sum(1 for p in projects if pub_of(p))
    print(f"  涉及 {n_proj_with:,} / {len(projects):,} 个 BioProject")

    print("\n--- ★ 有文献的最大项目 Top 15 ---")
    with_pub = [(p, c) for p, c in proj.most_common() if pub_of(p)]
    for p, c in with_pub[:15]:
        print(f"  {p:<16} {c:>6,} run")
        print(f"       {pub_of(p)[:110]}")

    if not with_pub:
        print("  （无）")
        print("\n  ⚠️ ENA 未提供文献关联，publication 字段仍为空。")
        print("     备选方案：按 BioProject 号在 Europe PMC 检索，见 literature_review.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
