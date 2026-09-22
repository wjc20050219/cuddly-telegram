#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""证明 `verify_shell_static.py` 真的能检出它声称能检出的缺陷。

只打印"无发现"的检查器毫无价值。这里把每类缺陷注入到真实脚本的副本里，
运行分析器，并断言发现确实出现。

**为什么要重写成本文件**：本文件原名就是 `test_shell_static_detects.py`，
但它是一个**模块级脚本**——`unittest discover` 会 import 它（于是真的执行
子进程、往 `.tmp/` 写文件），却收集到 **0 个测试用例**，
所有判定只 `print` 而不 `assert`，结果被**静默丢弃**。
更糟的是 `test_eval_reverse.py` 连 `sys.exit` 都没有，
即使反向验证失败它也返回 0。这三个文件都被报告与
`verify_undergraduate_scope.py` 当作"已证明能检出缺陷"的证据引用。

现在它是真正的 unittest 模块：每个用例独立、失败会被报告。
"""

from __future__ import print_function

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
SCRIPTS = ROOT / "scripts"
TMP = ROOT / ".tmp"


def run_analyzer(server_dir):
    """Run the analyzer against a substitute server directory."""
    code = (
        "import sys, pathlib\n"
        "sys.path.insert(0, r'%s')\n"
        "import verify_shell_static as v\n"
        "v.SERVER = pathlib.Path(r'%s')\n"
        "sys.exit(v.main(['--strict']))\n"
    ) % (str(SCRIPTS), str(server_dir))
    return subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True)


def stage_tmp_copy(dest):
    for path in SERVER.glob("*.sh"):
        shutil.copy2(path, dest / path.name)


INJECTIONS = [
    ("未定义变量", "config.sh",
     '\necho "使用未定义变量: $RV_TOTALLY_MISSING_VAR"\n', "未定义变量"),
    ("未闭合命令替换", "config.sh",
     '\nBROKEN="$(echo hi"\n', "命令替换"),
    ("关键命令无保护", "03_align.sh",
     "\nfastp -i x -o y\n", "未见失败保护"),
    ("阶段未被调度", None, None, None),
]


class ShellStaticDetectsTests(unittest.TestCase):
    """每类注入的缺陷都必须被检出；真实脚本必须干净。"""

    def setUp(self):
        TMP.mkdir(exist_ok=True)

    def _fresh_copy(self, tmp_path):
        if tmp_path.exists():
            shutil.rmtree(tmp_path)
        tmp_path.mkdir()
        stage_tmp_copy(tmp_path)
        return tmp_path

    def test_the_real_scripts_produce_no_findings(self):
        """基线：未注入时分析器必须干净，否则注入测试没有意义。"""
        with tempfile.TemporaryDirectory(dir=str(TMP)) as tmp:
            tmp_path = self._fresh_copy(Path(tmp))
            result = run_analyzer(tmp_path)
            self.assertEqual(
                0, result.returncode,
                "基线（未注入）应为 0 发现，实际 %d\n%s"
                % (result.returncode, result.stdout[-2000:]))

    def test_each_injected_defect_class_is_detected(self):
        for title, target, injection, expect_text in INJECTIONS:
            with self.subTest(defect=title):
                with tempfile.TemporaryDirectory(dir=str(TMP)) as tmp:
                    tmp_path = self._fresh_copy(Path(tmp))
                    if target is None:
                        (tmp_path / "99_orphan.sh").write_text(
                            "#!/usr/bin/env bash\necho orphan\n", encoding="utf-8")
                    else:
                        path = tmp_path / target
                        path.write_text(
                            path.read_text(encoding="utf-8") + injection,
                            encoding="utf-8")

                    result = run_analyzer(tmp_path)
                    self.assertNotEqual(
                        0, result.returncode,
                        "未检出: %s（分析器退出码为 0）" % title)
                    if expect_text:
                        self.assertIn(
                            expect_text, result.stdout,
                            "检出了 %s，但输出里没有 %r" % (title, expect_text))


if __name__ == "__main__":
    unittest.main()
