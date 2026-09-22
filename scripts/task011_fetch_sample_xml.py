#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task011_fetch_sample_xml.py —— TASK-011 步骤 2：批量拉取 ENA 样本属性

目的：
  Portal 的 cultivar 字段只覆盖 51.7%，缺口的品种名在样本 XML 里。
  实测批量 XML 可行：200 个样本/请求、约 1.7 s。
  32,564 条 run 去重后约 2 万余样本 -> 约百余次请求，数分钟可完成。

  同时 XML 里的 subspecific genetic lineage name 可与 Portal 的 cultivar
  交叉验证，用于发现"字段值其实是亚种/杂交组合"这类脏数据。

产出：
  data/metadata/candidates/sample_attrs.tsv
  data/metadata/candidates/xml_cache/*.xml（断点续传用缓存）
"""
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
CACHE = BASE / "xml_cache"
CACHE.mkdir(parents=True, exist_ok=True)
SRC = BASE / "ena_candidates_raw.tsv"
DST = BASE / "sample_attrs.tsv"
API = "https://www.ebi.ac.uk/ena/browser/api/xml/"

BATCH = 200
COLS = ["sample_accession", "lineage_name", "lineage_rank", "cultivar_tag",
        "ecotype_tag", "description", "xml_title", "xml_country",
        "dev_stage", "fetch_status"]


def get(url: str, timeout: int = 120) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def tag(body: str, name: str) -> str:
    m = re.search(rf"<TAG>{re.escape(name)}</TAG>\s*<VALUE>([^<]*)</VALUE>", body)
    return m.group(1).strip() if m else ""


def parse(xml_text: str, want: list[str]) -> dict[str, dict[str, str]]:
    """返回 {sample_accession: {字段}}"""
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"<SAMPLE\s([^>]*)>(.*?)</SAMPLE>", xml_text, re.S):
        attrs, body = m.group(1), m.group(2)
        am = re.search(r'accession="([^"]+)"', attrs)
        if not am:
            continue
        acc = am.group(1)
        t = re.search(r"<TITLE>([^<]*)</TITLE>", body)
        d = re.search(r"<DESCRIPTION>([^<]*)</DESCRIPTION>", body, re.S)
        out[acc] = {
            "lineage_name": tag(body, "subspecific genetic lineage name"),
            "lineage_rank": tag(body, "subspecific genetic lineage rank"),
            "cultivar_tag": tag(body, "cultivar"),
            "ecotype_tag": tag(body, "ecotype"),
            "dev_stage": tag(body, "plant developmental stage"),
            "xml_country": tag(body, "geographic location (country and/or sea)"),
            "xml_title": (t.group(1).strip() if t else ""),
            "description": (d.group(1).strip() if d else "")[:300],
        }
    return out


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 找不到 {SRC}", file=sys.stderr)
        return 1

    print("=" * 74)
    print("TASK-011 步骤 2：批量拉取 ENA 样本属性")
    print("=" * 74)
    print(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    with SRC.open(encoding="utf-8", errors="replace") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        si = hdr.index("sample_accession")
        samples: list[str] = []
        seen: set[str] = set()
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if si < len(parts):
                a = parts[si].strip()
                if a and a not in seen:
                    seen.add(a)
                    samples.append(a)

    print(f"总 run 数   ：{sum(1 for _ in open(SRC, encoding='utf-8')) - 1:,}")
    print(f"唯一样本数 ：{len(samples):,}")

    pref: dict[str, int] = {}
    for s in samples:
        pref[s[:4]] = pref.get(s[:4], 0) + 1
    print("样本 accession 前缀分布：")
    for k, v in sorted(pref.items(), key=lambda x: -x[1])[:8]:
        print(f"  {k:<8} {v:>7,}")
    print()

    batches = [samples[i:i + BATCH] for i in range(0, len(samples), BATCH)]
    print(f"分批：{len(batches)} 批 × {BATCH}\n")

    results: dict[str, dict[str, str]] = {}
    t0 = time.time()
    failed = 0
    for idx, batch in enumerate(batches):
        cpath = CACHE / f"batch_{idx:05d}.xml"
        if cpath.exists() and cpath.stat().st_size > 200:
            xml_text = cpath.read_text(encoding="utf-8", errors="replace")
            status = "cached"
        else:
            url = API + ",".join(batch)
            xml_text, status = "", "ok"
            for attempt in (1, 2):
                try:
                    xml_text = get(url)
                    break
                except Exception as exc:
                    if attempt == 2:
                        status = f"FAIL:{type(exc).__name__}"
                        failed += 1
                    else:
                        time.sleep(2)
            if xml_text:
                cpath.write_text(xml_text, encoding="utf-8")

        got = parse(xml_text, batch)
        for acc in batch:
            if acc in got:
                results[acc] = got[acc]
            else:
                results[acc] = {k: "" for k in COLS[1:-1]}
                results[acc]["fetch_status"] = "not_in_response"
                continue
            results[acc]["fetch_status"] = status

        if (idx + 1) % 20 == 0 or idx == len(batches) - 1:
            el = time.time() - t0
            done = min((idx + 1) * BATCH, len(samples))
            rate = done / el if el > 0 else 0
            eta = (len(samples) - done) / rate if rate > 0 else 0
            print(f"  进度 {done:>6,}/{len(samples):,}  "
                  f"已用 {el:>6.0f}s  速度 {rate:>6.1f}/s  预计剩余 {eta:>5.0f}s")

    print(f"\n完成，耗时 {time.time()-t0:.0f}s，失败批次 {failed}\n")

    with DST.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(COLS) + "\n")
        for acc in samples:
            r = results.get(acc, {})
            fh.write("\t".join(
                [acc] + [str(r.get(c, "")).replace("\t", " ") for c in COLS[1:]]
            ) + "\n")
    print(f"已写出：{DST}（{len(samples):,} 行）\n")

    # ---- 统计 ----
    bad = {"", "nan", "none", "not applicable", "not collected", "missing"}
    def cnt(key: str) -> int:
        return sum(1 for r in results.values()
                   if str(r.get(key, "")).strip().lower() not in bad)

    print("--- XML 字段命中率 ---")
    tot = len(samples)
    for c in ["lineage_name", "lineage_rank", "cultivar_tag", "ecotype_tag",
              "description", "xml_country"]:
        n = cnt(c)
        print(f"  {c:<16} {n:>7,}/{tot:,}  {100.0*n/tot:>5.1f}%  {'█'*int(100.0*n/tot/3)}")

    print("\n--- subspecific genetic lineage name 样例 ---")
    shown = 0
    for acc in samples:
        v = results[acc].get("lineage_name", "")
        if v:
            print(f"    {acc:<18} {v[:44]:<46} rank={results[acc].get('lineage_rank','')[:12]}")
            shown += 1
            if shown >= 15:
                break
    if shown == 0:
        print("    （无）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
