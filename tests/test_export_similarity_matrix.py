"""Tests for scripts/export_similarity_matrix.py (TASK-036/037 prerequisite).

The exporter is the only command-line path that produces the full
variety-by-variety similarity matrix the heatmap and PCA figures need. Two
properties matter most and are asserted here:

1. It must agree exactly with ``compare_varieties``, which is the audited
   implementation used by the web UI -- otherwise the thesis figure and the
   interactive tool would disagree.
2. It must never invent a number. A variety pair with too few shared markers is
   written as an empty cell, because 0.0 would read as "maximally dissimilar"
   rather than "not measured".
"""
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
sys.path.insert(0, str(ROOT / "scripts"))

from ricevar_id import database as db  # noqa: E402
from ricevar_id.dbquery import FingerprintDatabase  # noqa: E402
import export_similarity_matrix as ex  # noqa: E402

TMP_ROOT = ROOT / ".tmp"
SCRIPT = ROOT / "scripts" / "export_similarity_matrix.py"

# Varieties are constructed so IBS and Hamming disagree: VarA vs VarB contains a
# 0-vs-1 pair, whose |a-b| is 1 but which still counts as one differing position.
SAMPLES = [("S1", "VarA"), ("S2", "VarA"), ("S3", "VarB"), ("S4", "VarC")]
MARKERS = ["m%d" % i for i in range(6)]
GENOTYPES = {
    "S1": [0, 0, 1, 1, 2, 2],
    "S2": [0, 0, 1, 1, 2, 2],
    "S3": [1, 0, 1, 2, 2, 2],
    "S4": [2, 2, 2, 2, 2, 2],
}


def make_temp_dir(prefix):
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(TMP_ROOT)))


@contextlib.contextmanager
def temp_dir(prefix="matrix_"):
    path = make_temp_dir(prefix)
    try:
        yield path
    finally:
        shutil.rmtree(str(path), ignore_errors=True)


def build_synth_db(path, genotypes=None, samples=None):
    genotypes = GENOTYPES if genotypes is None else genotypes
    samples = SAMPLES if samples is None else samples
    conn = sqlite3.connect(str(path))
    conn.executescript(db.SCHEMA)
    for sid, var in samples:
        conn.execute(
            "INSERT INTO sample (sample_id, variety_name, subspecies, run_accession, panel_role)"
            " VALUES (?,?,?,?,?)", (sid, var, "japonica", "ERR" + sid, "pilot"))
    for m in MARKERS:
        conn.execute("INSERT INTO marker (marker_id, chrom, pos, ref, alt, marker_set)"
                     " VALUES (?,?,?,?,?,?)", (m, "chr1", 1, "A", "G", "500"))
    for sid, values in genotypes.items():
        for m, value in zip(MARKERS, values):
            conn.execute("INSERT OR REPLACE INTO genotype (sample_id, marker_id, dosage)"
                         " VALUES (?,?,?)", (sid, m, value))
    conn.commit()
    conn.close()
    return path


def run_exporter(*extra):
    return subprocess.run([sys.executable, str(SCRIPT)] + list(extra),
                          capture_output=True, text=True)


class ExporterEquivalenceTests(unittest.TestCase):
    """The fast path must not silently diverge from the audited slow path."""

    def test_pairwise_matches_compare_varieties_for_every_method(self):
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            conn = sqlite3.connect(str(dbp))
            api = FingerprintDatabase(conn)
            varieties = sorted(row[0] for row in api.list_varieties())
            self.assertEqual(varieties, ["VarA", "VarB", "VarC"])

            checked = 0
            for i, a in enumerate(varieties):
                for b in varieties[i:]:
                    for method in ("ibs", "hamming"):
                        mine = ex.pairwise(api, a, b, method=method, min_compared=1)
                        ref = api.compare_varieties(a, b, method=method, min_compared=1)
                        checked += 1
                        self.assertAlmostEqual(mine["mean_similarity"],
                                               ref["mean_similarity"], places=12)
                        self.assertEqual(mine["n_pairs_compared"], ref["n_pairs_compared"])
                        self.assertEqual(mine["n_compared_markers"],
                                         ref["n_compared_markers"])
                        self.assertEqual(mine["n_different_markers"],
                                         ref["n_different_markers"])
            self.assertEqual(checked, 12)
            conn.close()

    def test_jaccard_is_refused_on_dosage_data_with_a_clear_message(self):
        """Jaccard is undefined for 0/1/2 dosage. Fingerprint raises ValueError;
        the CLI must turn that into an actionable message, not a traceback."""
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            out = work / "j.tsv"
            result = run_exporter("--database", str(dbp), "--method", "jaccard",
                                  "--min-compared", "1", "--out", str(out))
            self.assertEqual(result.returncode, 2)
            self.assertIn("Jaccard", result.stderr)
            self.assertIn("ibs", result.stderr)
            self.assertFalse(out.exists(), "refused run must not write output")
            self.assertNotIn("Traceback", result.stderr)


class ExporterOutputTests(unittest.TestCase):
    def test_square_matrix_is_symmetric_with_unit_diagonal(self):
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            out = work / "p.tsv"
            result = run_exporter("--database", str(dbp), "--method", "ibs",
                                  "--min-compared", "1", "--out", str(out))
            self.assertEqual(result.returncode, 0)

            square = out.with_name("p_matrix.tsv").read_text(encoding="utf-8")
            lines = [l.split("\t") for l in square.strip().split("\n")]
            header, body = lines[0], lines[1:]
            self.assertEqual(header[0], "variety")
            names = header[1:]
            self.assertEqual(names, sorted(names))
            self.assertEqual(len(body), len(names))

            grid = {}
            for row in body:
                for name, cell in zip(names, row[1:]):
                    grid[(row[0], name)] = cell
            for name in names:
                self.assertEqual(grid[(name, name)], "1.000000")
            for a in names:
                for b in names:
                    self.assertEqual(grid[(a, b)], grid[(b, a)],
                                     "matrix must be symmetric for %s/%s" % (a, b))

    def test_long_table_reports_full_provenance(self):
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            out = work / "p.tsv"
            run_exporter("--database", str(dbp), "--method", "ibs",
                         "--min-compared", "1", "--out", str(out))
            lines = out.read_text(encoding="utf-8").strip().split("\n")
            header = lines[0].split("\t")
            for field in ("variety_a", "variety_b", "method", "mean_similarity",
                          "n_pairs_compared", "n_compared_markers",
                          "n_different_markers", "note"):
                self.assertIn(field, header)
            # 3 varieties -> 6 unordered pairs (upper triangle incl. diagonal).
            self.assertEqual(len(lines) - 1, 6)
            self.assertTrue(all(row.split("\t")[2] == "ibs" for row in lines[1:]))

            summary = json.loads(
                out.with_name("p_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["method"], "ibs")
            self.assertEqual(summary["n_varieties"], 3)
            self.assertEqual(summary["n_pairs"], 6)
            self.assertEqual(summary["n_pairs_scored"], 6)
            self.assertEqual(summary["n_pairs_skipped"], 0)
            self.assertEqual(summary["n_markers"], 6)

    def test_unusable_pairs_are_blank_not_zero(self):
        """The single most important anti-fabrication property of this script."""
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            out = work / "skip.tsv"
            run_exporter("--database", str(dbp), "--method", "ibs",
                         "--min-compared", "999", "--out", str(out))
            square = out.with_name("skip_matrix.tsv").read_text(encoding="utf-8")
            self.assertNotIn("0.000000", square,
                             "unusable comparisons must not be written as 0.0")
            # NB: strip() removes the trailing tabs of the final row, so split on
            # the raw text and drop only newlines.
            for line in square.rstrip("\n").split("\n")[1:]:
                self.assertEqual(line.split("\t")[1:], ["", "", ""])

            summary = json.loads(
                out.with_name("skip_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["n_pairs_scored"], 0)
            self.assertEqual(summary["n_pairs_skipped"], 6)
            self.assertIsNone(summary["similarity_min"])
            self.assertEqual(len(summary["skipped_pairs"]), 6)

            long_rows = out.read_text(encoding="utf-8").strip().split("\n")[1:]
            for row in long_rows:
                fields = row.split("\t")
                self.assertEqual(fields[3], "", "mean_similarity column must be blank")
                self.assertTrue(fields[-1], "a blank score must carry an explanatory note")

    def test_method_choice_changes_the_numbers(self):
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            ibs_out, ham_out = work / "i.tsv", work / "h.tsv"
            run_exporter("--database", str(dbp), "--method", "ibs",
                         "--min-compared", "1", "--out", str(ibs_out))
            run_exporter("--database", str(dbp), "--method", "hamming",
                         "--min-compared", "1", "--out", str(ham_out))
            ibs = json.loads(ibs_out.with_name("i_summary.json").read_text(encoding="utf-8"))
            ham = json.loads(ham_out.with_name("h_summary.json").read_text(encoding="utf-8"))
            self.assertNotAlmostEqual(ibs["similarity_mean"], ham["similarity_mean"])
            self.assertEqual(ham["method"], "hamming")

    def test_variety_subset_selection(self):
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            out = work / "sub.tsv"
            result = run_exporter("--database", str(dbp), "--min-compared", "1",
                                  "--varieties", "VarA,VarB", "--out", str(out))
            self.assertEqual(result.returncode, 0)
            summary = json.loads(
                out.with_name("sub_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["n_varieties"], 2)
            self.assertEqual(summary["n_pairs"], 3)

    def test_unknown_variety_in_subset_is_rejected(self):
        with temp_dir() as work:
            dbp = build_synth_db(work / "synth.sqlite")
            result = run_exporter("--database", str(dbp), "--min-compared", "1",
                                  "--varieties", "VarA,Nope",
                                  "--out", str(work / "x.tsv"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Nope", result.stderr)


class ExporterRefusalTests(unittest.TestCase):
    """An empty or absent database must produce an error, never a fake matrix."""

    def test_empty_database_refuses_and_writes_nothing(self):
        with temp_dir() as work:
            empty = work / "empty.sqlite"
            conn = sqlite3.connect(str(empty))
            conn.executescript(db.SCHEMA)
            conn.commit()
            conn.close()
            out = work / "empty.tsv"
            result = run_exporter("--database", str(empty), "--out", str(out))
            self.assertEqual(result.returncode, 1)
            self.assertFalse(out.exists())
            self.assertFalse(out.with_name("empty_matrix.tsv").exists())

    def test_single_variety_cannot_form_a_matrix(self):
        with temp_dir() as work:
            only = {k: v for k, v in GENOTYPES.items() if k in ("S1", "S2")}
            samples = [s for s in SAMPLES if s[0] in ("S1", "S2")]
            dbp = build_synth_db(work / "one.sqlite", genotypes=only, samples=samples)
            out = work / "one.tsv"
            result = run_exporter("--database", str(dbp), "--min-compared", "1",
                                  "--out", str(out))
            self.assertEqual(result.returncode, 1)
            self.assertFalse(out.exists())

    def test_missing_database_file_is_an_argument_error(self):
        with temp_dir() as work:
            result = run_exporter("--database", str(work / "nope.sqlite"),
                                  "--out", str(work / "x.tsv"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("不存在", result.stderr)


if __name__ == "__main__":
    unittest.main()
