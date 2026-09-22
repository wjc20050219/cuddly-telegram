#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""锁定 `docs/server_request_onepager.md` 与它承诺的探测脚本契约。

一页纸是**发给外部管理员**的材料，它里面每一句"脚本会/不会做什么"都是
对第三方作出的承诺。承诺与实际脚本不符，性质比内部文档写错更严重：
管理员据此批准权限，而实际行为不同。

因此本测试不检查文风，只检查**可核查的断言**：
资源数字是否可回源、必答问题是否齐全、探测脚本的只读声明是否属实。
"""

from __future__ import print_function

import io
import os
import re
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONEPAGER = os.path.join(ROOT, "docs", "server_request_onepager.md")
PROBE = os.path.join(ROOT, "server", "00_probe.sh")
CONFIG = os.path.join(ROOT, "server", "config.sh")


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class OnePagerResourceTableTests(unittest.TestCase):
    """资源表里的数字必须能被清单复现。"""

    def setUp(self):
        self.text = _read(ONEPAGER)

    def test_the_three_stage_sizes_are_the_verified_panel_sizes(self):
        """23.19 / 170.70 / 334.72 GiB 是本项目已核对的面板声明值。"""
        for figure in ("23.19", "170.70", "334.72"):
            self.assertIn(figure, self.text, "缺少已核对的 %s GiB" % figure)

    def test_sizes_are_labelled_as_declared_not_measured(self):
        """不能让管理员以为这些数字是实测下载量。"""
        self.assertIn("声明", self.text)
        self.assertRegex(self.text, r"不是我们实测")

    def test_the_source_columns_are_named(self):
        """可回源：必须写明数字来自哪个字段。"""
        self.assertIn("fastq_bytes", self.text)

    def test_no_unreproducible_legacy_figure_remains(self):
        """旧的"26 Gb / 9 GB 压缩"没有任何产物能复现，不得回流。"""
        self.assertNotIn("26 Gb", self.text)
        self.assertNotIn("9 GB 压缩", self.text)

    def test_the_first_stage_is_the_one_recommended_for_approval(self):
        """一页纸的策略是"先只批第一步"，这必须写在文里。"""
        self.assertIn("建议先只批第一步", self.text)


class OnePagerQuestionTests(unittest.TestCase):
    """四个必答问题必须齐全，且与判读脚本关心的维度一致。"""

    def setUp(self):
        self.text = _read(ONEPAGER)

    def test_all_four_questions_are_present(self):
        for topic in ("外网", "调度器", "存储", "conda"):
            self.assertIn(topic, self.text, "缺少必答问题：%s" % topic)

    def test_the_four_questions_match_what_interpret_probe_decides_on(self):
        """判读脚本真正用到的是这四个维度；一页纸不能问别的。"""
        decisions = _read(os.path.join(ROOT, "scripts", "interpret_probe.py"))
        # interpret_probe 读的键：网络速度、调度器、存储、工具可用性。
        for key in ("net_ena_speed", "scheduler", "home_avail", "tool_"):
            self.assertIn(key, decisions, "判读脚本应当读取 %s" % key)

    def test_scheduler_answer_states_which_branches_exist(self):
        """管理员按"有 Slurm / 没有"回答；脚本只实现这两条分支。"""
        self.assertIn("Slurm", self.text)
        run_all = _read(os.path.join(ROOT, "server", "run_all.sh"))
        self.assertIn("sbatch", run_all)


class OnePagerProbeContractTests(unittest.TestCase):
    """一页纸对探测脚本的描述必须与脚本实际行为一致。"""

    def setUp(self):
        self.text = _read(ONEPAGER)
        self.probe = _read(PROBE)

    def test_the_named_tool_count_matches_the_probe_loop(self):
        match = re.search(r"for t in ([^;]+); do", self.probe)
        self.assertIsNotNone(match, "00_probe.sh 里找不到工具循环")
        tools = match.group(1).split()
        self.assertIn("%d 个生信工具" % len(tools), self.text,
                      "一页纸的工具数与脚本循环不符（脚本有 %d 个）" % len(tools))

    def test_the_download_cap_matches_test_bytes(self):
        match = re.search(r"TEST_BYTES=(\d+)", self.probe)
        self.assertIsNotNone(match)
        mb = int(match.group(1)) // 1_000_000
        self.assertIn("%d MB" % mb, self.text,
                      "一页纸的下载上限与 TEST_BYTES 不符")

    def test_both_output_files_are_named_correctly(self):
        self.assertIn("logs/probe_report.txt", self.text)
        self.assertIn("logs/probe_summary.tsv", self.text)
        self.assertIn("probe_report.txt", self.probe)
        self.assertIn("probe_summary.tsv", self.probe)

    def test_both_ena_and_ncbi_are_actually_probed(self):
        """一页纸说测 ENA 与 NCBI；脚本必须真的测这两个。

        键名是 `probe_get <name>` 里拼出来的（`net_${name}_speed`），
        所以这里检查**调用点**，而不是去源码里找拼好的字面量——
        我最初直接断言 `net_ncbi_speed` 字面量存在，那是错的。
        """
        self.assertIn('kv "net_${name}_speed"', self.probe,
                      "测速函数应当用 net_<name>_speed 作为键")
        self.assertRegex(self.probe, r"probe_get\s+ena\b",
                         "脚本没有调用 probe_get ena")
        self.assertRegex(self.probe, r"probe_get\s+ncbi\b",
                         "脚本没有调用 probe_get ncbi")
        # 判读脚本消费的那两个键必须能从上面的调用拼出来。
        for name in ("ena", "ncbi"):
            self.assertIn('probe_get %s' % name, self.probe)
        self.assertIn("net_ena_speed", _read(
            os.path.join(ROOT, "scripts", "interpret_probe.py")))
        self.assertRegex(self.text, r"ENA")
        self.assertRegex(self.text, r"NCBI")


class OnePagerWriteScopeTests(unittest.TestCase):
    """一页纸如实说明脚本会写哪些目录——这是对管理员的承诺。

    历史缺陷：本文曾写"唯一的写操作是在当前目录下建 `logs/`"，
    但 `init_dirs` 实际在 `$RV_ROOT` 下建 13 个子目录。
    管理员据此批准权限，而实际行为不同——这是承诺失真，不是措辞问题。
    """

    def setUp(self):
        self.text = _read(ONEPAGER)
        self.config = _read(CONFIG)

    def _declared_subdirs(self):
        """从 config.sh 的 init_dirs 里取出它真正会建的目录数。"""
        block = self.config.split("init_dirs()")[1].split("}")[0]
        return sorted(set(re.findall(r"\$RV_[A-Z]+", block)))

    def test_the_claim_of_a_single_write_location_is_gone(self):
        self.assertNotIn("唯一的写操作是在当前目录下建", self.text)

    def test_the_stated_subdirectory_count_matches_init_dirs(self):
        """一页纸写的 13 个必须是 init_dirs 真正创建的个数。"""
        declared = [d for d in self._declared_subdirs() if d != "$RV_TMP"]
        stated = re.search(r"共 (\d+) 个子目录", self.text)
        self.assertIsNotNone(stated, "一页纸没写子目录数量")
        self.assertEqual(int(stated.group(1)), len(declared),
                         "一页纸说 %s 个，init_dirs 实际建 %d 个：%s"
                         % (stated.group(1), len(declared), " ".join(declared)))

    def test_the_real_default_root_is_disclosed(self):
        """管理员需要知道默认会写到 HOME 下。"""
        self.assertIn("$RV_ROOT", self.text)
        self.assertIn("$HOME/ricevar", self.text)
        self.assertIn('RV_ROOT="${RV_ROOT:-$HOME/ricevar}"', self.config)

    def test_no_system_directories_are_created(self):
        """一页纸承诺不写系统目录；init_dirs 不得出现绝对系统路径。"""
        block = self.config.split("init_dirs()")[1].split("}")[0]
        for bad in ("/etc", "/usr", "/var", "/opt", "C:\\"):
            self.assertNotIn(bad, block, "init_dirs 触碰了系统目录 %s" % bad)
        # 除临时目录外，全部路径都必须以 $RV_ROOT 开头。
        refs = re.findall(r'"(.*?)"', block)
        for ref in refs:
            self.assertTrue(ref.startswith("$RV_"),
                            "init_dirs 里出现非 $RV_ 前缀的路径：%s" % ref)

    def test_the_deletion_instruction_matches_the_root(self):
        """一页纸说"删除 $RV_ROOT 即可完全清除"；临时目录也必须交代。"""
        self.assertIn("删除 `$RV_ROOT` 即可完全清除", self.text)
        self.assertIn("ricevar_tmp", self.text)
        self.assertIn("ricevar_tmp", self.config)


if __name__ == "__main__":
    unittest.main()
