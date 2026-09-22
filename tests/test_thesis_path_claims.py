# -*- coding: utf-8 -*-
"""论文正文与附录里引用的**仓库内路径**必须真实存在。

这个文件源于第二十一轮的一个真实缺陷：我在第 5 章的填写协议表里
写下 `data/metadata/panels/pilot_manifest.tsv`，而该目录**从不存在**
（两个面板清单实际在 `data/metadata/server/` 下）。

论文引用一个不存在的路径，后果是读者**按图索骥找不到数据**——
这与"引用了不存在的图"是同一类缺陷，只是更隐蔽，
因为一个像模像样的路径看起来远比一个图名可信。

设计取舍：
  * 只检查以仓库内真实存在的顶层目录开头的路径（data/ docs/ scripts/ ...），
    `analysis/`、`figures/` 等**服务器产出目录**在实验运行前本就不存在，
    引用了它们是正确的，不算缺陷；
  * 少数**故意**引用的不存在路径（如附录 D 描述缺陷时引用的路径）
    必须逐条登记在 `EXPECTED_ABSENT` 里并写明理由——
    这样豁免是**显式且封闭**的：新增一个不存在的路径就会失败，
    逼人做出"要么改路径、要么登记理由"的决定。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THESIS = ROOT / "docs" / "thesis"

#: 这些顶层目录在本仓库里真实存在，引用了就必须找得到。
LOCAL_ROOTS = ("data/", "docs/", "scripts/", "src/", "server/", "tests/", "app/")

#: `analysis/`、`figures/`、`markers/` 等是**服务器运行后**才产生的产物目录，
#: 实验尚未执行，因此引用它们是正确行为，不检查存在性。
SERVER_ROOTS = ("analysis/", "figures/", "markers/", "joint/", "depth/",
                "qc/", "reference/", "logs/", "sim/", "vcf/")

#: 反引号里的"看起来像仓库路径"的串：至少含一个 `/`，且不由 $ / ~ 开头。
PATH_RE = re.compile(r"`([A-Za-z0-9_][\w.-]*(?:/[\w.-]+)+)`")

#: 明确允许引用的不存在路径，逐条给出理由。**新增条目必须写明理由**，
#: 否则豁免就会变成"把失败的测试登记掉"。
#:
#: 键是 `(文件名, 路径)` 而不是单纯路径——这一点是被我自己的一次错误逼出来的：
#: 我最初只按路径豁免，于是为了给附录 D.18 记录"第 5 章曾写错这个路径"
#: 而豁免 `data/metadata/panels/pilot_manifest.tsv` 之后，
#: **同一个豁免把 THESIS_DRAFT 里的真实错误也一并放行了**——
#: 守卫再也抓不到它本来要抓的那个缺陷。
#: 豁免必须精确到"哪个文件、哪条路径"，否则一次合法的豁免会静默地
#: 扩大成对整个仓库的放行。
EXPECTED_ABSENT = {
    ("APPENDIX_D_verification.md", "data/metadata/download_log.tsv"): (
        "附录 D 第 11 项**描述的就是这个缺陷**：README 曾引用这个不存在的路径。"
        "这里引用它是为了记录缺陷本身。"),
    ("APPENDIX_D_verification.md", "server/x.tsv"): (
        "附录 D 举例说明「输入文件缺失时报表该如何显示」所用的假想文件名。"),
    ("APPENDIX_D_verification.md", "data/metadata/server/x.tsv"): (
        "同上：附录 D 说明路径解析时用的假想文件。"),
    ("PLACEHOLDER_CONVENTIONS.md", "scripts/xxx.py"): (
        "`PLACEHOLDER_CONVENTIONS.md` 用 `xxx.py` 演示占位符命名约定。"),
    ("APPENDIX_D_verification.md", "data/metadata/panels/pilot_manifest.tsv"): (
        "附录 D.18 **描述的就是这个缺陷本身**：第 5 章曾引用这个不存在的路径。"
        "这里引用它是为了记录错误路径的样子。"),
}


class ThesisPathClaimsResolveTests(unittest.TestCase):
    def setUp(self):
        self.files = sorted(THESIS.glob("*.md"))
        self.assertTrue(self.files, "docs/thesis 下应有 markdown 文件")

    def _claims(self):
        """Yield (filename, lineno, path) for every repo-local path claim."""
        for f in self.files:
            for lineno, line in enumerate(
                    f.read_text(encoding="utf-8").split("\n"), 1):
                for m in PATH_RE.finditer(line):
                    path = m.group(1)
                    if path.startswith(LOCAL_ROOTS):
                        yield f.name, lineno, path

    def test_every_local_path_claim_exists(self):
        missing = []
        for name, lineno, path in self._claims():
            if (ROOT / path).exists():
                continue
            if (name, path) in EXPECTED_ABSENT:
                continue
            missing.append("%s:%d %s" % (name, lineno, path))
        self.assertEqual(
            [], missing,
            "论文引用了仓库内不存在的路径（读者将找不到对应文件）：\n  "
            + "\n  ".join(missing))

    def test_expected_absent_entries_all_carry_a_reason(self):
        """豁免必须写明理由，否则它就是"把失败的测试登记掉"。"""
        for key, reason in EXPECTED_ABSENT.items():
            self.assertTrue(reason.strip(), "%s 的豁免理由为空" % (key,))
            self.assertGreater(len(reason), 10,
                               "%s 的豁免理由过于简短，等于没写" % (key,))

    def test_expected_absent_entries_are_actually_used(self):
        """一个从未被引用的豁免条目会掩盖真实的路径错误。

        如果某条豁免不再出现在论文里，它应当被删除——
        否则它会永远豁免一个已经不需要豁免的路径。
        """
        used = {(n, p) for n, _, p in self._claims()}
        unused = sorted(set(EXPECTED_ABSENT) - used)
        self.assertEqual(
            [], unused,
            "以下豁免条目在论文中已不再出现，应删除以免掩盖将来的真实错误：%s"
            % unused)

    def test_expected_absent_entries_really_do_not_exist(self):
        """如果某个"豁免"的路径后来真的存在了，豁免就必须撤销。"""
        for _, path in EXPECTED_ABSENT:
            self.assertFalse(
                (ROOT / path).exists(),
                "%s 现在已存在，应把它从 EXPECTED_ABSENT 中删除" % path)

    def test_an_exemption_is_scoped_to_one_file(self):
        """豁免必须精确到文件，否则一次合法豁免会放行整个仓库。

        这是我修本轮缺陷时踩到的坑：为了让附录 D.18 能记录
        "第 5 章曾写错 `data/metadata/panels/pilot_manifest.tsv`"，
        我按**路径**做了豁免，结果把 THESIS_DRAFT 里的同一个错误也放行了。
        """
        exempted = {p for _, p in EXPECTED_ABSENT}
        for path in exempted:
            in_draft = (ROOT / "docs" / "thesis" / "THESIS_DRAFT.md").read_text(
                encoding="utf-8")
            if path in in_draft:
                # 只有当 THESIS_DRAFT 里出现该路径是**有理由**的时候才允许，
                # 目前没有任何一条属于这种情况。
                self.fail(
                    "THESIS_DRAFT.md 中出现了被豁免的路径 %s；"
                    "豁免只针对记录该缺陷的附录，正文引用必须真实存在" % path)

    def test_server_output_paths_are_not_treated_as_errors(self):
        """确保服务器产出目录确实被排除，否则实验前的论文永远无法通过守卫。"""
        for root in SERVER_ROOTS:
            self.assertFalse(root.startswith(LOCAL_ROOTS),
                             "%s 不应同时被视为本地路径" % root)
        for root in LOCAL_ROOTS:
            self.assertFalse(root.startswith(SERVER_ROOTS),
                             "%s 不应同时被视为服务器产出路径" % root)


if __name__ == "__main__":
    unittest.main()
