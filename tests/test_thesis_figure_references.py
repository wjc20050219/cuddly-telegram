#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""锁定论文里每一张 `figures/*.png` 引用都**真的有生成脚本**。

缺陷背景：论文第 3 章曾引用 `figures/fig_snp_density.png` 与
`figures/fig_prototype.png`，但 `make_figures.py` **根本不产出这两张**；
反过来，真正实现了核心结果的 `fig_pca.png` 与 `fig_confusion.png`
**一次都没被引用**。指向不存在产物的图表引用，在答辩时是硬伤。

本测试把"引用"与"产物"两个方向都锁死：
1. 每个被引用的文件名，必须能由某个 `scripts/*.py` 产出；
2. 每个能产出的图，必须在论文里被引用（否则做了图却没写进论文）。
"""

from __future__ import print_function

import io
import os
import re
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THESIS = os.path.join(ROOT, "docs", "thesis", "THESIS_DRAFT.md")
MAKE_FIGURES = os.path.join(ROOT, "scripts", "make_figures.py")


def _read(path):
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


class ThesisFigureReferenceTests(unittest.TestCase):
    def setUp(self):
        self.thesis = _read(THESIS)
        self.mf = _read(MAKE_FIGURES)
        self.cited = sorted(set(re.findall(r"figures/(fig_[A-Za-z0-9_]+\.png)", self.thesis)))

    def _all_script_text(self):
        blob = []
        for root, _dirs, files in os.walk(os.path.join(ROOT, "scripts")):
            for name in files:
                if name.endswith(".py"):
                    blob.append(_read(os.path.join(root, name)))
        return "\n".join(blob)

    def test_the_thesis_cites_at_least_one_figure(self):
        self.assertTrue(self.cited, "第 3 章应当引用图表")

    def test_every_cited_figure_has_a_producer(self):
        """没有生成脚本的图不能被引用——那是指向不存在产物的引用。"""
        blob = self._all_script_text()
        orphan = [c for c in self.cited if c[:-4] not in blob]
        self.assertEqual([], orphan,
                         "论文引用了没有生成脚本的图：%s" % orphan)

    def test_every_produced_figure_is_cited(self):
        """做出来的图必须写进论文，否则等于白做。"""
        produced = sorted(set(re.findall(r"fig_([a-z_]+)\.png", self.mf)))
        self.assertTrue(produced, "make_figures.py 应当产出图")
        missing = ["fig_%s.png" % p for p in produced
                   if "fig_%s.png" % p not in self.cited]
        self.assertEqual([], missing,
                         "这些图有生成脚本但论文未引用：%s" % missing)

    def test_placeholder_file_targets_are_well_formed(self):
        """`{{FILE: ...}}` 必须是真实路径，不得用中文描述冒充文件名。

        注意：`{{FILE:}}` 不只用于图，也用于其他产物（如 MultiQC 报告），
        所以这里只要求"看起来是个路径"，而不是"必须是 figures/ 下的 png"。
        正文里作为**行文**提到的空 `{{FILE:}}`（带反引号）不算引用。
        """
        raw = re.findall(r"\{\{FILE:\s*([^}]*?)\s*\}\}", self.thesis)
        real = [r for r in raw if r]  # 空的是行文提法，不是引用
        bad = [r for r in real if not re.match(r"^[A-Za-z0-9_./-]+$", r)]
        self.assertEqual([], bad,
                         "FILE 占位符必须是路径形式，不能是中文描述：%s" % bad)
        self.assertIn("因此本章不设对应", self.thesis,
                      "不设占位必须说明原因")

    def test_the_figure_command_table_matches_the_real_cli(self):
        """3.9 的对应表必须与实际 `--only` 取值一致。"""
        only = sorted(set(re.findall(r'["\']([a-z_]+)["\']\s*:', self.mf)))
        section = self.thesis.split("### 3.9")[1] if "### 3.9" in self.thesis else ""
        self.assertTrue(section, "应当有一节说明图表与脚本的对应关系")
        for key in ("marker_recall", "depth_curve", "marker_count",
                    "similarity_dist", "confusion", "pca"):
            self.assertIn(key, only, "make_figures 应支持 --only %s" % key)
            self.assertIn("--only %s" % key, section,
                          "3.9 未登记 --only %s" % key)

    def test_figures_that_cannot_yet_be_produced_are_declared(self):
        """不可产出的图必须**明说**，而不是留一个假占位。"""
        self.assertIn("尚未有生成脚本的图", self.thesis)
        # 这两项在服务器可用前确实做不出来，必须写明。
        self.assertIn("质控图", self.thesis)
        self.assertIn("Streamlit 原型截图", self.thesis)

    def test_the_two_phantom_figures_stay_out(self):
        """历史缺陷：这两个文件名没有生成脚本，不得回流。"""
        self.assertNotIn("fig_snp_density.png", self.thesis)
        self.assertNotIn("fig_prototype.png", self.thesis)


if __name__ == "__main__":
    unittest.main()
