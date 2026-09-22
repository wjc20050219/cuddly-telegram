# -*- coding: utf-8 -*-
"""任务清单的「状态口径」必须与表格里的实际标记一致。

这个文件的存在源于一个真实缺陷：清单正文写着「当前项目**没有任何 ✅**」，
而表格里其实已经有 8 项 ✅（整理类任务）。更麻烦的是，**原来那句
话曾经是对的**——在那些任务完成之前，项目确实一项 ✅ 都没有。
一句正确的话随着事实变化变成了错误的话。

所以这里不检查某个固定的数字（那会立刻过期），而是要求**正文与表格互相一致**：
正文声明的各档数量，必须等于按表格逐行统计出来的数量。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_LIST = ROOT / "UNDERGRADUATE_TASK_LIST.md"

DONE = "\u2705"
CODE = "\U0001f536"
TODO = "\u2b1c"

#: 「状态口径」为整理类任务新增的区分。正文必须出现这三个词，
#: 否则读者会把整理类 ✅ 误读成「已有实验数值」。
CLASSIFICATION_WORDS = ("整理类", "实验类")


def parse_rows(text):
    """Return {task_id: status_marker} for every '| TASK-nnn | ... | <marker> |' row."""
    rows = {}
    for line in text.split("\n"):
        m = re.match(r"^\|\s*(TASK-\d+)\s*\|([^|]*)\|([^|]*)\|", line)
        if not m:
            continue
        status = m.group(3)
        for marker in (DONE, CODE, TODO):
            if marker in status:
                rows[m.group(1)] = marker
                break
    return rows


class TaskListStatusCountTests(unittest.TestCase):
    def setUp(self):
        self.text = TASK_LIST.read_text(encoding="utf-8")
        self.rows = parse_rows(self.text)

    def test_the_table_covers_all_48_tasks(self):
        self.assertEqual(48, len(self.rows))
        self.assertEqual("TASK-001", min(self.rows))
        self.assertEqual("TASK-048", max(self.rows))

    def test_every_row_carries_exactly_one_status_marker(self):
        for line in self.text.split("\n"):
            m = re.match(r"^\|\s*(TASK-\d+)\s*\|([^|]*)\|([^|]*)\|", line)
            if not m:
                continue
            found = [k for k, v in (("done", DONE), ("code", CODE), ("todo", TODO))
                     if v in m.group(3)]
            self.assertEqual(1, len(found),
                             "%s 的状态列应恰好有一个标记，实为 %s" % (m.group(1), found))

    def test_stated_done_count_matches_the_table(self):
        """正文说「N 项 ✅」，就必须真的数出 N 项。

        这正是原来那条缺陷：正文写「没有任何 ✅」，表格里却已有 8 项。
        """
        actual = sum(1 for v in self.rows.values() if v == DONE)
        # 正文形如「当前项目有 **8 项 ✅，全部属于整理类**」——数量与标记
        # 之间存在说明文字是可以的，但数量本身必须被明确声明出来。
        m = re.search(r"当前项目有 \*\*(\d+) 项 " + DONE, self.text)
        self.assertIsNotNone(
            m, "正文必须声明 ✅ 的数量（形如「当前项目有 **N 项 ✅**」）")
        self.assertEqual(
            actual, int(m.group(1)),
            "正文说 %s 项 ✅，表格里实际有 %d 项" % (m.group(1), actual))

    def test_stated_lists_exactly_the_done_tasks(self):
        """正文列举的 ✅ 任务号，必须与表格里标 ✅ 的任务号完全一致。"""
        actual = sorted(t for t, v in self.rows.items() if v == DONE)
        block = self.text[self.text.find("当前项目有 **"):]
        block = block[:block.find("\n\n")]
        listed = sorted(set(re.findall(r"(TASK-\d+)", block)))
        self.assertEqual(actual, listed,
                         "正文列举 %s，表格标 ✅ 的是 %s" % (listed, actual))

    def test_no_experimental_task_is_marked_done(self):
        """口径的实质：任何需要真实测量值的任务都不得标 ✅。

        这一条不随数量变化，是保护论文诚信的那一道闸门。
        """
        #: 这些任务的完成定义就是「在真实数据上跑出数值」。
        experimental = {
            "TASK-001",  # 服务器环境调查（需真实服务器信息）
            "TASK-010", "TASK-011", "TASK-012", "TASK-013", "TASK-014",
            "TASK-015", "TASK-016", "TASK-017", "TASK-018", "TASK-019",
            "TASK-020", "TASK-021", "TASK-022", "TASK-023", "TASK-024",
            "TASK-025", "TASK-026", "TASK-027", "TASK-028", "TASK-029",
            "TASK-030", "TASK-031", "TASK-032", "TASK-033", "TASK-034",
            "TASK-035", "TASK-036", "TASK-037", "TASK-038", "TASK-039",
            "TASK-040", "TASK-041", "TASK-042", "TASK-043", "TASK-044",
            "TASK-045", "TASK-046",
        }
        wrongly = sorted(t for t in experimental if self.rows.get(t) == DONE)
        self.assertEqual(
            [], wrongly,
            "这些任务需要真实数据或服务器执行，不得标 ✅：%s" % wrongly)

    def test_status_legend_distinguishes_curation_from_experiment(self):
        """口径若不分「整理类/实验类」，读者会把整理类 ✅ 当成实验数值。"""
        legend = self.text[self.text.find("## 状态口径"):]
        self.assertTrue(legend)
        for word in CLASSIFICATION_WORDS:
            self.assertIn(word, legend, "状态口径缺少「%s」的区分" % word)

    def test_the_false_universal_statement_is_gone(self):
        """「没有任何 ✅」在整理类任务完成后就是假话，不应再出现。"""
        self.assertNotIn("当前项目**没有任何 ✅**", self.text)
        self.assertIn("没有任何 ✅ 级实验任务", self.text)


if __name__ == "__main__":
    unittest.main()
