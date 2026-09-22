#!/usr/bin/env python
"""构建 RiceVar-ID 品种指纹数据库（TASK-041）。

用法::

    python scripts/build_database.py \
        --matrix   data/processed/markers/pilot.genotypes_2000.tsv \
        --manifest data/metadata/server/pilot_manifest.tsv \
        --marker-vcf data/processed/markers/pilot.markers_2000.vcf \
        --per-query  data/processed/identification/markers_2000/per_query.tsv \
        --out      database/ricevar_id.sqlite

所有输入都是可选的"能用多少用多少"：矩阵和清单必需，marker VCF 与评估结果
缺失时只记录为 absent，**不会**生成占位数据。库中没有参考基因型时，查询层
会直接拒绝识别，而不是给出随机结果。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id.database import build_database  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="构建品种指纹 SQLite 数据库")
    parser.add_argument("--matrix", required=True,
                        help="Pilot 基因型矩阵 *.genotypes_<n>.tsv")
    parser.add_argument("--manifest", required=True,
                        help="冻结的服务器样本清单 pilot_manifest.tsv")
    parser.add_argument("--marker-vcf", default=None,
                        help="冻结 marker VCF（可选，仅用于溯源）")
    parser.add_argument("--per-query", default=None,
                        help="识别评估 per_query.tsv（可选）")
    parser.add_argument("--marker-set", default=None,
                        help="marker 集标签；默认从矩阵文件名推断")
    parser.add_argument("--out", default=str(ROOT / "database" / "ricevar_id.sqlite"),
                        help="输出数据库路径")
    parser.add_argument("--summary", default=None,
                        help="统计结果 JSON 输出路径；默认写到库旁")
    args = parser.parse_args(argv)

    matrix = Path(args.matrix)
    manifest = Path(args.manifest)
    for path, label in ((matrix, "基因型矩阵"), (manifest, "样本清单")):
        if not path.exists():
            parser.error("%s 不存在: %s" % (label, path))

    stats = build_database(
        args.out,
        matrix_tsv=str(matrix),
        manifest_path=str(manifest),
        marker_vcf=args.marker_vcf,
        per_query_path=args.per_query,
        marker_set=args.marker_set,
    )

    summary_path = Path(args.summary) if args.summary else Path(args.out).with_suffix(".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    call_rate = stats["call_rate"]
    print("数据库已构建: %s" % args.out)
    print("  样本 %d，位点 %d，基因型 %d（非缺失 %d，call rate %s）" % (
        stats["matrix_samples"], stats["matrix_markers"], stats["total_genotypes"],
        stats["called_genotypes"],
        "n/a" if call_rate is None else "%.4f" % call_rate,
    ))
    print("  评估记录 %d 行" % stats["evaluation_rows"])
    print("  统计: %s" % summary_path)
    if stats["evaluation_rows"] == 0:
        print("  提示: 未导入识别评估结果（尚未运行 07_identify.sh 属正常）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
