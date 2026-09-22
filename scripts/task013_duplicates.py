#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task013_duplicates.py —— TASK-013：重复样本检查

输入：
  data/metadata/candidates/candidate_samples.tsv （TASK-011）
  data/metadata/candidates/variety_alias.tsv     （TASK-012）
输出：
  data/metadata/candidates/duplicate_samples.tsv

检查五类重复/冲突（**类型不同，处理方式完全不同，不能一概当"重复要删"**）：

  1. same_biosample       同一 BioSample 有多个 run（同一份 DNA 重复测序）
                          -> 技术重复，建库时**只取一个 run**避免权重失衡
  2. same_fastq_file      多个 run 指向同一 FASTQ 文件（同一数据重复登记）
                          -> 真重复，必须去重
  3. same_variety_multi   同一品种有多个 run（不同种子/不同批次）
                          -> **不是重复**，是宝贵的重复性验证材料，保留
  4. same_variety_multiproject  同一品种跨多个 BioProject
                          -> 需人工判断是否同一材料（可能是同名不同系）
  5. subspecies_conflict  同一品种名在不同样本上标注了矛盾亚种
                          -> ★ 可能是标签错误，必须标记

诚实性：本脚本只做**证据报告**，不自动删除任何样本；
       每条都给出 recommendation 供 TASK-014 决策。
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = BASE / "candidate_samples.tsv"
ALIAS = BASE / "variety_alias.tsv"
DST = BASE / "duplicate_samples.tsv"


def fdepth(rec: dict) -> float:
    """TSV 读入的深度是字符串，安全转为 float"""
    try:
        return float(rec.get("estimated_depth", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 缺少 {SRC}", file=sys.stderr)
        return 1

    print("=" * 74)
    print("TASK-013：重复样本检查")
    print("=" * 74)

    with SRC.open(encoding="utf-8", errors="replace") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        rows = []
        for line in fh:
            p = line.rstrip("\n").split("\t")
            p += [""] * (len(hdr) - len(p))
            rows.append(dict(zip(hdr, p)))

    # 品种名 -> 规范名
    alias_map: dict[str, str] = {}
    if ALIAS.exists():
        with ALIAS.open(encoding="utf-8", errors="replace") as fh:
            ah = fh.readline().rstrip("\n").split("\t")
            ai, ci = ah.index("alias"), ah.index("canonical_name")
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) > max(ai, ci):
                    alias_map[p[ai]] = p[ci]
    print(f"读到 run {len(rows):,} 条，别名映射 {len(alias_map):,} 条\n")

    records = []
    for r in rows:
        if r["name_quality"] not in ("good", "caveat", "code"):
            continue
        name = r["variety_name"].strip()
        records.append({
            **r,
            "canonical": alias_map.get(name, name),
        })
    print(f"参与检查的 run（品种名可用）：{len(records):,}\n")

    dup_rows: list[dict[str, str]] = []
    gid = 0

    # ---- 1. 同一 BioSample 多 run ----
    by_sample: dict[str, list] = defaultdict(list)
    for r in records:
        by_sample[r["BioSample"]].append(r)
    n1 = 0
    for s, rs in by_sample.items():
        if len(rs) < 2:
            continue
        n1 += 1
        gid += 1
        names = sorted({x["canonical"] for x in rs})
        dup_rows.append({
            "group_id": f"DUP{gid:05d}",
            "duplicate_type": "same_biosample",
            "canonical_name": "|".join(names[:3]),
            "n_samples": str(len(rs)),
            "n_varieties_in_group": str(len(names)),
            "samples": ";".join(x["sample_id"] for x in rs[:12]),
            "biosamples": s,
            "bioprojects": "|".join(sorted({x["BioProject"] for x in rs})[:5]),
            "max_depth": f"{max(fdepth(x) for x in rs):.1f}",
            "recommendation": "keep_one_run（同一 DNA 的技术重复，建库只取 1 个 run）",
            "note": "同名冲突" if len(names) > 1 else "",
        })

    # ---- 2. 同一 FASTQ 文件 ----
    by_fq: dict[str, list] = defaultdict(list)
    for r in records:
        fq = r["fastq_ftp"].split(";")[0].strip()
        if fq:
            by_fq[fq].append(r)
    n2 = 0
    for fq, rs in by_fq.items():
        if len(rs) < 2:
            continue
        n2 += 1
        gid += 1
        dup_rows.append({
            "group_id": f"DUP{gid:05d}",
            "duplicate_type": "same_fastq_file",
            "canonical_name": "|".join(sorted({x["canonical"] for x in rs})[:3]),
            "n_samples": str(len(rs)),
            "n_varieties_in_group": str(len({x["canonical"] for x in rs})),
            "samples": ";".join(x["sample_id"] for x in rs[:12]),
            "biosamples": "|".join(sorted({x["BioSample"] for x in rs})[:5]),
            "bioprojects": "|".join(sorted({x["BioProject"] for x in rs})[:5]),
            "max_depth": f"{max(fdepth(x) for x in rs):.1f}",
            "recommendation": "remove_duplicates（指向同一文件，必须去重）",
            "note": fq[:60],
        })

    # ---- 3/4/5. 按规范品种聚合 ----
    by_var: dict[str, list] = defaultdict(list)
    for r in records:
        by_var[r["canonical"]].append(r)

    n3 = n4 = n5 = 0
    for var, rs in by_var.items():
        if len(rs) < 2:
            continue
        projs = sorted({x["BioProject"] for x in rs})
        subs = sorted({x["subspecies"] for x in rs if x["subspecies"]})

        # 5. 亚种冲突
        if len(subs) > 1:
            n5 += 1
            gid += 1
            dup_rows.append({
                "group_id": f"DUP{gid:05d}",
                "duplicate_type": "subspecies_conflict",
                "canonical_name": var,
                "n_samples": str(len(rs)),
                "n_varieties_in_group": "1",
                "samples": ";".join(x["sample_id"] for x in rs[:12]),
                "biosamples": "|".join(sorted({x["BioSample"] for x in rs})[:5]),
                "bioprojects": "|".join(projs[:5]),
                "max_depth": f"{max(fdepth(x) for x in rs):.1f}",
                "recommendation": "review（同名却标注不同亚种，疑似标签错误）",
                "note": "亚种=" + "|".join(subs),
            })

        # 4. 跨 BioProject 同名
        if len(projs) > 1:
            n4 += 1
            gid += 1
            dup_rows.append({
                "group_id": f"DUP{gid:05d}",
                "duplicate_type": "same_variety_multiproject",
                "canonical_name": var,
                "n_samples": str(len(rs)),
                "n_varieties_in_group": "1",
                "samples": ";".join(x["sample_id"] for x in rs[:12]),
                "biosamples": "|".join(sorted({x["BioSample"] for x in rs})[:5]),
                "bioprojects": "|".join(projs[:8]),
                "max_depth": f"{max(fdepth(x) for x in rs):.1f}",
                "recommendation": "keep（可能是同一品种的不同种子来源，可用于跨项目验证）",
                "note": f"涉及 {len(projs)} 个 BioProject",
            })
        else:
            # 3. 同项目内同品种多 run
            n3 += 1
            gid += 1
            dup_rows.append({
                "group_id": f"DUP{gid:05d}",
                "duplicate_type": "same_variety_multi_run",
                "canonical_name": var,
                "n_samples": str(len(rs)),
                "n_varieties_in_group": "1",
                "samples": ";".join(x["sample_id"] for x in rs[:12]),
                "biosamples": "|".join(sorted({x["BioSample"] for x in rs})[:5]),
                "bioprojects": "|".join(projs[:5]),
                "max_depth": f"{max(fdepth(x) for x in rs):.1f}",
                "recommendation": "keep（★ 重复性验证材料，不是重复）",
                "note": f"同项目内 {len(rs)} 个 run",
            })

    # ---- 输出 ----
    cols = ["group_id", "duplicate_type", "canonical_name", "n_samples",
            "n_varieties_in_group", "samples", "biosamples", "bioprojects",
            "max_depth", "recommendation", "note"]
    with DST.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in dup_rows:
            fh.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    print(f"已写出：{DST}（{len(dup_rows):,} 组）\n")

    # ---- 报告 ----
    print("--- 五类检查结果 ---")
    print(f"  1. same_biosample          {n1:>6,} 组  -> 技术重复，建库取 1 个 run")
    print(f"  2. same_fastq_file         {n2:>6,} 组  -> 真重复，必须去重")
    print(f"  3. same_variety_multi_run  {n3:>6,} 组  -> 保留（重复性验证材料）")
    print(f"  4. same_variety_multiproj  {n4:>6,} 组  -> 需人工判断是否同一材料")
    print(f"  5. subspecies_conflict     {n5:>6,} 组  -> ★ 疑似标签错误")

    if n5:
        print("\n--- ★ 亚种冲突明细（疑似标签错误，前 15）---")
        for r in [x for x in dup_rows if x["duplicate_type"] == "subspecies_conflict"][:15]:
            print(f"  {r['canonical_name'][:30]:<32} {r['note'][:40]:<42} n={r['n_samples']}")

    print("\n--- 技术重复最多的样本（同 BioSample 多 run，前 10）---")
    tb = sorted([x for x in dup_rows if x["duplicate_type"] == "same_biosample"],
                key=lambda x: -int(x["n_samples"]))[:10]
    for r in tb:
        print(f"  {r['biosamples'][:22]:<24} run 数={r['n_samples']:<5} 品种={r['canonical_name'][:26]}")

    print("\n--- ★ 单一品种占比过高的风险检查 ---")
    top = sorted(by_var.items(), key=lambda x: -len(x[1]))[:5]
    tot = len(records)
    for var, rs in top:
        print(f"  {var[:34]:<36} {len(rs):>6,} run  占可用样本 {100.0*len(rs)/tot:>5.1f}%")
    biggest = top[0][1] if top else []
    if biggest and len(biggest) / tot > 0.2:
        projs = Counter(x["BioProject"] for x in biggest)
        print(f"\n  ⚠️ 最大品种占 {100.0*len(biggest)/tot:.1f}%，来自 "
              f"{len(projs)} 个 BioProject：")
        for p, c in projs.most_common(5):
            print(f"       {p:<20} {c:>5,} run")
        print("  -> 建库时必须**限额抽样**，否则面板会被单一品种主导")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
