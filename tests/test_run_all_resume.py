"""Exit-code reporting in the orchestrator must not be fragile.

`run_all.sh` prints "阶段 X 失败（退出码 N）" when a stage fails. That message is
the only clue available when debugging on a server this project cannot reach, so
the number must be the failing stage's status, and it must stay correct if
someone later inserts a line above it.

The original form `log "... $?"` inside the `else` branch was correct (nothing
executes between the condition and the expansion, because `then`/`else` are not
commands) but fragile. This test locks the robust form: capture `$?` first.

No shell is available locally, so these are static assertions over the source.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ALL = ROOT / "server" / "run_all.sh"


class ExitCodeReportingTests(unittest.TestCase):
    def setUp(self):
        self.text = RUN_ALL.read_text(encoding="utf-8")
        self.lines = self.text.split("\n")

    def test_the_failing_stage_message_reports_a_named_variable(self):
        """失败信息里必须是 $rc，而不是裸的 $?。"""
        self.assertRegex(
            self.text, r"阶段 \$st 失败（退出码 \$rc）",
            "the failure message should interpolate a captured variable")

    def test_the_exit_code_is_captured_before_being_used(self):
        """`rc=$?` 必须先于使用它的 log 出现。"""
        capture = self.text.index("rc=$?")
        use = self.text.index("退出码 $rc")
        self.assertLess(capture, use,
                        "rc must be assigned before the log line that prints it")

    def test_the_capture_immediately_follows_the_else(self):
        """`rc=$?` 与 else 之间不能有**命令**。

        注释和空行都可以：它们不改变 `$?`。但如果中间出现任何真实命令
        （哪怕是一个 `:` 之外的简单赋值），存下的就不再是被测脚本的退出码。
        """
        idx = next(i for i, l in enumerate(self.lines) if "rc=$?" in l)
        # 向上回溯，跳过注释与空行，应当直接撞上 else。
        j = idx - 1
        while j >= 0 and (not self.lines[j].strip()
                          or self.lines[j].lstrip().startswith("#")):
            j -= 1
        self.assertGreaterEqual(j, 0, "rc=$? appears before any else")
        self.assertIn("else", self.lines[j],
                      "a command sits between else and rc=$?: %r" % self.lines[j])

    def test_no_bare_dollar_question_remains_in_a_log_call(self):
        """反向断言：不允许再出现 `log ... $?` 这种依赖展开时序的写法。"""
        offenders = [l for l in self.lines if "log " in l and "$?" in l]
        self.assertEqual(offenders, [],
                         "a log call expands $? at an unsafe position: %s" % offenders)

    def test_the_stage_that_failed_is_named(self):
        self.assertIn("${st%%_*}", self.text,
                      "the message should tell the user which stage to resume from")


if __name__ == "__main__":
    unittest.main()
