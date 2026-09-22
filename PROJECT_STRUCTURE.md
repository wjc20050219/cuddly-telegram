# RiceVar-ID 项目目录结构

> TASK-001 输出 · 创建日期：2026-09-15
> 项目：基于超低深度全基因组测序（ulcWGS）的水稻品种数字身份证系统

## 目录总览

```
RiceVar-ID/
│
├── UNDERGRADUATE_TASK_LIST.md # ★ 现行本科版任务清单（TASK-001–048）
├── TASK_LIST.md              # 历史完整科研版清单（规范 A，TASK-001–053）
├── PROJECT_STRUCTURE.md      # 本文件：目录结构说明
├── README.md                 # 项目总览（TASK-003 输出）
├── LICENSE                   # 待定开源协议
│
├── data/                     # 所有数据文件
│   ├── metadata/             # 样本元数据表（candidate_samples.tsv、variety_alias.tsv 等）
│   ├── raw/                  # 原始测序数据（FASTQ，不进入 Git）
│   ├── processed/            # 质控后数据、比对结果（BAM）、矩阵文件
│   └── qc/                   # FastQC / fastp / mapping QC 报告
│
├── reference/                # 参考基因组（IRGSP-1.0 等）及索引、版本记录
│
├── workflow/                 # Snakemake / Nextflow 工作流定义
│
├── server/                   # ★ 服务器端流水线（下载/比对/分型/模拟/导出）
│   ├── config.sh             #   共享配置
│   ├── 00_probe.sh           #   环境探测（调度器/外网/存储/软件）
│   ├── 01_setup_env.sh       #   conda 环境准备
│   ├── 02_download.sh        #   ENA 下载 + MD5 校验 + 下载日志
│   ├── 03_align.sh           #   fastp → bwa-mem2 → CRAM
│   ├── 04_variant_depth.sh   #   mosdepth 窗口深度
│   ├── 04_joint_snp.sh       #   bcftools 多样本联合 SNP calling
│   ├── prepare_marker_targets.sh # 冻结 marker VCF → 定点分型目标
│   ├── 05_simulate.sh        #   ulcWGS 下采样 + 可选固定 marker 分型
│   ├── 06_export.sh          #   特征矩阵汇总 + MANIFEST
│   ├── 07_identify.sh        #   低深度 recall / 识别率 / 拒识评估
│   ├── build_matrices.py     #   矩阵构建工具
│   └── run_all.sh            #   编排（Slurm/单机自动识别）
│
├── local/                    # ★ 本机侧脚本
│   └── import_export.sh      #   rsync + SHA256 校验 + 矩阵检查
│
├── scripts/                  # 辅助脚本（含 manifest 构建、SNP marker 筛选、识别评估、
│                             #   建库 build_database.py、相似度全矩阵 export_similarity_matrix.py、
│                             #   绘图 make_figures.py、静态与论文校验）
│
├── src/                      # 核心可复用代码包（IBS/Hamming/Jaccard、Top-k、marker recall、
│                             #   基因型矩阵读取、SQLite 建库与只读查询、上传表解析）
│
├── app/                      # Streamlit 识别原型（无数据库时拒绝显示任何结果）
├── results/                  # 分析结果
│   ├── statistics/           # 描述性统计（样本数、深度分布、QC 汇总）
│   ├── markers/              # 各路线标记筛选结果（SNP / k-mer / CNV / SV）
│   ├── fingerprints/         # 品种数字指纹（二进制矩阵、二维码数据）
│   └── validation/           # 模拟实验与独立测试集验证结果
│
├── figures/                  # 论文与报告用图
│
├── database/                 # 品种指纹数据库（构建于 Phase 后期）
│
├── web/                      # Web 查询系统（品种鉴定前端与后端）
│
├── tests/                    # src/ 代码的自动化测试
│
└── docs/                     # 文档
    ├── methods/              # 方法学笔记
    │   └── _raw/             # 论文原文抓取存档（**本机保留，不入库**，见下）
    ├── task_reports/         # 每个 TASK 的执行报告
    └── manuscript/           # 论文草稿
```

## 约定

- `data/raw/`、`reference/`、`data/processed/` 下的大文件**不纳入版本控制**，仅记录来源、版本与校验和（见 `download_log.tsv`）。
- 每个 TASK 完成后在 `docs/task_reports/` 落一份 `TASK-XXX_report.md`。
- 空目录以 `.gitkeep` 占位，待真实文件进入后移除。

## 目录计数说明（避免"19 个"与"25 个"混淆）

`TASK_LIST.md` 第三节规定的**标准子目录共 19 个**：`data/` 下 4 个、`results/` 下 4 个、
`docs/` 下 3 个，加 `reference/`、`workflow/`、`scripts/`、`src/`、`figures/`、
`database/`、`web/`、`tests/`。

本仓库**实际有 25 个目录**，多出的 6 个是：

| 类型 | 目录 | 说明 |
| --- | --- | --- |
| 父目录（3） | `data/`、`results/`、`docs/` | 规范中作为层级出现，本身也是目录 |
| **计划外新增（3）** | `server/` | 服务器端流水线（2026-09-15 架构决策新增） |
| | `local/` | 本机侧导入导出脚本 |
| | `docs/methods/_raw/` | 论文原文抓取存档（仅存在于开发机，`.gitignore` 排除，见下） |

> 结论：**规范要求的 19 个目录全部已创建**，且额外增加了 3 个；无缺失。
> 新增目录均已在本文档上方的目录树中登记。

## 当前状态

- [x] Phase 0 · TASK-001：目录结构创建（本文件）
- [x] Phase 0 · TASK-002：软件环境（environment.yml / requirements.txt / software_versions.txt + WSL2 部署）
- [x] Phase 0 · TASK-003：README
- [x] Phase 1 · TASK-004：参考论文解析（`docs/methods/paper_niu2024_extraction.md`、`docs/task_reports/TASK-004_report.md`）
- [x] Phase 1 · TASK-005：论文技术路线图（`docs/methods/paper_workflow.md`、`docs/task_reports/TASK-005_report.md`）
- [x] Phase 1 · TASK-006：小麦 → 水稻技术迁移表（`docs/methods/wheat_to_rice_migration.md`、`docs/task_reports/TASK-006_report.md`）
- [x] Phase 2 · TASK-007：四条候选标记体系（`docs/methods/marker_routes.md`、`docs/task_reports/TASK-007_report.md`）
- [x] Phase 3 · TASK-008：检索 NCBI SRA（`data/metadata/search/ncbi_*.tsv`、`docs/task_reports/TASK-008_report.md`）
- [x] Phase 3 · TASK-009：检索 ENA（`data/metadata/search/ena_rice_wgs_deep_runs.tsv`、`docs/task_reports/TASK-009_report.md`）
- [~] Phase 3 · TASK-010：检索 DDBJ（**部分完成**：官方 API 全线 504，数据经 INSDC 镜像库获取；`docs/task_reports/TASK-010_report.md`）
- [x] Phase 3 · 数据源调研汇总（`docs/methods/data_source_survey.md`）

### 第一轮（补充任务书 B，TASK-011~014）· 2026-09-20 完成

> 本节是规范 B 阶段的历史记录；当前执行规范为 C，编号差异见 `docs/TASK_NUMBERING.md`。

- [x] TASK-011 候选样本整理 → `data/metadata/candidates/candidate_samples.tsv`（**32,564 run × 34 列**，品种名可用 14,830 条）
- [x] TASK-012 品种名称标准化 → `variety_alias.tsv`（8,501 行）/ `variety_canonical.tsv`（**8,415 个规范品种**）
- [x] TASK-013 重复样本检查 → `duplicate_samples.tsv`（1,326 组，五类）
- [x] TASK-014 Pilot + 独立测试集 → `pilot_panel.tsv`（**30 份**）/ `independent_test_panel.tsv`（**25 份，已冻结**）
- [x] 第一轮总结 → `docs/ROUND1_SUMMARY.md`（10 项规定输出 + **GO（有条件）**）
- [x] 任务编号对照 → `docs/TASK_NUMBERING.md`

**本阶段新增数据目录**：`data/metadata/candidates/`（候选表、面板、XML 缓存）

### 现行本科版（规范 C）

- 现行范围：`docs/UNDERGRADUATE_SCOPE.md`
- 现行任务：`UNDERGRADUATE_TASK_LIST.md`
- 服务器规范清单：`data/metadata/server/`（Pilot 1/5/30 与冻结独立 25）
- 主线收敛为 SNP；历史 k-mer/CNV/SV 目录与文档保留但不再是必做。
