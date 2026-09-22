#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
final_verify.py —— TASK-007~010 交付物最终交叉核验

核验三件事：
  1. 文档中引用的关键数字，是否确实能在数据文件中找到
  2. 数据文件的行数/列数是否与文档描述一致
  3. 新建文档中的相对链接是否指向存在的文件
"""
import csv
import re
from pathlib import Path

ROOT = Path("/mnt/d/dsh/RiceVar-ID")
SEARCH = ROOT / "data" / "metadata" / "search"
fail: list[str] = []
ok: list[str] = []


def chk(cond: bool, msg: str) -> None:
    (ok if cond else fail).append(msg)
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")


def rows(p: Path) -> list[list[str]]:
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        return [r for r in csv.reader(fh, delimiter="\t")]


print("=" * 72)
print("1. 数据文件结构核验")
print("=" * 72)

f = SEARCH / "ncbi_search_summary.tsv"
r = rows(f)
chk(f.exists() and len(r) == 14, f"ncbi_search_summary.tsv 应为 1 表头 + 13 行，实得 {len(r)}")
chk(len(r[0]) == 5 and r[0][4] == "querytranslation",
    f"含执行证据列 querytranslation，实得 {len(r[0])} 列")

f = SEARCH / "ncbi_sra_runs.tsv"
r = rows(f)
chk(len(r) == 301, f"ncbi_sra_runs.tsv 应为 1 表头 + 300 行，实得 {len(r)}")
hdr = r[0]
for col in ("run", "experiment", "study", "bioproject", "biosample",
            "library_strategy", "platform", "est_depth", "title"):
    chk(col in hdr, f"  含列 {col}")

f = SEARCH / "ena_rice_wgs_deep_runs.tsv"
r = rows(f)
chk(len(r) == 10001, f"ena_rice_wgs_deep_runs.tsv 应为 1 表头 + 10,000 行，实得 {len(r)}")
chk("fastq_ftp" in r[0] and "base_count" in r[0], "含 fastq_ftp 与 base_count 列")

print()
print("=" * 72)
print("2. 文档引用的关键数字 vs 数据文件实测")
print("=" * 72)

# --- 深度分布 ---
hdr = r[0]
print(f"  ENA 表头：{hdr}")
ci = hdr.index("base_count")
li = hdr.index("library_layout")
ai = hdr.index("fastq_ftp")
si = hdr.index("run_accession")
plat_i = hdr.index("instrument_platform")
bins = {"5-10x": 0, "10-20x": 0, "20-30x": 0, "30-50x": 0, ">=50x": 0}
lay = {}
plat = {}
pref = {}
have_fq = 0
GS = 375_000_000
for row in r[1:]:
    bc = int(row[ci]) if row[ci].isdigit() else 0
    d = bc / GS
    if d < 10: bins["5-10x"] += 1
    elif d < 20: bins["10-20x"] += 1
    elif d < 30: bins["20-30x"] += 1
    elif d < 50: bins["30-50x"] += 1
    else: bins[">=50x"] += 1
    lay[row[li]] = lay.get(row[li], 0) + 1
    plat[row[plat_i]] = plat.get(row[plat_i], 0) + 1
    pref[row[si][:3]] = pref.get(row[si][:3], 0) + 1
    if row[ai] and row[ai] not in ("", "nan"):
        have_fq += 1

print(f"  ENA ≥5× 清单深度分布：{bins}")
chk(bins["5-10x"] == 2572, f"5–10× 应 2,572，实得 {bins['5-10x']}")
chk(bins["10-20x"] == 4055, f"10–20× 应 4,055，实得 {bins['10-20x']}")
chk(bins[">=50x"] == 911, f"≥50× 应 911，实得 {bins['>=50x']}")

print(f"  布局：{lay}")
print(f"  平台：{plat}")
print(f"  提交库前缀：{pref}")
chk(pref.get("SRR", 0) == 7373, f"SRR 应 7,373，实得 {pref.get('SRR', 0)}")
chk(pref.get("DRR", 0) == 1255, f"DRR 应 1,255，实得 {pref.get('DRR', 0)}")
chk(pref.get("ERR", 0) == 1372, f"ERR 应 1,372，实得 {pref.get('ERR', 0)}")
chk(have_fq == 10000, f"FASTQ 直链可用应 10,000（100%），实得 {have_fq}")

# --- NCBI 的 DDBJ 占比 ---
f = SEARCH / "ncbi_sra_runs.tsv"
r2 = rows(f)
h = r2[0]
ri = h.index("run")
ddbj = sum(1 for x in r2[1:] if x[ri].startswith("DRR"))
ncbi = sum(1 for x in r2[1:] if x[ri].startswith("SRR"))
print(f"  NCBI 前 300 条中：DRR {ddbj} / SRR {ncbi}")
chk(ddbj == 292, f"DRR 应 292，实得 {ddbj}")
chk(ncbi == 8, f"SRR 应 8，实得 {ncbi}")

print()
print("=" * 72)
print("3. 文档相对链接可达性")
print("=" * 72)

docs = [
    ROOT / "README.md",
    ROOT / "docs" / "methods" / "marker_routes.md",
    ROOT / "docs" / "methods" / "data_source_survey.md",
    ROOT / "docs" / "server_admin_questions.md",
    ROOT / "docs" / "STATUS.md",
    ROOT / "PROJECT_STRUCTURE.md",
    ROOT / "data" / "metadata" / "search" / "README.md",
]
bad = 0
for d in docs:
    txt = d.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"\]\(([^)]+\.(?:md|tsv|json|py|sh))\)", txt):
        tgt = m.group(1)
        if tgt.startswith(("http", "#")):
            continue
        p = (d.parent / tgt).resolve()
        if not p.exists():
            print(f"  [FAIL] {d.name} → {tgt} 不存在")
            bad += 1
chk(bad == 0, f"全部相对链接可达（检查 {len(docs)} 个文档）")

print()
print("=" * 72)
print(f"结果：{len(ok)} 项通过，{len(fail)} 项失败")
print("=" * 72)
for m in fail:
    print(f"  ✗ {m}")
raise SystemExit(1 if fail else 0)
