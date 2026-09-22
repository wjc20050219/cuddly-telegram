#!/usr/bin/env python3
"""Check that commands documented for the school server are still runnable.

The runbook and README are executed on a server this project cannot reach, so a
stale flag (``--matrix`` renamed to ``--matrix-tsv``, a script moved, an option
deleted) fails only after upload, on a machine where debugging is expensive and
the failure looks like a data problem rather than a documentation problem.

This verifier reads every ``python scripts/<name>.py ...`` invocation out of the
documentation, asks each script for its real ``--help`` output, and reports any
flag the docs use that the script no longer accepts. It also checks that every
``scripts/*.py`` and ``server/*.sh`` path mentioned in the docs actually exists.

Usage::

    python scripts/verify_documented_commands.py
    python scripts/verify_documented_commands.py --strict   # exit 1 on any finding
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Documents a user is expected to follow. Deliberately curated rather than a
# whole-tree scan: historical round reports describe commands as they were at
# the time and are not instructions.
DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "methods" / "server_pilot_runbook.md",
    ROOT / "docs" / "STATUS.md",
    ROOT / "PROJECT_STRUCTURE.md",
]

# Matches: python scripts/foo.py --bar ...   (stops at a pipe, quote or newline)
INVOCATION = re.compile(r"python3?\s+(scripts/[\w_]+\.py)([^|`\n>]*)")
# Matches any referenced project path, e.g. server/03_map.sh or scripts/x.py.
# The leading group is anchored so a path is only captured when it starts at a
# real boundary: matching a suffix of ``data/metadata/server/x.tsv`` would
# report a nonexistent ``server/x.tsv`` for a file that exists.
PATH_REFERENCE = re.compile(
    r"(?<![\w./-])((?:scripts|server|src|app|tests|docs|data)/[\w_./-]+"
    r"\.(?:py|sh|tsv|md|sqlite|json|yml))")

# Directories whose contents are produced by running the pipeline. A path under
# one of these is an *output*, so its absence before the server run is expected
# and must not be reported as a broken reference. Paths everywhere else are
# inputs (source, documents, manifests) and must already exist.
GENERATED_PREFIXES = ("data/processed/", "data/raw/", "data/interim/",
                      "figures/", "analysis/", "results/")

# Some runtime artefacts are never written inside the repository at all: the
# server pipeline writes them under ``$RV_ROOT`` (``$HOME/ricevar`` by default).
# Documents naming such a file are describing the server, not the checkout.
# (A bare repo-relative path to one of these was a real defect in README.md:
# ``data/metadata/download_log.tsv``; it now correctly points at $RV_ROOT.)


def is_generated(path):
    return path.startswith(GENERATED_PREFIXES)

FLAG = re.compile(r"--[a-z][a-z0-9-]+")


def iter_documented_invocations():
    """Yield ``(doc, script, argument_text, line_number)`` for every mention."""
    for doc in DOCS:
        if not doc.exists():
            continue
        for number, line in enumerate(doc.read_text(encoding="utf-8").split("\n"), 1):
            for match in INVOCATION.finditer(line):
                yield doc, match.group(1), match.group(2), number


def script_flags(script, timeout=60):
    """Return the set of long flags a script accepts, from its real --help."""
    path = ROOT / script
    if not path.exists():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(path), "--help"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(ROOT), stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (proc.stdout or "") + (proc.stderr or "")
    return set(FLAG.findall(text))


def check_invocations():
    findings = []
    cache = {}
    checked = 0
    for doc, script, arguments, number in iter_documented_invocations():
        checked += 1
        if script not in cache:
            cache[script] = script_flags(script)
        available = cache[script]
        if available is None:
            # A documented script that does not exist or cannot print help is a
            # finding in itself: the reader would run a broken command.
            findings.append((doc, number, script,
                             "文档引用的脚本不存在或无法运行 --help", arguments.strip()))
            continue
        unknown = sorted(set(FLAG.findall(arguments)) - available)
        if unknown:
            findings.append((doc, number, script,
                             "文档使用了脚本不支持的参数：%s" % ", ".join(unknown),
                             arguments.strip()))
    return checked, findings, cache


def check_paths():
    """Referenced input paths must exist; generated-output paths need not.

    ``data/metadata/download_log.tsv`` and the similarity matrix are written by
    the pipeline on the server, so flagging them before the run would be a false
    positive. Source files, documents and manifests, by contrast, are inputs the
    reader is told to open -- a missing one is a real documentation defect.
    """
    findings = []
    skipped_generated = []
    for doc in DOCS:
        if not doc.exists():
            continue
        for number, line in enumerate(doc.read_text(encoding="utf-8").split("\n"), 1):
            for match in PATH_REFERENCE.finditer(line):
                candidate = match.group(1)
                if (ROOT / candidate).exists():
                    continue
                if is_generated(candidate):
                    skipped_generated.append(candidate)
                    continue
                findings.append((doc, number, candidate, "文档引用的路径不存在", ""))
    return findings, sorted(set(skipped_generated))


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验文档中的命令是否仍然可执行")
    parser.add_argument("--strict", action="store_true", help="有任何发现即 exit 1")
    args = parser.parse_args(argv)

    print("检查 %d 份文档：%s" % (len(DOCS), "、".join(d.name for d in DOCS if d.exists())))
    if not any(d.exists() for d in DOCS):
        print("找不到任何待检查文档，无法验证。")
        return 1

    checked, findings, cache = check_invocations()
    print("识别到 %d 处 python 脚本调用，涉及 %d 个脚本" % (checked, len(cache)))

    path_findings, generated = check_paths()
    total = len(findings) + len(path_findings)
    if generated:
        print("  [--] %d 个路径属于流水线产物，尚未生成属正常：%s"
              % (len(generated), "、".join(generated)))

    if not total:
        print("  [OK] 文档中的命令与路径全部有效")
        print("合计发现：0")
        return 0

    for doc, number, script, message, snippet in findings:
        print("  [!!] %s:%d %s" % (doc.relative_to(ROOT), number, message))
        if snippet:
            print("       > %s" % snippet)
    for doc, number, candidate, message, _ in path_findings:
        print("  [!!] %s:%d %s: %s" % (doc.relative_to(ROOT), number, message, candidate))
    print("合计发现：%d" % total)
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
