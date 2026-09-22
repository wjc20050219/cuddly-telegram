"""Appendix D is a record of what was verified -- it must not overstate it.

The whole point of appendix D is honesty about which claims are checked and
which are not. So this test checks the *record itself*: every report it cites
must exist, the defect counts must match reality, and the "never executed"
section must still be true (if it silently became false, the appendix would be
understating the work; if it silently became unverifiable, worse).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "docs" / "thesis" / "APPENDIX_D_verification.md"
REPORTS = ROOT / "docs" / "task_reports"


class AppendixDRecordTests(unittest.TestCase):
    def setUp(self):
        self.text = APPENDIX.read_text(encoding="utf-8")

    def test_appendix_exists(self):
        self.assertTrue(APPENDIX.exists())

    def test_every_cited_report_exists(self):
        cited = set(re.findall(r"`(ROUND\d+_[a-z_]+\.md|TASK-\d+_report\.md)`", self.text))
        self.assertTrue(cited, "appendix D cites no reports")
        missing = sorted(name for name in cited if not (REPORTS / name).exists())
        self.assertEqual(missing, [], "cited reports do not exist: %s" % missing)

    def test_every_round_report_is_listed(self):
        """A verification appendix that omits a round is not a full record."""
        on_disk = {p.name for p in REPORTS.glob("ROUND*.md")}
        listed = set(re.findall(r"`(ROUND\d+_[a-z_]+\.md)`", self.text))
        self.assertEqual(sorted(on_disk - listed), [],
                         "round reports exist but are not recorded")

    def test_test_file_count_is_accurate(self):
        """Count only files that existed when the appendix was written.

        This test file is one of them, so the appendix's number must equal the
        real total -- if a new test file is added the appendix is stale.
        """
        actual = len(list((ROOT / "tests").glob("test_*.py")))
        claimed = int(re.search(r"tests/`（(\d+) 个测试文件", self.text).group(1))
        self.assertEqual(claimed, actual,
                         "appendix says %d test files, found %d" % (claimed, actual))

    def test_verifier_script_count_is_accurate(self):
        actual = len(list((ROOT / "scripts").glob("verify_*.py")))
        claimed = int(re.search(r"scripts/verify_\*\.py`（(\d+) 个）", self.text).group(1))
        self.assertEqual(claimed, actual,
                         "appendix says %d verifiers, found %d" % (claimed, actual))

    def test_stated_test_total_matches_what_the_runner_collects(self):
        """D.8 引用的"共 N 项"必须等于运行器实际收集到的用例数。

        `unittest` 的 `Ran N` **包含**被跳过的用例，所以总数可以用
        收集器的计数直接核对，不必真的跑一遍整套测试。
        这个数字以前只写在文档里、无人核对——正是"会漂移的散文数字"。
        """
        loader = unittest.TestLoader()
        actual = loader.discover(str(ROOT / "tests")).countTestCases()
        match = re.search(r"共 \*\*(\d+) 项\*\*", self.text)
        self.assertIsNotNone(match, "D.8 未给出测试总数")
        claimed = int(match.group(1))
        self.assertEqual(
            claimed, actual,
            "D.8 说共 %d 项，运行器实际收集 %d 项" % (claimed, actual))

    def test_stated_pass_and_skip_counts_are_internally_consistent(self):
        """通过数 + 跳过数 必须等于总数，否则是把跳过重复计数了。

        早先的写法是"467 项通过，9 项跳过"——但 `Ran 467` 已经包含
        那 9 项，两者相加等于把跳过算了两遍。
        """
        total = int(re.search(r"共 \*\*(\d+) 项\*\*", self.text).group(1))
        passed = int(re.search(r"其中 (\d+) 项通过", self.text).group(1))
        skipped = int(re.search(r"(\d+) 项因缺少 matplotlib 跳过", self.text).group(1))
        self.assertEqual(
            total, passed + skipped,
            "%d 项通过 + %d 项跳过 = %d，与总数 %d 不一致"
            % (passed, skipped, passed + skipped, total))

    def _defect_numbers(self):
        """Defect numbers from D.3 and D.4, each scoped to its own table."""
        numbers = []
        for start, end in (("## D.3", "## D.4"), ("## D.4", "## D.5")):
            section = self.text.split(start)[1].split(end)[0]
            numbers.extend(re.findall(r"^\| (\d+b?) \|", section, re.M))
        return numbers

    def test_code_defect_count_matches_the_table(self):
        """The stated total must equal the rows actually listed."""
        section = self.text.split("## D.3")[1].split("## D.4")[0]
        rows = re.findall(r"^\| (\d+) \|", section, re.M)
        self.assertEqual(len(rows), 9, "D.3 should list 9 code defects")

    def test_doc_defect_count_matches_the_table(self):
        """D.4 numbers 10..26, i.e. 17 defects, plus the extra 16b = 18 rows."""
        section = self.text.split("## D.4")[1].split("## D.5")[0]
        rows = re.findall(r"^\| (\d+b?) \|", section, re.M)
        plain = [n for n in rows if not n.endswith("b")]
        self.assertEqual(plain, [str(i) for i in range(10, 27)],
                         "D.4 should number 10..26")
        self.assertEqual(rows.count("16b"), 1, "D.4 should carry exactly one 16b")
        self.assertEqual(len(rows), 18, "D.4 should have 18 rows (17 + 16b)")

    def test_total_defect_count_is_consistent(self):
        """9 code (D.3) + 18 doc/tool rows (D.4, incl. 16b) = 27 rows.

        The appendix states 25 distinct defects: 25 numbered defects (1..25)
        plus 16b, which sits beside 16 rather than renumbering it. My first
        expectation reused the row count for both figures and was wrong.
        """
        numbers = self._defect_numbers()
        self.assertEqual(len(numbers), 27, "D.3+D.4 rows")
        self.assertEqual(len(set(numbers)), 27, "no duplicate numbers")
        plain = [n for n in numbers if not n.endswith("b")]
        self.assertEqual(len(plain), 26, "26 numbered defects")
        self.assertIn("26 项已修复缺陷", self.text)

    def test_no_two_defect_rows_describe_the_same_thing(self):
        """第 21 项曾与第 10 项是同一个缺陷（"26 Gb / 9 GB"）。

        重复计数会**夸大**复核的充分程度，与漏记一样有害。
        这里用"描述的关键词指纹"做粗查：两条不同编号的行不应
        共享一整套罕见特征串。
        """
        section = self.text.split("## D.4")[1].split("## D.5")[0]
        rows = re.findall(r"^\| (\d+b?) \| ([^|]+) \|", section, re.M)
        fingerprints = {}
        for number, desc in rows:
            key = tuple(sorted(set(re.findall(r"[0-9]+(?:\.[0-9]+)?\s*(?:Gb|GB|GiB)", desc))))
            if key:
                fingerprints.setdefault(key, []).append(number)
        duplicated = {k: v for k, v in fingerprints.items() if len(v) > 1}
        self.assertEqual(
            {}, duplicated,
            "以下缺陷行共享同一组数量特征，疑似重复计数：%s" % duplicated)

    def test_thesis_draft_agrees_on_the_defect_count(self):
        """A second copy of the number lives in the thesis; it must not drift."""
        draft = (ROOT / "docs" / "thesis" / "THESIS_DRAFT.md").read_text(encoding="utf-8")
        self.assertIn("26 项已修复缺陷", draft)

    def test_every_document_quoting_a_defect_count_agrees(self):
        """附录 D、论文、任务清单、STATUS 各自写着这个数字。

        `docs/STATUS.md` 曾停留在 **18 项**——比附录 D 落后六项，
        而没有任何检查会发现它。每份副本都是独立的漂移点，
        所以这里要求它们**逐份**与附录 D 的权威数字一致。
        """
        authoritative = int(re.search(r"合计记录 \*\*(\d+) 项已修复缺陷\*\*",
                                      self.text).group(1))
        copies = {
            "docs/thesis/THESIS_DRAFT.md": self._read("docs/thesis/THESIS_DRAFT.md"),
            "UNDERGRADUATE_TASK_LIST.md": self._read("UNDERGRADUATE_TASK_LIST.md"),
            "docs/STATUS.md": self._read("docs/STATUS.md"),
        }
        for name, text in copies.items():
            found = re.findall(r"\*\*(\d+) 项已修复缺陷\*\*", text)
            self.assertTrue(found, "%s 未提到缺陷总数" % name)
            for value in found:
                self.assertEqual(
                    authoritative, int(value),
                    "%s 说 %s 项，附录 D 说 %d 项" % (name, value, authoritative))

    def test_defect_numbering_is_contiguous_and_unique(self):
        """Numbering runs 1..26 continuously across D.3 and D.4, plus one 16b.

        The two tables share one continuous sequence (D.3 holds 1-9, D.4 holds
        10-26); 16b is an extra defect inserted next to 16.
        """
        numbers = self._defect_numbers()
        self.assertEqual(len(numbers), len(set(numbers)), "duplicate defect numbers")
        plain = [int(n) for n in numbers if not n.endswith("b")]
        self.assertEqual(plain, list(range(1, 27)),
                         "defect numbers must run 1..26 without gaps")
        self.assertEqual(numbers.count("16b"), 1)

    def test_task_list_status_defect_is_recorded(self):
        """D.17 records the self-contradicting task list, and D.4 references it."""
        self.assertIn("## D.17", self.text)
        self.assertIn("没有任何 ✅", self.text)
        self.assertIn("整理类", self.text)
    def test_truncated_listing_defect_is_recorded(self):
        """D.9 records the un-archived search counts, and D.4 references it."""
        self.assertIn("## D.9", self.text)
        self.assertIn("search_provenance.json", self.text)
        self.assertIn("10,000", self.text)
        self.assertIn("截断", self.text)

    def test_verifier_encoding_defect_is_recorded(self):
        """D.10 records the crash on real abstract data, and D.4 references it."""
        self.assertIn("## D.10", self.text)
        self.assertIn("UnicodeEncodeError", self.text)
        self.assertIn("U+00A0", self.text)
        self.assertIn("redirect_stdout", self.text)

    def test_appendix_states_the_truncation_does_not_touch_the_panels(self):
        """Scope must be stated, or readers will over- or under-worry."""
        self.assertIn("不影响已冻结的两个面板", self.text)

    def test_appendix_is_free_of_mojibake(self):
        """This file was once corrupted by a PowerShell round-trip.

        It is rewritten wholesale if that happens again, but a check is cheap
        and the failure mode (silent mojibake in a thesis appendix) is bad.
        """
        self.assertNotIn("\ufffd", self.text)
        # CJK mojibake shows up as rare-block characters; the real text uses
        # ordinary CJK. Assert a few known-correct strings survive.
        for phrase in ("复核记录", "占位符守卫", "变异测试"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    # ---------- the honesty constraints ----------

    NEVER_RUN = [
        "bash -n",
        "从未产出任何 PNG",
        "从未启动过",
        "从未运行",
    ]

    def test_still_states_what_was_never_verified(self):
        for phrase in self.NEVER_RUN:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_still_states_no_real_data_was_used(self):
        self.assertIn("没有实验数据", self.text)
        self.assertIn("不构成对流程在真实数据上正确性的任何保证", self.text)

    def test_no_result_metrics_are_claimed(self):
        self.assertEqual(
            re.findall(r"(准确率|recall|召回率|AUC|ROC|实测深度)\s*[:：]?\s*\d", self.text),
            [])

    # ---------- claims about specific fixed defects must be real ----------

    def _read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_like_escaping_defect_is_actually_fixed(self):
        """D.3 #2: find_variety must escape LIKE wildcards."""
        src = self._read("src/ricevar_id/dbquery.py")
        self.assertIn("_escape_like", src)
        self.assertIn("ESCAPE", src)

    def test_method_parameter_is_actually_honoured(self):
        """D.3 #1: compare_varieties must dispatch on `method`, not hardcode.

        It lives in dbquery.py, not fingerprint.py -- my first version of this
        test looked in the wrong module and failed for that reason alone.
        """
        src = self._read("src/ricevar_id/dbquery.py")
        self.assertIn("def compare_varieties", src)
        body = src.split("def compare_varieties(self")[1][:1500]
        self.assertIn("method", body)
        # It must delegate to the shared fingerprint implementation.
        self.assertIn("fingerprint", body)

    def test_unlabelled_reference_visibility_exists(self):
        """D.3 #3: the fix added visibility flags rather than filtering.

        Also in dbquery.py (the identification result dict), not fingerprint.py.
        """
        src = self._read("src/ricevar_id/dbquery.py")
        self.assertIn("best_match_lacks_variety", src)
        self.assertIn("n_unlabelled_reference_samples", src)

    def test_missing_values_are_not_imputed_in_the_matrix(self):
        """D.3 #7 spirit: MISSING must remain -1, never silently filled."""
        src = self._read("src/ricevar_id/fingerprint.py")
        self.assertIn("MISSING = -1", src)

    def test_readme_no_longer_references_a_missing_log(self):
        """D.4 #9: README must not point at a nonexistent download log."""
        readme = self._read("README.md")
        self.assertNotIn("data/metadata/download_log.tsv", readme)

    def test_thesis_no_longer_points_at_a_missing_directory(self):
        """D.4 #16 / the broken reference this appendix was created to fix."""
        self.assertFalse((ROOT / "docs" / "verification").exists())
        thesis = self._read("docs/thesis/THESIS_DRAFT.md")
        self.assertNotIn("`docs/verification/`", thesis)
        self.assertIn("APPENDIX_D_verification.md", thesis)


if __name__ == "__main__":
    unittest.main()
