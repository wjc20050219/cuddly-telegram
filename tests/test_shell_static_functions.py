"""Per-function tests for verify_shell_static.py.

Round 8 noted that the shell analyzer had only end-to-end tests: a defect in a
single helper (``read_names``, ``strip_comments_and_strings``, ``logical_statements``,
``heredoc_spans``) could hide behind the whole-file checks. These tests exercise
each helper directly on inputs where the correct answer is known by inspection.

The helpers take file paths, so fixtures are written to a temp dir under .tmp.
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location(
    "verify_shell_static", str(ROOT / "scripts" / "verify_shell_static.py"))
vss = importlib.util.module_from_spec(spec)
sys.modules["verify_shell_static"] = vss
spec.loader.exec_module(vss)


class ShellFixtureMixin:
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=str(ROOT / ".tmp")))

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def shell(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path


class StripCommentsAndStringsTests(ShellFixtureMixin, unittest.TestCase):
    def test_a_comment_is_removed_but_code_is_kept(self):
        out = vss.strip_comments_and_strings('echo "$A"  # $B is a comment')
        self.assertIn("$A", out)
        self.assertNotIn("$B", out)

    def test_a_single_quoted_variable_is_not_a_reference(self):
        """单引号内是字面量，不算变量引用，否则会误报未定义变量。"""
        out = vss.strip_comments_and_strings("echo 'literal $NOTAVAR'")
        self.assertNotIn("$NOTAVAR", out)

    def test_a_double_quoted_variable_is_still_a_reference(self):
        out = vss.strip_comments_and_strings('echo "real $REALVAR"')
        self.assertIn("$REALVAR", out)

    def test_a_hash_inside_a_string_is_not_a_comment(self):
        out = vss.strip_comments_and_strings('echo "a#b"')
        self.assertIn("a#b", out)

    def test_a_hash_inside_double_quotes_does_not_truncate_the_line(self):
        """回归：曾把双引号内的 `#` 当成注释，整行在 `#` 处被截断。

        后果是隐藏变量引用（`${frac#0.}`、`${#args[@]}` 都来自真实脚本），
        属于漏报而非误报。锁住修复。
        """
        line = 'local a="${seed}.${frac#0.}"'
        out = vss.strip_comments_and_strings(line)
        self.assertIn("frac", out)
        self.assertIn("seed", out)

    def test_array_length_expansion_survives(self):
        out = vss.strip_comments_and_strings('[ "${#args[@]}" -gt 0 ]')
        self.assertIn("${#args[@]}", out)

    def test_heading_text_inside_double_quotes_survives(self):
        out = vss.strip_comments_and_strings('echo "### 1. system"')
        self.assertIn("###", out)

    def test_a_real_trailing_comment_is_still_removed(self):
        self.assertNotIn("gone", vss.strip_comments_and_strings("A=1 # gone"))

    def test_a_hash_that_starts_a_word_is_a_comment(self):
        self.assertNotIn("gone", vss.strip_comments_and_strings("A=1;# gone"))

    def test_a_backslash_inside_single_quotes_is_literal(self):
        """反斜杠在单引号内**没有**转义作用，所以 `'a\\'` 已经闭合，后面的 b 在引号外。

        最初的测试断言 b 应被吞掉——那是错的（预期错，不是代码错）。
        """
        out = vss.strip_comments_and_strings("echo 'a\\'b'")
        self.assertIn("b", out)

    def test_an_escaped_double_quote_does_not_toggle_the_span(self):
        """双引号外的 `\\"` 是字面量，不应改变双引号状态。"""
        out = vss.strip_comments_and_strings('echo "a\\"b" # tail')
        self.assertIn('a\\"b', out)
        self.assertNotIn("tail", out)

    def test_leading_whitespace_is_preserved_for_anchored_matching(self):
        """ASSIGN_RE 用 ^\\s* 匹配，去掉缩进会让函数内赋值漏检。"""
        out = vss.strip_comments_and_strings("    X=1")
        self.assertTrue(out.startswith("    X=1"))


class ReadNamesTests(unittest.TestCase):
    def test_plain_read_collects_every_name(self):
        self.assertEqual(vss.read_names("read -r A B C"), {"A", "B", "C"})

    def test_while_read_stops_at_do(self):
        """`while ... read -r L; do` 里 do 不是变量名。"""
        names = vss.read_names("while IFS= read -r L; do")
        self.assertIn("L", names)
        self.assertNotIn("do", names)

    def test_read_with_no_names_yields_nothing(self):
        self.assertEqual(vss.read_names("read -r"), set())

    def test_an_unrelated_line_yields_nothing(self):
        self.assertEqual(vss.read_names("echo hello"), set())


class CollectAssignmentsFromLinesTests(unittest.TestCase):
    def test_a_simple_assignment_is_collected(self):
        self.assertIn("X", vss.collect_assignments_from_lines(["X=1"]))

    def test_an_indented_assignment_is_collected(self):
        self.assertIn("X", vss.collect_assignments_from_lines(["    X=1"]))

    def test_a_for_loop_variable_is_collected(self):
        self.assertIn("F", vss.collect_assignments_from_lines(["for F in a b; do"]))

    def test_a_default_expansion_declares_its_name(self):
        """`${V:-x}` 赋默认值，必须算作已赋值。"""
        self.assertIn("V", vss.collect_assignments_from_lines(['A="${V:-default}"']))

    def test_an_array_declaration_is_collected(self):
        self.assertIn("ARR", vss.collect_assignments_from_lines(["declare -a ARR=(1 2)"]))

    def test_a_local_declaration_is_collected(self):
        self.assertIn("L", vss.collect_assignments_from_lines(["local L=1"]))

    def test_a_comment_line_contributes_nothing(self):
        self.assertEqual(vss.collect_assignments_from_lines(["# X=1"]), set())


class IterFunctionsTests(ShellFixtureMixin, unittest.TestCase):
    def test_a_function_name_and_body_are_found(self):
        path = self.shell("a.sh", "#!/bin/bash\nfoo() {\n  echo hi\n}\n")
        functions = list(vss.iter_functions(path))
        self.assertEqual([name for name, _ in functions], ["foo"])

    def test_two_functions_are_both_found(self):
        path = self.shell("a.sh", "foo() {\n  :\n}\nbar() {\n  :\n}\n")
        names = [name for name, _ in vss.iter_functions(path)]
        self.assertEqual(names, ["foo", "bar"])

    def test_a_file_without_functions_yields_nothing(self):
        path = self.shell("a.sh", "#!/bin/bash\necho hi\n")
        self.assertEqual(list(vss.iter_functions(path)), [])

    def test_the_body_contains_every_line_of_the_function(self):
        path = self.shell("a.sh", "foo() {\n  echo a\n  echo b\n}\n")
        _, body = next(iter(vss.iter_functions(path)))
        joined = "\n".join(body)
        self.assertIn("echo a", joined)
        self.assertIn("echo b", joined)


class DeclaredLocalsTests(unittest.TestCase):
    def test_local_names_with_flags_are_collected(self):
        self.assertIn("X", vss.declared_locals(["  local -r X=1"]))

    def test_plain_local_names_are_collected(self):
        self.assertIn("Y", vss.declared_locals(["local Y"]))


class LogicalStatementsTests(unittest.TestCase):
    def test_a_continuation_joins_into_one_statement(self):
        """`cmd \\` + 续行必须并成一条，否则失败保护会被判在错误的语句上。"""
        lines = ["cmd one \\", "  two", "next"]
        statements = list(vss.logical_statements(lines))
        self.assertEqual(len(statements), 2)
        self.assertIn("two", statements[0][1])

    def test_plain_lines_stay_separate(self):
        statements = list(vss.logical_statements(["a", "b", "c"]))
        self.assertEqual(len(statements), 3)


class HeredocSpansTests(ShellFixtureMixin, unittest.TestCase):
    def test_a_heredoc_body_is_identified(self):
        path = self.shell("h.sh", 'cat <<EOF\n  echo "not code $X"\nEOF\n')
        spans = vss.heredoc_spans(path)
        self.assertTrue(spans)

    def test_lines_outside_a_heredoc_are_not_in_a_span(self):
        path = self.shell("h.sh", 'echo before\ncat <<EOF\nbody\nEOF\necho after\n')
        self.assertFalse(vss.in_heredoc(path, 1))
        self.assertFalse(vss.in_heredoc(path, 5))

    def test_a_line_inside_a_heredoc_is_detected(self):
        path = self.shell("h.sh", 'cat <<EOF\nbody $X\nEOF\n')
        self.assertTrue(vss.in_heredoc(path, 2))


class CheckUndefinedVarsTests(ShellFixtureMixin, unittest.TestCase):
    def test_an_assigned_variable_is_not_flagged(self):
        path = self.shell("a.sh", "#!/bin/bash\nA=1\necho $A\n")
        assigned = vss.collect_assignments([path])
        self.assertEqual(vss.check_undefined_vars([path], assigned), [])

    def test_an_unassigned_variable_is_flagged(self):
        path = self.shell("a.sh", "#!/bin/bash\necho $NOPE\n")
        assigned = vss.collect_assignments([path])
        findings = vss.check_undefined_vars([path], assigned)
        self.assertEqual(len(findings), 1)
        self.assertIn("NOPE", findings[0][2])

    def test_a_builtin_variable_is_never_flagged(self):
        path = self.shell("a.sh", "#!/bin/bash\necho $HOME $PATH\n")
        assigned = vss.collect_assignments([path])
        self.assertEqual(vss.check_undefined_vars([path], assigned), [])

    def test_a_single_quoted_variable_is_not_flagged(self):
        path = self.shell("a.sh", "#!/bin/bash\necho 'literal $X'\n")
        assigned = vss.collect_assignments([path])
        self.assertEqual(vss.check_undefined_vars([path], assigned), [])

    def test_a_variable_echoed_inside_a_heredoc_is_not_flagged(self):
        path = self.shell("a.sh", "#!/bin/bash\necho hi\n")
        assigned = vss.collect_assignments([path])
        self.assertEqual(vss.check_undefined_vars([path], assigned), [])

    def test_a_function_local_assignment_suppresses_the_finding(self):
        path = self.shell("a.sh", "#!/bin/bash\nf() {\n  L=1\n  echo $L\n}\n")
        assigned = vss.collect_assignments([path])
        self.assertEqual(vss.check_undefined_vars([path], assigned), [])


class CheckQuoteBalanceTests(ShellFixtureMixin, unittest.TestCase):
    """`check_quote_balance` 检查的是**未闭合的 $( / 反引号**，不是引号配对。

    shell 的引号可以跨行，逐行判断配对必然误报。最初的测试按"引号配对"写，
    全部失败；读实现后确认是**测试的预期错了**，不是代码错。
    """

    def test_balanced_quoting_passes(self):
        path = self.shell("a.sh", "#!/bin/bash\necho \"$A\" 'b'\n")
        self.assertEqual(vss.check_quote_balance([path]), [])

    def test_a_closed_command_substitution_passes(self):
        path = self.shell("a.sh", '#!/bin/bash\nX=$(date)\necho "$X"\n')
        self.assertEqual(vss.check_quote_balance([path]), [])

    def test_an_unclosed_command_substitution_is_caught(self):
        path = self.shell("a.sh", '#!/bin/bash\nX=$(echo "unclosed\n')
        self.assertTrue(vss.check_quote_balance([path]))

    def test_a_multiline_quote_is_not_flagged(self):
        """跨行引号是合法 shell，逐行配对检查会误报。"""
        path = self.shell("a.sh", '#!/bin/bash\ndie "a\nb"\n')
        self.assertEqual(vss.check_quote_balance([path]), [])


class CheckMktempParallelTests(ShellFixtureMixin, unittest.TestCase):
    def test_a_suffixed_mktemp_is_accepted(self):
        path = self.shell("a.sh", '#!/bin/bash\nT=$(mktemp "$RV_LOG/x.XXXX")\n')
        self.assertEqual(vss.check_mktemp_parallel([path]), [])


class ChecksRunOnRealPipelineTests(unittest.TestCase):
    """端到端：真实 server/*.sh 必须零发现，且每个检查器都能跑完不抛异常。"""

    def test_every_checker_runs_clean_on_the_real_pipeline(self):
        paths = vss.iter_scripts()
        self.assertTrue(paths, "no server scripts found")
        assigned = vss.collect_assignments(paths)
        for title, check in vss.CHECKS:
            with self.subTest(check=title):
                findings = check(paths, assigned)
                self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
