"""Appendix A must stay consistent with the panel manifests.

Appendix A is generated, but "generated" is not the same as "correct": the
generator could be run against stale manifests, or edited by hand afterwards.
These tests re-derive every value from the manifests and compare.
"""
import csv
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "docs" / "thesis" / "APPENDIX_A_samples.md"

spec = importlib.util.spec_from_file_location(
    "build_appendix_samples_t", str(ROOT / "scripts" / "build_appendix_samples.py"))
apx = importlib.util.module_from_spec(spec)
sys.modules["build_appendix_samples_t"] = apx
spec.loader.exec_module(apx)


def load(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class GeneratorInvariantTests(unittest.TestCase):
    """The generator's own checks must fire, not merely exist."""

    def setUp(self):
        self.pilot = apx.load(apx.PILOT)
        self.indep = apx.load(apx.INDEPENDENT)

    def clone(self):
        return [dict(r) for r in self.pilot], [dict(r) for r in self.indep]

    def test_real_manifests_pass(self):
        self.assertEqual(apx.verify(self.pilot, self.indep), [])

    def test_variety_overlap_is_detected(self):
        p, i = self.clone()
        i[0]["variety_name"] = p[0]["variety_name"]
        self.assertTrue(any("品种重叠" in m for m in apx.verify(p, i)))

    def test_duplicate_variety_within_a_panel_is_detected(self):
        p, i = self.clone()
        p[1]["variety_name"] = p[0]["variety_name"]
        self.assertTrue(any("重复品种" in m for m in apx.verify(p, i)))

    def test_wrong_panel_size_is_detected(self):
        p, i = self.clone()
        p.pop()
        self.assertTrue(any("pilot" in m for m in apx.verify(p, i)))

    def test_single_end_sample_is_detected(self):
        p, i = self.clone()
        i[3]["paired_or_single"] = "SINGLE"
        self.assertTrue(any("非双端" in m for m in apx.verify(p, i)))

    def test_shallow_sample_is_detected(self):
        p, i = self.clone()
        p[5]["estimated_depth"] = "12.0"
        self.assertTrue(any("低于 20" in m for m in apx.verify(p, i)))

    def test_missing_run_accession_is_detected(self):
        p, i = self.clone()
        i[7]["run_accession"] = ""
        self.assertTrue(any("缺少 run 号" in m for m in apx.verify(p, i)))

    def test_mixed_panel_role_is_detected(self):
        p, i = self.clone()
        p[2]["panel_role"] = "independent_test"
        self.assertTrue(any("panel_role" in m for m in apx.verify(p, i)))

    def test_paired_bytes_are_summed_not_truncated(self):
        """`fastq_bytes` is ';'-separated; a naive int() silently yields 0."""
        row = self.pilot[0]
        parts = [int(x) for x in row["fastq_bytes"].split(";") if x.strip()]
        self.assertGreater(len(parts), 1, "expected a paired-end sample to test on")
        self.assertEqual(apx.declared_bytes(row), sum(parts))


class AppendixContentTests(unittest.TestCase):
    """The shipped appendix must match the manifests row for row."""

    def setUp(self):
        self.text = APPENDIX.read_text(encoding="utf-8")
        self.rows = apx.load(apx.PILOT) + apx.load(apx.INDEPENDENT)
        self.parsed = re.findall(
            r"^\| (\d+) \| `([A-Z]{3}\d+)` \| `([A-Z]{3}\d+)` \| ([^|]+?) \|",
            self.text, re.M)

    def test_appendix_exists(self):
        self.assertTrue(APPENDIX.exists())

    def test_one_row_per_sample(self):
        self.assertEqual(len(self.parsed), len(self.rows))
        self.assertEqual(len(self.parsed), 55)

    def test_no_sample_is_listed_twice(self):
        ids = [sample for _, sample, _, _ in self.parsed]
        self.assertEqual(len(set(ids)), len(ids))

    def test_every_manifest_sample_appears(self):
        self.assertEqual({s for _, s, _, _ in self.parsed},
                         {r["sample_id"] for r in self.rows})

    def test_run_accessions_match(self):
        by_id = {r["sample_id"]: r["run_accession"] for r in self.rows}
        bad = [(s, run) for _, s, run, _ in self.parsed if by_id.get(s) != run]
        self.assertEqual(bad, [])

    def test_variety_names_match(self):
        by_id = {r["sample_id"]: r["variety_name"] for r in self.rows}
        bad = [(s, v.strip()) for _, s, _, v in self.parsed if by_id.get(s) != v.strip()]
        self.assertEqual(bad, [])

    def test_each_table_numbers_from_one(self):
        numbers = [int(n) for n, _, _, _ in self.parsed]
        self.assertEqual(numbers[:30], list(range(1, 31)))
        self.assertEqual(numbers[30:55], list(range(1, 26)))

    def test_claimed_total_matches_declared_bytes(self):
        total = sum(apx.declared_bytes(r) for r in self.rows)
        self.assertIn("%.2f GiB" % (total / float(1024 ** 3)), self.text)

    def test_appendix_contains_no_result_metrics(self):
        """An appendix lists samples; it must not smuggle in measured results."""
        self.assertEqual(
            re.findall(r"(准确率|recall|召回率|AUC|ROC|实测深度)\s*[:：]?\s*\d", self.text),
            [])

    def test_appendix_states_bytes_are_declared_not_measured(self):
        self.assertIn("不是实测下载量", self.text)


if __name__ == "__main__":
    unittest.main()
