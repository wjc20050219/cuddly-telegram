# 第九轮报告：静态工具自身的缺陷、文档命令可执行性

- 日期：2026-09-20
- 范围：规范 C（`UNDERGRADUATE_TASK_LIST.md` TASK-001–048）
- 本轮性质：**非数据依赖的加固**。真实服务器信息仍未到位，因此只推进不依赖真实数据、
  也不会产生任何实验数值的部分。

---

## 一、本轮为什么做这件事

第 8 轮结束时，把 TASK-020～TASK-048 逐条读了一遍，结论是：
**剩下的 🔶 任务全部卡在真实数据上**，没有一条能在本机继续推进。
唯一还能做的是两条"工具自身的缺口"，都由第 8 轮自己记录下来的：

1. `verify_shell_static.py` 只有端到端测试，**没有任何逐函数单测**；
2. `--only confusion --only pca` 同时使用（两者现在共用 `--similarity-matrix`）从未验证。

另外还有一条此前没人检查过的：**文档里写给用户的命令，从来没有跟真实 CLI 对过**。

---

## 二、先做的事：确认这两条缺口是真的

### 2.1 `--only confusion --only pca` 同时使用

结论：**接线是正确的，缺口只是"没测过"，不是"有问题"**。

用真实 3 品种方阵跑 `--only confusion --only pca`，程序按预期把两张图都排进队列，
然后因为**本机没有 matplotlib** 而同时跳过并明确报出原因（`未安装 matplotlib，无法绘图`），
退出码 1，`out-dir` 下不落任何文件。

同时确认了注册表自洽：

| 检查 | 结果 |
| --- | --- |
| `FIGURES` 中每一项都有 handler | 是（0 个缺失） |
| `HANDLERS` 中有任何键不在 `FIGURES` | 无（即没有 `--only` 无法触达的图） |
| 需要方阵的图 | `confusion`、`pca` 两张，均经 `MATRIX_FIGURES` 路由 |

**遗留事项因此可关闭**：两张图共用一个 `--similarity-matrix` 是设计意图，不是冲突。

### 2.2 文档命令可执行性

这是本轮真正挖出问题的地方，见下。

---

## 三、发现并修复的真实缺陷

### 3.1 `strip_comments_and_strings` 把 `#` 一律当注释（漏报方向）

**疑似缺陷（可证伪的表述）**：`verify_shell_static.py` 的
`strip_comments_and_strings` 在单引号外见到任意 `#` 就 `break`，会把
`${VAR#pattern}`、`${#arr[@]}` 这类**参数展开**和双引号内的字面 `#` 一起截断，
从而使后面的变量引用对该检查器不可见。

**验证**：在真实脚本里逐行找出 `#` 出现在未闭合双引号内的情况，命中 8 处，
其中 3 处是真实代码（其余是 `00_probe.sh` 的小标题）：

| 位置 | 原文 | 修复前被截成 |
| --- | --- | --- |
| `00_probe.sh:26` | `echo "### 1. 系统与硬件"` | `echo "` |
| `05_simulate.sh:84` | `local subsample_arg="${seed}.${frac#0.}"` | `local a="${seed}.${frac` |
| `07_identify.sh:67` | `[ "${#args[@]}" -gt 0 ]` | `[ "${` |

**方向判定（重要）**：截断只会**删掉**文本，不可能**暴露**本来被引号包住的变量，
所以该缺陷**只会漏报、不会误报**。这决定了修复不必担心引入新的假警报——
修复后真实流水线仍是 0 发现，与判定一致。

**一个被证伪的中间假设**：我最初以为"截断会吞掉 `${frac...}` 导致未定义变量漏检"。
实测**不成立**：检查器另有多条正则，`$frac` 和 `$seed` 仍被正常报出。
真正被吞掉的是 `${#args[@]}` 这种**整个引用都在 `#` 之后**的形式。
把这句假设写下来并实测，避免了基于错误理由去改代码。

**修复**：`#` 只在**词首**才是注释（行首，或前一个字符是空白 / `;` / `|` / `&` / `(`）；
同时跟踪单引号、双引号与反斜杠三种状态，引号内内容**填空格而非删除**，保持偏移不变。

| 输入 | 修复前 | 修复后 |
| --- | --- | --- |
| `echo "### 1. system"` | `echo "` | 原样保留 |
| `local a="${seed}.${frac#0.}"` | `local a="${seed}.${frac` | 原样保留 |
| `[ "${#args[@]}" -gt 0 ]` | `[ "${` | 原样保留 |
| `X="$A#literal"` | `X="$A` | 原样保留 |
| `Y='$Q'` | `Y=    ` | `Y=    `（不变，单引号内仍不可见） |
| `A=1 # gone` | 去掉注释 | 去掉注释（不变） |

修复后真实 `server/*.sh` 静态分析仍为 **0 发现**。

### 3.2 README 指向一个永远不会出现在仓库里的文件

**缺陷**：README《如何复现实验》第 2 步写"按 `data/metadata/download_log.tsv` 中记录的
accession 与校验和重新下载原始数据"。

**验证**：该文件在仓库中不存在（全仓搜索 `*download*` 只命中 `server/02_download.sh`）。
`server/02_download.sh` 第 14 行 `DLLOG="$RV_META/download_log.tsv"`，而
`server/config.sh` 第 8 行 `RV_META="$RV_ROOT/metadata"`、第 7 行
`RV_ROOT="${RV_ROOT:-$HOME/ricevar}"`——即该日志写在**服务器**的
`$HOME/ricevar/metadata/` 下，**根本不在仓库内**。照 README 操作的用户会找不到文件。

**修复**：README 改为指向服务器路径 `$RV_ROOT/metadata/download_log.tsv`，
并注明该日志由 `server/02_download.sh` 在服务器生成、仓库 `data/metadata/` 只放检索与面板元数据。

### 3.3 新建 `scripts/verify_documented_commands.py`

把"文档里的命令是否还能跑"变成一条可重复的门禁：

- 抽取 README / runbook / STATUS / PROJECT_STRUCTURE 中所有 `python scripts/*.py ...` 调用；
- 对每个脚本实跑 `--help`，取出它**真正**支持的参数，比对文档用到的参数；
- 检查文档引用的路径是否存在，但**区分两类**：源码/文档/清单属于输入，必须存在；
  `data/processed/`、`figures/` 等属于流水线产物，尚未生成属正常。

**变异测试（对真实文档做，做完还原）**：

| 注入的缺陷 | 是否被发现 |
| --- | --- |
| `--database` 改名为 `--db` | ✅ 1 处 |
| `export_similarity_matrix.py` 改名（脚本不存在） | ✅ 2 处（调用 + 路径） |
| `--analysis-dir` 改名为 `--results` | ✅ 1 处 |
| 引用一个不存在的 `docs/` 路径 | ✅（扩展覆盖后） |

runbook 还原后**逐字节相同**。

**它自己的第一次运行报了 4 处假阳性**，全是检查器的问题而不是文档的问题：
正则在 `data/metadata/server/pilot_smoke1.tsv` 上匹配到了后缀 `server/pilot_smoke1.tsv`。
已在正则前加边界 `(?<![\w./-])` 修正，并留了一条回归测试锁住。

---

## 四、逐函数单测（46 项）

`verify_shell_static.py` 此前只有端到端测试，单个辅助函数出错可能被整体结果掩盖。
新增 `tests/test_shell_static_functions.py`，覆盖
`strip_comments_and_strings` / `read_names` / `collect_assignments_from_lines` /
`iter_functions` / `declared_locals` / `logical_statements` / `heredoc_spans` /
`in_heredoc` / `check_undefined_vars` / `check_quote_balance` / `check_mktemp_parallel`，
外加一条端到端断言（真实流水线 6 类检查全 0 发现）。

**三个断言写错了，代码都是对的**——这是本轮最值得记的部分：

| 我写的断言 | 实际契约 | 判定 |
| --- | --- | --- |
| `iter_functions` 产出 3 元组 | 产出 `(name, body)` 2 元组 | **测试错** |
| `check_quote_balance` 检查引号配对 | 只查**未闭合的 `$(`/反引号** | **测试错** |
| `echo 'a\'b'` 中的 `b` 应被吞掉 | 反斜杠在单引号内是字面量，`'a\'` 已闭合，`b` 确在引号外 | **测试错** |

第二条尤其值得写下来：shell 的引号**可以跨行**，逐行做配对检查必然误报，
所以检查器只追踪跨行未闭合的命令替换是**正确设计**，是我按"引号配对"想当然了。

---

## 五、验收

| 项目 | 结果 |
| --- | --- |
| 单元测试 | **210 项通过，9 项跳过**（需 matplotlib），退出码 0 |
| 规范 C 静态检查 | **113/113**（第 8 轮为 109/109，新增 4 项） |
| shell 静态分析（真实流水线） | 12 个脚本、209 个已赋值变量，**6 类检查 0 发现** |
| 文档命令可执行性 | **0 发现** |
| 阶段顺序回归 / 论文占位符检查 | 通过 |
| `.tmp` 残留 | 0 个文件 |
| `.learnings/LEARNINGS.md` | 合法 UTF-8、无 U+FFFD、26 条 |

---

## 六、仍然没有做到的事

必须写清楚，避免这些"工具变绿"被误读成"实验有进展"：

- **本轮没有产生任何实验数值**。没有识别准确率、没有 recall、没有 ROC/AUC、
  没有最低可用深度——这些仍然全部不存在。
- **`fig_pca.png` 与 confusion 热图仍然从未真正渲染过**：本机没有 matplotlib，
  两张图至今只在"被正确跳过"这条路径上验证过。
- **Streamlit 页面仍然从未启动过**（本机无 streamlit）。
- **`server/*.sh` 仍然从未在真实服务器上执行过**；本轮的全部检查都是**离线静态**的，
  包括 3.1 的修复——它让检查器更准确，但**不能替代 `bash -n` 和真机运行**。
- **TASK-010 起（下载/QC/比对/SNP/降采样/识别）一条都没有动**，仍全部等服务器。
- 硬阻塞未变：调度器未知、EBI/ENA 连通性未知、存储配额未知、`00_probe.sh` 未运行、
  本机无可用 Bash、无 matplotlib、无 streamlit。

## 七、下一步

唯一的人为动作仍然是把 `docs/server_admin_questions.md` 交给管理员、
或在服务器上跑 `server/00_probe.sh`。信息到位后按
`pilot_smoke1 → pilot_smoke5 → Pilot 30` 依次执行，不直接启动全量。
