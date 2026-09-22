"""Transparent SNP-fingerprint similarity and identification utilities.

Genotypes use diploid dosage 0/1/2 and missing values use -1. Similarities are
computed only at markers called in both query and reference. Every result also
reports the number of compared markers to prevent sparse data from appearing
artificially convincing. The implementation deliberately uses only the Python
standard library; 20–30 varieties × 2,000 markers do not require vectorization.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

MISSING = -1


def _rows(query: Sequence[int], references: Sequence[Sequence[int]]) -> Tuple[List[int], List[List[int]]]:
    q = [int(value) for value in query]
    rows = [[int(value) for value in row] for row in references]
    if not q:
        raise ValueError("query must contain at least one marker")
    if any(len(row) != len(q) for row in rows):
        raise ValueError("every reference must have the same marker count as query")
    if any(value not in (MISSING, 0, 1, 2) for value in q):
        raise ValueError("genotypes must be -1, 0, 1, or 2")
    if any(value not in (MISSING, 0, 1, 2) for row in rows for value in row):
        raise ValueError("genotypes must be -1, 0, 1, or 2")
    return q, rows


def ibs_similarity(
    query: Sequence[int], references: Sequence[Sequence[int]], min_compared: int = 1
) -> Tuple[List[float], List[int]]:
    """Return diploid IBS similarity and compared-marker counts.

    Per-marker IBS is ``1 - abs(query-reference)/2``. Missing genotypes are
    ignored pairwise. Scores with fewer than ``min_compared`` markers are NaN.
    """
    if min_compared < 1:
        raise ValueError("min_compared must be positive")
    q, rows = _rows(query, references)
    scores: List[float] = []
    counts: List[int] = []
    for row in rows:
        pairs = [(a, b) for a, b in zip(q, row) if a >= 0 and b >= 0]
        n = len(pairs)
        counts.append(n)
        if n < min_compared:
            scores.append(float("nan"))
        else:
            scores.append(1.0 - sum(abs(a - b) for a, b in pairs) / (2.0 * n))
    return scores, counts


def hamming_similarity(
    query: Sequence[int], references: Sequence[Sequence[int]], min_compared: int = 1
) -> Tuple[List[float], List[int]]:
    """Return exact-genotype match proportion and compared-marker counts."""
    if min_compared < 1:
        raise ValueError("min_compared must be positive")
    q, rows = _rows(query, references)
    scores: List[float] = []
    counts: List[int] = []
    for row in rows:
        pairs = [(a, b) for a, b in zip(q, row) if a >= 0 and b >= 0]
        n = len(pairs)
        counts.append(n)
        scores.append(sum(a == b for a, b in pairs) / n if n >= min_compared else float("nan"))
    return scores, counts


def binary_jaccard(
    query: Sequence[int], references: Sequence[Sequence[int]], min_compared: int = 1
) -> Tuple[List[float], List[int]]:
    """Return Jaccard similarity for explicitly binary (0/1/-1) fingerprints."""
    if min_compared < 1:
        raise ValueError("min_compared must be positive")
    q = [int(value) for value in query]
    rows = [[int(value) for value in row] for row in references]
    if not q or any(len(row) != len(q) for row in rows):
        raise ValueError("incompatible query/reference shapes")
    if any(value not in (MISSING, 0, 1) for value in q):
        raise ValueError("binary Jaccard accepts only -1, 0, and 1")
    if any(value not in (MISSING, 0, 1) for row in rows for value in row):
        raise ValueError("binary Jaccard accepts only -1, 0, and 1")
    scores: List[float] = []
    counts: List[int] = []
    for row in rows:
        pairs = [(a, b) for a, b in zip(q, row) if a >= 0 and b >= 0]
        n = len(pairs)
        counts.append(n)
        intersection = sum(a == 1 and b == 1 for a, b in pairs)
        union = sum(a == 1 or b == 1 for a, b in pairs)
        scores.append(intersection / union if n >= min_compared and union else float("nan"))
    return scores, counts


def identify_top_k(
    query: Sequence[int],
    reference_matrix: Sequence[Sequence[int]],
    reference_ids: Sequence[str],
    method: str = "ibs",
    top_k: int = 5,
    min_compared: int = 1,
    reject_threshold: Optional[float] = None,
) -> Dict[str, object]:
    """Rank references and optionally apply a pre-calibrated rejection threshold."""
    if len(reference_ids) != len(reference_matrix):
        raise ValueError("reference_ids length must equal number of reference rows")
    if top_k < 1:
        raise ValueError("top_k must be positive")
    methods = {"ibs": ibs_similarity, "hamming": hamming_similarity, "jaccard": binary_jaccard}
    if method not in methods:
        raise ValueError("method must be one of: ibs, hamming, jaccard")
    scores, counts = methods[method](query, reference_matrix, min_compared=min_compared)
    valid = [index for index, score in enumerate(scores) if math.isfinite(score)]
    order = sorted(valid, key=lambda index: (-scores[index], str(reference_ids[index])))
    ranked: List[Dict[str, object]] = []
    query_values = [int(value) for value in query]
    reference_rows = [[int(value) for value in row] for row in reference_matrix]
    for index in order[:top_k]:
        compared = counts[index]
        different = sum(
            query_value >= 0 and reference_value >= 0 and query_value != reference_value
            for query_value, reference_value in zip(query_values, reference_rows[index])
        )
        ranked.append({
            "reference_id": str(reference_ids[index]),
            "similarity": float(scores[index]),
            "n_compared_markers": int(compared),
            "compared_marker_rate": float(compared / len(query_values)),
            "n_different_markers": int(different),
        })
    best = ranked[0] if ranked else None
    accepted = bool(best) and (reject_threshold is None or float(best["similarity"]) >= reject_threshold)
    return {
        "method": method,
        "accepted": accepted,
        "reject_threshold": reject_threshold,
        "best_match": best if accepted else None,
        "top_matches": ranked,
    }


def marker_recall(truth: Sequence[int], observed: Sequence[int]) -> Dict[str, float]:
    """Summarize low-depth marker call rate and genotype concordance."""
    t = [int(value) for value in truth]
    o = [int(value) for value in observed]
    if len(t) != len(o):
        raise ValueError("truth and observed must have the same length")
    if any(value not in (MISSING, 0, 1, 2) for value in t + o):
        raise ValueError("genotypes must be -1, 0, 1, or 2")
    truth_callable = [index for index, value in enumerate(t) if value >= 0]
    compared = [index for index in truth_callable if o[index] >= 0]
    denominator = len(truth_callable)
    called = len(compared)
    correct = sum(t[index] == o[index] for index in compared)
    return {
        "truth_markers": denominator,
        "called_markers": called,
        "correct_genotypes": correct,
        "marker_recall": called / denominator if denominator else float("nan"),
        "genotype_concordance": correct / called if called else float("nan"),
    }
