"""Tests for the query-table parser used by the Streamlit prototype."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id.genotypes import MISSING  # noqa: E402
from ricevar_id.query_input import parse_genotype_table  # noqa: E402

HEADER = "sample_id\tchr01:1000:A:G\tchr01:2000:C:T\tchr02:3000:G:A"


class ParseGenotypeTableTests(unittest.TestCase):
    def test_parses_a_normal_table(self):
        matrix = parse_genotype_table(HEADER + "\nq1\t0\t1\t2\n")
        self.assertEqual(matrix.samples, ["q1"])
        self.assertEqual(matrix.n_markers, 3)
        self.assertEqual(matrix.rows[0], [0, 1, 2])

    def test_missing_tokens_become_missing_not_zero(self):
        matrix = parse_genotype_table(HEADER + "\nq1\tNA\t.\t\n")
        self.assertEqual(matrix.rows[0], [MISSING, MISSING, MISSING])

    def test_explicit_minus_one_is_missing(self):
        matrix = parse_genotype_table(HEADER + "\nq1\t-1\t-1\t-1\n")
        self.assertEqual(matrix.rows[0], [MISSING, MISSING, MISSING])

    def test_empty_lines_are_ignored(self):
        matrix = parse_genotype_table(HEADER + "\n\nq1\t0\t1\t2\n\n")
        self.assertEqual(matrix.rows[0], [0, 1, 2])

    def test_sample_id_override(self):
        matrix = parse_genotype_table(HEADER + "\nq1\t0\t1\t2\n", sample_id="custom")
        self.assertEqual(matrix.samples, ["custom"])

    def test_rejects_empty_file(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table("\n\n")
        self.assertIn("空", str(ctx.exception))

    def test_rejects_wrong_first_column(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table("id\tchr01:1000:A:G\nq1\t0\n")
        self.assertIn("sample_id", str(ctx.exception))

    def test_rejects_malformed_marker_column(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table("sample_id\tchr01_1000_A_G\nq1\t0\n")
        self.assertIn("CHROM:POS:REF:ALT", str(ctx.exception))

    def test_rejects_duplicate_marker_columns(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table("sample_id\tchr01:1000:A:G\tchr01:1000:A:G\nq1\t0\t1\n")
        self.assertIn("重复", str(ctx.exception))

    def test_rejects_header_only_file(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table(HEADER + "\n")
        self.assertIn("没有样本行", str(ctx.exception))

    def test_rejects_column_count_mismatch(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table(HEADER + "\nq1\t0\t1\n")
        self.assertIn("列", str(ctx.exception))

    def test_rejects_non_integer_value(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table(HEADER + "\nq1\t0\tx\t2\n")
        self.assertIn("不是整数", str(ctx.exception))

    def test_rejects_out_of_range_dosage(self):
        with self.assertRaises(ValueError) as ctx:
            parse_genotype_table(HEADER + "\nq1\t0\t3\t2\n")
        self.assertIn("0/1/2", str(ctx.exception))

    def test_handles_crlf_line_endings(self):
        matrix = parse_genotype_table(HEADER + "\r\nq1\t0\t1\t2\r\n")
        self.assertEqual(matrix.rows[0], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
