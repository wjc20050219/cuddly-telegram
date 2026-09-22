#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record the provenance and completeness status of the ENA search artifacts.

Why this exists
---------------
Two different kinds of number live side by side in ``data/metadata/search/``:

* **Counts** measured by a ``limit=0`` query (the server does the counting, so
  they are exact) -- e.g. the 96,623 in ``ena_search_summary.tsv``.
* **Downloaded listings**, produced with an explicit ``limit=`` (a page cap).

Those are not the same thing, and a listing that hit its cap is *truncated*:
``ena_rice_wgs_deep_runs.tsv`` has exactly 10,000 data rows, which is the
``limit=10000`` passed by ``search_round2.sh``, not a natural total. Likewise
``ena_rice_wgs_runs.tsv`` has exactly 5,000 (``limit=5000``).

This script does not "fix" the listings -- it cannot, without network access.
It writes a machine-readable provenance file that states, per artifact, which
rows exist, whether the row count equals a round page cap (and is therefore
suspected truncated), and which claims in the repository rest on it.

The point is that a truncated listing must never be mistaken for a complete
one, and a console-printed count must never be cited as if it were archived.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data" / "metadata" / "search"

#: Page caps known to be used by the fetch scripts, with the reason.
KNOWN_CAPS = {
    5000: "scripts/search_ena.sh 使用 limit=5000",
    10000: "scripts/search_round2.sh 使用 limit=10000",
}

#: Artifacts, and what they are.
ARTIFACTS = [
    ("ena_search_summary.tsv",
     "counts",
     "各 query 的命中数（由 limit=0 计数查询产生，服务端计数，精确）"),
    ("ena_rice_wgs_runs.tsv",
     "listing",
     ">=1x WGS run 级清单（按 limit=5000 拉取，行数等于页上限即视为截断）"),
    ("ena_rice_wgs_deep_runs.tsv",
     "listing",
     ">=5x GENOMIC WGS run 级清单（按 limit=10000 拉取，行数等于页上限即视为截断）"),
]

#: Claims elsewhere in the repo that depend on these artifacts. Each is a
#: (path, regex) pair; the script reports whether the claim is still present.
DEPENDENT_CLAIMS = [
    ("data/metadata/search/README.md", r"24,633"),
    ("data/metadata/search/README.md", r"32,478"),
    ("data/metadata/search/README.md", r"10,707"),
    ("docs/server_admin_questions.md", r"24,633"),
    ("scripts/task011_fetch_ena.py", r"24,633"),
]


def count_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def classify(rows: int) -> str:
    """A row count exactly equal to a known page cap is suspicious, not final."""
    return "suspected_truncated" if rows in KNOWN_CAPS else "complete_or_unknown"


def build() -> dict:
    artifacts = []
    for name, kind, description in ARTIFACTS:
        path = SEARCH / name
        if not path.exists():
            artifacts.append({"name": name, "kind": kind, "present": False,
                              "description": description})
            continue
        rows = count_data_rows(path)
        record = {
            "name": name,
            "kind": kind,
            "present": True,
            "description": description,
            "data_rows": rows,
            "bytes": path.stat().st_size,
            "page_cap": rows if rows in KNOWN_CAPS else None,
            "cap_reason": KNOWN_CAPS.get(rows),
            "status": classify(rows) if kind == "listing" else "exact_count",
        }
        artifacts.append(record)

    claims = []
    for rel, pattern in DEPENDENT_CLAIMS:
        path = ROOT / rel
        found = False
        if path.exists():
            found = bool(re.search(pattern, path.read_text(encoding="utf-8")))
        claims.append({"file": rel, "pattern": pattern, "still_present": found})

    return {
        "generated_by": "scripts/record_search_provenance.py",
        "note": (
            "本文件记录检索产物的来源与完整性状态。"
            "行数恰好等于脚本所用 limit= 的清单视为**截断**，"
            "不得当作全量统计使用。"
        ),
        "artifacts": artifacts,
        "dependent_claims": claims,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=SEARCH / "search_provenance.json")
    parser.add_argument("--check", action="store_true",
                        help="只校验，不写文件")
    args = parser.parse_args()

    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if not args.out.exists():
            print("[FAIL] 缺少 %s" % args.out)
            return 1
        if args.out.read_text(encoding="utf-8") != text:
            print("[FAIL] %s 与当前仓库状态不一致，请重新生成" % args.out)
            return 1
        print("[OK] 检索产物来源记录与仓库一致")
        return 0

    with args.out.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    for item in data["artifacts"]:
        if not item.get("present"):
            print("  缺失: %s" % item["name"])
        elif item["kind"] == "listing":
            print("  %-30s %6d 行  %s"
                  % (item["name"], item["data_rows"], item["status"]))
        else:
            print("  %-30s 计数文件" % item["name"])
    print("已写出: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
