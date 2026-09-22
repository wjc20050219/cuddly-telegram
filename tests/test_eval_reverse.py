#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""反向验证评估层的两条回归测试确实检出了原缺陷。

做法：把**原始有缺陷的表达式**还原到仓库脚本的一个副本里，
确认新测试会失败。这证明测试是在检测真实缺陷，
而不是仅仅在修好后的代码上通过。

**为什么要重写成本文件**：它原名就匹配 `test_*.py`，却是一个模块级脚本。
`unittest discover` 会 **import** 它——真的执行子进程、往 `.tmp/` 写文件——
然后收集到 **0 个测试用例**，把全部判定 `print` 掉。更严重的是它
**从不调用 `sys.exit`**：即使反向验证失败，文件退出码仍是 0。
`verify_undergraduate_scope.py` 却引用它作为"已证明能检出缺陷"的证据——
而那条证据只检查文件**存在**。

现在它是真正的 unittest 模块，失败会导致套件变红。
"""

from __future__ import print_function

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp"
SCRIPT = ROOT / "scripts" / "evaluate_identification.py"
MARKERS = ["chr1:100:A:G", "chr1:200:A:G", "chr1:300:A:G", "chr1:400:A:G"]

# 修复前的两个表达式（未标注样本会被算成"未命中"，稀释准确率）。
BUGGY_OLD_TOP1 = ('row["top1_correct_variety"] = '
                  'bool(true_variety and row["top1_variety"] == true_variety)')
BUGGY_OLD_TOP5 = ('row["top5_correct_variety"] = '
                  'bool(true_variety and true_variety in top5)')

FIXED_BLOCK = """            if true_variety:
                row["top1_correct_variety"] = bool(row["top1_variety"] == true_variety)
                top5 = [truth.get(entry) for entry in str(row["top_k_ids"]).split(";") if entry]
                row["top5_correct_variety"] = bool(true_variety in top5)
            else:
                row["top1_correct_variety"] = None
                row["top5_correct_variety"] = None"""


def make_env(td):
    matrix = td / "ref.genotypes_4.tsv"
    rows = [
        ["sample_id"] + MARKERS,
        ["V1", "0", "0", "1", "1"],
        ["V2", "2", "2", "0", "1"],
        ["V4", "1", "1", "1", "2"],
    ]
    with matrix.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)
    truth = td / "truth.tsv"
    with truth.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["sample_id", "variety_name"])
        w.writerow(["V1", "variety_one"])
        w.writerow(["V2", ""])              # 未标注
        w.writerow(["V4", "variety_four"])

    def write_vcf(path, sample, gt):
        lines = ["##fileformat=VCFv4.2\n",
                 "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t%s\n" % sample]
        for m, d in zip(MARKERS, gt):
            chrom, pos, ref, alt = m.split(":")
            g = {0: "0/0", 1: "0/1", 2: "1/1"}[int(d)]
            lines.append("%s\t%s\t.\t%s\t%s\t60\tPASS\t.\tGT:DP:GQ\t%s:10:50\n"
                         % (chrom, pos, ref, alt, g))
        path.write_text("".join(lines), encoding="utf-8")

    d = td / "d1.00_r1"
    d.mkdir()
    queries = []
    for i, (s, gt) in enumerate((("V1", rows[1][1:]), ("V2", rows[2][1:]),
                                 ("V4", rows[3][1:])), 1):
        p = d / ("q%d.vcf" % i)
        write_vcf(p, s, gt)
        queries.append("%s=%s" % (s, p))
    return matrix, truth, queries


def build_reverted_copy(dest):
    """还原原始缺陷表达式并移除新守卫，写出一份副本。"""
    original_src = SCRIPT.read_text(encoding="utf-8")

    reverted = original_src.replace(
        FIXED_BLOCK,
        """            row["top1_correct_variety"] = %s
            top5 = [truth.get(entry) for entry in str(row["top_k_ids"]).split(";") if entry]
            row["top5_correct_variety"] = %s"""
        % ('bool(true_variety and row["top1_variety"] == true_variety)',
           'bool(true_variety and true_variety in top5)'))

    # 只移除"id 空间不匹配"守卫。
    # 早先的版本从守卫注释一直删到 "depths: Dict"，那个区间**顺带吞掉了**
    # 定义在 summarize 顶部的 `by_depth = defaultdict(list)`，
    # 于是副本以 NameError 崩溃、而不是表现出真实缺陷，
    # 反向验证便错误地记为"未检出"。
    guard_start = reverted.find("    # A truth table that matches none of the reference ids")
    guard_end = reverted.find("    fields = [")
    assert guard_start != -1 and guard_end != -1, "guard block not found"
    assert guard_start < guard_end, "guard block span is inverted"
    removed = reverted[guard_start:guard_end]
    assert "labelled == 0" in removed, "removal span missed the guard: %r" % removed[:200]
    assert "by_depth = defaultdict" not in removed, \
        "removal span would delete by_depth initialization"
    reverted = reverted[:guard_start] + reverted[guard_end:]

    assert reverted != original_src, "revert produced no change"
    dest.write_text(reverted, encoding="utf-8")
    return dest


def run_buggy(buggy, matrix, queries, truth_path, out_name, td):
    """在**已经建好**的输入目录上运行缺陷副本。

    输入只建一次：`make_env` 会创建 `d1.00_r1/`，重复调用会
    以 `FileExistsError` 失败——那是测试自身的 bug，会被误读成
    "缺陷副本行为异常"。
    """
    out = td / out_name
    cmd = [sys.executable, str(buggy), "--reference-matrix", str(matrix),
           "--query-vcf"] + queries + ["--truth", str(truth_path),
           "--out-dir", str(out), "--min-compared", "1", "--top-k", "3"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r, out


class EvalReverseTests(unittest.TestCase):
    """还原原缺陷后，评估层的两条新测试必须能够失败。"""

    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        # 副本必须**直接**放在 `.tmp/` 下，而不是嵌套的临时目录里：
        # 脚本用 `Path(__file__).resolve().parents[1] / "src"` 找到包，
        # 嵌套一层之后 parents[1] 就不是仓库根，会以
        # `ModuleNotFoundError: No module named 'ricevar_id'` 崩溃——
        # 那是"副本坏了"，而不是"缺陷被检出"，反向验证会得出错误结论。
        cls.buggy = TMP / "evaluate_buggy.py"
        build_reverted_copy(cls.buggy)

    @classmethod
    def tearDownClass(cls):
        if cls.buggy.exists():
            cls.buggy.unlink()

    def setUp(self):
        # 每个用例都在同一路径重建副本，避免残留影响。
        TMP.mkdir(exist_ok=True)
        build_reverted_copy(self.buggy)

    def test_the_reverted_copy_actually_differs_from_the_fixed_script(self):
        """反向验证的前提：副本确实被改动了。"""
        self.assertIn("bool(true_variety and",
                      self.buggy.read_text(encoding="utf-8"))
        self.assertNotEqual(SCRIPT.read_text(encoding="utf-8"),
                            self.buggy.read_text(encoding="utf-8"))

    def test_unlabelled_query_must_not_dilute_accuracy(self):
        """缺陷版会把未标注样本算成未命中，准确率降到 1.0 以下。

        这正是新测试要抓住的行为：修复后未标注样本记 `None`，
        不进入分母。
        """
        with tempfile.TemporaryDirectory(dir=str(TMP)) as td:
            td = Path(td)
            matrix, truth, queries = make_env(td)
            r, out = run_buggy(self.buggy, matrix, queries, truth, "out", td)
            self.assertEqual(0, r.returncode,
                             "缺陷副本应当正常退出：%s" % r.stderr[-300:])
            s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            acc = s["by_depth"]["1.00"]["top1_variety_accuracy"]
            self.assertNotEqual(1.0, acc,
                                "缺陷版本应把未标注样本算进分母而降低准确率")

    def test_mismatched_id_space_must_not_silently_succeed(self):
        """缺陷版在真值表与参考 id 完全不相交时仍会写出 summary。

        修复后这种情况必须被拒绝，而不是给出一个看似正常的空结果。
        """
        with tempfile.TemporaryDirectory(dir=str(TMP)) as td:
            td = Path(td)
            matrix, _truth, queries = make_env(td)
            bad_truth = td / "bad.tsv"
            with bad_truth.open("w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh, delimiter="\t", lineterminator="\n")
                w.writerow(["sample_id", "variety_name"])
                w.writerow(["NOPE", "variety_one"])
            r, out = run_buggy(self.buggy, matrix, queries, bad_truth, "out2", td)
            self.assertEqual(0, r.returncode)
            self.assertTrue((out / "summary.json").exists(),
                            "缺陷版本应静默写出 summary")


if __name__ == "__main__":
    unittest.main()
