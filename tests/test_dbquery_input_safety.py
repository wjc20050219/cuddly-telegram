"""Regression tests for two defects found by auditing the prototype's call sites.

Both were reachable from real data and invisible without a browser:

1. ``find_variety(exact=False)`` passed user text straight into a SQL ``LIKE``
   pattern, so ``%`` and ``_`` acted as wildcards. Typing ``_`` listed the whole
   database; typing ``Nip_pon`` matched ``Nipponbare``.
2. A reference sample whose ``variety_name`` is empty still carries genotypes
   and takes part in identification, but it appears in no variety listing. It
   could therefore be returned as the top answer while being invisible to the
   user and unattributable to any variety.

The empty-variety value is not hypothetical: ``database.load_manifest`` maps an
empty TSV cell to ``None``, and ``variety_name`` is only a required *column*.
"""
from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id import database as db  # noqa: E402
from ricevar_id.dbquery import FingerprintDatabase, _escape_like  # noqa: E402
from ricevar_id.genotypes import GenotypeMatrix  # noqa: E402

MARKERS = ["m0", "m1", "m2", "m3"]
# S3 deliberately has no variety name but real genotypes.
SAMPLES = [("S1", "Nipponbare"), ("S2", "Zh11"), ("S3", None), ("S4", "Nip_pon_bare")]
GENOTYPES = {
    "S1": [0, 0, 1, 2],
    "S2": [2, 2, 1, 0],
    "S3": [0, 1, 2, 1],
    "S4": [0, 0, 1, 1],
}


def build_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA)
    for sample_id, variety in SAMPLES:
        conn.execute(
            "INSERT INTO sample (sample_id, variety_name, subspecies, run_accession, panel_role)"
            " VALUES (?,?,?,?,?)", (sample_id, variety, "japonica", "ERR" + sample_id, "pilot"))
    for marker in MARKERS:
        conn.execute("INSERT INTO marker (marker_id, chrom, pos, ref, alt, marker_set)"
                     " VALUES (?,?,?,?,?,?)", (marker, "chr1", 1, "A", "G", "500"))
    for sample_id, values in GENOTYPES.items():
        for marker, value in zip(MARKERS, values):
            conn.execute("INSERT OR REPLACE INTO genotype (sample_id, marker_id, dosage)"
                         " VALUES (?,?,?)", (sample_id, marker, value))
    conn.commit()
    return conn


class LikeEscapingTests(unittest.TestCase):
    """查询框里的 % 和 _ 是字面字符，不是 SQL 通配符。"""

    def setUp(self):
        self.conn = build_db()
        self.api = FingerprintDatabase(self.conn)

    def tearDown(self):
        self.conn.close()

    def names(self, keyword):
        return sorted(row[0] for row in self.api.find_variety(keyword, exact=False))

    def test_percent_does_not_match_everything(self):
        # 修复前：'%' 返回全部 3 个品种。
        self.assertEqual(self.names("%"), [])

    def test_underscore_is_matched_literally(self):
        # 'Nip_pon' 只应命中真的含下划线的名字，不应命中 Nipponbare。
        self.assertEqual(self.names("Nip_pon"), ["Nip_pon_bare"])

    def test_underscore_matches_only_where_a_real_underscore_exists(self):
        # 'Nip_pon_bare' 含下划线，所以搜 '_' 命中它是**正确**的（字面语义）；
        # 修复前它同时命中 Nipponbare/Zh11，那才是通配符泄漏。
        self.assertEqual(self.names("_"), ["Nip_pon_bare"])

    def test_escaped_query_matches_python_literal_containment(self):
        """转义后 SQL 语义必须与"字面子串包含"完全一致。

        注意大小写：SQLite 的 ``LIKE`` 对 ASCII 默认不区分大小写，而 Python
        的 ``in`` 区分。这是**有意的**差异（用户输品种名不该计较大小写），
        所以比较时两边都折叠为小写，以单独检验通配符是否泄漏。
        """
        names = ["Nip_pon_bare", "Nipponbare", "Zh11"]
        for probe in ["%", "_", "Nip_pon", "N_p_pon_bare", "Nip%bare",
                      "Nip", "nip", "___", "Nipponbare"]:
            with self.subTest(probe=probe):
                self.assertEqual(self.names(probe),
                                 sorted(n for n in names if probe.lower() in n.lower()))

    def test_search_is_case_insensitive(self):
        self.assertEqual(self.names("nip"), self.names("NIP"))

    def test_percent_in_the_middle_is_literal(self):
        self.assertEqual(self.names("Nip%bare"), [])

    def test_plain_substring_still_works(self):
        self.assertEqual(self.names("Nip"), ["Nip_pon_bare", "Nipponbare"])
        self.assertEqual(self.names("nip"), ["Nip_pon_bare", "Nipponbare"])

    def test_exact_search_is_unaffected_by_metacharacters(self):
        self.assertEqual(self.api.find_variety("%", exact=True), [])
        self.assertEqual(len(self.api.find_variety("Nipponbare", exact=True)), 1)

    def test_escape_helper_escapes_backslash_first(self):
        # 反斜杠必须最先转义，否则后续插入的转义符会被再次加倍。
        self.assertEqual(_escape_like("a\\b"), "a\\\\b")
        self.assertEqual(_escape_like("100%"), "100\\%")
        self.assertEqual(_escape_like("a_b"), "a\\_b")


class UnlabelledSampleTests(unittest.TestCase):
    """没有品种名的参考样本必须可见，且不能被当成识别结论。"""

    def setUp(self):
        self.conn = build_db()
        self.api = FingerprintDatabase(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_unlabelled_sample_is_listed_and_not_in_variety_table(self):
        self.assertEqual(self.api.unlabelled_samples(), ["S3"])
        self.assertNotIn("S3", [row[0] for row in self.api.list_varieties()])
        self.assertEqual(
            sorted(row[0] for row in self.api.list_varieties()),
            ["Nip_pon_bare", "Nipponbare", "Zh11"])

    def test_unlabelled_sample_still_scores_genotypes(self):
        # 这是问题的根源：它确实参与比对，所以确实可能拿第一。
        reference = self.api.reference_matrix()
        self.assertIn("S3", reference.samples)
        self.assertEqual(self.api.counts()["called_genotypes"], 16)

    def test_identify_flags_an_unlabelled_best_match(self):
        query = GenotypeMatrix(["Q"], MARKERS, [GENOTYPES["S3"]])
        result = self.api.identify(query, method="ibs", top_k=5, min_compared=1)
        self.assertEqual(result["best_match"]["reference_id"], "S3")
        self.assertIsNone(result["best_match"]["variety_name"])
        # 关键：页面必须能看出"这个最佳匹配没有品种名"。
        self.assertTrue(result["best_match_lacks_variety"])
        self.assertEqual(result["n_unlabelled_reference_samples"], 1)

    def test_a_named_match_is_not_flagged(self):
        query = GenotypeMatrix(["Q"], MARKERS, [GENOTYPES["S2"]])
        result = self.api.identify(query, method="ibs", top_k=5, min_compared=1)
        self.assertEqual(result["best_match"]["reference_id"], "S2")
        self.assertEqual(result["best_match"]["variety_name"], "Zh11")
        self.assertFalse(result["best_match_lacks_variety"])

    def test_blank_string_variety_counts_as_unlabelled(self):
        """空字符串和 NULL 都不能算作品种名。"""
        self.conn.execute(
            "INSERT INTO sample (sample_id, variety_name, panel_role) VALUES (?,?,?)",
            ("S5", "   ", "pilot"))
        self.conn.commit()
        self.assertEqual(self.api.unlabelled_samples(), ["S3", "S5"])
        self.assertNotIn("S5", [row[0] for row in self.api.list_varieties()])

    def test_no_unlabelled_samples_reports_zero(self):
        self.conn.execute("UPDATE sample SET variety_name = 'X' WHERE sample_id = 'S3'")
        self.conn.commit()
        self.assertEqual(self.api.unlabelled_samples(), [])
        query = GenotypeMatrix(["Q"], MARKERS, [GENOTYPES["S1"]])
        result = self.api.identify(query, method="ibs", top_k=5, min_compared=1)
        self.assertEqual(result["n_unlabelled_reference_samples"], 0)
        self.assertFalse(result["best_match_lacks_variety"])


class ManifestProducesEmptyVarietyTests(unittest.TestCase):
    """证明空品种名不是臆想：manifest 里的空单元格确实会变成 NULL。"""

    def test_empty_variety_cell_becomes_null_in_the_database(self):
        tmp = ROOT / ".tmp"
        tmp.mkdir(exist_ok=True)
        manifest = tmp / "empty_variety_manifest.tsv"
        try:
            manifest.write_text(
                "sample_id\tvariety_name\trun_accession\n"
                "S1\tNipponbare\tERR1\n"
                "S2\t\tERR2\n",
                encoding="utf-8")

            conn = sqlite3.connect(":memory:")
            conn.executescript(db.SCHEMA)
            count = db.load_manifest(conn, str(manifest))
            self.assertEqual(count, 2)
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM sample WHERE variety_name IS NULL").fetchone()[0], 1)
            self.assertEqual(FingerprintDatabase(conn).unlabelled_samples(), ["S2"])
            conn.close()
        finally:
            manifest.unlink()


if __name__ == "__main__":
    unittest.main()
