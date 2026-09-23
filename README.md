🌾 RiceVar-ID

基于超低深度全基因组测序的水稻品种数字身份证系统

Rice Variety Digital Identification System Based on Ultra-Low-Coverage Whole-Genome Sequencing

"Status" (https://img.shields.io/badge/项目状态-研究中-orange)
"Data" (https://img.shields.io/badge/数据来源-公开WGS-blue)
"Method" (https://img.shields.io/badge/核心方法-SNP数字指纹-green)
"Python" (https://img.shields.io/badge/Python-3.11-blue)
"R" (https://img.shields.io/badge/R-4.3-276DC3)
"Snakemake" (https://img.shields.io/badge/Snakemake-9.x-066DA5)
"Streamlit" (https://img.shields.io/badge/Streamlit-应用原型-FF4B4B)

«RiceVar-ID 是一个面向水稻品种识别的计算生物学项目，探索利用超低深度全基因组测序（ulcWGS）与少量预定义 SNP 标记，构建水稻品种的数字化基因组身份。»

---

📖 项目简介

水稻品种鉴定传统上可以依赖形态学特征、农艺性状、生化标记以及分子标记等方法。

RiceVar-ID 希望探索一种更加数字化的思路：

«如果只获得极低深度的水稻全基因组测序数据，是否仍然能够通过一组预先确定的 SNP 标记可靠地区分不同水稻品种？»

本项目完全基于 NCBI SRA、ENA、DDBJ 等公共数据库中的真实测序数据，不进行新的湿实验。

项目不是直接进行新的超低深度测序，而是利用真实的中/高深度 WGS 数据，通过计算机随机降采样模拟不同测序深度，从而评价超低深度条件下的品种识别能力。

---

🎯 核心思想

整个项目可以概括为：

真实公开 WGS 数据
        ↓
质量控制
        ↓
参考基因组比对
        ↓
多样本联合 SNP Calling
        ↓
SNP 筛选
        ↓
500 / 1000 / 2000 SNP 数字指纹
        ↓
超低深度模拟
        ↓
固定 SNP 位点分型
        ↓
指纹相似度计算
        ↓
品种识别
        ↓
Top-1 / Top-5 / Marker Recall
        ↓
开放集拒识
        ↓
水稻品种数字身份证

---

🔬 核心科学问题

RiceVar-ID 主要研究以下四个问题。

1. SNP 数字指纹能否区分不同水稻品种？

利用公开真实 WGS 数据建立水稻品种 SNP 指纹，并评价其区分能力。

2. 测序深度降低后，识别能力如何变化？

模拟：

1×
0.5×
0.2×
0.1×
0.05×
0.02×

六种测序深度，研究基因组信息量降低后品种识别性能的变化。

3. 需要多少个 SNP 才能形成有效的数字指纹？

比较：

500 SNP
1000 SNP
2000 SNP

三种 marker panel，研究 SNP 数量与识别性能之间的关系。

4. 对于数据库之外的未知品种，系统能否拒绝错误匹配？

系统不仅进行封闭集识别，还设计开放集识别（Open-set Identification）。

已知品种
   ↓
达到匹配条件
   ↓
输出品种身份


未知品种
   ↓
无法达到匹配条件
   ↓
拒绝错误指派

---

🧬 项目核心概念

RiceVar-ID 的核心是将一个水稻品种的基因组变异转换为一个紧凑的数字指纹。

水稻品种
   ↓
全基因组
   ↓
SNP 分型
   ↓
固定 SNP Panel
   ↓
SNP Fingerprint
   ↓
RiceVar-ID

例如：

品种 A
   ↓
010110011010010101...
   ↓
RV-A8F3C21D

最终可以将这种数字身份存储在数据库中，并通过 SNP 指纹进行查询和匹配。

---

🌱 为什么研究超低深度测序？

传统全基因组测序通常会产生大量测序数据。

RiceVar-ID 希望回答：

«如果只获得非常少的测序信息，是否仍然能够提取足够的遗传信号完成品种级识别？»

因此项目不预先假设某个超低深度一定有效，而是通过实验比较：

测序深度
   ×
SNP 数量
   ×
识别性能

最终由真实数据决定最低可用测序深度以及不同 marker panel 的实际表现。

---

🧪 实验设计

数据集设计

项目将数据划分为两个相互独立的面板：

                    公共 WGS 数据
                          │
                    样本筛选与分组
                          │
             ┌────────────┴────────────┐
             ↓                         ↓
        Pilot Panel             Independent Test
             │                         │
             ↓                         ↓
       Marker 筛选                 最终评价
       参数校准                  开放集验证

当前实验设计：

数据集| 样本数| 主要用途
Pilot Panel| 30| Marker 筛选、参数校准
Independent Test Panel| 25| 独立性能评价、开放集验证

独立测试集不参与 marker 优化和阈值确定。

---

🧩 SNP Marker Panel

本科版 RiceVar-ID 将 SNP 作为唯一核心 marker 类型。

设计三个 SNP Panel：

Panel| SNP 数量| 定位
Small| 500| 紧凑型数字指纹
Medium| 1000| 中等规模数字指纹
Large| 2000| 高信息量数字指纹

Marker 的筛选和参数优化只使用 Pilot Panel。

Marker Panel 冻结后，不再根据独立测试集结果进行修改。

---

📉 超低深度模拟

项目使用真实中/高深度 WGS 数据进行计算机降采样：

真实 WGS
   │
   ├── Seed 1 → 1×
   ├── Seed 2 → 1×
   ├── Seed 3 → 1×
   │
   ├── Seed 1 → 0.2×
   ├── Seed 2 → 0.2×
   ├── Seed 3 → 0.2×
   │
   └── ...

模拟深度：

深度| 说明
1×| 低深度
0.5×| 低深度
0.2×| 超低深度
0.1×| 超低深度
0.05×| 极低深度
0.02×| 极低深度

每个实验条件使用多个随机 seed，以降低单次随机抽样造成的偶然影响。

整体实验矩阵为：

3 种 SNP Panel
×
6 种测序深度
×
多个随机 Seed

---

🧬 生物信息学分析流程

                    FASTQ
                      │
             ┌────────┴────────┐
             ↓                 ↓
          FastQC              fastp
             │                 │
             └────────┬────────┘
                      ↓
                  BWA-MEM2
                      ↓
                 SAM / BAM
                      ↓
                  samtools
                      ↓
                    CRAM
                      │
             ┌────────┴────────┐
             ↓                 ↓
         mosdepth          SNP Calling
                               ↓
                            bcftools
                               ↓
                       多样本 SNP 矩阵
                               ↓
                         SNP 质量控制
                               ↓
                         Marker 筛选
                               ↓
                 ┌─────────────┼─────────────┐
                 ↓             ↓             ↓
              500 SNP       1000 SNP      2000 SNP
                 └─────────────┼─────────────┘
                               ↓
                       超低深度模拟
                               ↓
                       固定位点分型
                               ↓
                       SNP Fingerprint
                               ↓
                        相似度 / 距离
                               ↓
                           品种识别

参考基因组：

«IRGSP-1.0»

---

🧮 品种识别方法

对于每一个待识别样本：

待识别样本
    ↓
固定 SNP 位点分型
    ↓
生成 SNP Fingerprint
    ↓
与数据库中的品种指纹比较
    ↓
IBS / Hamming Distance
    ↓
候选品种排序

系统输出：

- Top-1 候选品种
- Top-5 候选品种
- 相似度
- SNP 差异数量
- Marker Recall
- 是否拒识

---

🚪 开放集识别

普通分类系统往往要求：

«输入一个样本 → 必须返回一个已知类别。»

RiceVar-ID 增加了开放集拒识机制。

                  输入样本
                     │
                     ▼
                指纹匹配
                     │
              ┌──────┴──────┐
              ↓             ↓
          达到阈值       未达到阈值
              ↓             ↓
          已知品种         Reject

因此系统不仅回答：

«“它最像哪个品种？”»

还回答：

«“这个样本是否足够像数据库中的某个已知品种？”»

拒识阈值使用 Pilot 数据进行校准，并通过独立测试集评价开放集误指派风险。

---

📊 评价指标

Top-1 Accuracy

真实品种是否排名第一。

---

Top-5 Accuracy

真实品种是否进入前五名候选。

---

Marker Recall

预定义 SNP marker 中能够获得有效基因型信息的比例。

---

Open-set Rejection

对于数据库之外的未知品种，系统是否能够避免将其错误指派为某个已知品种。

---

🗃️ 数据来源

项目使用公共数据库中的真实水稻 WGS 数据：

数据库| 主要用途
ENA| 主要数据下载源
NCBI SRA| 数据检索与交叉核验
DDBJ| INSDC 数据交叉核验

项目不将原始 FASTQ 等大型测序文件直接提交到 Git 仓库。

记录的数据溯源信息包括：

Accession
Sample Metadata
Source Database
Checksum
Reference Genome
Software Version
Analysis Parameters
Random Seed

---

📈 数据规模

当前公共数据调查显示，水稻 WGS 数据具有较大的数据供给。

数据来源| WGS 记录
ENA| 96,623
NCBI SRA| 106,474
DDBJ| 1,255*

其中 ENA 数据中包含大量达到较高测序深度的 WGS 记录，可以为超低深度模拟提供数据基础。

但本项目的数据筛选并非单纯追求数据量，而重点考虑：

测序深度
    +
品种名称
    +
样本质量
    +
品种代表性
    +
样本独立性

«*DDBJ 官方 API 在数据调查期间存在服务异常，相关信息通过 INSDC 镜像体系进行交叉核验。»

---

🏗️ 系统架构

RiceVar-ID 由三个主要层次组成：

┌──────────────────────────────────────────┐
│                 数据层                    │
│                                          │
│  Public WGS / Metadata / SNP Matrix      │
└─────────────────────┬────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────┐
│                 分析层                    │
│                                          │
│  QC                                     │
│  Alignment                              │
│  SNP Calling                            │
│  Marker Selection                       │
│  ulcWGS Simulation                      │
│  Fingerprint Matching                   │
│  Open-set Rejection                     │
└─────────────────────┬────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────┐
│                 应用层                    │
│                                          │
│  SQLite                                 │
│  Streamlit                              │
│  Digital Fingerprint                    │
│  QR Code                                │
└──────────────────────────────────────────┘

---

🪪 水稻品种数字身份证

最终系统将一个水稻品种表示为一个数字身份：

┌────────────────────────────────┐
│          RiceVar-ID            │
│                                │
│ 品种名称：Example Variety      │
│ 数字 ID：RV-XXXXXXXX            │
│                                │
│ SNP Panel：1000                │
│ Fingerprint：010110...         │
│                                │
│ Similarity：XX.XX%             │
│ 差异 Marker：XX                │
│                                │
│ 数据来源：Public WGS            │
│                                │
│             ▣ QR Code          │
└────────────────────────────────┘

数字身份证可以保存：

- 品种名称
- 唯一数字 ID
- SNP Fingerprint
- SNP Panel 信息
- 匹配结果
- 数据来源
- 参考文献
- 二维码

---

💻 技术栈

生物信息学

FastQC
fastp
BWA-MEM2
samtools
bcftools
mosdepth
KMC

工作流

Snakemake
Bash
Python
R

数据分析

NumPy
Pandas
SciPy
scikit-learn

数据可视化

Matplotlib
R

数据库与应用

SQLite
Streamlit

运行环境

Windows 11
    ↓
WSL 2
    ↓
Ubuntu
    ↓
Miniconda
    ↓
Python 3.11 / R 4.3

---

📁 项目目录

RiceVar-ID/
│
├── data/
│   ├── metadata/          # 数据与样本元信息
│   ├── raw/               # 原始数据
│   ├── processed/         # 处理后数据
│   └── qc/                # 质量控制结果
│
├── results/
│   ├── statistics/        # 统计结果
│   ├── markers/           # SNP Marker
│   ├── fingerprints/      # 数字指纹
│   └── validation/        # 验证结果
│
├── scripts/               # 分析脚本
│
├── server/                # 服务器分析流程
│
├── app/                   # Streamlit 应用
│
├── docs/
│   ├── methods/           # 方法文档
│   └── task_reports/      # 任务报告
│
├── environment.yml        # Conda 环境
├── requirements.txt       # Python 依赖
├── software_versions.txt  # 软件版本
├── PROJECT_STRUCTURE.md   # 项目结构说明
├── UNDERGRADUATE_TASK_LIST.md
└── README.md

大型文件：

FASTQ
BAM / CRAM
参考基因组

不直接进入 Git 仓库，仅记录来源、版本和 checksum。

---

🔁 可复现性

RiceVar-ID 从设计阶段就考虑实验可复现性。

每次主要分析记录：

- 数据库 accession
- 样本信息
- 文件 checksum
- 软件版本
- 参数
- 随机 seed
- 参考基因组
- SNP marker panel
- 样本划分
- 输出结果

环境重建：

bash setup_wsl_env3.sh

环境检查：

bash scripts/verify_env.sh

---

🖥️ 计算架构

由于 WGS 数据处理涉及大量存储和计算资源，项目采用服务器 + 本机的分工模式。

                    学校服务器
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
       数据下载          QC             比对
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                    SNP Calling
                         ↓
                  深度计算 / 模拟
                         ↓
                   特征矩阵 / 结果
                         │
                         ▼
                       本机
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
       Marker分析       统计分析       可视化
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                  SQLite / Streamlit

服务器主要负责大规模 WGS 数据处理。

本机主要负责：

- SNP marker 分析
- 指纹匹配
- 统计分析
- 可视化
- 数据库
- Streamlit
- 论文相关工作

---

📊 项目最终输出

RiceVar-ID 主要产生三类成果。

① 科学结果

建立：

测序深度
    ×
SNP 数量
    ×
识别性能

的系统评价框架。

最终可以得到：

- 不同深度下的 Top-1 Accuracy
- 不同深度下的 Top-5 Accuracy
- Marker Recall
- 不同 SNP Panel 的比较
- Open-set Rejection 表现

---

② 水稻品种数字指纹

将水稻品种转换为：

品种
 ↓
SNP Fingerprint
 ↓
Digital ID

形成可计算、可存储、可查询的数字身份。

---

③ 软件原型

最终形成一个基于 Streamlit 的轻量级品种识别系统：

输入 SNP Fingerprint
        ↓
     RiceVar-ID
        ↓
候选品种排序
        ↓
┌─────────────────┐
│ Top-1           │
│ Top-5           │
│ Similarity      │
│ Marker Recall   │
│ Difference      │
│ Reject          │
└─────────────────┘

---

🧭 项目范围

本科版项目有意控制研究范围，以保证能够形成一个完整、可验证、可复现的研究闭环。

核心主线

              RiceVar-ID
                   │
                   ▼
                  SNP
                   │
                   ▼
                ulcWGS
                   │
                   ▼
             品种识别
                   │
                   ▼
              Digital ID

当前不属于本科核心范围

CNV
SV
PAV
复杂单倍型模型
大型机器学习分类模型

后续可扩展方向

k-mer
CNV
SV
PAV
Haplotype
更大规模品种面板
机器学习模型

这些方向将在 SNP 主线完成验证后再考虑。

---

🗺️ 项目路线图

[✓] 项目设计
       │
       ▼
[✓] 公共数据调查
       │
       ▼
[✓] 样本库建立
       │
       ▼
[ ] WGS → SNP Matrix
       │
       ▼
[ ] SNP Marker Panel
       │
       ▼
[ ] ulcWGS 模拟
       │
       ▼
[ ] 品种识别
       │
       ▼
[ ] Open-set 验证
       │
       ▼
[ ] SQLite + Streamlit
       │
       ▼
[ ] 论文与成果整理

---

📚 项目文档

详细研究方法和工程规范位于：

docs/
├── methods/
│   ├── data_source_survey.md
│   ├── literature_review.md
│   ├── reference_genome_plan.md
│   ├── snp_evaluation_design.md
│   ├── server_pilot_runbook.md
│   └── compute_feasibility_assessment.md
│
├── task_reports/
└── ...

本科版任务清单：

UNDERGRADUATE_TASK_LIST.md

---

🔬 项目原则

真实数据

优先使用公共数据库中的真实测序数据，而不是人为构造的理想数据。

不预设结果

不提前设定最低可用测序深度、识别准确率和拒识阈值。

严格数据隔离

Pilot 数据用于 marker 开发和参数校准，独立测试集用于最终性能评价。

可复现

记录 accession、checksum、软件版本、分析参数和随机 seed。

控制研究范围

本科版以 SNP 为唯一核心 marker，优先完成一个完整、可验证的研究闭环。

开放集意识

系统不仅考虑：

«“它最像哪个已知品种？”»

同时考虑：

«“它是否根本不属于当前数据库中的已知品种？”»

---

🌾 项目愿景

RiceVar-ID 希望探索一个简单而明确的问题：

«少量预定义 SNP + 超低深度全基因组测序，是否能够提供足够的遗传信息，实现水稻品种级别的数字化识别？»

如果这一思路得到数据验证，可以形成：

水稻品种
    ↓
全基因组
    ↓
SNP Fingerprint
    ↓
Digital ID
    ↓
数据库
    ↓
自动化识别

最终目标不是简单构建一个 SNP 分析脚本，而是探索一个从：

公开基因组数据 → 遗传特征 → 数字指纹 → 品种身份 → 自动识别

的完整计算框架。

---

📜 License

当前仓库暂未设置正式 "LICENSE" 文件。

原始测序数据的使用权限和许可条款由对应公共数据库及原始研究项目决定。

项目正式发布或投稿时，将根据软件代码、数据及论文的实际发布要求确定相应许可协议。

---

📖 Citation

正式论文或项目发布后将在此处补充引用信息。

如果 RiceVar-ID 对你的研究有所帮助，请同时引用：

1. RiceVar-ID 项目；
2. 所使用的原始测序数据；
3. IRGSP-1.0 参考基因组相关研究；
4. 项目中使用的相关方法学文献。

---

<div align="center">🌾 RiceVar-ID

公开 WGS · SNP 数字指纹 · 超低深度测序 · 开放集识别 · 品种数字身份证

将水稻基因组变异转化为可计算的数字身份

</div>