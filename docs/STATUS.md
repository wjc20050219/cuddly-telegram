# RiceVar-ID 项目状态汇总

- 汇总时间：2026-09-20（本科版范围收敛与服务器骨架加固后更新）
- 项目：基于超低深度全基因组测序的水稻品种数字身份证系统
- **现行任务清单**：`UNDERGRADUATE_TASK_LIST.md`（规范 C，TASK-001–048）
- 历史规范：`TASK_LIST.md`（A，001–053）+《AI Agent 项目总任务书》（B，001–080）
- 三套编号对照见 `docs/TASK_NUMBERING.md`

---

## 一、一句话状态

**项目已按用户最新要求收敛为本科毕设 SNP 主线；数据基础 GO（有条件），实际分析仍卡在学校服务器信息。**
公共数据检索与候选样本整理已完成：**32,564 条 ≥5× 水稻 WGS，其中 14,830 条（45.5%）品种名可用，
覆盖 8,415 个规范品种**；**Pilot Panel 30 份、独立测试集 25 份（已冻结，零重叠）**已选定；
**冻结清单标注的 FASTQ 总量 334.71 GiB / 计算量暂估约 140–275 核时**。
本机环境已建成、实测可用且逐项复核过（查出并修复 2 处依赖缺陷）；
已完成本机算力实测（单样本 10× = 0.81 核时，**本机瓶颈由「CPU」修正为「磁盘」**）。
**下一步唯一的人为动作**：把 `docs/server_admin_questions.md` 交给管理员并在学校服务器运行 `server/00_probe.sh`。信息到位后按 `pilot_smoke1 → pilot_smoke5 → Pilot 30` 依次执行，不直接启动全量。
**注意：至今未下载任何测序数据，未跑任何真实 QC/比对/SNP/降采样；当前没有识别准确率、ROC/AUC 或最低可用深度结论。**

<details>
<summary>上一版（2026-09-16）的一句话状态</summary>

Phase 0–3 已完成（TASK-001~010，其中 TASK-010 为部分完成）；本机环境已建成、实测可用且逐项复核过
（查出并修复 2 处依赖缺陷）；已完成本机算力实测（单样本 10× 全基因组 = 0.81 核时，
比原文献估算低 4–12 倍，**本机瓶颈由「CPU」修正为「磁盘」**）；
小麦论文的技术路线图与"小麦→水稻"迁移决策已成型（6 项可直接迁移、5 项必须重新优化）；
四条候选标记体系已建立并配齐统一比较框架与假设清单。

</details>

---

## 二、任务进度

| 阶段 | 任务 | 状态 | 产出 |
| --- | --- | --- | --- |
| Phase 0 | TASK-001 创建项目目录 | ✅ | 25 个目录 + `PROJECT_STRUCTURE.md` |
| Phase 0 | TASK-002 建立软件环境 | ✅ | 环境**实际建成并通过冒烟测试**（非仅配置） |
| Phase 0 | TASK-003 建立 README | ✅ | `README.md`（九项要求全覆盖） |
| Phase 1 | TASK-004 解析小麦论文 | ✅ | `paper_niu2024_extraction.md`（601 行）+ `TASK-004_report.md` |
| Phase 1 | TASK-005 论文技术路线图 | ✅ | `paper_workflow.md`（10 节：主线八阶段 + 原文 Step 0–7 全参数） |
| Phase 1 | TASK-006 小麦→水稻迁移表 | ✅ | `wheat_to_rice_migration.md`（8 节：13 环节逐项迁移判定） |
| Phase 2 | TASK-007 四条候选标记体系 | ✅ | `marker_routes.md`（10 节：四路线 + 统一比较框架 + 假设清单 H1–H6） |
| Phase 3 | TASK-008 检索 NCBI | ✅ | `ncbi_search_summary.tsv` + `ncbi_sra_runs.tsv`（300 条 run 级） |
| Phase 3 | TASK-009 检索 ENA | ✅ | `ena_rice_wgs_deep_runs.tsv`（**10,000 条 ≥5×，含 FASTQ 直链**） |
| Phase 3 | TASK-010 检索 DDBJ | ⚠️ 部分完成 | 官方 API 全线 504；**数据经 ENA/NCBI 镜像库获取**（DRR 1,255 条） |
| **第一轮** | **TASK-011 候选样本整理** | ✅ | `candidate_samples.tsv`（**32,564 run × 34 列**；品种名可用 14,830） |
| **第一轮** | **TASK-012 品种名称标准化** | ✅ | `variety_alias.tsv` + `variety_canonical.tsv`（**8,415 个规范品种**） |
| **第一轮** | **TASK-013 重复样本检查** | ✅ | `duplicate_samples.tsv`（1,326 组，分五类） |
| **第一轮** | **TASK-014 Pilot + 独立测试集** | ✅ | `pilot_panel.tsv`（**30 份**）/ `independent_test_panel.tsv`（**25 份，已冻结**） |
| **第一轮** | **阶段总结与 GO/NO-GO** | ✅ | `docs/ROUND1_SUMMARY.md`（10 项规定输出，结论 **GO（有条件）**） |
| **补做** | **TASK-A011 检索公开研究论文**（原编号，B 无对应） | ✅ | `literature_review.md`（380 条记录 + 10 篇摘要）；**publication 字段回填 33.9%** |
| 历史提前项 | 性能基准测试 | 🔶 本机合成读段部分完成 | `bench2.sh` + `benchmark_results.md`：单样本 10× = 0.81 核时 |
| **本科版收敛** | **规范 C 与 SNP 预注册** | ✅ | `docs/UNDERGRADUATE_SCOPE.md`、`UNDERGRADUATE_TASK_LIST.md`、`snp_evaluation_design.md` |
| **服务器准备** | **1/5/30 + 独立 25 规范 manifest** | ✅（仅元数据） | `data/metadata/server/`；没有下载 FASTQ |
| **参考基因组** | **IRGSP-1.0 调查与偏倚方案** | 🔶 | 选择/记录方案完成；学校服务器未下载 |
| **工作流加固** | **联合 SNP、Pilot-only marker、低深度定点分型、指纹相似度** | 🔶 | 静态检查 116/116；核心单测 218 项通过（9 项需 matplotlib 跳过）；marker 选择、识别评估、指纹相似度、原型接口、PCA、shell 静态分析六层均经证伪审查并修复 7 个真实缺陷；shell 静态分析 0 发现；文档命令可执行性 0 发现；校验和完整性与失败退出码报法已锁为不变量；未在真实服务器执行 |
| **PCA（TASK-036）** | **`make_figures.py --only pca --similarity-matrix`** | 🔶 | 标准库实现，无 numpy 依赖；6 组解析算例验证（椭圆方差比、旋转不变性、共线、全同、空输入、非等长拒绝）；缺失格子按行均值填补、仅对角线行剔除，绝不产生"与所有品种相同"的伪造行；仅缺真实方阵 |
| **识别原型接口审计** | **`app/streamlit_app.py` 调用契约（TASK-042~045）** | 🔶 | 页面从未启动（本机无 streamlit），改按真实调用序列审计数据层并修复 2 个真实缺陷：LIKE 通配符从用户输入泄漏、无品种名参考样本可赢下识别却不可见；6 项反向测试证明两处修复均起作用；浏览器级验证仍待 `ricevar` 环境 |
| **相似度矩阵导出** | **`scripts/export_similarity_matrix.py`（TASK-036/037 前置）** | 🔶 | 长表 + 方阵 + summary 三份输出；与 `compare_varieties` 逐对等价（18/18 组合零差异，含异常行为一致）；不可比对品种对写空单元格而非 0，空库拒绝导出且不落盘；11 项单测；无真实数据库 |
| **识别评估层** | **低深度 recall / Top-1 / Top-5 / 拒识** | 🔶 | 代码完成并用合成 VCF 端到端验证；证伪审查修复 2 个真实缺陷（未标注查询稀释分母、id 空间不一致静默出 0.0），反向验证 2/2；无真实数据结果 |
| **指纹数据库** | **SQLite schema + 只读查询层（TASK-041/043~045）** | 🔶 | `database.py`/`dbquery.py`/`build_database.py` + 20 项单测通过；**无真实数据入库** |
| **识别原型** | **Streamlit 页面（TASK-042）** | 🔶 | `app/streamlit_app.py` 完成；无数据库时拒绝显示结果；未在真实库上启动 |
| **图表层** | **深度曲线 / recall / 相似度分布（TASK-036~040）** | 🔶 | `scripts/make_figures.py` + 11 项单测（含中文字体字形校验）；**无真实结果即不产图** |
| **论文骨架** | **论文章节 + 答辩提纲（TASK-047/048）** | 🔶 | `docs/thesis/` 五份文档；**第 1 章引言、2.1 数据来源、4.3 局限性（8 条）、4.4 应用前景已扩写为正式行文**；2.1 使用已复算的检索/整理事实（96,623 runs、32,564 候选、8,415 品种名、填充率 75.0%、334.71 GiB 声明量）并强制标注来源；**第 3 章结果与第 5 章结论仍全为占位符**；`verify_thesis_placeholders.py` 机械校验无虚构数值 |
| **附录 A 样本清单** | **`APPENDIX_A_samples.md` 自动生成** | ✅（生成物本身） | 55 样本 × 13 列完整元数据（accession/品种/亚种/平台/布局/估计深度/读长/声明字节/来源库/BioProject），由 `scripts/build_appendix_samples.py` 从两个清单生成；**生成前强制校验 7 项不变量**（面板规模 30/25、品种零重叠、面板内品种唯一、全双端、最低深度 ≥20×、run 号非空、panel_role 唯一），任一项不满足则不写文件；19 项测试覆盖，含 8 项注入式反例 |
| **附录 B 软件版本** | **`APPENDIX_B_software.md`** | ✅（整理事实） | 环境/工具/依赖版本**取自实测记录 `software_versions.txt`**（2026-09-15 实测），参数取自 `server/*.sh` 实际代码；明确区分"本机 WSL2 实测环境"与"学校服务器未知环境"；记录 fastp 使用默认参数、QC 阈值待 Pilot 分布审查后确定；**不声明任何校验和数值**（`reference_record.tsv` 尚未生成）；10 项测试逐版本号比对源文件 |
| **附录 E 可获得性** | **`APPENDIX_E_availability.md`** | ✅（整理事实） | 说明代码结构、数据来源、运行方式与复现条件；**明确声明本项目尚未纳入版本控制、实验尚未执行、不提供也不声称任何准确率/召回率/最低深度**；给出复现所需的四项前置条件与 334.71 GiB 声明空间；14 项测试校验其中每一条路径与仓库树真实存在，并复算 334.71 GiB |
| **版本控制基础** | **`.gitignore`** | ✅（工具本身） | 本项目此前**完全没有版本控制**（无 `.git`）；新增忽略规则：排除原始 FASTQ/BAM/CRAM/参考/中间产物与 110 MB XML 缓存，**但保留 `data/metadata/` 下全部整理产物与各输出目录的 `.gitkeep`**（否则克隆后脚本因目录不存在而失败）；10 项测试双向锁定（该忽略的必忽略、论文依赖的文件必保留、keep 规则所指路径必须真实存在） |
| **附录 C 位点筛选公式** | **`APPENDIX_C_marker_formula.md`** | ✅（方法定义） | 从 `scripts/select_snp_markers.py` **实际代码**逐条提取：区分度/MAF/判型率三个指标的完整公式、七步硬性过滤顺序、五键字典序排序规则（区分度→判型率→MAF→QUAL→出现次序，末项取负以保证全序可复现）、贪心物理间距过滤、候选池 = 50 × 最大档位、嵌套档位的**子集性质**、以及 `choices=["pilot"]` 的**代码级防泄漏约束**；26 项测试**在本文件内独立重算全部公式**并与代码逐值比对，而非仅比对参数 |
| **附录 D 复核记录** | **`APPENDIX_D_verification.md`** | ✅（整理事实） | 汇总全部轮次的对抗性证伪与变异测试：**26 项已修复缺陷**（9 项代码 + 17 项文档/工具/数据产物，连续编号且由测试强制；**曾一度误记为 23 项，因第 21 项与第 10 项实为同一缺陷，重复计数已更正**）、我自己写错的期望（诚实记录，含"测试失败应先怀疑期望"这条方法学经验）、以及**尚未复核事项的明确清单**（`bash -n`、图表渲染、Streamlit、真实数据运行**全部从未执行**）；附录本身受守卫检查，其讨论守卫规则的段落用显式标记区块隔离 |
| **检索产物来源与截断** | **`search_provenance.json`** + `record_search_provenance.py` | ✅（整理事实） | 查出一个**数据来源类缺陷（第 17 项）**：`ena_rice_wgs_runs.tsv` / `ena_rice_wgs_deep_runs.tsv` 行数恰为 5,000 / 10,000，等于两个脚本传入的 `limit=5000` / `limit=10000`，**属截断而非全量**；且派生的深度分档数字（32,478 / 24,633 / 10,707）**只在控制台打印过、从未存档**，无法从仓库复核。修复为：生成机读来源记录（显式标注截断）、两个下载脚本在行数等于 `limit` 时**打印截断警告**、撤下不可复核数字改用有存档来源的 96,623、15 项测试锁定"计数 ≠ 清单"这一区分**并界定影响范围**（两个冻结面板取自更大的 `candidate_samples.tsv`，不受影响，逐项断言） |
| **校验脚本可在真实数据上运行** | **`verify_pub_match.py` 的编码容错** | ✅（工具本身） | 按序运行全部 6 个校验脚本时它**以非零码退出**——**不是查出了问题，而是自己崩溃**：真实 Europe PMC 摘要含非断行空格（U+00A0），本机控制台为 GBK。这类缺陷对校验工具尤其危险，因为"崩溃"看起来与"没查出错"完全相同。修复为在导入时**一次性捕获真实控制台编码**并做替换容错（**不**依赖 `PYTHONIOENCODING` 环境变量）；**修复过程中我自己又错一次**：第一版用 `sys.stdout.encoding`，在 `redirect_stdout` 下回退 UTF-8 而漏过 `\xa0`，由测试直接证伪。8 项测试锁定；修复后该脚本**真正完成任务**（确认案例 B 实为稻飞虱抗性论文，属错配） |
| **占位符守卫边界** | **`verify_thesis_placeholders.py` 的四类数值判定** | ✅（工具本身） | 原守卫只认"设计常量/可疑结果"，现扩展为：设计常量、**数据整理事实（需同段溯源）**、**已校验的生成型附录（需横幅+声明值免责）**、以及一律判失败的结果指标；**修复既有漏洞**：原规则"数值 ≤1.0 且单位 ×"放行了实测深度（如 `0.98×`）；横幅匹配改为文档头部（Markdown 换行不破坏识别）；13 项边界测试锁定，其中 4 项专门证明豁免**无法被滥用** |
| **Shell 静态检查** | **本机无 Bash，用 Python 兜底校验 `server/*.sh`** | ✅（工具本身） | `verify_shell_static.py` 6 类检查 0 发现；`test_shell_static_detects.py` 证明能检出注入缺陷；**新增 46 项逐函数单测**（原只有端到端测试）；**修复 `strip_comments_and_strings` 把双引号内 `#` 当注释导致整行截断的缺陷**（`${frac#0.}`、`${#args[@]}` 均来自真实脚本，属漏报方向）；**脚本仍未在真实服务器执行** |
| **文档命令可执行性** | **`scripts/verify_documented_commands.py`** | ✅（工具本身） | 把 README/runbook/STATUS/PROJECT_STRUCTURE 里的 `python scripts/*.py` 调用逐个拿真实 `--help` 校验，并检查引用路径是否存在；10 项单测（含"注入改名参数/删除脚本/改名路径必须被发现"的反向验证）；**修复 README《如何复现实验》中的下载日志路径错误**（原写作仓库内相对路径，实际该日志由 `server/02_download.sh` 写到服务器 `$RV_ROOT/metadata/` 下，不在仓库内） |
| **参考基因组校验和不变量** | **`03_align.sh` 必须记录完整 SHA256** | ✅（工具本身） | `reference_genome_plan.md` 曾用现在时声称脚本"只截取前 16 位"，**实测代码早已改为完整摘要**（`sha256sum \| awk '{print $1}'`，9 列含 `gzip_sha256`/`fasta_sha256`）——错的是文档；已把该不变量变成 3 项机械检查，并用注入 `cut -c1-16` 的方式证明检查会失败；**从未在真实服务器产出 `reference_record.tsv`** |
| **失败退出码可读性** | **`run_all.sh` 报出失败阶段的真实退出码** | ✅（工具本身） | 原写法 `log "… $?"` 经推演**确认是正确的**（`then`/`else` 不是命令，参数在 `log` 执行前展开），但依赖排版巧合：在 `log` 前插入任何命令都会静默改掉报出的数字；已改为先 `rc=$?` 再使用，5 项静态测试含反向断言；**本机无可用 shell，该结论为语义推演而非实机验证** |
| **选择逻辑证伪审查** | **`select_snp_markers.py` 的 4 个疑似缺陷逐一证伪** | 🔶 | 4 个假设全部证伪（含精确 DP 对比 2 万次布局）；发现并修复 1 个形同虚设的测试；测试 2→12 项，变异测试 4/4；**从未在真实 joint VCF 上运行** |
| **识别评估层证伪审查** | **`evaluate_identification.py` 的 4 个疑似缺陷逐一验证** | 🔶 | 2 个真实缺陷已修复（未标注查询计入分母致准确率偏低；真值表 id 空间不一致时静默产出 0.0）；1 个证伪并锁为测试；1 个记为表述边界；测试 10→13 项，反向验证 2/2；报告 `docs/task_reports/ROUND4_evaluation_falsification_report.md` |
| **指纹相似度证伪审查** | **`fingerprint.py` + `compare_varieties` 的 5 个疑似缺陷逐一验证** | 🔶 | 1 个真实缺陷已修复（`compare_varieties` 的 `method` 参数从未被使用，硬编码 Hamming，UI 三选一形同虚设，且与识别层 IBS 尺度不一致）；3 个证伪并锁为测试；测试 26→36 项，反向验证 3/3（含夹具区分力守卫）；报告 `docs/task_reports/ROUND5_fingerprint_similarity_falsification_report.md` |

---

## 三、软件环境（TASK-002 成果）

```
Windows 11 23H2
  └─ WSL 2.7.14.0（内核 6.18.33.2-2）
       └─ Ubuntu 26.04.1 LTS
            └─ Miniconda3 /opt/miniconda3（conda 26.7.1）
                 └─ conda env ricevar  ← 全部工具已验证可用
```

**实测版本**：Python 3.11.16 / R 4.3.3 / samtools 1.24 / bcftools 1.24 / bedtools 2.31.1 /
bwa-mem2 2.3 / minimap2 2.31 / mosdepth 0.3.14 / fastp 1.3.7 / FastQC 0.12.1 /
KMC 3.2.4 / jellyfish 2.3.1 / Snakemake 9.24.0 / sra-tools 3.4.1 / seqkit 2.13.0

**冒烟测试全通过**：16 个 Python 库导入 + 16 个 CLI 工具 + `samtools→bcftools` 实跑链路。

**过程中解决的三个真实障碍**：
1. `wsl --install` 需管理员权限 → 提权完成；
2. WSL 内 GitHub / TUNA github-release 两条 Miniforge 源都失败 → 改用 **TUNA Miniconda3**；
3. 首版 `environment.yml` 求解爆炸（41 分钟、7 GB 内存未收敛）→ 改 `python=3.11` + 去掉 `r-tidyverse` + `channel_priority: strict`，**数秒求解成功**。

---

## 四、TASK-004 论文解析成果

论文：Niu et al., *Genome Biology* 2024;25:171（小麦 CNVb 数字指纹）
全文被 reCAPTCHA 拦截 → 改用 **NCBI E-utilities EFetch** 取到完整 JATS 全文。

**关键参数**：528 份材料建库（平均 5.4×）→ pan-genome `chrNCP`（17 组装/975 blocks/2.7 Gb）
→ 100 Kb 窗口 read-depth（<0.5 缺失、>1.5 重复）→ HMM 平滑 + 过滤 + 合并（8134）
→ 0.1× 稳定性过滤 → **1240 个 CNVb（1045 del + 195 dup）**；
**0.05× 平均 recall 99.3%**；**>0.05× 时 >99.9% 品种可准确分类**；
指纹 = **1240 位 0/1**；相似度 = **Jaccard** `M_share/(M_s1+M_s2−M_share)`；
阈值 **85%**（取自"不同品种"分布 99% 置信区间）。

**发现的三处风险**（已写入报告）：
- 原文内部矛盾：present 判据长度差 **<100 Kb vs <1 Mb** 两处不一致；
- **全文无 ROC/AUC**（→ 恰好是水稻项目的增量贡献点）；
- 补充材料/成本金额/下采样命令与种子均未获取到（已标注"禁止推测"）。

**对水稻的两个关键结论**：
- 小麦深度梯度是 **0.01/0.05/0.1/0.5/1/1.5×**，**没有 0.02× 和 0.2×**；
- **水稻 CNV 尺度与小麦差 3 个数量级**（水稻平均 19 个 CNV 区域、总长 142 Kb；
  小麦平均 2061 个、总长可达 GB 级）→ **100 Kb 窗口 + ≥100 Kb 阈值照搬到水稻会筛不出标记**，
  必须在 TASK-038 重新标定窗口（脚本已默认导出 10 kb/50 kb/100 kb/1 Mb 四档供比较）。

---

## 五、算力评估结论（2026-09-16 实测修订）

**本机实测**：Ryzen 9 7945HX（16C/32T）/ **内存 15.7 GB** / 单块 954 GB NVMe
（C: 174.6 + D: 249.9 = **424 GB 可用，且是同一块物理盘**）/ RTX 4060。

算力已实测（见第九节）：**单样本 10× 全基因组 = 墙钟 12.1 分钟 / CPU 0.81 核时**。

| 场景 | 可行性 | 瓶颈 |
| --- | --- | --- |
| Pilot 30 份 | ✅ 5–9 小时 | — |
| 180–200 份全流程 | ✅ 1.3–2.6 天 | 磁盘接近上限（约需 470 GB） |
| 1000+ 份原始 FASTQ | ❌ **磁盘不够**（需 2.0 TB 净数据） | **磁盘**（CPU 仅需 6.5–13 天，**可行**） |
| 参考论文的小麦规模（15 TB FASTQ） | ❌ 完全不可能 | 磁盘 + 内存 |

**关键修正**：原先判断 1000 份「CPU 不可行（需 65 天）」是**错误的**——
实测表明 CPU 只需 **6.5–13 天**。真正的硬约束是**磁盘容量**
（本机 424 GB vs 需求 4–5 TB 工作盘）。内存 15.7 GB 也**不是**瓶颈——
在 WSL 限 10 GB 的条件下仍跑通了全链路基准。

**反向结论**：水稻基因组只有小麦 **1/43**，做水稻可行、做小麦不可能——
从数据量角度印证了选水稻是对的。

---

## 六、架构决策：重活放服务器（2026-09-15 定）

**核心设计：不让 BAM 过网，只让"特征矩阵"过网。**

```
服务器：下载 → 质控 → 比对 → 分型 → 窗口深度 → ulcWGS 模拟 → 汇总导出
                                                          ↓ 只传矩阵
本机  ：标记筛选 → 指纹 → 相似度 → 阈值/ROC → 图表 → 论文
```

| 过网内容 | 体积 |
| --- | --- |
| 窗口深度矩阵（10 kb × 180 样本） | 13 MB |
| ulcWGS 各档深度矩阵（7 档×10 重复） | 910 MB |
| SNP 基因型矩阵（180 × 4M） | ~200 MB |
| k-mer / SV 矩阵 + QC 表 | 50–200 MB |
| **合计** | **≈ 3 GB**（对比：传 BAM 是 ~3 TB） |

**重要副作用**：之前评估里的两个瓶颈（16 GB 内存、424 GB 磁盘）**全部来自读级操作**。
这些留在服务器后，本机最大矩阵是 180×4M int8（720 MB）——
**不加内存也能完成论文**，升级内存只是让并行更舒服。

---

## 七、当前阻塞（1 项）

### ~~阻塞 1：本机 WSL 服务卡死~~ ✅ 已解决（2026-09-16 16:06）

重启 Windows 后完全恢复，环境逐项验证通过：工具 **0/14 缺失**、Python 库 **0/11 缺失**、
`samtools → bwa-mem2 → samtools sort → bcftools mpileup/call → mosdepth` 实跑链路通畅。
详见 `docs/task_reports/TASK-002_report.md` 第 5.1 节。

**两条重要经验**：

1. **本自动化会话（DSH）不具备提权能力**——`Start-Process -Verb RunAs` 会阻塞等待 UAC
   （自动化进程不在用户交互桌面上，对话框弹不出来），`schtasks /create /rl HIGHEST` 被
   `Access is denied` 拒绝。**需要管理员权限的操作必须由人工执行**；
   已备好 `fix_wsl.cmd`（双击自动请求提权）作为下次的恢复入口。
2. 已创建 `C:\Users\86159\.wslconfig`（此前不存在），实测生效：
   内存上限 10 GB（实测 9.7Gi）、CPU 16 核、swap 16 GB 放 D 盘、
   `sparseVhd=true`（防止 `ext4.vhdx` 只涨不缩吃满 C 盘）、`autoMemoryReclaim=gradual`。

### 阻塞 2：服务器信息未知（需向管理员确认）

调度器（Slurm/PBS/单机）、外网可达性、存储配额三项均未知。
→ 已用 `server/00_probe.sh` 把这三项变成"跑一个脚本 5 分钟出答案"。
→ **本机 WSL 外网已确认畅通**（EBI / TUNA / NCBI 均返回 HTTP 200，参考基因组下载验证通过），
   可作为服务器下载能力的参照基线。

---

## 八、下一步（按优先级）

| 优先级 | 事项 | 状态 |
| --- | --- | --- |
| ⏸️ | ~~项目暂停~~ → **已恢复**：2026-09-20 用户下达《AI Agent 项目总任务书》并要求执行第一轮 | ✅ 第一轮 TASK-011~014 已完成 |
| ★★★ | 向管理员确认服务器三项信息 | 🔶 **问题清单已备好**：`docs/server_admin_questions.md`（可直接转发；或上传 `server/` 跑 `00_probe.sh`） |
| ★★☆ | 跑 Pilot（**30 份**，已选定，见 `pilot_panel.tsv`） | ⬜ **待下载**（约 171 GiB），见 `docs/methods/server_pilot_runbook.md` |
| ★★☆ | 冻结独立测试集 | ✅ **已冻结**：25 份，`independent_test_panel.tsv`，种子 20260920 |
| ★☆☆ | 复测 DDBJ Search API（择期） | ⬜ 2026-09-16 实测全线 504，见 `TASK-010_report.md` |
| ~~★☆☆~~ | ~~统计 `subspecific genetic lineage name` 字段填写率~~ | ✅ 2026-09-20 完成：**0.1%**（`cultivar` 才是主力，72.4%）——**并据此更正了 TASK-009 报告的错误结论** |
| ~~★★★~~ | ~~TASK-011 候选样本整理 / TASK-012 名称标准化 / TASK-013 去重 / TASK-014 建面板~~ | ✅ 2026-09-20 完成（第一轮） |
| ~~★★★~~ | ~~TASK-007 四条候选标记体系~~ | ✅ 2026-09-16 完成（Phase 2） |
| ~~★★★~~ | ~~TASK-008 / 009 / 010 公共数据检索~~ | ✅ 2026-09-16 完成（Phase 3；TASK-010 部分完成） |
| ~~★★★~~ | ~~重启 Windows 恢复 WSL~~ | ✅ 2026-09-16 完成（工具 0/14 缺失） |
| ~~★★☆~~ | ~~TASK-005 / TASK-006~~ | ✅ 2026-09-16 完成（Phase 1 收尾） |
| ~~★☆☆~~ | ~~写 `.wslconfig`~~ | ✅ 2026-09-16 完成（内存 10 GB、swap 放 D:） |
| ~~★☆☆~~ | ~~决定 LICENSE~~ | ✅ 2026-09-16 决定：**推迟到投稿时确定**（见 README §10） |

---

## 九、本机算力实测（2026-09-16 完成）

用**真实** IRGSP-1.0 参考序列（375,049,285 bp）在 1 号染色体（43.27 Mb）上做 10× 全基因组基准，
脚本 `scripts/bench2.sh`，用 `/usr/bin/time` 采集 wall / user / sys / maxRSS：

| 指标 | 结果 |
| --- | --- |
| 单样本 10× 全基因组 | **墙钟 12.1 分钟，CPU 0.81 核时** |
| 现实估算（施加 3–6× 真实数据惩罚） | 约 **2.5 – 5 核时/样本** |
| 最重步骤 | **bwa-mem2 比对占 69.8% 核时**（**不是**变异检测，后者仅 15.8%） |
| 1000 样本 | 本机 16 线程 **6.5 – 13 天**（原估算 65 天，**高估 5–10 倍**） |

**结论修正**：**本机瓶颈是磁盘，不是 CPU。**

- 旧判断：「1000 样本本机需 65 天，CPU 不可行」
- 新判断：「1000 样本本机约 1–2 周，**CPU 可行**；但需净数据 2.0 TB + 工作盘 4–5 TB，
  本机仅 424 GB 可用，**存储不可行**」

因此「服务器下载+比对、本机分析+写作」的方案**依然正确**，但理由应从
~~「算力不够」~~ 修正为 **「磁盘装不下」**。对本机的准确表述是：
**CPU 足以承担 Pilot 与 ≤200 份规模的实验，服务器主要承担数据存储与批量预处理。**

> ⚠️ 该基准使用**合成读段**（源自参考本身、不含真实变异），因此是**成本下界**。
> 完整的 5 条乐观性说明、方法学教训与交叉验证见 `docs/methods/benchmark_results.md`。

---

## 十、交付物索引

**任务报告**：`docs/task_reports/TASK-001~014_report.md`

**★ 阶段总结**：
- `docs/ROUND1_SUMMARY.md` — **第一轮总结**（10 项规定输出 + **GO（有条件）** 判断）
- `docs/TASK_NUMBERING.md` — **三套任务规范对照表**（规范 C 现行，A/B 历史）

**方法学文档**：
- `docs/methods/paper_niu2024_extraction.md` — 论文全文技术解析（601 行）
- `docs/methods/paper_workflow.md` — **论文技术路线图**（TASK-005：主线八阶段 + 原文 Step 0–7 全参数）
- `docs/methods/wheat_to_rice_migration.md` — **小麦→水稻迁移表**（TASK-006：13 环节逐项迁移判定）
- `docs/methods/marker_routes.md` — **四条候选标记体系**（TASK-007：四路线 + 统一比较框架 + 假设清单）
- `docs/methods/data_source_survey.md` — **公开数据源调研**（TASK-008/009/010：三库对照 + 品种名字段发现）
- `docs/methods/literature_review.md` — **文献综述**（TASK-A011：★★ 两条会改变项目论证方式的发现）
- `docs/methods/compute_feasibility_assessment.md` — 本机算力可行性评估
- `docs/methods/benchmark_results.md` — **本机算力实测基准**（2026-09-16，含偏差分析）
- `docs/methods/server_local_split_design.md` — 服务器/本机分工架构
- `docs/methods/server_pilot_runbook.md` — Pilot 运行手册
- `docs/server_admin_questions.md` — ★ **服务器使用咨询清单**（可直接转发给管理员；含"2 分钟版 5 问"）

**成本测算**：
- `docs/COST_ESTIMATE.md` — 全项目软件+硬件成本（结论：软件 ¥0、数据免费，推荐方案现金支出 ¥0–700）

**服务器端流水线**（`server/`）：
`config.sh` / `00_probe.sh` / `01_setup_env.sh` / `02_download.sh` / `03_align.sh` /
`04_variant_depth.sh` / `04_joint_snp.sh` / `prepare_marker_targets.sh` /
`05_simulate.sh` / `06_export.sh` / `07_identify.sh` /
`run_all.sh` / `build_matrices.py`。另有 `workflow/Snakefile` 薄编排骨架。

**本机侧代码**（不需服务器即可完成与验证）：
- `src/ricevar_id/` — 标准库实现：`fingerprint.py`（相似度）、`genotypes.py`（矩阵读取/投影）、
  `database.py`（SQLite schema + 建库）、`dbquery.py`（只读查询层）、`query_input.py`（上传表解析）
- `scripts/build_database.py` — 建库 CLI（默认 `database/ricevar_id.sqlite`）
- `scripts/make_figures.py` — 论文图生成（无真实结果文件则不产图）
- `app/streamlit_app.py` — 识别原型（无数据库时不显示任何结果）
- `docs/thesis/` — `THESIS_DRAFT.md` 章节骨架、`DEFENSE_SLIDES.md` 答辩提纲、
  `PLACEHOLDER_CONVENTIONS.md` 占位符与结果出处约定

**验证脚本**（`scripts/`）：
`verify_undergraduate_scope.py`（116 项静态检查）/ `verify_stage_order.py`（23 项阶段顺序回归）/
`verify_thesis_placeholders.py`（论文骨架虚构数值机械检查）/ `verify_shell_static.py`（shell 静态分析，6 类）/
`verify_documented_commands.py`（文档中的命令与路径可执行性）/
`round1_verify.py`（28 项第一轮文档校验）


**本机侧**：`local/import_export.sh`；识别评估脚本 `scripts/evaluate_identification.py`

**数据**：
- `data/metadata/server/` — 现行本科版服务器清单：Pilot 1/5/30 与冻结独立 25
- `data/metadata/pilot_samples.tsv` — 历史早期 5 份样本表（不再是默认输入）
- `data/metadata/search/` — **公开数据检索结果**（TASK-008/009/010）：
  - `ncbi_search_summary.tsv` — NCBI 13 条查询命中数 + 执行证据（`querytranslation`）
  - `ncbi_count_verification.tsv` — 命中数稳定性核验
  - `ncbi_sra_esummary.json` / `ncbi_sra_runs.tsv` — 300 条 SRA 实验的原始响应与解析表
  - `ena_search_summary.tsv` — ENA 命中数矩阵
  - `ena_rice_wgs_runs.tsv` — 5,000 条（默认排序，**含偏倚，仅作参照**）
  - `ena_rice_wgs_deep_runs.tsv` — ★ **10,000 条 ≥5×，含 FASTQ 直链**
- `data/metadata/candidates/` — **★ 第一轮产出（TASK-011~014）**：
  - `candidate_samples.tsv` — **候选样本主表（32,564 run × 34 列）**
  - `ena_candidates_raw.tsv` — ENA 原始响应（29 列）
  - `sample_attrs.tsv` — 21,654 个样本的 XML 属性
  - `variety_alias.tsv` / `variety_canonical.tsv` — 品种名映射与 **8,415 个规范品种**
  - `unresolved_names.txt` — 712 个待人工核对的编号型名称
  - `duplicate_samples.tsv` — 1,326 组重复检查结果（分五类）
  - `name_quality_report.txt` / `panel_selection_log.txt` — 质量与选样日志
  - **`pilot_panel.tsv`** — ★ **Pilot Panel 30 份**（170.70 GiB）
  - **`independent_test_panel.tsv`** — ★ **独立测试集 25 份（已冻结）**（164.02 GiB）
  - `xml_cache/` — 109 个 XML 批次缓存（支持断点续跑）

**环境**：`environment.yml` / `server/environment.server.yml` / `requirements.txt` /
`software_versions.txt` / `setup_wsl_env3.sh`

**工具**：
- `scripts/bench2.sh` — **水稻规模真实吞吐基准**（★ 现行版本）
- `scripts/bench_run.sh` — 激活 ricevar 环境后运行基准
- `scripts/verify_env.sh` — 环境全项自检（资源/工具/库/实跑链路/磁盘）
- `scripts/fetch_rice_ref.sh` — 下载 IRGSP-1.0 参考序列
- `scripts/bench.sh` — v1 玩具级基准（20 Mb 参考，**已废弃，勿引用其数字**）
- `scripts/smoke_test.sh` / `scripts/collect_env_versions.sh` — 环境自检与版本采集
- `fix_wsl.cmd` / `recover_wsl2.ps1` — WSL 服务修复（**需人工提权**）

**数据检索脚本**（TASK-008/009/010）：
- NCBI：`search_ncbi.sh`（含执行证据抓取）/ `fetch_ncbi_esummary.sh` / `verify_ncbi_counts.sh` / `parse_ncbi_esummary.py` / `inspect_esummary.py`
- ENA：`search_ena.sh` / `search_round2.sh`（按深度过滤）/ `analyze_deep.sh` / `inspect_ena.sh` / `probe_ena_samples.sh`（**品种名字段验证**）
- DDBJ：`probe_ddbj.sh` / `probe_ddbj2.sh`（多路径探测，证明 API 全线故障）/ `show_sample_attrs.sh`

---

## 十一、已知缺口（诚实清单）

1. **流水线脚本从未在真实服务器上执行过** —— 服务器信息未知，首次务必先跑 `00_probe.sh`，再用 `pilot_smoke1.tsv` 单样本试跑。
2. ~~**本机吞吐实测未完成**~~ ✅ **已于 2026-09-16 完成**（见第九节）。
   但仍有两项**待实测**：①用 Pilot 真实数据（而非合成读段）重跑基准；
   ②ulcWGS 降采样成本（现为推算的 1.5 核时/样本）。
   此外**未实测** fastp 质控与多样本并行下的总吞吐。
3. **现行 Pilot 30 是元数据分层面板，不是群体遗传学代表性抽样**（indica 8、japonica 8、aus 4、temperate_japonica 2、aromatic 1、admixed 1、unknown 6）；论文须如实报告标签缺失与类群代表性限制。
4. **R 生态未装**（tidyverse 等）—— 为让 conda 求解收敛而移除，按需在 Phase 6 前单独安装。
5. ~~**LICENSE 未创建**~~ ✅ **已决定推迟**（2026-09-16）：项目 100% 使用公开数据、
   不做新湿实验；目标期刊通常会指定或推荐许可协议，现在选定可能返工。
   触发条件：论文定稿投出前按期刊要求创建。**这是主动决策，不是遗留缺口。**
6. ~~**TASK-005 / TASK-006 未做**~~ ✅ **已于 2026-09-16 完成**（Phase 1 收尾）。
   但**迁移文档中的关键参数仍待实测确定**：最优窗口大小、CNV 路线 AUC 能否超过 SNP、
   判定阈值取值、0.05× 能否达论文的 99.3% recall —— 属 Phase 2 及以后的工作，
   已列入 `wheat_to_rice_migration.md` 第 6 节「水稻侧待确定的问题」。
7. **Phase 0–1 复核查出的 2 处依赖缺陷已修复**（`environment.yml` 的 jellyfish 包名错误→
   复现性 bug；`hmmlearn` 缺失→阻塞 CNV 路线），详见 `TASK-002_report.md` 第七节。
   此处保留记录以免复发。
