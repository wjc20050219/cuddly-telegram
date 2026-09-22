#!/usr/bin/env python3
"""Build canonical server manifests from the frozen panel TSV files.

No FASTQ is downloaded. The script validates panel sizes and the zero-overlap
claim, then writes deterministic 1-sample/5-sample smoke-test manifests plus
the full Pilot and independent manifests.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data" / "metadata" / "candidates"
OUT = ROOT / "data" / "metadata" / "server"
PILOT = CAND / "pilot_panel.tsv"
INDEPENDENT = CAND / "independent_test_panel.tsv"

FIELDS = [
    "sample_id", "variety_name", "subspecies", "run_accession",
    "bioproject", "biosample", "platform", "paired_or_single",
    "estimated_depth", "read_length", "fastq_ftp", "fastq_bytes",
    "source_db", "panel_role",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def total_bytes(row: Dict[str, str]) -> int:
    total = 0
    for part in row.get("fastq_bytes", "").replace(",", "").split(";"):
        part = part.strip()
        if part:
            total += int(part)
    return total


def selected_fastqs(row: Dict[str, str]) -> tuple:
    """Return aligned URL/byte lists, excluding redundant ENA orphan files.

    A few paired runs expose an additional unsuffixed FASTQ alongside the real
    ``_1/_2`` pair. Downloading all three wastes space and makes provenance
    ambiguous. Prefer the pair when both mates are present; otherwise preserve
    the submitted list and let the smoke test reveal malformed metadata.
    """
    urls = [part.strip() for part in row.get("fastq_ftp", "").split(";") if part.strip()]
    sizes = [part.strip() for part in row.get("fastq_bytes", "").split(";")]
    if len(sizes) != len(urls):
        raise ValueError("FASTQ URL/byte count mismatch for %s" % row.get("accession", "unknown"))
    pairs = list(zip(urls, sizes))
    if (row.get("paired_or_single") or "").upper() == "PAIRED":
        mate1 = [item for item in pairs if item[0].endswith("_1.fastq.gz")]
        mate2 = [item for item in pairs if item[0].endswith("_2.fastq.gz")]
        if len(mate1) == 1 and len(mate2) == 1:
            pairs = [mate1[0], mate2[0]]
    return ";".join(item[0] for item in pairs), ";".join(item[1] for item in pairs)


def canonical(row: Dict[str, str]) -> Dict[str, str]:
    fastq_ftp, fastq_bytes = selected_fastqs(row)
    return {
        "sample_id": row["sample_id"],
        "variety_name": row["canonical_name"],
        "subspecies": row.get("subspecies", "") or "unknown",
        "run_accession": row["accession"],
        "bioproject": row.get("BioProject", ""),
        "biosample": row.get("BioSample", ""),
        "platform": row.get("sequencing_platform", ""),
        "paired_or_single": row.get("paired_or_single", ""),
        "estimated_depth": row.get("estimated_depth", ""),
        "read_length": row.get("read_length", ""),
        "fastq_ftp": fastq_ftp,
        "fastq_bytes": fastq_bytes,
        "source_db": row.get("source_db", ""),
        "panel_role": row.get("panel_role", ""),
    }


def write_tsv(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def choose_smoke5(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Choose a deterministic, small download set spanning major labels.

    The smallest sample in each preferred subspecies is selected first, then
    remaining slots are filled by total FASTQ bytes. This is an engineering
    smoke set, not a statistical subsample and not a replacement for Pilot 30.
    """
    ordered = sorted(rows, key=lambda r: (total_bytes(r), r["sample_id"]))
    chosen: List[Dict[str, str]] = []
    seen = set()
    for label in ("indica", "japonica", "aus", "unknown", "temperate_japonica"):
        candidate = next((r for r in ordered if (r.get("subspecies") or "unknown") == label), None)
        if candidate and candidate["sample_id"] not in seen:
            chosen.append(candidate)
            seen.add(candidate["sample_id"])
        if len(chosen) == 5:
            return chosen
    for row in ordered:
        if row["sample_id"] not in seen:
            chosen.append(row)
            seen.add(row["sample_id"])
        if len(chosen) == 5:
            break
    return chosen


def main() -> None:
    pilot = read_tsv(PILOT)
    independent = read_tsv(INDEPENDENT)
    if len(pilot) != 30:
        raise SystemExit("Pilot panel must contain 30 rows; got %d" % len(pilot))
    if len(independent) != 25:
        raise SystemExit("Independent panel must contain 25 rows; got %d" % len(independent))

    pilot_varieties = {r["canonical_name"] for r in pilot}
    independent_varieties = {r["canonical_name"] for r in independent}
    overlap = sorted(pilot_varieties & independent_varieties)
    if overlap:
        raise SystemExit("Panel variety overlap detected: " + ", ".join(overlap))
    for row in pilot + independent:
        if not row.get("accession") or not row.get("fastq_ftp"):
            raise SystemExit("Missing accession/FASTQ URL: " + repr(row))

    ordered = sorted(pilot, key=lambda r: (total_bytes(r), r["sample_id"]))
    smoke1 = ordered[:1]
    smoke5 = choose_smoke5(pilot)

    outputs = {
        "pilot_manifest.tsv": pilot,
        "pilot_smoke1.tsv": smoke1,
        "pilot_smoke5.tsv": smoke5,
        "independent_manifest.tsv": independent,
    }
    for name, rows in outputs.items():
        write_tsv(OUT / name, (canonical(row) for row in rows))

    summary = {
        "inputs": {
            str(PILOT.relative_to(ROOT)): sha256(PILOT),
            str(INDEPENDENT.relative_to(ROOT)): sha256(INDEPENDENT),
        },
        "selection_rule": "minimum FASTQ bytes; smoke5 spans preferred subspecies labels before size fill",
        "pilot_rows": len(pilot),
        "independent_rows": len(independent),
        "variety_overlap": overlap,
        "smoke1": [r["sample_id"] for r in smoke1],
        "smoke5": [r["sample_id"] for r in smoke5],
        "smoke1_fastq_bytes": sum(total_bytes(canonical(r)) for r in smoke1),
        "smoke5_fastq_bytes": sum(total_bytes(canonical(r)) for r in smoke5),
    }
    (OUT / "manifest_build_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
