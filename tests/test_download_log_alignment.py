# -*- coding: utf-8 -*-
"""`download_log.tsv` must be machine-readable: every row exactly 9 columns.

`server/02_download.sh` writes the TASK-018 download log. Its header declares
nine columns::

    sample_id run_accession file_name file_size md5 sha256 source_url
    download_time status

Every data row was misaligned against that header (defect found in round 18):

* three rows had a 9-slot format with only 7-8 arguments, so `date`/`status`
  were silently dropped or shifted;
* the `ok_no_md5` row put **`source_url` into the `md5` column**;
* the `failed` row put `source_url` into the `md5` column and `download_time`
  into `source_url`.

The consequence is not cosmetic: the summary at the end of the script indexes
the log by column name (``h["status"]``), so with `status` empty it printed
**nothing at all**, and `docs/thesis/APPENDIX_A_samples.md` plus
`THESIS_DRAFT.md` both promise byte counts "以 download_log.tsv 为准".
A corrupt log would therefore have silently been treated as the authority.

These tests parse the printf templates structurally rather than grepping for
literals, so the alignment rule stays checked even if the wording changes.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "server" / "02_download.sh"

HEADER = ["sample_id", "run_accession", "file_name", "file_size", "md5",
          "sha256", "source_url", "download_time", "status"]


STATUS_WORDS = ("skip_ok", "ok", "md5_mismatch", "ok_no_md5", "failed")


def _read():
    return SCRIPT.read_text(encoding="utf-8")


def _header_columns(src):
    m = re.search(r"DL_HEADER='([^']+)'", src)
    assert m, "DL_HEADER not found in 02_download.sh"
    return m.group(1).split("\\t")


def _split_args(argtext):
    """Split a shell argument region into tokens, honouring nesting.

    ``$(sha256sum x | awk '{print $1}')`` contains single quotes *inside* a
    double-quoted command substitution, which breaks naive regex scraping.
    This scanner tracks double-quote, single-quote and paren depth instead.
    """
    body = argtext.split(">>")[0]
    lines = [ln.strip().rstrip("\\").strip() for ln in body.split("\n")]
    body = " ".join(lines)

    toks, cur = [], ""
    i, dq, sq, depth = 0, False, False, 0
    while i < len(body):
        ch = body[i]
        if sq:
            cur += ch
            if ch == "'":
                sq = False
        elif dq:
            cur += ch
            if ch == "\\":
                if i + 1 < len(body):
                    cur += body[i + 1]
                    i += 1
            elif ch == "'":
                sq = True
            elif ch == "$" and i + 1 < len(body) and body[i + 1] == "(":
                cur += "("
                depth += 1
                i += 1
            elif ch == ")" and depth:
                depth -= 1
            elif ch == '"':
                dq = False
        else:
            if ch == '"':
                dq = True
                cur += ch
            elif ch == "$" and i + 1 < len(body) and body[i + 1] == "(":
                cur += "$("
                depth += 1
                i += 1
            elif ch == ")" and depth:
                depth -= 1
                cur += ch
            elif ch.isspace() and depth == 0 and not dq:
                if cur:
                    toks.append(cur)
                    cur = ""
            else:
                cur += ch
        i += 1
    if cur:
        toks.append(cur)
    return [t for t in toks if t and t != "\\"]


def _symbolise(tok):
    t = tok.strip().strip('"')
    if t.startswith("$("):
        return "<DATE>" if "date" in t else "<SHA256>"
    if t.startswith("$"):
        return "<%s>" % t.lstrip("$").upper()
    return t


def _printf_blocks(src):
    """Yield (line_number, template, [symbolic argument values])."""
    lines = src.split("\n")
    for i, ln in enumerate(lines):
        if "printf '%s" not in ln or "DLLOG" in ln:
            continue
        blob, j = [], i
        while j < len(lines) and j < i + 8:
            blob.append(lines[j])
            if ">>" in lines[j]:
                break
            j += 1
        text = " ".join(x.strip() for x in blob)
        tmpl = re.search(r"printf '([^']+)'", text).group(1)
        argpart = text.split("' \\", 1)[-1] if "' \\" in text else ""
        yield i + 1, tmpl, [_symbolise(t) for t in _split_args(argpart)]


def _render(tmpl, args):
    """Model bash printf: consume args in order, missing ones become empty."""
    out, ai, k = [], 0, 0
    while k < len(tmpl):
        if tmpl.startswith("%s", k):
            out.append(args[ai] if ai < len(args) else "")
            ai += 1
            k += 2
        else:
            out.append(tmpl[k])
            k += 1
    text = "".join(out).replace("\\t", "\t").replace("\\n", "")
    cells = text.split("\t")
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


class DownloadLogHeaderTests(unittest.TestCase):
    def test_header_is_the_documented_nine_columns(self):
        self.assertEqual(_header_columns(_read()), HEADER)

    def test_header_check_exists_so_old_logs_are_rejected(self):
        src = _read()
        self.assertIn('head -n1 "$DLLOG"', src)
        self.assertIn("die ", src)


class DownloadLogRowAlignmentTests(unittest.TestCase):
    def test_every_row_writes_exactly_the_header_column_count(self):
        blocks = list(_printf_blocks(_read()))
        self.assertGreaterEqual(len(blocks), 5,
                                "the five log rows should still exist")
        for line, tmpl, args in blocks:
            with self.subTest(line=line):
                cells = _render(tmpl, args)
                self.assertEqual(
                    len(cells), len(HEADER),
                    "line %d writes %d columns, header declares %d"
                    % (line, len(cells), len(HEADER)))

    def test_status_column_is_always_a_known_status_word(self):
        """The summary groups by status, so status must be both non-empty and
        one of the words the script actually uses.

        Checking only "non-empty" was a real hole: reverting the original
        misalignment left a plausible word in the last column (``ok`` for the
        ``failed`` row), so the guard passed on broken code.
        """
        for line, tmpl, args in _printf_blocks(_read()):
            with self.subTest(line=line):
                cells = _render(tmpl, args)
                status = cells[-1] if cells else ""
                self.assertTrue(status, "line %d has an empty status" % line)
                self.assertIn(
                    status, STATUS_WORDS,
                    "line %d has status %r, not one of %s"
                    % (line, status, list(STATUS_WORDS)))

    def test_each_status_word_is_used_exactly_once(self):
        """Five code paths -> five distinct statuses, no duplicates."""
        seen = []
        for _, tmpl, args in _printf_blocks(_read()):
            cells = _render(tmpl, args)
            if cells:
                seen.append(cells[-1])
        self.assertEqual(sorted(seen), sorted(STATUS_WORDS))
        self.assertEqual(len(seen), len(set(seen)),
                         "a status word is used by two rows")

    def test_columns_are_in_the_declared_order(self):
        """Every row must place its values in the header's positions.

        This is the check that catches `source_url` landing in the `md5`
        column: a row can have the right *number* of columns and still be
        wrong.
        """
        for line, tmpl, args in _printf_blocks(_read()):
            with self.subTest(line=line):
                cells = _render(tmpl, args)
                if len(cells) != len(HEADER):
                    continue
                got = dict(zip(HEADER, cells))
                self.assertEqual(got["sample_id"], "<SID>")
                self.assertEqual(got["run_accession"], "<RUN>")
                self.assertEqual(got["file_name"], "<FN>")
                self.assertEqual(got["file_size"], "<BYTES>")
                self.assertEqual(got["source_url"], "<URL>")
                # md5 / sha256 / download_time are genuinely optional
                self.assertIn(got["md5"], ("", "<MD5>"))
                self.assertIn(got["sha256"], ("", "<SHA256>"))

    def test_source_url_is_never_written_into_the_md5_column(self):
        """Regression for the `ok_no_md5`/`failed` rows."""
        for line, tmpl, args in _printf_blocks(_read()):
            with self.subTest(line=line):
                cells = _render(tmpl, args)
                if len(cells) < len(HEADER):
                    continue
                md5_cell = cells[HEADER.index("md5")]
                self.assertNotIn("http", md5_cell.lower(),
                                 "line %d wrote a URL into the md5 column" % line)
                self.assertNotIn("ftp", md5_cell.lower(),
                                 "line %d wrote a URL into the md5 column" % line)
                self.assertNotEqual(md5_cell, "<URL>")

    def test_download_time_holds_a_timestamp_or_is_empty(self):
        for line, tmpl, args in _printf_blocks(_read()):
            with self.subTest(line=line):
                cells = _render(tmpl, args)
                if len(cells) < len(HEADER):
                    continue
                cell = cells[HEADER.index("download_time")]
                if cell:
                    self.assertEqual(
                        cell, "<DATE>",
                        "download_time should come from $(date ...), got %r"
                        % cell)

    def test_the_five_distinct_status_words_are_all_present(self):
        """Each code path must be distinguishable in the log."""
        found = set()
        for _, tmpl, args in _printf_blocks(_read()):
            cells = _render(tmpl, args)
            if cells:
                found.add(cells[-1])
        for expected in STATUS_WORDS:
            with self.subTest(status=expected):
                self.assertIn(expected, found)


class SummaryConsumerTests(unittest.TestCase):
    def test_summary_indexes_the_log_by_column_name(self):
        """If status is renamed, this consumer breaks silently."""
        src = _read()
        m = re.search(r'awk -F\'\\t\' \'NR==1\{[^}]*\}.*', src)
        self.assertIsNotNone(m, "the summary awk line was not found")
        self.assertIn('h["status"]', m.group(0))

    def test_status_appears_in_the_header_the_summary_reads(self):
        self.assertIn("status", _header_columns(_read()))


if __name__ == "__main__":
    unittest.main()
