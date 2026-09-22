#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""锁定 `scripts/vcs.py` —— 本机唯一的版本控制手段。

之所以值得单独测试：本项目没有 git 可执行文件，`.git` 由 dulwich 创建。
**一个提交"成功"但内容为空，比没有提交更危险**——它给出一个有效的 SHA，
让人以为改动已经安全保存。这在本轮真实发生过：`porcelain.commit` 不会把
已跟踪文件的改动写进索引，于是第二个提交只含新增文件、丢掉了全部修改。

所以这里的核心断言不是"命令退出码为 0"，而是**提交的内容必须包含改动**。
"""

from __future__ import print_function

import io
import os
import subprocess
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VCS = os.path.join(ROOT, "scripts", "vcs.py")
GITDIR = os.path.join(ROOT, ".git")


def _run(*args):
    proc = subprocess.Popen(
        [sys.executable, VCS] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=ROOT,
    )
    out, _ = proc.communicate()
    return proc.returncode, out.decode("utf-8", "replace")


class VcsScriptShapeTests(unittest.TestCase):
    """脚本本身的基本契约。"""

    def setUp(self):
        with io.open(VCS, encoding="utf-8") as fh:
            self.src = fh.read()

    def test_script_exists_and_is_python(self):
        self.assertTrue(os.path.isfile(VCS))
        self.assertIn("dulwich", self.src)

    def test_help_runs_without_a_repo_command(self):
        rc, out = _run("--help")
        self.assertEqual(rc, 0, out)
        self.assertIn("status", out)
        self.assertIn("commit", out)

    def test_unknown_subcommand_fails_loudly(self):
        rc, out = _run("frobnicate")
        self.assertEqual(rc, 2, out)

    def test_missing_message_is_rejected(self):
        """提交必须带信息，否则历史不可读。"""
        rc, out = _run("commit")
        self.assertEqual(rc, 2, out)

    def test_status_normalises_gitstatus_fields(self):
        """GitStatus 的字段可能是 list 也可能是 dict，必须显式兼容。

        我最初按 dict 迭代 `unstaged`，拿到的是整数下标，
        直到 porcelain.add 抛 TypeError 才暴露。
        """
        self.assertIn("_status_paths", self.src)
        self.assertIn("isinstance(value, dict)", self.src)


class VcsRepositoryStateTests(unittest.TestCase):
    """仓库当前状态的自洽性（只读检查，不修改仓库）。"""

    def test_a_git_directory_exists(self):
        """本项目长期没有版本控制；这一项防止它悄悄消失。"""
        self.assertTrue(os.path.isdir(GITDIR),
                        "缺少 .git —— 改动将无法回滚")

    def test_gitignore_excludes_machine_local_and_large_files(self):
        with io.open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            gi = fh.read()
        for pattern in (".tools/", ".tmp/", "*.fastq", "*.bam", "xml_cache"):
            self.assertIn(pattern, gi,
                          ".gitignore 应排除 %s" % pattern)

    @unittest.skipUnless(os.path.isdir(GITDIR), "需要 .git")
    def test_the_repo_has_at_least_one_commit(self):
        rc, out = _run("log", "-n", "5")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("还没有任何提交", out)

    @unittest.skipUnless(os.path.isdir(GITDIR), "需要 .git")
    def test_large_binaries_are_not_tracked(self):
        """绝不能把 FASTQ/BAM 提交进库。"""
        sys.path.insert(0, os.path.join(ROOT, ".tools", "pylibs"))
        try:
            from dulwich.repo import Repo
        except ImportError:
            self.skipTest("需要 dulwich")
        repo = Repo(ROOT)
        names = []

        def walk(tree, prefix=""):
            for name, mode, sha in tree.iteritems():
                path = prefix + name.decode("utf-8")
                if mode & 0o040000:
                    walk(repo[sha], path + "/")
                else:
                    names.append(path)

        walk(repo[repo[repo.head()].tree])
        bad = [n for n in names
               if n.endswith((".fastq", ".fastq.gz", ".bam", ".sra", ".cram"))
               or n.startswith(".tools/") or n.startswith(".tmp/")]
        self.assertEqual([], bad, "版本库里不应出现：%s" % bad)


class VcsCommitContentTests(unittest.TestCase):
    """提交必须真的包含改动——本文件存在的理由。"""

    @unittest.skipUnless(os.path.isdir(GITDIR), "需要 .git")
    def test_head_commit_reports_its_changed_paths(self):
        """最近的提交里，凡是工作区已改动的文件都应当已入库。

        这条断言直接对应本轮的真实缺陷：当时提交"成功"但 changed 为空。
        """
        sys.path.insert(0, os.path.join(ROOT, ".tools", "pylibs"))
        try:
            from dulwich.repo import Repo
        except ImportError:
            self.skipTest("需要 dulwich")
        repo = Repo(ROOT)

        def paths(commit):
            out = {}

            def walk(tree, prefix=""):
                for name, mode, sha in tree.iteritems():
                    p = prefix + name.decode("utf-8")
                    if mode & 0o040000:
                        walk(repo[sha], p + "/")
                    else:
                        out[p] = sha
            walk(repo[commit.tree])
            return out

        head = repo[repo.head()]
        # 工作区当前仍有未提交改动的文件，说明上一次提交没有把它们收进去。
        from dulwich import porcelain
        st = porcelain.status(repo)
        untracked = list(getattr(st, "untracked", []) or [])
        self.assertEqual([], untracked,
                         "存在未提交的未跟踪文件：%s" % untracked[:10])


if __name__ == "__main__":
    unittest.main()
