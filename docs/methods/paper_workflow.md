# 参考论文技术路线图（Niu et al. 2024, Genome Biology）

> **TASK-005 输出** · 建立日期：2026-09-16
> 项目：RiceVar-ID（基于 ulcWGS 的水稻品种数字身份证系统）
> 依据文档：`docs/methods/paper_niu2024_extraction.md`（逐节技术解析，601 行）
> 原始证据：`docs/methods/_raw/`（EBI/PMC 全文抓取存档，6 个文件；**仅存于开发机，未入库**）

---

## 0. 本文档的定位与边界

本文档回答**一个问题**：*这篇小麦论文的技术路线具体是怎么走的？*

| 文档 | 回答的问题 |
| --- | --- |
| `paper_niu2024_extraction.md` | 论文各要素**是什么**（数据规模、CNVb 定义、阈值…逐项解析） |
| **本文档 `paper_workflow.md`** | 论文的**执行顺序与数据流**如何串联（谁吃谁的输出、每步参数） |
| `wheat_to_rice_migration.md`（TASK-006） | 迁移到水稻时，**哪些照搬、哪些必须重做** |

**重要声明**：本文档描述的是**小麦论文的做法**，不代表 RiceVar-ID 应照此执行。
特别是——论文路线是 **CNV 中心的**，其优势建立在小麦超大 CNV 块这一物种特性上；
**水稻不能预设 CNV 是最佳标记类型**（见第 9 节）。

---

## 1. 主线流程图（任务清单 TASK-005 要求的八阶段）

```
                         WGS
                          │
                          ▼
                   CNV Discovery
                          │
                          ▼
                     CNV Block
                          │
                          ▼
                  Marker Filtering
                          │
                          ▼
                 Binary Fingerprint
                          │
                          ▼
                       ulcWGS
                          │
                          ▼
                     Similarity
                          │
                          ▼
                Variety Identification
```

### 主线八阶段 ↔ 论文原始步骤对照

| # | 主线阶段 | 论文对应 | 一句话说明 |
| --- | --- | --- | --- |
| 1 | **WGS** | Step 0 数据准备 | 1599 份重测序数据，建库用其中 528 份（平均 5.4×） |
| 2 | **CNV Discovery** | Step 1 前半 | 100 Kb 非重叠窗口算平均深度，按全基因组众数归一化，找出偏离窗口 |
| 3 | **CNV Block** | Step 1 后半 | 连续同类窗口合并成 CNV block |
| 4 | **Marker Filtering** | Step 2 + 3 + 4 | HMM 平滑 → 合并去冗余 → ulcWGS 稳定性过滤：**8134 → 1240** |
| 5 | **Binary Fingerprint** | Step 5 | 1599 份材料各生成 1240 位 0/1 指纹 |
| 6 | **ulcWGS** | Step 4（建库侧）+ Step 6（扫描侧） | ⚠️ **两种角色**，见下方说明 |
| 7 | **Similarity** | Step 6 | 两两 Jaccard 相似度 |
| 8 | **Variety Identification** | Step 6 | 与 85% 阈值比较判定同品种/不同品种 |

> ⚠️ **关于 ulcWGS 的位置**：主线把 ulcWGS 画在 Fingerprint 之后，容易误读为"只有扫描阶段用低深度"。
> 实际论文中 **ulcWGS 出现了两次，角色完全不同**：
> - **建库侧（Step 4）**：把 marker 拿去跑 0.1× 模拟，**筛掉低深度下不稳定的 marker**——这是 1240 这个数字的来源；
> - **扫描侧（Step 6）**：新样品用 ulcWGS（≥0.05×）实测，再比对指纹库做鉴定。
>
> **这一步是本论文的核心创新**：不是"先定 marker 再测低深度能不能用"，而是**用低深度反过来筛选 marker 集**。

---

## 2. 完整技术路线（论文原始 Step 0–7，含全部参数）

```
[Pre-step] 泛基因组构建（chrNCP）
   17 个小麦 de novo 组装（含 CS RefSeq v1）
     → 除 CS 外 16 个按 contig N50 + 是否 Hi-C 挂载 排序
     → 全基因组迭代比对（1 Mb 滑动窗口 + read depth）
        起始参考 Aikang58 → Fielder → … → 共 16 个品种
     → 975 个 non-CS novel blocks，总长 2.7 Gb，按染色体顺序拼装
     → 命名 "chrNCP"
   pan-genome = CS 基因组 + chrNCP
        │
        ▼
[Step 0] 数据准备
   1599 份重测序数据（建库用其中 528 份，平均深度 5.4×）
   Trimmomatic        去接头 / 低质量
     → BWA-MEM        比对到 pan-genome
     → Bamtools v2.4  过滤异常插入片段（>10,000 bp 或 =0 bp）与低 MAPQ（<1）
     → Samtools v1.3  去 PCR 重复
        │
        ▼
[Step 1] 原始 CNV bins / blocks 检测
   100 Kb 非重叠窗口
     → bedtools v2.27.1 coverage  求窗口平均深度
     → 除以全基因组深度众数        归一化（消除测序深度差异）
     → <0.5 判 deletion，>1.5 判 duplication
     → 连续同类窗口合并            = CNV block
        │
        ▼
[Step 2] HMM 平滑 + 低频/短片段过滤
   hmmlearn multinomial HMM
     n_components=3, n_iter=60, tol=0.001
     Baum-Welch 拟合 → Viterbi 解码
   长度/频次过滤：
     CS 区块   ：剔除 (length/100Kb + N) ≤ 10
     chrNCP 区块：剔除 (length/1Mb + N) ≤ 10 或 (length/1Mb + n) ≤ 10
        │
        ▼
[Step 3] 合并去冗余
   重叠合并：ρo ≥ 0.8        ρo = Lo/(L1+L2−Lo)
   连锁合并：间距 ≤5 Mb 且 ρlink ≥ 0.9   ρlink = Cs/(C1+C2−Cs)
   chrNCP marker 与 CS marker 基因型高度相关者 → 剔除
   产出：初步 marker library，共 8134 个 CNVb marker
        │
        ▼
[Step 4] ulcWGS 稳定性过滤（0.1×）★ 核心创新步骤
   hcWGS 与模拟 0.1×（Samtools v1.3.1 下采样）分别基因分型
   present 判据：重叠 ≥90% 且长度差 <1 Mb
   >10 份材料检测不一致 → 剔除该 marker
   产出：最终 1240 个高质量 CNVb marker = 1045 deletion + 195 duplication
        │
        ▼
[Step 5] 指纹图谱构建
   对 1599 份材料（528 建库 + 1071 公共）计算每个 CNVb 的 present/absent
   → 每份材料一个 1240 位二进制指纹 + QR-code 式二维矩阵
   → 平均每条染色体 59 个 marker，单条染色体覆盖率最高 92.6%
        │
        ▼
[Step 6] ulcWGS 扫描与品种鉴定
   新样品 ulcWGS（≥0.05×，约 1 GB 数据）
     → 比对 pan-genome
     → 检测 deletion / duplication blocks
     → 与 CNVb marker 集比对（重叠 ≥90% 且长度差 <100 Kb 判 present）
     → 生成指纹
     → 两两 Jaccard 相似度 = M_share/(M_s1+M_s2−M_share)
     → 与 85% 阈值比较 → 同品种 / 不同品种
   性能：深度 >0.05× 时 >99.9% 品种可准确分类
        │
        ▼
[Step 7] 平台化
   WheatCNVb 数据库四个模块：
     CNVb profile / CNVb marker info / Variety compare / Geno scan
   Geno scan：上传 bin-wise read-depth 文件
     → 1–2 分钟返回指纹与比对结果
```

---

## 3. 逐步展开（输入 / 方法 / 工具 / 参数 / 输出）

### Step 0 · 数据准备

| 项目 | 内容 |
| --- | --- |
| **输入** | 原始 FASTQ（1599 份重测序数据） |
| **工具链** | Trimmomatic → BWA-MEM → Bamtools v2.4 → Samtools v1.3 |
| **过滤参数** | 插入片段 >10,000 bp 或 =0 bp → 丢；MAPQ <1 → 丢；PCR 重复 → 去 |
| **参考** | CS 基因组 + chrNCP（pan-genome） |
| **输出** | 去重后的 BAM/CRAM |
| **原文缺失** | 测序平台型号、读长、Trimmomatic/BWA-MEM 具体版本号 |

### Step 1 · CNV 检测

| 项目 | 内容 |
| --- | --- |
| **输入** | Step 0 的比对结果 |
| **窗口** | **100 Kb 非重叠** |
| **归一化** | 窗口深度 ÷ 全基因组深度众数 |
| **判定** | <0.5 → deletion 窗口；>1.5 → duplication 窗口 |
| **合并** | 连续同类窗口 → CNV block |
| **工具** | bedtools v2.27.1 `coverage` |

> **为什么用众数而非均值**：测序深度分布右偏（存在高深度重复区），
> 众数代表"正常"单拷贝区域，用它归一化才能让 1.0 对应单拷贝。

### Step 2 · HMM 平滑与过滤

| 项目 | 内容 |
| --- | --- |
| **模型** | multinomial HMM（`hmmlearn`） |
| **参数** | `n_components=3`, `n_iter=60`, `tol=0.001` |
| **算法** | Baum-Welch 拟合 → Viterbi 解码 |
| **作用** | 把原始噪声深度信号**平滑**成三个状态（缺失 / 正常 / 重复）的连续区段 |
| **过滤（CS 区块）** | 剔除 `(length/100Kb + N) ≤ 10` |
| **过滤（chrNCP 区块）** | 剔除 `(length/1Mb + N) ≤ 10` 或 `(length/1Mb + n) ≤ 10` |

> `N` 与 `n` 的含义：原文未在解析文档中明确区分用途，**若引用需回原文核对**。
> 该过滤的实质是"**短且出现频次低的区块不可靠，丢掉**"。

### Step 3 · 合并去冗余

| 合并类型 | 判据 | 公式 |
| --- | --- | --- |
| 重叠合并 | ρo ≥ 0.8 | ρo = Lo/(L1+L2−Lo) |
| 连锁合并 | 间距 ≤5 Mb **且** ρlink ≥ 0.9 | ρlink = Cs/(C1+C2−Cs) |
| 相关性剔除 | chrNCP marker 与 CS marker 基因型高度相关 | — |

**产出：8134 个 CNVb marker**

### Step 4 · ulcWGS 稳定性过滤 ★

| 项目 | 内容 |
| --- | --- |
| **目的** | 剔除"在低深度下测不准"的 marker |
| **方法** | 同一材料分别用 hcWGS 与模拟 0.1× 基因分型，比对两者结果 |
| **present 判据** | 重叠 ≥90% 且长度差 **<1 Mb** |
| **剔除条件** | >10 份材料检测不一致 |
| **产出** | **1240 个** = 1045 deletion + 195 duplication |

> ⚠️ **原文存在内部不一致**：present 的"长度差"阈值在 Methods Par32（Step 3）写作 **<1 Mb**，
> 而 Par34 写作 **<100 Kb**。本表按 Step 3 语境取 <1 Mb，**引用时须注明此分歧**。

### Step 5 · 指纹图谱构建

| 项目 | 内容 |
| --- | --- |
| **输入** | 1240 个 CNVb marker × 1599 份材料 |
| **编码** | 每 marker 一比特：present=1 / absent=0 |
| **指纹长度** | **1240 bit** |
| **空间分布** | 平均每条染色体 59 个 marker；单条染色体覆盖率最高 **92.6%** |
| **展示形态** | QR-code 式二维矩阵 |

### Step 6 · 扫描与鉴定

| 项目 | 内容 |
| --- | --- |
| **输入** | 新样品 ulcWGS（≥0.05×，约 **1 GB** 数据量） |
| **present 判据** | 重叠 ≥90% 且长度差 **<100 Kb** |
| **相似度** | Jaccard：`M_share/(M_s1+M_s2−M_share)` |
| **判定阈值** | **85%**（来源：同品种相似度分布的 99% 置信区间） |
| **性能** | 深度 >0.05× 时 **>99.9%** 品种可准确分类 |

### Step 7 · 平台化

| 模块 | 功能 |
| --- | --- |
| CNVb profile | 材料指纹总览 |
| CNVb marker info | marker 元信息（位置/类型/长度） |
| Variety compare | 品种两两比较 |
| Geno scan | 上传 bin-wise read-depth → **1–2 分钟**返回指纹与比对结果 |

---

## 4. 关键阈值与决策点汇总

| 环节 | 阈值/参数 | 含义 |
| --- | --- | --- |
| 窗口大小 | 100 Kb | 非重叠 |
| 深度归一化 | ÷ 全基因组众数 | |
| deletion 判定 | <0.5 | 归一化深度 |
| duplication 判定 | >1.5 | 归一化深度 |
| HMM 状态数 | 3 | |
| HMM 迭代 | n_iter=60, tol=0.001 | |
| 短片段过滤 | (len/100Kb + N) ≤ 10 | CS 区块 |
| 重叠合并 | ρo ≥ 0.8 | |
| 连锁合并 | 间距 ≤5 Mb 且 ρlink ≥ 0.9 | |
| **稳定性过滤深度** | **0.1×** | ★ 核心 |
| 稳定性 present 判据 | 重叠 ≥90% 且长度差 <1 Mb | ⚠️ 原文有分歧 |
| 稳定性剔除 | >10 份材料不一致 | |
| 建库深度 | 平均 5.4× | |
| 测试集规模 | 100 份 >5× 材料 | |
| ulcWGS 扫描深度 | ≥0.05× | |
| 扫描 present 判据 | 重叠 ≥90% 且长度差 <100 Kb | |
| **判定阈值** | **85%** | ❌ **不可照搬到水稻** |
| marker 数 | 8134 → **1240** | |
| 指纹长度 | 1240 bit | |

### 原文实际测试的 ulcWGS 深度梯度

**0.01 / 0.05 / 0.1 / 0.5 / 1 / 1.5×**（共 6 档，**仅 2 批重复**）

> ⚠️ 与本项目的差异：TASK_LIST 要求 **0.01/0.02/0.05/0.10/0.20/0.50/1.00× 共 7 档、
> 每档 ≥5（理想 10）重复**。论文的深度梯度更粗、重复更少——**这是本项目的方法学增量**。

---

## 5. 软件与版本（原文实测清单）

| 软件 | 原文版本 | 用途 |
| --- | --- | --- |
| Trimmomatic | **未注明** | reads 修剪 |
| BWA-MEM | **未注明** | 比对 |
| Bamtools | v2.4 | 过滤异常插入片段与低 MAPQ |
| Samtools | v1.3（去重）/ v1.3.1（下采样） | |
| bedtools | v2.27.1（分析）/ v2.26.0（平台） | 窗口深度 |
| hmmlearn | 库版本未注明（参数已给） | HMM 平滑 |
| GATK | v3.868 | SNP 检测（**仅作对照**） |
| **mosdepth** | **未使用** | 原文用 bedtools coverage，**非 mosdepth** |
| R | **未提及** | |

> **对 RiceVar-ID 的提示**：本项目环境已装 `mosdepth 0.3.14`，它是 bedtools coverage 的
> 现代化替代（更快、原生窗口深度）。**用 mosdepth 替换 bedtools coverage 是合理的技术更新**，
> 但需在论文中说明这一差异，不可声称"与原文一致"。

---

## 6. 数据流与产物

```
FASTQ (1599 份)
   │
   ├─► BAM/CRAM ──────────────► bin-wise depth ──► CNV blocks ──► 8134 CNVb
   │                                                                │
   │                                          [0.1× 模拟筛选] ◄─────┘
   │                                                │
   │                                                ▼
   │                                          1240 CNVb marker
   │                                                │
   │                                                ▼
   │                                    指纹矩阵 (1599 × 1240 bit)
   │                                                │
   新样品 ulcWGS (≥0.05×, ~1 GB)                     │
        │                                           │
        └──► blocks ──► present/absent ──► Jaccard ◄┘
                                             │
                                             ▼
                                    ≥85% → 同品种
                                    <85% → 不同品种
```

| 产物 | 规模 |
| --- | --- |
| CNVb marker 库 | 1240 个（1045 del + 195 dup） |
| 指纹矩阵 | 1599 × 1240 bit |
| 单样品扫描输入 | ~1 GB（≥0.05×） |
| 扫描耗时 | 1–2 分钟（平台侧） |

---

## 7. 论文的验证设计（可移植部分）

论文做了三层验证，**这三层设计都可原样移植到水稻**：

1. **低深度 recall 曲线**：逐档深度下 marker 的 recall（0.05× 平均 99.3%）；
2. **与 SNP 对照**：GATK 检测 SNP，比较"低深度下 CNVb recall vs SNP recall"；
3. **湿实验验证**：对 chr2A 端部三种等位型做 **PCR**，结果与 CNVb 预测的等位型一致（Fig. 3g–i）。

> **第 3 层水稻做不了**——本项目明确"不做新的湿实验"。
> 水稻应以**公开数据交叉验证**替代（如用独立数据集、品种登记信息、已知同名异种案例）。

---

## 8. 论文未做 / 未给出的部分（本项目的增量机会）

| 缺口 | RiceVar-ID 的机会 |
| --- | --- |
| **全文无 ROC / AUC** | 水稻项目重算 ROC/AUC/Precision/Recall/F1 —— **明确的增量贡献** |
| 未做误差棒 / 重复批次少（仅 2 批） | 本项目每档 ≥5 重复 |
| 深度梯度粗（6 档） | 本项目 7 档 |
| 未比较多种标记类型（只有 CNVb vs SNP） | 本项目四条路线并行实测 |
| 无成本分析（缺少 Table S9） | 本项目已做算力实测（`benchmark_results.md`） |
| 未做同名异种（EDV）系统评估 | 可纳入独立测试集设计 |

---

## 9. 关键警示：不要把论文的路线当成水稻的答案

论文路线的每一环都**建立在小麦的物种特性上**：

| 小麦特性 | 数值 | 水稻对比 | 后果 |
| --- | --- | --- | --- |
| 倍性 | 六倍体 | **二倍体** | CNV 检测的信噪比基础不同 |
| 基因组 | ~16 Gb | **~375 Mb（1/43）** | 数据量、成本差一个量级 |
| **平均 CNV 区域数** | **2061 个/材料** | **约 19 个/材料** | ★ 致命差异 |
| **CNV 总长** | 139–1567 Mb | **约 142 Kb** | ★ 致命差异 |
| 最大 CNV 块 | 可达百 Mb 级 | 通常 ≤ 数十 Kb | 100 Kb 窗口 + ≥100 Kb 长度阈值**在水稻筛不出 marker** |

> **结论**：论文的"**思路**"（窗口深度 → 块 → 低深度反筛 → 指纹 → Jaccard）可以迁移；
> 论文的"**参数**"（100 Kb 窗口、≥100 Kb 长度、85% 阈值）**一个都不能直接搬**。
>
> **水稻不能预设 CNV 是最佳标记类型**——必须在 SNP / k-mer / CNV / SV 四条路线间实测比较
> （Phase 12，TASK-047–TASK-052）。具体迁移决策见 `wheat_to_rice_migration.md`（TASK-006）。

---

## 10. 下一步接口

| 下游任务 | 从本文档取什么 |
| --- | --- |
| **TASK-006** | 第 9 节的差异表 + `TASK-004_report.md` 第 14 节 → 逐项迁移决策 |
| **TASK-007** | 第 1/2 节路线 → 改写为水稻四条候选路线 |
| **TASK-038** | 第 4 节窗口参数 → 在 10/50/100 kb 间重新比较 |
| **TASK-049/050** | 第 4 节深度梯度 → 扩展为 7 档 × ≥5 重复 |
| **TASK-051/052** | 第 7 节验证设计 → 增加 ROC/AUC |
| **TASK-053** | 第 6 节阈值 → 用水稻真实数据重算，**禁止照搬 85%** |

---

## 附：本文档的事实来源与可信度

| 内容 | 来源 | 可信度 |
| --- | --- | --- |
| Step 0–7 流程与参数 | `paper_niu2024_extraction.md` 第 12.1 节 | **高**（原文 Methods 逐段可核对） |
| 软件版本 | 第 12.2 节 | **高**（原文明确给出者）/ 低（"未注明"者） |
| 优先级与结论性判断（第 9 节） | TASK-004 解析 + 水稻文献常识 | **判断**，非原文陈述 |
| 原文内部不一致（present 长度差阈值） | 第 13 节引用风险清单 | **已知分歧**，引用须注明 |

> 完整可信度分级（A 逐字可核对 / B 平台可信 / C 推断或原文不一致 / D 未获取禁止推测 / E 解析方法学）
> 见 `paper_niu2024_extraction.md` 末尾"数据可信度说明"。
