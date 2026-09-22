"""The full-checksum invariant must actually fire on truncation.

`reference_genome_plan.md` once claimed `03_align.sh` stored only the first 16
hex characters of SHA256. The script had already been fixed, so the *document*
was stale -- a claim about the code that nothing checked. The invariant is now
mechanical, and this test proves it has teeth: inject the historical truncation,
confirm the scope checker fails, and restore the file byte-for-byte.
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "server" / "03_align.sh"
SCOPE = ROOT / "scripts" / "verify_undergraduate_scope.py"


def run_scope():
    proc = subprocess.run([sys.executable, str(SCOPE)], capture_output=True,
                          text=True, cwd=str(ROOT))
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class FullChecksumInvariantTests(unittest.TestCase):
    def test_the_real_script_passes(self):
        code, text = run_scope()
        self.assertEqual(code, 0, "scope checker is not clean:\n%s" % text[-2000:])
        self.assertIn("never truncated", text)

    def test_injecting_truncation_is_detected(self):
        original = TARGET.read_bytes()
        try:
            mutated = original.decode("utf-8").replace(
                "sha256sum \"$gz\" | awk '{print $1}'",
                "sha256sum \"$gz\" | awk '{print $1}' | cut -c1-16")
            self.assertNotEqual(mutated, original.decode("utf-8"),
                                "fixture no longer matches the script; update the mutation")
            # Python 3.7 has no `newline` argument on Path.write_text.
            with TARGET.open("w", encoding="utf-8", newline="") as handle:
                handle.write(mutated)
            code, text = run_scope()
            self.assertNotEqual(code, 0, "truncated checksum was NOT detected")
            self.assertIn("cut -c1-16", text)
        finally:
            TARGET.write_bytes(original)
        self.assertEqual(TARGET.read_bytes(), original,
                         "03_align.sh was not restored byte-for-byte")

    def test_restored_script_passes_again(self):
        """恢复后必须回到干净状态，否则夹具会污染后续测试。"""
        code, _ = run_scope()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
