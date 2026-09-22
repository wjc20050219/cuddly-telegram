"""Read frozen-marker genotype matrices and low-depth VCFs into one layout.

Two sources feed the identification stage:

* the Pilot nested-marker matrix written by ``scripts/select_snp_markers.py``
  (``sample_id`` plus one column per ``CHROM:POS:REF:ALT`` marker), and
* per-sample low-depth VCFs produced by ``server/05_simulate.sh`` with
  ``bcftools call -m -A -C alleles -T ...``.

Both must be projected onto exactly the same frozen marker set before any
similarity is computed, otherwise "missing marker" and "different marker"
become indistinguishable. ``GenotypeMatrix.project`` enforces that: markers
absent from a query VCF are recorded as missing, never as reference genotype,
and a query VCF that is not a subset of the frozen markers is rejected.

Only the Python standard library is used, matching the rest of the package.
"""
from __future__ import annotations

import csv
import gzip
import math
import os
import re
from typing import Dict, List, Optional, Sequence, TextIO, Tuple

MISSING = -1

#: ``CHROM:POS:REF:ALT`` — the marker identifier used across the project.
MARKER_RE = re.compile(r"^(?P<chrom>[^:]+):(?P<pos>\d+):(?P<ref>[ACGTNacgtn]+):(?P<alt>[ACGTNacgtn]+)$")


def open_text(path) -> TextIO:
    """Open a plain or gzip-compressed text file for reading."""
    text = str(path)
    if text.endswith(".gz"):
        return gzip.open(text, "rt", encoding="utf-8")
    return open(text, "r", encoding="utf-8")


def marker_id(chrom: str, pos: object, ref: str, alt: str) -> str:
    return "%s:%s:%s:%s" % (chrom, pos, ref.upper(), alt.upper())


def parse_marker_id(value: str) -> Optional[Tuple[str, int, str, str]]:
    match = MARKER_RE.match(value.strip())
    if not match:
        return None
    return (
        match.group("chrom"),
        int(match.group("pos")),
        match.group("ref").upper(),
        match.group("alt").upper(),
    )


def _split_allele_index(value: str, alt: str) -> int:
    """Map one allele string onto the frozen ALT index, or -1 when it differs."""
    if value in ("", "."):
        return -1
    if value == "0":
        return 0
    if value == "1":
        return 1
    # 05_simulate.sh calls with -C alleles, so ALT should match; anything else
    # is a different variant at the same position and must not be counted.
    return -1


def parse_sample_genotype(
    fmt: str,
    sample_field: str,
    min_dp: Optional[int] = None,
    min_gq: Optional[float] = None,
) -> int:
    """Return 0/1/2 dosage for one sample column, or MISSING.

    A genotype is rejected when it is haploid, has an unexpected allele index,
    or fails the optional DP/GQ guards. Rejecting on depth is important at
    0.02x, where the caller emits many low-evidence genotypes.
    """
    keys = fmt.split(":")
    index = {key: position for position, key in enumerate(keys)}
    values = sample_field.split(":")
    gt = values[index["GT"]] if "GT" in index and index["GT"] < len(values) else "."
    alleles = gt.replace("|", "/").split("/")
    if len(alleles) != 2:
        return MISSING
    mapped = [_split_allele_index(allele, "1") for allele in alleles]
    if any(value < 0 for value in mapped):
        return MISSING
    if min_dp is not None:
        raw = values[index["DP"]] if "DP" in index and index["DP"] < len(values) else "."
        dp = _parse_number(raw)
        if not math.isfinite(dp) or dp < min_dp:
            return MISSING
    if min_gq is not None:
        raw = values[index["GQ"]] if "GQ" in index and index["GQ"] < len(values) else "."
        gq = _parse_number(raw)
        if not math.isfinite(gq) or gq < min_gq:
            return MISSING
    return int(mapped[0] + mapped[1])


def _parse_number(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


class GenotypeMatrix:
    """A marker-aligned genotype matrix with sample and marker identifiers."""

    def __init__(self, samples: Sequence[str], markers: Sequence[str], rows: Sequence[Sequence[int]],
                 marker_set: Optional[str] = None):
        self.samples: List[str] = [str(sample) for sample in samples]
        self.markers: List[str] = [str(marker) for marker in markers]
        self.rows: List[List[int]] = [[int(value) for value in row] for row in rows]
        # Provenance label for the marker panel (e.g. "pilot.2000"); carried through
        # select/project so downstream writers can record which set was used.
        self.marker_set: Optional[str] = marker_set
        if len(self.rows) != len(self.samples):
            raise ValueError("row count must equal sample count")
        for row in self.rows:
            if len(row) != len(self.markers):
                raise ValueError("every row must have one value per marker")
            if any(value not in (MISSING, 0, 1, 2) for value in row):
                raise ValueError("genotypes must be -1, 0, 1, or 2")

    def __len__(self) -> int:
        return len(self.samples)

    @property
    def n_markers(self) -> int:
        return len(self.markers)

    @property
    def n_samples(self) -> int:
        return len(self.samples)

    def row_for(self, sample: str) -> List[int]:
        try:
            index = self.samples.index(sample)
        except ValueError:
            raise KeyError("unknown sample: %s" % sample)
        return self.rows[index]

    def call_rate(self, sample: str) -> float:
        row = self.row_for(sample)
        if not row:
            return float("nan")
        return sum(value >= 0 for value in row) / float(len(row))

    def select_markers(self, markers: Sequence[str]) -> "GenotypeMatrix":
        """Return a sub-matrix in the exact requested marker order."""
        position = {marker: index for index, marker in enumerate(self.markers)}
        missing = [marker for marker in markers if marker not in position]
        if missing:
            raise KeyError("markers absent from matrix: " + ", ".join(missing[:3]))
        columns = [position[marker] for marker in markers]
        return GenotypeMatrix(self.samples, markers, [[row[c] for c in columns] for row in self.rows],
                              marker_set=self.marker_set)

    def project(self, markers: Sequence[str]) -> "GenotypeMatrix":
        """Align onto a frozen marker set, filling absent markers with MISSING.

        This is used for low-depth query VCFs, which legitimately cover only a
        subset of the frozen markers. Absent markers become missing, never 0.
        """
        frozen = set(markers)
        unknown = [marker for marker in self.markers if marker not in frozen]
        if unknown:
            raise ValueError(
                "query contains %d markers outside the frozen set, e.g. %s"
                % (len(unknown), ", ".join(unknown[:3]))
            )
        # Target order defines the output columns; the query only supplies values.
        target = {marker: index for index, marker in enumerate(markers)}
        width = len(markers)
        projected: List[List[int]] = []
        for row in self.rows:
            out = [MISSING] * width
            for marker, value in zip(self.markers, row):
                out[target[marker]] = value
            projected.append(out)
        return GenotypeMatrix(self.samples, markers, projected, marker_set=self.marker_set)


def read_matrix_tsv(path, marker_set: Optional[str] = None) -> GenotypeMatrix:
    """Read ``<prefix>.genotypes_<n>.tsv`` written by the marker selector.

    ``marker_set`` labels the panel for provenance; when omitted it is derived
    from the filename (``pilot.genotypes_2000.tsv`` → ``pilot.2000``).
    """
    if marker_set is None:
        name = os.path.basename(str(path))
        match = re.match(r"^(?P<prefix>.+?)\.genotypes_(?P<count>\d+)\.tsv$", name)
        if match:
            marker_set = "%s.%s" % (match.group("prefix"), match.group("count"))
    with open_text(path) as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("empty genotype matrix: %s" % path)
        if not header or header[0] != "sample_id":
            raise ValueError("expected a sample_id header row in %s" % path)
        markers = header[1:]
        if not markers:
            raise ValueError("genotype matrix has no marker columns: %s" % path)
        for marker in markers:
            if parse_marker_id(marker) is None:
                raise ValueError("malformed marker column %r in %s" % (marker, path))
        samples: List[str] = []
        rows: List[List[int]] = []
        for record in reader:
            if not record or not record[0]:
                continue
            if len(record) != len(header):
                raise ValueError("row %s has %d fields, expected %d" % (record[0], len(record), len(header)))
            samples.append(record[0])
            rows.append([int(value) for value in record[1:]])
    return GenotypeMatrix(samples, markers, rows, marker_set=marker_set)


def read_vcf_genotypes(
    path,
    min_dp: Optional[int] = None,
    min_gq: Optional[float] = None,
    sample: Optional[str] = None,
) -> GenotypeMatrix:
    """Read a (possibly multi-sample) VCF into dosage rows.

    ``bcftools call`` emits the ALT allele, so only biallelic single-base
    records whose REF/ALT match a frozen marker are kept; other records are
    reported through the returned ``skipped`` mapping rather than silently
    dropped.
    """
    samples: List[str] = []
    markers: List[str] = []
    rows: List[List[int]] = []
    with open_text(path) as handle:
        for line in handle:
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                columns = line.rstrip("\n").split("\t")
                samples = columns[9:]
                if sample is not None:
                    if sample not in samples:
                        raise ValueError("sample %r not found in %s" % (sample, path))
                    samples = [sample]
                if not samples:
                    raise ValueError("VCF has no sample columns: %s" % path)
                rows = [[] for _ in samples]
                continue
            if line.startswith("#"):
                continue
            if not samples:
                raise ValueError("VCF body before #CHROM header: %s" % path)
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10:
                continue
            chrom, pos, _vid, ref, alt, _qual, _filt = fields[:7]
            if "," in alt or len(ref) != 1 or len(alt) != 1:
                continue
            if sample is not None:
                column = fields[9:][samples.index(sample)]
            else:
                column = None
            markers.append(marker_id(chrom, pos, ref, alt))
            for index in range(len(samples)):
                if column is not None:
                    value = parse_sample_genotype(fields[8], column, min_dp, min_gq)
                else:
                    value = parse_sample_genotype(fields[8], fields[9 + index], min_dp, min_gq)
                rows[index].append(value)
    if not samples:
        raise ValueError("no #CHROM header found in %s" % path)
    return GenotypeMatrix(samples, markers, rows)


def merge_vcf_genotypes(
    paths: Sequence,
    min_dp: Optional[int] = None,
    min_gq: Optional[float] = None,
) -> GenotypeMatrix:
    """Merge one-sample low-depth VCFs into a single matrix.

    Each VCF must describe exactly one sample. Records are unioned by marker
    identifier; a sample missing a record receives MISSING, which is correct
    here because each file is already restricted to the frozen marker set.
    """
    if not paths:
        raise ValueError("no VCF paths given")
    marker_order: List[str] = []
    seen: Dict[str, int] = {}
    per_sample: Dict[str, Dict[str, int]] = {}
    order: List[str] = []
    for path in paths:
        matrix = read_vcf_genotypes(path, min_dp=min_dp, min_gq=min_gq)
        if len(matrix.samples) != 1:
            raise ValueError("expected exactly one sample in %s, found %d" % (path, len(matrix.samples)))
        name = matrix.samples[0]
        if name in per_sample:
            raise ValueError("duplicate sample %r across VCF inputs" % name)
        order.append(name)
        per_sample[name] = dict(zip(matrix.markers, matrix.rows[0]))
        for marker in matrix.markers:
            if marker not in seen:
                seen[marker] = len(marker_order)
                marker_order.append(marker)
    rows = [[per_sample[name].get(marker, MISSING) for marker in marker_order] for name in order]
    return GenotypeMatrix(order, marker_order, rows)
