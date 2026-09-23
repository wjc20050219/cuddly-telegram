RiceVar-ID

基于超低深度全基因组测序（ulcWGS）的水稻品种数字身份证系统

RiceVar-ID 是一个面向水稻品种鉴定的计算生物学与生物信息学项目，探索利用超低深度全基因组测序（ulcWGS）+ SNP 数字指纹，实现水稻品种的快速识别与数字化表达。

项目完全基于 NCBI SRA / ENA / DDBJ 等公开数据库中的真实测序数据，不进行新的湿实验。通过对真实中/高深度 WGS 数据进行计算机降采样，模拟不同超低测序深度，并系统评价 SNP 数字指纹在低深度条件下的品种识别能力。

«核心思想：

真实 WGS → SNP 指纹 → 超低深度模拟 → 品种识别 → 开放集拒识 → 数字身份证»

---

1. 项目简介

传统水稻品种鉴定通常依赖形态学、农艺性状、生化标记或较高深度的基因组测序。

RiceVar-ID 尝试回答一个更具体的问题：

«如果将水稻全基因组测序深度降低到极低水平，仅利用预先确定的一组 SNP marker，是否仍然能够可靠地区分不同水稻品种？»

项目以公开水稻 WGS 数据为基础，建立从原始 FASTQ 到数字指纹识别的完整分析流程：

公开 WGS 数据
      │
      ▼
FastQC / fastp
      │
      ▼
BWA-MEM2 + samtools
      │
      ▼
多样本联合 SNP Calling
      │
      ▼
SNP QC + Marker 筛选
      │
      ├──────────────┐
      ▼              ▼
 500 SNP         1000 SNP
      │              │
      └──────┬───────┘
             ▼
          2000 SNP
             │
             ▼
      超低深度模拟
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
   1×      0.2×     0.02×
    │        │        │
    └────────┼────────┘
             ▼
       固定位点分型
             │
             ▼
      IBS / Hamming
             │
             ▼
       品种身份匹配
             │
      ┌──────┼──────┐
      ▼      ▼      ▼
    Top-1  Top-5  Recall
             │
             ▼
        Open-set 拒识
             │
             ▼
      RiceVar-ID 数字身份证

---

2. 核心科学问题

RiceVar-ID 主要研究以下问题：

Q1：SNP 数字指纹能否区分不同水稻品种？

利用公开 WGS 数据构建水稻品种 SNP 指纹，并评价其品种区分能力。

Q2：超低测序深度对品种识别有什么影响？

模拟：

1×
0.5×
0.2×
0.1×
0.05×
0.02×

六种测序深度，比较不同深度下的识别表现。

Q3：需要多少个 SNP marker？

比较：

500 SNP
1000 SNP
2000 SNP

三种 marker panel，研究 marker 数量与识别性能之间的关系。

Q4：系统能否识别“未知品种”？

除了封闭集识别之外，RiceVar-ID 引入开放集识别（open-set identification）：

已知品种
   ↓
正常匹配
   ↓
输出候选品种

未知品种
   ↓
无法达到匹配阈值
   ↓
拒绝错误指派

拒识阈值通过 Pilot 数据进行校准，并使用零重叠独立测试集评估开放集误指派风险。

---

3. 项目特色

3.1 真实公开 WGS 数据

项目不依赖自行测序数据。

主要数据来源：

- NCBI SRA
- ENA
- DDBJ

通过公开数据库获取真实水稻 WGS 数据，并记录 accession、样本信息和数据来源。

---

3.2 真实数据驱动的 ulcWGS 模拟

项目并不直接假设某个超低深度一定能够达到某种准确率。

而是：

真实高/中深度 WGS
        │
        ▼
计算机随机降采样
        │
        ▼
模拟不同测序深度
        │
        ▼
重新进行 marker 分型
        │
        ▼
真实评价识别性能

因此最低可用测序深度、识别率和拒识阈值均由实验结果确定。

---

3.3 SNP 数字指纹

本科版项目将 SNP 作为唯一核心 marker 类型。

通过多样本联合 SNP calling 获得候选变异位点，并根据区分度等指标进行 marker 筛选，最终冻结：

500-SNP Panel
1000-SNP Panel
2000-SNP Panel

用于后续低深度识别实验。

«k-mer、CNV、SV、PAV 等属于后续扩展方向，不属于当前本科版核心流程。»

---

4. 实验设计

4.1 数据集

项目采用两个相互独立的数据集合：

数据集| 用途
Pilot Panel| marker 筛选、参数校准、阈值确定
Independent Test Panel| 最终识别性能与开放集风险评价

当前设计采用：

Pilot Panel
30 samples

Independent Test Panel
25 samples

两个面板在实验设计阶段进行样本隔离，避免利用测试集信息反向优化 marker 或阈值。

---

5. Marker Panel

项目比较三种 SNP marker 数量：

Panel| SNP 数量| 主要用途
Small| 500| 低成本指纹
Medium| 1000| 中等规模指纹
Large| 2000| 高信息量指纹

marker 筛选仅使用 Pilot 数据完成。

冻结后，不再根据独立测试集结果修改 marker panel。

---

6. 超低深度模拟

项目模拟六档测序深度：

模拟深度
1×
0.5×
0.2×
0.1×
0.05×
0.02×

每个条件使用多个随机 seed，以降低单次随机抽样造成的结果波动。

最终形成：

3 marker panels
×
6 sequencing depths
×
multiple random seeds

的实验矩阵。

---

7. 品种识别方法

RiceVar-ID 使用固定 SNP marker 集对样本进行定点分型。

核心比较指标包括：

IBS

通过样本之间的等位基因一致程度衡量遗传相似性。

Hamming Distance

统计两个 SNP fingerprint 在固定 marker 位点上的差异数量。

最终产生：

Query Sample
      │
      ▼
SNP Fingerprint
      │
      ▼
与数据库中的品种指纹逐一比较
      │
      ▼
Similarity / Distance
      │
      ▼
Candidate Ranking
      │
      ├── Top 1
      ├── Top 5
      └── Reject

---

8. 评价指标

项目主要采用以下评价指标：

Top-1 Accuracy

正确品种是否排名第一。

Top-5 Accuracy

真实品种是否进入前五名候选。

Marker Recall

在低深度条件下能够获得可靠信息的 marker 比例。

Open-set Rejection

对于数据库之外的未知品种，系统能否避免强行匹配到某个已知品种。

---

9. 完整技术路线

                Public WGS
                    │
          ┌─────────┴─────────┐
          │                   │
        NCBI                 ENA
          │                   │
          └─────────┬─────────┘
                    ▼
              FASTQ Download
                    │
                    ▼
             FastQC / fastp
                    │
                    ▼
              BWA-MEM2
                    │
                    ▼
            SAM/BAM → CRAM
                    │
                    ▼
         Multi-sample SNP Calling
                    │
                    ▼
             SNP Quality Control
                    │
                    ▼
           Marker Informativeness
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       500 SNP   1000 SNP  2000 SNP
          │         │         │
          └─────────┼─────────┘
                    ▼
             ulcWGS Simulation
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
      1×           0.2×         0.02×
       │            │            │
       └────────────┼────────────┘
                    ▼
             Fixed-site Genotyping
                    │
                    ▼
              IBS / Hamming
                    │
                    ▼
             Identification
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     Top-1        Top-5        Recall
                    │
                    ▼
             Open-set Rejection
                    │
                    ▼
             Statistical Analysis
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
         PCA       Heatmap   Accuracy
                              Curves
                    │
                    ▼
             SQLite Database
                    │
                    ▼
              Streamlit App
                    │
                    ▼
             RiceVar-ID

---

10. 系统架构

RiceVar-ID 最终由三个层次组成：

┌─────────────────────────────────────┐
│           Data Layer                │
│                                     │
│ Public WGS / Metadata / SNP Matrix  │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         Analysis Layer              │
│                                     │
│ SNP Calling                         │
│ Marker Selection                    │
│ Low-depth Simulation                │
│ Fingerprint Matching                │
│ Open-set Rejection                  │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         Application Layer           │
│                                     │
│ SQLite                              │
│ Streamlit                           │
│ Digital Fingerprint                │
│ QR Code                             │
└─────────────────────────────────────┘

---

11. 数字身份证

最终系统将每一个水稻品种表示为一个数字身份：

┌──────────────────────────────┐
│        RiceVar-ID            │
│                              │
│   Variety: XXXXX             │
│   ID: RV-XXXXXXXX             │
│                              │
│   SNP Panel: 1000            │
│   Fingerprint: XXXXXXXX...   │
│                              │
│   Similarity: XX.XX%         │
│   Difference: XX markers     │
│                              │
│   Data Source: Public WGS    │
│                              │
│            ▣ QR Code         │
└──────────────────────────────┘

数字身份证用于保存：

- 品种名称
- 唯一 ID
- SNP fingerprint
- marker panel 信息
- 数据来源
- 匹配结果
- 参考文献
- 二维码

---

12. 数据规模

公开数据调查显示，水稻 WGS 数据具有较大的数据供给。

当前检索结果包括：

数据来源| WGS Records
ENA| 96,623
NCBI SRA| 106,474
DDBJ| 1,255*

其中 ENA 检索结果中有大量达到较高测序深度的记录，可用于筛选适合 ulcWGS 模拟的真实 WGS 数据。

«* DDBJ 官方 API 在项目检索阶段存在服务异常，相关数据通过 INSDC 镜像体系进行交叉核验。»

真正的数据筛选重点不是简单追求数据量，而是：

测序深度
+
品种名称可用性
+
样本质量
+
品种代表性
+
样本之间的信息独立性

---

13. 软件与技术栈

Operating System

Windows 11
    ↓
WSL 2
    ↓
Ubuntu

Environment

Miniconda
Python 3.11
R 4.3

Bioinformatics

FastQC
fastp
BWA-MEM2
samtools
bcftools
mosdepth
KMC

Workflow

Snakemake
Bash
Python
R

Data / Application

SQLite
Streamlit
Pandas
NumPy
SciPy
scikit-learn
Matplotlib

---

14. Repository Structure

RiceVar-ID/
│
├── data/
│   ├── metadata/
│   ├── raw/
│   ├── processed/
│   └── qc/
│
├── results/
│   ├── statistics/
│   ├── markers/
│   ├── fingerprints/
│   └── validation/
│
├── scripts/
│
├── server/
│   ├── 00_probe.sh
│   ├── 01_setup_env.sh
│   ├── 02_download.sh
│   └── run_all.sh
│
├── docs/
│   ├── methods/
│   ├── task_reports/
│   └── ...
│
├── app/
│   └── ...
│
├── environment.yml
├── requirements.txt
├── software_versions.txt
├── UNDERGRADUATE_TASK_LIST.md
├── PROJECT_STRUCTURE.md
└── README.md

大规模 FASTQ、BAM/CRAM 和参考基因组不进入 Git 仓库，仅保存：

Accession
Source
Metadata
Checksum
Software Version
Random Seed

以保证实验可追溯和可复现。

---

15. 可复现性

RiceVar-ID 将实验可复现性作为项目设计的一部分。

每次分析尽可能记录：

- 数据库 accession
- 原始数据来源
- 文件 checksum
- 软件版本
- 参数
- 随机 seed
- marker panel
- 测序深度
- 样本划分
- 分析结果

项目环境可以通过 Conda 配置文件重新构建。

bash setup_wsl_env3.sh

环境检查：

bash scripts/verify_env.sh

---

16. 计算架构

由于 WGS 数据处理具有较大的存储和计算需求，项目采用：

        School Server
              │
      ┌───────┴────────┐
      │                │
   FASTQ            WGS Analysis
      │                │
      └───────┬────────┘
              ▼
        Feature Matrix
              │
              ▼
        Local Computer
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
   Marker   Matching  Statistics
   Analysis           Visualization
              │
              ▼
        SQLite / Streamlit

服务器主要负责：

- WGS 数据下载
- FASTQ 处理
- 比对
- SNP calling
- 深度计算
- ulcWGS 模拟

本机主要负责：

- marker 分析
- 指纹匹配
- 统计分析
- 可视化
- 数据库
- Streamlit 原型
- 论文整理

---

17. 项目输出

RiceVar-ID 最终形成三个层次的输出。

科学结果

不同 SNP panel
×
不同测序深度
×
识别性能

回答：

«在什么 marker 数量和测序深度组合下，可以获得怎样的品种识别表现？»

数据产品

Rice Variety
      ↓
SNP Fingerprint
      ↓
Digital ID

软件原型

用户输入低深度 SNP 指纹：

Query SNP Fingerprint
          ↓
     RiceVar-ID
          ↓
 ┌─────────────────┐
 │ Top 1           │
 │ Top 5           │
 │ Similarity      │
 │ Marker Recall   │
 │ Difference      │
 │ Rejection       │
 └─────────────────┘

---

18. 项目定位

RiceVar-ID 并不是试图建立一个覆盖所有水稻遗传变异类型的完整基因组平台。

本科版项目有意控制研究范围：

                  RiceVar-ID
                      │
          ┌───────────┴───────────┐
          │                       │
       必做主线                  后续扩展
          │                       │
          ▼                       ▼
        SNP                     k-mer
          │                     CNV
          │                      SV
          │                      PAV
          ▼
     ulcWGS Identification

核心目标是建立一个完整、可复现、可验证的 SNP 数字身份证原型，并通过真实公开数据回答超低深度条件下的品种识别问题。

---

19. Roadmap

Phase 1
项目设计
      ✓
      │
      ▼
Phase 2
公开数据调查
      ✓
      │
      ▼
Phase 3
样本库与实验面板
      ✓
      │
      ▼
Phase 4
WGS → SNP
      │
      ▼
Phase 5
Marker Panel
      │
      ▼
Phase 6
ulcWGS Simulation
      │
      ▼
Phase 7
Identification
      │
      ▼
Phase 8
Open-set Validation
      │
      ▼
Phase 9
SQLite + Streamlit
      │
      ▼
Phase 10
论文与成果整理

---

20. 研究原则

本项目遵循以下原则：

真实数据优先

«使用公开数据库中的真实 WGS 数据，而不是人为生成的理想数据。»

结果驱动

«不预设最低可用测序深度、识别准确率或最终拒识阈值。»

严格数据隔离

«Pilot 用于 marker 与参数开发，独立测试集用于最终评价。»

可复现

«记录 accession、checksum、软件版本、参数和随机 seed。»

控制研究范围

«本科版以 SNP 为唯一核心 marker，避免同时引入过多复杂变异类型。»

开放集意识

«不仅关注“能否识别已知品种”，同时关注“未知品种是否会被错误指派”。»

---

21. 项目意义

RiceVar-ID 探索一种低成本、数字化的水稻品种基因组身份表达方法：

传统品种信息
      ↓
品种名称
      ↓
表型 / 图片 / 描述

进一步扩展为：

水稻品种
      ↓
Genome
      ↓
SNP Fingerprint
      ↓
Digital ID
      ↓
Database
      ↓
Automated Identification

项目希望验证：

«少量预定义 SNP + 超低深度全基因组测序，是否能够构建具有实际区分能力的水稻品种数字身份证。»

---

License

本项目目前暂不设置正式 "LICENSE" 文件。

项目数据主要来自公开数据库，其具体数据使用条款以 NCBI、ENA、DDBJ 及对应原始研究项目的许可和数据库政策为准。

---

Citation

如果 RiceVar-ID 的方法、代码或结果对你的研究有所帮助，请引用本项目及其所使用的原始数据和相关研究论文。

«Citation information will be added with the first formal publication/release.»

---

Status

RiceVar-ID — Rice Variety Digital Identification

"ulcWGS" · "SNP Fingerprint" · "Open-set Identification" · "Digital ID"

一个面向水稻品种识别的公开数据驱动型计算生物学研究项目。