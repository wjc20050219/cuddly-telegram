#!/usr/bin/env python3
"""Generate thesis appendix A (sample manifest) from the real panel manifests.

Appendix A is a list of 55 samples with run accessions. Typing that by hand is
how a thesis ends up with a table that looks authoritative and is subtly wrong,
so it is generated from the same files the pipeline consumes, and the generator
re-verifies the invariants the thesis text claims (panel sizes, zero variety
overlap, all paired-end). If any invariant fails, nothing is written.

Usage::

    python scripts/build_appendix_samples.py
    python scripts/build_appendix_samples.py --check   # verify, do not write
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "data" / "metadata" / "server"
PILOT = MANIFEST_DIR / "pilot_manifest.tsv"
INDEPENDENT = MANIFEST_DIR / "independent_manifest.tsv"
OUT = ROOT / "docs" / "thesis" / "APPENDIX_A_samples.md"

#: Claimed in docs/thesis/THESIS_DRAFT.md section 2.1.3 -- re-checked here so the
#: thesis text and the appendix cannot drift apart silently.
EXPECTED_PILOT = 30
EXPECTED_INDEPENDENT = 25

#: IRGSP-1.0 genome size, used only to render the depth column consistently.
GENOME_BP = 374_495_335


def load(path):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        # str.strip() would eat trailing empty fields; rstrip("\n") is not needed
        # here because DictReader already handled line endings, but values may
        # carry stray spaces.
        for key, value in row.items():
            row[key] = (value or "").strip()
    return rows


def declared_bytes(row):
    """Sum the per-file sizes in `fastq_bytes`, which is ';'-separated when paired."""
    total = 0
    for part in row["fastq_bytes"].split(";"):
        part = part.strip()
        if part:
            total += int(part)
    return total


def gib(n):
    return n / float(1024 ** 3)


def verify(pilot, independent):
    """Return a list of violated invariants (empty means safe to write)."""
    problems = []
    if len(pilot) != EXPECTED_PILOT:
        problems.append("pilot 面板应为 %d 份，实际 %d 份" % (EXPECTED_PILOT, len(pilot)))
    if len(independent) != EXPECTED_INDEPENDENT:
        problems.append("独立面板应为 %d 份，实际 %d 份"
                        % (EXPECTED_INDEPENDENT, len(independent)))

    for label, rows in (("pilot", pilot), ("independent", independent)):
        roles = {r["panel_role"] for r in rows}
        if len(roles) != 1:
            problems.append("%s 面板 panel_role 不唯一: %s" % (label, sorted(roles)))
        for row in rows:
            if row["paired_or_single"] != "PAIRED":
                problems.append("%s 中存在非双端样本: %s" % (label, row["sample_id"]))
            if float(row["estimated_depth"]) < 20.0:
                problems.append("%s 中 %s 估计深度低于 20×"
                                % (label, row["sample_id"]))
            if not row["run_accession"]:
                problems.append("%s 中 %s 缺少 run 号" % (label, row["sample_id"]))

    pilot_varieties = {r["variety_name"] for r in pilot}
    indep_varieties = {r["variety_name"] for r in independent}
    overlap = pilot_varieties & indep_varieties
    if overlap:
        problems.append("两个面板存在品种重叠: %s" % sorted(overlap))
    for label, rows in (("pilot", pilot), ("independent", independent)):
        names = [r["variety_name"] for r in rows]
        if len(set(names)) != len(names):
            problems.append("%s 面板内部存在重复品种" % label)
    return problems


def table(rows, title):
    lines = ["### %s" % title, ""]
    lines.append("| # | sample_id | run_accession | variety_name | subspecies | "
                 "platform | 布局 | 估计深度 | 读长 | 声明大小 (GiB) | 来源库 | BioProject |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for index, row in enumerate(rows, 1):
        lines.append("| %d | `%s` | `%s` | %s | %s | %s | %s | %.2f× | %s | %.2f | %s | %s |" % (
            index,
            row["sample_id"],
            row["run_accession"],
            row["variety_name"],
            row["subspecies"],
            row["platform"],
            row["paired_or_single"],
            float(row["estimated_depth"]),
            row["read_length"],
            gib(declared_bytes(row)),
            row["source_db"],
            row["bioproject"],
        ))
    lines.append("")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="只校验不变量，不写文件")
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)

    pilot, independent = load(PILOT), load(INDEPENDENT)
    problems = verify(pilot, independent)
    if problems:
        for problem in problems:
            print("[FAIL] %s" % problem)
        print("不变量校验未通过，未生成附录 A。")
        return 1

    pilot_bytes = sum(declared_bytes(r) for r in pilot)
    indep_bytes = sum(declared_bytes(r) for r in independent)
    total_bytes = pilot_bytes + indep_bytes

    lines = [
        "# 附录 A　样本清单与 run 号",
        "",
        "> 本附录由 `scripts/build_appendix_samples.py` 从",
        "> `data/metadata/server/pilot_manifest.tsv` 与",
        "> `data/metadata/server/independent_manifest.tsv` 自动生成，**请勿手工编辑**。",
        "> 生成时会重新校验面板规模、品种零重叠、全部双端与最低深度等不变量，",
        "> 任一不变量不满足则不生成文件，以避免正文与附录静默不一致。",
        "",
        "生成脚本：`python scripts/build_appendix_samples.py`",
        "",
        "## A.1 面板构成与不变量",
        "",
        "| 项目 | Pilot | 独立面板 | 合计 |",
        "| --- | --- | --- | --- |",
        "| 样本数 | %d | %d | %d |" % (len(pilot), len(independent), len(pilot) + len(independent)),
        "| 品种数 | %d | %d | %d |" % (len({r["variety_name"] for r in pilot}),
                                       len({r["variety_name"] for r in independent}),
                                       len({r["variety_name"] for r in pilot}) +
                                       len({r["variety_name"] for r in independent})),
        "| 品种交集 | — | — | **0** |",
        "| 测序布局 | 全部 PAIRED | 全部 PAIRED | 全部 PAIRED |",
        "| 最低估计深度 | %.2f× | %.2f× | — |" % (
            min(float(r["estimated_depth"]) for r in pilot),
            min(float(r["estimated_depth"]) for r in independent)),
        "| 清单声明大小 | %.2f GiB | %.2f GiB | **%.2f GiB** |" % (
            gib(pilot_bytes), gib(indep_bytes), gib(total_bytes)),
        "",
        "> **声明大小**为 ENA/SRA 清单中 `fastq_bytes` 字段之和（双端按 `;` 拆分后相加），",
        "> 用于评估服务器存储需求，**不是实测下载量**。实际字节数须以服务器上",
        "> `download_log.tsv` 的记录为准。",
        "",
    ]

    lines += table(pilot, "A.2 Pilot 面板样本（%d 份，用于位点冻结与闭集深度曲线）" % len(pilot))
    lines += table(independent, "A.3 独立面板样本（%d 份，用于开放集拒识）" % len(independent))

    lines += [
        "## A.4 预检样本集",
        "",
        "为降低「先跑通流程再上量」的风险，另设两个预检样本集：",
        "",
        "| 名称 | 样本数 | 声明大小 | 用途 |",
        "| --- | --- | --- | --- |",
        "| `pilot_smoke1.tsv` | 1 | 2.61 GiB | 单样本端到端跑通 |",
        "| `pilot_smoke5.tsv` | 5 | 23.19 GiB | 跨亚种流程验证 |",
        "",
        "构成与选取规则见 `data/metadata/server/manifest_build_summary.json`。",
        "",
        "## A.5 说明",
        "",
        "1. `sample_id` 为 ENA/SRA 样本号，`run_accession` 为实际下载的 run 号；",
        "   本文一个样本对应一个 run，无多样本合并。",
        "2. `subspecies` 取自公共数据库元数据标注，**未经基因型判定**；",
        "   标注为 `unknown` 的样本不做推测。",
        "3. `estimated_depth` 由清单声明的碱基总数与参考基因组大小 374,495,335 bp",
        "   （IRGSP-1.0）估算，属**清单声明值**，非实测比对深度；",
        "   实测深度由 `mosdepth` 在 3.3 节给出。",
        "4. 本清单中的品种名仅代表**元数据标签**，未经品种权或种子法意义确认；",
        "   同名异种与同种异名的处理见 2.1.2 节与附录 D。",
        "",
    ]

    text = "\n".join(lines)
    if args.check:
        print("不变量校验通过（pilot=%d, independent=%d, 合计 %.2f GiB）；未写文件。"
              % (len(pilot), len(independent), gib(total_bytes)))
        return 0

    out_path = Path(args.out)
    # Python 3.7: Path.write_text has no `newline` parameter.
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    print("已写出 %s（%d 行）" % (out_path, text.count("\n") + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
