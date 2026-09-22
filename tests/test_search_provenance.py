"""Search artifacts must not be mistaken for complete listings.

The ENA search directory mixes two very different kinds of file:

* ``ena_search_summary.tsv`` -- counts computed by the server (``limit=0``),
  therefore exact;
* ``ena_rice_wgs_runs.tsv`` / ``ena_rice_wgs_deep_runs.tsv`` -- downloaded
  listings fetched with an explicit page cap.

Those listings have exactly 5,000 and 10,000 data rows, matching the
``limit=`` values in ``search_ena.sh`` and ``search_round2.sh``. A row count
that lands exactly on a page cap is evidence of truncation, not of a natural
total. This was not previously recorded anywhere machine-readable: the derived
numbers (24,633 / 32,478 / 10,707) lived only in a comment and a README.

These tests pin that distinction, and pin the *scope* of the damage: the frozen
panels must not depend on a truncated listing.
"""
import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data" / "metadata" / "search"
PROVENANCE = SEARCH / "search_provenance.json"
SERVER = ROOT / "data" / "metadata" / "server"


def load_provenance():
    with PROVENANCE.open(encoding="utf-8") as handle:
        return json.load(handle)


def artifact(name):
    for item in load_provenance()["artifacts"]:
        if item["name"] == name:
            return item
    raise AssertionError("artifact not recorded: %s" % name)


class ProvenanceRecordTests(unittest.TestCase):
    def test_provenance_file_exists(self):
        self.assertTrue(PROVENANCE.exists(),
                        "run scripts/record_search_provenance.py")

    def test_every_recorded_artifact_exists_on_disk(self):
        for item in load_provenance()["artifacts"]:
            with self.subTest(name=item["name"]):
                self.assertTrue((SEARCH / item["name"]).exists())

    def test_row_counts_match_reality(self):
        for item in load_provenance()["artifacts"]:
            if item["kind"] != "listing":
                continue
            with self.subTest(name=item["name"]):
                with (SEARCH / item["name"]).open(encoding="utf-8") as handle:
                    actual = max(0, sum(1 for _ in handle) - 1)
                self.assertEqual(item["data_rows"], actual)

    def test_listings_are_flagged_as_suspected_truncated(self):
        """Both listings sit exactly on a known page cap."""
        for name in ("ena_rice_wgs_runs.tsv", "ena_rice_wgs_deep_runs.tsv"):
            with self.subTest(name=name):
                item = artifact(name)
                self.assertEqual(item["status"], "suspected_truncated")
                self.assertIsNotNone(item["page_cap"])
                self.assertIn("limit=", item["cap_reason"])

    def test_the_caps_are_the_ones_the_scripts_actually_use(self):
        """The claimed cap must be findable in the fetch script."""
        expectations = {
            "scripts/search_ena.sh": "limit=5000",
            "scripts/search_round2.sh": "limit=10000",
        }
        for rel, needle in expectations.items():
            with self.subTest(script=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(needle, text,
                              "%s 中找不到 %s，来源记录可能已过期" % (rel, needle))

    def test_count_file_is_not_marked_truncated(self):
        """The limit=0 counts are exact and must stay in the other category."""
        item = artifact("ena_search_summary.tsv")
        self.assertEqual(item["kind"], "counts")
        self.assertEqual(item["status"], "exact_count")
        self.assertNotIn("page_cap", [k for k, v in item.items() if v])

    def test_verifier_passes_against_current_state(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "record_search_provenance.py"),
             "--check"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class DependentClaimTests(unittest.TestCase):
    """The un-archived numbers must be traceable, and their use reviewed."""

    def test_derived_counts_are_listed_as_dependent_claims(self):
        patterns = {c["pattern"] for c in load_provenance()["dependent_claims"]}
        for expected in ("24,633", "32,478", "10,707"):
            with self.subTest(pattern=expected):
                self.assertIn(expected, patterns)

    def test_every_dependent_claim_file_exists(self):
        for claim in load_provenance()["dependent_claims"]:
            with self.subTest(file=claim["file"]):
                self.assertTrue((ROOT / claim["file"]).exists())

    def test_recorded_claim_presence_matches_the_files(self):
        """If a claim is removed, the record must be regenerated."""
        for claim in load_provenance()["dependent_claims"]:
            with self.subTest(file=claim["file"], pattern=claim["pattern"]):
                text = (ROOT / claim["file"]).read_text(encoding="utf-8")
                self.assertEqual(claim["still_present"],
                                 bool(re.search(claim["pattern"], text)))

    def test_admin_questions_does_not_assert_the_unarchived_count_as_fact(self):
        """docs/server_admin_questions.md cited 24,633 with no archived source.

        The number was printed to a console once and never persisted, so it
        cannot be re-derived from the repository. Naming it as unreliable is
        fine and useful; stating it as a fact is not. So the check is not
        "the digits are absent" but "the digits are never presented as a
        finding" -- every occurrence must sit in a caveat.
        """
        text = (ROOT / "docs" / "server_admin_questions.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            if "24,633" in line:
                with self.subTest(line=line.strip()[:60]):
                    self.assertTrue(
                        ("无法" in line or "未存档" in line or "复核" in line),
                        "24,633 被当作事实陈述，而非标注为不可复核：%s" % line.strip())

    def test_admin_questions_still_gives_a_verifiable_number(self):
        """Removing the unreliable figure must not leave no figure at all."""
        text = (ROOT / "docs" / "server_admin_questions.md").read_text(encoding="utf-8")
        self.assertIn("96,623", text)
        self.assertIn("ena_search_summary.tsv", text)


class PanelIndependenceTests(unittest.TestCase):
    """Scope check: the frozen panels must not rest on a truncated listing."""

    def _deep_accessions(self):
        accessions = set()
        with (SEARCH / "ena_rice_wgs_deep_runs.tsv").open(encoding="utf-8") as handle:
            reader = csv.reader(handle, delimiter="\t")
            next(reader)
            for row in reader:
                if row:
                    accessions.add(row[0])
        return accessions

    def test_deep_listing_is_exactly_the_page_cap(self):
        self.assertEqual(len(self._deep_accessions()), 10000)

    def test_panels_have_runs_outside_the_truncated_listing(self):
        """If every panel run came from the listing, truncation would be fatal."""
        deep = self._deep_accessions()
        for name, size in (("pilot_manifest.tsv", 30),
                           ("independent_manifest.tsv", 25)):
            with self.subTest(panel=name):
                with (SERVER / name).open(encoding="utf-8") as handle:
                    runs = [r["run_accession"] for r in csv.DictReader(handle, delimiter="\t")]
                self.assertEqual(len(runs), size)
                outside = [r for r in runs if r not in deep]
                self.assertTrue(outside,
                                "%s 的样本全部来自被截断的清单" % name)

    def test_panels_are_sourced_from_candidate_samples_not_the_listing(self):
        """The panels derive from the >=5x candidate table, which is a different
        and larger artifact; confirm that rather than assuming it."""
        candidates = ROOT / "data" / "metadata" / "candidates" / "candidate_samples.tsv"
        self.assertTrue(candidates.exists())
        with candidates.open(encoding="utf-8") as handle:
            cand_runs = {row[0] for row in csv.reader(handle, delimiter="\t") if row}
        self.assertGreater(len(cand_runs), 10000,
                           "候选表应当远大于被截断的清单")

        for name in ("pilot_manifest.tsv", "independent_manifest.tsv"):
            with self.subTest(panel=name):
                with (SERVER / name).open(encoding="utf-8") as handle:
                    runs = [r["run_accession"] for r in csv.DictReader(handle, delimiter="\t")]
                missing = [r for r in runs if r not in cand_runs]
                self.assertEqual(missing, [],
                                 "面板样本必须来自候选表：%s" % missing)


if __name__ == "__main__":
    unittest.main()
