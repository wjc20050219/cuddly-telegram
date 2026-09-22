"""End-to-end test of the path the Streamlit prototype follows.

The prototype itself needs Streamlit, which is only available in the ``ricevar``
conda environment on the server. These tests cover the same code path directly:
uploaded table -> parser -> fingerprint database -> identification result.
"""
from __future__ import annotations

import contextlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id.database import build_database, connect  # noqa: E402
from ricevar_id.dbquery import FingerprintDatabase  # noqa: E402
from ricevar_id.query_input import parse_genotype_table  # noqa: E402

TMP_ROOT = ROOT / ".tmp"

MARKERS = ["chr01:1000:A:G", "chr01:2000:C:T", "chr02:3000:G:A", "chr02:4000:T:C"]


@contextlib.contextmanager
def _temp_dir():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="e2e_", dir=str(TMP_ROOT)))
    try:
        yield path
    finally:
        shutil.rmtree(str(path), ignore_errors=True)


def build_reference(directory):
    header = "\t".join(["sample_id"] + MARKERS)
    rows = [
        "s1\t0\t1\t2\t0",
        "s2\t0\t1\t2\t0",
        "s3\t2\t2\t0\t1",
    ]
    matrix = directory / "pilot.genotypes_4.tsv"
    matrix.write_text("\n".join([header] + rows) + "\n", encoding="utf-8")

    manifest = directory / "pilot_manifest.tsv"
    manifest.write_text(
        "\n".join([
            "sample_id\tvariety_name\tsubspecies\trun_accession\tpanel_role",
            "s1\tVarA\ttemperate_japonica\tR1\tpilot",
            "s2\tVarA2\ttemperate_japonica\tR2\tpilot",
            "s3\tVarB\tindica\tR3\tpilot",
        ]) + "\n",
        encoding="utf-8",
    )

    db = directory / "ricevar_id.sqlite"
    build_database(db, matrix_tsv=str(matrix), manifest_path=str(manifest))
    conn = connect(db)
    return FingerprintDatabase(conn), conn


class PrototypePathTests(unittest.TestCase):
    def setUp(self):
        self._ctx = _temp_dir()
        self.dir = Path(self._ctx.__enter__())
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.api, self.conn = build_reference(self.dir)
        self.addCleanup(self.conn.close)

    def test_uploaded_table_identifies_the_source_variety(self):
        text = "\t".join(["sample_id"] + MARKERS) + "\nquery\t0\t1\t2\t0\n"
        query = parse_genotype_table(text)
        result = self.api.identify(query, min_compared=1)
        self.assertEqual(result["best_match"]["variety_name"], "VarA")
        self.assertAlmostEqual(result["best_match"]["similarity"], 1.0)

    def test_uploaded_table_with_gaps_reports_honest_coverage(self):
        # Only the first two markers were covered at low depth.
        text = "\t".join(["sample_id", MARKERS[0], MARKERS[1]]) + "\nquery\t0\t1\n"
        query = parse_genotype_table(text)
        result = self.api.identify(query, min_compared=1)
        best = result["best_match"]
        self.assertEqual(best["n_compared_markers"], 2)
        self.assertEqual(best["compared_marker_rate"], 0.5)

    def test_all_missing_query_cannot_be_identified(self):
        text = "\t".join(["sample_id"] + MARKERS) + "\nquery\tNA\tNA\tNA\tNA\n"
        query = parse_genotype_table(text)
        result = self.api.identify(query, min_compared=1)
        self.assertIsNone(result["best_match"])

    def test_min_compared_guard_applies_to_uploaded_queries(self):
        text = "\t".join(["sample_id", MARKERS[0]]) + "\nquery\t0\n"
        query = parse_genotype_table(text)
        result = self.api.identify(query, min_compared=50)
        self.assertIsNone(result["best_match"])

    def test_unknown_marker_in_upload_is_rejected(self):
        text = "sample_id\tchr09:9999:A:T\nquery\t0\n"
        query = parse_genotype_table(text)
        with self.assertRaises(ValueError):
            self.api.identify(query, min_compared=1)

    def test_database_counts_are_visible_to_the_overview_panel(self):
        counts = self.api.counts()
        self.assertEqual(counts["samples"], 3)
        self.assertEqual(counts["varieties"], 3)
        self.assertEqual(counts["markers"], 4)
        self.assertEqual(counts["evaluation_rows"], 0)

    def test_depth_table_is_empty_before_identification_runs(self):
        self.assertEqual(self.api.evaluation_by_depth(), [])


if __name__ == "__main__":
    unittest.main()
