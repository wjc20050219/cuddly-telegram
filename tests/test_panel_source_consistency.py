# -*- coding: utf-8 -*-
"""Panel manifests must agree with the candidate table they were drawn from.

The admin-facing documents quote download sizes and base counts. Those numbers
are only trustworthy if the manifests they come from actually match their
source (``data/metadata/candidates/candidate_samples.tsv``). Nothing checked
that before this round, and two real problems surfaced while verifying the
one-pager by hand:

* ``DRR771401`` (a DDBJ run) has an **empty** ``SRA_accession`` -- it is keyed
  by ``ENA_accession``. Joining on ``SRA_accession`` alone silently reports it
  as "missing", which is how a stale "26 Gb / 9 GB" figure survived.
* the sizes quoted in ``docs/server_admin_questions.md`` matched neither
  ``base_count`` nor ``fastq_bytes``.

These tests pin the join rule and the numbers the documents quote.
"""
import csv
import io
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDS = ROOT / "data" / "metadata" / "candidates" / "candidate_samples.tsv"
MANIFESTS = {
    "smoke1": ROOT / "data" / "metadata" / "server" / "pilot_smoke1.tsv",
    "smoke5": ROOT / "data" / "metadata" / "server" / "pilot_smoke5.tsv",
    "pilot": ROOT / "data" / "metadata" / "server" / "pilot_manifest.tsv",
    "independent": (ROOT / "data" / "metadata" / "server"
                    / "independent_manifest.tsv"),
}
GiB = 1024 ** 3

# Verified this round from the manifests (declared sizes, never downloaded).
EXPECTED = {
    "smoke1": (1, 2.61),
    "smoke5": (5, 23.19),
    "pilot": (30, 170.70),
    "independent": (25, 164.02),
}


def _rows(path):
    with io.open(str(path), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _sum_bytes(value):
    """fastq_bytes is ';'-separated for paired-end runs."""
    total = 0
    for part in (value or "").split(";"):
        part = part.strip()
        if part.isdigit():
            total += int(part)
    return total


def _join_key(row):
    """The accession to join a manifest run against the candidate table.

    DDBJ runs (DRR*) carry an empty ``SRA_accession``; joining on that field
    alone silently drops them.
    """
    return row["SRA_accession"] or row["ENA_accession"] or row["accession"]


def _file_list(bytes_field, ftp_field):
    """Map URL -> declared bytes, so files can be compared by identity."""
    urls = [u.strip() for u in (ftp_field or "").split(";")]
    sizes = [s.strip() for s in (bytes_field or "").split(";")]
    return {u: s for u, s in zip(urls, sizes)}


class CandidateTableTests(unittest.TestCase):
    def setUp(self):
        self.rows = _rows(CANDS)
        self.by_key = {_join_key(r): r for r in self.rows}

    def test_candidate_table_is_present_and_substantial(self):
        self.assertGreater(len(self.rows), 10000)

    def test_it_carries_the_columns_the_documents_quote(self):
        for col in ("base_count", "fastq_bytes", "estimated_depth",
                    "subspecies", "variety_name"):
            with self.subTest(col=col):
                self.assertIn(col, self.rows[0])

    def test_some_runs_have_no_sra_accession_so_the_fallback_matters(self):
        """If this ever becomes 0, the join rule can be simplified -- and the
        test should be updated deliberately rather than left as folklore."""
        no_sra = [r for r in self.rows if not r["SRA_accession"]]
        self.assertGreater(len(no_sra), 0,
                           "the SRA_accession fallback exists for a reason")
        for r in no_sra:
            with self.subTest(acc=r["accession"]):
                self.assertTrue(_join_key(r))

    def test_join_keys_are_unique(self):
        keys = [_join_key(r) for r in self.rows]
        dupes = {k for k in keys if keys.count(k) > 1}
        self.assertEqual(dupes, set(), "duplicate join keys: %s" % sorted(dupes)[:5])


class ManifestConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.by_key = {_join_key(r): r for r in _rows(CANDS)}

    def test_every_panel_run_is_found_in_the_candidate_table(self):
        """Regression: joining on SRA_accession alone reported DRR771401 missing."""
        for label, path in MANIFESTS.items():
            with self.subTest(panel=label):
                missing = [r["run_accession"] for r in _rows(path)
                           if r["run_accession"] not in self.by_key]
                self.assertEqual(missing, [],
                                 "%s runs absent from candidate table: %s"
                                 % (label, missing))

    def test_manifest_sizes_agree_with_the_candidate_table(self):
        """Manifest sizes must equal the candidate table **or** be the
        documented paired-only normalization.

        `build_server_manifests.select_fastqs()` deliberately drops an
        unsuffixed orphan FASTQ that some paired runs expose alongside the real
        `_1`/`_2` pair, because downloading it wastes space and makes
        provenance ambiguous (see its docstring). `SRR34854885` is exactly such
        a run: ENA lists three files, the manifest keeps two.

        So a blanket "must be byte-identical" assertion is wrong -- but the
        dropped set must be *precisely* the unsuffixed files, never a mate.
        """
        for label, path in MANIFESTS.items():
            for row in _rows(path):
                src = self.by_key[row["run_accession"]]
                with self.subTest(panel=label, run=row["run_accession"]):
                    m_files = _file_list(row["fastq_bytes"], row["fastq_ftp"])
                    c_files = _file_list(src["fastq_bytes"], src["fastq_ftp"])
                    self.assertTrue(
                        set(m_files.items()) <= set(c_files.items()),
                        "manifest invented a file the candidate table lacks")
                    dropped = [u for u in c_files if u not in m_files]
                    for url in dropped:
                        self.assertFalse(
                            url.endswith("_1.fastq.gz")
                            or url.endswith("_2.fastq.gz"),
                            "a real mate was dropped, not just the orphan: %s" % url)

    def test_the_orphan_file_case_is_real_and_still_present(self):
        """Pin the concrete case, so the rule above is not vacuous."""
        hits = []
        for row in _rows(MANIFESTS["pilot"]):
            src = self.by_key[row["run_accession"]]
            n_manifest = len(_file_list(row["fastq_bytes"], row["fastq_ftp"]))
            n_source = len(_file_list(src["fastq_bytes"], src["fastq_ftp"]))
            if n_manifest != n_source:
                hits.append((row["run_accession"], n_manifest, n_source))
        self.assertTrue(hits, "the orphan case vanished -- re-check this rule")
        for run, n_manifest, n_source in hits:
            with self.subTest(run=run):
                self.assertEqual(n_manifest, 2)
                self.assertEqual(n_source, 3)

    def test_declared_panel_sizes_match_what_the_documents_quote(self):
        for label, (n, gib) in EXPECTED.items():
            path = MANIFESTS[label]
            rows = _rows(path)
            with self.subTest(panel=label):
                self.assertEqual(len(rows), n)
                total = sum(_sum_bytes(r["fastq_bytes"]) for r in rows)
                self.assertAlmostEqual(total / GiB, gib, places=2)

    def test_panels_do_not_overlap(self):
        pilot = {r["run_accession"] for r in _rows(MANIFESTS["pilot"])}
        indep = {r["run_accession"] for r in _rows(MANIFESTS["independent"])}
        self.assertEqual(pilot & indep, set(),
                         "the independent panel must not reuse pilot samples")


class DocumentedNumberTests(unittest.TestCase):
    """The admin documents quote these figures; keep them honest."""

    def setUp(self):
        self.admin = (ROOT / "docs" / "server_admin_questions.md").read_text(
            encoding="utf-8")
        self.onepager = (ROOT / "docs" / "server_request_onepager.md").read_text(
            encoding="utf-8")

    def test_stale_download_estimate_is_gone(self):
        """'26 Gb / 9 GB' matched neither base_count nor fastq_bytes."""
        for doc, name in ((self.admin, "admin questions"),
                          (self.onepager, "one-pager")):
            with self.subTest(doc=name):
                self.assertNotIn("26 Gb", doc)
                self.assertNotIn("9 GB 压缩", doc)

    def test_documents_quote_the_verified_panel_sizes(self):
        """Each document quotes the panels relevant to it."""
        self.assertIn("23.19", self.admin)
        self.assertIn("170.70", self.admin)
        for token in ("23.19", "170.70", "164.02"):
            with self.subTest(doc="one-pager", token=token):
                self.assertIn(token, self.onepager)

    def test_documents_say_the_sizes_are_declared_not_measured(self):
        for doc, name in ((self.admin, "admin questions"),
                          (self.onepager, "one-pager")):
            with self.subTest(doc=name):
                self.assertTrue(
                    ("声明" in doc) or ("不是我们实测" in doc),
                    "%s must not present declared sizes as measurements" % name)

    def test_tool_count_matches_the_probe_loop(self):
        """The probe's TOOLS loop has 18 names; a doc said 21, another 18."""
        probe = (ROOT / "server" / "00_probe.sh").read_text(encoding="utf-8")
        m = re.search(r"for t in ([^;]+); do", probe)
        n_tools = len(m.group(1).split())
        self.assertEqual(n_tools, 18)
        self.assertIn("%d 个逐个检查" % n_tools, self.admin)

    def test_pipeline_script_count_matches_the_directory(self):
        n_sh = len(list((ROOT / "server").glob("*.sh")))
        self.assertEqual(n_sh, 12)
        self.assertNotIn("`server/` 10 个", self.admin)

    def test_admin_doc_does_not_promise_a_script_count_that_is_wrong(self):
        self.assertNotIn("全部 10 个流程脚本", self.admin)


if __name__ == "__main__":
    unittest.main()
