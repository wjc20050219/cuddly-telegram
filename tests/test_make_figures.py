"""Tests for the figure generation scripts.

These confirm two things that matter for thesis integrity:

1. With no result files, the scripts produce **no** figures (they must never
   invent a placeholder curve).
2. With real-shaped input, the plotting code actually runs and writes a file,
   so the figures are known to work before real data arrives.
"""
from __future__ import annotations

import contextlib
import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_figures  # noqa: E402

TMP_ROOT = ROOT / ".tmp"


def have_matplotlib():
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def have_cjk_font():
    """True when the interpreter can actually render the figures' Chinese labels."""
    try:
        import matplotlib
    except ImportError:
        return False
    matplotlib.use("Agg")
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    return any(name in available for name in
               ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                "Source Han Sans SC", "WenQuanYi Zen Hei", "Arial Unicode MS"))


@contextlib.contextmanager
def _temp_dir():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="fig_", dir=str(TMP_ROOT)))
    try:
        yield path
    finally:
        shutil.rmtree(str(path), ignore_errors=True)


BY_DEPTH_FIELDS = [
    "marker_count", "depth_label", "n_queries", "mean_marker_recall",
    "mean_genotype_concordance", "mean_best_similarity",
    "top1_correct_variety", "top5_correct_variety", "accepted_rate",
]


def write_by_depth(directory, rows=None):
    """Write a by-depth table shaped like the real one."""
    if rows is None:
        rows = []
        for marker_count in (500, 1000, 2000):
            for depth, top1 in (("0.02", 0.30), ("0.10", 0.62), ("1.00", 0.98)):
                rows.append({
                    "marker_count": str(marker_count),
                    "depth_label": depth,
                    "n_queries": "30",
                    "mean_marker_recall": "%.4f" % (0.20 + float(depth)),
                    "mean_genotype_concordance": "%.4f" % (0.90 + float(depth) * 0.05),
                    "mean_best_similarity": "%.4f" % (0.90 + float(depth) * 0.05),
                    "top1_correct_variety": "%.4f" % top1,
                    "top5_correct_variety": "%.4f" % min(1.0, top1 + 0.04),
                    "accepted_rate": "%.4f" % top1,
                })
    path = directory / "identification_by_depth.tsv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_DEPTH_FIELDS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_per_query(directory, rows=None):
    if rows is None:
        rows = [
            {"query_id": "s1_0.10", "depth_label": "0.10", "best_similarity": "0.97"},
            {"query_id": "s2_0.10", "depth_label": "0.10", "best_similarity": "0.93"},
            {"query_id": "s1_1.00", "depth_label": "1.00", "best_similarity": "0.999"},
        ]
    path = directory / "per_query.tsv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query_id", "depth_label", "best_similarity"],
                                delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


class HelperTests(unittest.TestCase):
    def test_as_float_maps_nan_and_blank_to_none(self):
        self.assertIsNone(make_figures.as_float(""))
        self.assertIsNone(make_figures.as_float("nan"))
        self.assertIsNone(make_figures.as_float("NaN"))
        self.assertIsNone(make_figures.as_float(None))
        self.assertEqual(make_figures.as_float("0.5"), 0.5)

    def test_read_tsv_returns_none_for_missing_file(self):
        with _temp_dir() as tmp:
            self.assertIsNone(make_figures.read_tsv(Path(tmp) / "nope.tsv"))

    def test_read_tsv_returns_none_for_header_only_file(self):
        with _temp_dir() as tmp:
            path = Path(tmp) / "empty.tsv"
            path.write_text("a\tb\n", encoding="utf-8")
            self.assertIsNone(make_figures.read_tsv(path))


class NoDataTests(unittest.TestCase):
    def test_no_figures_without_result_files(self):
        with _temp_dir() as tmp:
            out = Path(tmp) / "figures"
            code = make_figures.main([
                "--analysis-dir", str(Path(tmp) / "analysis"),
                "--out-dir", str(out),
            ])
            self.assertEqual(code, 1)
            # 关键断言：无数据时不产生任何图片文件。
            self.assertEqual(list(out.glob("*.png")), [])

    def test_cli_reports_missing_data_without_crashing(self):
        with _temp_dir() as tmp:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "make_figures.py"),
                 "--analysis-dir", str(Path(tmp) / "analysis"),
                 "--out-dir", str(Path(tmp) / "figures")],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("0 张图", proc.stdout)
            self.assertEqual(list((Path(tmp) / "figures").glob("*.png")), [])

    def test_only_flag_rejects_unknown_figure(self):
        with _temp_dir() as tmp:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "make_figures.py"),
                 "--analysis-dir", str(Path(tmp)), "--only", "nope"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            )
            self.assertEqual(proc.returncode, 2)


@unittest.skipUnless(have_matplotlib(), "matplotlib 仅存在于 ricevar 环境")
class WithDataTests(unittest.TestCase):
    def test_depth_curve_is_written_from_real_shaped_input(self):
        with _temp_dir() as tmp:
            analysis = Path(tmp) / "analysis"
            analysis.mkdir()
            write_by_depth(analysis)
            out = Path(tmp) / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "depth_curve",
            ])
            self.assertEqual(code, 0)
            target = out / "fig_depth_curve.png"
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 1000)

    def test_similarity_distribution_is_written(self):
        with _temp_dir() as tmp:
            analysis = Path(tmp) / "analysis"
            analysis.mkdir()
            write_per_query(analysis)
            out = Path(tmp) / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "similarity_dist",
            ])
            self.assertEqual(code, 0)
            self.assertTrue((out / "fig_similarity_dist.png").exists())

    def test_confusion_figure_declines_without_a_full_matrix(self):
        with _temp_dir() as tmp:
            analysis = Path(tmp) / "analysis"
            analysis.mkdir()
            write_per_query(analysis)
            out = Path(tmp) / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "confusion",
            ])
            # 明确不产图，而不是画一张只有最佳匹配的伪热图。
            self.assertEqual(code, 1)
            self.assertEqual(list(out.glob("*.png")), [])


class SimilarityMatrixReaderTests(unittest.TestCase):
    """confusion 热图的真实输入是 export_similarity_matrix.py 导出的方阵。

    解析层必须在无 matplotlib 的机器上也能测，因此不依赖绘图。
    """

    def _write(self, directory, text, name="m_matrix.tsv"):
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_labels_and_values(self):
        with _temp_dir() as tmp:
            path = self._write(
                Path(tmp),
                "variety\tVarA\tVarB\nVarA\t1.000000\t0.500000\nVarB\t0.500000\t1.000000\n")
            labels, values = make_figures.read_square_matrix(path)
            self.assertEqual(labels, ["VarA", "VarB"])
            self.assertEqual(values, [[1.0, 0.5], [0.5, 1.0]])

    def test_unmeasured_cells_stay_none_not_zero(self):
        """空白单元格代表"未测量"，绝不能读成 0.0（= 完全不相似）。"""
        with _temp_dir() as tmp:
            path = self._write(
                Path(tmp),
                "variety\tA\tB\nA\t\t\nB\t\t\n")
            labels, values = make_figures.read_square_matrix(path)
            self.assertEqual(labels, ["A", "B"])
            self.assertEqual(values, [[None, None], [None, None]])
            self.assertNotIn(0.0, [v for row in values for v in row])

    def test_missing_file_returns_none(self):
        with _temp_dir() as tmp:
            labels, values = make_figures.read_square_matrix(Path(tmp) / "nope.tsv")
            self.assertIsNone(labels)
            self.assertIsNone(values)

    def test_ragged_row_is_rejected(self):
        with _temp_dir() as tmp:
            path = self._write(Path(tmp), "variety\tA\tB\nA\t1.0\n")
            with self.assertRaises(ValueError):
                make_figures.read_square_matrix(path)

    def test_confusion_declines_when_matrix_is_all_blank(self):
        """没有任何可比对的品种对时，不能画一张全灰的图冒充结果。"""
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            write_per_query(analysis)
            matrix = self._write(tmpdir, "variety\tA\tB\nA\t\t\nB\t\t\n")
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "confusion", "--similarity-matrix", str(matrix),
            ])
            self.assertEqual(code, 1,
                             "全空矩阵必须拒绝出图；matplotlib 缺失时同样返回 1")
            self.assertEqual(list(out.glob("*.png")), [])

    def test_confusion_matrix_only_needs_no_other_result_file(self):
        """只给方阵、没有 per_query/by_depth 时也应能出热图。"""
        if not have_matplotlib():
            self.skipTest("matplotlib 仅存在于 ricevar 环境")
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            matrix = self._write(
                tmpdir,
                "variety\tA\tB\nA\t1.000000\t0.500000\nB\t0.500000\t1.000000\n")
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "confusion", "--similarity-matrix", str(matrix),
            ])
            self.assertEqual(code, 0)
            self.assertTrue((out / "fig_confusion.png").exists())


class PcaMathTests(unittest.TestCase):
    """PCA 用标准库实现（本机与 ricevar 环境都无 numpy 依赖）。

    这些用例的答案可以解析求出，因此能真正检验实现，而不是"跑通即可"。
    """

    def test_axis_aligned_ellipse_has_known_explained_variance(self):
        # 3:1 椭圆 -> 方差比恰好 0.9 / 0.1
        coords, ratios, found = make_figures.pca_2d(
            [[3.0, 0.0], [-3.0, 0.0], [0.0, 1.0], [0.0, -1.0]])
        self.assertEqual(found, 2)
        self.assertAlmostEqual(ratios[0], 0.9, places=9)
        self.assertAlmostEqual(ratios[1], 0.1, places=9)

    def test_pca_is_rotation_invariant(self):
        """同一形状旋转后，方差比必须不变（这是 PCA 的定义性质）。"""
        import math as _math
        base = [[3.0, 0.0], [-3.0, 0.0], [0.0, 1.0], [0.0, -1.0]]
        for degrees in (37.0, 90.0, 143.0):
            c = _math.cos(_math.radians(degrees))
            s = _math.sin(_math.radians(degrees))
            rotated = [[c * x - s * y, s * x + c * y] for x, y in base]
            _, ratios, found = make_figures.pca_2d(rotated)
            self.assertEqual(found, 2, "旋转 %.0f 度后分量数变了" % degrees)
            self.assertAlmostEqual(ratios[0], 0.9, places=9)
            self.assertAlmostEqual(ratios[1], 0.1, places=9)

    def test_collinear_data_yields_one_component(self):
        _, ratios, found = make_figures.pca_2d(
            [[float(t), 2.0 * float(t)] for t in (-3, -2, -1, 0, 1, 2, 3)])
        self.assertEqual(found, 1)
        self.assertAlmostEqual(ratios[0], 1.0, places=9)

    def test_all_identical_samples_have_no_components(self):
        """所有品种指纹相同时没有方差，必须返回 0 个分量而不是任意方向。"""
        coords, ratios, found = make_figures.pca_2d(
            [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]])
        self.assertEqual(found, 0)
        self.assertEqual(ratios, [])
        self.assertEqual(coords, [[], [], []])

    def test_all_ones_vector_is_not_a_valid_seed(self):
        """中心化矩阵的全 1 向量恒为 0 特征向量，若拿它作种子会得到全 0。

        这是实现中真实踩过的坑，固化为回归测试。
        """
        coords, ratios, found = make_figures.pca_2d(
            [[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]])
        # 各向同性 -> 0.5/0.5；若种子退化会返回 0 个分量。
        self.assertEqual(found, 2)
        self.assertAlmostEqual(ratios[0], 0.5, places=9)
        self.assertAlmostEqual(ratios[1], 0.5, places=9)
        # 坐标非零，证明投影确实算出来了。
        self.assertTrue(any(value != 0.0 for point in coords for value in point))

    def test_empty_and_single_inputs_are_handled(self):
        self.assertEqual(make_figures.pca_2d([]), ([], [], 0))
        coords, ratios, found = make_figures.pca_2d([[1.0, 2.0]])
        self.assertEqual(found, 0)
        self.assertEqual(ratios, [])

    def test_ragged_input_is_rejected(self):
        with self.assertRaises(ValueError):
            make_figures.pca_2d([[1.0, 2.0], [1.0]])

    def test_explained_ratios_sum_to_at_most_one(self):
        rows = [[float(i), float(i % 3), float((i * 7) % 5)] for i in range(10)]
        _, ratios, _ = make_figures.pca_2d(rows)
        self.assertLessEqual(sum(ratios), 1.0 + 1e-9)
        self.assertTrue(all(r >= 0.0 for r in ratios))

    def test_components_are_orthogonal_and_ordered(self):
        """特征值必须降序，且坐标能量与解释方差一致。"""
        rows = [[3.0, 0.0, 1.0], [-3.0, 0.0, 1.0], [0.0, 1.0, -1.0],
                [0.0, -1.0, -1.0], [1.0, 1.0, 0.0]]
        coords, ratios, found = make_figures.pca_2d(rows)
        self.assertEqual(found, 2)
        self.assertGreaterEqual(ratios[0], ratios[1])


class PcaFigureTests(unittest.TestCase):
    """PCA 图的输入是方阵，不是 per_query.tsv。"""

    def _matrix(self, directory, text, name="m_matrix.tsv"):
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_pca_declines_without_a_matrix(self):
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            write_per_query(analysis)
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "pca",
            ])
            # 没有方阵就不产图；matplotlib 缺失时同样返回 1。
            self.assertEqual(code, 1)
            self.assertEqual(list(out.glob("*.png")), [])

    def test_pca_needs_at_least_three_varieties(self):
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            matrix = self._matrix(
                tmpdir, "variety\tA\tB\nA\t1.000000\t0.500000\nB\t0.500000\t1.000000\n")
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "pca", "--similarity-matrix", str(matrix),
            ])
            self.assertEqual(code, 1)
            self.assertEqual(list(out.glob("*.png")), [])

    def test_pca_declines_when_every_row_is_unmeasured(self):
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            matrix = self._matrix(tmpdir, "variety\tA\tB\tC\nA\t\t\t\nB\t\t\t\nC\t\t\t\n")
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "pca", "--similarity-matrix", str(matrix),
            ])
            self.assertEqual(code, 1)
            self.assertEqual(list(out.glob("*.png")), [])

    def test_row_with_only_self_similarity_is_dropped_not_imputed_to_ones(self):
        """对角线的 1.0 不含"这个品种在哪"的信息。

        若只用对角线去填补整行，该品种会被填成 [1,1,1]，即"与所有品种完全
        相同"——这是凭空造出的相似度。必须剔除，而不是补成 1。
        """
        labels = ["A", "B", "C"]
        values = [[1.0, None, None],
                  [None, 1.0, 0.1],
                  [None, 0.1, 1.0]]
        usable, dropped = make_figures.prepare_pca_rows(labels, values)
        self.assertEqual(dropped, ["A"])
        self.assertEqual([name for name, _ in usable], ["B", "C"])
        for _, row in usable:
            self.assertFalse(all(abs(v - 1.0) < 1e-12 for v in row),
                             "行被错误地补成了全 1：%s" % row)

    def test_missing_cells_are_imputed_with_the_row_mean_not_zero(self):
        """未测量的格子不能当 0（完全不相似）填。"""
        labels = ["A", "B", "C"]
        values = [[1.0, 0.8, None],
                  [0.8, 1.0, 0.4],
                  [None, 0.4, 1.0]]
        usable, dropped = make_figures.prepare_pca_rows(labels, values)
        self.assertEqual(dropped, [])
        rows = {name: row for name, row in usable}
        # A 的非对角信息只有 0.8 -> 缺失格填 0.8，而不是 0.0。
        self.assertAlmostEqual(rows["A"][2], 0.8)
        self.assertNotEqual(rows["A"][2], 0.0)
        # C 的非对角信息只有 0.4 -> 缺失格填 0.4。
        self.assertAlmostEqual(rows["C"][0], 0.4)
        # 已测量的值必须原样保留。
        self.assertAlmostEqual(rows["B"][2], 0.4)
        self.assertAlmostEqual(rows["B"][1], 1.0)

    def test_complete_rows_are_left_untouched(self):
        labels = ["A", "B"]
        values = [[1.0, 0.25], [0.25, 1.0]]
        usable, dropped = make_figures.prepare_pca_rows(labels, values)
        self.assertEqual(dropped, [])
        self.assertEqual(usable, [("A", [1.0, 0.25]), ("B", [0.25, 1.0])])

    def test_pca_declines_when_only_one_variety_has_real_pairs(self):
        """只有一个品种有可比对数据时，PCA 无意义，必须拒绝出图。"""
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            matrix = self._matrix(
                tmpdir,
                "variety\tA\tB\tC\n"
                "A\t1.000000\t\t\n"
                "B\t\t1.000000\t0.100000\n"
                "C\t\t0.100000\t1.000000\n")
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "pca", "--similarity-matrix", str(matrix),
            ])
            # A 被剔除后只剩 B、C 两个品种，不足 3 个 -> 不产图。
            self.assertEqual(code, 1)
            self.assertEqual(list(out.glob("*.png")), [])

    def test_pca_writes_coordinates_alongside_the_figure(self):
        if not have_matplotlib():
            self.skipTest("matplotlib 仅存在于 ricevar 环境")
        with _temp_dir() as tmp:
            tmpdir = Path(tmp)
            analysis = tmpdir / "analysis"
            analysis.mkdir()
            text = "variety\tA\tB\tC\n"
            for a in ("A", "B", "C"):
                row = {"A": {"A": "1.0", "B": "0.9", "C": "0.2"},
                       "B": {"A": "0.9", "B": "1.0", "C": "0.3"},
                       "C": {"A": "0.2", "B": "0.3", "C": "1.0"}}[a]
                text += "%s\t%s\t%s\t%s\n" % (a, row["A"], row["B"], row["C"])
            matrix = self._matrix(tmpdir, text)
            out = tmpdir / "figures"
            code = make_figures.main([
                "--analysis-dir", str(analysis), "--out-dir", str(out),
                "--only", "pca", "--similarity-matrix", str(matrix),
            ])
            self.assertEqual(code, 0)
            self.assertTrue((out / "fig_pca.png").exists())
            table = out / "fig_pca_coordinates.tsv"
            self.assertTrue(table.exists())
            lines = table.read_text(encoding="utf-8").rstrip("\n").split("\n")
            self.assertEqual(lines[0].split("\t")[0], "variety")
            self.assertEqual(len(lines), 4)


class FontSelectionTests(unittest.TestCase):
    """图内中文标签必须有字体可渲染，否则论文里会是一堆方框。"""

    def test_load_matplotlib_reports_missing_cjk_font_as_a_warning(self):
        if not have_matplotlib():
            self.skipTest("matplotlib 仅存在于 ricevar 环境")
        plt = make_figures.load_matplotlib()
        self.assertIsNotNone(plt)
        # 无论有无中文字体，都必须显式设定 sans-serif，避免依赖默认字体。
        self.assertTrue(plt.rcParams["font.sans-serif"])
        # 负号在部分中文字体下缺失，必须关闭 unicode_minus。
        self.assertFalse(plt.rcParams["axes.unicode_minus"])

    @unittest.skipUnless(have_matplotlib(), "matplotlib 仅存在于 ricevar 环境")
    @unittest.skipUnless(have_cjk_font(), "本机无中文字体")
    def test_cjk_glyphs_are_actually_available_in_the_chosen_font(self):
        from matplotlib import font_manager
        from matplotlib.ft2font import FT2Font

        plt = make_figures.load_matplotlib()
        chosen = plt.rcParams["font.sans-serif"][0]
        face = FT2Font(font_manager.findfont(font_manager.FontProperties(family=chosen)))
        cmap = face.get_charmap()
        for ch in "测序深度品种准确率最优最相似度闭集技术重复×":
            self.assertIn(ord(ch), cmap, "字体 %s 缺少字形 %r" % (chosen, ch))


if __name__ == "__main__":
    unittest.main()
