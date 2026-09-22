#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task011_name_diagnostics.py —— 诊断品种名被拒的原因（TASK-011 质量分析）

目的：7,848/32,564 可用（24%）这个数字需要解释——
      是数据本身没有品种名，还是校验规则过严？
      本脚本逐条归类拒绝原因，并列出高频被拒原始值。
"""
import importlib.util
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
BUILDER = Path("/mnt/d/dsh/RiceVar-ID/scripts/task011_build_candidates.py")

# 导入构建脚本里的校验函数（其 main 有 __main__ 保护，导入安全）
spec = importlib.util.spec_from_file_location("builder", BUILDER)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def reason(val: str) -> str:
    if not val:
        return "空值（字段无内容）"
    if val.strip().lower() in b.MISSING_VOCAB:
        return "INSDC 缺失值词表（not applicable 等）"
    if b.is_subpop(val):
        return "亚种名而非品种名（indica/japonica…）"
    if b.looks_placeholder(val):
        return "占位/无信息值"
    if b.looks_code(val):
        return "纯编号/代码"
    if b.looks_description(val):
        return "实验/群体描述"
    if b.looks_too_long(val):
        return "词数过多（>5）"
    return "其他"


def main() -> int:
    src = BASE / "ena_candidates_raw.tsv"
    attr = BASE / "sample_attrs.tsv"

    with src.open(encoding="utf-8", errors="replace") as fh:
        h = fh.readline().rstrip("\n").split("\t")
        runs = []
        for line in fh:
            p = line.rstrip("\n").split("\t")
            p += [""] * (len(h) - len(p))
            runs.append(dict(zip(h, p)))

    attrs = {}
    with attr.open(encoding="utf-8", errors="replace") as fh:
        ah = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            p = line.rstrip("\n").split("\t")
            p += [""] * (len(ah) - len(p))
            d = dict(zip(ah, p))
            attrs[d["sample_accession"]] = d

    print("=" * 74)
    print("TASK-011 品种名质量诊断")
    print("=" * 74)
    print(f"总 run：{len(runs):,}\n")

    reasons = Counter()
    rejected_vals = Counter()
    no_field = 0

    for r in runs:
        a = attrs.get(r.get("sample_accession", ""), {})
        ct = b.clean_name(a.get("cultivar_tag", ""))
        cp = b.clean_name(r.get("cultivar", ""))
        ln = b.clean_name(a.get("lineage_name", ""))

        if not (ct or cp or ln):
            no_field += 1
            reasons["★ 三个结构化字段全为空"] += 1
            continue

        # 逐个字段判断：只要有一个通过就算可用
        ok = False
        first_reason = None
        for v in (ct, cp, ln):
            if not v:
                continue
            if not (b.is_subpop(v) or b.looks_placeholder(v) or b.looks_code(v)
                    or b.looks_description(v) or b.looks_too_long(v)):
                ok = True
                break
            if first_reason is None:
                first_reason = reason(v)
                rejected_vals[v.lower()] += 1
        if not ok:
            reasons[first_reason or "其他"] += 1

    tot = len(runs)
    print("--- 被拒原因分布 ---")
    for k, v in reasons.most_common():
        print(f"  {k:<38} {v:>7,}  {100.0*v/tot:>5.1f}%")

    print(f"\n--- 被拒的高频原始值 Top 25 ---")
    for k, v in rejected_vals.most_common(25):
        print(f"  {v:>6}  {k[:66]}")

    print("\n--- 判定 ---")
    empty_pct = 100.0 * reasons["★ 三个结构化字段全为空"] / tot
    vocab_pct = 100.0 * reasons["INSDC 缺失值词表（not applicable 等）"] / tot
    print(f"  结构化字段全空        ：{empty_pct:.1f}%  <- 数据本身没有，无法改善")
    print(f"  填了 INSDC 缺失值     ：{vocab_pct:.1f}%  <- 提交者明确表示「无此项」，无法改善")
    print(f"  合计不可改善          ：{empty_pct + vocab_pct:.1f}%")
    print(f"  其余为可讨论的过滤边界：{100.0 - empty_pct - vocab_pct:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
