#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task012_variety_alias.py —— TASK-012：品种名称标准化

输入：data/metadata/candidates/candidate_samples.tsv（TASK-011 产出）
输出：
  data/metadata/candidates/variety_alias.tsv      品种名 → 规范名 映射
  data/metadata/candidates/variety_canonical.tsv  规范品种表（含样本数/深度）
  data/metadata/candidates/unresolved_names.txt   无法解析的名称（待人工核对）

诚实性声明（重要）：
  本脚本做两类归并，**证据强度不同，必须分开标注**：
    1. mechanical —— 机械规范化（大小写/空格/连字符/括号），
       证据是"规范化后字符串相同"，客观可验证。
    2. curated —— 人工整理的已知同义词（如 ZH11 = Zhonghua 11），
       依据是**公开常识与文献惯用**，不是从数据推导出来的。
       这类一律标注 evidence=curated_common_usage，可被人工复核推翻。
  ★ 绝不把"看起来像"的两个名字合并。无法确定的留在 unresolved 里等人看。
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = BASE / "candidate_samples.tsv"
DST_ALIAS = BASE / "variety_alias.tsv"
DST_CANON = BASE / "variety_canonical.tsv"
DST_UNRES = BASE / "unresolved_names.txt"

# ---------------------------------------------------------------------------
# 人工整理的已知同义词表
# 依据：水稻研究领域的公开惯用缩写。仅收录**高置信度**条目。
# key = 规范化键（小写、去非字母数字），value = 规范名
# ---------------------------------------------------------------------------
CURATED: dict[str, str] = {
    # 中花 11
    "zh11": "Zhonghua 11", "zhonghua11": "Zhonghua 11",
    # 日本晴
    "npb": "Nipponbare", "nip": "Nipponbare", "nipponbare": "Nipponbare",
    # 93-11
    "9311": "93-11",
    # 明恢 63
    "mh63": "Minghui 63", "minghui63": "Minghui 63",
    # 台中在来 1 号
    "tn1": "Taichung Native 1", "taichungnative1": "Taichung Native 1",
    # IR64
    "ir64": "IR64", "irri64": "IR64",
    # 广占 63S / 常用两系不育系
    "y58s": "Y58S",
    # 空育 / 滇型等暂不合并
    "dg1": "DG1",
    "sk1": "SK1",
    # 中籼 9311 已在上
    "huanghuazhan": "Huanghuazhan",
    "hhz": "Huanghuazhan",
    # 桂朝 2 号等常见材料暂不臆测
}
# 只做"大小写/空格/连字符"这类机械归一时，规范名取"出现次数最多的原始写法"


def norm_key(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"\(.*?\)", "", s)          # 去括号内容 "(IRRI)"
    s = re.sub(r"[^a-z0-9]+", "", s)       # 去所有非字母数字
    return s


def is_code_like(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z]{0,4}\d+[a-z]?", norm_key(name)))


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 缺少 {SRC}（先跑 TASK-011）", file=sys.stderr)
        return 1

    print("=" * 74)
    print("TASK-012：品种名称标准化")
    print("=" * 74)

    with SRC.open(encoding="utf-8", errors="replace") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        rows = []
        for line in fh:
            p = line.rstrip("\n").split("\t")
            p += [""] * (len(hdr) - len(p))
            rows.append(dict(zip(hdr, p)))

    usable = [r for r in rows if r["name_quality"] in ("good", "caveat", "code")]
    print(f"候选 run 总数     ：{len(rows):,}")
    print(f"品种名可用 run 数 ：{len(usable):,}\n")

    # ---- 统计每个原始写法 ----
    raw_count: Counter[str] = Counter()
    for r in usable:
        raw_count[r["variety_name"].strip()] += 1
    print(f"不同原始写法：{len(raw_count):,}\n")

    # ---- 分组 ----
    groups: dict[str, list[str]] = defaultdict(list)
    for name in raw_count:
        groups[norm_key(name)].append(name)

    alias_rows: list[dict[str, str]] = []
    canon_stats: dict[str, dict] = {}

    for key, names in groups.items():
        names_sorted = sorted(names, key=lambda n: (-raw_count[n], n))
        total = sum(raw_count[n] for n in names_sorted)

        if key in CURATED:
            canon = CURATED[key]
            relation_base = "abbreviation" if len(names_sorted) > 1 else "curated_synonym"
            evidence = "curated_common_usage"
        else:
            # 机械归一：规范名取出现最多的写法（若无并列，天然唯一）
            canon = names_sorted[0]
            relation_base = "mechanical"
            evidence = "mechanical_normalization"

        for n in names_sorted:
            if n == canon:
                rel = "canonical"
            elif relation_base == "mechanical":
                rel = "spelling_variant"
            else:
                rel = "abbreviation"
            alias_rows.append({
                "canonical_name": canon,
                "alias": n,
                "relation": rel,
                "evidence": evidence,
                "n_runs": str(raw_count[n]),
                "norm_key": key,
            })

        # ★ 注意：多个 norm_key 可能映射到同一规范名（如 zh11 与 zhonghua11
        #   都映射到 Zhonghua 11），此处必须**累加**而非覆盖。
        if canon in canon_stats:
            s = canon_stats[canon]
            s["n_runs"] += total
            s["n_spellings"] += len(names_sorted)
            s["spellings"] = s["spellings"] + "|" + "|".join(names_sorted)
            if evidence == "curated_common_usage":
                s["evidence"] = "curated_common_usage"
        else:
            canon_stats[canon] = {
                "canonical_name": canon, "norm_key": key,
                "n_runs": total, "n_spellings": len(names_sorted),
                "spellings": "|".join(names_sorted),
                "evidence": evidence,
                "is_code_like": "yes" if is_code_like(canon) else "no",
            }

    # ---- 输出 alias 表 ----
    cols = ["canonical_name", "alias", "relation", "evidence", "n_runs", "norm_key"]
    with DST_ALIAS.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in sorted(alias_rows, key=lambda x: (-int(x["n_runs"]), x["alias"])):
            fh.write("\t".join(r[c] for c in cols) + "\n")
    print(f"已写出：{DST_ALIAS}（{len(alias_rows):,} 行）")

    # ---- 输出规范品种表 ----
    ccols = ["canonical_name", "norm_key", "n_runs", "n_spellings",
             "spellings", "evidence", "is_code_like"]
    stats_sorted = sorted(canon_stats.values(), key=lambda x: -x["n_runs"])
    with DST_CANON.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(ccols) + "\n")
        for r in stats_sorted:
            fh.write("\t".join(str(r[c]) for c in ccols) + "\n")
    print(f"已写出：{DST_CANON}（{len(stats_sorted):,} 个规范品种）\n")

    # ---- 未解析名称 ----
    unresolved = [r for r in stats_sorted if r["is_code_like"] == "yes"
                  and r["canonical_name"] == r["norm_key"]]
    with DST_UNRES.open("w", encoding="utf-8") as fh:
        fh.write("# 疑似编号型品种名，无法自动解析为规范名，待人工核对\n")
        fh.write("# 格式：规范化键<TAB>n_runs<TAB>原始写法\n")
        for r in unresolved:
            fh.write(f"{r['norm_key']}\t{r['n_runs']}\t{r['spellings']}\n")
    print(f"已写出：{DST_UNRES}（{len(unresolved):,} 个待核对）\n")

    # ---- 报告 ----
    print("--- 归并概况 ---")
    multi = [r for r in stats_sorted if r["n_spellings"] > 1]
    print(f"  原始写法          ：{len(raw_count):,}")
    print(f"  规范品种          ：{len(stats_sorted):,}")
    print(f"  发生归并的品种    ：{len(multi):,}")
    print(f"  其中 curated 归并 ：{sum(1 for r in stats_sorted if r['evidence']=='curated_common_usage' and r['n_spellings']>1):,}")

    print("\n--- ★ 归并明细（多种写法合一，前 20）---")
    for r in sorted(multi, key=lambda x: -x["n_runs"])[:20]:
        tag = "curated" if r["evidence"] == "curated_common_usage" else "mechanical"
        print(f"  {r['canonical_name'][:26]:<28} run={r['n_runs']:<6} [{tag}]")
        print(f"      ← {r['spellings'][:88]}")

    print("\n--- 样本数 Top 20 规范品种 ---")
    for r in stats_sorted[:20]:
        print(f"  {r['canonical_name'][:34]:<36} run={r['n_runs']:<6} 写法数={r['n_spellings']}")

    print("\n--- ★ 每个品种的 run 数分布（决定能否做重复性检验）---")
    dist = Counter()
    for r in stats_sorted:
        n = r["n_runs"]
        dist["1"] += n == 1
        dist["2-3"] += 2 <= n <= 3
        dist["4-9"] += 4 <= n <= 9
        dist[">=10"] += n >= 10
    for k in ["1", "2-3", "4-9", ">=10"]:
        v = dist[k]
        print(f"  {k:<6} 个品种：{v:>6,}  占 {100.0*v/len(stats_sorted):>5.1f}%")
    n_multi = len(stats_sorted) - dist["1"]
    print(f"\n  有 ≥2 个 run 的品种：{n_multi:,}")
    print("  ^ 只有这些能做「同品种跨测序 run」的指纹稳定性检验")
    print("    单 run 品种只能做「同一样本不同降采样」的检验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
