import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ricevar_id.fingerprint import (  # noqa: E402
    binary_jaccard,
    hamming_similarity,
    identify_top_k,
    ibs_similarity,
    marker_recall,
)


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.query = [0, 1, 2, -1]
        self.refs = [[0, 1, 2, 2], [2, 1, 0, 1], [-1, -1, 2, 0]]

    def test_ibs(self):
        scores, counts = ibs_similarity(self.query, self.refs)
        self.assertEqual(counts, [3, 3, 1])
        self.assertAlmostEqual(scores[0], 1.0)
        self.assertAlmostEqual(scores[1], 1.0 / 3.0)
        self.assertAlmostEqual(scores[2], 1.0)

    def test_minimum_compared_prevents_sparse_false_match(self):
        scores, counts = ibs_similarity(self.query, self.refs, min_compared=2)
        self.assertTrue(math.isnan(scores[2]))
        self.assertEqual(counts[2], 1)

    def test_hamming(self):
        scores, _ = hamming_similarity(self.query, self.refs)
        self.assertAlmostEqual(scores[0], 1.0)
        self.assertAlmostEqual(scores[1], 1.0 / 3.0)

    def test_binary_jaccard(self):
        scores, counts = binary_jaccard([1, 0, 1, -1], [[1, 1, 0, 1]])
        self.assertEqual(counts[0], 3)
        self.assertAlmostEqual(scores[0], 1.0 / 3.0)
        with self.assertRaises(ValueError):
            binary_jaccard([2, 0], [[1, 0]])

    def test_identification_and_rejection(self):
        result = identify_top_k(self.query, self.refs[:2], ["A", "B"], min_compared=2, reject_threshold=0.9)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["best_match"]["reference_id"], "A")
        self.assertEqual(result["best_match"]["n_compared_markers"], 3)
        self.assertAlmostEqual(result["best_match"]["compared_marker_rate"], 0.75)
        self.assertEqual(result["best_match"]["n_different_markers"], 0)
        rejected = identify_top_k([2, 1, 0], [[0, 1, 2]], ["A"], reject_threshold=0.9)
        self.assertFalse(rejected["accepted"])
        self.assertIsNone(rejected["best_match"])

    def test_marker_recall(self):
        result = marker_recall([0, 1, 2, -1], [0, -1, 1, 2])
        self.assertEqual(result["truth_markers"], 3)
        self.assertEqual(result["called_markers"], 2)
        self.assertEqual(result["correct_genotypes"], 1)
        self.assertAlmostEqual(result["marker_recall"], 2.0 / 3.0)
        self.assertAlmostEqual(result["genotype_concordance"], 0.5)


class SimilarityBoundaryTests(unittest.TestCase):
    """Properties established by the round-5 falsification audit.

    These pin behaviour that a future refactor could silently change: the
    semantics of n_different_markers, the Jaccard degenerate case, NaN
    handling, and the fact that method choice can flip the Top-1 answer.
    """

    def test_n_different_markers_counts_sites_not_allele_distance(self):
        """n_different_markers and (1-similarity)*n are DIFFERENT quantities.

        IBS scores 1 - sum|a-b|/(2n), so a 0-vs-2 pair costs a full unit, while
        n_different_markers just counts positions that differ. Mixing the two
        in a thesis table would compare incompatible numbers.
        """
        hit = identify_top_k([0, 0], [[1, 2]], ["R"], method="ibs",
                             min_compared=1)["top_matches"][0]
        self.assertEqual(hit["n_different_markers"], 2)      # two positions differ
        self.assertAlmostEqual(hit["similarity"], 0.25)      # sum|a-b| = 3
        # (1 - 0.25) * 2 = 1.5, which is NOT the integer 2.
        self.assertNotAlmostEqual((1.0 - hit["similarity"]) * hit["n_compared_markers"],
                                  hit["n_different_markers"])

    def test_n_different_markers_equals_distance_when_all_pairs_are_0_vs_2(self):
        """The two definitions coincide only in this special case, which is why
        the simple probe above can look like agreement."""
        hit = identify_top_k([0, 0, 0], [[2, 2, 2]], ["R"], method="ibs",
                             min_compared=1)["top_matches"][0]
        self.assertAlmostEqual((1.0 - hit["similarity"]) * hit["n_compared_markers"],
                               hit["n_different_markers"])

    def test_method_choice_can_flip_the_top1_answer(self):
        """IBS and Hamming are not equivalent rankings; the thesis must state
        which method produced a given Top-1 number."""
        query = [0, 0]
        refs = [[1, 1], [0, 2]]          # IBS: tie; Hamming: R2 wins outright
        ibs = identify_top_k(query, refs, ["R1", "R2"], method="ibs",
                             top_k=2, min_compared=1)
        ham = identify_top_k(query, refs, ["R1", "R2"], method="hamming",
                             top_k=2, min_compared=1)
        self.assertEqual(ibs["top_matches"][0]["reference_id"], "R1")
        self.assertEqual(ham["top_matches"][0]["reference_id"], "R2")
        # IBS ties them, so the deterministic id tie-break decides R1.
        self.assertAlmostEqual(ibs["top_matches"][0]["similarity"],
                               ibs["top_matches"][1]["similarity"])

    def test_jaccard_drops_a_degenerate_all_zero_match(self):
        """Documented boundary: with no shared 1s the union is 0, so Jaccard is
        undefined (NaN) and the candidate is dropped from the ranking -- even
        though an all-reference-allele query is a plausible true match. This is
        why Jaccard is reserved for explicit binary presence/absence data."""
        result = identify_top_k([0, 0, 0], [[0, 0, 0], [1, 1, 1]],
                                ["ALLZERO", "ALLONE"], method="jaccard",
                                top_k=5, min_compared=1)
        ids = [m["reference_id"] for m in result["top_matches"]]
        self.assertNotIn("ALLZERO", ids)
        self.assertEqual(ids, ["ALLONE"])

    def test_empty_concordance_is_nan_not_zero(self):
        """A NaN can be filtered; a 0.0 would be averaged in as a real failure."""
        result = marker_recall([0, 1, -1], [-1, -1, -1])
        self.assertTrue(math.isnan(result["genotype_concordance"]))
        self.assertAlmostEqual(result["marker_recall"], 0.0)
        self.assertEqual(result["truth_markers"], 2)
        self.assertEqual(result["called_markers"], 0)

    def test_reject_threshold_is_inclusive_and_keeps_candidates(self):
        query, refs = [0, 0], [[0, 0], [1, 1]]
        at_best = identify_top_k(query, refs, ["P", "Q"], method="ibs",
                                 min_compared=1, reject_threshold=1.0)
        self.assertTrue(at_best["accepted"])
        self.assertIsNotNone(at_best["best_match"])
        above_best = identify_top_k(query, refs, ["P", "Q"], method="ibs",
                                    min_compared=1, reject_threshold=1.0001)
        self.assertFalse(above_best["accepted"])
        self.assertIsNone(above_best["best_match"])
        # A rejected query still exposes its candidates, so a caller must not
        # read top_matches[0] as an accepted identification.
        self.assertTrue(above_best["top_matches"])

    def test_min_compared_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            ibs_similarity([0], [[0]], min_compared=0)
        with self.assertRaises(ValueError):
            hamming_similarity([0], [[0]], min_compared=0)
        with self.assertRaises(ValueError):
            binary_jaccard([0], [[0]], min_compared=0)

    def test_shape_and_value_validation(self):
        with self.assertRaises(ValueError):
            ibs_similarity([], [[0]])                      # empty query
        with self.assertRaises(ValueError):
            ibs_similarity([0, 1], [[0]])                  # length mismatch
        with self.assertRaises(ValueError):
            ibs_similarity([3], [[0]])                     # invalid dosage
        with self.assertRaises(ValueError):
            identify_top_k([0], [[0]], ["A", "B"])         # id/row mismatch
        with self.assertRaises(ValueError):
            identify_top_k([0], [[0]], ["A"], method="cosine")
        with self.assertRaises(ValueError):
            identify_top_k([0], [[0]], ["A"], top_k=0)


if __name__ == "__main__":
    unittest.main()
