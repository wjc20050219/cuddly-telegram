"""Reverse verification: prove the dbquery/fingerprint method tests catch the
real defect (a `method` parameter that was accepted and silently ignored).

A test that only ever passes is worthless. This restores the ORIGINAL
hard-coded-Hamming body of ``compare_varieties`` in a local subclass and
confirms the observable behaviour really does regress -- i.e. the new tests are
load-bearing, not decorative.

It is a normal TestCase so ``unittest discover`` runs it with everything else.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id import database as db
from ricevar_id import dbquery

MARKERS = ["m1", "m2", "m3"]


def build_conn():
    """Three samples: VarA{S1,S2} and VarB{S3}.

    S1 vs S3 must DISCRIMINATE IBS from Hamming. A pure 0-vs-2 fixture does not
    (both give 0). A 0-vs-1 pair separates them because it has |a-b| = 1 yet
    still counts as one differing position:
        query [0,0] vs [1,0]: IBS = 1 - 1/4 = 0.75 ; Hamming = 1 - 1/2 = 0.50
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA)
    for sid, var in (("S1", "VarA"), ("S2", "VarA"), ("S3", "VarB")):
        conn.execute(
            "INSERT INTO sample (sample_id, variety_name, subspecies, run_accession, panel_role)"
            " VALUES (?,?,?,?,?)", (sid, var, "japonica", "ERR" + sid, "pilot"))
    for m in MARKERS:
        conn.execute("INSERT INTO marker (marker_id, chrom, pos, ref, alt, marker_set)"
                     " VALUES (?,?,?,?,?,?)", (m, "chr1", 1, "A", "G", "500"))
    rows = {"S1": [0, 0, 0], "S2": [0, 0, 0], "S3": [1, 0, 0]}
    for sid, vals in rows.items():
        for m, v in zip(MARKERS, vals):
            conn.execute("INSERT OR REPLACE INTO genotype (sample_id, marker_id, dosage)"
                         " VALUES (?,?,?)", (sid, m, v))
    conn.commit()
    return conn


# The pre-fix implementation: accepts `method`, defaults to "ibs", never uses it.
BUGGY_BODY = '''
def _buggy_compare(self, variety_a, variety_b, method="ibs", min_compared=50):
    samples_a = [row[0] for row in self.samples_of(variety_a)]
    samples_b = [row[0] for row in self.samples_of(variety_b)]
    if not samples_a or not samples_b:
        raise KeyError("unknown variety")
    reference = self.reference_matrix()
    index = {sample: i for i, sample in enumerate(reference.samples)}
    rows_a = [reference.rows[index[s]] for s in samples_a]
    rows_b = [reference.rows[index[s]] for s in samples_b]
    scores = []
    compared_union = 0
    different_union = 0
    for row_a in rows_a:
        for row_b in rows_b:
            compared = [(x, y) for x, y in zip(row_a, row_b) if x >= 0 and y >= 0]
            if len(compared) < min_compared:
                continue
            different = sum(1 for x, y in compared if x != y)
            scores.append(1.0 - different / float(len(compared)))
            compared_union += len(compared)
            different_union += different
    return {
        "variety_a": variety_a, "variety_b": variety_b,
        "samples_a": samples_a, "samples_b": samples_b,
        "n_pairs_compared": len(scores),
        "n_pairs_total": len(rows_a) * len(rows_b),
        "n_compared_markers": compared_union,
        "n_different_markers": different_union,
        "mean_similarity": (sum(scores) / len(scores)) if scores else None,
        "min_compared": min_compared, "note": None if scores else "too few",
    }
'''


class MethodParameterReverseTests(unittest.TestCase):
    def setUp(self):
        self._ns = {}
        exec(BUGGY_BODY, self._ns)
        self.buggy = self._ns["_buggy_compare"]

    def test_baseline_fixture_really_discriminates_the_two_methods(self):
        """Guard against an ineffective mutation: if the fixture made IBS and
        Hamming agree, every reverse check below would be vacuous."""
        api = dbquery.FingerprintDatabase(build_conn())
        ibs = api.compare_varieties("VarA", "VarB", method="ibs", min_compared=1)
        ham = api.compare_varieties("VarA", "VarB", method="hamming", min_compared=1)
        self.assertNotEqual(ibs["mean_similarity"], ham["mean_similarity"],
                            "fixture cannot tell IBS from Hamming")
        self.assertAlmostEqual(ibs["mean_similarity"], 0.8333333333333334)
        self.assertAlmostEqual(ham["mean_similarity"], 0.6666666666666666)

    def test_buggy_implementation_ignores_the_method(self):
        """The pre-fix body returns identical numbers for both methods, which
        is exactly the defect. If this ever stops holding, the reverse test
        below has lost its power."""
        api = dbquery.FingerprintDatabase(build_conn())
        api.compare_varieties = lambda *a, **k: self.buggy(api, *a, **k)
        ibs = api.compare_varieties("VarA", "VarB", method="ibs", min_compared=1)
        ham = api.compare_varieties("VarA", "VarB", method="hamming", min_compared=1)
        self.assertEqual(ibs["mean_similarity"], ham["mean_similarity"])
        self.assertNotIn("method", ibs)
        # And it silently accepts a nonsense method.
        nonsense = api.compare_varieties("VarA", "VarB", method="cosine",
                                         min_compared=1)
        self.assertIsNotNone(nonsense["mean_similarity"])

    def test_fixed_implementation_is_distinguishable_from_the_buggy_one(self):
        """The whole point: the fixed code must differ observably from the
        pre-fix code, otherwise the new assertions prove nothing."""
        api = dbquery.FingerprintDatabase(build_conn())
        fixed = api.compare_varieties("VarA", "VarB", method="ibs", min_compared=1)
        buggy = self.buggy(api, "VarA", "VarB", method="ibs", min_compared=1)
        # The buggy body computes Hamming, so it matches the HAMMING result and
        # not the IBS one.
        self.assertNotAlmostEqual(fixed["mean_similarity"], buggy["mean_similarity"])
        self.assertIn("method", fixed)
        self.assertNotIn("method", buggy)


if __name__ == "__main__":
    unittest.main()
