#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task011_fetch_ena.py —— TASK-011 步骤 1：拉取候选样本的完整元数据

数据来源：ENA Portal API（result=read_run）
目标：水稻 Oryza sativa、文库策略 WGS、深度 ≥5× 的全部 run

为什么取 ≥5×：
  本项目要"从较高深度数据降采样模拟 ulcWGS"，深度不足的材料无法当参考。
  阈值取 ≥5× 而非 ≥10×，是为了留出筛选余量。

  注：早期注释中写的">=10× 有 24,633 条、>=5× 有 32,478 条"**无法复核**——
  那是 count() 运行时打印的计数，未存档；且本脚本的产出是 limit=0 的全量拉取，
  与 data/metadata/search/ 下按 limit= 分页拉取的清单**不是同一类文件**
  （后者行数恰等于页上限，属截断）。如需要准确的深度分档计数，
  请重新运行并**把 count() 的结果写入文件**保存。

产出：data/metadata/candidates/ena_candidates_raw.tsv
"""
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUTDIR = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
OUTDIR.mkdir(parents=True, exist_ok=True)
API = "https://www.ebi.ac.uk/ena/portal/api/search"
GS = 375_000_000          # IRGSP-1.0 单倍体基因组大小
MIN_BASES = 5 * GS        # ≥5×

FIELDS = [
    "run_accession", "experiment_accession", "sample_accession",
    "study_accession", "secondary_study_accession", "study_title",
    "sample_title", "sample_alias", "scientific_name", "tax_id",
    "cultivar", "ecotype", "strain", "isolate",
    "country", "collection_date", "center_name", "first_public",
    "instrument_platform", "instrument_model",
    "library_strategy", "library_source", "library_layout", "library_name",
    "read_count", "base_count", "fastq_ftp", "fastq_bytes", "fastq_md5",
]


def request(url: str, timeout: int = 300) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def count(query: str) -> int | None:
    params = {"result": "read_run", "query": query, "fields": "run_accession",
              "format": "tsv", "limit": "0"}
    try:
        text = request(API + "?" + urllib.parse.urlencode(params), timeout=180)
        return max(0, len(text.rstrip("\n").split("\n")) - 1)
    except Exception as exc:
        print(f"  [count 失败] {exc}", file=sys.stderr)
        return None


def main() -> int:
    print("=" * 74)
    print("TASK-011 步骤 1：拉取候选样本元数据")
    print("=" * 74)
    print(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")

    query = f'tax_eq(4530) AND library_strategy="WGS" AND base_count>={MIN_BASES}'
    print(f"查询：{query}")
    print(f"（base_count ≥ {MIN_BASES:,} ≈ 5×）\n")

    print("--- 先确认命中数 ---")
    n = count(query)
    print(f"  命中：{n if n is not None else '未知'} 条 run\n")

    fields = ",".join(FIELDS)
    params = {"result": "read_run", "query": query, "fields": fields,
              "format": "tsv", "limit": "0"}
    url = API + "?" + urllib.parse.urlencode(params)
    print("--- 拉取全量（limit=0）---")
    t0 = time.time()
    try:
        text = request(url)
    except Exception as exc:
        print(f"[ERROR] 拉取失败：{exc}", file=sys.stderr)
        return 1
    dt = time.time() - t0

    lines = text.rstrip("\n").split("\n")
    if len(lines) < 2:
        print("[ERROR] 无数据", file=sys.stderr)
        print(text[:400], file=sys.stderr)
        return 1

    hdr = lines[0].split("\t")
    rows = [l.split("\t") for l in lines[1:]]
    print(f"  返回 {len(rows)} 行 × {len(hdr)} 列，耗时 {dt:.1f}s "
          f"（{len(text)/1048576:.1f} MB）")

    # 补齐列数不一致的行
    rows = [r + [""] * (len(hdr) - len(r)) if len(r) < len(hdr) else r for r in rows]

    dst = OUTDIR / "ena_candidates_raw.tsv"
    with dst.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(hdr) + "\n")
        for r in rows:
            fh.write("\t".join(r[:len(hdr)]) + "\n")
    print(f"  已存：{dst}（{dst.stat().st_size:,} B）\n")

    print("--- 关键字段填写率 ---")
    def fill(col: str) -> tuple[int, float]:
        if col not in hdr:
            return 0, 0.0
        i = hdr.index(col)
        bad = {"", "nan", "none", "not applicable", "not collected",
               "missing", "na", "null"}
        n = sum(1 for r in rows if r[i].strip().lower() not in bad)
        return n, 100.0 * n / len(rows)

    for col in ["cultivar", "ecotype", "strain", "isolate", "country",
                "collection_date", "sample_title", "sample_alias",
                "instrument_model", "center_name", "fastq_ftp"]:
        n, pct = fill(col)
        print(f"  {col:<20} {n:>6}/{len(rows)}  {pct:>5.1f}%  {'█' * int(pct/3)}")

    print("\n--- 深度分布 ---")
    if "base_count" in hdr:
        i = hdr.index("base_count")
        bins = {"5-10x": 0, "10-20x": 0, "20-30x": 0, "30-50x": 0, ">=50x": 0}
        for r in rows:
            try:
                d = int(r[i]) / GS
            except (ValueError, IndexError):
                continue
            if d < 10: bins["5-10x"] += 1
            elif d < 20: bins["10-20x"] += 1
            elif d < 30: bins["20-30x"] += 1
            elif d < 50: bins["30-50x"] += 1
            else: bins[">=50x"] += 1
        for k, v in bins.items():
            print(f"  {k:<10} {v:>6}")

    print("\n--- 平台分布 ---")
    if "instrument_platform" in hdr:
        i = hdr.index("instrument_platform")
        c: dict[str, int] = {}
        for r in rows:
            c[r[i]] = c.get(r[i], 0) + 1
        for k, v in sorted(c.items(), key=lambda x: -x[1])[:8]:
            print(f"  {k:<20} {v:>6}")

    print("\n--- 提交库分布（accession 前缀）---")
    i = hdr.index("run_accession")
    c = {}
    for r in rows:
        c[r[i][:3]] = c.get(r[i][:3], 0) + 1
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"  {k:<6} {v:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
