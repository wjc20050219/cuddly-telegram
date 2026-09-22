#!/usr/bin/env python3
"""Select nested 500/1000/2000 SNP panels from a Pilot joint VCF.

This script is intentionally restricted to ``--panel-role pilot`` to guard
against marker leakage from the frozen independent panel. It performs a
streaming first pass, keeps the strongest candidate sites, applies a simple
physical-spacing filter, and then makes a second pass to write nested marker
VCFs and a 0/1/2/-1 genotype matrix.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import heapq
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, TextIO, Tuple


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(str(path), "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_number(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_calls(fmt: str, sample_fields: Sequence[str], min_dp: int, min_gq: float) -> List[int]:
    keys = fmt.split(":")
    index = {key: position for position, key in enumerate(keys)}
    calls: List[int] = []
    for field in sample_fields:
        values = field.split(":")
        gt = values[index["GT"]] if "GT" in index and index["GT"] < len(values) else "."
        alleles = gt.replace("|", "/").split("/")
        if len(alleles) != 2 or any(allele not in ("0", "1") for allele in alleles):
            calls.append(-1)
            continue
        dp = parse_number(values[index["DP"]]) if "DP" in index and index["DP"] < len(values) else float("nan")
        gq = parse_number(values[index["GQ"]]) if "GQ" in index and index["GQ"] < len(values) else float("nan")
        if not math.isfinite(dp) or not math.isfinite(gq) or dp < min_dp or gq < min_gq:
            calls.append(-1)
            continue
        calls.append(int(alleles[0]) + int(alleles[1]))
    return calls


def site_metrics(calls: Sequence[int]) -> Tuple[float, float, float]:
    called = [value for value in calls if value >= 0]
    if not called:
        return 0.0, 0.0, 0.0
    call_rate = len(called) / len(calls)
    alt_frequency = sum(called) / (2.0 * len(called))
    maf = min(alt_frequency, 1.0 - alt_frequency)
    counts = Counter(called)
    pairs = len(called) * (len(called) - 1) / 2.0
    concordant = sum(count * (count - 1) / 2.0 for count in counts.values())
    discrimination = 1.0 - concordant / pairs if pairs else 0.0
    return call_rate, maf, discrimination


def scan_candidates(
    vcf: Path,
    max_missing: float,
    min_maf: float,
    min_qual: float,
    min_dp: int,
    min_gq: float,
    pool_size: int,
) -> Tuple[List[str], List[str], List[Tuple[object, ...]], Dict[str, int]]:
    headers: List[str] = []
    samples: List[str] = []
    heap: List[Tuple[object, ...]] = []
    counts = Counter()
    ordinal = 0
    with open_text(vcf) as handle:
        for line in handle:
            if line.startswith("##"):
                headers.append(line)
                continue
            if line.startswith("#CHROM"):
                headers.append(line)
                samples = line.rstrip("\n").split("\t")[9:]
                continue
            counts["records"] += 1
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10 or not samples:
                counts["malformed"] += 1
                continue
            chrom, pos_text, _vid, ref, alt, qual_text, filt = fields[:7]
            if "," in alt or len(ref) != 1 or len(alt) != 1:
                counts["not_biallelic_snp"] += 1
                continue
            if filt not in ("PASS", "."):
                counts["filter"] += 1
                continue
            qual = parse_number(qual_text)
            if not math.isfinite(qual) or qual < min_qual:
                counts["qual"] += 1
                continue
            calls = parse_calls(fields[8], fields[9:], min_dp, min_gq)
            call_rate, maf, discrimination = site_metrics(calls)
            if call_rate < 1.0 - max_missing:
                counts["missing"] += 1
                continue
            if maf < min_maf:
                counts["maf"] += 1
                continue
            ordinal += 1
            pos = int(pos_text)
            # Earlier sites win exact ties; all remaining fields ensure total ordering.
            candidate = (discrimination, call_rate, maf, qual, -ordinal, chrom, pos, ref, alt)
            if len(heap) < pool_size:
                heapq.heappush(heap, candidate)
            elif candidate > heap[0]:
                heapq.heapreplace(heap, candidate)
            counts["eligible"] += 1
    if not samples:
        raise SystemExit("VCF lacks a #CHROM header or sample columns")
    return headers, samples, sorted(heap, reverse=True), dict(counts)


def apply_spacing(candidates: Sequence[Tuple[object, ...]], wanted: int, min_distance: int) -> List[Tuple[object, ...]]:
    selected: List[Tuple[object, ...]] = []
    positions: Dict[str, List[int]] = defaultdict(list)
    for candidate in candidates:
        chrom, pos = str(candidate[5]), int(candidate[6])
        existing = positions[chrom]
        index = bisect.bisect_left(existing, pos)
        left_ok = index == 0 or pos - existing[index - 1] >= min_distance
        right_ok = index == len(existing) or existing[index] - pos >= min_distance
        if left_ok and right_ok:
            bisect.insort(existing, pos)
            selected.append(candidate)
            if len(selected) == wanted:
                break
    return selected


def marker_id(candidate: Sequence[object]) -> str:
    return "%s:%s:%s:%s" % (candidate[5], candidate[6], candidate[7], candidate[8])


def write_outputs(
    vcf: Path,
    out_dir: Path,
    prefix: str,
    headers: Sequence[str],
    samples: Sequence[str],
    selected: Sequence[Tuple[object, ...]],
    marker_counts: Sequence[int],
    min_dp: int,
    min_gq: float,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    max_count = max(marker_counts)
    selected = list(selected[:max_count])
    ordered_ids = [marker_id(candidate) for candidate in selected]
    rank = {site: index for index, site in enumerate(ordered_ids)}
    nested = {count: set(ordered_ids[:count]) for count in marker_counts}
    handles = {}
    try:
        for count in marker_counts:
            path = out_dir / ("%s.markers_%d.vcf" % (prefix, count))
            handle = path.open("w", encoding="utf-8", newline="")
            handles[count] = handle
            for header in headers:
                handle.write(header)
        calls_by_site: Dict[str, List[int]] = {}
        with open_text(vcf) as source:
            for line in source:
                if line.startswith("#"):
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 10:
                    continue
                site = "%s:%s:%s:%s" % (fields[0], fields[1], fields[3], fields[4])
                if site not in rank:
                    continue
                calls_by_site[site] = parse_calls(fields[8], fields[9:], min_dp, min_gq)
                for count in marker_counts:
                    if site in nested[count]:
                        handles[count].write(line)
        missing_sites = [site for site in ordered_ids if site not in calls_by_site]
        if missing_sites:
            raise SystemExit("Selected sites disappeared on VCF second pass: " + ", ".join(missing_sites[:3]))
        matrix_path = out_dir / (prefix + ".genotypes_%d.tsv" % max_count)
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["sample_id"] + ordered_ids)
            for sample_index, sample in enumerate(samples):
                writer.writerow([sample] + [calls_by_site[site][sample_index] for site in ordered_ids])
        sites_path = out_dir / (prefix + ".marker_ranking.tsv")
        with sites_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["rank", "marker_id", "chrom", "pos", "ref", "alt", "discrimination", "call_rate", "maf", "qual"])
            for index, candidate in enumerate(selected, 1):
                writer.writerow([index, marker_id(candidate), candidate[5], candidate[6], candidate[7], candidate[8], candidate[0], candidate[1], candidate[2], candidate[3]])
    finally:
        for handle in handles.values():
            handle.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vcf", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--prefix", default="pilot")
    parser.add_argument("--panel-role", required=True, choices=["pilot"], help="Leakage guard: marker selection is Pilot-only")
    parser.add_argument("--marker-counts", nargs="+", type=int, default=[500, 1000, 2000])
    parser.add_argument("--max-missing", type=float, default=0.2)
    parser.add_argument("--min-maf", type=float, default=0.05)
    parser.add_argument("--min-qual", type=float, default=30.0)
    parser.add_argument("--min-dp", type=int, default=3)
    parser.add_argument("--min-gq", type=float, default=20.0)
    parser.add_argument("--min-distance", type=int, default=1000)
    parser.add_argument("--candidate-multiplier", type=int, default=50)
    args = parser.parse_args()
    counts = sorted(set(args.marker_counts))
    if not counts or min(counts) < 1:
        raise SystemExit("marker counts must be positive")
    if not 0 <= args.max_missing < 1 or not 0 <= args.min_maf <= 0.5:
        raise SystemExit("invalid missing/MAF parameters")
    pool_size = max(counts) * max(1, args.candidate_multiplier)
    headers, samples, candidates, scan_counts = scan_candidates(
        args.vcf, args.max_missing, args.min_maf, args.min_qual,
        args.min_dp, args.min_gq, pool_size,
    )
    selected = apply_spacing(candidates, max(counts), args.min_distance)
    if len(selected) < max(counts):
        raise SystemExit("Only %d spaced markers passed QC; requested %d" % (len(selected), max(counts)))
    write_outputs(args.vcf, args.out_dir, args.prefix, headers, samples, selected, counts, args.min_dp, args.min_gq)
    provenance = {
        "input_vcf": str(args.vcf),
        "input_sha256": sha256(args.vcf),
        "panel_role": args.panel_role,
        "sample_count": len(samples),
        "marker_counts": counts,
        "parameters": {
            "max_missing": args.max_missing, "min_maf": args.min_maf,
            "min_qual": args.min_qual, "min_dp": args.min_dp,
            "min_gq": args.min_gq, "min_distance": args.min_distance,
            "candidate_multiplier": args.candidate_multiplier,
        },
        "scan_counts": scan_counts,
        "selected_markers": len(selected),
    }
    path = args.out_dir / (args.prefix + ".selection.json")
    path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
