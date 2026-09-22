#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""服务器脚本与源码不得含 CRLF 行尾；`.gitattributes` 必须持续约束它们。

**这个缺陷真实发生过**：`server/00_probe.sh` 与 `server/02_download.sh`
在工作区里是 CRLF。这两个文件要被上传到 Linux 执行：

    #!/usr/bin/env bash\\r     -> bad interpreter（解释器名字带上 \\r）
    for d in ...; do\\r        -> $'\\r': command not found

也就是说脚本**根本跑不起来**。而 `00_probe.sh` 正是
`docs/server_request_onepager.md` 请求管理员**第一个执行**的脚本——
这个缺陷会在流程的第一步、在别人机器上、以看不懂的语法错误形式出现。

本地之所以一直没发现：Windows 上没有任何可用的 shell
（WSL 被拒、无 git-bash、无 sh），所以"脚本能跑"这件事从未被本地验证过。
静态检查是这里唯一可行的防线。
"""

from __future__ import print_function

import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 这些扩展名会被 Linux 直接解释或导入；CRLF 会让它们失败或产生噪声。
LINUX_CRITICAL = (".sh", ".py")


def _walk():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".tools", ".tmp", "xml_cache",
                                    "__pycache__", ".mypy_cache", "node_modules")]
        for name in filenames:
            yield os.path.join(dirpath, name)


class NoCrlfInLinuxCriticalFilesTests(unittest.TestCase):

    def test_shell_and_python_files_use_lf_only(self):
        offenders = []
        for path in _walk():
            if not path.endswith(LINUX_CRITICAL):
                continue
            with open(path, "rb") as fh:
                data = fh.read()
            if b"\r\n" in data:
                offenders.append((os.path.relpath(path, ROOT).replace("\\", "/"),
                                  data.count(b"\r\n")))
        self.assertEqual(
            [], offenders,
            "以下文件含 CRLF，在 Linux 上会语法失败：%s" % offenders)

    def test_the_probe_script_shebang_is_clean(self):
        """单独点名 `00_probe.sh`：它是管理员执行的第一个脚本。"""
        path = os.path.join(ROOT, "server", "00_probe.sh")
        with open(path, "rb") as fh:
            first = fh.readline()
        self.assertEqual(b"#!/usr/bin/env bash\n", first,
                         "00_probe.sh 的 shebang 不含裸 LF：%r" % first)

    def test_the_download_script_shebang_is_clean(self):
        path = os.path.join(ROOT, "server", "02_download.sh")
        with open(path, "rb") as fh:
            first = fh.readline()
        self.assertEqual(b"#!/usr/bin/env bash\n", first,
                         "02_download.sh 的 shebang 不含裸 LF：%r" % first)

    def test_gitattributes_forces_lf_for_shell_scripts(self):
        """没有 .gitattributes，CRLF 会在下一次编辑时悄悄回来。"""
        path = os.path.join(ROOT, ".gitattributes")
        self.assertTrue(os.path.exists(path),
                        "缺少 .gitattributes，无法阻止 CRLF 回归")
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8")
        self.assertIn("*.sh", text)
        self.assertIn("eol=lf", text)
        self.assertIn("*.py", text)

    def test_gitattributes_itself_is_lf(self):
        with open(os.path.join(ROOT, ".gitattributes"), "rb") as fh:
            self.assertNotIn(b"\r\n", fh.read())


if __name__ == "__main__":
    unittest.main()
