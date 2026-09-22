"""Verification scripts must survive the unicode in real data.

`verify_pub_match.py` fetches abstracts from Europe PMC and prints them. Real
abstracts carry characters outside the local console's encoding -- the very
first case contains a non-breaking space (U+00A0) and crashed the script with
``UnicodeEncodeError: 'gbk' codec can't encode character '\\xa0'``.

That is a serious kind of defect for a *verification tool*: it failed on the
real data it exists to check, and would look like "the check found nothing"
rather than "the check never ran". The fix routes printed text through an
encoding-tolerant helper instead of asking the caller to set an environment
variable.

These tests assert the helper's behaviour directly, so they hold regardless of
what the current console encoding happens to be.
"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_pub_match.py"
SOURCE = SCRIPT.read_text(encoding="utf-8")


def load_module():
    """Import the script under its real name without executing the main body."""
    import importlib.util
    import types
    name = "ricevar_verify_pub_match_under_test"
    module = types.ModuleType(name)
    module.__package__ = ""
    sys.modules[name] = module
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    # The script runs checks at import time (module level), so stub the network
    # call out before executing it.
    source = SOURCE.split('print("=" * 76)')[0]
    exec(compile(source, str(SCRIPT), "exec"), module.__dict__)
    return module


class EncodingToleranceTests(unittest.TestCase):
    def test_safe_helper_exists(self):
        self.assertIn("def safe(", SOURCE,
                      "打印必须经过编码容错处理")

    def test_no_bare_print_of_abstract_text(self):
        """The abstract lines specifically must go through safe()."""
        for line in SOURCE.splitlines():
            stripped = line.strip()
            if stripped.startswith("print(f\"    · ") or \
               stripped.startswith("print(f\"  标题：") or \
               stripped.startswith("print(f\"  期刊："):
                with self.subTest(line=stripped[:50]):
                    self.assertTrue(stripped.startswith("print(safe("),
                                    "摘要文本未经 safe() 直接打印：%s" % stripped)

    def test_non_breaking_space_survives(self):
        module = load_module()
        boom = "rice\xa0varieties"          # the exact character class that crashed
        with redirect_stdout(io.StringIO()):
            out = module.safe(boom)
        self.assertIn("rice", out)
        self.assertIn("varieties", out)

    def test_ascii_passes_through_unchanged(self):
        module = load_module()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(module.safe("plain ascii"), "plain ascii")

    def test_every_character_is_encodable_in_the_captured_console(self):
        """Whatever safe() returns must be printable, or the crash just moves.

        Note the encoding comes from the module's captured constant, not from
        ``sys.stdout`` here -- under ``redirect_stdout`` the latter is a
        StringIO with no ``encoding``. My first version of the fix used the
        live ``sys.stdout`` and this test is what exposed it.
        """
        module = load_module()
        payload = "a\xa0b\u2019c\u2014d\ufeffe"
        with redirect_stdout(io.StringIO()):
            out = module.safe(payload)
        out.encode(module._CONSOLE_ENCODING)      # must not raise

    def test_a_redirected_stdout_does_not_weaken_the_filter(self):
        """Regression: the fix must not depend on the live sys.stdout."""
        module = load_module()
        with redirect_stdout(io.StringIO()):
            out = module.safe("nobreak\xa0space")
        if module._CONSOLE_ENCODING.lower().replace("-", "") == "gbk":
            self.assertNotIn("\xa0", out,
                             "重定向后非断行空格又漏过去了")

    def test_script_does_not_require_an_environment_variable(self):
        """The fix must be in code, not in a documented PYTHONIOENCODING habit."""
        self.assertNotIn("PYTHONIOENCODING", SOURCE)

    def test_script_compiles(self):
        compile(SOURCE, str(SCRIPT), "exec")


if __name__ == "__main__":
    unittest.main()
