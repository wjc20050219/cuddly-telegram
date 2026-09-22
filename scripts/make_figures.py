#!/usr/bin/env python3
"""Generate thesis figures from real result files (TASK-036~040).

Every figure is driven by a result file produced by the pipeline. When the
required file is missing or empty the script reports that and produces **no**
figure — it never substitutes synthetic data or a placeholder curve, because a
fabricated figure in a thesis is indistinguishable from a fabricated experiment.

Usage::

    python scripts/make_figures.py --analysis-dir analysis --out-dir figures
    python scripts/make_figures.py --analysis-dir analysis --only depth_curve

Figures
-------
* ``depth_curve``     Top-1/Top-5 variety accuracy vs sequencing depth
* ``marker_recall``   marker recall and genotype concordance vs depth
* ``marker_count``    accuracy vs frozen marker-set size
* ``similarity_dist`` best-match similarity distribution per depth
* ``confusion``       variety-vs-variety similarity heatmap
* ``pca``             PCA of the variety similarity matrix (needs a square matrix)
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

FIGURES = ["depth_curve", "marker_recall", "marker_count", "similarity_dist",
           "confusion", "pca"]


def log(message):
    sys.stderr.write("[figures] %s\n" % message)


def read_tsv(path):
    """Read a TSV into a list of dicts, tolerating a missing file."""
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle, delimiter="\t") if row]
    return rows or None


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_float(value):
    """Convert to float, mapping missing/NaN text to ``None``."""
    number = to_float(value)
    if number is None:
        return None
    # NaN != NaN is the portable check and avoids importing math for one test.
    return None if number != number else number


def load_matplotlib():
    try:
        import matplotlib
    except ImportError:
        log("未安装 matplotlib，无法绘图。请在 ricevar 环境中安装：conda install matplotlib")
        return None
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 图的中文标题/轴标签需要 CJK 字体；默认 DejaVu Sans 没有汉字，
    # 会静默渲染成方框（图仍是有效 PNG，但论文里不能用）。
    # 因此按可用性挑一个中文字体，并关掉缺字告警噪音。
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for candidate in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                      "Source Han Sans SC", "WenQuanYi Zen Hei", "Arial Unicode MS"):
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate]
            log("使用中文字体：%s" % candidate)
            break
    else:
        log("警告：未找到中文字体，图内中文标签会显示为方框。"
            "请安装 Microsoft YaHei / Noto Sans CJK，或在无中文字体环境下接受英文标签。")
    plt.rcParams["axes.unicode_minus"] = False  # 负号在部分中文字体下会缺失

    return plt


def require_rows(rows, path, what):
    """Return True when a figure has real data behind it."""
    if rows is None:
        log("跳过：缺少结果文件 %s（%s）" % (path, what))
        return False
    log("%s：读取 %d 行自 %s" % (what, len(rows), path))
    return True


# ---------- 图 1：深度–准确率曲线 ----------
def fig_depth_curve(rows, out_dir, plt):
    depths = sorted({r["depth_label"] for r in rows if r.get("depth_label")},
                    key=lambda d: float(d))
    series = {}
    for row in rows:
        marker_count = row.get("marker_count", "?")
        series.setdefault(marker_count, {})[row["depth_label"]] = row

    if not series:
        log("depth_curve：无有效深度标签，跳过。")
        return None

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for marker_count in sorted(series, key=lambda c: to_float(c) or 0):
        points = series[marker_count]
        xs = [float(d) for d in depths if d in points]
        if not xs:
            continue
        top1 = [as_float(points[d].get("top1_correct_variety")) for d in depths if d in points]
        top5 = [as_float(points[d].get("top5_correct_variety")) for d in depths if d in points]
        axes[0].plot(xs, top1, marker="o", label="%s markers" % marker_count)
        axes[1].plot(xs, top5, marker="s", label="%s markers" % marker_count)

    for ax, title in zip(axes, ["Top-1 品种准确率", "Top-5 品种准确率"]):
        ax.set_xscale("log")
        ax.set_xlabel("测序深度 (×)")
        ax.set_ylabel("准确率")
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(title)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle("超低深度下水稻品种识别准确率（闭集，技术重复）", fontsize=10)
    fig.tight_layout()
    target = out_dir / "fig_depth_curve.png"
    fig.savefig(str(target), dpi=300)
    plt.close(fig)
    return target


# ---------- 图 2：marker recall 与基因型一致率 ----------
def fig_marker_recall(rows, out_dir, plt):
    depths = sorted({r["depth_label"] for r in rows if r.get("depth_label")},
                    key=lambda d: float(d))
    if not depths:
        log("marker_recall：无有效深度标签，跳过。")
        return None

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for marker_count in sorted({r.get("marker_count", "?") for r in rows},
                               key=lambda c: to_float(c) or 0):
        subset = {r["depth_label"]: r for r in rows if r.get("marker_count") == marker_count}
        xs = [float(d) for d in depths if d in subset]
        recall = [as_float(subset[d].get("marker_recall")) for d in depths if d in subset]
        ax.plot(xs, recall, marker="o", label="%s markers" % marker_count)

    ax.set_xscale("log")
    ax.set_xlabel("测序深度 (×)")
    ax.set_ylabel("marker recall")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("低深度下冻结 marker 的检出率")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    target = out_dir / "fig_marker_recall.png"
    fig.savefig(str(target), dpi=300)
    plt.close(fig)
    return target


# ---------- 图 3：marker 数量–准确率 ----------
def fig_marker_count(rows, out_dir, plt):
    by_count = {}
    for row in rows:
        count = as_float(row.get("marker_count"))
        value = as_float(row.get("top1_correct_variety"))
        if count is None or value is None:
            continue
        by_count.setdefault(count, []).append(value)
    if not by_count:
        log("marker_count：没有可用的 marker 数–准确率配对，跳过。")
        return None

    xs = sorted(by_count)
    # 每个深度各一条曲线会过密，这里按深度分组绘制。
    depths = sorted({r["depth_label"] for r in rows if r.get("depth_label")},
                    key=lambda d: float(d))
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for depth in depths:
        xs_d, ys_d = [], []
        for count in xs:
            values = [as_float(r.get("top1_correct_variety")) for r in rows
                      if r.get("depth_label") == depth
                      and as_float(r.get("marker_count")) == count]
            values = [v for v in values if v is not None]
            if values:
                xs_d.append(count)
                ys_d.append(sum(values) / len(values))
        if xs_d:
            ax.plot(xs_d, ys_d, marker="o", label="%s×" % depth)

    ax.set_xscale("log")
    ax.set_xlabel("冻结 marker 数量")
    ax.set_ylabel("Top-1 品种准确率")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("marker 数量对识别准确率的影响")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    target = out_dir / "fig_marker_count.png"
    fig.savefig(str(target), dpi=300)
    plt.close(fig)
    return target


# ---------- 图 4：最佳相似度分布 ----------
def fig_similarity_dist(per_query, out_dir, plt):
    by_depth = {}
    for row in per_query:
        depth = row.get("depth_label")
        value = as_float(row.get("best_similarity"))
        if depth and value is not None:
            by_depth.setdefault(depth, []).append(value)
    if not by_depth:
        log("similarity_dist：per_query.tsv 中没有可用相似度，跳过。")
        return None

    depths = sorted(by_depth, key=lambda d: float(d))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.boxplot([by_depth[d] for d in depths], labels=depths, showmeans=True)
    ax.set_xlabel("测序深度 (×)")
    ax.set_ylabel("最佳匹配相似度")
    ax.set_title("各深度下最佳匹配相似度分布")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    target = out_dir / "fig_similarity_dist.png"
    fig.savefig(str(target), dpi=300)
    plt.close(fig)
    return target


# ---------- 图 5：品种间相似度热图 ----------
def read_square_matrix(path):
    """Read the square matrix written by export_similarity_matrix.py.

    Returns ``(labels, values)`` where ``values[i][j]`` is a float or ``None``
    for an unmeasured pair. Cells are left as ``None`` (not 0.0) so the heatmap
    can mask them; drawing "not measured" as "maximally dissimilar" would
    invent a result.
    """
    if not path.exists():
        return None, None
    labels = None
    values = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            fields = line.split("\t")
            if labels is None:
                labels = fields[1:]
                continue
            cells = [as_float(cell) for cell in fields[1:]]
            if len(cells) != len(labels):
                raise ValueError("矩阵行 %s 的列数与表头不一致" % fields[0])
            values.append(cells)
    if not labels or len(values) != len(labels):
        return None, None
    return labels, values


def fig_confusion(per_query, out_dir, matrix_path=None):
    """Variety-vs-variety similarity heatmap from the exported square matrix.

    ``per_query.tsv`` only records each query's best match, which is not enough
    to draw a matrix, so the real input is ``*_matrix.tsv`` produced by
    ``scripts/export_similarity_matrix.py``.
    """
    plt = load_matplotlib()
    if plt is None:
        return None
    from matplotlib.colors import LinearSegmentedColormap

    if matrix_path is None or not Path(matrix_path).exists():
        log("confusion：未找到相似度方阵 *_matrix.tsv，跳过该图。"
            "请先用 scripts/export_similarity_matrix.py 导出成对相似度矩阵"
            "（per_query.tsv 只含最佳匹配，无法构成矩阵），"
            "再用 --similarity-matrix 指定该文件。")
        return None
    matrix_path = Path(matrix_path)

    labels, values = read_square_matrix(matrix_path)
    if not labels:
        log("confusion：%s 不是有效的方阵，跳过。" % matrix_path)
        return None

    n = len(labels)
    if n < 2:
        log("confusion：只有 %d 个品种，无法构成热图。" % n)
        return None

    masked = [
        [float("nan") if value is None else value for value in row]
        for row in values
    ]
    measured = sum(1 for row in values for v in row if v is not None)
    total = n * n
    if measured == 0:
        log("confusion：矩阵中没有任何可比对的品种对（比较位点均不足），跳过。")
        return None
    if measured < total:
        log("confusion：%d/%d 个单元格无可用相似度，将显示为遮罩（非 0）。"
            % (total - measured, total))

    fig, ax = plt.subplots(figsize=(max(6.0, 0.42 * n + 2.0), max(5.0, 0.42 * n + 1.5)))
    cmap = LinearSegmentedColormap.from_list("ricevar", ["#f7f7f7", "#9ecae1", "#08519c"])
    cmap.set_bad(color="#d9d9d9")
    image = ax.imshow(masked, cmap=cmap, vmin=0.0, vmax=1.0)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_title("品种间 SNP 指纹相似度（%s）" % matrix_path.stem)
    ax.set_xlabel("参考品种")
    ax.set_ylabel("参考品种")

    bar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    bar.set_label("相似度")
    fig.tight_layout()

    target = out_dir / "fig_confusion.png"
    fig.savefig(str(target), dpi=300)
    plt.close(fig)
    log("相似度热图来源：%s（%d 个品种）" % (matrix_path, n))
    return target


def pca_2d(rows, n_components=2, iters=1000, tol=1e-13):
    """Top principal components of centred row vectors, standard library only.

    The core package is stdlib-only by design and the local Windows Python has
    no numpy, so PCA is computed directly on the ``n x n`` Gram matrix
    ``X X^T``. Working on the Gram matrix (rather than the ``d x d`` covariance)
    is exact, and here ``n`` = number of varieties, which is far smaller than
    the marker count ``d``.

    Returns ``(coords, explained_ratio, n_found)`` where ``coords[i][k]`` is the
    projection of sample ``i`` onto component ``k``.

    Seeds are unit basis vectors, never the all-ones vector: for a **centred**
    matrix every row sums to zero, so the all-ones vector is always an
    eigenvector with eigenvalue 0 and a power iteration started from it returns
    exactly zero. Components with negligible eigenvalue are dropped rather than
    returned as arbitrary directions.
    """
    n = len(rows)
    if n == 0:
        return [], [], 0
    if any(len(r) != len(rows[0]) for r in rows):
        raise ValueError("PCA 输入各样本的特征维数必须一致")

    dim = len(rows[0])
    means = [sum(r[j] for r in rows) / n for j in range(dim)]
    centred = [[r[j] - means[j] for j in range(dim)] for r in rows]
    gram = [[sum(centred[i][k] * centred[j][k] for k in range(dim)) for j in range(n)]
            for i in range(n)]
    total = sum(gram[i][i] for i in range(n))
    if total <= 0:
        # All samples identical: no variance, so no components to report.
        return [[] for _ in range(n)], [], 0

    def matvec(vector):
        return [sum(gram[i][j] * vector[j] for j in range(n)) for i in range(n)]

    def norm(vector):
        return math.sqrt(sum(x * x for x in vector))

    def deflate(vector, basis):
        for unit in basis:
            dot = sum(vector[i] * unit[i] for i in range(n))
            vector = [vector[i] - dot * unit[i] for i in range(n)]
        return vector

    found = []
    for index in range(n):
        if len(found) >= n_components:
            break
        seed = [0.0] * n
        seed[index] = 1.0
        # Skip a seed that already lies (almost) in the span of found components.
        if any(abs(sum(seed[i] * unit[i] for i in range(n))) > 0.99 for unit, _ in found):
            continue

        basis = [unit for unit, _ in found]
        vector = deflate(seed, basis)
        length = norm(vector)
        if length < 1e-12:
            continue
        vector = [x / length for x in vector]

        for _ in range(iters):
            candidate = deflate(matvec(vector), basis)
            candidate_norm = norm(candidate)
            if candidate_norm < 1e-12:
                vector = None
                break
            candidate = [x / candidate_norm for x in candidate]
            if norm([candidate[i] - vector[i] for i in range(n)]) < tol:
                vector = candidate
                break
            vector = candidate
        if vector is None:
            continue

        eigenvalue = sum(vector[i] * matvec(vector)[i] for i in range(n))
        if eigenvalue <= 1e-9:
            continue
        found.append((vector, eigenvalue))

    ratios = [eigenvalue / total for _, eigenvalue in found]
    coords = [[math.sqrt(eigenvalue) * vector[i] for vector, eigenvalue in found]
              for i in range(n)]
    return coords, ratios, len(found)


def prepare_pca_rows(labels, values):
    """Turn a sparse similarity matrix into dense PCA input rows.

    Unmeasured cells must never be treated as "similarity 0": that would place
    two varieties at opposite ends of PC1 purely for lack of data. Each missing
    cell is imputed with the mean of the row's **informative** off-diagonal
    entries.

    The diagonal (self-similarity, always 1.0) carries no information about
    where a variety sits, so a row whose only measured value is its own diagonal
    is dropped rather than imputed -- otherwise it would become all-ones and be
    drawn as a variety identical to every other one, which is a fabricated
    result rather than a missing one.

    Returns ``(usable, dropped)`` as ``([(label, row), ...], [label, ...])``.
    """
    usable, dropped = [], []
    for index, row in enumerate(values):
        informative = [value for position, value in enumerate(row)
                       if value is not None and position != index]
        if not informative:
            dropped.append(labels[index])
            continue
        row_mean = sum(informative) / len(informative)
        usable.append((labels[index],
                       [row_mean if value is None else value for value in row]))
    return usable, dropped


def fig_pca(per_query, out_dir, matrix_path=None):
    """PCA of the variety fingerprint similarity matrix (TASK-036).

    The input is the pairwise similarity matrix, not ``per_query.tsv``: a PCA
    needs every variety's coordinates, and ``per_query.tsv`` only records each
    query's best match.
    """
    plt = load_matplotlib()
    if plt is None:
        return None

    if matrix_path is None or not Path(matrix_path).exists():
        log("pca：未找到相似度方阵 *_matrix.tsv，跳过该图。"
            "请先用 scripts/export_similarity_matrix.py 导出成对相似度矩阵，"
            "再用 --similarity-matrix 指定该文件。")
        return None
    matrix_path = Path(matrix_path)

    labels, values = read_square_matrix(matrix_path)
    if not labels:
        log("pca：%s 不是有效的方阵，跳过。" % matrix_path)
        return None

    n = len(labels)
    if n < 3:
        log("pca：只有 %d 个品种，主成分分析没有意义（至少需要 3 个），跳过。" % n)
        return None

    usable, dropped = prepare_pca_rows(labels, values)
    if dropped:
        log("pca：%d 个品种除自身外没有任何可比对的品种对（%s），"
            "无法定位其坐标，已剔除。" % (len(dropped), "、".join(dropped[:5])))
    if len(usable) < 3:
        log("pca：可用品种不足 3 个，跳过。")
        return None

    used_labels = [label for label, _ in usable]
    coords, ratios, found = pca_2d([row for _, row in usable])
    if found < 1:
        log("pca：矩阵没有方差（所有品种指纹完全相同），跳过。")
        return None

    xs = [point[0] for point in coords]
    if found >= 2:
        ys = [point[1] for point in coords]
        ylabel = "PC2 (%.1f%% 方差)" % (100 * ratios[1])
    else:
        ys = [0.0] * len(coords)
        ylabel = "PC2 (无)"

    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    ax.scatter(xs, ys, s=28, c="#08519c", alpha=0.85, edgecolors="white", linewidths=0.4)
    for label, x, y in zip(used_labels, xs, ys):
        ax.annotate(label, (x, y), fontsize=6, xytext=(3, 3),
                    textcoords="offset points", alpha=0.85)
    ax.axhline(0.0, color="#cccccc", linewidth=0.6, zorder=0)
    ax.axvline(0.0, color="#cccccc", linewidth=0.6, zorder=0)
    ax.set_xlabel("PC1 (%.1f%% 方差)" % (100 * ratios[0]))
    ax.set_ylabel(ylabel)
    ax.set_title("品种 SNP 指纹主成分分析（%d 个品种）" % len(used_labels))
    ax.grid(alpha=0.25, linestyle=":")
    fig.tight_layout()

    target = out_dir / "fig_pca.png"
    fig.savefig(str(target), dpi=300)
    plt.close(fig)
    log("PCA 来源：%s（%d 个品种，PC1 %.1f%%，PC2 %s）"
        % (matrix_path, len(used_labels), 100 * ratios[0],
           "%.1f%%" % (100 * ratios[1]) if found >= 2 else "无"))
    # PCA coordinates are only meaningful together with their explained
    # variance, so write them next to the figure for the thesis text.
    table = out_dir / "fig_pca_coordinates.tsv"
    with table.open("w", encoding="utf-8", newline="") as handle:
        handle.write("variety\tPC1\tPC2\texplained_ratio_PC1\texplained_ratio_PC2\n")
        for label, x, y in zip(used_labels, xs, ys):
            handle.write("%s\t%.6f\t%.6f\t%.6f\t%s\n"
                         % (label, x, y, ratios[0],
                            ("%.6f" % ratios[1]) if found >= 2 else ""))
    return target


HANDLERS = {
    "depth_curve": ("identification_by_depth.tsv", fig_depth_curve),
    "marker_recall": ("identification_by_depth.tsv", fig_marker_recall),
    "marker_count": ("identification_by_depth.tsv", fig_marker_count),
    "similarity_dist": ("per_query.tsv", fig_similarity_dist),
    "confusion": ("per_query.tsv", fig_confusion),
    "pca": ("per_query.tsv", fig_pca),
}

# These figures read the exported similarity matrix rather than a per_query
# table, so they are gated on --similarity-matrix instead of their filename.
MATRIX_FIGURES = {fig_confusion, fig_pca}


def main(argv=None):
    parser = argparse.ArgumentParser(description="从真实结果文件生成论文图（无数据则不产图）")
    parser.add_argument("--analysis-dir", required=True,
                        help="包含 identification_by_depth.tsv / per_query.tsv 的结果目录")
    parser.add_argument("--out-dir", default="figures", help="图片输出目录")
    parser.add_argument("--only", choices=FIGURES, action="append",
                        help="只生成指定图（可重复）")
    parser.add_argument("--similarity-matrix", default=None,
                        help="confusion 热图与 pca 用的 <stem>_matrix.tsv"
                             "（由 scripts/export_similarity_matrix.py 生成）")
    args = parser.parse_args(argv)

    analysis = Path(args.analysis_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    by_depth = read_tsv(analysis / "identification_by_depth.tsv")
    per_query = read_tsv(analysis / "per_query.tsv")
    sources = {"identification_by_depth.tsv": by_depth, "per_query.tsv": per_query}

    # 先盘清有哪些真实结果文件，再决定能否绘图——缺数据与缺 matplotlib 是两类
    # 不同的问题，必须分别报清楚，否则用户不知道到底该补数据还是补依赖。
    matrix_file = Path(args.similarity_matrix) if args.similarity_matrix else None
    has_matrix = bool(matrix_file and matrix_file.exists())
    available = [name for name, rows in sources.items() if rows]
    if not available and not has_matrix:
        log("在 %s 中没有找到任何可用结果文件。" % analysis)
        log("需要 identification_by_depth.tsv 和/或 per_query.tsv（由 07_identify.sh 生成）；")
        log("confusion 热图与 pca 还需要 --similarity-matrix 指定的方阵文件。")
        log("无真实数据时不产图，也不使用任何示意数据代替。")
        print("生成 0 张图：缺少结果文件（见 stderr）")
        return 1

    plt = load_matplotlib()
    if plt is None:
        log("已找到结果文件，但缺少 matplotlib，无法绘图。")
        return 1

    produced, skipped = [], []
    for name in (args.only or FIGURES):
        filename, handler = HANDLERS[name]
        if handler in MATRIX_FIGURES:
            # These read the exported square matrix, not per_query.tsv.
            target = handler(sources.get("per_query.tsv"), out_dir,
                             matrix_path=args.similarity_matrix)
        else:
            rows = sources[filename]
            if not require_rows(rows, analysis / filename, name):
                skipped.append(name)
                continue
            target = handler(rows, out_dir, plt)
        if target is None:
            skipped.append(name)
        else:
            log("已生成 %s" % target)
            produced.append(target)

    print("生成 %d 张图，跳过 %d 张" % (len(produced), len(skipped)))
    for target in produced:
        print("  %s" % target)
    if skipped:
        print("跳过：%s（原因见 stderr）" % ", ".join(skipped))
    # 无图可出不算失败，但要让调用方知道结果为空。
    return 0 if produced else 1


if __name__ == "__main__":
    raise SystemExit(main())
