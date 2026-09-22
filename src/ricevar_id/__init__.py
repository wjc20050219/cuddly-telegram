"""Core, lightweight RiceVar-ID analysis functions."""

from .dbquery import FingerprintDatabase
from .fingerprint import (
    binary_jaccard,
    hamming_similarity,
    identify_top_k,
    ibs_similarity,
    marker_recall,
)
from .genotypes import (
    MISSING,
    GenotypeMatrix,
    marker_id,
    merge_vcf_genotypes,
    parse_marker_id,
    read_matrix_tsv,
    read_vcf_genotypes,
)
from .database import build_database, connect

__all__ = [
    "MISSING",
    "FingerprintDatabase",
    "GenotypeMatrix",
    "binary_jaccard",
    "build_database",
    "connect",
    "hamming_similarity",
    "identify_top_k",
    "ibs_similarity",
    "marker_id",
    "marker_recall",
    "merge_vcf_genotypes",
    "parse_marker_id",
    "read_matrix_tsv",
    "read_vcf_genotypes",
]
