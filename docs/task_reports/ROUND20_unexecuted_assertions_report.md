# 第二十轮报告：从未被执行的断言

**日期**：2026-09-21
**范围**：本科论文主线（C 规格 TASK-001~048），本轮不涉及新实验
**状态**：🔶 代码与文档工作完成；**无任何真实实验数据**

---

## 1. 本轮为什么开始查这件事

本轮起点是一件很小的收尾工作：把附录 D 里"467 项通过"更新成最新数字。

为了核对这个数字，我写了一个脚本，逐个 `test_*.py` 文件调用
`unittest.TestLoader().discover(..., pattern=文件名)` 统计用例数。
结果脚本的输出里混进了不属于它的内容：

```
reverted copy written: evaluate_buggy.py
  [OK] unlabelled dilution      buggy accuracy=0.667 (test expects 1.0)
  [!!] doc.md:1 文档使用了脚本不支持的参数：--old-flag
```

这些行来自 `tests/test_eval_reverse.py`——它在**被 import 时**就执行了
子进程、往 `.tmp/` 写了文件。而统计结果说它贡献 **0 个测试用例**。

顺着这条线查下去，发现了一个此前从未被发现的缺陷类别。

---

## 2. 缺陷：三个"反向验证"文件贡献 0 个测试用例（第 24 项）

`tests/` 下有三个文件名匹配 `test_*.py`，内容却是**模块级脚本**：

| 文件 | 用途 | 实际贡献的用例数 |
| --- | --- | --- |
| `test_shell_static_detects.py` | 注入 shell 缺陷，验证静态分析器能检出 | 0 |
| `test_selector_invariants_reverse.py` | 变异 `select_snp_markers`，验证不变量测试有效 | 0 |
| `test_eval_reverse.py` | 还原原始缺陷表达式，验证评估层测试有效 | 0 |

`unittest discover` 对它们的处理是：**import**（于是真的执行子进程、
往 `.tmp/` 写文件），然后收集到 **0 个用例**。
所有判定只 `print` 而从不 `assert`，失败**被彻底丢弃**，套件照样打印 `OK`。

`test_eval_reverse.py` 更彻底：它连 `sys.exit` 都没有，
即使反向验证失败，**文件退出码仍是 0**。

### 2.1 为什么这个缺陷特别有欺骗性

正常的测试套件**确实会执行**这些脚本，所以运行输出里能看到 `[OK] ...` 行。
这让人以为"它们在跑、而且通过了"。

实际上那些 `[OK]` 是**打印出来的**，不是**断言出来的**。
两者的区别在失败时才会显现——而失败从不会显现。

### 2.2 更糟的是：一个校验脚本把它当作证据

`scripts/verify_undergraduate_scope.py` 原文：

```python
check((ROOT / "tests" / "test_shell_static_detects.py").exists(),
      "analyzer has a reverse test proving it detects injected defects")
```

条件只检查文件**存在**，断言却说"**证明**能检出缺陷"。
断言强度远超证据强度——这是一条**永远为真**的检查。

**修复后**：

```
[OK] analyzer has a reverse test proving it detects injected defects
     (test_shell_static_detects.py=2, test_selector_invariants_reverse.py=8,
      test_eval_reverse.py=3)
```

---

## 3. 缺陷：服务器脚本含 CRLF，在 Linux 上无法执行（第 21 项）

核对提交内容时，我写脚本比对工作区与 HEAD 的字节差。
`server/00_probe.sh` 报告"已修改"，但**解码后的行完全相同**——
差异在字节层面：**CRLF**。

```
HEAD blob : 5904 bytes, CRLF = 0
worktree  : 6025 bytes, CRLF = 121
```

首行字节是 `b'#!/usr/bin/env bash\r'`。

在 Linux 上这意味着：

```
#!/usr/bin/env bash\r     -> bad interpreter（解释器名字带上 \r）
for d in ...; do\r        -> $'\r': command not found
```

**脚本根本跑不起来。** 而 `00_probe.sh` 正是
`docs/server_request_onepager.md` 请求管理员**第一个执行**的脚本；
`02_download.sh` 则是第十八轮刚修完日志列错位的那个。

### 3.1 为什么本地一直没发现

Windows 侧**没有任何可用的 shell**：WSL 被系统拒绝、无 git-bash、无 `sh`。
所以"脚本能跑"这件事**从未在本地被验证过**。

这不是"疏漏"，而是一个**结构性的盲区**：项目依赖一批只能在 Linux 上
执行的脚本，而开发环境唯一的检查手段是静态检查。
此前从未把"可执行性"降级为静态可判定的断言。

**修复**：

1. 全部 `.sh`/`.py` 归一化为 LF（6 个文件）；
2. 新增 `.gitattributes`（`*.sh text eol=lf` 等），阻止复发；
3. 新增 `tests/test_no_crlf_in_scripts.py`（5 项）。

> **变异验证**：把 CRLF 重新注入真实的 `00_probe.sh`，
> **2 项测试立即失败**（全树扫描 + shebang 专项）；还原后通过。

---

## 4. 缺陷：附录 D 自己重复计数（第 21 项曾与第 10 项重复）

更新附录时我注意到第 10 项与第 21 项**描述的是同一件事**：
管理员文档里的"26 Gb / 9 GB"。为确认不是错觉，
我通过 `dulwich` 把 `APPENDIX_D_verification.md` 在每个提交上的版本读出来，
逐条打印第 10、21 行：

| 提交 | 第 10 行 | 第 21 行 |
| --- | --- | --- |
| `e99642e` ~ `f484d7c` | 26 Gb / 9 GB | **不存在** |
| `f484d7c` 起 | 26 Gb / 9 GB | 26 Gb / 9 GB（同一缺陷） |

第十九轮新增第 21 行时，没有注意到第 10 行已经记录过。
于是"23 项"这个数字**夸大了复核的充分程度**。

处理方式：不去掉计数，而是**用两项本轮真实发现的新缺陷替换**
（CRLF、零用例反向验证），总数更正为 **24 项**，并在附录中留下更正记录。

> **教训**：漏记会低估，**重复计数会高估**。
> 后者更危险，因为它让人以为已经查得够多了。
> 清单类文档需要一条"两行不能描述同一件事"的粗查。

---

## 5. 我自己写错的期望（诚实记录）

本轮我的测试代码本身出了 4 个错，全部是**我的错**，不是项目代码的错：

| # | 我的错误 | 真相 |
| --- | --- | --- |
| 1 | 把反向验证副本放进嵌套的临时目录 | 脚本用 `parents[1] / "src"` 找包；嵌套一层后 `parents[1]` 不是仓库根，副本以 `ModuleNotFoundError` 崩溃——那是"副本坏了"而非"缺陷被检出" |
| 2 | `make_env()` 被调用了两次 | 它创建 `d1.00_r1/`，第二次调用以 `FileExistsError` 失败——测试自身的 bug，会被误读成"副本行为异常" |
| 3 | 以为 `Ran 467 ... skipped=9` 是"467 通过 + 9 跳过" | `Ran N` **已经包含**被跳过的用例；我原来的写法把跳过算了两遍 |
| 4 | 第一次写 diff 脚本时，递归子目录没有拼接父路径前缀 | 于是 `server/` 下的文件被**静默跳过**，导致我先误判"`00_probe.sh` 内容无差异、是索引问题" |

第 4 个错误尤其值得记：**一个静默跳过文件的 diff 脚本，
看起来就像"没有差异"**。我差点据此去改索引逻辑。

---

## 6. 本轮的验证结果

| 项目 | 结果 |
| --- | --- |
| 全部单元测试 | **490 项，OK（9 项因缺少 matplotlib 跳过）** |
| 测试文件数 | 36（新增 2：零用例守卫、CRLF 守卫） |
| 静态校验脚本 | 6 个全部退出码 0 |
| `verify_undergraduate_scope.py` | 116 项通过，0 失败 |
| 新增变异验证 | 3 组，全部证明守卫能失败 |

**变异验证明细**：

| 变异 | 结果 |
| --- | --- |
| 注入一个"有副作用、0 用例"的诱饵 `test_zz_decoy.py` | 守卫失败：`[] != ['test_zz_decoy.py']` |
| 把 `test_shell_static_detects.py` 换成模块级脚本 | `verify_undergraduate_scope.py` 退出码 1，"贡献 0 个用例" |
| 把 CRLF 重新注入真实的 `00_probe.sh` | **2 项测试失败**（全树 + shebang） |

---

## 7. 本轮做了什么 / 没做什么

**做了**：

- 三个反向验证文件重写为真正的 `unittest` 模块（2 + 8 + 3 项），
  每条注入缺陷配一条"未变异时必须通过"的对照；
- 新增 `tests/test_every_test_file_contributes.py`（3 项）；
- 新增 `tests/test_no_crlf_in_scripts.py`（5 项）+ `.gitattributes`；
- 归一化 6 个文件的 CRLF；
- 加强 `verify_undergraduate_scope.py`（从"文件存在"改为"实际收集用例数"）；
- 更正附录 D 的重复计数（23 → 24），新增 D.15、D.16 两节；
- 新增两条 D.8 数字守卫（总数、通过+跳过=总数）；
- 提交 `096ed1a1`（3 新增 + 9 修改，已逐项核对确实包含变更）。

**没做**（本轮明确未触及）：

- **没有运行任何真实实验**，没有下载任何 FASTQ；
- 没有执行 `select_snp_markers.py` / `evaluate_identification.py`；
- 没有产出任何 `fig_*.png`（本机无 matplotlib）；
- 没有渲染 Streamlit 页面；
- 没有验证 `bash -n` 或真实的 bcftools/samtools 命令（本机无可用 shell）；
- 没有填充 `{{CITE:}}` 文献占位符。

---

## 8. 两条教训

> **教训 1：文件名不是契约。**
> `test_*.py` 只说明它会被 import，不说明它的判定会被报告。
> **一个从未被执行的断言，和一个被注释掉的断言，价值相同。**

> **教训 2：检查"证据存在"与检查"证据成立"是两件事。**
> 前者几乎总能通过，后者才需要真正执行。
> 本项目此前多次强调"验证工具必须在真实数据上端到端跑一遍"，
> 但这些**反向验证脚本自己**从未被"以测试身份"跑过。

---

## 9. 下一步（不变）

主线仍被**服务器环境**阻塞。需要的外部动作没有变化：

1. 管理员阅读 `docs/server_request_onepager.md`，或运行 `bash server/00_probe.sh`
   并回传 `logs/probe_summary.tsv`；
2. 本地执行 `python scripts/interpret_probe.py --summary logs/probe_summary.tsv`；
3. 上传 `server/` + `pilot_smoke1.tsv`，跑通单样本全流程。

在服务器可用前，可继续推进的仍是**不依赖真实数据**的部分：
论文第 5 章与结论的占位符框架、以及继续对抗性复核现有代码与文档。
