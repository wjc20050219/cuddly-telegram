#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
round1_verify.py —— 第一轮（TASK-011~014）交付物自动核验

核验四件事：
  1. 面板规模与不重叠性（可复现性声明是否成立）
  2. 候选表结构完整性（22 个规定字段是否齐备）
  3. 文档中引用的关键数字是否与数据文件一致
  4. 文档相对链接可达性
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data" / "metadata" / "candidates"
fail: list[str] = []
ok: list[str] = []


def chk(cond: bool, msg: str) -> None:
    (ok if cond else fail).append(msg)
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")


def rows(p: Path) -> list[list[str]]:
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        return [r for r in csv.reader(fh, delimiter="\t")]


print("=" * 74)
print("1. 候选样本表结构")
print("=" * 74)
r = rows(CAND / "candidate_samples.tsv")
hdr = r[0]
chk(len(r) - 1 == 32564, f"candidate_samples.tsv 应为 32,564 行，实得 {len(r)-1:,}")

# 任务书第九节规定的 22 个字段
REQUIRED = ["sample_id", "variety_name", "variety_alias", "species", "subspecies",
            "accession", "BioProject", "BioSample", "SRA_accession",
            "ENA_accession", "publication", "country", "population",
            "cultivar_or_landrace", "sequencing_platform", "read_length",
            "paired_or_single", "estimated_depth", "reference_genome",
            "data_source", "download_status", "qc_status"]
missing = [c for c in REQUIRED if c not in hdr]
chk(not missing, f"22 个规定字段齐备（缺：{missing or '无'}）")
print(f"       实际列数：{len(hdr)}")

print()
print("=" * 74)
print("2. 面板规模与冻结声明")
print("=" * 74)
pr = rows(CAND / "pilot_panel.tsv")
tr = rows(CAND / "independent_test_panel.tsv")
chk(len(pr) - 1 == 30, f"Pilot 应为 30 份，实得 {len(pr)-1}")
chk(len(tr) - 1 == 25, f"独立测试集应为 25 份，实得 {len(tr)-1}")

pi, ti = pr[0].index("canonical_name"), tr[0].index("canonical_name")
pv = {x[pi] for x in pr[1:]}
tv = {x[ti] for x in tr[1:]}
chk(len(pv & tv) == 0, f"两面板品种零重叠（交集 {len(pv & tv)} 个）")

# accession 唯一
si = pr[0].index("sample_id")
allacc = [x[si] for x in pr[1:]] + [x[si] for x in tr[1:]]
chk(len(allacc) == len(set(allacc)), f"55 个 accession 无重复（{len(allacc)} 个）")

# 真实性：必须含 FASTQ 直链
fi = pr[0].index("fastq_ftp")
n_fq = sum(1 for x in pr[1:] if x[fi].strip())
chk(n_fq == 30, f"Pilot 全部含 FASTQ 直链（{n_fq}/30）")

# 深度区间
di = pr[0].index("estimated_depth")
d = [float(x[di]) for x in pr[1:]]
chk(all(20.0 <= v <= 50.0 for v in d),
    f"Pilot 深度均在 20–50× 内（min {min(d):.1f} / max {max(d):.1f}）")

# 无突变体（study_title 不含 ems/mutant）
if "canonical_name" in pr[0]:
    chk(all("zh11" not in x[pi].lower() for x in pr[1:]),
        "Pilot 未混入 ZH11 EMS 突变体库")

print()
print("=" * 74)
print("3. 关键数字与数据文件一致性")
print("=" * 74)
# 品种名质量分级
qi = hdr.index("name_quality")
from collections import Counter
q = Counter(x[qi] for x in r[1:])
chk(q["good"] == 7773, f"good 应 7,773，实得 {q['good']:,}")
chk(q["code"] == 7025, f"code 应 7,025，实得 {q['code']:,}")
chk(q["unusable"] == 17734, f"unusable 应 17,734，实得 {q['unusable']:,}")
usable = q["good"] + q["caveat"] + q["code"]
chk(usable == 14830, f"可用合计应 14,830，实得 {usable:,}")

# 规范品种数
cr = rows(CAND / "variety_canonical.tsv")
chk(len(cr) - 1 == 8415, f"规范品种应 8,415，实得 {len(cr)-1:,}")

# ★ 别名表与重复表的行数（曾因改逻辑后重跑而与报告不一致，故纳入核验）
ar = rows(CAND / "variety_alias.tsv")
chk(len(ar) - 1 == 8501, f"variety_alias 应 8,501 行，实得 {len(ar)-1:,}")
dr = rows(CAND / "duplicate_samples.tsv")
chk(len(dr) - 1 == 1326, f"duplicate_samples 应 1,326 组，实得 {len(dr)-1:,}")

# 存储量（文档称 Pilot 170.70 GiB / 测试集 164.02 GiB）
def gib(panel: list[list[str]]) -> float:
    bi = panel[0].index("fastq_bytes")
    t = 0
    for x in panel[1:]:
        for part in x[bi].replace(",", "").split(";"):
            if part.strip().isdigit():
                t += int(part)
    return t / 1024 ** 3

pg, tg = gib(pr), gib(tr)
chk(abs(pg - 170.70) < 0.05, f"Pilot 应为 170.70 GiB，实得 {pg:.2f}")
chk(abs(tg - 164.02) < 0.05, f"测试集应为 164.02 GiB，实得 {tg:.2f}")
chk(abs(pg + tg - 334.71) < 0.05, f"合计应为 334.71 GiB，实得 {pg+tg:.2f}")

print()
print("=" * 74)
print("4. 文献检索产出（原 TASK-011）")
print("=" * 74)
LIT = ROOT / "data" / "metadata" / "literature"
for fn, want in (("literature_hits.tsv", 200), ("literature_targeted.tsv", 180)):
    lr = rows(LIT / fn)
    chk(len(lr) - 1 == want, f"{fn} 应 {want} 条，实得 {len(lr)-1}")

ka = LIT / "key_abstracts.txt"
chk(ka.exists() and ka.stat().st_size > 5000,
    f"key_abstracts.txt 存在且有内容（{ka.stat().st_size if ka.exists() else 0:,} B）")
if ka.exists():
    txt = ka.read_text(encoding="utf-8", errors="replace")
    n_doi = len(re.findall(r"^DOI：10\.", txt, re.M))
    chk(n_doi >= 10, f"关键文献 DOI 提取完整（{n_doi} 个）")

sp = rows(CAND / "study_publications.tsv")
chk("scale_check" in sp[0], "study_publications.tsv 含可信度分级列 scale_check")
ps = rows(CAND / "panel_sources.tsv")
chk(len(ps) - 1 == 55, f"panel_sources.tsv 应 55 行，实得 {len(ps)-1}")

# 主表 publication 回填
pub_i = hdr.index("publication")
n_pub = sum(1 for x in r[1:] if x[pub_i].strip())
chk(n_pub == 11040, f"publication 回填应 11,040 行，实得 {n_pub:,}")
n_match = sum(1 for x in r[1:] if x[pub_i].startswith("[MATCH]"))
chk(n_match == 1593, f"[MATCH] 应 1,593 行，实得 {n_match:,}")

print()
print("=" * 74)
print("5. 文档链接可达性")
print("=" * 74)
docs = [
    ROOT / "README.md", ROOT / "PROJECT_STRUCTURE.md",
    ROOT / "docs" / "STATUS.md", ROOT / "docs" / "ROUND1_SUMMARY.md",
    ROOT / "docs" / "TASK_NUMBERING.md",
    ROOT / "docs" / "methods" / "data_source_survey.md",
    ROOT / "docs" / "methods" / "marker_routes.md",
    ROOT / "docs" / "server_admin_questions.md",
] + [ROOT / "docs" / "task_reports" / f"TASK-{i:03d}_report.md" for i in range(11, 15)]

bad = 0
for d in docs:
    if not d.exists():
        print(f"  [FAIL] 文档不存在：{d.name}")
        bad += 1
        continue
    txt = d.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"\]\(([^)]+\.(?:md|tsv|json|py|sh))\)", txt):
        tgt = m.group(1)
        if tgt.startswith(("http", "#")):
            continue
        if not (d.parent / tgt).resolve().exists():
            print(f"  [FAIL] {d.name} → {tgt} 不存在")
            bad += 1
chk(bad == 0, f"全部相对链接可达（检查 {len(docs)} 个文档）")

print()
print("=" * 74)
print(f"结果：{len(ok)} 项通过，{len(fail)} 项失败")
print("=" * 74)
for m in fail:
    print(f"  ✗ {m}")
raise SystemExit(1 if fail else 0)
