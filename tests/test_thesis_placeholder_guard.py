"""The thesis guard must still catch fabricated results after being relaxed.

Round 11 allowed curation facts (search counts, panel sizes, metadata fill
rates) to be written concretely when a repository file is cited nearby, so the
thesis can state how the data was assembled. Relaxing a safety net is exactly
how safety nets disappear, so these tests pin the boundary:

  * a fabricated experimental metric must fail, with OR without a nearby source
  * a genuine curation number with a source must pass
  * a design constant must pass
  * the real drafts must pass
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_thesis_placeholders.py"

spec = importlib.util.spec_from_file_location("verify_thesis_placeholders_t", str(SCRIPT))
vp = importlib.util.module_from_spec(spec)
sys.modules["verify_thesis_placeholders_t"] = vp
spec.loader.exec_module(vp)


class GuardBoundaryTests(unittest.TestCase):
    def check(self, body):
        path = ROOT / ".tmp" / "vp_case_under_test.md"
        path.parent.mkdir(exist_ok=True)
        try:
            # Python 3.7: Path.write_text has no `newline` argument.
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write("# t\n\n" + body + "\n")
            return vp.check_file(path)
        finally:
            if path.exists():
                path.unlink()

    # ---------- must still catch fabrication ----------

    def test_fabricated_accuracy_without_source_fails(self):
        self.assertTrue(self.check("0.1× 下 Top-1 准确率达到 96.3%。"))

    def test_fabricated_accuracy_with_a_nearby_source_still_fails(self):
        """关键用例：引用数据来源不得成为编造结果指标的通行证。"""
        problems = self.check(
            "0.1× 下 Top-1 准确率达到 96.3%\n"
            "（见 `data/metadata/server/pilot_manifest.tsv`）。")
        self.assertTrue(problems, "a cited source must not license a fake metric")

    def test_fabricated_recall_with_source_still_fails(self):
        problems = self.check(
            "marker recall 为 88.5%（`data/metadata/search/ena_search_summary.tsv`）。")
        self.assertTrue(problems)

    def test_unknown_percentage_without_source_fails(self):
        self.assertTrue(self.check("面板覆盖了 42.7% 的品种。"))

    def test_measured_depth_still_fails(self):
        self.assertTrue(self.check("六个梯度的实测深度为 0.98×。"))

    # ---------- must allow what is legitimately known ----------

    def test_curation_count_with_source_passes(self):
        self.assertEqual(
            self.check("候选样本共 32,564 条（`data/metadata/candidates/candidate_samples.tsv`）。"),
            [])

    def test_citation_on_the_following_line_still_counts(self):
        """Markdown 换行不该让溯源失效。"""
        self.assertEqual(
            self.check("`cultivar` 非空的有 16,243 条，即填充率 75.0%\n"
                       "（`data/metadata/candidates/sample_attrs.tsv`）。"),
            [])

    def test_design_constants_pass(self):
        self.assertEqual(
            self.check("候选深度梯度为 1×、0.5×、0.2×、0.1×、0.05×、0.02×。"), [])

    # ---------- generated-appendix exemption must not be a loophole ----------

    BANNER = ("# 附录 A\n\n> 本附录由 `scripts/build_appendix_samples.py` 从清单自动生成，请勿手工编辑。\n"
              "> 声明大小为元数据值，不是实测下载量。\n\n")

    def test_generated_banner_across_a_line_wrap_is_recognised(self):
        """The real appendix wraps its banner; a one-line regex would reject it."""
        text = (ROOT / "docs" / "thesis" / "APPENDIX_A_samples.md").read_text(encoding="utf-8")
        self.assertTrue(vp.GENERATED_BANNER.search(text[:vp.BANNER_CHARS]))
        self.assertTrue(vp.DECLARED_DISCLAIMER.search(text[:vp.BANNER_CHARS]))

    def test_fabricated_metric_still_fails_in_a_generated_file(self):
        """Claiming 'generated' must not license a fake accuracy in table OR prose."""
        path = ROOT / ".tmp" / "vp_gen_case.md"
        path.parent.mkdir(exist_ok=True)
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(self.BANNER + "| 深度 | Top-1 准确率 |\n| --- | --- |\n"
                             "| 0.1× | 96.3% |\n")
            self.assertTrue(vp.check_file(path), "fake metric in a table slipped through")

            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(self.BANNER + "本方法在 0.1× 下准确率达到 96.3%。\n")
            self.assertTrue(vp.check_file(path), "fake metric in prose slipped through")
        finally:
            if path.exists():
                path.unlink()

    def test_a_file_without_the_banner_gets_no_exemption(self):
        """Only a file that both names its generator and disclaims measurement."""
        path = ROOT / ".tmp" / "vp_nobanner_case.md"
        path.parent.mkdir(exist_ok=True)
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write("| 深度 | 估计深度 |\n| --- | --- |\n| 1 | 38.49× |\n")
            self.assertTrue(vp.check_file(path), "table numbers passed without a banner")
        finally:
            if path.exists():
                path.unlink()

    def test_banner_alone_without_disclaimer_is_insufficient(self):
        path = ROOT / ".tmp" / "vp_halfbanner_case.md"
        path.parent.mkdir(exist_ok=True)
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write("# x\n\n由 `scripts/build_appendix_samples.py` 自动生成。\n\n"
                             "| 深度 | 值 |\n| --- | --- |\n| 1 | 38.49× |\n")
            self.assertTrue(vp.check_file(path),
                            "generator name without a declared-value disclaimer is not enough")
        finally:
            if path.exists():
                path.unlink()

    # ---------- the real thing ----------

    def test_real_thesis_drafts_are_clean(self):
        for path in sorted((ROOT / "docs" / "thesis").glob("*.md")):
            if path.name == "PLACEHOLDER_CONVENTIONS.md":
                continue
            with self.subTest(path=path.name):
                self.assertEqual(vp.check_file(path), [],
                                 "%s contains a result-like number" % path.name)


class MetaDocumentExemptionTests(unittest.TestCase):
    """The meta-document escape hatch must not become a hole.

    Appendix D is a *record of the guard's own rules*, so it must be able to
    quote forbidden numbers as counter-examples. That is a real need -- but a
    file that simply declares itself a meta-document must not thereby be able
    to assert fabricated results.
    """
    DECL = "<!-- meta-document: marker-guard -->"

    def check(self, body):
        path = ROOT / ".tmp" / "vp_meta_under_test.md"
        path.parent.mkdir(exist_ok=True)
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write("# t\n\n" + body + "\n")
            return vp.check_file(path)
        finally:
            if path.exists():
                path.unlink()

    def test_declaration_alone_does_not_exempt_a_fabricated_metric(self):
        """Declaring the file a meta-document must grant nothing by itself."""
        body = self.DECL + "\n\n本实验 Top-1 准确率为 96.3%。"
        self.assertTrue(self.check(body), "declaration alone must not exempt")

    def test_declaration_alone_does_not_exempt_outside_a_block(self):
        body = self.DECL + "\n\n正文 0.1× 下召回率达到 88%。"
        self.assertTrue(self.check(body))

    def test_marked_block_does_exempt_quoted_examples(self):
        body = (self.DECL
                + "\n\n<!-- guard-examples-start -->\n"
                + "守卫必须拒绝 `实测深度为 0.98×` 这类写法。\n"
                + "<!-- guard-examples-end -->\n")
        self.assertEqual(self.check(body), [])

    def test_exemption_stops_at_the_end_marker(self):
        """A fabricated metric after the block must still fail."""
        body = (self.DECL
                + "\n\n<!-- guard-examples-start -->\n"
                + "反例：`实测深度为 0.98×`。\n"
                + "<!-- guard-examples-end -->\n"
                + "\n本次实验实测深度为 0.98×。")
        self.assertTrue(self.check(body), "exemption leaked past the end marker")

    def test_block_without_the_declaration_does_not_exempt(self):
        """The delimiters alone must not be enough either."""
        body = ("<!-- guard-examples-start -->\n"
                + "本次实验实测深度为 0.98×。\n"
                + "<!-- guard-examples-end -->\n")
        self.assertTrue(self.check(body), "block alone must not exempt")

    def test_unterminated_block_does_not_exempt_to_end_of_file(self):
        """An unclosed marker must NOT swallow the rest of the file.

        My first version of this test asserted the opposite, having read the
        non-greedy regex as if it were safe. It is not: with no end marker the
        block would extend to EOF and silently disable the guard for everything
        below. The code now refuses to exempt an unclosed block at all.
        """
        body = (self.DECL
                + "\n\n<!-- guard-examples-start -->\n"
                + "反例：`实测深度为 0.98×`。\n"
                + "\n本次实验实测深度为 0.98×。")
        self.assertTrue(self.check(body),
                        "an unclosed block must exempt nothing")

    def test_real_appendix_d_passes(self):
        self.assertEqual(vp.check_file(ROOT / "docs" / "thesis"
                                       / "APPENDIX_D_verification.md"), [])


if __name__ == "__main__":
    unittest.main()
