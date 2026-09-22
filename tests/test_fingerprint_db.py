"""Tests for the fingerprint database and query layer (TASK-041~045)."""
from __future__ import annotations

import contextlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id.database import build_database, connect  # noqa: E402
from ricevar_id.dbquery import FingerprintDatabase  # noqa: E402
from ricevar_id.genotypes import MISSING, GenotypeMatrix, read_matrix_tsv  # noqa: E402

# The system temp directory is not always writable, so temporary workspaces live
# under a repository-local ``.tmp`` directory instead.
TMP_ROOT = ROOT / ".tmp"


def make_temp_dir():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.mkdtemp(prefix="db_", dir=str(TMP_ROOT))


@contextlib.contextmanager
def _temp_dir():
    path = make_temp_dir()
    try:
        yield path
    finally:
        shutil.rmtree(str(path), ignore_errors=True)


MARKERS = [
    "chr01:1000:A:G",
    "chr01:2000:C:T",
    "chr02:3000:G:A",
    "chr02:4000:T:C",
]


def write_matrix(path, samples, rows, markers=None, prefix="pilot"):
    markers = markers or MARKERS
    lines = ["\t".join(["sample_id"] + markers)]
    for sample, row in zip(samples, rows):
        lines.append("\t".join([sample] + [str(value) for value in row]))
    target = Path(path) / ("%s.genotypes_%d.tsv" % (prefix, len(markers)))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_manifest(path, entries):
    lines = ["sample_id\tvariety_name\tsubspecies\trun_accession\tpanel_role"]
    for sample_id, variety, sub, run in entries:
        lines.append("\t".join([sample_id, variety, sub, run, "pilot"]))
    target = Path(path) / "pilot_manifest.tsv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


class TempDirMixin(unittest.TestCase):
    """Give each test a writable workspace without relying on the system temp dir."""

    def setUp(self):
        self._ctx = _temp_dir()
        self.dir = Path(self._ctx.__enter__())
        self.addCleanup(self._ctx.__exit__, None, None, None)


class BuildDatabaseTests(TempDirMixin):
    def setUp(self):
        super().setUp()
        self.matrix = write_matrix(
            self.dir, ["s1", "s2", "s3"],
            [[0, 1, 2, 0], [0, 1, 2, 0], [2, 2, 0, 1]],
        )
        self.manifest = write_manifest(self.dir, [
            ("s1", "VarA", "temperate_japonica", "R1"),
            ("s2", "VarA2", "temperate_japonica", "R2"),
            ("s3", "VarB", "indica", "R3"),
        ])
        self.db = self.dir / "test.sqlite"

    def build(self, **kwargs):
        return build_database(self.db, matrix_tsv=str(self.matrix),
                              manifest_path=str(self.manifest), **kwargs)

    def test_build_records_samples_markers_and_genotypes(self):
        stats = self.build()
        self.assertEqual(stats["samples"], 3)
        self.assertEqual(stats["matrix_markers"], 4)
        self.assertEqual(stats["total_genotypes"], 12)
        conn = connect(self.db)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM sample").fetchone()[0], 3)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM marker").fetchone()[0], 4)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM genotype").fetchone()[0], 12)

    def test_missing_is_stored_as_minus_one_not_imputed(self):
        write_matrix(self.dir, ["s1", "s2", "s3"],
                     [[0, 1, MISSING, 0], [0, 1, 2, 0], [2, 2, 0, 1]])
        self.build()
        conn = connect(self.db)
        self.addCleanup(conn.close)
        row = conn.execute(
            "SELECT dosage FROM genotype WHERE sample_id='s1' AND marker_id=?",
            ("chr02:3000:G:A",),
        ).fetchone()
        self.assertEqual(row[0], -1)

    def test_metadata_records_input_hashes(self):
        self.build()
        conn = connect(self.db)
        self.addCleanup(conn.close)
        metadata = {k: v for k, v in conn.execute("SELECT key, value FROM metadata")}
        self.assertEqual(metadata["matrix_tsv"], str(self.matrix))
        self.assertEqual(len(metadata["matrix_sha256"]), 64)
        self.assertEqual(len(metadata["manifest_sha256"]), 64)
        self.assertEqual(metadata["marker_vcf"], "absent")
        self.assertEqual(metadata["per_query"], "absent")

    def test_marker_set_is_derived_from_filename(self):
        self.build()
        conn = connect(self.db)
        self.addCleanup(conn.close)
        value = conn.execute("SELECT DISTINCT marker_set FROM marker").fetchone()[0]
        self.assertEqual(value, "pilot.4")

    def test_absent_optional_inputs_do_not_create_placeholder_rows(self):
        stats = self.build()
        self.assertEqual(stats["evaluation_rows"], 0)
        conn = connect(self.db)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM evaluation").fetchone()[0], 0)


class QueryLayerTests(TempDirMixin):
    def setUp(self):
        super().setUp()
        self.matrix = write_matrix(
            self.dir, ["s1", "s2", "s3"],
            [[0, 1, 2, 0], [0, 1, 2, 0], [2, 2, 0, 1]],
        )
        self.manifest = write_manifest(self.dir, [
            ("s1", "VarA", "temperate_japonica", "R1"),
            ("s2", "VarA2", "temperate_japonica", "R2"),
            ("s3", "VarB", "indica", "R3"),
        ])
        self.db = self.dir / "test.sqlite"
        build_database(self.db, matrix_tsv=str(self.matrix), manifest_path=str(self.manifest))
        conn = connect(self.db)
        self.addCleanup(conn.close)
        self.api = FingerprintDatabase(conn)

    def test_identify_recovers_the_exact_reference_sample(self):
        query = GenotypeMatrix(["q"], MARKERS, [[0, 1, 2, 0]])
        result = self.api.identify(query, min_compared=1)
        self.assertEqual(result["best_match"]["reference_id"], "s1")
        self.assertAlmostEqual(result["best_match"]["similarity"], 1.0)
        self.assertEqual(result["best_match"]["variety_name"], "VarA")
        self.assertEqual(result["best_match"]["n_compared_markers"], 4)

    def test_identify_annotates_every_hit_with_a_variety(self):
        query = GenotypeMatrix(["q"], MARKERS, [[0, 1, 2, 0]])
        result = self.api.identify(query, min_compared=1, top_k=3)
        self.assertTrue(result["top_matches"])
        for hit in result["top_matches"]:
            self.assertIn("variety_name", hit)

    def test_missing_markers_are_never_treated_as_reference(self):
        # Only two markers are covered; similarity must rest on 2 compared sites.
        query = GenotypeMatrix(["q"], [MARKERS[0], MARKERS[1]], [[0, 1]])
        result = self.api.identify(query, min_compared=1)
        self.assertEqual(result["best_match"]["n_compared_markers"], 2)
        self.assertEqual(result["best_match"]["compared_marker_rate"], 0.5)

    def test_marker_outside_frozen_set_is_rejected(self):
        query = GenotypeMatrix(["q"], ["chr09:9999:A:T"], [[0]])
        with self.assertRaises(ValueError):
            self.api.identify(query, min_compared=1)

    def test_min_compared_blocks_weak_matches(self):
        query = GenotypeMatrix(["q"], [MARKERS[0]], [[0]])
        result = self.api.identify(query, min_compared=3)
        self.assertIsNone(result["best_match"])

    def test_empty_database_refuses_to_identify(self):
        empty_db = self.dir / "empty.sqlite"
        conn = sqlite3.connect(str(empty_db))
        conn.executescript(
            (ROOT / "src" / "ricevar_id" / "database.py").read_text(encoding="utf-8")
            .split('SCHEMA = """')[1].split('"""')[0]
        )
        api = FingerprintDatabase(conn)
        self.addCleanup(conn.close)
        self.assertTrue(api.is_empty())
        with self.assertRaises(ValueError):
            api.identify(GenotypeMatrix(["q"], MARKERS, [[0, 1, 2, 0]]))

    def test_compare_varieties_reports_compared_marker_counts(self):
        result = self.api.compare_varieties("VarA", "VarB", min_compared=1)
        self.assertEqual(result["n_pairs_compared"], 1)
        self.assertEqual(result["n_compared_markers"], 4)
        self.assertIsNotNone(result["mean_similarity"])

    def test_compare_varieties_refuses_when_too_few_markers(self):
        result = self.api.compare_varieties("VarA", "VarB", min_compared=99)
        self.assertIsNone(result["mean_similarity"])
        self.assertIsNotNone(result["note"])

    def test_compare_unknown_variety_raises(self):
        with self.assertRaises(KeyError):
            self.api.compare_varieties("Nope", "VarB")

    def test_compare_varieties_honours_the_method_argument(self):
        """Regression: `method` was accepted, defaulted to "ibs", and never used
        -- the body hard-coded Hamming. A caller selecting any method got the
        same number, and the reported label was wrong. Variety-pair similarity
        (thesis section 3.7) and identification similarity (chapter 4) must sit
        on the same, correctly-labelled scale."""
        result = self.api.compare_varieties("VarA", "VarB", method="hamming",
                                            min_compared=1)
        # The chosen method must be reported back for auditability.
        self.assertEqual(result["method"], "hamming")
        with self.assertRaises(ValueError):
            self.api.compare_varieties("VarA", "VarB", method="cosine",
                                       min_compared=1)

    def test_compare_varieties_methods_can_differ_on_real_data(self):
        """Two methods must not be interchangeable; if they always agreed the
        parameter would still be decorative. Insert a 0-vs-1 pair, where
        IBS = 1 - 1/(2n) but Hamming = 1 - 1/n."""
        conn = self.api.conn
        # VarA2 has a single sample; make it differ from VarA sample S? by a
        # 0-vs-1 pair. Use the existing markers so the comparison is valid.
        row = conn.execute(
            "SELECT sample_id FROM sample WHERE variety_name = 'VarA2'").fetchone()
        sample_id = row[0]
        first_marker = MARKERS[0]
        conn.execute("INSERT OR REPLACE INTO genotype (sample_id, marker_id, dosage)"
                     " VALUES (?,?,?)", (sample_id, first_marker, 1))
        conn.commit()
        ibs = self.api.compare_varieties("VarA", "VarA2", method="ibs", min_compared=1)
        ham = self.api.compare_varieties("VarA", "VarA2", method="hamming", min_compared=1)
        self.assertIsNotNone(ibs["mean_similarity"])
        self.assertIsNotNone(ham["mean_similarity"])
        self.assertGreaterEqual(ibs["mean_similarity"], ham["mean_similarity"])
        self.assertNotEqual(ibs["mean_similarity"], ham["mean_similarity"])

    def test_variety_listing_is_grouped(self):
        varieties = {row[0] for row in self.api.list_varieties()}
        self.assertEqual(varieties, {"VarA", "VarA2", "VarB"})

    def test_counts_reports_call_rate_inputs(self):
        counts = self.api.counts()
        self.assertEqual(counts["samples"], 3)
        self.assertEqual(counts["markers"], 4)
        self.assertEqual(counts["called_genotypes"], 12)


class BuildCliTests(unittest.TestCase):
    def test_cli_builds_database_and_summary(self):
        with _temp_dir() as tmp:
            tmp_dir = Path(tmp)
            matrix = write_matrix(tmp_dir, ["s1", "s2"], [[0, 1, 2, 0], [2, 2, 0, 1]])
            manifest = write_manifest(tmp_dir, [
                ("s1", "VarA", "temperate_japonica", "R1"),
                ("s2", "VarB", "indica", "R2"),
            ])
            out = tmp_dir / "out.sqlite"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_database.py"),
                 "--matrix", str(matrix), "--manifest", str(manifest), "--out", str(out)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.exists())
            summary = json.loads(out.with_suffix(".summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["samples"], 2)
            self.assertEqual(summary["matrix_markers"], 4)

    def test_cli_rejects_missing_matrix(self):
        with _temp_dir() as tmp:
            manifest = write_manifest(Path(tmp), [("s1", "VarA", "x", "R1")])
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_database.py"),
                 "--matrix", str(Path(tmp) / "nope.tsv"), "--manifest", str(manifest),
                 "--out", str(Path(tmp) / "out.sqlite")],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("不存在", proc.stderr)


class MatrixLabelTests(unittest.TestCase):
    def test_marker_set_derived_from_filename(self):
        with _temp_dir() as tmp:
            path = write_matrix(Path(tmp), ["s1"], [[0, 1, 2, 0]])
            self.assertEqual(read_matrix_tsv(path).marker_set, "pilot.4")

    def test_explicit_marker_set_overrides_filename(self):
        with _temp_dir() as tmp:
            path = write_matrix(Path(tmp), ["s1"], [[0, 1, 2, 0]])
            self.assertEqual(read_matrix_tsv(path, marker_set="frozen").marker_set, "frozen")


if __name__ == "__main__":
    unittest.main()
