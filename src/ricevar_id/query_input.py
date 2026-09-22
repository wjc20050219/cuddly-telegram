"""Parse user-supplied genotype tables into a query :class:`GenotypeMatrix`.

Kept out of the Streamlit page so the parsing rules — which decide whether a
query is accepted at all — are unit-testable without a running app.

The accepted layout is the project's own matrix format: a ``sample_id`` column
followed by one column per ``CHROM:POS:REF:ALT`` marker. Missing calls must be
written as ``-1``/``NA``/``.``/empty and are stored as missing, never imputed.
"""

from __future__ import annotations

from typing import List, Optional

from .genotypes import MISSING, GenotypeMatrix, parse_marker_id

#: Text tokens accepted as "no call".
MISSING_TOKENS = frozenset(["", "na", "nan", ".", "-1", "none", "null"])


def parse_genotype_table(text: str, sample_id: Optional[str] = None) -> GenotypeMatrix:
    """Parse a tab-separated genotype table into a single-sample matrix.

    ``sample_id`` overrides the name found in the file. Raises ``ValueError``
    with an actionable message for every rejection reason, because a silently
    mis-parsed query would produce a plausible-but-wrong identification.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("文件为空")

    header = lines[0].rstrip("\r").split("\t")
    if header[0] != "sample_id":
        raise ValueError("第一列必须是 sample_id（本项目基因型矩阵格式）")

    markers = header[1:]
    if not markers:
        raise ValueError("表头里没有任何位点列")
    for marker in markers:
        if parse_marker_id(marker) is None:
            raise ValueError("位点列格式必须是 CHROM:POS:REF:ALT，例如 %r" % marker)
    duplicates = len(markers) != len(set(markers))
    if duplicates:
        raise ValueError("表头存在重复位点列")

    if len(lines) < 2:
        raise ValueError("文件里没有样本行")

    fields = lines[1].rstrip("\r").split("\t")
    if len(fields) != len(header):
        raise ValueError("样本行有 %d 列，表头有 %d 列" % (len(fields), len(header)))

    row: List[int] = []
    for position, token in enumerate(fields[1:], start=1):
        cleaned = token.strip()
        if cleaned.lower() in MISSING_TOKENS:
            row.append(MISSING)
            continue
        try:
            value = int(cleaned)
        except ValueError:
            raise ValueError("位点 %s 的取值 %r 不是整数（缺失请写 NA 或 -1）"
                             % (markers[position - 1], token))
        if value not in (0, 1, 2):
            raise ValueError("位点 %s 的取值 %d 不是 0/1/2（缺失请写 NA 或 -1）"
                             % (markers[position - 1], value))
        row.append(value)

    name = sample_id or fields[0] or "query"
    return GenotypeMatrix([name], markers, [row])
