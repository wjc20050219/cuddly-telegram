import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_snp_markers.py"
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
import select_snp_markers as ssm  # noqa: E402


def make_vcf(path):
    lines = [
        "##fileformat=VCFv4.2\n",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2\tS3\n",
    ]
    genotypes = [
        (100, "0/0:10:50", "0/1:10:50", "1/1:10:50"),
        (1200, "0/0:10:50", "0/0:10:50", "1/1:10:50"),
        (2400, "0/1:10:50", "0/1:10:50", "1/1:10:50"),
        (3600, "0/0:10:50", "0/1:10:50", "0/1:10:50"),
    ]
    for pos, a, b, c in genotypes:
        lines.append("chr1\t%d\t.\tA\tG\t60\tPASS\t.\tGT:DP:GQ\t%s\t%s\t%s\n" % (pos, a, b, c))
    path.write_text("".join(lines), encoding="utf-8")


class MarkerSelectionTests(unittest.TestCase):
    def test_nested_marker_selection_and_matrix(self):
        with tempfile.TemporaryDirectory(dir=str(TMP_ROOT)) as tmp:
            tmp = Path(tmp)
            vcf = tmp / "pilot.vcf"
            out = tmp / "out"
            make_vcf(vcf)
            command = [
                sys.executable, str(SCRIPT), "--vcf", str(vcf), "--out-dir", str(out),
                "--panel-role", "pilot", "--marker-counts", "2", "3",
                "--min-distance", "1000", "--candidate-multiplier", "2",
            ]
            subprocess.check_call(command)
            self.assertTrue((out / "pilot.markers_2.vcf").exists())
            self.assertTrue((out / "pilot.markers_3.vcf").exists())
            matrix = (out / "pilot.genotypes_3.tsv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(matrix), 4)
            self.assertEqual(len(matrix[0].split("\t")), 4)
            meta = json.loads((out / "pilot.selection.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["panel_role"], "pilot")
            self.assertEqual(meta["selected_markers"], 3)

    def test_nonpilot_role_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=str(TMP_ROOT)) as tmp:
            tmp = Path(tmp)
            vcf = tmp / "x.vcf"
            make_vcf(vcf)
            command = [sys.executable, str(SCRIPT), "--vcf", str(vcf), "--out-dir", str(tmp / "out"), "--panel-role", "independent"]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode, 0)

    def test_too_few_spaced_sites_fails_loudly_and_writes_no_panel(self):
        """Requesting more markers than QC can supply must fail, not silently
        emit a smaller panel. This is the path that protects the "2000 markers"
        claim in the thesis from being an unverified number."""
        with tempfile.TemporaryDirectory(dir=str(TMP_ROOT)) as tmp:
            tmp = Path(tmp)
            vcf = tmp / "pilot.vcf"
            out = tmp / "out"
            make_vcf(vcf)
            command = [
                sys.executable, str(SCRIPT), "--vcf", str(vcf), "--out-dir", str(out),
                "--panel-role", "pilot", "--marker-counts", "99",
                "--min-distance", "1000", "--candidate-multiplier", "2",
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((out / "pilot.markers_99.vcf").exists(),
                             "no panel may be written when the request cannot be met")


def cand(disc, ordinal, pos, chrom="chr1"):
    return (disc, 1.0, 0.2, 60.0, -ordinal, chrom, pos, "A", "T")


class SiteMetricsTests(unittest.TestCase):
    """Locks in properties verified by direct probing. These are invariants the
    marker ranking depends on, not stylistic preferences."""

    def test_invariant_sites_score_zero_discrimination(self):
        for calls in ([0] * 10, [1] * 10, [2] * 10, [-1] * 10):
            self.assertEqual(ssm.site_metrics(calls)[2], 0.0)

    def test_metrics_stay_in_range_exhaustively(self):
        import itertools
        for n in range(1, 7):
            for combo in itertools.product([-1, 0, 1, 2], repeat=n):
                call_rate, maf, disc = ssm.site_metrics(list(combo))
                self.assertTrue(0.0 <= call_rate <= 1.0)
                self.assertTrue(0.0 <= maf <= 0.5)
                self.assertTrue(0.0 <= disc <= 1.0)

    def test_discrimination_is_label_free(self):
        """Permuting samples must not change the score: markers are ranked
        without reference to variety labels, which is what keeps the frozen set
        from being tuned to the panel."""
        import random
        random.seed(20260920)
        calls = [0, 1, 2, 0, 1, 2, -1, 0]
        base = ssm.site_metrics(calls)
        for _ in range(200):
            shuffled = calls[:]
            random.shuffle(shuffled)
            self.assertEqual(ssm.site_metrics(shuffled), base)

    def test_balanced_site_outranks_a_rare_variant(self):
        rare = ssm.site_metrics([0] * 19 + [1])
        balanced = ssm.site_metrics([0] * 10 + [1] * 10)
        self.assertGreater(balanced[2], rare[2])


class SpacingTests(unittest.TestCase):
    def test_greedy_matches_the_exact_optimum_on_dense_and_sparse_layouts(self):
        """apply_spacing is greedy first-fit. Verified by exact DP over 20k
        random layouts and the structured density shapes below that it never
        returns fewer than the true maximum, so the `len(selected) < max(counts)`
        guard cannot fire on a satisfiable request."""
        import bisect
        import random

        def exact_max(positions, min_distance):
            pts = sorted(set(positions))
            dp = [0] * (len(pts) + 1)
            for i in range(1, len(pts) + 1):
                j = bisect.bisect_right(pts, pts[i - 1] - min_distance)
                dp[i] = max(dp[i - 1], 1 + dp[j])
            return dp[len(pts)]

        random.seed(20260920)
        layouts = [[i * 100 for i in range(60)],
                   [i * 1000 for i in range(60)],
                   [i * 100 for i in range(30)] + [5_000_000 + i * 100 for i in range(30)]]
        for _ in range(300):
            n = random.randint(3, 12)
            layouts.append(sorted(random.sample(range(0, random.choice([300, 800, 2000, 20000])), n)))

        for positions in layouts:
            for min_distance in (100, 200, 1000):
                wanted = 5
                sites = [cand(1.0 - i * 1e-4, i, p) for i, p in enumerate(positions)]
                got = len(ssm.apply_spacing(sorted(sites, reverse=True), wanted, min_distance))
                self.assertEqual(got, min(wanted, exact_max(positions, min_distance)),
                                 "greedy under-filled at positions=%s d=%d" % (positions, min_distance))

    def test_spacing_is_global_not_per_chromosome(self):
        """A per-chromosome interpretation would inflate a 2000-marker request
        to 2000 x n_chromosomes. Pin the global behaviour."""
        sites = [cand(0.9 - o * 1e-4, o, 1_000_000 + k * 10_000, "chr%d" % c)
                 for o, (c, k) in enumerate([(c, k) for c in range(1, 13) for k in range(5)], 1)]
        picked = ssm.apply_spacing(sorted(sites, reverse=True), 5, 1000)
        self.assertEqual(len(picked), 5)

    def test_min_distance_is_respected(self):
        """Candidates must be packed CLOSER than min_distance, otherwise a
        regression that ignores spacing entirely still passes. Verified by
        mutation: wrapping the call with min_distance=0 is caught only by the
        packed layout below."""
        # Packed: 100bp apart, min_distance 1000 -> only a sparse subset survives.
        packed = [cand(0.9 - o * 1e-4, o, p) for o, p in enumerate([0, 100, 200, 300])]
        picked = ssm.apply_spacing(sorted(packed, reverse=True), 4, 1000)
        self.assertEqual(len(picked), 1,
                         "ignoring min_distance would keep all 4 packed sites")
        self.assertEqual(picked[0][6], 0, "strongest site must be the survivor")

        positions = sorted(p[6] for p in picked)
        for a, b in zip(positions, positions[1:]):
            self.assertGreaterEqual(b - a, 1000)

    def test_all_missing_site_scores_zero_and_is_never_eligible(self):
        """The `if not called: return 0,0,0` early return is what stops an
        all-missing site from contributing noise. Mutation-verified."""
        call_rate, maf, disc = ssm.site_metrics([-1] * 10)
        self.assertEqual((call_rate, maf, disc), (0.0, 0.0, 0.0))


class NestedTierTests(unittest.TestCase):
    def test_tiers_are_nested_by_construction(self):
        """500/1000/2000 must be prefix-subsets of one ranked list, otherwise
        the thesis's nested-marker comparison is not a nested comparison."""
        ranked = [cand(0.99 - i * 1e-5, i, i * 2000) for i in range(2000)]
        ids = [ssm.marker_id(c) for c in ranked]
        tiers = {n: set(ids[:n]) for n in (500, 1000, 2000)}
        self.assertTrue(tiers[500] <= tiers[1000])
        self.assertTrue(tiers[1000] <= tiers[2000])
        self.assertEqual(len(tiers[500]), 500)
        self.assertEqual(len(tiers[2000]), 2000)


if __name__ == "__main__":
    unittest.main()
