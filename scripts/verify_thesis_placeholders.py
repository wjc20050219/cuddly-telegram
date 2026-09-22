#!/usr/bin/env python3
"""Guard the thesis skeleton against fabricated numbers.

A thesis skeleton that silently contains numbers looks finished while being
fiction. This script scans ``docs/thesis/`` for concrete *result-like*
percentages and rates and fails if any appear outside a placeholder.

Design constants are allowed and explicitly whitelisted below: candidate depth
gradients, marker-set sizes, panel sizes and the reference accession are
methodology, not measurements.

Usage::

    python scripts/verify_thesis_placeholders.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THESIS_DIR = ROOT / "docs" / "thesis"

#: Numbers that are design constants or otherwise legitimate to state outright.
ALLOWED_LITERALS = {
    "0.02", "0.05", "0.1", "0.2", "0.5", "0.10", "0.20", "0.50", "1.0", "1.00",
    "500", "1000", "2000", "30", "25", "50", "5", "1", "2", "3", "4", "6",
    "0/1/2", "0/0", "1.875", "001433935", "1",
}

#: A concrete accuracy/rate/percentage is a result claim, not a design choice.
SUSPICIOUS = re.compile(r"(\d+(?:\.\d+)?)\s*(%|×|倍)")

#: A line carrying a result claim must also carry a placeholder, unless the
#: number is a whitelisted design constant.
PLACEHOLDER = re.compile(r"\{\{\s*(RESULT|TODO|CITE|FILE)")

#: Curation and external facts are NOT experimental results, and stating them
#: concretely is correct: how many runs a query returned, how many varieties
#: were parsed, how large the manifests declare the download to be. Those come
#: from files already in the repository, not from an experiment that has not
#: run. They are allowed only when the same line cites the file they came from,
#: so every such number stays auditable. Measurement of *this project's* data
#: (recall, accuracy, depth achieved) is never allowed here.
CURATION_SOURCE = re.compile(r"`?(data/metadata/[\w./-]+\.(?:tsv|json)|docs/[\w./-]+\.md)`?")

#: Numbers measured in a laboratory/analysis sense -- always a result claim.
RESULT_METRICS = re.compile(
    r"(准确率|recall|召回|一致率|深度达到|实测深度|AUC|ROC|拒识率|误接受率|"
    r"Top-?1|Top-?5|比对率|Q30)")

#: Wording that signals a *design* gradient rather than a measurement. A bare
#: "0.5×" is ambiguous; "候选深度梯度"/"降采样至" is methodology.
DESIGN_CONTEXT = re.compile(r"(梯度|候选深度|降采样至|降至|预设|目标深度)")

#: Generated appendices (currently appendix A) list per-sample *declared*
#: metadata: accession numbers, platform, read length, estimated depth and
#: declared file sizes. None of it is measured by this project, and all of it is
#: reproducible byte-for-byte from the manifests by re-running the generator.
#: Such a file is allowed to carry those numbers ONLY when:
#:   1. it declares itself machine-generated (the banner names its generator), and
#:   2. it explicitly states its depths/sizes are declared rather than measured.
#: Markdown table rows from such a file are then skipped, but prose is still
#: checked -- so a fabricated result cannot hide in the narrative around a table.
#: A generator banner is ordinary Markdown prose, so the two facts this rule
#: needs -- "which script generated me" and "am I machine-generated" -- may be
#: separated by a line wrap. Match against the document header rather than one
#: physical line, or a correctly-bannered file would be rejected purely because
#: its sentence wrapped.
GENERATED_BANNER = re.compile(
    r"scripts/[\w_]+\.py[\s\S]{0,200}?自动生成")
DECLARED_DISCLAIMER = re.compile(r"(不是实测|非实测|声明值)")

#: How much of the document counts as its banner.
BANNER_CHARS = 900

#: A *meta-document* is one whose subject is this guard itself: it explains the
#: rules and therefore has to quote examples of the very numbers that are
#: forbidden elsewhere ("实测深度为 0.98×" is cited as a thing the guard must
#: reject). Quoting a forbidden example is not making the claim.
#:
#: This exemption is deliberately narrow and doubly gated:
#:   1. the file must declare itself a meta-document in its header, AND
#:   2. only lines *inside an explicitly delimited example block* are exempted.
#: Everything else in the file -- including all prose and every table outside
#: those blocks -- is checked exactly as before.
META_DECLARATION = re.compile(r"<!--\s*meta-document:\s*marker-guard\s*-->")
META_START = re.compile(r"<!--\s*guard-examples-start\s*-->")
META_END = re.compile(r"<!--\s*guard-examples-end\s*-->")

#: A Markdown table row: starts with a pipe. Data rows carry numbers, so they are
#: the lines this exemption targets.
TABLE_ROW = re.compile(r"^\s*\|")


def iter_paragraphs(text):
    """Yield (first_line_number, paragraph_text) for blank-line-separated blocks.

    Provenance is a property of the sentence, not of one physical line: in
    Markdown a citation often lands a line or two after the number it supports,
    purely because of wrapping. Checking per line would force authors to cram
    the path next to every figure, which invites the opposite failure -- paths
    sprinkled around to satisfy the linter rather than to be accurate.
    """
    lines = text.splitlines()
    start = None
    buffer = []
    for index, line in enumerate(lines, 1):
        if line.strip():
            if start is None:
                start = index
            buffer.append(line)
        else:
            if buffer:
                yield start, "\n".join(buffer)
            start, buffer = None, []
    if buffer:
        yield start, "\n".join(buffer)


def check_file(path):
    problems = []
    text = path.read_text(encoding="utf-8")

    # A generated appendix may carry declared metadata in its tables, but only
    # if it says so: it must name its generator AND disclaim that values are
    # declared rather than measured. Otherwise it is treated like any prose.
    generated = bool(GENERATED_BANNER.search(text[:BANNER_CHARS])
                     and DECLARED_DISCLAIMER.search(text[:BANNER_CHARS]))

    # A document about the guard's own rules may quote forbidden examples, but
    # ONLY inside a *properly closed* explicitly delimited block. An unclosed
    # start marker deliberately exempts nothing: otherwise a single forgotten
    # end marker would silently disable the guard for the rest of the file.
    meta_doc = bool(META_DECLARATION.search(text[:BANNER_CHARS]))
    exempt_lines = set()
    unmatched = 0
    if meta_doc:
        cursor = 0
        while True:
            start = META_START.search(text, cursor)
            if not start:
                break
            end = META_END.search(text, start.end())
            if not end:
                unmatched += 1
                break
            first = text.count("\n", 0, start.end()) + 1
            last = text.count("\n", 0, end.start()) + 1
            exempt_lines.update(range(first, last + 1))
            cursor = end.end()

    for start, para in iter_paragraphs(text):
        # A paragraph that cites a curation source may state curation numbers,
        # but never a metric of this project's own measurements.
        cites_source = bool(CURATION_SOURCE.search(para))
        for offset, line in enumerate(para.split("\n")):
            number = start + offset
            if PLACEHOLDER.search(line):
                continue
            # Inside a verified generated appendix, table rows are machine-derived.
            # Prose in the same file is still checked below.
            if generated and TABLE_ROW.match(line):
                if RESULT_METRICS.search(line):
                    problems.append((number, line.strip(), "结果指标出现在生成表格中"))
                continue
            # In a meta-document, an explicitly delimited example block is
            # discussing the rule rather than asserting a measurement.
            if meta_doc and number in exempt_lines:
                continue
            if cites_source:
                if RESULT_METRICS.search(line):
                    problems.append((number, line.strip(), "结果指标与数据来源同现"))
                continue
            for match in SUSPICIOUS.finditer(line):
                value = match.group(1)
                if value in ALLOWED_LITERALS:
                    continue
                # 允许形如 "0.02×–1×" 的深度梯度区间写法，但**仅限设计梯度**：
                # 实测深度（如 "实测深度为 0.98×"）是实验结果，必须走占位符。
                # 原来的写法只判断数值 ≤1.0，等于给任何小于 1 的倍数放行，
                # 实测深度会因此漏检。
                if float(value) <= 1.0 and match.group(2) in ("×", "倍") \
                        and DESIGN_CONTEXT.search(line) \
                        and not RESULT_METRICS.search(line):
                    continue
                problems.append((number, line.strip(), match.group(0)))
    return problems


def main():
    if not THESIS_DIR.exists():
        print("找不到 %s" % THESIS_DIR)
        return 1

    failures = []
    checked = 0
    for path in sorted(THESIS_DIR.glob("*.md")):
        if path.name == "PLACEHOLDER_CONVENTIONS.md":
            continue  # 约定文件本身就在描述这些规则
        checked += 1
        for number, line, token in check_file(path):
            failures.append("%s:%d 出现疑似结果数值 %r -> %s" % (path.name, number, token, line))

    for failure in failures:
        print("[FAIL] %s" % failure)
    print("检查 %d 个文件，%d 处疑似结果数值" % (checked, len(failures)))
    if not failures:
        print("未被占位符包裹的具体百分比/倍数：0（符合预期）")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
