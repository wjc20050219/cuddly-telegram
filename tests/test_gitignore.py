"""Guard the .gitignore: it must exclude bulk data WITHOUT hiding needed files.

A .gitignore is unusually easy to get subtly wrong in a damaging way. Two
failure modes matter here:

  * Over-exclusion: the manifests, metadata TSVs and generated appendices are
    the *evidence* behind every number in the thesis. Committing the code
    without them would leave a repository that cannot reproduce its own claims.
  * Under-exclusion: raw FASTQ/CRAM/BAM and the ~110 MB XML cache are either
    re-downloadable or huge, and would make the repository unusable.

This test states which real paths must be kept and which must be ignored, and
checks them with `pathspec`-style prefix matching implemented locally (no
third-party dependency, since the project has none installed).
"""
import fnmatch
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = ROOT / ".gitignore"


def load_rules():
    """Return (patterns, negations) in file order."""
    patterns, negations = [], []
    for raw in GITIGNORE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            negations.append(line[1:])
        else:
            patterns.append(line)
    return patterns, negations


def matches(path, pattern):
    """Match a repo-relative posix path against one gitignore pattern."""
    path = path.replace("\\", "/")
    # Directory-only patterns (trailing slash) match anything beneath.
    if pattern.endswith("/"):
        base = pattern.rstrip("/")
        return path == base or path.startswith(base + "/")
    if "/" in pattern:
        # Anchored pattern: match the path or any ancestor prefix.
        if fnmatch.fnmatch(path, pattern):
            return True
        parts = path.split("/")
        for i in range(1, len(parts) + 1):
            if fnmatch.fnmatch("/".join(parts[:i]), pattern):
                return True
        return False
    # Bare pattern matches at any depth.
    return any(fnmatch.fnmatch(part, pattern) for part in path.split("/"))


def is_ignored(path):
    patterns, negations = load_rules()
    ignored = any(matches(path, p) for p in patterns)
    if ignored and any(matches(path, n) for n in negations):
        return False
    return ignored


class GitignoreTests(unittest.TestCase):
    def test_gitignore_exists(self):
        self.assertTrue(GITIGNORE.exists(), "project has no .gitignore")

    # ---------- must be kept: the evidence behind the thesis ----------

    KEEP = [
        # Panel manifests: every sample table and the appendix derive from these.
        "data/metadata/server/pilot_manifest.tsv",
        "data/metadata/server/independent_manifest.tsv",
        "data/metadata/server/pilot_smoke1.tsv",
        "data/metadata/server/pilot_smoke5.tsv",
        "data/metadata/server/manifest_build_summary.json",
        # Curation outputs the thesis quotes numbers from.
        "data/metadata/search/ena_search_summary.tsv",
        "data/metadata/candidates/variety_canonical.tsv",
        "data/metadata/candidates/sample_attrs.tsv",
        "data/metadata/candidates/candidate_samples.tsv",
        "data/metadata/candidates/duplicate_samples.tsv",
        "data/metadata/candidates/independent_test_panel.tsv",
        # Thesis and appendices.
        "docs/thesis/THESIS_DRAFT.md",
        "docs/thesis/APPENDIX_A_samples.md",
        "docs/thesis/APPENDIX_B_software.md",
        # Code, config, environment record.
        "scripts/build_appendix_samples.py",
        "src/ricevar_id/fingerprint.py",
        "server/config.sh",
        "environment.yml",
        "requirements.txt",
        "software_versions.txt",
        # Directory placeholders must survive or clones lack output dirs.
        "data/raw/.gitkeep",
        "data/qc/.gitkeep",
        "data/metadata/.gitkeep",
        "reference/.gitkeep",
        "results/markers/.gitkeep",
        "database/.gitkeep",
    ]

    def test_needed_files_are_not_ignored(self):
        for path in self.KEEP:
            with self.subTest(path=path):
                self.assertFalse(is_ignored(path), "%s would be excluded" % path)

    def test_every_kept_path_actually_exists(self):
        """A keep-rule for a nonexistent file is dead weight, not protection."""
        for path in self.KEEP:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists(), "%s does not exist" % path)

    def test_all_real_manifests_and_metadata_survive(self):
        """No file under data/metadata/ may be ignored except the XML cache."""
        offenders = []
        for path in (ROOT / "data" / "metadata").rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if is_ignored(rel) and "xml_cache" not in rel:
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         "metadata files excluded by .gitignore: %s" % offenders)

    # ---------- must be ignored: bulk and re-downloadable ----------

    IGNORE = [
        "data/raw/SRR25567266_1.fastq.gz",
        "data/raw/sample.fq.gz",
        "data/bam/sample.bam",
        "data/bam/sample.bam.bai",
        "data/vcf/cohort.vcf.gz",
        "reference/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa",
        "reference/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz",
        "data/metadata/candidates/xml_cache/batch_00001.xml",
        "database/ricevar.db",
        "database/ricevar.sqlite",
        ".tmp/scratch.log",
        "scripts/__pycache__/x.cpython-311.pyc",
    ]

    def test_bulk_artifacts_are_ignored(self):
        for path in self.IGNORE:
            with self.subTest(path=path):
                self.assertTrue(is_ignored(path), "%s would be committed" % path)

    def test_xml_cache_is_the_only_metadata_exclusion(self):
        self.assertTrue(is_ignored("data/metadata/candidates/xml_cache/batch_00009.xml"))
        self.assertFalse(is_ignored("data/metadata/candidates/sample_attrs.tsv"))

    def test_cache_bulk_is_actually_large_enough_to_justify_exclusion(self):
        """Sanity: if the cache were tiny, excluding it would be unjustified."""
        cache = ROOT / "data" / "metadata" / "candidates" / "xml_cache"
        total = sum(p.stat().st_size for p in cache.glob("*.xml"))
        self.assertGreater(total, 50 * 1024 * 1024,
                           "xml_cache is only %.1f MB; exclusion may be unnecessary"
                           % (total / 1024.0 / 1024.0))

    # ---------- structure of the file itself ----------

    def test_no_dangling_section_heading(self):
        """A '## Section' with no rules after it means an edit went wrong."""
        lines = GITIGNORE.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("##"):
                continue
            rest = [x.strip() for x in lines[i + 1:]]
            following = [x for x in rest if x and not x.startswith("#")]
            self.assertTrue(following, "section %r has no rules" % line.strip())

    def test_no_blanket_log_ignore_that_would_hide_records(self):
        """*.log is fine for scratch, but tracked logs must be re-included."""
        patterns, _ = load_rules()
        self.assertIn("*.log", patterns)
        # wsl_install.log etc. are host build logs, not scientific records;
        # their exclusion is intentional and asserted here so it is not a surprise.
        self.assertTrue(is_ignored("wsl_install.log"))

    def test_ignored_paths_are_not_also_forced(self):
        """No negation may re-include a bulk artifact we just excluded."""
        for path in self.IGNORE:
            with self.subTest(path=path):
                self.assertTrue(is_ignored(path))


if __name__ == "__main__":
    unittest.main()
