"""Prove verify_documented_commands.py actually detects stale documentation.

A verifier that reports zero findings is only trustworthy if it can be shown to
report non-zero on real defects. Each test injects a defect into a temporary
copy of the docs and asserts the checker catches it.
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_documented_commands as vdc  # noqa: E402


def load_module_at(root):
    """Load a fresh copy of the verifier whose ROOT points at ``root``."""
    spec = importlib.util.spec_from_file_location(
        "vdc_copy_%d" % id(root), str(ROOT / "scripts" / "verify_documented_commands.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = Path(root)
    module.DOCS = [Path(root) / "doc.md"]
    return module


class DocumentedCommandDetectionTests(unittest.TestCase):
    """每个用例注入一个真实缺陷，断言之必须被发现。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=str(ROOT / ".tmp")))
        # A minimal project: one script with one real flag.
        (self.tmp / "scripts").mkdir()
        (self.tmp / "scripts" / "tool.py").write_text(
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--real-flag')\n"
            "p.parse_args()\n", encoding="utf-8")
        self.module = load_module_at(self.tmp)

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def write_doc(self, text):
        (self.tmp / "doc.md").write_text(text, encoding="utf-8")

    def test_a_correct_command_is_accepted(self):
        """先证明夹具本身是"能通过的"，否则后面的失败可能来自夹具而非检查。"""
        self.write_doc("run `python scripts/tool.py --real-flag` now\n")
        checked, findings, _ = self.module.check_invocations()
        self.assertEqual(checked, 1)
        self.assertEqual(findings, [])

    def test_a_renamed_flag_is_caught(self):
        self.write_doc("run `python scripts/tool.py --old-flag` now\n")
        _, findings, _ = self.module.check_invocations()
        self.assertEqual(len(findings), 1)
        self.assertIn("--old-flag", findings[0][3])

    def test_a_missing_script_is_caught(self):
        self.write_doc("run `python scripts/deleted.py --x` now\n")
        _, findings, _ = self.module.check_invocations()
        self.assertEqual(len(findings), 1)
        self.assertIn("不存在", findings[0][3])

    def test_a_correct_path_is_accepted(self):
        self.write_doc("see `scripts/tool.py` for details\n")
        findings, _ = self.module.check_paths()
        self.assertEqual(findings, [])

    def test_a_missing_path_is_caught(self):
        self.write_doc("see `scripts/vanished.py` for details\n")
        findings, _ = self.module.check_paths()
        self.assertEqual(len(findings), 1)
        self.assertIn("vanished.py", findings[0][2])

    def test_a_missing_document_is_caught(self):
        """docs/ 引用也曾被完全漏检，这里锁住覆盖范围。"""
        self.write_doc("see `docs/methods/design_OLD.md` for details\n")
        findings, _ = self.module.check_paths()
        self.assertEqual(len(findings), 1)
        self.assertIn("design_OLD.md", findings[0][2])

    def test_a_missing_output_is_not_flagged(self):
        """流水线产物尚未生成不是文档缺陷，否则会天天假报警。"""
        self.write_doc("writes `data/processed/similarity/pairwise.tsv`\n")
        findings, generated = self.module.check_paths()
        self.assertEqual(findings, [])
        self.assertEqual(generated, ["data/processed/similarity/pairwise.tsv"])

    def test_a_suffix_of_a_real_path_is_not_flagged(self):
        """回归：检查器曾把 data/metadata/server/x.tsv 的后缀误判为缺失。

        这是检查器自己的缺陷（假阳性），不是文档缺陷。
        """
        (self.tmp / "data" / "metadata" / "server").mkdir(parents=True)
        (self.tmp / "data" / "metadata" / "server" / "pilot.tsv").write_text(
            "a\n", encoding="utf-8")
        self.write_doc("see `data/metadata/server/pilot.tsv` for details\n")
        findings, _ = self.module.check_paths()
        self.assertEqual(findings, [])

    def test_strict_exit_code_reflects_findings(self):
        self.write_doc("run `python scripts/tool.py --old-flag` now\n")
        self.assertEqual(self.module.main(["--strict"]), 1)
        self.write_doc("run `python scripts/tool.py --real-flag` now\n")
        self.assertEqual(self.module.main(["--strict"]), 0)

    def test_non_strict_always_exits_zero(self):
        """非 strict 模式只报告不失败，便于人工阅读。"""
        self.write_doc("run `python scripts/tool.py --old-flag` now\n")
        self.assertEqual(self.module.main([]), 0)


if __name__ == "__main__":
    unittest.main()
