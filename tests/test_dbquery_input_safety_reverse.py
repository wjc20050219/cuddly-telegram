"""Reverse test: revert each fix and confirm the new tests actually catch it.

A regression test that passes against both the fixed and the buggy code proves
nothing. This reverts each fix inside a copy of the real module and asserts the
specific defect reappears.
"""
from __future__ import annotations

import re
import shutil
import sys
import types
import unittest
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

SOURCE = ROOT / "src" / "ricevar_id" / "dbquery.py"
TMP = ROOT / ".tmp"
TEXT = SOURCE.read_text(encoding="utf-8")

# The exact pre-fix fuzzy search: user text interpolated into the LIKE pattern.
FIXED_LIKE = '''        pattern = "%" + _escape_like(name) + "%"
        return self.conn.execute(
            "SELECT variety_name, subspecies, sample_id, run_accession FROM sample "
            "WHERE variety_name LIKE ? ESCAPE '\\\\' ORDER BY variety_name, sample_id",
            (pattern,),
        ).fetchall()'''

BUGGY_LIKE = '''        return self.conn.execute(
            "SELECT variety_name, subspecies, sample_id, run_accession FROM sample "
            "WHERE variety_name LIKE ? ORDER BY variety_name, sample_id",
            ("%" + name + "%",),
        ).fetchall()'''

BUGGY_TAIL = "        return result"


def load_module_with(text, tick):
    """Import a patched copy of dbquery under a unique name.

    The module uses relative imports (``from .fingerprint import ...``), so the
    copy must be registered under the ``ricevar_id`` package rather than loaded
    as a standalone file. The copy is registered in ``sys.modules`` and the
    on-disk file is removed when the test suite exits.
    """
    import atexit
    import importlib.util

    TMP.mkdir(exist_ok=True)
    path = TMP / ("dbquery_mut_%d.py" % tick)
    path.write_text(text, encoding="utf-8")
    name = "ricevar_id.dbquery_mut_%d" % tick
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    # Make the relative imports resolve against the real package.
    module.__package__ = "ricevar_id"
    sys.modules[name] = module
    spec.loader.exec_module(module)

    def _cleanup():
        sys.modules.pop(name, None)
        path.unlink()
        cache = path.parent / "__pycache__" / (path.stem + ".cpython-37.pyc")
        if cache.exists():
            cache.unlink()

    atexit.register(_cleanup)
    return module


def build_db():
    from ricevar_id import database as db
    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA)
    for sid, var in [("S1", "Nipponbare"), ("S2", "Zh11"), ("S3", None), ("S4", "Nip_pon_bare")]:
        conn.execute("INSERT INTO sample (sample_id, variety_name, subspecies, run_accession,"
                     " panel_role) VALUES (?,?,?,?,?)", (sid, var, "japonica", "ERR" + sid, "pilot"))
    for m in ["m0", "m1", "m2", "m3"]:
        conn.execute("INSERT INTO marker (marker_id, chrom, pos, ref, alt, marker_set)"
                     " VALUES (?,?,?,?,?,?)", (m, "chr1", 1, "A", "G", "500"))
    for sid, vals in {"S1": [0, 0, 1, 2], "S2": [2, 2, 1, 0],
                      "S3": [0, 1, 2, 1], "S4": [0, 0, 1, 1]}.items():
        for m, v in zip(["m0", "m1", "m2", "m3"], vals):
            conn.execute("INSERT OR REPLACE INTO genotype (sample_id, marker_id, dosage)"
                         " VALUES (?,?,?)", (sid, m, v))
    conn.commit()
    return conn


class LikeFixIsLoadBearingTests(unittest.TestCase):
    def test_baseline_source_contains_the_fixed_form(self):
        """先证明补丁锚点真的存在，否则下面的突变是空的。"""
        self.assertIn(FIXED_LIKE, TEXT,
                      "修复后的 LIKE 代码块未找到；若实现已改写，请同步更新本反向测试")

    def test_reverted_module_leaks_wildcards(self):
        mutated = TEXT.replace(FIXED_LIKE, BUGGY_LIKE)
        self.assertNotEqual(mutated, TEXT, "突变未生效：替换目标是空的")
        module = load_module_with(mutated, 1)
        conn = build_db()
        api = module.FingerprintDatabase(conn)
        # 缺陷必须重现：'%' 和 '_' 变成通配符。
        self.assertEqual(sorted(r[0] for r in api.find_variety("%", exact=False)),
                         ["Nip_pon_bare", "Nipponbare", "Zh11"])
        self.assertEqual(sorted(r[0] for r in api.find_variety("_", exact=False)),
                         ["Nip_pon_bare", "Nipponbare", "Zh11"])
        # 而修复版不会。
        from ricevar_id.dbquery import FingerprintDatabase as Fixed
        fixed = Fixed(conn)
        self.assertEqual([r[0] for r in fixed.find_variety("%", exact=False)], [])
        self.assertEqual([r[0] for r in fixed.find_variety("_", exact=False)], ["Nip_pon_bare"])
        conn.close()

    def test_fixed_and_buggy_are_distinguishable(self):
        """两个版本必须在某个输入上给出不同结果，否则测试无鉴别力。"""
        module = load_module_with(TEXT.replace(FIXED_LIKE, BUGGY_LIKE), 2)
        from ricevar_id.dbquery import FingerprintDatabase as Fixed
        conn = build_db()
        buggy = module.FingerprintDatabase(conn)
        fixed = Fixed(conn)
        differing = [p for p in ["%", "_", "N_p_pon_bare", "Nip_pon"]
                     if sorted(r[0] for r in buggy.find_variety(p, exact=False))
                     != sorted(r[0] for r in fixed.find_variety(p, exact=False))]
        self.assertEqual(differing, ["%", "_", "N_p_pon_bare"],
                         "突变版与修复版差异不符预期")
        conn.close()


class UnlabelledFixIsLoadBearingTests(unittest.TestCase):
    def test_baseline_source_contains_the_flag(self):
        self.assertIn("best_match_lacks_variety", TEXT)
        self.assertIn("n_unlabelled_reference_samples", TEXT)

    def test_without_the_flag_callers_cannot_detect_an_unlabelled_winner(self):
        """移除两个标记后，identify() 的结果里没有任何线索说明最佳匹配没有品种名。"""
        mutated = TEXT.replace(
            "        result[\"n_unlabelled_reference_samples\"] = len(self.unlabelled_samples())",
            "        pass  # mutation: flag removed")
        mutated = mutated.replace(
            "        result[\"best_match_lacks_variety\"] = bool(\n"
            "            best and not (best.get(\"variety_name\") or \"\").strip())",
            "        pass  # mutation: flag removed")
        self.assertNotEqual(mutated, TEXT, "突变未生效")
        module = load_module_with(mutated, 3)
        from ricevar_id.genotypes import GenotypeMatrix
        conn = build_db()
        api = module.FingerprintDatabase(conn)
        result = api.identify(GenotypeMatrix(["Q"], ["m0", "m1", "m2", "m3"], [[0, 1, 2, 1]]),
                              method="ibs", top_k=5, min_compared=1)
        # 最佳匹配仍是无名样本——缺陷重现。
        self.assertEqual(result["best_match"]["reference_id"], "S3")
        self.assertIsNone(result["best_match"]["variety_name"])
        # 突变版没有任何字段可供页面提示用户。
        self.assertNotIn("best_match_lacks_variety", result)
        self.assertNotIn("n_unlabelled_reference_samples", result)
        conn.close()

    def test_fixed_version_exposes_both_flags(self):
        from ricevar_id.dbquery import FingerprintDatabase
        from ricevar_id.genotypes import GenotypeMatrix
        conn = build_db()
        api = FingerprintDatabase(conn)
        result = api.identify(GenotypeMatrix(["Q"], ["m0", "m1", "m2", "m3"], [[0, 1, 2, 1]]),
                              method="ibs", top_k=5, min_compared=1)
        self.assertTrue(result["best_match_lacks_variety"])
        self.assertEqual(result["n_unlabelled_reference_samples"], 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
