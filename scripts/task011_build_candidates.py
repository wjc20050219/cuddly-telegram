#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task011_build_candidates.py —— TASK-011：构建候选样本表

输入：
  data/metadata/candidates/ena_candidates_raw.tsv  （Portal API，32,564 run）
  data/metadata/candidates/sample_attrs.tsv        （样本 XML 属性，21,654 样本）

输出：
  data/metadata/candidates/candidate_samples.tsv   （候选样本表）
  data/metadata/candidates/name_quality_report.txt （品种名质量报告）

设计要点：
  1. 品种名不轻信单一字段——Portal 的 cultivar 有 51.7% 覆盖，
     且实测含 "indica"、"indica/japonica"、"LGE-Bulk - A X B" 这类非品种值。
     故采用多来源 + 分级校验，并显式记录 name_source 与 name_quality。
  2. 每个值都可追溯：name_source 标明来自 cultivar / lineage_name / title / alias。
  3. 拒绝伪造：无法确定的一律留空并标 quality=unusable，绝不猜测填充。
"""
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/mnt/d/dsh/RiceVar-ID/data/metadata/candidates")
SRC = BASE / "ena_candidates_raw.tsv"
ATTR = BASE / "sample_attrs.tsv"
DST = BASE / "candidate_samples.tsv"
REPORT = BASE / "name_quality_report.txt"

GS = 375_000_000

# ---- 非品种值的判定规则 ----
SUBPOP = {
    "indica", "japonica", "aus", "aromatic", "admixed", "temperate japonica",
    "tropical japonica", "indica/japonica", "japonica/indica", "aus/boro",
    "boro", "rayada", "ashina", "aromatic/japonica", "sadri", "basmati",
}
# INSDC 官方缺失值受控词表 —— 实测中 "not applicable" 出现 9,904 次，
# 是最常见的伪值，若不剔除会严重虚高"品种名可用率"。
MISSING_VOCAB = {
    "not applicable", "not collected", "not provided", "missing",
    "restricted access", "no data", "unknown", "n/a", "na", "none",
    "null", "unspecified", "unavailable", "not determined", "missing data",
}
PLACEHOLDER = [
    r"^plant sample from", r"^rice$", r"^oryza sativa", r"^unknown",
    r"^n/?a$", r"^none$", r"^missing$", r"^sample$", r"^dna$",
    r"^genomic dna", r"^rice dna", r"^whole genome", r"^wgs",
    r"mapping to", r"^3k rgp", r"^reference$", r"^control$", r"^wt$",
    r"^mutant$", r"^wild type$", r"^null$", r"^test$", r"^pool$",
    # ↓ 实测新增：21,654 样本中真实出现的高频伪值
    r"^cultivar$", r"^variety$", r"^rice variety$",
    r"^indica rice$", r"^japonica rice$", r"^aus rice$",
    r"^asian cultivated rice$", r"^common wild rice",
    r"^generic sample", r"^samples? from",
]
# 描述性文本：是实验/群体描述，不是品种名
DESC_PAT = [
    r"\bderived from\b", r"\bcross(?:ed|es)?\b", r"\brils?\b",
    r"\bintrogress", r"\bchromosome segment\b", r"\bfor genome assembly\b",
    r"\bgeneric sample\b", r"\bsamples? from\b", r"\bpopulation\b",
    r"\bmutant\b", r"\btransgenic\b", r"\bknockout\b", r"\boverexpress",
    r"\bsegregating\b", r"\bbackcross", r"\bdouble haploid\b",
    r"\brecombinant inbred\b", r"\bnear.isogenic\b", r"\bwild rice\b",
    r"\s[x×]\s",                    # A x B 杂交组合
    r"\bvariety\b.*\bvariety\b",    # 一句里出现两次 variety，多半是描述
    # ★ 混合样本不是品种：实测出现 "Daudzai Field Mix"
    r"\bmix\b", r"\bbulk\b", r"\bcomposite\b", r"\bmultiline\b",
]
# 纯编号/代码：1143 / 786 / X173 / N1-10-8D 等
CODEISH = [
    r"^\d+$", r"^[a-z]{1,2}\d+$", r"^\d+[-_]\d+", r"^[a-z]\d+[-_]\d+",
    r"^\d+[-_][a-z0-9]+$",
]
# 杂交组合
CROSS = [r"\s[x×]\s", r"^lge-bulk", r"\bcross\b", r"\bf\d\b", r"\bbc\d\b"]


def is_subpop(v: str) -> bool:
    return v.strip().lower() in SUBPOP


def looks_placeholder(v: str) -> bool:
    s = v.strip().lower()
    if not s or s in MISSING_VOCAB:
        return True
    return any(re.search(p, s) for p in PLACEHOLDER)


def looks_description(v: str) -> bool:
    """是否为实验/群体描述而非品种名"""
    s = v.strip().lower()
    return any(re.search(p, s) for p in DESC_PAT)


def looks_too_long(v: str) -> bool:
    """品种名一般不超过 5 个词；过长的多半是描述"""
    return len(v.strip().split()) > 5


def looks_code(v: str) -> bool:
    s = v.strip().lower()
    return any(re.match(p, s) for p in CODEISH)


def looks_cross(v: str) -> bool:
    s = v.strip().lower()
    return any(re.search(p, s) for p in CROSS)


def clean_name(v: str) -> str:
    """基础清洗：去引号、去多余空白、去尾部括号编号"""
    s = (v or "").strip().strip('"').strip("'")
    s = re.sub(r"\s+", " ", s)
    # 去掉形如 " (CRX842160)" 的数据库编号后缀
    s = re.sub(r"\s*\((?:CRX|IRGC|GSOR|W\d{3})[^)]*\)\s*$", "", s, flags=re.I)
    return s.strip()


def name_from_text(text: str) -> str:
    """从 description / alias / title 的自由文本里提取品种名"""
    if not text:
        return ""
    s = text.strip()

    # "Caravela variety rice seedling shoot..."  -> Caravela
    m = re.match(r"^([A-Z][\w\-]{1,30})\s+(?:variety|cultivar)\b", s)
    if m:
        return clean_name(m.group(1))

    # "rice_shoot_Arborio_ITQB" -> Arborio
    m = re.match(r"^rice[_-](?:shoot|leaf|root|seedling|seed|plant)[_-]"
                 r"([A-Za-z][\w\-]*?)(?:[_-][A-Z]{2,6})?$", s)
    if m:
        return clean_name(m.group(1))

    # "LIU XU::IRGC 109232-1" -> LIU XU
    if "::" in s:
        head = clean_name(s.split("::")[0])
        if head and not looks_placeholder(head) and not looks_code(head):
            return head

    # "Genomic DNA of rice cultivar X" / "variety X"
    m = re.search(r"(?:cultivar|cv\.?|variety)\s+([A-Za-z][\w\-]{1,30})", s, re.I)
    if m:
        cand = clean_name(m.group(1))
        if cand.lower() not in MISSING_VOCAB and not looks_description(cand):
            return cand

    return ""


def extract_cv(v: str) -> str:
    """从 "Oryza sativa japonica cv. Nipponbare" 这类学名串里取出品种名"""
    m = re.search(r"\bcv\.?\s+([A-Za-z][\w\-]{1,30})", v, re.I)
    return m.group(1) if m else ""


def pick_variety(cultivar_tag: str, cultivar_portal: str, lineage: str,
                 description: str, alias: str, title: str) -> tuple[str, str, str]:
    """
    返回 (variety_name, name_source, name_quality)

    name_quality 四级：
      good     干净的字母品种名
      caveat   杂交组合 / 派生长名 / 来自自由文本
      code     ★ 短字母数字编号（zh11 / ir64 / dn416 / 9311）
               **不丢弃**——实测 zh11 出现 5,349 次，是真实品种"中花 11"的缩写。
               这类交由 TASK-012（品种名称标准化）解析。
      unusable 占位符 / 缺失值 / 描述文本

    优先级依据 21,654 个样本的实测命中率：
      xml:cultivar_tag   72.4%   <- 主力字段
      portal:cultivar    51.7%   （与上者有重叠）
      xml:lineage_name    0.1%   <- 仅个别提交者习惯，非主流

    注意：字段有值 != 值是品种名。实测高频伪值：
      not applicable(9,904) / cultivar(575) / indica rice /
      allotetraploid derived from nipponbare / rils from the cross ...
    """
    cands = [
        (clean_name(cultivar_tag), "xml:cultivar_tag"),
        (clean_name(cultivar_portal), "portal:cultivar"),
        (clean_name(lineage), "xml:lineage_name"),
    ]
    for val, src in cands:
        if not val:
            continue
        val = extract_cv(val) or val
        if (is_subpop(val) or looks_placeholder(val)
                or looks_description(val) or looks_too_long(val)):
            continue
        if looks_code(val):
            return val, src, "code"      # 不丢弃，降级待解析
        q = "caveat" if (looks_cross(val) or len(val) > 40) else "good"
        return val, src, q

    # 兜底：从自由文本提取（一律降级，因不如结构化字段可靠）
    # ★ 注意：这条路径同样必须过 is_subpop——实测曾把亚种名 "aus" 当成品种名。
    for text, src in ((description, "derived:description"),
                      (alias, "derived:alias"),
                      (title, "derived:title")):
        v = name_from_text(text)
        if (v and not is_subpop(v) and not looks_placeholder(v)
                and not looks_description(v) and not looks_code(v)):
            return v, src, "caveat"
    return "", "", "unusable"


def infer_subspecies(*texts: str) -> str:
    """从 cultivar / ecotype / 文本推断亚种——只做保守推断，不猜"""
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return ""
    for key, val in [
        ("indica/japonica", "admixed"),
        ("temperate japonica", "temperate_japonica"),
        ("tropical japonica", "tropical_japonica"),
        ("japonica", "japonica"),
        ("indica", "indica"),
        ("aromatic", "aromatic"),
        ("aus", "aus"),
        ("admixed", "admixed"),
    ]:
        if key in blob:
            return val
    return ""


def infer_cultivar_or_landrace(*texts: str) -> str:
    blob = " ".join(t for t in texts if t).lower()
    if "landrace" in blob:
        return "landrace"
    if "breeding" in blob or "breed" in blob or "line" in blob:
        return "breeding_line"
    if "cultivar" in blob or "variety" in blob or "cv." in blob:
        return "cultivar"
    return ""


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 缺少 {SRC}", file=sys.stderr)
        return 1

    print("=" * 74)
    print("TASK-011：构建候选样本表")
    print("=" * 74)

    # ---- 读 Portal 元数据 ----
    with SRC.open(encoding="utf-8", errors="replace") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        rows = []
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < len(hdr):
                p += [""] * (len(hdr) - len(p))
            rows.append(dict(zip(hdr, p)))
    print(f"Portal 记录：{len(rows):,} run")

    # ---- 读样本属性 ----
    attrs: dict[str, dict[str, str]] = {}
    if ATTR.exists():
        with ATTR.open(encoding="utf-8", errors="replace") as fh:
            ah = fh.readline().rstrip("\n").split("\t")
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) < len(ah):
                    p += [""] * (len(ah) - len(p))
                d = dict(zip(ah, p))
                attrs[d.get("sample_accession", "")] = d
        print(f"样本属性   ：{len(attrs):,} 样本")
    else:
        print(f"[WARN] 未找到 {ATTR}，仅用 Portal 字段", file=sys.stderr)

    # ---- 组装 ----
    out = []
    q_counter: Counter[str] = Counter()
    src_counter: Counter[str] = Counter()
    for r in rows:
        sacc = r.get("sample_accession", "")
        a = attrs.get(sacc, {})

        vname, vsrc, vqual = pick_variety(
            a.get("cultivar_tag", ""), r.get("cultivar", ""),
            a.get("lineage_name", ""), a.get("description", ""),
            r.get("sample_alias", ""), r.get("sample_title", ""),
        )
        q_counter[vqual] += 1
        src_counter[vsrc or "(none)"] += 1

        try:
            bases = int(r.get("base_count") or 0)
        except ValueError:
            bases = 0
        try:
            reads = int(r.get("read_count") or 0)
        except ValueError:
            reads = 0
        depth = round(bases / GS, 3) if bases else 0.0
        rlen = round(bases / reads, 1) if reads else 0.0

        run = r.get("run_accession", "")
        pref = run[:3]
        srca = run if pref == "SRR" else ""
        enaa = run if pref in ("ERR", "DRR") else ""

        out.append({
            "sample_id": run,
            "variety_name": vname,
            "variety_alias": "|".join(filter(None, [
                clean_name(a.get("cultivar_tag", "")) if clean_name(a.get("cultivar_tag", "")) != vname else "",
                clean_name(r.get("cultivar", "")) if clean_name(r.get("cultivar", "")) != vname else "",
                clean_name(a.get("lineage_name", "")) if clean_name(a.get("lineage_name", "")) != vname else "",
            ])),
            "species": r.get("scientific_name", ""),
            "subspecies": infer_subspecies(
                r.get("cultivar", ""), r.get("ecotype", ""),
                a.get("lineage_name", ""), a.get("description", ""), r.get("sample_title", "")),
            "accession": run,
            "BioProject": r.get("study_accession", ""),
            "BioSample": sacc,
            "SRA_accession": srca,
            "ENA_accession": enaa,
            "publication": "",
            "country": r.get("country", "") or a.get("xml_country", ""),
            "population": a.get("lineage_rank", ""),
            "cultivar_or_landrace": infer_cultivar_or_landrace(
                r.get("cultivar", ""), a.get("description", ""), r.get("sample_title", "")),
            "sequencing_platform": r.get("instrument_platform", ""),
            "read_length": rlen,
            "paired_or_single": r.get("library_layout", ""),
            "estimated_depth": depth,
            "reference_genome": "IRGSP-1.0",
            "data_source": "ENA Portal API + ENA sample XML",
            "download_status": "not_downloaded",
            "qc_status": "pending",
            # ---- 附加可追溯字段 ----
            "name_source": vsrc,
            "name_quality": vqual,
            "source_db": {"SRR": "NCBI_SRA", "ERR": "ENA", "DRR": "DDBJ"}.get(pref, "unknown"),
            "instrument_model": r.get("instrument_model", ""),
            "base_count": bases,
            "fastq_ftp": r.get("fastq_ftp", ""),
            "fastq_bytes": r.get("fastq_bytes", ""),
            "sample_title": r.get("sample_title", ""),
            "study_title": r.get("study_title", ""),
            "sample_alias": r.get("sample_alias", ""),
            "center_name": r.get("center_name", ""),
            "first_public": r.get("first_public", ""),
        })

    cols = list(out[0].keys())
    with DST.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in out:
            fh.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
    print(f"\n已写出：{DST}（{len(out):,} 行 × {len(cols)} 列）\n")

    # ---- 质量报告 ----
    lines = []
    def w(s: str = "") -> None:
        print(s)
        lines.append(s)

    w("--- ★ 品种名质量分级 ---")
    tot = len(out)
    for k in ["good", "caveat", "code", "unusable"]:
        n = q_counter[k]
        w(f"  {k:<10} {n:>7,}/{tot:,}  {100.0*n/tot:>5.1f}%  {'█'*int(100.0*n/tot/3)}")
    w("  （code = 短字母数字编号，多为真实品种缩写，待 TASK-012 解析）")

    w("\n--- 品种名来源 ---")
    for k, v in src_counter.most_common():
        w(f"  {k:<28} {v:>7,}  {100.0*v/tot:>5.1f}%")

    w("\n--- 可用于建库的样本 ---")
    strict = [r for r in out if r["name_quality"] in ("good", "caveat")]
    usable = [r for r in out if r["name_quality"] in ("good", "caveat", "code")]
    w(f"  严格的（good+caveat，名字直接可用）  ：{len(strict):,} 条 run")
    w(f"  含编号类（+code，需 TASK-012 解析）  ：{len(usable):,} 条 run")

    # 按品种去重后有多少品种
    vmap: dict[str, list] = {}
    for r in usable:
        vmap.setdefault(r["variety_name"].lower(), []).append(r)
    w(f"  去重后品种数：{len(vmap):,}")

    w("\n--- 品种出现次数 Top 30（可用于评估重复度）---")
    for k, v in sorted(vmap.items(), key=lambda x: -len(x[1]))[:30]:
        runs = len(v)
        best = max(x["estimated_depth"] for x in v)
        w(f"  {k[:38]:<40} run={runs:<5} 最高深度={best:.1f}x")

    w("\n--- 每个品种只出现 1 次的品种数 ---")
    singles = sum(1 for v in vmap.values() if len(v) == 1)
    w(f"  {singles:,} / {len(vmap):,}  ({100.0*singles/len(vmap):.1f}%)")
    w("  ^ 单样本品种无法做「同品种不同深度」的稳定性检验，建库时需注意")

    w("\n--- 深度 ≥10× 且品种名可用的样本 ---")
    good10 = [r for r in usable if r["estimated_depth"] >= 10]
    w(f"  {len(good10):,} 条 run，覆盖 {len({r['variety_name'].lower() for r in good10}):,} 个品种")

    w("\n--- 亚种分布（good/caveat 样本）---")
    sub = Counter(r["subspecies"] or "(未标注)" for r in usable)
    for k, v in sub.most_common(10):
        w(f"  {k:<24} {v:>7,}")

    w("\n--- 来源库分布（good/caveat 样本）---")
    for k, v in Counter(r["source_db"] for r in usable).most_common():
        w(f"  {k:<12} {v:>7,}")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n质量报告：{REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
