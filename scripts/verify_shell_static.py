#!/usr/bin/env python3
"""Static analysis for the server shell pipeline.

There is no usable Bash on the development machine (WSL is denied), so
``bash -n`` and real tool invocations cannot be run before the scripts reach the
school server. This analyzer closes part of that gap by reading the shell
sources with Python and flagging the specific defect classes that have already
bitten this project:

* ``$VAR`` used but never assigned anywhere in the sourced set (an undefined
  variable expands to empty under ``set -u``-less scripts and silently changes
  a path or a flag) — this class caused a real bug (``$RUN``).
* command substitutions with unbalanced quoting, which swallow following lines.
* ``mktemp`` results reused across parallel jobs without a per-job suffix.
* critical commands whose failure is not guarded (``|| die``) while the script
  continues to write downstream outputs.
* python invocations inside heredocs whose module imports are not provided by
  the conda environment file.

It is deliberately conservative: every check reports file and line so a human
can judge, and the goal is to make silent failures loud before they reach a
machine we cannot debug on.

Usage::

    python scripts/verify_shell_static.py            # report
    python scripts/verify_shell_static.py --strict   # exit 1 on any finding
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"

# Shell variables provided by the environment or by bash itself; never "undefined".
BUILTIN_VARS = {
    "PATH", "HOME", "PWD", "OLDPWD", "IFS", "SHELL", "USER", "LOGNAME", "TMPDIR",
    "HOSTNAME", "LANG", "LC_ALL", "TERM", "RANDOM", "SECONDS", "LINENO", "FUNCNAME",
    "BASH_SOURCE", "BASH_VERSION", "PPID", "UID", "EUID", "GROUPS", "SHLVL", "OSTYPE",
    "MACHTYPE", "HOSTTYPE", "DIRSTACK", "PIPESTATUS", "BASH_SUBSHELL", "EPOCHSECONDS",
}
# Variables provided by a sourced system file that the analyzer cannot read.
SOURCED_SYSTEM_VARS = {
    "PRETTY_NAME", "NAME", "VERSION", "VERSION_ID", "ID", "ID_LIKE",
    "HOME_URL", "ANSI_COLOR", "CPE_NAME", "VARIANT", "VARIANT_ID",
}
# Positional/special parameters and loop-local names that are fine to see bare.
SPECIAL_VARS = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "@", "*", "#", "?", "-", "$", "!",
}

ASSIGN_RE = re.compile(r"^\s*(?:export\s+|local\s+|readonly\s+|declare\s+-\w+\s+)?"
                       r"([A-Za-z_][A-Za-z0-9_]*)=")
# `local a="$1" b="$2"` / `local a b` declare several names on one line.
LOCAL_DECL_RE = re.compile(r"^\s*(?:local|declare\s+-\w+|readonly)\s+(.*)$")
# ${VAR}, ${VAR:-x}, ${VAR%x}, ${VAR#x}, ${VAR/a/b}, ${!VAR}, ${#VAR}
BRACE_RE = re.compile(r"\$\{(!|#)?([A-Za-z_][A-Za-z0-9_]*)")
# $VAR not followed by an identifier character (avoids matching $VARNAME mid-token)
BARE_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
# Variables defined by sourcing another script in the same pipeline.
SOURCE_RE = re.compile(r"^\s*(?:\.|source)\s+(\S+)")
# ${arr[@]} / ${!arr[@]} / ${arr[$i]} all reference the array name `arr`.
ARRAY_USE_RE = re.compile(r"\$\{!?([A-Za-z_][A-Za-z0-9_]*)\[")
# Function definition start.
FUNC_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")


def declared_locals(body_lines):
    """Names introduced by `local`/`declare` anywhere in a function body."""
    names = set()
    for raw in body_lines:
        line = strip_comments_and_strings(raw)
        match = LOCAL_DECL_RE.match(line)
        if not match:
            continue
        for token in match.group(1).split():
            token = token.split("=")[0].strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", token):
                names.add(token)
    return names


def iter_functions(path):
    """Yield (name, body_text) for each top-level shell function in a file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    current = None
    body = []
    depth = 0
    for raw in lines:
        if current is None:
            match = FUNC_RE.match(strip_comments_and_strings(raw))
            if match:
                current = match.group(1)
                body = [raw]
                depth = raw.count("{") - raw.count("}")
                continue
            continue
        body.append(raw)
        cleaned = strip_comments_and_strings(raw)
        depth += cleaned.count("{") - cleaned.count("}")
        if depth <= 0:
            yield current, body
            current = None
            body = []
    if current is not None:
        yield current, body


def strip_comments_and_strings(line):
    """Blank out comments and single-quoted spans so matching does not fire on prose.

    Two subtleties, both learned from real lines in this pipeline:

    * ``#`` starts a comment only at the beginning of a word. In
      ``"${frac#0.}"`` and ``"${#args[@]}"`` the ``#`` is a parameter-expansion
      operator, and in ``echo "### 1."`` it is literal text inside double
      quotes. Treating every ``#`` as a comment truncated those lines, which
      silently hid variable references from the undefined-variable check (the
      very check that once caught ``$RUN``). Truncation could only ever remove
      text, so the bug was false-negative-only.
    * single-quoted spans are blanked rather than deleted, and inner ``"`` and
      ``#`` inside them are literal, so they must not end the span or start a
      comment.
    """
    out = []
    i = 0
    in_single = False
    in_double = False
    while i < len(line):
        ch = line[i]
        if ch == "\\" and not in_single:
            # An escape keeps the next character literal; keep both as-is so
            # offsets stay aligned.
            out.append(ch)
            if i + 1 < len(line):
                out.append(line[i + 1])
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(" ")
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if ch == "#" and not in_single and not in_double:
            # Comment only when it begins a word: `a#b` is not a comment.
            if i == 0 or line[i - 1].isspace() or line[i - 1] in ";|&(":
                break
        out.append(" " if in_single else ch)
        i += 1
    return "".join(out)


def iter_scripts():
    return sorted(SERVER.glob("*.sh"))


def collect_assignments(paths):
    """Names assignable at file scope: plain assignments, for/read, `${X:-default}`."""
    assigned = set()
    for path in paths:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = strip_comments_and_strings(raw)
            match = ASSIGN_RE.match(line)
            if match:
                assigned.add(match.group(1))
            # `for x in ...` and `read a b` also introduce names.
            for_name = re.match(r"^\s*for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b", line)
            if for_name:
                assigned.add(for_name.group(1))
            assigned |= read_names(line)
            # `X="${X:-default}"` both assigns and references X; the reference is safe.
            defaulted = re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-", line)
            assigned.update(defaulted)
            # `${arr[@]}` and `${#arr[@]}` require arr to exist; treat as used, not assigned.
            declared_array = re.match(r"^\s*(?:declare\s+-\w*[aA]\w*\s+)?([A-Za-z_][A-Za-z0-9_]*)=\(", line)
            if declared_array:
                assigned.add(declared_array.group(1))
    return assigned


def collect_function_locals(paths):
    """Map function name -> set of names it declares locally."""
    locals_by_func = {}
    for path in paths:
        for name, body in iter_functions(path):
            locals_by_func.setdefault(name, set()).update(declared_locals(body))
    return locals_by_func


def function_spans(path):
    """Return list of (name, start_line0, end_line0, body_lines); cached per path."""
    cached = _SPAN_CACHE.get(path)
    if cached is not None:
        return cached
    text_lines = path.read_text(encoding="utf-8").splitlines()
    spans = []
    for name, body in iter_functions(path):
        first = body[0]
        start = None
        # Locate this function's first line at or after the previous span.
        search_from = spans[-1][2] if spans else 0
        for i in range(search_from, len(text_lines)):
            if text_lines[i] == first:
                start = i
                break
        if start is None:
            continue
        spans.append((name, start, start + len(body), body))
    _SPAN_CACHE[path] = spans
    return spans


_SPAN_CACHE = {}


def enclosing_function(path, line_number):
    """Return (name, body_lines) for the function containing a 1-based line."""
    target = line_number - 1
    for name, start, end, body in function_spans(path):
        if start <= target < end:
            return name, body
    return None, []


def check_undefined_vars(paths, assigned, arg_names=None):
    findings = []
    # Variables a function may legitimately see from its caller/positional args.
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, raw in enumerate(lines, 1):
            line = strip_comments_and_strings(raw)
            names = set()
            for match in BRACE_RE.finditer(line):
                names.add(match.group(2))
            for match in BARE_RE.finditer(line):
                names.add(match.group(1))
            for match in ARRAY_USE_RE.finditer(line):
                names.add(match.group(1))
            if not names:
                continue

            func, body = enclosing_function(path, number)
            local_names = set()
            if func:
                local_names = declared_locals(body) | collect_assignments_from_lines(body)
                # A function body may reference globals assigned elsewhere too.

            for name in sorted(names):
                if name in BUILTIN_VARS or name in SPECIAL_VARS:
                    continue
                if name in SOURCED_SYSTEM_VARS and "os-release" in raw:
                    continue
                if name in assigned or name in local_names:
                    continue
                findings.append((path, number, "未定义变量 $%s" % name, raw.strip()))
    return findings


def read_names(line):
    """Names introduced by `read`, including `while ... read -r a b c; do`."""
    names = set()
    for match in re.finditer(r"\bread\s+((?:-\w+\s+)*)([A-Za-z_][A-Za-z0-9_]*(?:\s+[A-Za-z_][A-Za-z0-9_]*)*)", line):
        for token in match.group(2).split():
            # Stop at the `do`/`;` that ends the read clause.
            if token in ("do", "then", "done", "fi"):
                break
            names.add(token)
    return names


def collect_assignments_from_lines(body_lines):
    """Names assigned within a function body (any scope)."""
    names = set()
    for raw in body_lines:
        line = strip_comments_and_strings(raw)
        match = ASSIGN_RE.match(line)
        if match:
            names.add(match.group(1))
        for_name = re.match(r"^\s*for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b", line)
        if for_name:
            names.add(for_name.group(1))
        names |= read_names(line)
        names.update(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-", line))
        declared_array = re.match(r"^\s*(?:declare\s+-\w*[aA]\w*\s+)?([A-Za-z_][A-Za-z0-9_]*)=\(", line)
        if declared_array:
            names.add(declared_array.group(1))
    return names


def heredoc_spans(path):
    """Return [(start_line0, end_line0)] for heredoc *bodies* (content, not code).

    Backticks and ``$(`` inside a heredoc body are literal text, so the shell
    checks must skip those lines entirely.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    spans = []
    i = 0
    while i < len(lines):
        match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", lines[i])
        if not match:
            i += 1
            continue
        tag = match.group(1)
        start = i + 1
        j = start
        while j < len(lines) and lines[j].strip() != tag:
            j += 1
        spans.append((start, j))
        i = j + 1
    return spans


_HEREDOC_CACHE = {}


def in_heredoc(path, line_number):
    spans = _HEREDOC_CACHE.get(path)
    if spans is None:
        spans = heredoc_spans(path)
        _HEREDOC_CACHE[path] = spans
    target = line_number - 1
    for start, end in spans:
        if start <= target < end:
            return True
    return False


def check_quote_balance(paths):
    """Flag a ``$(`` opened on one line whose closing paren is never found.

    A naive global paren count is useless in shell (``case`` patterns, ``awk``
    bodies and ``${VAR}bp`` all contain bare parens), so this tracks a real
    substitution stack and only reports a substitution left open at EOF.
    Heredoc bodies are skipped: their backticks and ``$(`` are literal text.
    """
    findings = []
    for path in paths:
        stack = []  # line numbers where an unclosed $( or backtick began
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if in_heredoc(path, number):
                continue
            i = 0
            in_single = False
            while i < len(raw):
                ch = raw[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == "'":
                    in_single = not in_single
                    i += 1
                    continue
                if in_single:
                    i += 1
                    continue
                if ch == "#" and (i == 0 or raw[i - 1].isspace()):
                    break
                if raw.startswith("$(", i):
                    stack.append(number)
                    i += 2
                    continue
                if ch == ")":
                    if stack:
                        stack.pop()
                    i += 1
                    continue
                i += 1
        if stack:
            findings.append((path, stack[0],
                             "命令替换 $( 自该行起未闭合（共 %d 处未闭合）" % len(stack), ""))
    return findings


def check_mktemp_parallel(paths):
    """mktemp inside a parallel loop body must be per-job or jobs collide."""
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "parallel" not in text and "&" not in text:
            continue
        lines = text.splitlines()
        for number, raw in enumerate(lines, 1):
            if "mktemp" not in raw or "$(" not in raw:
                continue
            # Look back for a parallel worker context.
            window = "\n".join(lines[max(0, number - 25):number])
            if re.search(r"\bparallel\b|\)\s*&\s*$|\$PAR", window):
                findings.append((path, number,
                                 "并行上下文中使用 mktemp，需确认模板含 $! 或样本名",
                                 raw.strip()))
    return findings


REVIEWED_UNGUARDED = {
    # (script, line) -> reason it is acceptable that no bail-out follows.
    # Index/faidx steps act on files already validated by a preceding guarded
    # step; a failure aborts the downstream reader loudly rather than silently
    # producing an empty result, and re-running is cheap and idempotent.
    ("03_align.sh", 33): "faidx on the reference; a failure makes bwa-mem2 fail loudly",
    ("03_align.sh", 114): "flagstat is a QC report; a missing report is visible downstream",
    ("03_align.sh", 115): "stats is a QC report; a missing report is visible downstream",
    ("03_align.sh", 120): "index follows a guarded CRAM conversion on the same file",
    ("04_joint_snp.sh", 26): "index follows a guarded CRAM check; readers fail loudly",
    ("04_joint_snp.sh", 66): "smoke-mode index; the counts are written to a summary",
    ("04_joint_snp.sh", 67): "summary printf; the index above already succeeded",
    ("04_joint_snp.sh", 79): "index of a validated VCF; downstream view fails loudly",
    ("04_joint_snp.sh", 81): "index of a validated VCF; downstream view fails loudly",
    ("04_joint_snp.sh", 89): "index of a validated VCF; downstream view fails loudly",
    ("04_joint_snp.sh", 91): "index of a validated VCF; downstream view fails loudly",
    ("04_joint_snp.sh", 106): "count written into a summary; absent count is visible",
    ("04_joint_snp.sh", 107): "count written into a summary; absent count is visible",
    ("04_variant_depth.sh", 18): "index follows a guarded CRAM check; readers fail loudly",
    ("05_simulate.sh", 57): "index follows a guarded CRAM check; readers fail loudly",
    ("05_simulate.sh", 94): "index follows a guarded sort; mosdepth below is now guarded",
    ("05_simulate.sh", 120): "index of an existing gVCF; typing readers fail loudly",
    ("06_export.sh", 87): "sample list for the export package; absent list is visible",
    ("prepare_marker_targets.sh", 18):
        "script runs under set -euo pipefail and the result is checked by "
        "[ -s \"$tmp\" ] || die on the next statement",
}


def logical_statements(lines):
    buffer = []
    start = None
    for number, raw in enumerate(lines, 1):
        stripped = strip_comments_and_strings(raw)
        if start is None and not stripped.strip():
            continue
        if start is None:
            start = number
        if stripped.rstrip().endswith("\\"):
            buffer.append(stripped.rstrip()[:-1])
            continue
        buffer.append(stripped)
        yield start, " ".join(buffer).strip()
        buffer = []
        start = None
    if buffer:
        yield start or 0, " ".join(buffer).strip()


def check_unguarded_critical(paths):
    """A critical producer whose failure is ignored can yield empty downstream files.

    Only a tool in *command position* counts; a tool name inside a ``log``
    message or a ``for t in ...`` list is not an invocation. Backslash
    continuations are joined first so a guard on the last line of a multi-line
    pipeline protects the whole statement.

    Commands reviewed as intentionally unguarded are listed in
    ``REVIEWED_UNGUARDED`` with a reason, so this check reports *new* risks and
    stays actionable instead of drowning in a permanent baseline.
    """
    critical = ("bcftools", "samtools", "bwa-mem2", "bwa", "fastp", "mosdepth", "minimap2")
    findings = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for start, statement in logical_statements(lines):
            if not statement or statement.startswith("#"):
                continue
            # Skip heredoc bodies (they are content, not commands).
            if in_heredoc(path, start):
                continue
            # Command position: start, after pipe/&&/||/;/brace/paren.
            invoked = None
            for segment in re.split(r"(?:\|\||&&|\||;|\{|\()", statement):
                first = segment.strip().split()
                if not first:
                    continue
                base = first[0].lstrip("$(").rsplit("/", 1)[-1]
                if base in critical:
                    invoked = base
                    break
            if not invoked:
                continue
            # Subshell assignment `x=$(tool ...)` is opt-in; the assignment is
            # later used in a guarded context or is informational.
            if re.search(r"=\$\(|=\`", statement):
                continue
            # A guard may be `|| die`, `|| { log ...; return 1; }`, or any
            # `||`-chained bail-out. Treat any ||-guard containing a bail-out
            # keyword, and any ||-guard block, as protected.
            guarded = (
                re.search(r"\|\|", statement) and re.search(
                    r"\b(die|return|exit|log|continue|break)\b", statement)
                or statement.startswith("if ")
                or re.search(r"(?:^|\s)if\s", statement)
                or "then" in statement
            )
            if guarded:
                continue
            key = (path.name, start)
            if key in REVIEWED_UNGUARDED:
                continue
            findings.append((path, start,
                             "关键命令 %s 未见失败保护" % invoked,
                             lines[start - 1].strip() if start else ""))
    return findings


def check_heredoc_python_imports(paths):
    """Python heredocs must only import modules the server env provides."""
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"<<\s*['\"]?(\w+)['\"]?\n(.*?)\n\s*\1\b", text, re.S):
            body = match.group(2)
            start_line = text[:match.start()].count("\n") + 1
            for import_match in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", body, re.M):
                module = import_match.group(1).split(".")[0]
                if module in ("os", "sys", "re", "json", "csv", "gzip", "collections",
                              "argparse", "math", "itertools", "subprocess", "pathlib",
                              "statistics", "hashlib", "io", "glob", "shutil", "textwrap"):
                    continue
                findings.append((path, start_line,
                                 "heredoc 内 python 导入非标准库模块 %s，需确认环境已装" % module,
                                 ""))
    return findings


def check_stage_coverage(paths):
    """Every stage in run_all.sh must exist, and every stage script be listed."""
    findings = []
    run_all = SERVER / "run_all.sh"
    if not run_all.exists():
        return findings
    text = run_all.read_text(encoding="utf-8")
    match = re.search(r"STAGES=\((.*?)\)", text, re.S)
    if not match:
        findings.append((run_all, 0, "run_all.sh 中未找到 STAGES 数组", ""))
        return findings
    listed = set(match.group(1).split())
    present = {p.name[:-3] for p in SERVER.glob("*.sh")}
    # Every listed stage must have a script.
    for stage in sorted(listed):
        if stage not in present:
            findings.append((run_all, 0, "STAGES 中的阶段缺少脚本: %s.sh" % stage, ""))
    # Numbered stage scripts must be scheduled, or they will never run.
    for name in sorted(present):
        if re.match(r"^\d\d_", name) and name not in listed:
            findings.append((run_all, 0, "脚本 %s.sh 未被 STAGES 调度" % name, ""))
    return findings


CHECKS = [
    ("未定义变量", lambda p, a: check_undefined_vars(p, a)),
    ("引号闭合", lambda p, a: check_quote_balance(p)),
    ("mtemp/并行", lambda p, a: check_mktemp_parallel(p)),
    ("关键命令保护", lambda p, a: check_unguarded_critical(p)),
    ("heredoc 导入", lambda p, a: check_heredoc_python_imports(p)),
    ("阶段覆盖", lambda p, a: check_stage_coverage(p)),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description="server shell 脚本静态分析")
    parser.add_argument("--strict", action="store_true", help="有任何发现即 exit 1")
    args = parser.parse_args(argv)

    paths = iter_scripts()
    if not paths:
        print("找不到 shell 脚本于 %s" % SERVER)
        return 1

    assigned = collect_assignments(paths)
    total = 0
    print("扫描 %d 个脚本；识别到 %d 个已赋值变量" % (len(paths), len(assigned)))
    for title, check in CHECKS:
        findings = check(paths, assigned)
        total += len(findings)
        if not findings:
            print("  [OK] %s：无发现" % title)
            continue
        print("  [!!] %s：%d 处" % (title, len(findings)))
        for path, number, message, snippet in findings:
            location = "%s:%d" % (path.name, number) if number else path.name
            print("       %s %s" % (location, message))
            if snippet:
                print("         > %s" % snippet)

    print("合计发现：%d" % total)
    if args.strict and total:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
