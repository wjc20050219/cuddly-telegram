#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task014_panels.py —— TASK-014：建立 Pilot Panel 与独立测试集

输入：
  data/metadata/candidates/candidate_samples.tsv （TASK-011）
  data/metadata/candidates/variety_alias.tsv     （TASK-012）
  data/metadata/candidates/duplicate_samples.tsv （TASK-013）
输出：
  data/metadata/candidates/pilot_panel.tsv
  data/metadata/candidates/independent_test_panel.tsv
  data/metadata/candidates/panel_selection_log.txt

设计原则（对应任务书第十二节与第二十八节）：
  1. ★ 独立测试集**现在冻结**，用固定随机种子选出，**不得在看过结果后重选**。
  2. 一个 BioSample 只取一个 run（避免技术重复造成权重失衡）。
  3. ★ 排除 EMS 突变体库——突变体不是原品种，混入会造成标签错误。
  4. 深度优先：要降采样到 0.01×，原始深度越高越好。
  5. 亚种分层：indica / japonica / aus / aromatic 都要有，否则无法回答 Q6。
  6. Pilot 与测试集品种**完全不重叠**。
"""
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = BASE / "candidate_samples.tsv"
ALIAS = BASE / "variety_alias.tsv"
PILOT = BASE / "pilot_panel.tsv"
TEST = BASE / "independent_test_panel.tsv"
LOG = BASE / "panel_selection_log.txt"

SEED = 20260920          # ★ 固定种子，写入日志以便复现
N_PILOT = 30
N_TEST = 25
# ★ 深度区间而非"越深越好"：目标实验最高只到 1×，
#   源数据 20–50× 已足够降采样，再深只是白付存储费。
#   实测按降序取最深的会给 55 份样本带来 1,662 GiB，不可接受。
MIN_DEPTH = 20.0
MAX_DEPTH = 50.0
MAX_PER_PROJECT = 3      # 单个 BioProject 限额，防止面板被单一项目主导

# ★ 仅用短读平台：长读（PacBio/ONT）降采样后的覆盖统计与短读完全不同，
#   混入小规模 Pilot 会引入平台偏倚。平台间比较应作为独立实验后做。
ALLOWED_PLATFORMS = {"ILLUMINA", "DNBSEQ", "BGISEQ"}

# ★ 显式亚种配额（对应任务书 Q6：必须能回答近缘/亚种区分问题）
#   若按候选池比例分配，"unknown"会占 19/30，无法评价亚种区分能力。
QUOTA_PILOT = {"indica": 8, "japonica": 8, "aus": 4, "aromatic": 3,
               "temperate_japonica": 2, "admixed": 1, "unknown": 4}
QUOTA_TEST = {"indica": 6, "japonica": 6, "aus": 3, "aromatic": 3,
              "temperate_japonica": 2, "admixed": 1, "unknown": 4}

# ★ EMS/突变体/转基因等"非原品种"的关键词——这些材料的基因组已改变
MUTANT_PAT = [
    r"\bems\b", r"\bems\d+", r"\bmutant\b", r"\bmutagen", r"\birradiat",
    r"\btransgenic\b", r"\bknockout\b", r"\bko\b", r"\bcrispr\b",
    r"\btilling\b", r"\bactivation tag", r"\binsertional\b",
    r"\boverexpress", r"\brnai\b", r"\bantisense\b",
]
# "B1674 (CRX...)" 这类突变体株系编号：单个大写字母+4位数字
LINE_CODE_PAT = r"^[a-z]\d{4}\b"


def fdepth(rec: dict) -> float:
    try:
        return float(rec.get("estimated_depth", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def fbytes(rec: dict) -> int:
    """fastq_bytes 可能是 '1234;5678' 形式，取和"""
    s = str(rec.get("fastq_bytes", "") or "")
    tot = 0
    for part in s.replace(",", "").split(";"):
        part = part.strip()
        if part.isdigit():
            tot += int(part)
    return tot


def is_mutant_context(rec: dict) -> bool:
    """
    判断样本是否来自突变体/转基因材料。

    ★ 关键：不能只看样本标题。实测 "rice ZH11 ems4611 database" 这个 EMS 突变体库
      有 5,344 个 run，其样本标题形如 "B1674 (CRX842160)"（株系编号），
      单看标题容易漏判；必须结合 study_title（BioProject 的研究名称）。
    """
    import re
    blob = " ".join([
        rec.get("sample_title", ""), rec.get("sample_alias", ""),
        rec.get("study_title", ""), rec.get("BioProject", ""),
    ]).lower()
    if any(re.search(p, blob) for p in MUTANT_PAT):
        return True
    # 株系编号形态（如 "b1674"、"a1065"）
    t = rec.get("sample_title", "").strip().lower()
    if re.match(LINE_CODE_PAT, t):
        return True
    return False


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 缺少 {SRC}", file=sys.stderr)
        return 1

    random.seed(SEED)
    log: list[str] = []

    def w(s: str = "") -> None:
        print(s)
        log.append(s)

    w("=" * 74)
    w("TASK-014：建立 Pilot Panel 与独立测试集")
    w("=" * 74)
    w(f"随机种子：{SEED}（固定，用于复现）")
    w(f"目标规模：Pilot {N_PILOT} 份 / 独立测试集 {N_TEST} 份")

    with SRC.open(encoding="utf-8", errors="replace") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        rows = []
        for line in fh:
            p = line.rstrip("\n").split("\t")
            p += [""] * (len(hdr) - len(p))
            rows.append(dict(zip(hdr, p)))

    alias_map: dict[str, str] = {}
    if ALIAS.exists():
        with ALIAS.open(encoding="utf-8", errors="replace") as fh:
            ah = fh.readline().rstrip("\n").split("\t")
            ai, ci = ah.index("alias"), ah.index("canonical_name")
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) > max(ai, ci):
                    alias_map[p[ai]] = p[ci]

    for r in rows:
        r["canonical"] = alias_map.get(r["variety_name"].strip(),
                                       r["variety_name"].strip())

    # ---- 筛选 ----
    steps = []
    cur = [r for r in rows if r["name_quality"] in ("good", "caveat", "code")]
    steps.append(("品种名可用", len(cur)))

    cur = [r for r in cur if not is_mutant_context(r)]
    steps.append(("排除突变体/转基因材料", len(cur)))

    n_long = sum(1 for r in cur if r["sequencing_platform"] not in ALLOWED_PLATFORMS)
    cur = [r for r in cur if r["sequencing_platform"] in ALLOWED_PLATFORMS]
    steps.append((f"仅短读平台（剔除 {n_long} 个长读）", len(cur)))

    cur = [r for r in cur if MIN_DEPTH <= fdepth(r) <= MAX_DEPTH]
    steps.append((f"深度 {MIN_DEPTH:.0f}–{MAX_DEPTH:.0f}×", len(cur)))

    # 一个 BioSample 一个 run：取深度最高的
    best: dict[str, dict] = {}
    for r in cur:
        s = r["BioSample"]
        if s not in best or fdepth(r) > fdepth(best[s]):
            best[s] = r
    cur = list(best.values())
    steps.append(("每 BioSample 仅取 1 run", len(cur)))

    # 每品种只保留深度最高的 run（品种内去冗余；重复性检验另有材料）
    bv: dict[str, dict] = {}
    for r in cur:
        v = r["canonical"]
        if v not in bv or fdepth(r) > fdepth(bv[v]):
            bv[v] = r
    cur = list(bv.values())
    steps.append(("每品种仅取 1 run", len(cur)))

    w("\n--- 筛选过程 ---")
    prev = None
    for name, n in steps:
        delta = f"  (-{prev-n:,})" if prev is not None and prev > n else ""
        w(f"  {name:<30} {n:>7,}{delta}")
        prev = n

    # ---- 亚种分层 ----
    w("\n--- 候选池的亚种构成 ---")
    strata: dict[str, list] = defaultdict(list)
    for r in cur:
        strata[r["subspecies"] or "unknown"].append(r)
    for k, v in sorted(strata.items(), key=lambda x: -len(x[1])):
        w(f"  {k:<22} {len(v):>7,}")

    # ---- 抽样（显式亚种配额 + 项目限额 + 取够用即可的最省样本）----
    def pick(quota_spec: dict, target_n: int, used_proj: Counter,
             used_var: set, used_proj_cap: int) -> list:
        """
        两阶段抽样：

        阶段 1 —— 按**显式亚种配额**取，保证 indica/japonica/aus/aromatic 等
                  关键亚种都有代表（否则无法回答任务书 Q6 的近缘区分问题）。
        阶段 2 —— 若配额未填满目标规模，从**全部剩余候选**（主要是 unknown）
                  补足到 target_n。这些样本的亚种由后续群体结构分析判定，
                  不在此处臆测。

        亚种内按深度**升序**取——目标实验最高只模拟到 1×，
        20× 与 200× 可用性相同，但后者存储开销是前者的 10 倍。
        """
        out: list = []
        taken: set = set()

        def take(cand) -> bool:
            if cand["canonical"] in used_var or cand["sample_id"] in taken:
                return False
            if used_proj[cand["BioProject"]] >= used_proj_cap:
                return False
            out.append(cand)
            taken.add(cand["sample_id"])
            used_var.add(cand["canonical"])
            used_proj[cand["BioProject"]] += 1
            return True

        for sub, want in sorted(quota_spec.items(), key=lambda x: -x[1]):
            pool = [r for r in strata.get(sub, []) if r["sample_id"] not in taken]
            if not pool:
                w(f"  [提示] 亚种 {sub} 无候选")
                continue
            pool.sort(key=lambda r: fdepth(r))
            window = pool[:max(want * 3, want)]
            rest = pool[len(window):]
            random.shuffle(window)
            got = 0
            for cand in list(window) + rest:
                if got >= want:
                    break
                if take(cand):
                    got += 1
            if got < want:
                w(f"  [提示] 亚种 {sub} 配额 {want} 未满，实得 {got}（候选池不足）")

        # 阶段 2：补足目标规模
        if len(out) < target_n:
            filler = [r for r in cur if r["sample_id"] not in taken]
            filler.sort(key=lambda r: fdepth(r))
            random.shuffle(filler[:max((target_n - len(out)) * 3, 1)])
            for cand in filler:
                if len(out) >= target_n:
                    break
                take(cand)
            w(f"  [补足] 从剩余候选补到 {len(out)} 份（目标 {target_n}）")
        return out

    used_proj: Counter = Counter()
    used_var: set = set()
    pilot = pick(QUOTA_PILOT, N_PILOT, used_proj, used_var, MAX_PER_PROJECT)
    test = pick(QUOTA_TEST, N_TEST, used_proj, used_var, MAX_PER_PROJECT)

    # ---- 校验：两个面板品种不重叠 ----
    pv = {r["canonical"] for r in pilot}
    tv = {r["canonical"] for r in test}
    overlap = pv & tv

    w(f"\n--- 面板构建结果 ---")
    w(f"  Pilot          ：{len(pilot)} 份")
    w(f"  独立测试集     ：{len(test)} 份")
    w(f"  品种重叠       ：{len(overlap)} 个 {'✅ 无重叠' if not overlap else '❌ ' + str(overlap)}")

    def summarize(panel: list, name: str) -> None:
        if not panel:
            return
        w(f"\n--- {name} 构成 ---")
        w(f"  亚种：{dict(Counter(r['subspecies'] or 'unknown' for r in panel))}")
        w(f"  平台：{dict(Counter(r['sequencing_platform'] for r in panel))}")
        w(f"  来源：{dict(Counter(r['source_db'] for r in panel))}")
        d = [fdepth(r) for r in panel]
        w(f"  深度：min={min(d):.1f}× median={sorted(d)[len(d)//2]:.1f}× max={max(d):.1f}×")
        tb = sum(fbytes(r) for r in panel)
        w(f"  FASTQ 总字节：{tb:,} B = {tb/1024**3:.2f} GiB")
        w(f"  BioProject 数：{len({r['BioProject'] for r in panel})}")

    summarize(pilot, "Pilot Panel")
    summarize(test, "独立测试集")

    tot_bytes = sum(fbytes(r) for r in pilot + test)
    tot_depth = sum(fdepth(r) for r in pilot + test)
    w(f"\n--- ★ 下载与存储估算（基于真实 fastq_bytes，非理论推算）---")
    w(f"  两面板合计 FASTQ：{tot_bytes:,} B = {tot_bytes/1024**3:.2f} GiB")
    w(f"  合计测序深度     ：{tot_depth:.0f}×  （{len(pilot)+len(test)} 份样本）")
    w(f"  推算 100 份规模  ：约 {tot_bytes/1024**3/(len(pilot)+len(test))*100:.0f} GiB")
    w(f"  推算 500 份规模  ：约 {tot_bytes/1024**3/(len(pilot)+len(test))*500:.0f} GiB")

    # ---- 写文件 ----
    cols = ["sample_id", "canonical_name", "variety_name", "subspecies",
            "accession", "BioProject", "BioSample", "SRA_accession",
            "ENA_accession", "country", "sequencing_platform",
            "paired_or_single", "estimated_depth", "read_length",
            "reference_genome", "fastq_ftp", "fastq_bytes",
            "source_db", "name_quality", "panel_role"]
    for path, panel, role in ((PILOT, pilot, "pilot"),
                              (TEST, test, "independent_test")):
        with path.open("w", encoding="utf-8", newline="") as fh:
            fh.write("\t".join(cols) + "\n")
            for r in sorted(panel, key=lambda x: -fdepth(x)):
                fh.write("\t".join(
                    [str(r.get("sample_id", "")), r["canonical"],
                     r["variety_name"], r["subspecies"], r["accession"],
                     r["BioProject"], r["BioSample"], r["SRA_accession"],
                     r["ENA_accession"], r["country"], r["sequencing_platform"],
                     r["paired_or_single"], r["estimated_depth"], r["read_length"],
                     r["reference_genome"], r["fastq_ftp"], r["fastq_bytes"],
                     r["source_db"], r["name_quality"], role]) + "\n")
        w(f"\n已写出：{path}（{len(panel)} 行）")

    w(f"\n★ 独立测试集自本文件生成之时起冻结，后续不得根据结果重选。")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"\n选择日志：{LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
