#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""反向验证 `select_snp_markers` 的位点筛选不变量。

只通过、从不失败的测试毫无价值。这里对真实模块的行为做内存级变异，
确认每条不变量测试**确实能检出**对应缺陷。

**为什么要重写成本文件**：它原先是一个模块级脚本（名字却匹配 `test_*.py`），
`unittest discover` 会 import 它、执行全部变异与检查，
却收集到 **0 个测试用例**——所有判定只 `print` 而不 `assert`，
失败既不会让测试套件变红，也不会体现在退出码里。
一个"反向验证"如果它的失败无法被报告，就不构成证据。

`setUp` 用 `importlib.reload` 保证每个用例拿到**干净**的模块，
避免变异在用例之间泄漏。
"""

from __future__ import print_function

import bisect
import importlib
import sys
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import select_snp_markers as ssm  # noqa: E402


class SelectorInvariantReverseTests(unittest.TestCase):
    """每条不变量都必须能在缺陷被注入时失败。"""

    def setUp(self):
        # 干净副本，防止上一个用例的变异泄漏。
        importlib.reload(ssm)

    def tearDown(self):
        importlib.reload(ssm)

    # ---------- 1. 全缺失位点必须得 0 分 ----------

    def _break_metrics(self):
        def bad(calls):
            called = [v for v in calls if v >= 0]
            call_rate = len(called) / len(calls)
            alt = sum(called) / (2.0 * len(called)) if called else 0.0
            maf = min(alt, 1.0 - alt)
            from collections import Counter
            counts = Counter(called)
            pairs = len(called) * (len(called) - 1) / 2.0
            conc = sum(c * (c - 1) / 2.0 for c in counts.values())
            return call_rate, maf, (1.0 - conc / pairs) if pairs else 0.12
        ssm.site_metrics = bad

    @staticmethod
    def _check_all_missing():
        if ssm.site_metrics([-1] * 10) != (0.0, 0.0, 0.0):
            raise AssertionError("all-missing site scored non-zero")
        for calls in ([0] * 10, [1] * 10, [2] * 10):
            if ssm.site_metrics(calls)[2] != 0.0:
                raise AssertionError("invariant site scored non-zero")

    def test_all_missing_sites_must_score_zero(self):
        """去掉全缺失早退后，空位点会得到 0.12 的假区分度——必须被检出。"""
        self._break_metrics()
        with self.assertRaises(AssertionError):
            self._check_all_missing()

    def test_the_invariant_holds_on_unmutated_code(self):
        """对照：未变异时必须通过，否则上面的断言没有意义。"""
        self._check_all_missing()

    # ---------- 2. 间隔筛选必须是全局的 ----------

    def _break_spacing_scope(self):
        def per_chrom(candidates, wanted, min_distance):
            selected, positions = [], {}
            from collections import defaultdict
            positions = defaultdict(list)
            for cand in candidates:
                chrom, pos = str(cand[5]), int(cand[6])
                existing = positions[chrom]
                i = bisect.bisect_left(existing, pos)
                left = i == 0 or pos - existing[i - 1] >= min_distance
                right = i == len(existing) or existing[i] - pos >= min_distance
                if left and right:
                    bisect.insort(existing, pos)
                    selected.append(cand)
            return selected          # 无全局上限 -> 变成按染色体
        ssm.apply_spacing = per_chrom

    @staticmethod
    def _check_global():
        def cand(d, o, p, c):
            return (d, 1.0, 0.2, 60.0, -o, c, p, "A", "T")
        sites = [cand(0.9 - o * 1e-4, o, 1_000_000 + k * 10_000, "chr%d" % c)
                 for o, (c, k) in enumerate(
                     [(c, k) for c in range(1, 13) for k in range(5)], 1)]
        got = len(ssm.apply_spacing(sorted(sites, reverse=True), 5, 1000))
        if got != 5:
            raise AssertionError("expected 5, got %d" % got)

    def test_spacing_must_be_global_not_per_chromosome(self):
        self._break_spacing_scope()
        with self.assertRaises(AssertionError):
            self._check_global()

    def test_global_spacing_holds_on_unmutated_code(self):
        self._check_global()

    # ---------- 3. min_distance 必须被真正执行 ----------

    def _break_min_distance(self):
        original = ssm.apply_spacing

        def ignore_distance(candidates, wanted, min_distance):
            return original(candidates, wanted, 0)
        ssm.apply_spacing = ignore_distance

    @staticmethod
    def _check_min_distance():
        def cand(d, o, p):
            return (d, 1.0, 0.2, 60.0, -o, "chr1", p, "A", "T")
        # 密集位点：相隔 100 bp。min_distance=1000 必须只留 1 个。
        packed = [cand(0.9 - o * 1e-4, o, p)
                  for o, p in enumerate([0, 100, 200, 300])]
        picked = ssm.apply_spacing(sorted(packed, reverse=True), 4, 1000)
        if len(picked) != 1:
            raise AssertionError("expected 1 survivor, got %d" % len(picked))

    def test_min_distance_must_be_enforced_on_packed_layout(self):
        self._break_min_distance()
        with self.assertRaises(AssertionError):
            self._check_min_distance()

    def test_min_distance_holds_on_unmutated_code(self):
        self._check_min_distance()

    # ---------- 4. 嵌套来自"前缀切片"这一结构，而非 id 的取值 ----------

    @staticmethod
    def _check_nesting():
        def cand(d, o, p):
            return (d, 1.0, 0.2, 60.0, -o, "chr1", p, "A", "T")
        ranked = [cand(0.99 - i * 1e-5, i, i * 2000) for i in range(2000)]
        ids = [ssm.marker_id(c) for c in ranked]
        tiers = {n: set(ids[:n]) for n in (500, 1000, 2000)}
        if not (tiers[500] <= tiers[1000] <= tiers[2000]):
            raise AssertionError("tiers not nested")

    def test_nesting_survives_an_id_change_because_it_is_structural(self):
        """如实记录：改 `marker_id` 的**取值**不会破坏嵌套。

        嵌套来自"同一排名上的前缀切片"，与 id 如何拼写无关。
        所以这里断言的是"变异后**仍然通过**"——
        这是一个**语义等价的变异**，不是测试漏洞。
        把它写成"期望失败"会得到一个永远为假的反向验证。
        """
        def bad_id(candidate):
            return "%s:%s" % (candidate[5], candidate[6])
        ssm.marker_id = bad_id
        self._check_nesting()   # 不应抛异常

    def test_nesting_holds_on_unmutated_code(self):
        self._check_nesting()


if __name__ == "__main__":
    unittest.main()
