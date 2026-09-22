"""Appendix E describes the repository; those claims must be true.

Appendix E tells a reader how to obtain and run this project. A wrong path or a
missing script there is worse than an omission: the reader concludes the project
is broken. Every structural claim is checked against the real tree.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "docs" / "thesis" / "APPENDIX_E_availability.md"


class AppendixEAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.text = APPENDIX.read_text(encoding="utf-8")

    def test_appendix_exists(self):
        self.assertTrue(APPENDIX.exists())

    def test_every_referenced_repo_path_exists(self):
        """Every backticked repo-relative path must resolve on disk."""
        # Paths inside the ASCII tree are read from the tree block separately.
        candidates = set(re.findall(r"`([A-Za-z0-9_./-]+)`", self.text))
        missing = []
        for raw in candidates:
            if raw.startswith(("http", "GCF_", "GCA_")) or "." not in raw:
                continue
            if not re.match(r"^[A-Za-z0-9_]+/", raw) and "/" not in raw:
                continue
            # Skip inline commands and pure filenames used as prose.
            if raw.startswith("server/") or raw.startswith("data/") \
                    or raw.startswith("docs/") or raw.startswith("scripts/") \
                    or raw.startswith("src/") or raw.startswith("app/") \
                    or raw.startswith("tests/"):
                if not (ROOT / raw).exists():
                    missing.append(raw)
        self.assertEqual(missing, [], "paths named in appendix E do not exist: %s" % missing)

    def test_stage_scripts_listed_in_the_tree_all_exist(self):
        """The ASCII tree names each pipeline stage; none may be invented."""
        # Only inspect the fenced tree block.
        match = re.search(r"```\n(RiceVar-ID/[\s\S]*?)```", self.text)
        self.assertIsNotNone(match, "appendix E has no repository tree block")
        tree = match.group(1)
        listed = re.findall(r"([0-9]{2}_[a-z_]+\.sh)", tree)
        self.assertTrue(listed, "tree lists no stage scripts")
        for name in listed:
            with self.subTest(script=name):
                self.assertTrue((ROOT / "server" / name).exists(),
                                "server/%s does not exist" % name)

    def test_tree_does_not_omit_an_existing_stage_script(self):
        """A stage script missing from the tree is a documentation gap."""
        match = re.search(r"```\n(RiceVar-ID/[\s\S]*?)```", self.text)
        tree = match.group(1)
        listed = set(re.findall(r"([0-9]{2}_[a-z_]+\.sh)", tree))
        actual = {p.name for p in (ROOT / "server").glob("[0-9][0-9]_*.sh")}
        self.assertEqual(sorted(actual - listed), [],
                         "stage scripts exist but are absent from the tree")

    def test_declared_run_commands_match_real_files(self):
        for name in ("00_probe.sh", "01_setup_env.sh", "run_all.sh"):
            with self.subTest(script=name):
                self.assertIn(name, self.text)
                self.assertTrue((ROOT / "server" / name).exists())

    def test_config_sh_is_called_out_as_the_parameter_home(self):
        self.assertIn("config.sh", self.text)
        self.assertTrue((ROOT / "server" / "config.sh").exists())

    # ---------- the honesty assertions ----------

    def test_version_control_state_is_described_truthfully(self):
        """附录 E 对版本控制的描述必须与磁盘现状一致。

        本轮之前这里断言"没有 .git"——那是当时的事实。现在仓库已建立，
        于是这条断言本身成了过期陈述。测试改为**双向一致**：
        磁盘上有 `.git` 就必须说有，没有就必须说没有。
        """
        has_git = (ROOT / ".git").exists()
        text = self.text
        if has_git:
            self.assertNotIn("尚未纳入版本控制", text,
                             "仓库已建立，附录 E 不应再说没有版本控制")
            self.assertTrue(
                "版本控制" in text and ("已" in text or "dulwich" in text),
                "附录 E 应说明版本控制已建立及其方式")
        else:
            self.assertIn("尚未纳入版本控制", text)

    def test_states_experiments_have_not_run(self):
        self.assertIn("实验**尚未执行**", self.text.replace("实验**尚未执行**", "实验**尚未执行**"))
        self.assertIn("尚不存在", self.text)

    def test_no_result_metrics_are_claimed(self):
        self.assertEqual(
            re.findall(r"(准确率|recall|召回率|AUC|ROC|实测深度)\s*[:：]?\s*\d", self.text),
            [])

    def test_declared_size_matches_the_manifests(self):
        """334.71 GiB must be the real sum, re-derived here from the manifests."""
        import csv

        total = 0
        for name in ("pilot_manifest.tsv", "independent_manifest.tsv"):
            with (ROOT / "data" / "metadata" / "server" / name).open(
                    encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    for part in row["fastq_bytes"].split(";"):
                        if part.strip():
                            total += int(part)
        gib = total / 1024.0 ** 3
        self.assertAlmostEqual(gib, 334.71, places=1,
                               msg="manifest total is %.2f GiB, appendix says 334.71" % gib)
        self.assertIn("334.71", self.text)

    def test_the_size_is_labelled_as_declared_not_measured(self):
        self.assertIn("声明", self.text)
        self.assertIn("从未下载", self.text)

    def test_gitignore_is_described_and_present(self):
        self.assertIn(".gitignore", self.text)
        self.assertTrue((ROOT / ".gitignore").exists())
        self.assertIn("test_gitignore.py", self.text)
        self.assertTrue((ROOT / "tests" / "test_gitignore.py").exists())

    def test_todo_placeholders_remain_for_undecided_items(self):
        """Licence and DOI are genuinely undecided; they must not be invented."""
        self.assertIn("{{TODO:", self.text)
        for word in ("许可证", "DOI"):
            self.assertIn(word, self.text)

    def test_environment_and_requirements_are_named(self):
        for name in ("environment.yml", "requirements.txt"):
            with self.subTest(f=name):
                self.assertIn(name, self.text)
                self.assertTrue((ROOT / name).exists())


if __name__ == "__main__":
    unittest.main()
