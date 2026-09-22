#!/usr/bin/env python3
"""Evaluate ultra-low-depth variety identification against frozen markers.

Inputs
------
``--reference-matrix``
    Pilot genotype matrix (``<prefix>.genotypes_<n>.tsv``) restricted to the
    frozen marker panel. Reference rows may be restricted with
    ``--reference-samples`` so that a sample is never scored against itself.
``--query-vcf``
    One or more low-depth VCFs from ``server/05_simulate.sh``. Each file must
    hold exactly one sample.
``--truth``
    ``sample_id<TAB>variety_name`` mapping used for accuracy and open-set
    scoring. Samples absent from this table are reported but not scored.

Outputs (all TSV unless noted)
------------------------------
``per_query.tsv``
    One row per query: marker recall, genotype concordance, best/Top-k match,
    whether the true variety was recovered, and accepted/rejected status.
``summary.json``
    Aggregated recall, Top-1/Top-5 accuracy, and rejection rates per depth,
    with the exact parameters and input hashes used.

This script produces *technical-replicate* identification results: queries are
downsampled versions of Pilot samples, so same-variety accuracy is closed-set.
It never claims independent same-variety accuracy, which the zero-overlap
panel cannot support.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ricevar_id.fingerprint import identify_top_k, marker_recall  # noqa: E402
from ricevar_id.genotypes import (  # noqa: E402
    MISSING,
    GenotypeMatrix,
    merge_vcf_genotypes,
    read_matrix_tsv,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_truth(path: Optional[Path]) -> Dict[str, str]:
    """Read ``sample_id<TAB>variety_name`` with a header row."""
    if path is None:
        return {}
    truth: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if not header:
            return truth
        try:
            sample_index = header.index("sample_id")
        except ValueError:
            raise SystemExit("truth table %s lacks a sample_id column" % path)
        variety_index = None
        for candidate in ("variety_name", "variety", "truth_variety"):
            if candidate in header:
                variety_index = header.index(candidate)
                break
        if variety_index is None:
            raise SystemExit("truth table %s lacks a variety_name column" % path)
        for record in reader:
            if not record or not record[0] or record[0].startswith("#"):
                continue
            if len(record) <= max(sample_index, variety_index):
                continue
            sample = record[sample_index].strip()
            variety = record[variety_index].strip()
            if sample and variety:
                truth[sample] = variety
    return truth


def depth_from_name(path: Path) -> Optional[float]:
    """Recover the depth label from ``d0.05_r1`` style directory names."""
    for part in reversed(path.parts):
        if len(part) > 2 and part[0] == "d" and part[1].isdigit():
            label = part.split("_")[0][1:]
            try:
                return float(label)
            except ValueError:
                return None
    return None


def parse_query_entries(values: Sequence[str]) -> List[Tuple[str, Path]]:
    """Accept ``LABEL=PATH`` or a bare path (label defaults to the stem)."""
    entries: List[Tuple[str, Path]] = []
    for value in values:
        if "=" in value:
            label, _, raw = value.partition("=")
            entries.append((label.strip(), Path(raw).resolve()))
        else:
            path = Path(value).resolve()
            entries.append((path.stem, path))
    return entries


def evaluate_query(
    reference: GenotypeMatrix,
    markers: Sequence[str],
    label: str,
    path: Path,
    method: str,
    top_k: int,
    min_compared: int,
    reject_threshold: Optional[float],
    min_dp: Optional[int],
    min_gq: Optional[float],
) -> Dict[str, object]:
    query_matrix = merge_vcf_genotypes([path], min_dp=min_dp, min_gq=min_gq)
    sample = query_matrix.samples[0]
    projected = query_matrix.project(markers)
    query_row = projected.rows[0]

    # Truth row: the same variety's Pilot genotype is the high-depth reference
    # genotype, used only for recall/concordance, never for matching.
    truth_row: Optional[List[int]] = None
    if sample in reference.samples:
        truth_row = reference.row_for(sample)

    recall = marker_recall(truth_row, query_row) if truth_row is not None else None
    result = identify_top_k(
        query_row,
        reference.rows,
        reference.samples,
        method=method,
        top_k=top_k,
        min_compared=min_compared,
        reject_threshold=reject_threshold,
    )
    ranked = result["top_matches"]
    best = ranked[0] if ranked else None

    return {
        "query_label": label,
        "query_sample": sample,
        "query_vcf": str(path),
        "n_frozen_markers": len(markers),
        "called_markers": recall["called_markers"] if recall else None,
        "marker_recall": recall["marker_recall"] if recall else None,
        "genotype_concordance": recall["genotype_concordance"] if recall else None,
        "depth_label": depth_from_name(path),
        "method": method,
        "best_reference_id": best["reference_id"] if best else None,
        "best_similarity": best["similarity"] if best else None,
        "best_compared_markers": best["n_compared_markers"] if best else None,
        "best_different_markers": best["n_different_markers"] if best else None,
        "accepted": result["accepted"],
        "top_k_ids": ";".join(str(entry["reference_id"]) for entry in ranked),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-matrix", required=True, type=Path)
    parser.add_argument("--query-vcf", nargs="+", required=True, help="LABEL=PATH or PATH entries")
    parser.add_argument("--truth", type=Path, default=None)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--marker-count", type=int, default=None, help="Restrict to the first N frozen markers")
    parser.add_argument("--method", default="ibs", choices=["ibs", "hamming", "jaccard"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-compared", type=int, default=50)
    parser.add_argument("--reject-threshold", type=float, default=None)
    parser.add_argument("--min-dp", type=int, default=None)
    parser.add_argument("--min-gq", type=float, default=None)
    args = parser.parse_args()

    if not args.reference_matrix.exists():
        raise SystemExit("reference matrix not found: %s" % args.reference_matrix)
    reference = read_matrix_tsv(args.reference_matrix)
    markers = list(reference.markers)
    if args.marker_count is not None:
        if args.marker_count < 1 or args.marker_count > len(markers):
            raise SystemExit("--marker-count must be between 1 and %d" % len(markers))
        markers = markers[: args.marker_count]
        reference = reference.select_markers(markers)
    truth = read_truth(args.truth)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    entries = parse_query_entries(args.query_vcf)

    rows: List[Dict[str, object]] = []
    for label, path in entries:
        if not path.exists():
            raise SystemExit("query VCF not found: %s" % path)
        query_matrix = merge_vcf_genotypes([path], min_dp=args.min_dp, min_gq=args.min_gq)
        sample = query_matrix.samples[0]
        if sample not in reference.samples:
            print("[warn] query sample %s has no reference row; recall will be blank" % sample, file=sys.stderr)
        row = evaluate_query(
            reference, markers, label, path,
            args.method, args.top_k, args.min_compared, args.reject_threshold,
            args.min_dp, args.min_gq,
        )
        # Variety-level scoring uses the truth table for reference samples.
        if truth:
            best = row["best_reference_id"]
            row["top1_variety"] = truth.get(best) if best else None
            row["top5_varieties"] = ";".join(
                truth.get(entry, "") for entry in str(row["top_k_ids"]).split(";") if entry
            )
            true_variety = truth.get(sample)
            row["query_variety"] = true_variety
            row["top1_correct_sample"] = bool(best == sample)
            # ``scored`` in summarize() filters on "top1_correct_variety is not
            # None". A query whose true variety is unknown must therefore be
            # left as None, NOT False: a bare bool() would count an unlabelled
            # query as a guaranteed miss and depress every reported accuracy.
            if true_variety:
                row["top1_correct_variety"] = bool(row["top1_variety"] == true_variety)
                top5 = [truth.get(entry) for entry in str(row["top_k_ids"]).split(";") if entry]
                row["top5_correct_variety"] = bool(true_variety in top5)
            else:
                row["top1_correct_variety"] = None
                row["top5_correct_variety"] = None
        rows.append(row)

    # A truth table that matches none of the reference ids would otherwise
    # report a perfectly-formed 0.0 accuracy instead of failing loudly.
    if truth and rows:
        labelled = sum(1 for row in rows if row.get("query_variety"))
        if labelled == 0:
            raise SystemExit(
                "真值表 %s 与任何查询样本都不匹配：请检查 sample_id 列是否与参考矩阵/清单一致"
                % args.truth
            )
        if labelled < len(rows):
            print(
                "[warn] %d/%d 个查询在真值表中无品种名，这些查询不计入准确率分母"
                % (len(rows) - labelled, len(rows)),
                file=sys.stderr,
            )

    fields = [
        "query_label", "query_sample", "query_vcf", "query_variety", "depth_label",
        "n_frozen_markers", "called_markers", "marker_recall", "genotype_concordance",
        "method", "min_compared", "reject_threshold",
        "best_reference_id", "best_similarity", "best_compared_markers", "best_different_markers",
        "accepted", "top_k_ids", "top1_variety", "top5_varieties",
        "top1_correct_sample", "top1_correct_variety", "top5_correct_variety",
    ]
    per_query = args.out_dir / "per_query.tsv"
    with per_query.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields)
        for row in rows:
            writer.writerow(["" if row.get(field) is None else row.get(field) for field in fields])

    summary = summarize(rows, args, markers, reference, per_query)
    summary_path = args.out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _mean(values: Iterable[float]) -> Optional[float]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def summarize(rows, args, markers, reference, per_query: Path) -> Dict[str, object]:
    by_depth: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "unknown" if row["depth_label"] is None else ("%.2f" % float(row["depth_label"]))
        by_depth[key].append(row)

    depths: Dict[str, object] = {}
    for key in sorted(by_depth, key=lambda value: (value == "unknown", value)):
        group = by_depth[key]
        scored = [row for row in group if row.get("top1_correct_variety") is not None]
        depths[key] = {
            "n_queries": len(group),
            "mean_marker_recall": _mean(row["marker_recall"] for row in group),
            "mean_genotype_concordance": _mean(row["genotype_concordance"] for row in group),
            "mean_best_similarity": _mean(row["best_similarity"] for row in group),
            "mean_compared_markers": _mean(row["best_compared_markers"] for row in group),
            "n_scored": len(scored),
            "n_unlabelled": len(group) - len(scored),
            "top1_sample_accuracy": _mean(1.0 if row["top1_correct_sample"] else 0.0 for row in scored),
            "top1_variety_accuracy": _mean(1.0 if row["top1_correct_variety"] else 0.0 for row in scored),
            "top5_variety_accuracy": _mean(1.0 if row["top5_correct_variety"] else 0.0 for row in scored),
            "accept_rate": _mean(1.0 if row["accepted"] else 0.0 for row in group),
        }

    return {
        "note": (
            "Queries are downsampled technical replicates of Pilot samples. "
            "Accuracy here is closed-set and does not represent independent "
            "same-variety performance."
        ),
        "reference_matrix": str(args.reference_matrix),
        "reference_matrix_sha256": sha256(args.reference_matrix),
        "reference_samples": len(reference.samples),
        "frozen_markers": len(markers),
        "truth_table": None if args.truth is None else str(args.truth),
        "parameters": {
            "method": args.method,
            "top_k": args.top_k,
            "min_compared": args.min_compared,
            "reject_threshold": args.reject_threshold,
            "min_dp": args.min_dp,
            "min_gq": args.min_gq,
            "marker_count": args.marker_count,
        },
        "n_queries": len(rows),
        "n_labelled_queries": sum(1 for row in rows if row.get("query_variety")),
        "per_query_tsv": str(per_query),
        "by_depth": depths,
    }


if __name__ == "__main__":
    main()
