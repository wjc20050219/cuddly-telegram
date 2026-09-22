# ROUND 8 报告：PCA 图实现与文档编号修复

**日期**：2026-09-20
**范围**：TASK-036（PCA）实现；`snp_evaluation_design.md` 章节编号修复；`.learnings` 事故记录
**结论**：TASK-036 代码完成（仍为 🔶，无真实数据结果）；项目仍未执行任何真实实验。

---

## 一、为什么本轮做 PCA

TASK-036 是 `make_figures.py` 中**唯一没有任何代码路径**的图。它的前置依赖——品种间
成对相似度方阵——在 R6 由 `scripts/export_similarity_matrix.py` 解除，且
`--similarity-matrix` 参数已接入 CLI，因此本轮可以完成全部**不依赖真实数据**的部分。

### 约束

| 约束 | 来源 | 处理 |
| --- | --- | --- |
| 无真实数据不产图 | `PLACEHOLDER_CONVENTIONS.md` 五条禁令 | 方阵缺失/无效/品种不足时返回 `None` 并写 stderr，绝不使用示意数据 |
| 核心包不依赖第三方库 | 项目既有设计 | PCA 用**标准库**实现，不引入 numpy |
| 缺数据必须表现为缺数据 | 数据库层既有原则 | 未测量格子不填 0.0 |

---

## 二、实现

`scripts/make_figures.py` 新增：

| 函数 | 作用 |
| --- | --- |
| `pca_2d(rows, n_components, iters, tol)` | 对中心化后的 `n × n` Gram 矩阵 `X X^T` 做幂迭代，返回 `(coords, explained_ratio, n_found)` |
| `prepare_pca_rows(labels, values)` | 把稀疏相似度方阵转成 PCA 的稠密输入行，返回 `(usable, dropped)` |
| `fig_pca(per_query, out_dir, matrix_path)` | 出图，并写出 `fig_pca_coordinates.tsv` |

`FIGURES` 增加 `"pca"`；新增 `MATRIX_FIGURES = {fig_confusion, fig_pca}` 取代原先只判断
`handler is fig_confusion` 的硬编码分支。

### 为什么用 Gram 矩阵而不是协方差矩阵

品种数 `n` 远小于 marker 数 `d`。对 `n × n` 的 Gram 矩阵做幂迭代是**精确**的，且代价
只与 `n` 有关；形成 `d × d` 协方差矩阵在 `d` 达到 500~2000 时既慢又无必要。

---

## 三、证伪与修复：一个真实的实现缺陷

### 缺陷 A：全 1 向量是中心化 Gram 矩阵的精确零向量

**可疑命题**："以全 1 向量为种子做幂迭代，可以求主成分。"

**实测**：3:1 椭圆算例返回 `k=0`、坐标全为空。追踪每一步：

```
gram = [[9,-9,0,0],[-9,9,0,0],[0,0,1,-1],[0,0,-1,1]]   # 矩阵本身正确
trace = 20.0
start = [0.5, 0.5, 0.5, 0.5]
it0 matvec = [0.0, 0.0, 0.0, 0.0]  norm=0.0   <-- 精确为零
```

**根因**：中心化后每一行之和恒为 0，因此全 1 向量**永远是特征值 0 的特征向量**。
用它作种子等于从一个与该矩阵值域正交的方向出发，投影必然为零。这不是数值不稳定，
是逻辑必然。

**修复**：改用单位基向量作种子，跳过与已求得分量近似平行的种子，并把"特征值低于
阈值则丢弃"写成显式规则。

**验证**（解析可解，非"跑通即可"）：

| 算例 | 期望 | 实测 |
| --- | --- | --- |
| 轴对齐 3:1 椭圆 | 方差比 0.9 / 0.1 | `[0.9, 0.1]` |
| 同形状旋转 37° / 90° / 143° | 方差比不变 | 三处均 `[0.9, 0.1]` |
| 共线点 | 1 个分量，方差比 1.0 | `k=1, [1.0]` |
| 各向同性四点 | 0.5 / 0.5 | `[0.5, 0.5]` |
| 全部相同的点 | 0 个分量 | `k=0, []` |
| 空输入 / 单点 | 不崩 | `([], [], 0)` / `k=0` |

旋转不变性是 PCA 的**定义性质**，因此它能真正检验实现，而不是只检验"代码能跑"。

### 缺陷 B：用对角线填补会把品种变成"与所有品种完全相同"

**可疑命题**："缺失格子用整行均值填补即可。"

**实测**（稀疏方阵，品种 A 只测到自身）：

```
A [1.0, None, None]    ->  imputed [1.0, 1.0, 1.0]
B [None, 1.0, 0.1]     ->  imputed [0.55, 1.0, 0.1]
C [None, 0.1, 1.0]     ->  imputed [0.55, 0.1, 1.0]
```

品种 A 被补成"与所有品种相似度 1.0"——这是**凭空造出的相似度**，且在图上会表现为一个
与所有品种重合的点，看起来像真实结论。

**根因**：把对角线上的自相似（恒为 1）当成普通测量值参与填补。它不含"这个品种在哪"
的任何信息。

**修复**：只用**非对角**已测量值的均值填补；若某行除对角线外没有任何测量值，**剔除
该品种**并明确记录原因。这与"未测量格子写空而非写 0"是同一条原则的延伸。

**测试**：`test_row_with_only_self_similarity_is_dropped_not_imputed_to_ones` 直接断言
"没有任何一行被补成全 1"；`test_missing_cells_are_imputed_with_the_row_mean_not_zero`
断言未测量格子填的是行均值而不是 0.0。

### 一处自我纠正

初次验证时我在临时脚本里**复制**了填补逻辑而非调用真实代码，因此脚本输出仍是修复前的
结果，一度误以为修复无效。改为把预处理抽成具名函数 `prepare_pca_rows` 后，测试直接
调用真实实现。**这正是"预处理必须具名"的理由**：不可测的代码无法被验证。

---

## 四、文档编号修复（附带发现）

在 `docs/methods/snp_evaluation_design.md` 插入 PCA 小节时发现原文层级本身不自洽：
`## 4.4` 之下挂着 `### 4.1` / `### 4.2`。已一并修正为 `### 4.1` / `### 4.2` / `### 4.3`。

**跨文件引用必须同步**——grep 全仓库后发现 3 处指向旧编号：

| 文件 | 原引用 | 修正为 |
| --- | --- | --- |
| `docs/methods/server_pilot_runbook.md` | §4.1 | §4.2 |
| `docs/task_reports/ROUND5_fingerprint_similarity_falsification_report.md`（2 处） | §4.2 / §4.1 | §4.3 / §4.2 |

---

## 五、工具事故（已完整恢复）

用 PowerShell `Add-Content` 追加 `.learnings/LEARNINGS.md` 时，PowerShell 按**系统代码页
（GBK）**编码新内容，导致文件不再是合法 UTF-8（`read` 报 "invalid UTF-8 text"）。

诊断结果：字节 0..27059 是干净 UTF-8（原有 19 条全部完好），自 `## LRN-020` 起是 GBK；
中文已变成不可恢复的错误字形（GBK 往返只能得到错误字符，不是原文）。**原始内容未受损**。

处理：截断损坏段，改用 `edit` 工具重新追加。复验：文件合法 UTF-8、无 U+FFFD 替换字符、
新段含 122 个真实中日韩字符、22 条记录齐全。

这是同一故障模式的**第二次**发生（此前 `Set-Content` 曾损坏 `tests/test_database.py`），
已记为 LRN-022 并明确规则：**仓库文本文件只用 `write`/`edit` 工具或显式 UTF-8 的 Python
写入，绝不用 PowerShell 文本写入 cmdlet。**

---

## 六、验收

| 检查 | 结果 |
| --- | --- |
| 单元测试 | **154 项通过**（9 项需 matplotlib 跳过），较上轮 +17 |
| `verify_undergraduate_scope.py` | **109 / 109**（较上轮 +4） |
| `verify_stage_order.py` | 0 failed |
| `verify_thesis_placeholders.py` | 通过（论文骨架仍无任何具体结果数字） |
| `round1_verify.py` | 通过 |
| `verify_shell_static.py --strict` | 0 发现 |
| `.tmp` 残留 | 0 文件 |

### 一次假失败（已排除，非代码缺陷）

首次汇总验收时在 shell 里设了 `$env:PYTHONIOENCODING="utf-8"`，套件立刻报 1 failure
+ 14 errors，全部集中在**通过 `subprocess` 调用子进程 CLI** 的用例上
（`test_export_similarity_matrix` / `test_fingerprint_db` / `test_evaluate_identification`
/ `test_make_figures`）。**代码未改动，只有环境变了**；去掉该变量后恢复 154/154 全绿。

结论：控制台中文乱码是显示层问题，**不得**用 `PYTHONIOENCODING` 去"修"；它改变了被测
行为。套件在无代码改动时由绿转红，应先怀疑环境并在干净 shell 中复跑。已记为 LRN-023。

---

## 七、仍然没有做到的事

1. **`fig_pca` 从未真正出过 PNG。** 本机 Python 3.7 无 matplotlib，实际绘图路径只在
   解析、门槛判断与数学层被验证；渲染必须在 `ricevar` 环境复验。
2. **PCA 从未见过真实数据。** 品种间真实相似度结构、PC1/PC2 能否分开品种，全部未知。
   本轮的"验证"只证明**算法与缺值处理正确**，不证明任何生物学结论。
3. **TASK-036 状态仍是 🔶，不是 ✅。** 按"状态口径"，无真实数据结果的实验任务不得标 ✅。
4. **服务端执行仍全部阻塞**：调度器未知、`www.ebi.ac.uk` 可达性未知、存储配额未知、
   `00_probe.sh` 未运行、无 FASTQ、无参考基因组。
5. **论文与 PPT 仍无任何真实数字**，全部为占位符。

---

## 八、下一步

在服务器不可用期间，剩余的非数据依赖工作已基本清空。可继续的方向：

1. 为 `verify_shell_static.py` 补**逐函数单元测试**（目前只有端到端用例）。
2. 复核 `fig_confusion` 与 `fig_pca` 共用 `--similarity-matrix` 时的交互（如同时指定
   `--only confusion --only pca`）。
3. 服务器可用后按 runbook 顺序执行：`00_probe.sh` → 单样本 → 5 样本 → 30 样本 Pilot →
   冻结 marker/阈值 → `07_identify.sh` 出深度曲线 → 独立面板做开集拒绝。
