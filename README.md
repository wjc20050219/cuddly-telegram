🌾 RiceVar-ID

基于超低深度全基因组测序的水稻品种数字身份证系统

Rice Variety Digital Identification System Based on Ultra-Low-Coverage Whole-Genome Sequencing

---

📖 项目简介

RiceVar-ID 是一个面向水稻品种基因组识别的计算生物学研究项目，探索利用**超低深度全基因组测序（ulcWGS）**和少量预定义 SNP Marker，构建水稻品种的数字化基因组身份。

本研究完全基于 NCBI SRA、ENA、DDBJ 等公共数据库中的真实水稻 WGS 数据，不进行新的湿实验。

研究采用真实中、高深度 WGS 数据，通过计算机随机降采样模拟不同测序深度，并在固定 SNP 位点上进行分型，最终评价不同测序深度和不同 SNP 数量条件下的水稻品种识别能力。

核心研究路线：

flowchart TD
    A[公共真实 WGS 数据] --> B[质量控制]
    B --> C[参考基因组比对]
    C --> D[多样本联合 SNP Calling]
    D --> E[SNP 筛选]
    E --> F[固定 SNP Panel]
    F --> G[超低深度模拟]
    G --> H[固定 SNP 位点分型]
    H --> I[SNP Fingerprint]
    I --> J[指纹相似度计算]
    J --> K[品种识别]
    K --> L[Open-set 拒识]
    L --> M[数字身份证]

---

🎯 研究目标

本研究主要回答以下问题：

1. SNP 数字指纹能否区分不同水稻品种？

利用真实公共 WGS 数据构建品种 SNP 指纹，并评价其品种区分能力。

2. 测序深度降低后，品种识别能力如何变化？

模拟不同超低测序深度，研究测序信息量下降对品种识别性能的影响。

3. 不同 SNP 数量对识别性能有什么影响？

比较 500、1000 和 2000 个 SNP Marker 所形成的数字指纹。

4. 系统能否识别数据库之外的未知品种？

通过 Open-set Identification 设计拒识机制，避免将未知品种强制匹配到已知品种。

---

🧬 核心研究思路

RiceVar-ID 将水稻品种的基因组变异转换为固定长度的 SNP 数字指纹。

flowchart LR
    A[水稻品种] --> B[全基因组变异]
    B --> C[SNP Marker]
    C --> D[SNP Fingerprint]
    D --> E[品种识别]
    E --> F[Digital ID]

一个品种可以表示为：

品种 A
    ↓
SNP Fingerprint
    ↓
010110011010010101...
    ↓
RV-A8F3C21D

其中：

- SNP Fingerprint：固定 SNP 位点上的基因型组合；
- Digital ID：用于数据库存储和查询的数字化身份标识。

---

🌱 超低深度全基因组测序

本研究不直接预设某个测序深度一定能够完成品种识别，而是通过真实 WGS 数据的随机降采样进行系统评价。

模拟深度：

测序深度
1×
0.5×
0.2×
0.1×
0.05×
0.02×

实验矩阵：

3 种 SNP Panel × 6 种测序深度 × 多个随机 Seed

通过重复随机降采样，降低单次随机抽样造成的偶然影响。

---

🧪 数据集设计

研究使用两个相互独立的数据面板。

flowchart TD
    A[公共水稻 WGS 数据] --> B[样本筛选]
    B --> C[Pilot Panel]
    B --> D[Independent Test Panel]

    C --> E[Marker 筛选]
    C --> F[参数校准]
    C --> G[阈值校准]

    D --> H[最终性能评价]
    D --> I[Open-set 验证]

数据集| 样本数| 用途
Pilot Panel| 30| SNP Marker 筛选、参数校准
Independent Test Panel| 25| 独立性能评价、Open-set 验证

Independent Test Panel 不参与 Marker 优化和最终阈值确定。

---

🧩 SNP Marker Panel

本研究以 SNP 作为核心遗传 Marker。

设计三个不同规模的 SNP Panel：

Panel| SNP 数量| 研究目的
Small| 500| 紧凑型数字指纹
Medium| 1000| 中等规模数字指纹
Large| 2000| 高信息量数字指纹

Marker 筛选和参数优化只使用 Pilot Panel。

Marker Panel 确定后，在 Independent Test Panel 上保持固定。

---

🧬 生物信息学分析流程

flowchart TD
    A[FASTQ] --> B[FastQC / fastp]
    B --> C[BWA-MEM2]
    C --> D[SAM / BAM]
    D --> E[samtools]
    E --> F[CRAM]

    F --> G[mosdepth]
    F --> H[bcftools]

    H --> I[多样本联合 SNP Calling]
    I --> J[SNP 质量控制]
    J --> K[Marker 筛选]

    K --> L[500 SNP]
    K --> M[1000 SNP]
    K --> N[2000 SNP]

    L --> O[超低深度模拟]
    M --> O
    N --> O

    O --> P[固定 SNP 位点分型]
    P --> Q[SNP Fingerprint]
    Q --> R[IBS / Hamming Distance]
    R --> S[品种识别]
    S --> T[Open-set 拒识]

参考基因组：

IRGSP-1.0

---

⚠️ SNP 矩阵构建原则

正式 SNP 指纹矩阵必须基于：

- 多样本联合 VCF；
- 或固定 SNP Marker 位点重新分型。

不应简单拼接多个单样本 Variant-only VCF。

原因是：

«VCF 中没有某个位点的 Variant 记录，并不等价于该样本在该位点已经被确认是 0/0。»

正式 SNP 矩阵需要明确区分：

0/0
0/1
1/1
Missing

这一原则对于后续 SNP Fingerprint 构建和品种识别非常重要。

---

📉 超低深度模拟

利用真实 WGS 数据进行随机降采样：

flowchart TD
    A[真实 WGS] --> B{随机降采样}

    B --> C[1×]
    B --> D[0.5×]
    B --> E[0.2×]
    B --> F[0.1×]
    B --> G[0.05×]
    B --> H[0.02×]

    C --> I[固定 SNP 位点分型]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I

    I --> J[SNP Fingerprint]

每一个深度条件使用多个随机 Seed。

这样可以评价：

测序深度 → Marker Recall → 指纹质量 → 品种识别性能

之间的关系。

---

🧮 品种识别方法

对于一个待识别样本：

flowchart TD
    A[待识别样本] --> B[固定 SNP 位点分型]
    B --> C[生成 SNP Fingerprint]
    C --> D[与参考品种指纹比较]
    D --> E[计算 IBS / Hamming Distance]
    E --> F[候选品种排序]
    F --> G[输出识别结果]

主要输出：

- Top-1 Candidate
- Top-5 Candidates
- Similarity
- Difference Marker Count
- Marker Recall
- Reject Status

---

🚪 Open-set Identification

传统封闭集分类通常要求每一个输入样本都属于已有类别。

RiceVar-ID 增加开放集识别机制：

flowchart TD
    A[输入样本] --> B[SNP Fingerprint]
    B --> C[与已知品种匹配]
    C --> D{是否达到匹配阈值}

    D -->|是| E[输出已知品种]
    D -->|否| F[Reject]

因此系统不仅判断：

«“它最像哪个已知品种？”»

还判断：

«“它是否足够像数据库中的某个已知品种？”»

拒识阈值在 Pilot Panel 中进行校准，再使用 Independent Test Panel 进行独立评价。

---

📊 评价指标

Top-1 Accuracy

真实品种是否为匹配结果中的第一名。

Top-5 Accuracy

真实品种是否进入前五名候选。

Marker Recall

预定义 SNP Marker 中获得有效基因型信息的比例。

Similarity

待识别样本与候选品种 SNP Fingerprint 的相似程度。

Difference Marker Count

两个 SNP Fingerprint 之间存在差异的有效 Marker 数量。

Open-set Rejection

对于数据库之外的未知品种，系统能否避免将其错误指派为已知品种。

---

🗃️ 公共数据来源

本研究使用公共数据库中的真实水稻 WGS 数据：

数据库| 用途
ENA| WGS 数据检索与下载
NCBI SRA| 数据检索与交叉核验
DDBJ| INSDC 数据交叉核验

大型原始测序文件不直接进入 Git 仓库。

记录数据溯源信息：

Accession
Sample Metadata
Source Database
Checksum
Reference Genome
Software Version
Analysis Parameters
Random Seed

---

📈 公共数据规模

前期公共数据库调查显示，水稻 WGS 数据具有较大的数据供给。

数据来源| WGS 记录
ENA| 96,623
NCBI SRA| 106,474
DDBJ| 1,255*

数据筛选并非单纯追求样本数量，而重点考虑：

- 测序深度
- 品种名称完整性
- 样本质量
- 品种代表性
- 样本独立性

«* DDBJ 相关统计来自项目调查期间可获得的 INSDC 数据及镜像信息，正式论文中将根据最终数据检索时间重新核实统计数字。»

---

🔬 研究变量

本研究重点考察三个因素：

flowchart LR
    A[测序深度] --> D[识别性能]
    B[SNP 数量] --> D
    C[随机 Seed] --> D

    D --> E[Top-1]
    D --> F[Top-5]
    D --> G[Marker Recall]
    D --> H[Similarity]
    D --> I[Open-set Rejection]

核心实验关系：

Sequencing Depth × SNP Panel Size × Identification Performance

---

🪪 数字身份证设计

研究最终将水稻品种的 SNP Fingerprint 转换为数字化身份。

一个数字身份证可以包含：

RiceVar-ID
│
├── Variety Name
├── Digital ID
├── SNP Panel
├── SNP Fingerprint
├── Similarity
├── Difference Marker Count
├── Marker Recall
├── Data Source
└── Reference Information

示意：

品种名称：Example Variety

Digital ID：
RV-XXXXXXXX

SNP Panel：
1000 SNP

SNP Fingerprint：
010110011010010101...

Similarity：
XX.XX%

Difference Marker：
XX

Data Source：
Public WGS

最终可以将这些信息存储到数据库，并进一步实现基于 SNP Fingerprint 的自动品种查询。

---

💻 研究技术栈

生物信息学

FastQC
fastp
BWA-MEM2
samtools
bcftools
mosdepth
KMC

数据分析

Python
R
NumPy
Pandas
SciPy
scikit-learn

可视化

Matplotlib
R

数据库与系统原型

SQLite
Streamlit

---

🏗️ 研究系统框架

flowchart TD
    A[公共 WGS 数据] --> B[生物信息学分析]
    B --> C[SNP Matrix]

    C --> D[Marker Selection]
    D --> E[500 / 1000 / 2000 SNP]

    E --> F[ulcWGS Simulation]
    F --> G[固定 SNP 分型]
    G --> H[SNP Fingerprint]

    H --> I[Fingerprint Matching]
    I --> J[品种识别]
    J --> K[Open-set Rejection]

    K --> L[Digital ID]
    L --> M[数据库 / 系统原型]

---

📌 研究范围

本科研究阶段以 SNP + ulcWGS + 品种识别 为核心主线。

核心研究内容

公共真实 WGS
      ↓
SNP Calling
      ↓
SNP Marker
      ↓
ulcWGS 模拟
      ↓
固定 SNP 分型
      ↓
SNP Fingerprint
      ↓
品种识别
      ↓
Open-set 验证
      ↓
Digital ID

暂不作为核心研究内容

CNV
SV
PAV
复杂单倍型模型
大型深度学习分类模型

后续扩展方向

k-mer
CNV
SV
PAV
Haplotype
大规模品种面板
机器学习模型

---

🎓 预期研究结果

本研究最终希望建立一个完整的评价框架：

flowchart LR
    A[公共 WGS] --> B[SNP Digital Fingerprint]
    B --> C[不同测序深度]
    C --> D[不同 SNP Panel]
    D --> E[品种识别性能]
    E --> F[Open-set 性能]
    F --> G[Digital ID]

最终获得：

- 不同测序深度下的品种识别结果；
- 不同 SNP Panel 的识别性能；
- Marker Recall 与测序深度之间的关系；
- Top-1 / Top-5 识别结果；
- Open-set 拒识结果；
- 水稻品种 SNP 数字指纹；
- 水稻品种数字身份证系统原型。

---

🌾 项目核心假设

RiceVar-ID 探索的核心假设是：

«即使测序深度降低到超低水平，只要预先选择具有较高区分度的 SNP Marker，仍可能从有限的基因组测序信息中提取足够的遗传特征，用于水稻品种识别。»

这一假设不预先设定最终成立与否。

最终结论将以真实公共 WGS 数据、超低深度模拟结果以及独立测试集评价结果为依据。

---

📚 数据与方法学原则

本研究遵循以下原则：

真实数据

使用公共数据库中的真实 WGS 数据，不使用人为构造的数据替代真实测序数据。

不预设性能

不预先规定最低可用测序深度、识别准确率或拒识阈值。

数据独立

Pilot Panel 用于 Marker 开发和参数校准，Independent Test Panel 用于最终独立评价。

方法可复现

记录数据 Accession、软件版本、参数、随机 Seed 和参考基因组信息。

SNP 主线

研究主体聚焦 SNP，避免在本科阶段同时引入过多复杂遗传变异类型。

---

📖 Citation

正式论文发表后将在此处补充 RiceVar-ID 的正式引用信息。

同时建议引用：

1. RiceVar-ID 项目；
2. 所使用的公共 WGS 数据及其原始研究；
3. IRGSP-1.0 参考基因组相关研究；
4. SNP Calling、测序比对及相关分析方法学文献。

---

<div align="center">🌾 RiceVar-ID

公共 WGS · SNP 数字指纹 · 超低深度测序 · 品种识别 · Open-set · Digital ID

将水稻基因组变异转化为可计算的品种数字身份

</div>