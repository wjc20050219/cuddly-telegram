# 基于超低深度全基因组测序的水稻品种数字身份证系统

> 本文件为 Markdown 任务清单版：可直接保存为 `.md` 文件，也可直接复制给 AI Agent 使用。

- **项目英文名建议**：RiceVar-ID
- **项目定位**：基于真实公开测序数据，利用超低深度全基因组测序（ulcWGS）和计算基因组学方法，建立能够区分水稻品种的数字 DNA 身份证系统。
- **重要说明**：本项目不进行新的湿实验，所有基础数据必须来自公开数据库；ulcWGS 部分原则上从真实高/中深度 WGS 数据进行计算机模拟。

## 目录

- 一、项目总目标
- 二、核心科学问题
- 三、项目总体目录
- 四、TASK 任务清单（Phase 0 – Phase 13，TASK-001 – TASK-053）

---

## 一、项目总目标

构建一个完整的：

```
真实公开数据 → 数据质控 → SNP/k-mer/CNV/SV 特征挖掘 → 稳定标记筛选 → 超低深度模拟 → 数字指纹 → 品种鉴定 → 数据库 → Web 系统 → 科研论文
```

完整技术体系。

最终系统能够实现：

1. 输入一个水稻品种的测序数据；
2. 即使测序深度非常低；
3. 提取预先建立的 DNA 标记；
4. 生成该品种的数字指纹；
5. 与数据库中的品种进行比较；
6. 输出：
   - 最可能的品种；
   - Top 5 候选品种；
   - 相似度；
   - 匹配置信度；
   - 差异标记数量；
   - 品种数字身份证；
   - 二维码 / QR-like DNA Fingerprint；
   - 数据来源和文献来源。

---

## 二、核心科学问题

> AI Agent 必须围绕以下问题开展研究。

### 问题 1：什么类型的遗传标记最适合建立水稻数字身份证？

至少比较：

- SNP
- k-mer
- CNV
- CNV Block
- SV
- PAV
- SNP + k-mer
- SNP + CNV
- CNV + SV
- 多类型组合

**不能预设 CNV 一定是最佳方案。**

### 问题 2：在多低的测序深度下仍然可以准确识别品种？

至少测试：

- 0.01×
- 0.02×
- 0.05×
- 0.10×
- 0.20×
- 0.50×
- 1.00×

重点分析：

```
测序深度 → 标记召回率 → 品种鉴定准确率
```

### 问题 3：需要多少个 DNA 标记才能实现可靠鉴定？

至少测试：

- 50
- 100
- 200
- 500
- 1000
- 2000
- 5000

分析：

```
Marker 数量 → 鉴定准确率 → 计算成本
```

寻找最优的：

```
最少标记 + 最低测序深度 + 最高鉴定准确率
```

### 问题 4：如何确定“两个品种是否为同一个品种”的阈值？

- 不能直接照搬小麦研究中的 85% 阈值。
- 必须根据水稻真实数据重新计算：
  - Same variety similarity distribution（同品种相似度分布）
  - Different variety similarity distribution（不同品种相似度分布）
- 然后确定：
  - 最优阈值；
  - ROC；
  - AUC；
  - Precision；
  - Recall；
  - F1；
  - False Positive Rate；
  - False Negative Rate。

---

## 三、项目总体目录

> AI Agent 创建：

```
RiceVar-ID/
│
├── README.md
├── LICENSE
│
├── data/
│   ├── metadata/
│   ├── raw/
│   ├── processed/
│   └── qc/
│
├── reference/
│
├── workflow/
│
├── scripts/
│
├── src/
│
├── results/
│   ├── statistics/
│   ├── markers/
│   ├── fingerprints/
│   └── validation/
│
├── figures/
│
├── database/
│
├── web/
│
├── tests/
│
└── docs/
    ├── methods/
    ├── task_reports/
    └── manuscript/
```

---

## 四、TASK 任务清单

### Phase 0：项目初始化

#### TASK-001：创建项目目录

**任务**

建立：

```
RiceVar-ID/
```

并创建全部标准子目录。

**输出**

- `PROJECT_STRUCTURE.md`

#### TASK-002：建立软件环境

**任务**

安装或准备：

- 基础环境
  - Python
  - R
  - Conda/Mamba
  - Git
- 测序数据处理
  - FastQC
  - fastp
  - samtools
  - bcftools
  - bedtools
  - BWA-MEM2
  - minimap2
  - mosdepth
- k-mer
  - KMC
  - Jellyfish
- 工作流
  - Snakemake
  - 或：Nextflow

**输出**

- `environment.yml`
- `requirements.txt`
- `software_versions.txt`

#### TASK-003：建立 README

**任务**

README 必须说明：

- 项目目标；
- 数据来源；
- 技术路线；
- 软件；
- 数据结构；
- 分析流程；
- 如何运行；
- 如何复现实验；
- 当前研究状态。

---

### Phase 1：解析小麦论文技术路线

#### TASK-004：阅读并解析参考论文

**任务**

重点解析用户提供的小麦论文：

> Niu et al., Genome Biology, 2024.

重点提取：

- 数据规模；
- WGS 深度；
- CNVb 定义；
- CNVb 筛选；
- Marker 数量；
- ulcWGS 方法；
- 0.05× 分析；
- 指纹编码；
- 相似度计算；
- 品种判定；
- 阈值；
- 数据库设计。

#### TASK-005：建立论文技术路线

**输出**

- `paper_workflow.md`

绘制：

```
WGS
 ↓
CNV Discovery
 ↓
CNV Block
 ↓
Marker Filtering
 ↓
Binary Fingerprint
 ↓
ulcWGS
 ↓
Similarity
 ↓
Variety Identification
```

#### TASK-006：建立“小麦 → 水稻”技术迁移表

**任务**

建立：

| 小麦研究 | 水稻研究 |
| --- | --- |
| CNVb | Rice CNV/CNV Block |
| Hexaploid wheat | Diploid rice |
| Wheat reference | Rice reference |
| Wheat varieties | Rice varieties |
| Wheat CNV markers | Rice markers |
| 85% threshold | 重新计算 |
| Wheat ulcWGS | Rice ulcWGS |

必须明确：

- 哪些方法可以直接迁移，哪些必须重新优化。

---

### Phase 2：确定候选技术路线

#### TASK-007：建立候选标记体系

**任务**

至少建立四条路线：

- **Route A：SNP**

  ```
  WGS
   ↓
  Mapping
   ↓
  SNP calling
   ↓
  High-quality SNP
   ↓
  Discriminative SNP
   ↓
  Fingerprint
  ```

- **Route B：k-mer**

  ```
  FASTQ
   ↓
  K-mer counting
   ↓
  Unique k-mer
   ↓
  Variety-specific k-mer
   ↓
  Fingerprint
  ```

  测试：

  - k=21
  - k=25
  - k=31
  - k=35
  - k=41
  - k=51

- **Route C：CNV**

  ```
  WGS
   ↓
  Read depth
   ↓
  CNV
   ↓
  CNV Block
   ↓
  Stable marker
   ↓
  Binary fingerprint
  ```

- **Route D：SV/PAV**

  分析：

  - deletion；
  - insertion；
  - inversion；
  - translocation；
  - presence/absence variation。

---

### Phase 3：公开数据搜索

> 这是本项目最重要的基础阶段之一。

#### TASK-008：搜索 NCBI SRA

**任务**

AI Agent 必须自主搜索：

- NCBI SRA；
- BioProject；
- BioSample；
- GenBank。

搜索关键词：

- Oryza sativa WGS
- rice whole genome sequencing
- rice variety WGS
- rice cultivar WGS
- rice genome resequencing

#### TASK-009：搜索 ENA

**任务**

搜索：

- Oryza sativa WGS
- rice cultivar sequencing
- rice variety resequencing

#### TASK-010：搜索 DDBJ

**任务**

搜索日本公开测序数据。

#### TASK-011：搜索公开研究论文

**任务**

重点查找：

- rice resequencing；
- rice diversity；
- rice cultivar identification；
- rice population genomics；
- rice pan-genome；
- rice structural variation。

---

### Phase 4：建立真实样本数据库

#### TASK-012：建立候选样本表

**任务**

创建：

- `candidate_samples.tsv`

至少包括：

| 字段 | 内容 |
| --- | --- |
| sample_id | 样本ID |
| variety_name | 品种名称 |
| alias | 别名 |
| species | 物种 |
| subspecies | indica/japonica等 |
| accession | 数据库编号 |
| BioProject | 项目编号 |
| BioSample | 样本编号 |
| SRA/ENA | 测序编号 |
| publication | 文献 |
| country | 来源国家 |
| population | 群体 |
| platform | 测序平台 |
| read_length | read长度 |
| estimated_depth | 预计深度 |
| reference | 参考基因组 |
| source | 数据来源 |
| status | 数据状态 |

#### TASK-013：品种名称标准化

**任务**

处理：

- IR64
- IR 64
- IR-64

等别名问题。

建立：

- `variety_alias.tsv`

#### TASK-014：样本去重

**任务**

检测：

- 同一样本重复上传；
- 同一品种多个测序项目；
- 技术重复；
- 生物学重复；
- 不同论文重复使用同一样本。

建立：

- `duplicate_samples.tsv`

---

### Phase 5：建立 Pilot 数据集

#### TASK-015：建立 Pilot Panel

**任务**

首先选择：

- 20–50 个真实水稻样本

作为测试数据。

要求：

- 品种名称明确；
- 测序数据真实存在；
- FASTQ/BAM 可获得；
- 数据来源可追溯；
- 尽可能覆盖 indica、japonica 等主要类型；
- 包含遗传距离较近的品种。

#### TASK-016：建立独立测试集

**任务**

从项目开始就预留：

- Independent Test Set

**禁止后期根据结果重新选择测试样本。**

#### TASK-017：建立正式数据集

**任务**

Pilot 成功以后扩展至：

- 100
- 200
- 500
- 1000+

个样本。

具体数量根据真实公开数据质量确定。

#### TASK-018：建立数据下载日志

**任务**

记录：

- sample_id
- accession
- download_time
- source
- file_name
- file_size
- checksum
- status

**输出**

- `download_log.tsv`

---

### Phase 6：原始测序数据质控

#### TASK-019：FastQC

**任务**

对所有 FASTQ 进行：

- FastQC

#### TASK-020：fastp

**任务**

进行：

- adapter trimming；
- low-quality base trimming；
- read filtering。

#### TASK-021：建立 QC Summary

**输出**

- `qc_summary.tsv`

至少包括：

- raw_reads
- clean_reads
- Q20
- Q30
- GC
- adapter_rate
- duplication

#### TASK-022：剔除低质量样本

**任务**

建立：

- `excluded_samples.tsv`

必须记录：

- 为什么排除。

---

### Phase 7：参考基因组

#### TASK-023：调查水稻参考基因组

**任务**

比较：

- IRGSP-1.0

以及：

- 高质量水稻参考基因组；
- Pan-genome；
- 多品种参考基因组。

#### TASK-024：下载参考基因组

**任务**

保存：

```
reference/
```

并记录：

- 版本；
- 下载地址；
- MD5/SHA256；
- 发布时间。

#### TASK-025：评估参考基因组偏倚

**任务**

比较：

- 单参考基因组 vs Pan-genome

分析：

- reference bias 是否影响 Marker。

---

### Phase 8：SNP 路线

#### TASK-026：WGS Mapping

**任务**

使用：

- BWA-MEM2

或者根据数据情况选择：

- minimap2

#### TASK-027：建立 Mapping QC

**任务**

计算：

- mapping rate
- properly paired
- coverage
- duplication
- insert size

#### TASK-028：建立深度统计

**任务**

使用：

- samtools
- mosdepth

#### TASK-029：SNP Calling

**任务**

使用：

- bcftools

或其他合适工具。

#### TASK-030：SNP Filtering

**任务**

筛选：

- missing rate；
- depth；
- genotype quality；
- MAF；
- biallelic SNP。

#### TASK-031：建立 SNP Matrix

**输出**

- `snp_matrix.vcf`
- `snp_matrix.tsv`

#### TASK-032：SNP 鉴别能力分析

**任务**

计算：

- 每个 SNP 信息量；
- 品种区分能力；
- PCA；
- phylogenetic tree；
- pairwise distance。

---

### Phase 9：k-mer 路线

#### TASK-033：k-mer Counting

**任务**

测试：

- k=21
- 25
- 31
- 35
- 41
- 51

#### TASK-034：建立 k-mer 数据库

**任务**

使用：

- KMC

或：

- Jellyfish

#### TASK-035：寻找特异性 k-mer

**任务**

寻找：

- variety-specific k-mer

以及：

- discriminative k-mer

#### TASK-036：建立 k-mer Matrix

**任务**

建立：

```
samples × k-mers
```

矩阵。

#### TASK-037：评估 k-mer 鉴别能力

**任务**

比较不同：

- k

对：

- 准确率；
- marker 数量；
- 计算时间；
- 内存消耗；

的影响。

---

### Phase 10：CNV 路线

#### TASK-038：Read Depth CNV

**任务**

使用窗口：

- 10 kb
- 50 kb
- 100 kb

进行 read-depth 分析。

#### TASK-039：CNV Calling

**任务**

识别：

- deletion
- duplication

#### TASK-040：CNV Block 构建

**任务**

将连续稳定 CNV 合并为：

- CNV Block

#### TASK-041：CNV Marker Filtering

**任务**

重点筛选：

- 高稳定性；
- 高区分度；
- 低缺失；
- 跨数据集可重复；
- 不受测序深度明显影响。

#### TASK-042：建立 CNV Fingerprint

**任务**

将每个 Marker 编码：

- 0 = absence
- 1 = presence

生成：

- Binary DNA Fingerprint

---

### Phase 11：SV/PAV

#### TASK-043：搜索公开水稻 SV 数据

**任务**

寻找：

- deletion；
- insertion；
- inversion；
- translocation；
- PAV。

#### TASK-044：SV/PAV 与 WGS 数据整合

**任务**

将公开 SV 与实际测序样本对应。

#### TASK-045：评估 SV/PAV 鉴别能力

**任务**

计算：

- Marker 信息量；
- 品种特异性；
- 稳定性；
- 可检测性。

---

### Phase 12：Marker 综合比较

#### TASK-046：建立统一比较框架

**任务**

比较：

- SNP
- k-mer
- CNV
- SV
- PAV

#### TASK-047：建立 Marker Evaluation Score

**任务**

建议考虑：

```
Discrimination
+
Stability
+
Low-depth detectability
+
Reproducibility
+
Computational cost
```

#### TASK-048：选择最佳路线

**任务**

最终比较：

- SNP-only
- k-mer-only
- CNV-only
- SV-only
- CNV + SNP
- CNV + k-mer
- SNP + k-mer
- CNV + SV
- Combined

最终确定：

- RiceVar-ID 最佳 Marker 体系。

---

### Phase 13：超低深度 WGS 模拟

#### TASK-049：建立 ulcWGS 模拟方案

**任务**

从真实：

- 高深度 WGS

中随机抽取 reads。

模拟：

- 0.01×
- 0.02×
- 0.05×
- 0.10×
- 0.20×
- 0.50×
- 1.00×

#### TASK-050：重复模拟

**任务**

每个深度至少：

- 5 replicates

最好：

- 10 replicates

#### TASK-051：计算 Marker Recall

**任务**

计算：

```
Recall = Detected markers / True markers
```

#### TASK-052：建立 Coverage–Recall 曲线

**任务**

绘制：

```
Coverage
    ↓
Marker Recall
```

#### TASK-053：确定最低有效深度

**任务**

确定：

- 在什么测序深度下可以保持可靠的品种识别？

---

> 📌 备注：原对话内容在 **Phase 13 / TASK-053** 处截断。若原始任务清单还有后续 Phase（如阈值计算、数据库、Web 系统、论文写作等），请补充提供，可继续追加到本文件。
