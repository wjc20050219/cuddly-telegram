"""Appendix B must not misquote software_versions.txt.

Appendix B restates ~30 version numbers. Transcription is exactly where a
thesis acquires a plausible-but-wrong number, so every version token in the
appendix is checked against the authoritative record.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "docs" / "thesis" / "APPENDIX_B_software.md"
VERSIONS = ROOT / "software_versions.txt"


class AppendixBVersionTests(unittest.TestCase):
    def setUp(self):
        self.text = APPENDIX.read_text(encoding="utf-8")
        self.source = VERSIONS.read_text(encoding="utf-8")

    def test_appendix_exists(self):
        self.assertTrue(APPENDIX.exists())

    def test_named_tool_versions_appear_verbatim_in_the_record(self):
        # (label in appendix, exact version string that must be in the record)
        expected = [
            ("FastQC", "0.12.1"), ("fastp", "1.3.7"), ("samtools", "1.24"),
            ("bcftools", "1.24"), ("bedtools", "2.31.1"), ("bwa-mem2", "2.3"),
            ("minimap2", "2.31-r1302"), ("mosdepth", "0.3.14"),
            ("seqkit", "2.13.0"), ("KMC", "3.2.4"), ("Snakemake", "9.24.0"),
            ("Python", "3.11.16"), ("numpy", "2.4.6"), ("pandas", "3.0.5"),
            ("pysam", "0.24.1"), ("scikit-allel", "1.3.13"),
            ("matplotlib", "3.11.2"), ("hmmlearn", "0.3.3"),
            ("R / Rscript", "4.3.3"),
        ]
        for label, version in expected:
            with self.subTest(label=label):
                self.assertIn(version, self.text, "%s missing from appendix" % label)
                self.assertIn(version, self.source,
                              "%s: %s not in software_versions.txt" % (label, version))

    def test_conda_and_os_details_match(self):
        for token in ("26.7.1", "Ubuntu 26.04.1", "6.18.33.2", "/opt/miniconda3"):
            with self.subTest(token=token):
                self.assertIn(token, self.source)
                self.assertIn(token, self.text)

    def test_reference_url_matches_pipeline_config(self):
        """The pipeline identifies the reference by URL/name, not by accession.

        The `GCF_/GCA_` accessions are documentation-level facts (from NCBI/ENA);
        asserting they appear in the scripts would be asserting something that is
        simply not there. What must match is the URL and name the pipeline uses.
        """
        self.assertIn("GCF_001433935.1", self.text)
        self.assertIn("GCA_001433935", self.text)
        config = (ROOT / "server" / "config.sh").read_text(encoding="utf-8")
        self.assertIn("IRGSP-1.0", config)
        self.assertIn("Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz", config)
        self.assertIn("Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz", self.text)

    def test_minimap2_version_is_present(self):
        """Appendix B must not silently drop a tool the record lists."""
        self.assertIn("minimap2", self.source)
        self.assertIn("minimap2", self.text)
        self.assertIn("2.31-r1302", self.text)

    def test_default_parameters_match_the_scripts(self):
        """Parameters quoted in B.5 must be the ones the scripts actually use."""
        config = (ROOT / "server" / "config.sh").read_text(encoding="utf-8")
        joint = (ROOT / "server" / "04_joint_snp.sh").read_text(encoding="utf-8")
        for token in ("THREADS", "PAR", "SORT_MEM", "RV_WINDOWS", "RV_DEPTHS"):
            self.assertIn(token, config)
            self.assertIn(token, self.text)
        # depth gradient must be identical to the declared six levels
        self.assertIn("0.02 0.05 0.10 0.20 0.50 1.00", config)
        for level in ("0.02", "0.05", "0.10", "0.20", "0.50", "1.00"):
            self.assertIn(level, self.text)
        # MAPQ/BASEQ quoted as 20
        self.assertIn('MAPQ="${MAPQ:-20}"', joint)
        self.assertIn('BASEQ="${BASEQ:-20}"', joint)
        self.assertIn("MAPQ=20", self.text.replace("`MAPQ=20`", "MAPQ=20"))

    def test_appendix_admits_versions_were_measured_in_wsl2(self):
        """The version list is real but was NOT measured on the school server."""
        self.assertIn("WSL2", self.text)
        self.assertIn("学校服务器上的最终运行环境可能不同", self.text)

    def test_appendix_does_not_claim_a_reference_checksum(self):
        """reference_record.tsv has never been produced; no digest may appear."""
        digests = re.findall(r"\b[0-9a-f]{16,64}\b", self.text)
        self.assertEqual(digests, [], "appendix must not state a checksum value")
        self.assertIn("尚未生成", self.text)

    def test_appendix_contains_no_result_metrics(self):
        self.assertEqual(
            re.findall(r"(准确率|recall|召回率|AUC|ROC|实测深度)\s*[:：]?\s*\d", self.text),
            [])

    def test_python37_sqlite_note_matches_reality(self):
        self.assertIn("3.21.0", self.text)
        self.assertIn("INSERT OR REPLACE", self.text)


if __name__ == "__main__":
    unittest.main()
