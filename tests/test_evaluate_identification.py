"""Synthetic end-to-end tests for the low-depth identification layer.

These tests build a tiny frozen marker panel, a Pilot reference matrix, and
fake ``bcftools``-style low-depth VCFs entirely in a temporary directory. They
verify that the evaluation script reports honest numbers: missing markers stay
missing, degraded queries lose recall, and a rejected query is not reported as
a match.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_identification.py"
# Route every temp dir through the project .tmp so the Windows sandbox can
# create it; a bare TemporaryDirectory() resolves to the CWD and raises
# PermissionError here.
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id.genotypes import (  # noqa: E402
    MISSING,
    GenotypeMatrix,
    merge_vcf_genotypes,
    read_matrix_tsv,
    read_vcf_genotypes,
)

VCF_HEADER = """##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype quality">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{sample}
"""

MARKERS = [
    ("chr01", 1000, "A", "G"),
    ("chr01", 5000, "C", "T"),
    ("chr01", 9000, "G", "A"),
    ("chr02", 2000, "T", "C"),
    ("chr02", 6000, "A", "T"),
    ("chr03", 3000, "C", "G"),
]


def write_vcf(path: Path, sample: str, calls, depth: int = 30, gq: int = 40) -> None:
    """Write a VCF with one line per marker; ``calls`` maps index -> dosage."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(VCF_HEADER.format(sample=sample))
        for index, (chrom, pos, ref, alt) in enumerate(MARKERS):
            dosage = calls.get(index, MISSING)
            if dosage == MISSING:
                gt = "./."
            else:
                alleles = {0: "0/0", 1: "0/1", 2: "1/1"}[dosage]
                gt = alleles
            handle.write(
                "\t".join([
                    chrom, str(pos), ".", ref, alt, "60", "PASS", ".", "GT:DP:GQ",
                    "%s:%d:%d" % (gt, depth, gq),
                ]) + "\n"
            )


class GenotypeReaderTests(unittest.TestCase):
    def test_vcf_round_trip_and_missing(self):
        with tempfile.TemporaryDirectory(dir=str(TMP_ROOT)) as tmp:
            path = Path(tmp) / "s1.vcf"
            write_vcf(path, "S1", {0: 0, 1: 1, 3: 2, 5: MISSING})
            matrix = read_vcf_genotypes(path)
            self.assertEqual(matrix.samples, ["S1"])
            self.assertEqual(matrix.n_markers, len(MARKERS))
            self.assertEqual(matrix.rows[0], [0, 1, MISSING, 2, MISSING, MISSING])

    def test_depth_guard_marks_low_evidence_missing(self):
        with tempfile.TemporaryDirectory(dir=str(TMP_ROOT)) as tmp:
            path = Path(tmp) / "s1.vcf"
            write_vcf(path, "S1", {0: 1, 1: 1}, depth=1)
            strict = read_vcf_genotypes(path, min_dp=3)
            self.assertEqual(strict.rows[0][0], MISSING)
            relaxed = read_vcf_genotypes(path)
            self.assertEqual(relaxed.rows[0][0], 1)

    def test_project_fills_absent_markers_with_missing(self):
        matrix = GenotypeMatrix(["S1"], ["chr01:1000:A:G", "chr01:5000:C:T"], [[0, 2]])
        projected = matrix.project(["chr01:1000:A:G", "chr02:2000:T:C", "chr01:5000:C:T"])
        self.assertEqual(projected.markers, ["chr01:1000:A:G", "chr02:2000:T:C", "chr01:5000:C:T"])
        self.assertEqual(projected.rows[0], [0, MISSING, 2])

    def test_project_rejects_markers_outside_frozen_set(self):
        matrix = GenotypeMatrix(["S1"], ["chr01:1000:A:G"], [[0]])
        with self.assertRaises(ValueError):
            matrix.project(["chr09:9999:A:T"])

    def test_merge_keeps_missing_for_absent_records(self):
        with tempfile.TemporaryDirectory(dir=str(TMP_ROOT)) as tmp:
            a = Path(tmp) / "a.vcf"
            b = Path(tmp) / "b.vcf"
            write_vcf(a, "A", {0: 0, 1: 1})
            write_vcf(b, "B", {1: 2, 2: 1})
            merged = merge_vcf_genotypes([a, b])
            index = {marker: position for position, marker in enumerate(merged.markers)}
            self.assertEqual(merged.rows[0][index["chr01:1000:A:G"]], 0)
            self.assertEqual(merged.rows[1][index["chr01:1000:A:G"]], MISSING)
            self.assertEqual(merged.rows[1][index["chr01:5000:C:T"]], 2)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir=str(TMP_ROOT))
        self.tmp = Path(self._tmp.name)
        self.markers = ["%s:%d:%s:%s" % marker for marker in MARKERS]
        # Reference: V1 and V2 differ at every marker; V3 is a copy of V2.
        self.v1 = {i: [0, 1, 2, 0, 1, 2][i] for i in range(len(MARKERS))}
        self.v2 = {i: [2, 0, 0, 2, 2, 0][i] for i in range(len(MARKERS))}
        matrix_path = self.tmp / "pilot.genotypes_6.tsv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["sample_id"] + self.markers)
            writer.writerow(["V1"] + [self.v1[i] for i in range(len(MARKERS))])
            writer.writerow(["V2"] + [self.v2[i] for i in range(len(MARKERS))])
            writer.writerow(["V3"] + [self.v2[i] for i in range(len(MARKERS))])
        self.matrix_path = matrix_path
        self.truth = self.tmp / "truth.tsv"
        with self.truth.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["sample_id", "variety_name"])
            writer.writerow(["V1", "variety_one"])
            writer.writerow(["V2", "variety_two"])
            writer.writerow(["V3", "variety_three"])

    def tearDown(self):
        self._tmp.cleanup()

    def run_script(self, queries, extra=()):
        out = self.tmp / "out"
        truth = extra[0] if extra else None
        command = [
            sys.executable, str(SCRIPT),
            "--reference-matrix", str(self.matrix_path),
            "--query-vcf",
        ] + [str(path) for path in queries] + [
            "--out-dir", str(out),
            "--top-k", "3",
            "--min-compared", "1",
        ]
        if truth is not None:
            command += ["--truth", str(truth)]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return out

    def read_rows(self, out: Path):
        with (out / "per_query.tsv").open("r", encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_clean_query_recovers_source_sample(self):
        query = self.tmp / "q_v1.vcf"
        write_vcf(query, "V1", self.v1)
        out = self.run_script([query], extra=(self.truth,))
        rows = self.read_rows(out)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["best_reference_id"], "V1")
        self.assertEqual(float(rows[0]["best_similarity"]), 1.0)
        self.assertEqual(float(rows[0]["marker_recall"]), 1.0)
        self.assertEqual(float(rows[0]["genotype_concordance"]), 1.0)
        self.assertEqual(rows[0]["top1_correct_sample"], "True")
        self.assertEqual(rows[0]["top1_correct_variety"], "True")

    def test_degraded_query_reports_loss_of_recall(self):
        query = self.tmp / "q_low.vcf"
        # Only the first two markers survive at ultra-low depth.
        write_vcf(query, "V1", {0: self.v1[0], 1: self.v1[1]})
        out = self.run_script([query], extra=(self.truth,))
        rows = self.read_rows(out)
        self.assertAlmostEqual(float(rows[0]["marker_recall"]), 2.0 / len(MARKERS), places=6)
        self.assertEqual(float(rows[0]["genotype_concordance"]), 1.0)

    def test_wrong_genotypes_do_not_match_the_source(self):
        query = self.tmp / "q_bad.vcf"
        write_vcf(query, "V1", {index: self.v2[index] for index in range(len(MARKERS))})
        out = self.run_script([query], extra=(self.truth,))
        rows = self.read_rows(out)
        self.assertNotEqual(rows[0]["best_reference_id"], "V1")
        self.assertEqual(rows[0]["top1_correct_variety"], "False")

    def test_reject_threshold_blocks_marginal_match(self):
        query = self.tmp / "q_mix.vcf"
        mixed = {0: self.v1[0], 1: self.v1[1], 2: self.v2[2], 3: self.v2[3], 4: self.v2[4], 5: self.v2[5]}
        write_vcf(query, "V1", mixed)
        out = self.run_script([query], extra=(self.truth,))
        rows = self.read_rows(out)
        self.assertIn(rows[0]["accepted"], ("True", "False"))

        rejected_out = self.tmp / "out_reject"
        completed = subprocess.run([
            sys.executable, str(SCRIPT),
            "--reference-matrix", str(self.matrix_path),
            "--query-vcf", str(query),
            "--out-dir", str(rejected_out),
            "--top-k", "3", "--min-compared", "1",
            "--reject-threshold", "0.99",
        ], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rows = self.read_rows(rejected_out)
        self.assertEqual(rows[0]["accepted"], "False")

    def test_summary_reports_per_depth_accuracy(self):
        deep = self.tmp / "d1.00_r1"
        deep.mkdir()
        shallow = self.tmp / "d0.05_r1"
        shallow.mkdir()
        q_deep = deep / "markers.vcf"
        q_shallow = shallow / "markers.vcf"
        write_vcf(q_deep, "V1", self.v1)
        write_vcf(q_shallow, "V1", {0: self.v1[0]})
        out = self.run_script([q_deep, q_shallow], extra=(self.truth,))
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["n_queries"], 2)
        self.assertIn("1.00", summary["by_depth"])
        self.assertIn("0.05", summary["by_depth"])
        self.assertEqual(summary["by_depth"]["1.00"]["top1_variety_accuracy"], 1.0)
        self.assertLess(
            summary["by_depth"]["0.05"]["mean_marker_recall"],
            summary["by_depth"]["1.00"]["mean_marker_recall"],
        )
        self.assertIn("closed-set", summary["note"])

    def test_unlabelled_query_is_excluded_from_the_accuracy_denominator(self):
        """Regression: an unlabelled query must NOT count as a miss.

        ``summarize`` selects scored rows with
        ``row.get("top1_correct_variety") is not None``. A bare
        ``bool(true_variety and ...)`` made an unlabelled query False rather
        than None, so it entered the denominator as a guaranteed failure and
        understated accuracy. Here two labelled queries are correct and one
        query is unlabelled; accuracy must stay 1.0, not fall to 0.667.
        """
        truth = self.tmp / "truth_partial.tsv"
        with truth.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["sample_id", "variety_name"])
            writer.writerow(["V1", "variety_one"])
            writer.writerow(["V2", ""])            # blank -> unlabelled
            writer.writerow(["V3", "variety_three"])

        # NOTE: V3 is a deliberate copy of V2 in the shared fixture, so a V3
        # query ties between V2 and V3 and cannot be asserted as correct. Build
        # the labelled pair from V1 (unique) and a third distinct sample.
        v4 = {i: [1, 1, 1, 2, 0, 2][i] for i in range(len(MARKERS))}
        with self.matrix_path.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, delimiter="\t", lineterminator="\n").writerow(
                ["V4"] + [v4[i] for i in range(len(MARKERS))])
        with truth.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, delimiter="\t", lineterminator="\n").writerow(
                ["V4", "variety_four"])

        deep = self.tmp / "d1.00_r1"
        deep.mkdir()
        queries = []
        for index, (sample, genotypes) in enumerate(
                (("V1", self.v1), ("V2", self.v2), ("V4", v4)), 1):
            path = deep / ("q%d.vcf" % index)
            write_vcf(path, sample, genotypes)
            queries.append(path)

        out = self.run_script(queries, extra=(truth,))
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        depth = summary["by_depth"]["1.00"]

        self.assertEqual(summary["n_queries"], 3)
        self.assertEqual(summary["n_labelled_queries"], 2)
        self.assertEqual(depth["n_scored"], 2)
        self.assertEqual(depth["n_unlabelled"], 1)
        # V1 and V4 are unique so their top hits are unambiguous; the V2 query
        # is unlabelled. Counting it as a miss would give 0.5.
        self.assertEqual(depth["top1_variety_accuracy"], 1.0)
        self.assertEqual(depth["top5_variety_accuracy"], 1.0)

    def test_truth_table_that_matches_no_query_fails_loudly(self):
        """Regression: a mismatched id space (truth keyed by a different id
        column than the reference matrix) used to produce a well-formed
        summary.json full of 0.0 accuracies. It must abort instead."""
        truth = self.tmp / "truth_wrong_ids.tsv"
        with truth.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["sample_id", "variety_name"])
            writer.writerow(["NOT_A_SAMPLE", "variety_one"])

        query = self.tmp / "q_v1.vcf"
        write_vcf(query, "V1", self.v1)
        out = self.tmp / "out_wrong_truth"
        completed = subprocess.run([
            sys.executable, str(SCRIPT),
            "--reference-matrix", str(self.matrix_path),
            "--query-vcf", str(query),
            "--truth", str(truth),
            "--out-dir", str(out),
            "--top-k", "3", "--min-compared", "1",
        ], capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0,
                            "a truth table matching no query must not pass silently")
        self.assertIn("sample_id", completed.stderr + completed.stdout)
        self.assertFalse((out / "summary.json").exists(),
                         "no summary may be written when the truth table is unusable")

    def test_depth_label_is_parsed_from_the_directory_name(self):
        """depth_from_name drives the per-depth curve; pin the shapes that
        server/05_simulate.sh and 07_identify.sh actually produce."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import evaluate_identification as ev
        cases = {
            "d0.05_r1": 0.05,
            "d1_r2": 1.0,
            "d0.02_r1": 0.02,
            "d0.10_r3": 0.10,
        }
        for part, expected in cases.items():
            path = Path("/x/sim") / part / "ERR1.markers.vcf.gz"
            self.assertEqual(ev.depth_from_name(path), expected, part)
        # A path with no depth component must return None, not invent a depth.
        self.assertIsNone(ev.depth_from_name(Path("/x/results/ERR1.vcf.gz")))


if __name__ == "__main__":
    unittest.main()
