# RiceVar-ID 本科毕业论文任务清单（规范 C，现行）

> 生效日期：2026-09-20  
> 范围定义见 `docs/UNDERGRADUATE_SCOPE.md`。本清单替代规范 B 作为后续执行编号；A/B 历史报告保留，编号对照见 `docs/TASK_NUMBERING.md`。

状态：✅ 完成；🔶 部分完成/已有方案但缺真实服务器或数据执行；⬜ 未开始。

## 环境、文献和数据

| 任务 | 内容 | 状态 | 说明/产出 |
| --- | --- | --- | --- |
| TASK-001 | 服务器环境调查 | 🔶 | `server/00_probe.sh` 已有；学校服务器尚未运行 |
| TASK-002 | 项目目录建立 | ✅ | `PROJECT_STRUCTURE.md` |
| TASK-003 | 软件环境建立 | ✅ | `environment.yml` 等；本机环境历史验证通过 |
| TASK-004 | 阅读参考论文 | ✅ | `docs/methods/literature_review.md` 等 |
| TASK-005 | 公开水稻数据搜索 | ✅ | NCBI/ENA/DDBJ 镜像检索结果 |
| TASK-006 | 样本筛选 | ✅ | `candidate_samples.tsv` |
| TASK-007 | 品种名称整理 | ✅ | `variety_alias.tsv` / `variety_canonical.tsv` |
| TASK-008 | 建立 20–30 个品种 Pilot 数据集 | ✅ | Pilot 30 份 |
| TASK-009 | 建立测试数据集 | ✅ | 独立面板 25 份，冻结且与 Pilot 品种零重叠 |
| TASK-010 | 下载数据到学校服务器 | ⬜ | 等服务器 probe；**本机不下载 FASTQ**（硬约束） |

> **本机验证边界**：本机没有可用的 Bash（WSL 报 `E_ACCESSDENIED`），因此
> `server/*.sh` 无法用 `bash -n` 或真实 bcftools/samtools 校验。已用
> `scripts/verify_shell_static.py` 做 Python 静态分析（未定义变量、未闭合命令替换、
> 并行 mktemp、关键命令失败保护、heredoc 导入、阶段覆盖），并由
> `tests/test_shell_static_detects.py` **反向验证其确实能检出注入缺陷**。
> 这仍**不等于**脚本已在真实服务器跑通——真正的执行验证只能在服务器上完成。

## QC、参考与比对

| 任务 | 内容 | 状态 | 说明/产出 |
| --- | --- | --- | --- |
| TASK-011 | FastQC | ⬜ | 无 FASTQ |
| TASK-012 | fastp | ⬜ | 无 FASTQ |
| TASK-013 | 数据 QC | 🔶 | 输出字段/排除规则已有方案；无真实结果 |
| TASK-014 | 参考基因组下载 | 🔶 | IRGSP-1.0 已选定；服务器未下载，见 `reference_genome_plan.md` |
| TASK-015 | BWA-MEM2 比对 | 🔶 | 服务器脚本已有；`verify_shell_static.py` 静态检查通过（6 类 0 发现，新增 46 项逐函数单测）；**参考基因组完整 SHA256（不截断）已锁为 3 项机械检查**，`reference_record.tsv` 的 9 列字段齐备；仍未在真实服务器执行，`reference_record.tsv` 无真实值 |
| TASK-016 | BAM/CRAM 处理 | 🔶 | 同上；无真实 BAM/CRAM |
| TASK-017 | mapping 统计 | 🔶 | 统计字段已定义；无真实结果 |

## SNP 主线

| 任务 | 内容 | 状态 | 说明/产出 |
| --- | --- | --- | --- |
| TASK-018 | SNP calling | 🔶 | bcftools 脚本原型已有；正式分析需联合 calling，未执行 |
| TASK-019 | SNP QC | 🔶 | 流式 QC/缺失/MAF/QUAL/DP/GQ 代码与合成测试已准备；参数待 Pilot 确定 |
| TASK-020 | SNP 矩阵 | 🔶 | 矩阵导出代码与合成测试已准备；无真实 VCF |
| TASK-021 | SNP marker 筛选 | 🔶 | Pilot-only 防泄漏与嵌套 500/1000/2000 筛选已实现；无真实 marker |
| TASK-022 | 品种数字指纹 | 🔶 | 0/1/2/-1 矩阵格式已实现；等真实 SNP |
| TASK-023 | Hamming similarity | 🔶 | 算法模块与合成单元测试完成；等真实指纹 |
| TASK-024 | Jaccard/IBS similarity | 🔶 | IBS/Jaccard 模块与合成测试完成；无真实计算 |
| TASK-025 | 品种识别 | 🔶 | Top-k/拒识代码骨架与预注册完成；无真实准确率结果 |

## 超低深度与验证

| 任务 | 内容 | 状态 | 说明/产出 |
| --- | --- | --- | --- |
| TASK-026 | 1× downsampling | 🔶 | 代码骨架/seed manifest/固定 marker 分型已实现；无真实 CRAM |
| TASK-027 | 0.5× downsampling | 🔶 | 同上，未执行 |
| TASK-028 | 0.2× downsampling | 🔶 | 同上，未执行 |
| TASK-029 | 0.1× downsampling | 🔶 | 同上，未执行 |
| TASK-030 | 0.05× downsampling | 🔶 | 同上，未执行 |
| TASK-031 | 0.02× downsampling | 🔶 | 同上，未执行 |
| TASK-032 | 不同深度识别率 | 🔶 | `server/07_identify.sh` + `scripts/evaluate_identification.py` 已实现并用合成 VCF 端到端验证；**经证伪审查修复 2 个真实缺陷**（未标注查询曾计入分母致准确率偏低；真值表 id 空间不一致曾静默产出 0.0）；反向验证 2/2；**无真实结果**，禁止预设 |
| TASK-033 | marker recall | 🔶 | 同上：逐 query 输出 `marker_recall`/`genotype_concordance`；`depth_from_name` 已证伪为正确并锁为回归测试；无真实结果 |
| TASK-034 | marker 数量实验 | 🔶 | 500/1000/2000 设计已冻结；评估按三个 marker 数分别输出；无结果 |
| TASK-035 | 独立/重复测试 | 🔶 | 面板已冻结；当前独立面板仅适合开放集拒识，不是同品种 Top-1 测试 |

## 图表、软件与论文

| 任务 | 内容 | 状态 | 说明/产出 |
| --- | --- | --- | --- |
| TASK-036 | PCA | 🔶 | **已实现**：`make_figures.py --only pca --similarity-matrix <方阵>` 生成 `fig_pca.png` + `fig_pca_coordinates.tsv`；PCA 用**标准库**实现（不依赖 numpy，本机可测），在 6 组解析可解的算例上逐一验证（3:1 椭圆 0.9/0.1、旋转不变性 37°/90°/143°、共线 1.0、全同 0 分量）；未测量格子按行均值填补而非填 0，仅有对角线的品种剔除而非补成全 1；无真实方阵不产图 |
| TASK-037 | similarity heatmap | 🔶 | **已完成前置：`scripts/export_similarity_matrix.py` 导出品种两两相似度长表 + 方阵（长表含 method/比较位点数/差异位点数，方阵对称、对角线 1.0）；不可比对的品种对写**空单元格**而非 0；`make_figures.py --similarity-matrix` 已接线；11 项新单测 + 与 `compare_varieties` 逐对等价验证（18/18 组合零差异）。仅缺真实数据库，无数据不产图 |
| TASK-038 | fingerprint visualization | 🔶 | 框架就绪（深度曲线/recall/相似度分布）；等真实识别结果 |
| TASK-039 | accuracy figure | 🔶 | 框架就绪；无真实结果文件时明确跳过，不用示意数据代替 |
| TASK-040 | depth–accuracy figure | 🔶 | `fig_depth_curve.png` 生成逻辑与单测就绪；等真实识别结果 |
| TASK-041 | SQLite 数据库 | 🔶 | `database.py` + `build_database.py` + `dbquery.py` 完成，20 项单测通过；无真实数据入库 |
| TASK-042 | RiceVar-ID 软件 | 🔶 | `app/streamlit_app.py` 完成；无数据库时拒绝显示任何结果；**页面仍未启动过**（本机无 streamlit）；已按真实调用序列审计数据层并修复 2 个真实缺陷（见 TASK-043） |
| TASK-043 | 品种查询 | 🔶 | `find_variety`/`list_varieties` + 页面查询页；单测通过；**修复 `find_variety` 把用户输入的 `%`/`_` 当 SQL 通配符的缺陷**（搜 `_` 曾列出整个库），已转义并与字面包含语义逐一比对；新增 `unlabelled_samples()` 使无品种名样本可见 |
| TASK-044 | 品种识别 | 🔶 | 页面上传→解析→识别链路单测端到端通过；无真实参考库；**修复无品种名参考样本可赢下识别却对用户不可见的问题**，`identify()` 现返回 `best_match_lacks_variety` 与 `n_unlabelled_reference_samples` |
| TASK-045 | 品种比较 | 🔶 | `compare_varieties` 报告比较样本对与比较位点数；**证伪审查发现并修复 `method` 参数从未生效的缺陷**（曾硬编码 Hamming，现已复用 fingerprint 实现并与识别层同尺度）；反向验证 3/3 |
| TASK-046 | 整理实验结果 | ⬜ | 等真实分析 |
| TASK-047 | 撰写论文 | 🔶 | `docs/thesis/THESIS_DRAFT.md` 骨架 + **第 1 章引言、2.1 数据来源、4.3 局限性（8 条）、4.4 应用前景已扩写为正式行文**；**五份附录全部完成**：A（55 样本 ×13 列，脚本生成 + 7 项不变量校验）、B（版本号取自实测记录）、C（位点筛选公式，逐条取自实际代码并由测试独立重算）、D（复核记录，**26 项已修复缺陷**（含 `download_log.tsv` 列错位、管理员材料不可复核数字、一页纸写入范围承诺失真、论文引用不存在的图、服务器脚本 CRLF 行尾导致 Linux 下无法执行、三个"反向验证"文件贡献 0 个测试用例、任务清单正文自称"没有任何 ✅"而表格已有 8 项）+ 尚未复核清单 + 变异测试小节）、E（可获得性，含"实验尚未执行"声明与版本控制实际状态）；第 3 章结果与第 5 章结论仍全为占位符（第 5 章已给出"哪份产物填哪段"的填写协议），**§3.9 已建立"图 → 生成命令"对应表并双向校验**；`verify_thesis_placeholders.py` 机械检查无虚构数值 |
| TASK-048 | 制作答辩 PPT | 🔶 | `docs/thesis/DEFENSE_SLIDES.md` 22 页提纲 + 预设问答完成；等真实结果填充 |

## 当前放行顺序

1. 把 `docs/server_request_onepager.md` 发给管理员；或由管理员运行 `server/00_probe.sh`，
   或逐条回答 `docs/server_admin_questions.md`；
2. **用 `python scripts/interpret_probe.py --summary logs/probe_summary.tsv` 判读探测结果**
   （exit 0 就绪 / 1 已探测但有阻塞 / 2 尚未探测）；
3. 上传 `server/` 与 `data/metadata/server/pilot_smoke1.tsv`；
4. 用 1 个最小样本完成下载、校验、QC、比对和 SNP calling 冒烟测试；
5. 扩到 `pilot_smoke5.tsv`；
6. 复核 QC 与 calling，再运行 Pilot 30；
7. marker 与阈值冻结后，才运行独立面板；独立面板不得按结果重选。

## 状态口径

- ⬜ 未开始：还没有任何实现。
- 🔶 **代码完成、无真实数据结果**：实现与单测已就位，但**尚未在真实数据上运行**，
  因此论文中不得引用任何数值。
- ✅ 完成：分两类，**必须区分**——
  - **整理类**：产出是可追溯的仓库文件（目录结构、软件环境、文献综述、
    检索结果、样本清单），**不含实验测量值**；
  - **实验类**：产出是**可追溯到结果文件的真实数值**（如识别率、实测深度）。

当前项目有 **8 项 ✅，全部属于整理类**：TASK-002（项目目录）、TASK-003（软件环境）、
TASK-004（参考论文）、TASK-005（数据检索）、TASK-006（样本筛选）、
TASK-007（品种名称整理）、TASK-008（Pilot 数据集）、TASK-009（独立测试集）。

**当前项目没有任何 ✅ 级实验任务**。全部实验类条目均为 🔶（"准备好了但还没跑"），
**没有任何真实测量数值**，不得在论文或答辩中表述为已有实验结果。

> 这条口径此前写作"当前项目没有任何 ✅"，在整理类任务完成后即成为**假命题**——
> 一句正确的话会因事实变化而变成错误的话，必须随事实更新（见附录 D）。

