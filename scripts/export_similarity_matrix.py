#!/usr/bin/env python
"""导出版本级两两相似度全矩阵（TASK-037 相似度热图 / TASK-036 PCA 的前置）。

`FingerprintDatabase.compare_varieties` 早已实现且经证伪审查修正（曾把
`method` 参数当装饰），但它只在 Streamlit 页面里被调用，没有命令行出口，
因此论文需要的"品种 × 品种"全矩阵一直无法产出——`per_query.tsv` 只记录每条
查询的最佳匹配，没有全矩阵就画不了热图，也无法做 PCA。

本脚本把该矩阵导出为长表和方阵两个文件：

    python scripts/export_similarity_matrix.py \
        --database database/ricevar_id.sqlite \
        --method ibs --marker-set 2000 \
        --out data/processed/similarity/pilot_pairwise_ibs.tsv

输出：
  * ``<out>``               长表：variety_a, variety_b, method, mean_similarity,
                            n_pairs_compared, n_pairs_total, n_compared_markers,
                            n_different_markers, min_compared, note
  * ``<out 去后缀>_matrix.tsv``  方阵：首列 variety，其余列为品种名，单元格为相似度
  * ``<out 去后缀>_summary.json`` 参数与统计（含被跳过的品种对，便于溯源）

严格约束：
  * 相似度不足（比较位点 < ``--min-compared``）时写空单元格并在长表 ``note``
    中说明，**绝不**用 0 或 1 填充——那会把"无法比较"伪装成"不相似"。
  * 只有真实数据库中有真实基因型时才产出行；空库直接报错退出。
  * 全程使用与 ``identify()`` 相同的 ``fingerprint`` 实现，保证两处同尺度。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id import fingerprint as fp  # noqa: E402
from ricevar_id.dbquery import FingerprintDatabase  # noqa: E402

METHODS = {"ibs": fp.ibs_similarity, "hamming": fp.hamming_similarity,
           "jaccard": fp.binary_jaccard}

LONG_FIELDS = ["variety_a", "variety_b", "method", "mean_similarity",
               "n_pairs_compared", "n_pairs_total", "n_compared_markers",
               "n_different_markers", "min_compared", "note"]


def format_cell(value):
    """Write floats with fixed precision; leave unusable comparisons empty."""
    if value is None:
        return ""
    return "%.6f" % float(value)


def pairwise(database, variety_a, variety_b, method="ibs", min_compared=50):
    """Same semantics as compare_varieties but without the per-pair Python loop.

    compare_varieties issues one fingerprint call per sample pair; for a full
    matrix that is O(V^2) calls each rebuilding nothing but still paying
    function overhead. Scoring every sample of B against every sample of A in a
    single vectorized call is equivalent (the similarity functions already loop
    over references internally) and keeps the whole export to O(V^2) cheap calls.
    """
    similarity_of = METHODS[method]
    samples_a = [row[0] for row in database.samples_of(variety_a)]
    samples_b = [row[0] for row in database.samples_of(variety_b)]
    if not samples_a or not samples_b:
        raise KeyError("未知品种: %s" % (variety_a if not samples_a else variety_b))

    reference = database.reference_matrix()
    index = {sample: i for i, sample in enumerate(reference.samples)}
    rows_a = [reference.rows[index[s]] for s in samples_a]
    rows_b = [reference.rows[index[s]] for s in samples_b]

    scores = []
    compared_union = 0
    different_union = 0
    for row_a in rows_a:
        # All of variety B scored against this one sample of A in a single call.
        sims, counts = similarity_of(row_a, rows_b, min_compared=min_compared)
        for row_b, sim, count in zip(rows_b, sims, counts):
            if sim != sim:  # NaN -> too few compared markers
                continue
            scores.append(float(sim))
            compared_union += int(count)
            different_union += sum(1 for x, y in zip(row_a, row_b)
                                   if x >= 0 and y >= 0 and x != y)

    return {
        "variety_a": variety_a,
        "variety_b": variety_b,
        "method": method,
        "n_pairs_compared": len(scores),
        "n_pairs_total": len(rows_a) * len(rows_b),
        "n_compared_markers": compared_union,
        "n_different_markers": different_union,
        "mean_similarity": (sum(scores) / len(scores)) if scores else None,
        "min_compared": min_compared,
        "note": None if scores else "样本对比较位点均少于 %d，未给出相似度" % min_compared,
    }


def write_long_table(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\t".join(LONG_FIELDS) + "\n")
        for row in rows:
            fields = []
            for name in LONG_FIELDS:
                value = row.get(name)
                if name == "mean_similarity":
                    fields.append(format_cell(value))
                elif value is None:
                    fields.append("")
                else:
                    fields.append(str(value))
            handle.write("\t".join(fields) + "\n")


def write_square_matrix(varieties, lookup, path):
    """Square matrix with a header row so it can be read back by name.

    Cells come straight from ``lookup``; a variety pair whose comparison was
    unusable (too few shared markers) stays blank rather than becoming 0.0,
    which would read as "maximally dissimilar" instead of "not measured".
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("variety\t" + "\t".join(varieties) + "\n")
        for a in varieties:
            cells = [format_cell(lookup.get((a, b))) for b in varieties]
            handle.write(a + "\t" + "\t".join(cells) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="导出版本级两两相似度全矩阵（供热图/PCA 使用）")
    parser.add_argument("--database", required=True, help="ricevar_id.sqlite")
    parser.add_argument("--method", default="ibs", choices=sorted(METHODS),
                        help="相似度方法；必须与识别阶段一致（默认 ibs）")
    parser.add_argument("--min-compared", type=int, default=50,
                        help="低于该比较位点数的品种对不给出相似度（默认 50）")
    parser.add_argument("--out", required=True, help="长表 TSV 输出路径")
    parser.add_argument("--varieties", default=None,
                        help="可选：只比较这些品种（逗号分隔）")
    parser.add_argument("--no-square", action="store_true",
                        help="不写方阵文件")
    args = parser.parse_args(argv)

    db_path = Path(args.database)
    if not db_path.exists():
        parser.error("数据库不存在: %s" % db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        database = FingerprintDatabase(conn)

        if database.is_empty():
            print("数据库中没有参考基因型，拒绝导出（不生成任何占位矩阵）。",
                  file=sys.stderr)
            print("请先运行 07_identify.sh 并 build_database.py 导入真实基因型。",
                  file=sys.stderr)
            return 1

        # Jaccard is only defined for explicit binary presence/absence data; the
        # stored fingerprints are 0/1/2 dosage, so it would abort mid-export with
        # a raw ValueError after possibly writing a partial file. Refuse up front
        # with an actionable message instead.
        if args.method == "jaccard":
            print("Jaccard 只适用于明确的二元 presence/absence 编码，"
                  "而库中指纹是 0/1/2 dosage。", file=sys.stderr)
            print("请改用 --method ibs（预注册主方法）或 hamming；"
                  "若确需 Jaccard，须先把 dosage 明确折叠为 0/1 并说明规则。",
                  file=sys.stderr)
            return 2

        if args.varieties:
            wanted = [v.strip() for v in args.varieties.split(",") if v.strip()]
            available = {row[0] for row in database.list_varieties()}
            missing = [v for v in wanted if v not in available]
            if missing:
                parser.error("品种不在数据库中: %s" % ", ".join(missing))
            varieties = sorted(wanted)
        else:
            varieties = sorted(row[0] for row in database.list_varieties())

        if len(varieties) < 2:
            print("数据库中只有 %d 个品种，无法构成两两矩阵。" % len(varieties),
                  file=sys.stderr)
            return 1

        rows = []
        lookup = {}
        skipped = []
        for i, a in enumerate(varieties):
            # Upper triangle including the diagonal: similarities are symmetric,
            # so computing a<=b halves the work. The square writer fills both
            # halves from this lookup.
            for b in varieties[i:]:
                result = pairwise(database, a, b, method=args.method,
                                  min_compared=args.min_compared)
                rows.append(result)
                if result["mean_similarity"] is None:
                    skipped.append("%s|%s" % (a, b))
                else:
                    lookup[(a, b)] = result["mean_similarity"]
                    lookup[(b, a)] = result["mean_similarity"]
        # Must be read while the connection is open; the summary below is built
        # after the finally block closes it.
        n_markers = database.reference_matrix().n_markers
    finally:
        conn.close()

    out = Path(args.out)
    write_long_table(rows, out)

    square_path = None
    if not args.no_square:
        square_path = out.with_name(out.stem + "_matrix.tsv")
        write_square_matrix(varieties, lookup, square_path)

    scored = [r["mean_similarity"] for r in rows if r["mean_similarity"] is not None]
    summary = {
        "database": str(db_path),
        "method": args.method,
        "min_compared": args.min_compared,
        "n_varieties": len(varieties),
        "n_pairs": len(rows),
        "n_pairs_scored": len(scored),
        "n_pairs_skipped": len(skipped),
        "skipped_pairs": skipped,
        "similarity_min": min(scored) if scored else None,
        "similarity_max": max(scored) if scored else None,
        "similarity_mean": (sum(scored) / len(scored)) if scored else None,
        "n_markers": n_markers,
        "note": ("不同 method 之间相似度不可混用；本文件全部使用 %s。" % args.method),
    }
    summary_path = out.with_name(out.stem + "_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    print("相似度矩阵已导出: %s" % out)
    print("  品种 %d，品种对 %d（给出相似度 %d，跳过 %d）" % (
        summary["n_varieties"], summary["n_pairs"],
        summary["n_pairs_scored"], summary["n_pairs_skipped"]))
    print("  方法 %s，min_compared %d" % (args.method, args.min_compared))
    if square_path:
        print("  方阵: %s" % square_path)
    print("  统计: %s" % summary_path)
    if summary["similarity_min"] is not None:
        print("  相似度范围: %.4f ~ %.4f（均值 %.4f）" % (
            summary["similarity_min"], summary["similarity_max"],
            summary["similarity_mean"]))
    if skipped:
        print("  注意: %d 个品种对因比较位点不足被跳过，方阵中以空单元格表示，"
              "未用 0 填充。" % len(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
