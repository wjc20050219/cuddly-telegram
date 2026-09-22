# RiceVar-ID

**基于超低深度全基因组测序（ulcWGS）的水稻品种数字身份证系统**

> 全部基础数据来自公开数据库（NCBI SRA / ENA / DDBJ）；不做新的湿实验，
> ulcWGS 通过对真实高/中深度 WGS 数据计算机抽样模拟。

## 1. 项目目标

本项目现已收敛为**本科毕业论文最小可行系统**：

```
真实公开数据 → FastQC/fastp → IRGSP-1.0 比对 → 联合 SNP calling
→ 500/1000/2000 SNP 指纹 → 六档超低深度模拟 → 品种识别
→ SQLite + Streamlit 原型 → 本科论文
```

SNP 是唯一必做 marker 主线；k-mer 仅在主线全部完成后作为可选扩展，CNV/SV/PAV 与复杂平台不作为本科必做。现行范围见 [`docs/UNDERGRADUATE_SCOPE.md`](docs/UNDERGRADUATE_SCOPE.md)，任务见 [`UNDERGRADUATE_TASK_LIST.md`](UNDERGRADUATE_TASK_LIST.md)。

最终系统输入一份低深度水稻 SNP 指纹，即可输出：

- 最可能的品种与 Top 5 候选；
- 相似度与匹配置信度、差异标记数量；
- 品种数字身份证（二维码 / DNA Fingerprint）;
- 数据来源与文献来源。

## 2. 核心科学问题

1. 真实公开 WGS 是否能建立可区分 20–30 个水稻品种的 SNP 数字指纹？
2. 在 1 / 0.5 / 0.2 / 0.1 / 0.05 / 0.02× 六档深度下，Top-1 与 marker recall 如何变化？
3. 500 / 1000 / 2000 个 SNP 中，哪一档能在工作量与识别效果间取得合理平衡？
4. 如何用 Pilot 内部验证校准拒识阈值，并用零重叠独立面板检验开放集误指派风险？

所有最低深度、准确率与阈值均待真实 FASTQ 计算，不能提前设定。

## 3. 数据来源

**已完成检索（Phase 3，TASK-008/009/010）**，详见
[`docs/methods/data_source_survey.md`](docs/methods/data_source_survey.md)：

| 来源 | 水稻 WGS 记录 | 可用性 |
| --- | ---: | --- |
| **ENA**（主下载源） | 96,623（其中 **≥10× 有 24,633**） | ✅ API 稳定，FASTQ 直链直接可得 |
| NCBI SRA / BioProject / BioSample | 106,474 / 9,450 / 218,272 | ✅ API 正常，用于交叉核验 |
| DDBJ DRA | 经 INSDC 镜像可见 1,255（≥5×） | ⚠️ **官方 API 全线 504**，数据改经 ENA/NCBI 获取 |

- 公开研究论文检索已完成，见 `docs/methods/literature_review.md`；
- 主参考固定为 IRGSP-1.0，见 `docs/methods/reference_genome_plan.md`。

> **数据供给不是瓶颈**（≥10× 有 24,633 条），但**品种名覆盖才是真瓶颈**：
> ≥5× 的 32,564 条 run 中，仅 **45.5%（14,830 条）**能提取出可用品种名，
> 不可改善部分达 48.2%（字段全空 + 提交者填了 INSDC 缺失值）。
> 本项目的真正约束是**磁盘与算力**。

## 4. 技术路线

### 4.1 分析流程总览

**本科版现行流程**：

```text
公开 FASTQ
  → FastQC + fastp
  → BWA-MEM2 / samtools（CRAM）
  → Pilot 多样本联合 bcftools calling
  → SNP QC 与区分度排序（只用 Pilot）
  → 冻结 500 / 1000 / 2000 SNP 集
  → 六档降采样、每档 3–5 个 seed
  → 固定位点分型与 IBS/Hamming
  → Top-1 / Top-5 / marker recall / 开放集拒识
  → PCA、热图、准确率图
  → SQLite + Streamlit
```

正式 SNP 矩阵必须来自多样本联合 VCF或固定 marker 定点分型。不能把多个仅含变异位点的单样本 VCF 直接拼接，因为某样本“未出现该位点”不等于已确认 `0/0`。完整预注册设计见 [`docs/methods/snp_evaluation_design.md`](docs/methods/snp_evaluation_design.md)。

历史四路线设计仍保存在 `docs/methods/marker_routes.md`，仅作研究档案；不再是本科版交付要求。

## 5. 软件环境（已建成）

环境三层结构：

```
Windows 11 → WSL 2.7.14（内核 6.18.33.2）→ Ubuntu 26.04.1 LTS
          → Miniconda3 /opt/miniconda3（conda 26.7.1）
          → conda env ricevar
```

进入环境：

```bash
wsl -d Ubuntu -u root
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate ricevar
```

- 环境规格见 `environment.yml`（Python 3.11 / R 4.3），Python 依赖见 `requirements.txt`；
- 实测版本清单（samtools 1.24、bwa-mem2 2.3、mosdepth 0.3.14、KMC 3.2.4、
  Snakemake 9.24 等全部工具已逐项验证）见 `software_versions.txt`；
- 通道与 PyPI 均指向 TUNA 镜像，`channel_priority: strict`；
- 一键重建：`bash setup_wsl_env3.sh`（WSL 内以 root 运行）；
- 资源限制见 `C:\Users\86159\.wslconfig`（内存上限 10 GB、swap 16 GB 放 D 盘、
  `sparseVhd=true` 防止虚拟磁盘只涨不缩吃满 C 盘）；
- **环境自检**：`bash scripts/verify_env.sh`（资源 / 工具 / Python 库 / 实跑链路 / 磁盘一次查完）。

> **已知事件与恢复入口**：2026-09-15 19:02 WSL 服务因 `wslsettings.exe` 崩溃而卡死，
> 2026-09-16 重启后完全恢复（工具 0/14 缺失）。下次若再卡死，双击 `fix_wsl.cmd`
> （自动请求提权）或运行 `recover_wsl2.ps1`。
> **注意**：需要管理员权限的操作无法由自动化会话完成——自动化进程不在交互桌面上，
> UAC 对话框弹不出来。

## 6. 目录结构

见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)。要点：

- `data/{metadata,raw,processed,qc}` — 数据四层；
- `results/{statistics,markers,fingerprints,validation}` — 结果四类；
- `docs/task_reports/` — 每个 TASK 一份执行报告；
- 大文件（FASTQ/BAM/参考基因组）不入库，只记录来源与校验和。

## 7. 如何运行

**运行架构（2026-09-15 决策）**：重活放学校服务器，分析与写作放本机。

```
服务器：下载 → 质控 → 比对 → 分型 → 窗口深度 → ulcWGS 模拟 → 汇总导出
                                                              ↓ 只传特征矩阵（GB 级）
本机  ：标记筛选 → 指纹 → 相似度 → 阈值/ROC → 图表 → 论文
```

- 架构设计：`docs/methods/server_local_split_design.md`
- Pilot 运行手册：`docs/methods/server_pilot_runbook.md`
- 算力评估：`docs/methods/compute_feasibility_assessment.md`

```bash
# 【服务器】先探测环境（5 分钟，回答调度器/外网/存储三个未知数）
cd ~/ricevar/server && bash 00_probe.sh

# 【本机】先生成并验证服务器样本清单（不下载 FASTQ）
python scripts/build_server_manifests.py
python scripts/verify_undergraduate_scope.py

# 【服务器】上传 server/ 与 pilot_smoke1.tsv 后建环境并单样本试跑
bash 01_setup_env.sh
source ~/miniconda3/etc/profile.d/conda.sh && conda activate ricevar
RV_SAMPLES="$HOME/ricevar/metadata/pilot_smoke1.tsv" bash run_all.sh 02 2>&1 | tee logs/run_smoke1.log

# 单样本通过后再换 pilot_smoke5.tsv；不要直接启动 30+25 全量

# 【本机，WSL 内】拉回特征矩阵并校验
wsl -d Ubuntu -u root
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate ricevar
bash /mnt/d/dsh/RiceVar-ID/local/import_export.sh user@server:~/ricevar/export
```

## 8. 如何复现实验

1. 按 `software_versions.txt` 锁定的版本部署环境；
2. 按服务器 `$RV_ROOT/metadata/download_log.tsv` 中记录的 accession 与校验和
   重新下载原始数据（该日志由 `server/02_download.sh` 在服务器上生成，
   **不在本仓库内**；仓库内的 `data/metadata/` 只存放检索与面板元数据）；
3. 先执行 1 样本与 5 样本 smoke test，再运行完整 Pilot；
4. marker 集与阈值在查看冻结独立面板结果前固定；
5. 每次下载、抽样与导出均保留 checksum、工具版本和随机 seed。

## 9. 当前研究状态

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Phase 0 | 项目初始化 | ✅ **完成**：TASK-001 ✅ / TASK-002 ✅（环境已建成并逐项验证）/ TASK-003 ✅ |
| Phase 1 | 小麦论文技术路线解析 | ✅ **完成**：TASK-004 ✅（逐节解析）/ TASK-005 ✅（技术路线图）/ TASK-006 ✅（迁移表） |
| Phase 2 | 候选标记体系 | ✅ **完成**：TASK-007 ✅（四条路线 + 统一比较框架 + 诚实假设清单） |
| Phase 3 | 公共数据搜索 | ✅ **完成**：TASK-008 ✅（NCBI）/ TASK-009 ✅（ENA）/ TASK-010 ⚠️（DDBJ 官方 API 故障，数据经 INSDC 镜像库获取） |
| Phase 4–5 | 样本库与 Pilot 数据集 | ✅ **第一轮完成（2026-09-20，TASK-011~014）**：候选样本表 **32,564 run**（品种名可用 14,830，8,415 个规范品种）；**Pilot Panel 30 份 + 独立测试集 25 份（已冻结）**；详见 [`docs/ROUND1_SUMMARY.md`](docs/ROUND1_SUMMARY.md) |
| 本科 TASK-010~017 | 下载 / QC / IRGSP-1.0 / 比对 | 🔶 脚本与方案已有；学校服务器未 probe、未下载 FASTQ |
| 本科 TASK-018~025 | SNP / 指纹 / 识别 | 🔶 联合 calling 与评估方案已有；无真实 VCF、指纹或准确率 |
| 本科 TASK-026~040 | 六档降采样与图表 | ⬜ 无真实 CRAM，尚未执行 |
| 本科 TASK-041~048 | SQLite / Streamlit / 论文 / PPT | ⬜ |

> **第一轮结论：GO（有条件）** —— 数据基础真实可用；放行条件为确认服务器
> 存储 ≥600 GiB、能访问 EBI、≥8 核/作业。
> **注意：至今未下载任何测序数据，未跑任何基因组分析。**
> 三套任务规范的编号差异见 [`docs/TASK_NUMBERING.md`](docs/TASK_NUMBERING.md)；现行使用本科版规范 C。
>
> **文献检索（原 TASK-011，已补做）**：见
> [`docs/methods/literature_review.md`](docs/methods/literature_review.md)。
> ★ 两条关键发现：①**没有"超低深度做品种鉴定"的先例**（新颖性来源，但审查会更严）；
> ②**现有低深度文献全部依赖"填补"**，与本项目的"直接检测"范式不同，
> **不能直接引用其阳性结论**。

**计划外但已完成的三项工作**（为降低后续返工风险而提前做）：

1. **环境全项自检**（`scripts/verify_env.sh`）：关键工具 0/14 缺失、Python 库 0/11 缺失、
   `samtools → bwa-mem2 → bcftools → mosdepth` 实跑链路通畅；
2. **本机算力实测**（`scripts/bench2.sh`）：用真实参考序列测得单样本 10× 全基因组
   = **墙钟 12.1 分钟 / CPU 0.81 核时**。该结果**推翻了此前的文献估算**（原估 10–31 核时），
   并查明**本机瓶颈是磁盘而非 CPU**。详见 `docs/methods/benchmark_results.md`；
3. **Phase 0–1 四项任务复核**：逐条对照 `TASK_LIST.md` 核验 TASK-001~004，
   查出并修复 **2 处真实依赖缺陷**（`environment.yml` 的 jellyfish 包名错误 → 复现性 bug；
   `hmmlearn` 完全缺失 → 阻塞 CNV 路线）。详见 `TASK-002_report.md` 第七节。

> 现行任务总清单：[UNDERGRADUATE_TASK_LIST.md](UNDERGRADUATE_TASK_LIST.md)（规范 C，TASK-001–048）。
> 历史完整科研版 `TASK_LIST.md` 与规范 B 的产出继续保留，但不再定义本科必做范围。

## 10. 许可

**决定（2026-09-16）：暂不创建 `LICENSE` 文件，推迟到论文投稿时确定。**

理由：

- 本项目 100% 使用公开数据、不做新湿实验，**不涉及需要立即声明的资产**；
- 目标期刊（Genome Biology、The Plant Journal、中国农业科学等）通常会**指定或推荐**
  特定许可协议（多为 CC-BY / CC0），现在选定反而可能返工；
- **数据本身的许可由各来源数据库决定**（NCBI SRA / ENA / DDBJ），
  与代码仓库的 LICENSE 是两件事，不受此决定影响。

> **触发条件**：论文定稿投出前，按目标期刊要求创建 `LICENSE` 并更新本节。
> 详见 `docs/task_reports/TASK-003_report.md` 复核一节。
