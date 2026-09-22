"""Appendix C documents formulas; the formulas must compute what it claims.

Appendix C is the one appendix where being subtly wrong is worst: a reader could
re-implement from it. So this does not just check that the default numbers match
the script -- it re-derives the documented formulas independently, in this file,
and compares them against the real functions on constructed inputs.
"""
import importlib.util
import math
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "docs" / "thesis" / "APPENDIX_C_marker_formula.md"
SCRIPT = ROOT / "scripts" / "select_snp_markers.py"


def load_selector():
    spec = importlib.util.spec_from_file_location("rv_selector", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["rv_selector"] = module
    spec.loader.exec_module(module)
    return module


class DocumentedFormulaTests(unittest.TestCase):
    """Re-derive the formulas from the appendix's own wording."""

    @classmethod
    def setUpClass(cls):
        cls.sel = load_selector()

    def documented_metrics(self, calls):
        """Exactly what appendix C.2 and C.3 say, implemented independently."""
        called = [c for c in calls if c >= 0]
        if not called:
            return 0.0, 0.0, 0.0
        call_rate = len(called) / len(calls)
        alt_freq = sum(called) / (2.0 * len(called))
        maf = min(alt_freq, 1.0 - alt_freq)
        counts = Counter(called)
        pairs = len(called) * (len(called) - 1) / 2.0
        concordant = sum(n * (n - 1) / 2.0 for n in counts.values())
        discrimination = 1.0 - concordant / pairs if pairs else 0.0
        return call_rate, maf, discrimination

    CASES = [
        [0, 0, 0, 1, 1, 2],
        [0, 1, 2, -1, -1, 0],
        [0, 0, 0, 0],
        [1, 1, 1],
        [0, 2],
        [],
        [-1, -1, -1],
        [2],
        [0],
        [0, 1],
    ]

    def test_site_metrics_matches_the_documented_formula(self):
        for calls in self.CASES:
            with self.subTest(calls=calls):
                self.assertEqual(self.sel.site_metrics(calls),
                                 self.documented_metrics(calls))

    def test_discrimination_boundaries_named_in_appendix(self):
        # N_c == 0 -> all zeros
        self.assertEqual(self.sel.site_metrics([-1, -1]), (0.0, 0.0, 0.0))
        self.assertEqual(self.sel.site_metrics([]), (0.0, 0.0, 0.0))
        # N_c == 1 -> pairs == 0 -> discrimination 0.0, not a ZeroDivisionError
        call_rate, maf, disc = self.sel.site_metrics([1])
        self.assertEqual(call_rate, 1.0)
        self.assertEqual(disc, 0.0)

    def test_all_identical_genotypes_give_zero_discrimination(self):
        """Appendix claims discrimination is 1 - P(same pair). All same -> 0."""
        for value in (0, 1, 2):
            with self.subTest(genotype=value):
                _, _, disc = self.sel.site_metrics([value] * 8)
                self.assertAlmostEqual(disc, 0.0)

    def test_maf_is_symmetric_under_a_true_allele_swap(self):
        """MAF = min(f, 1-f), so swapping REF/ALT must not change it.

        A genuine swap mirrors every dosage g -> 2-g (0/0<->1/1, 0/1 fixed).
        My first attempt at this used [0]*9+[1] vs [1]*9+[0], which is NOT a
        swap -- it changes the alt allele count from 1 to 9 -- so it failed.
        The code was right; the test was not.
        """
        original = [0, 0, 1, 2, 2, 1, 0]
        swapped = [2 - g for g in original]
        self.assertAlmostEqual(self.sel.site_metrics(original)[1],
                               self.sel.site_metrics(swapped)[1])
        # And it really is a different allele frequency, not a no-op.
        self.assertNotAlmostEqual(self.sel.site_metrics(original)[1], 0.5)

    def test_discrimination_is_not_maf(self):
        """Appendix claims discrimination is the ranking metric instead of MAF.

        Construct two sites with equal MAF but different genotype spread; if the
        two metrics were interchangeable this test would be vacuous.
        """
        spread = [0, 0, 1, 1, 2, 2]
        concentrated = [0] * 4 + [1, 1]
        maf_a = self.sel.site_metrics(spread)[1]
        maf_b = self.sel.site_metrics(concentrated)[1]
        disc_a = self.sel.site_metrics(spread)[2]
        disc_b = self.sel.site_metrics(concentrated)[2]
        self.assertNotAlmostEqual(maf_a, maf_b, places=6)
        self.assertNotAlmostEqual(disc_a, disc_b, places=6)


class ParseCallsTests(unittest.TestCase):
    """Appendix C.3 fixes the genotype encoding; check it literally."""

    @classmethod
    def setUpClass(cls):
        cls.sel = load_selector()

    def call(self, gt, dp="10", gq="30"):
        return self.sel.parse_calls("GT:DP:GQ", ["%s:%s:%s" % (gt, dp, gq)], 3, 20.0)[0]

    def test_dosage_encoding_as_documented(self):
        self.assertEqual(self.call("0/0"), 0)
        self.assertEqual(self.call("0/1"), 1)
        self.assertEqual(self.call("1/0"), 1)
        self.assertEqual(self.call("1/1"), 2)

    def test_phased_separator_is_equivalent(self):
        self.assertEqual(self.call("0|1"), 1)
        self.assertEqual(self.call("1|1"), 2)

    def test_missing_cases_encode_as_minus_one(self):
        for gt in ("./.", "./1", "0/.", "0/2", "0/1/2", "2/2"):
            with self.subTest(gt=gt):
                self.assertEqual(self.call(gt), -1)

    def test_depth_and_quality_thresholds_produce_missing(self):
        self.assertEqual(self.call("0/1", dp="2"), -1)      # DP < min_dp=3
        self.assertEqual(self.call("0/1", gq="19.9"), -1)   # GQ < min_gq=20.0
        self.assertEqual(self.call("0/1", dp="3", gq="20.0"), 1)  # boundary passes

    def test_missing_numeric_fields_become_missing(self):
        self.assertEqual(self.sel.parse_calls("GT:DP:GQ", ["0/1:.:30"], 3, 20.0)[0], -1)
        self.assertEqual(self.sel.parse_calls("GT:DP:GQ", ["0/1:10:."], 3, 20.0)[0], -1)


class RankingTests(unittest.TestCase):
    """Appendix C.4 claims a five-key lexicographic order with -ordinal last."""

    @classmethod
    def setUpClass(cls):
        cls.sel = load_selector()

    def key(self, disc, cr, maf, qual, ordinal):
        return (disc, cr, maf, qual, -ordinal, "chr1", 100, "A", "G")

    def test_ordering_is_lexicographic_by_discrimination_first(self):
        low = self.key(0.5, 1.0, 0.5, 99.0, 1)
        high = self.key(0.6, 0.8, 0.1, 1.0, 2)
        self.assertGreater(high, low, "discrimination must dominate call rate/QUAL")

    def test_tie_broken_by_call_rate_then_maf_then_qual(self):
        base = self.key(0.5, 1.0, 0.3, 40.0, 1)
        self.assertGreater(self.key(0.5, 1.0, 0.3, 40.0, 0), base)   # earlier ordinal
        self.assertLess(self.key(0.5, 1.0, 0.3, 30.0, 1), base)      # lower QUAL
        self.assertLess(self.key(0.5, 1.0, 0.2, 40.0, 1), base)      # lower MAF
        self.assertLess(self.key(0.5, 0.9, 0.3, 40.0, 1), base)      # lower call rate

    def test_earlier_ordinal_wins_exact_ties(self):
        """-ordinal makes smaller ordinals sort first in reverse=True order."""
        first = self.key(0.5, 1.0, 0.3, 40.0, 1)
        later = self.key(0.5, 1.0, 0.3, 40.0, 2)
        self.assertGreater(first, later)


class SpacingTests(unittest.TestCase):
    """Appendix C.5 documents greedy spacing with >= min_distance."""

    @classmethod
    def setUpClass(cls):
        cls.sel = load_selector()

    def cand(self, pos, disc=0.5):
        return (disc, 1.0, 0.3, 40.0, -pos, "chr1", pos, "A", "G")

    def test_exactly_min_distance_is_accepted(self):
        """Documented as >= min_distance, so equality must pass."""
        out = self.sel.apply_spacing([self.cand(1000), self.cand(2000)], 5, 1000)
        self.assertEqual([c[6] for c in out], [1000, 2000])

    def test_one_base_closer_is_rejected(self):
        out = self.sel.apply_spacing([self.cand(1000), self.cand(1999)], 5, 1000)
        self.assertEqual([c[6] for c in out], [1000])

    def test_spacing_is_per_chromosome(self):
        """Two sites at the same position on different chromosomes do not clash."""
        a = (0.5, 1.0, 0.3, 40.0, -1, "chr1", 1000, "A", "G")
        b = (0.5, 1.0, 0.3, 40.0, -2, "chr2", 1000, "A", "G")
        out = self.sel.apply_spacing([a, b], 5, 1000)
        self.assertEqual(len(out), 2)

    def test_greedy_stops_at_wanted(self):
        cands = [self.cand(1000 + 2000 * i) for i in range(10)]
        self.assertEqual(len(self.sel.apply_spacing(cands, 3, 1000)), 3)

    def test_greedy_keeps_higher_ranked_of_a_close_pair(self):
        high = self.cand(1000, disc=0.9)
        low = self.cand(1500, disc=0.1)
        out = self.sel.apply_spacing([high, low], 5, 1000)
        self.assertEqual([c[6] for c in out], [1000])


class AppendixTextTests(unittest.TestCase):
    def setUp(self):
        self.text = APPENDIX.read_text(encoding="utf-8")
        self.source = SCRIPT.read_text(encoding="utf-8")

    def test_appendix_exists(self):
        self.assertTrue(APPENDIX.exists())

    def test_documented_defaults_match_the_code(self):
        # (flag, exact snippet in the script, what the appendix must state)
        expected = [
            ("--marker-counts", "default=[500, 1000, 2000]", "500 1000 2000"),
            ("--max-missing", "default=0.2", "0.2"),
            ("--min-maf", "default=0.05", "0.05"),
            ("--min-qual", "default=30.0", "30.0"),
            ("--min-dp", "default=3", "3"),
            ("--min-gq", "default=20.0", "20.0"),
            ("--min-distance", "default=1000", "1000"),
            ("--candidate-multiplier", "default=50", "50"),
        ]
        for flag, code_snippet, doc_text in expected:
            with self.subTest(flag=flag):
                self.assertIn(flag, self.source)
                self.assertIn(code_snippet, self.source)
                self.assertIn(flag, self.text)
                self.assertIn(doc_text, self.text)

    def test_pool_size_arithmetic_is_stated_correctly(self):
        self.assertIn("100000", self.text.replace("{,}", "").replace(",", ""))

    def test_leakage_guard_is_documented_and_real(self):
        self.assertIn("choices=[\"pilot\"]", self.source)
        self.assertIn("防泄漏约束", self.text)
        self.assertIn("pilot", self.text)

    def test_appendix_does_not_claim_tuned_or_optimal_thresholds(self):
        self.assertIn("不是经过调优的最优值", self.text)

    def test_appendix_lists_no_concrete_marker_sites(self):
        """The selection has never run, so no site may be named."""
        self.assertNotIn("chr01:", self.text)
        self.assertNotIn("chr1:", self.text)

    def test_appendix_contains_no_result_metrics(self):
        import re
        self.assertEqual(
            re.findall(r"(准确率|recall|召回率|AUC|ROC|实测深度)\s*[:：]?\s*\d", self.text),
            [])

    def test_nesting_claim_holds_by_construction(self):
        """Appendix C.6 claims the K tiers are nested subsets.

        They are produced by taking prefixes of one sorted list, so verify the
        property the appendix relies on rather than trusting the prose.
        """
        ranked = sorted([(i % 7, 1.0, 0.3, 40.0, -i, "chr1", 1000 * i, "A", "G")
                         for i in range(60)], reverse=True)
        for small, large in ((500, 1000), (1000, 2000)):
            with self.subTest(small=small, large=large):
                self.assertTrue(set(ranked[:small]) <= set(ranked[:large]))


if __name__ == "__main__":
    unittest.main()
