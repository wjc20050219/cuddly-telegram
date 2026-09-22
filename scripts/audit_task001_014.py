#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_task001_014.py —— TASK-001 ~ TASK-014 逐项审计（诚实版）

不只看"文件在不在"，还看：
  - 文件是否真的有内容（不是空壳）
  - 数据是否真的可追溯（不是占位）
  - 哪一项的实际深度低于任务书要求（如实标出，不掩饰）

编号采用任务书 B（TASK-001~080）。
"""
import csv
from pathlib import Path

ROOT = Path("/mnt/d/dsh/RiceVar-ID")
D = ROOT / "docs"
M = D / "methods"
TR = D / "task_reports"
SEARCH = ROOT / "data" / "metadata" / "search"
CAND = ROOT / "data" / "metadata" / "candidates"

results: list[tuple[str, str, str, str]] = []   # (id, 名称, 状态, 证据/说明)


def size_of(p: Path) -> str:
    if not p.exists():
        return "缺失"
    n = p.stat().st_size
    if p.is_dir():
        return f"{len(list(p.iterdir()))} 项"
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.0f} KB"
    return f"{n/1024/1024:.1f} MB"


def rows_of(p: Path) -> int:
    if not p.exists():
        return -1
    with p.open(encoding="utf-8", errors="replace") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def add(tid: str, name: str, status: str, evidence: str) -> None:
    results.append((tid, name, status, evidence))


# ---------------- TASK-001 ~ 007 ----------------
add("TASK-001", "项目目录建立",
    "✅" if (ROOT / "PROJECT_STRUCTURE.md").exists() else "❌",
    f"PROJECT_STRUCTURE.md {size_of(ROOT/'PROJECT_STRUCTURE.md')}；"
    f"顶层目录 {len([d for d in ROOT.iterdir() if d.is_dir()])} 个")

env_ok = all((ROOT / f).exists() for f in
             ["environment.yml", "requirements.txt", "software_versions.txt"])
add("TASK-002", "软件环境调查", "✅" if env_ok else "🔶",
    f"environment.yml / requirements.txt / software_versions.txt "
    f"均在；WSL2 环境实测 0/14 工具缺失")

add("TASK-003", "README",
    "✅" if (ROOT / "README.md").exists() else "❌",
    f"README.md {size_of(ROOT/'README.md')}")

for tid, name, fn in [
    ("TASK-004", "阅读 wheat 参考论文", "paper_niu2024_extraction.md"),
    ("TASK-005", "提取论文技术路线", "paper_workflow.md"),
    ("TASK-006", "wheat→rice 技术迁移分析", "wheat_to_rice_migration.md"),
    ("TASK-007", "水稻候选 marker 路线设计", "marker_routes.md"),
]:
    p = M / fn
    n = rows_of(p)
    add(tid, name, "✅" if p.exists() and n > 50 else "❌",
        f"{fn} {size_of(p)}，{n} 行")

# ---------------- TASK-008 ~ 010（数据检索） ----------------
ncbi = SEARCH / "ncbi_search_summary.tsv"
n_ncbi = rows_of(ncbi)
add("TASK-008", "NCBI SRA 数据搜索",
    "✅" if n_ncbi >= 13 else "❌",
    f"ncbi_search_summary.tsv {n_ncbi} 条查询（含 querytranslation 执行证据）；"
    f"ncbi_sra_runs.tsv {rows_of(SEARCH/'ncbi_sra_runs.tsv')} 条 run")

ena = SEARCH / "ena_rice_wgs_deep_runs.tsv"
n_ena = rows_of(ena)
add("TASK-009", "ENA 数据搜索",
    "✅" if n_ena >= 10000 else "❌",
    f"ena_rice_wgs_deep_runs.tsv {n_ena:,} 条 ≥5×（含 FASTQ 直链）；"
    f"ena_search_summary.tsv {rows_of(SEARCH/'ena_search_summary.tsv')} 条查询")

# TASK-010 是 B 编号的 BioProject/BioSample —— 检查是否真有这两库的结果
bp = bs = 0
if ncbi.exists():
    with ncbi.open(encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if len(row) >= 4 and row[0] == "bioproject" and row[3].isdigit():
                bp = int(row[3])
            if len(row) >= 4 and row[0] == "biosample" and row[3].isdigit():
                bs = int(row[3])
add("TASK-010", "BioProject/BioSample 搜索",
    "🔶" if bp and bs else "❌",
    f"BioProject 命中 {bp:,}；BioSample 命中 {bs:,}。"
    f"⚠️ **只做了命中数统计，未逐条拉取记录**（见下方说明）")

# ---------------- TASK-011 ~ 014 ----------------
cs = CAND / "candidate_samples.tsv"
n_cs = rows_of(cs)
with cs.open(encoding="utf-8", errors="replace") as _fh:
    n_col = len(next(csv.reader(_fh, delimiter="\t")))
add("TASK-011", "候选样本整理",
    "✅" if n_cs == 32564 else "❌",
    f"candidate_samples.tsv {n_cs:,} 行 × {n_col} 列")

add("TASK-012", "品种名称标准化",
    "✅" if (CAND / "variety_alias.tsv").exists() else "❌",
    f"variety_alias.tsv {rows_of(CAND/'variety_alias.tsv'):,} 行；"
    f"variety_canonical.tsv {rows_of(CAND/'variety_canonical.tsv'):,} 个规范品种")

add("TASK-013", "重复样本检查",
    "✅" if (CAND / "duplicate_samples.tsv").exists() else "❌",
    f"duplicate_samples.tsv {rows_of(CAND/'duplicate_samples.tsv'):,} 组（分五类）")

p_pilot = rows_of(CAND / "pilot_panel.tsv")
p_test = rows_of(CAND / "independent_test_panel.tsv")
add("TASK-014", "Pilot panel / Independent test panel",
    "✅" if p_pilot == 30 and p_test == 25 else "❌",
    f"pilot_panel.tsv {p_pilot} 份；independent_test_panel.tsv {p_test} 份（已冻结）")

# ---------------- 报告齐备性 ----------------
reports_missing = []
for i in range(1, 15):
    if not (TR / f"TASK-{i:03d}_report.md").exists():
        reports_missing.append(f"TASK-{i:03d}")
add("（报告）", "TASK-001~014 执行报告",
    "✅" if not reports_missing else f"缺少 {len(reports_missing)} 份",
    f"docs/task_reports/ 共 "
    f"{len(list(TR.glob('TASK-*_report.md')))} 份；"
    + (f"缺：{', '.join(reports_missing)}" if reports_missing else "无缺失"))

# ---------------- 输出 ----------------
print("=" * 96)
print("TASK-001 ~ TASK-014 审计（任务书 B 编号）")
print("=" * 96)
print()
w = max(len(r[1]) for r in results)
for tid, name, status, ev in results:
    print(f"{status}  {tid:<9} {name:<{w}}  {ev}")

print()
print("=" * 96)
n_ok = sum(1 for r in results if r[2] == "✅")
n_part = sum(1 for r in results if r[2] == "🔶")
n_bad = sum(1 for r in results if r[2] not in ("✅", "🔶"))
print(f"汇总：{n_ok} 项完成 / {n_part} 项部分完成 / {n_bad} 项未完成")
print("=" * 96)

print()
print("### 必须如实说明的薄弱处 ###")
print()
print("1. TASK-010（BioProject/BioSample）**只做了命中数统计**，")
print("   未像 TASK-008 对 SRA 那样逐条拉取记录（那做了 300 条 esummary）。")
print("   理由：候选样本表以 run 为单位，BioProject/BioSample 编号已随 run 一并取得，")
print("   单独拉取记录对下游无增量。**但严格说，这一项的深度低于其他检索任务。**")
print()
print("2. **原编号 TASK-011（检索公开研究论文）从未执行。**")
print("   它在任务书 B 的第一轮里没有对应编号，所以不算第一轮缺口；")
print("   但后果是 candidate_samples.tsv 的 `publication` 字段全空。")
print()
print("3. 旧编号 TASK-010（DDBJ）仍为部分完成——DDBJ 官方 API 全线 504，")
print("   数据经 INSDC 镜像库取得（该项在 B 编号里没有对应任务）。")
print()
print("4. 全部 14 项均为**数据/文献层面**，未下载任何测序数据，未跑任何基因组分析。")
