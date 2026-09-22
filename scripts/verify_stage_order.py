"""Verify run_all.sh stage resolution semantics without a POSIX shell.

The orchestrator used to decide "has this stage been reached?" with a
lexicographic string comparison. That silently skipped ``04_joint_snp`` when
resuming from ``04``, because ``"04_joint_snp" < "04_variant_depth"``. This
check pins the array-index behaviour that replaced it.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "server" / "run_all.sh").read_text(encoding="utf-8")

STAGES = re.search(r"STAGES=\(([^)]*)\)", src).group(1).split()


def stage_index(want: str):
    try:
        return STAGES.index(want)
    except ValueError:
        return None


def resolve(from_arg: str):
    """Mirror the run_all.sh logic: exact name first, then numeric prefix."""
    if stage_index(from_arg) is not None:
        return from_arg
    for st in STAGES:
        if st.startswith(from_arg):
            return st
    return None


def main() -> int:
    failures = []

    def check(condition, message):
        if condition:
            print("[OK] %s" % message)
        else:
            print("[FAIL] %s" % message)
            failures.append(message)

    # Stage 07 must be scheduled and ordered last.
    check("07_identify" in STAGES, "07_identify is scheduled")
    check(STAGES[-1] == "07_identify", "07_identify runs last")
    check(len(STAGES) == len(set(STAGES)), "stage names are unique")

    # The old string comparison broke on these: "04_joint_snp" < "04_variant_depth"
    # lexicographically, so resuming from 04 could skip the joint calling stage.
    check("04_joint_snp" < "04_variant_depth", "string order of the two 04 stages is reversed")
    check(stage_index("04_variant_depth") < stage_index("04_joint_snp"), "array order keeps variant_depth before joint_snp")

    check(stage_index("04_joint_snp") == 5, "joint SNP resolves to index 5")

    # From-argument resolution.
    check(resolve("00") == "00_probe", "FROM=00 resolves to 00_probe")
    check(resolve("04") == "04_variant_depth", "FROM=04 resolves to the first 04 stage")
    check(resolve("07") == "07_identify", "FROM=07 resolves to 07_identify")
    check(resolve("05_simulate") == "05_simulate", "FROM accepts an exact stage name")
    check(resolve("99") is None, "unknown FROM is rejected")

    # Resume-from-07 must run only the last stage.
    start = stage_index(resolve("07"))
    ran = [st for i, st in enumerate(STAGES) if i >= start]
    check(ran == ["07_identify"], "resuming from 07 runs only 07_identify")

    # Resume-from-04 must still reach everything after it, in order.
    start = stage_index(resolve("04"))
    ran = [st for i, st in enumerate(STAGES) if i >= start]
    check(ran == ["04_variant_depth", "04_joint_snp", "05_simulate", "06_export", "07_identify"], "resuming from 04 runs all later stages in order")

    # The script must no longer rely on the lexicographic comparison.
    check('[ "$num" \\< "$FROM" ]' not in src, "lexicographic FROM comparison was removed")

    # Stage files referenced by run_all.sh must exist.
    for stage in STAGES:
        check((ROOT / "server" / ("%s.sh" % stage)).exists(), "stage script exists: %s.sh" % stage)

    print("\nResult: %d failed" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
