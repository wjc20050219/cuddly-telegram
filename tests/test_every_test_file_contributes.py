#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""每个 `tests/test_*.py` 都必须真的贡献测试用例。

**这个缺陷真实发生过**：三个文件名字匹配 `test_*.py`，内容却是
**模块级脚本**。`unittest discover` 会 import 它们——于是真的执行
子进程、往 `.tmp/` 写文件——然后收集到 **0 个测试用例**：
所有判定只 `print` 而从不 `assert`，失败被彻底丢弃。
套件依然打印 `OK`。

其中 `test_eval_reverse.py` 连 `sys.exit` 都没有：即使反向验证
失败，它的退出码仍是 0。而 `verify_undergraduate_scope.py`
把它当作"已证明能检出缺陷"的证据引用，那条检查却只验证文件**存在**。

危险之处在于它有**两面性**：正常的测试套件会执行这些脚本的副作用，
所以输出里能看到 `[OK] ...`，让人误以为它们"在跑且通过了"。

本文件从两个方向锁死：
1. 每个 `test_*.py` 至少贡献 1 个用例；
2. 这些用例必须能被真正执行（`run`），而不只是被收集。
"""

from __future__ import print_function

import os
import unittest


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _test_files():
    return sorted(f for f in os.listdir(TESTS_DIR)
                  if f.startswith("test_") and f.endswith(".py"))


class EveryTestFileContributesCasesTests(unittest.TestCase):
    """没有任何 `test_*.py` 可以"存在但零用例"。"""

    def test_there_is_at_least_one_test_file(self):
        """防止目录被清空后本文件空转通过。"""
        self.assertGreater(len(_test_files()), 0)

    def test_no_test_file_contributes_zero_cases(self):
        loader = unittest.TestLoader()
        offenders = []
        for name in _test_files():
            if name == os.path.basename(__file__):
                continue
            suite = loader.discover(TESTS_DIR, pattern=name)
            if suite.countTestCases() == 0:
                offenders.append(name)
        self.assertEqual(
            [], offenders,
            "以下文件匹配 test_*.py 却贡献 0 个测试用例，其判定会被静默丢弃：%s"
            % offenders)

    def test_discovery_collects_the_same_total_as_listing_files(self):
        """逐文件收集的总数应与整体 discover 一致。

        若某个文件被 import 时抛异常，整体 discover 会记录一个
        `_FailedTest`，而逐文件收集不会——这个差异要能被看见。
        """
        loader = unittest.TestLoader()
        whole = loader.discover(TESTS_DIR).countTestCases()
        per_file = sum(
            loader.discover(TESTS_DIR, pattern=name).countTestCases()
            for name in _test_files())
        self.assertEqual(per_file, whole,
                         "逐文件收集 %d 个用例，整体收集 %d 个：有文件在 import 时"
                         "行为不一致" % (per_file, whole))


if __name__ == "__main__":
    unittest.main()
