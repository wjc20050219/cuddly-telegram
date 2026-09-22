# Niu et al. 2024 (Genome Biology) 全文技术解析

**论文**：Niu J, Wang W, Wang Z, Chen Z, Zhang X, Qin Z, Miao L, Yang Z, Xie C, Xin M, Peng H, Yao Y, Liu J, Ni Z, Sun Q, Guo W. *Tagging large CNV blocks in wheat boosts digitalization of germplasm resources by ultra-low-coverage sequencing.* **Genome Biology** 2024;25:171. DOI: 10.1186/s13059-024-03315-6（PMID 38951917；PMCID PMC11218387）

**勘误**：2024-11-25 发表 Publisher Correction（DOI: 10.1186/s13059-024-03442-0，Genome Biol 25:298，PMCID PMC11587774），内容为"补充了同等贡献声明"（"The original version of this article was revised: The equal contribution statement has been added."）。Niu J、Wang W、Wang Z 为共同第一作者。

**全文来源（本次实际抓取成功者）**：
1. NCBI E-utilities EFetch，`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=11218387&retmode=xml` —— **完整 JATS 全文 XML（含 Results / Discussion / Methods / Data availability 全文）**，本次解析的主证据源。
2. NCBI BioC-PMC OA API，`https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC11218387/unicode` —— 提供全文分段文本，用于交叉校验。
3. Europe PMC REST search（`resultType=core`）—— 用于核对作者、卷期、MeSH、基金与勘误信息。
4. Semanticscholar / Unpaywall API —— 用于核对 OA 状态与 PMID/PMCID/DOI 映射。
5. 官方平台 `http://wheat.cau.edu.cn/WheatCNVb/` 及其子页 `tutorial.html`、`genoscan.html`；代码库 `https://github.com/Niujx98/WheatCNVbScan`、`https://github.com/Niujx98/WheatCNVbDB`。
- **抓取失败**：PMC 网页版与 PDF（`pmc.ncbi.nlm.nih.gov` 被 reCAPTCHA 拦截）、BMC/Springer 站点（跨域重定向到 `link.springer.com` → `idp.springer.com`）、Europe PMC 站点（HTTP 403 Cloudflare）。**补充材料（Additional file 1 XLSX / 2 PDF / 3 DOCX）全部无法下载**，因此凡仅在附表中的数字（如 Table S1 的测序平台与读长、Table S9 的成本明细）本文件均标注"未获取到"。

---

## 1. 数据规模

**核实后的准确数字（存在两个层次，务必区分）**：

| 层次 | 份数 | 用途 | 出处 |
|---|---|---|---|
| 收集并做全基因组重测序的种质 | **186 份现代栽培品种（modern cultivars）+ 342 份地方品种（landraces）= 528 份** | 用于 CNV 普查与 **CNVb marker 建库** | Results "Pervasive large CNV blocks identified in wheat" 第 1 段（Par9）；Fig. 2a Step 1 |
| 追加的公共重测序数据 | **1071 份** | 扩充数字指纹图谱 | Results "Digital fingerprinting map…" 第 1 段（Par17） |
| **合计（CNVb 指纹图谱/数据库）** | **1599 份全球小麦材料** | 构建数字化指纹图谱与 WheatCNVb 数据库 | Methods "Collection and variation calling…"（Par26）；Abstract；Data availability |
| ulcWGS 测试集 | **100 份**（测序深度 > 5×） | 覆盖度梯度 recall 评估 | Methods "Construction of the low-coverage sequencing test set"（Par33） |
| 泛基因组组装 | **17 个小麦基因组组装** | 构建 pan-genome | Methods "Construct non-Chinese Spring chromosome…"（Par27） |

> "we collected a panel of whole genome resequencing data of worldwide wheat accessions …, including 186 modern cultivars and 342 landraces (Additional file 1: Table S1)."

> "We constructed a comprehensive CNVb fingerprint map consisting of 1599 accessions, by further integrating public resequencing data of 1071 wheat accessions."

> "A total of 1599 published wheat accessions with whole genome resequencing data … were used in this study."

**算术自洽性核验**：186 + 342 = 528 ✔；528 + 1071 = 1599 ✔。用户问题中的"528 accessions / 1071 public / 1599 total"三个数字全部正确。

**数据来源数据库与 BioProject 编号（Data availability，原文完整列出）**：

- **1599 份重测序原始 reads 的 SRA BioProject**：`PRJNA544491`、`PRJNA722149`、`PRJNA476679`、`PRJNA597250`、`PRJNA596843`、`PRJNA439156`、`PRJNA663409`、`PRJEB48988`、`PRJEB48738`
- **国家基因组科学数据中心（NGDC, https://bigd.big.ac.cn/gwh）**：项目号 `CRA005878`
- **17 个 de novo 组装基因组的 BioProject**：`PRJNA544491`、`PRJEB37938`、`PRJNA492239`、`PRJNA528431`、`PRJEB39558`、`PRJEB35709`、`PRJNA595806`、`PRJEB44721`、`PRJEB45541`、`PRJEB49351`；NGDC 登录号 `GWHANRF00000000`；BIG Data Center BioProject `PRJCA004332`
- **数据库代码**：WheatCNVb 数据库 https://github.com/Niujx98/WheatCNVbDB （MIT），Zenodo 10.5281/zenodo.11403154；CNVb 检测流程 https://github.com/Niujx98/WheatCNVbScan （MIT），Zenodo 10.5281/zenodo.11401875

> "The raw reads of 1599 previously published resequenced accessions are available under the following NCBI Sequence Read Archive accessions: PRJNA544491, PRJNA722149, PRJNA476679, PRJNA597250, PRJNA596843, PRJNA439156, PRJNA663409, PRJEB48988, PRJEB48738, and the National Genomics Data Center (https://bigd.big.ac.cn/gwh) database under project CRA005878."

**测序平台与读长**：**未获取到**。正文与 Methods 均未写明测序平台型号或读长；仅在致谢中出现"Illumina sequencing data"这一间接表述（"We thank Prof. Hongqing Ling for providing the Illumina sequencing data."）。平台/读长详情应位于 Additional file 1: Table S1（无法下载）。

> "We thank Prof. Hongqing Ling for providing the Illumina sequencing data."

**平台数据量与论文数字不一致（重要提示）**：WheatCNVb 网站 tutorial 页现写 "This database profiles **1,171** wheat accessions with 1,240 CNVb markers"，与论文的 1599 份不一致；网站 News 记录 "17 Aug 2023: WheatCNVb database is now open!"（早于论文发表）。推测网站页面为较早期或后期改版口径，引用时应以论文的 1599 为准。

---

## 2. WGS 深度、参考基因组与泛基因组构建

**建库用高深度重测序的平均覆盖度 = 5.4×**（用于 CNVb marker 开发的 528 份材料）：

> "we developed a pipeline to obtain high-quality CNVb markers by examining consistent borders, overlaping ratio, and continuity of CNV blocks based on a panel of whole genome resequencing data with an average coverage of **5.4×**, which covers **528** wheat accessions (Additional file 1: Table S1)."——Results "Developing CNVb markers at pan-genome level"（Par12）

**测试集深度门槛**：ulcWGS 测试集从"测序深度 > 5×"的材料中随机选 100 份（Methods Par33）。

**参考基因组名称与版本**：**Chinese Spring（CS）IWGSC RefSeq v1（文中写作 IWGSCv1 / "Chinese Spring RefSeq v1"）**。注意：**不是 v2.0**，也**不是**由 10+ 基因组组装而成的 IWGSC 泛基因组。

> "After mapping reads against the Chinese Spring (CS) reference genome **IWGSCv1** [28] …"——Results Par9

> "we first collected de novo assembled genomes of 17 wheat varieties …, including the reference assembly of **Chinese Spring RefSeq v1** (CS)."——Methods Par27

**泛基因组（pan-genome）构建方法**：不是"17 个组装直接做图基因组"，而是 **CS 参考 + 一条人工拼出的"非 CS 染色体"chrNCP**：

1. 收集 17 个小麦品种的 de novo 组装（含 CS）；
2. 除去 CS 后剩 **16 个基因组按 contig N50 长度、以及是否使用 Hi-C 挂载**排序（Additional file 1: Table S2）；
3. 采用**全基因组迭代比对策略**：以排名第一的 **Aikang58** 为起始参考，将 CS 重测序数据比对到 Aikang58，用 **1 Mb 滑动窗口 + read-depth 方法**检测"CS 中相对 Aikang58 缺失"的序列；再以 CS+Aikang58 的重测序数据比对排名第二的 **Fielder**，识别相对 Fielder 的非冗余缺失区，依次迭代至全部 16 个品种；
4. 提取到的"CS 中缺失"的非冗余缺失块序列，**按染色体顺序拼装成 chrNCP**；
5. **975 个 novel genome blocks，总长 2.7 Gb**；饱和分析显示加入 **14 个基因组**时新块数量趋于平台期，故最终整合 **17 个组装**；
6. pan-genome = **CS 基因组 + chrNCP**。

> "Starting with the Aikang58 genome as the initial reference, and progressing through each genome in order of assembly quality, we systematically detected and compiled **975 novel genome blocks with a total length of 2.7 Gb** (Additional file 1: Table S3). These blocks, which represent genomic regions absent in CS, were then assembled into a non-Chinese Spring pan-genome chromosome, denoted as **"chrNCP"**."

> "Thus, "chrNCP" combined with the CS genome forms the wheat pan-genome (Additional file 1: Table S4)."

> "The saturation analysis showed that the number of non-CS sequence blocks increased by adding new assemblies and approached a plateau when 14 genomes were included …, indicating the representativeness of the constructed pan-genome by integrating a total of 17 wheat assemblies."

**用户问题核对**：17 个组装 ✔；chrNCP ✔；975 blocks ✔；2.7 Gb ✔。注意 S4 与 S3 的表号在正文中略有串位（Results 说 975 blocks 在 Table S3、pan-genome 在 Methods 说 Table S4），属原文自身不一致。

---

## 3. CNVb 定义

**bin 大小与相对深度计算（Methods "Identification of CNV blocks"，Par28）**：

- 基因组切分为 **100 Kb 非重叠窗口（nonoverlapping windows）**；
- 用 **bedtools v2.27.1 的 `coverage` 函数**计算每个窗口的平均 read depth；
- **归一化：除以全基因组 read depth 的众数（mode）**（"normalized by dividing them by the mode of the read depth across the genome"，即 **relative read depth**）；
- 归一化 read count 近似正态分布、中心在 1；据此判定：
  - **normalized read count < 0.5 → deletion window（缺失窗口）**
  - **normalized read count > 1.5 → duplication window（重复窗口）**
- **连续的 deletion / duplication 窗口合并**，界定出全基因组 **CNV blocks**。

> "The genome was segmented into 100 Kb nonoverlapping windows to calculate the average read depth, utilizing the "coverage" function in bedtools v2.27.1 [50]. These counts were then normalized by dividing them by the mode of the read depth across the genome. … windows exhibiting normalized read counts below 0.5 or above 1.5 were classified as deletion and duplication windows, respectively. Finally, contiguous deletion and duplication windows were merged to delineate whole-genome CNV blocks."

**CNVb（CNV block）长度阈值**：**≥ 100 Kb**。Fig. 1e 图注明确 "Left panel, CNV blocks with length **≥100 Kb**"。即 CNVb 定义为长度不小于一个 bin（100 Kb）的大片段拷贝数变异块。

**CNVb-deletion / CNVb-duplication 判定标准（ulcWGS 扫描阶段，Methods "Identification of CNVb markers using ulcWGS"，Par34）**：

- ulcWGS 数据比对到 pan-genome 后，检测 **raw deletion（copy number = 0）** 与 **duplication（copy number ≥ 2）** blocks；
- 缺失块只与 CNVb-deletion marker 集比较，重复块只与 CNVb-duplication marker 集比较（"These blocks are then separately compared with their corresponding CNVb marker set."）；
- **某 marker 在样品中"存在（present）"的判据（ulcWGS 扫描）**：样品中一个 deletion/duplication block 与对应 marker **重叠 ≥ 90%**，且 **block 与 marker 的长度差 < 100 Kb**。

> "The presence of a deletion or duplication marker in a variety is determined based on the following criteria, if a deletion or duplication block present in the variety overlaps with a deletion or duplication marker by at least 90% and the difference in length between the block and the marker is less than 100 Kb."

**建库阶段（Step 3）判据略有不同**：重叠 ≥ 90% 且 **长度差 < 1 Mb**（Methods Par32）。**原文对同一件事给出 100 Kb 与 1 Mb 两个阈值，属原文内部不一致，引用时需并列注明**：

> "A marker was considered present if at least one CNV block overlapped with it by ≥90% and the length discrepancy between the CNV block and the marker is less than 1 Mb."

**CNV 的规模特征（用于说明"大 CNV 块是小麦特有"）**：

- 至少在 1 份材料中判为 deletion 的非冗余 bin 合计 **8430 Mb**；判为 duplication 的合计 **3375 Mb**（Results Par9）；
- 各品种 CNV 区域总长 **139–1567 Mb**；**81.6% 的材料 CNV 总长超过 500 Mb**；**平均每个材料 2061 个 CNV 区域**；
- 对比：玉米平均总长 382 Kb、平均 53 个 CNV；水稻平均总长 142 Kb、平均 19 个 CNV（Fig. 1b）；
- Jagger 在 1D、2A、2D、5A、5B、6B 上有 **6 个 ≥ 10 Mb 的超大 CNV 块**（Fig. 1c）。

> "A total of **8430 Mb and 3375 Mb** non-redundant bins were identified as deletion and duplication in at least one accession, respectively."

> "the total length of CNV regions ranged from 139 to **1567 Mb** across different varieties … the total lengths of CNV regions for **81.6%** of the accessions exceed 500 Mb, with an average of **2061** CNV regions per accession"

> "There are **six** extra-large CNV blocks with lengths spanning **≥10 Mb** detected on chromosomes 1D, 2A, 2D, 5A, 5B, and 6B in the wheat cultivar Jagger"

---

## 4. CNVb 筛选流程（8134 → 1240 的每一步阈值）

原始 CNV bins → **8134 CNVb** → **1240 高质量 CNVb**。全部流程在 **528 份**材料上进行，共三大步（Fig. 2a）：

> "The pipeline consists of three main steps: detecting raw CNV blocks, deducing low-confident and redundant CNV blocks, and removing CNV blocks sensitive to low sequencing depth."

### Step 1：原始 CNV block 过滤（HMM 平滑 + 低频/短片段过滤）

- **HMM 类型与实现**：**multinomial hidden Markov model**，使用 **Python `hmmlearn` 库**（https://pypi.org/project/hmmlearn/）；
- **HMM 参数（原文明确）**：`n_components=3, n_iter=60, tol=0.001`；用 **Baum-Welch** 迭代重估（`fit()` 方法）优化；用 `decode()` 且 `algorithm="viterbi"` 平滑并解码 CNV 块；
- **长度/频率联合过滤阈值 1（比对到 CS 参考的块）**：剔除 **(length / 100 Kb + N) ≤ 10** 的 CNV 块，其中 **N = 含有该 CNV 块的样品数（accessions containing the CNV block）**，length 为该 CNV 块长度；
- **长度/频率联合过滤阈值 2（比对到 chrNCP 的块）**：剔除 **(length / 1 Mb + N) ≤ 10** 或 **(length / 1 Mb + n) ≤ 10** 的块，其中 **n = 不含该 CNV 块的样品数**。

> "This model was configured with parameters set to "**n_components=3, n_iter=60, tol=0.001**" and optimized via the Baum-Welch iterative re-estimation algorithm through the "fit()" method. The "decode()" method, with "algorithm=viterbi", was then used to smooth and decode CNV blocks. CNV blocks with a value of **(length / 100 Kb + N) ≤ 10** were further filtered out, where "N" indicates the number of accessions containing the CNV block … For CNV blocks mapped to the "chrNCP" genome … excluding CNV blocks with a value of **(length / 1 Mb + N) ≤ 10** or **(length / 1 Mb + n) ≤ 10**, where "n" indicates the number of accessions without the CNV block."

### Step 2：CNV block 合并（重叠合并 + 连锁 cluster 合并）

- **重叠合并（reciprocal overlap）**：**ρ_o ≥ 0.8** 的显著重叠块合并（Results 文字表述为"CNV blocks sharing one border and have more than **80%** overlapping regions were merged"）。公式：
  **ρ_o = L_o / (L_1 + L_2 − L_o)**，L_1、L_2 为两个 CNV 块长度，L_o 为重叠长度；
- **连锁 cluster 合并**：**间距在 5 Mb 以内**且 **ρ_link ≥ 0.9** 的块合并。公式：
  **ρ_link = C_s / (C_1 + C_2 − C_s)**，C_1、C_2 为携带各 CNV 块的样品数，C_s 为同时携带两个块的样品数；
- **chrNCP 冗余剔除**：一个来自 chrNCP 的 marker 若其"存在/缺失基因型"与某个来自 CS 的 marker 高度相关，则该 chrNCP marker 被剔除（"If the genotype of a marker from "chrNCP" is highly correlated with that of another marker from CS, the marker from the "chrNCP" sequence will be filtered out."）；
- 合并后得到**初步 CNV marker library，"每个 marker 可对应多个 CNV blocks"**（"encompassing multiple CNV blocks per marker"）；
- 结果：**全群体共鉴定出 8134 个 CNVb marker**。

> "For CNV blocks within the CS reference regions, redundancy was addressed by merging significantly overlapping blocks (**ρ_o ≥ 0.8**) and merging linked blocks (those within **5 Mb apart** and with **ρ_link ≥ 0.9**)."

> "Then, an initial set of **8134** CNVb makers were identified genome-widely across the population."——Results Par12

### Step 3：ulcWGS 稳定性过滤（0.1× recall 剔除）

- 将 hcWGS 数据**下采样到 0.1×**，分别在 hcWGS 与 0.1× 数据上对初步 marker library 做基因分型；
- **marker 判为 present 的判据**：至少一个 CNV block 与其**重叠 ≥ 90%** 且**长度差 < 1 Mb**；
- **剔除规则（关键阈值）**：**在超过 10 份材料中检测结果不一致（inconsistent detections in more than 10 accessions）的 marker 被删除**；
- 结果：**1240 个非冗余高质量 CNVb marker**。

> "Step 3: Filtering CNVb markers for ulcWGS stability. To ensure the applicability of CNVb markers for ulcWGS data, markers indistinguishable at low sequencing coverage were excluded. CNV blocks were initially genotyped from hcWGS and simulated 0.1× coverage data … **Markers with inconsistent detections in more than 10 accessions were removed.**"

> "Step 3, we eliminated CNVb blocks with low recalls in ultra-low-coverage whole genome sequencing (ulcWGS) data (**0.1×**) to develop stable in silico markers … Finally, our pipeline yielded a total of **1240** non-redundant high-quality CNVb markers, comprising **1045 CNVb-deletion markers and 195 CNVb-duplication markers**."——Results Par12

**流程小结（阈值一览）**：

| 步骤 | 操作 | 阈值/参数 | 输出规模 |
|---|---|---|---|
| — | 100 Kb 窗口 read depth，除以全基因组 depth 众数 | deletion <0.5，duplication >1.5 | 原始 CNV bins |
| Step 1 | HMM（hmmlearn, multinomial）平滑 | n_components=3, n_iter=60, tol=0.001, Viterbi 解码 | — |
| Step 1 | 长度+频率联合过滤 | CS：(len/100Kb + N) ≤10 剔除；chrNCP：(len/1Mb + N) ≤10 或 (len/1Mb + n) ≤10 剔除 | — |
| Step 2 | 重叠合并 / 连锁合并 | ρ_o ≥ 0.8；间距 ≤5 Mb 且 ρ_link ≥ 0.9；chrNCP-CS 基因型高相关者剔除 | **8134 CNVb** |
| Step 3 | 0.1× ulcWGS 稳定性过滤 | 重叠 ≥90% 且长度差 <1 Mb 判 present；>10 份材料不一致即剔除 | **1240 CNVb（1045 del + 195 dup）** |

---

## 5. Marker 数量与特征

- **最终 marker 数：1240 个**非冗余高质量 CNVb marker；
- **类型拆分：CNVb-deletion 1045 个 + CNVb-duplication 195 个**（缺失型占 84.3%，重复型占 15.7%）；
- **染色体分布：覆盖全部染色体，平均每条染色体 59 个 marker**；
- **覆盖度：这些 CNVb marker 覆盖每条染色体最多达 92.6% 的区域**（"occupying up to 92.6% of each chromosome"，Additional file 2: Fig. S6）；
- **饱和分析结论：当 panel 规模达到 230 份时，可召回 95% 的 CNVb marker**（Fig. 2b）；饱和分析每次随机加入 **5 份材料**，每个抽样点做 **100 次重复**，蓝点为 100 次重复的平均 marker 数；

> "Finally, our pipeline yielded a total of **1240** non-redundant high-quality CNVb markers, comprising **1045 CNVb-deletion markers and 195 CNVb-duplication markers**. By profiling these CNVb markers across the genome, we observed that these CNVb markers are distributed across all chromosomes, with an average of **59 markers per chromosome** … occupying up to **92.6%** of each chromosome"

> "We further performed saturation analysis of CNVb markers and showed that **95% of CNVb markers could be recalled when the panel size reached 230** (Fig. 2b)"

> Fig. 2b 图注："Saturation analysis of CNVb markers. **Five accessions were randomly added each time.** The shaded area represents **100 replications** for each sampling. The blue dot represents the average number of CNVb markers across 100 repetitions."

**Marker 命名规则**：`CNVb.<整数编号>`；对同一区段的不同亚型使用**小数后缀**（如 `CNVb.67.1` 与 `CNVb.67.2` 分别对应 1RS·1BL 与 1RS∙7DL/7DS∙1BL 两种易位亚型）。原文明示的 marker ID 举例：

| Marker ID | 染色体 | 区间 (Mb) | 关联特征 | 关联基因 | 材料数 |
|---|---|---|---|---|---|
| CNVb.67.1 | 1B | 0–239.3 | 1RS·1BL 易位 | *Pm8/Sr31/Lr26/Yr9* | 111（表）/16（正文 FISH 确认） |
| CNVb.67.2 | 1B | 0–236.7 | 1RS·7DL/7DS·1BL | *Pm8/Sr31/Lr26/Yr9* | 16 |
| CNVb.162 | 1D | 412.1–412.5 | *Glu-D1d* (Dx5 + Dy10) | — | 430 |
| CNVb.189 | 2A | 0–24.7 | 2N^v S / 2AS | *Lr37/Yr17/Sr38* | 142 |
| CNVb.290 | 2B | 89.5–769.0 | *Triticum timopheevii* 渗入 | *Sr36* | 2 |
| CNVb.540 | 3D | 592.2–616.0 | *Thinopyrum ponticum* 渗入 | — | 13 |
| CNVb.647 | 4B | 30.5–31.1 | *r-e-z* 缺失（半矮秆） | *Rht-B1/EamA-B/ZnF-B* | 10 |
| CNVb.989 | 6B | 167.9–183.4 | perInv-6B 臂内倒位 | — | 33 |
| CNVb.173 | 2A | 11.5–21.0 | 与 CNVb.189 重叠的另一渗入 | — | — |
| CNVb.139 | 2A | 0–24.7 | PCR 验证用（Jagger 渗入片段） | — | — |
| CNVb.142 | 2A | 12.0–21.3 | PCR 验证用（Zang1817 渗入片段） | — | — |

> Table 1 caption: "Information and genomic features of representative CNVb markers associated with known structural variations and predominant haplotypes"

**指纹层面的 marker 数量特征**：

- 每份材料中**呈"存在"状态的 CNVb marker 数在 119–322 之间**；
- Lunxuan987 的指纹中检出 **276 个 CNVb marker 为 present**（含 1RS·1BL 易位 marker 与 perInv-6B marker）；
- **两两材料之间平均有 199 个 marker 基因型不同**；**99.5% 的材料对之间差异 marker 数超过 100 个**；
- 姊妹系 **Bima1 与 Bima4 之间有 117 个差异 marker**（Additional file 2: Fig. S10）；
- 数据库示例：**Jimai22 与 Jimai20 相似度 52.6%，各自拥有 90 个与 80 个特有 CNVb marker**（Fig. 5c）。

> "In the CNVb fingerprint map, the number of CNVb markers present in each accession ranges from **119 to 322**. The genotypes of **199** markers are different between pairwise accessions on average (Fig. 4b), and there are more than **100** markers with different genotypes for **99.5%** of the accession pairs"

> "the sibling cultivars Bima1 and Bima4 present **117** distinct markers"

---

## 6. ulcWGS 方法（超低深度数据怎么来）

**数据获取方式**：**并非新测序，而是对已有高深度 BAM 文件做下采样（downsampling）**，工具为 **Samtools v1.3.1**。原文**未**写明具体子命令（用户猜测的 `samtools view -s` 在原文中并未出现），也未写明随机数种子；仅说明"随机下采样"。

**测试集构建（Methods "Construction of the low-coverage sequencing test set"，Par33）**：

- 从材料中**随机选取 100 份测序深度 > 5× 的材料**（Additional file 1: Table S5）；
- 其原始 BAM 文件被下采样到 **6 个深度梯度：0.01×、0.05×、0.1×、0.5×、1×、1.5×**；
- 对每份材料的 ulcWGS 数据做 CNV block 基因分型，再与 raw CNVb marker library 比对，判定每个 CNVb marker 的 present/absent。

> "To create a test set for ulcWGS, **100 accessions with sequencing depths > 5×** were randomly selected (Additional file 1: Table S5). Their original BAM files were downsampled to depth levels of **0.01×, 0.05×, 0.1×, 0.5×, 1×, and 1.5×**, thereby generating simulated ulcWGS data using **Samtools v1.3.1**."

**用户问题核对**：实际梯度为 **0.01× / 0.05× / 0.1× / 0.5× / 1× / 1.5×**（用户列出的 0.02×、0.2× 在文中**不存在**；0.05×、0.1×、0.5×、1× 正确，另有两个用户未列出的 0.01× 与 1.5×）。**可靠性统计只报告了 0.05×、0.1×、0.5×、1.0×、1.5× 五档**（Results Par18 明确列举）。

**重复次数 / 批次**：

- 品种鉴定模拟（replicate 设计）：100 份 ulcWGS 数据为 **replicate 1**，同一批 100 份的高深度数据为 **replicate 2**，在两组间做两两比较以模拟品种鉴定过程（Methods Par38）；
- **泛化能力测试**：随机选 **100 份"不在 CNVb marker 建库材料中"的材料**，将其原始 BAM **分两批（in two separate batches）**下采样到 **0.05×**，得到两套 0.05× 模拟数据，互为 replicate 1 / replicate 2 做两两比较（Methods Par39）；
- 因此**明确记录的重复采样为 2 批**；用户所问"重复几次"若指 >2 次的技术重复，**未获取到**。

> "In addition, we randomly selected 100 accessions that were not among accessions used to construct the CNVb marker library and performed downsampling on their original BAM files to 0.05× coverage **in two separate batches** using Samtools v1.3.1."

**实际建库阶段使用的 ulcWGS 深度 = 0.1×**（Step 3 剔除低 recall marker 时的模拟深度）。

**平台侧最低要求**：WheatCNVb 的 Geno Scan 文档明确"**A minimum coverage of 0.05x (~1GB) is required**"。

> "To identify CNVb fingerprints for your wheat varieties, start with low-coverage sequencing. **A minimum coverage of 0.05x (~1GB) is required.**"

---

## 7. 0.05× 分析结果

**核心结论：CNVb marker 在 0.05× 覆盖度下的平均 recall = 99.3%**，且全面优于 raw CNV 与 SNP：

> "The results showed that the performance of developed CNVb markers exceeded raw CNV regions and SNPs, especially for the ultra-low coverage data. The CNVb markers achieved a **mean recall of 99.3% even at coverage of 0.05×** (Fig. 2c), highlighting the superiority of CNVb as a stable marker compared to traditional strategies."——Results "High recalls achieved by scanning CNVb markers in ultra-low-coverage sequencing data"（Par13）

**覆盖度—准确度曲线的要点（Fig. 2c）**：原文正文仅给出上述定性/单点结论；**Fig. 2c 中各覆盖度下 SNP、raw CNV、CNVb 三者的具体 recall 数值未在正文以文字给出，本次也未能读取图片（图片托管在 PMC/Springer，抓取被拦截），故逐点数值：未获取到**。可确证的曲线要点为：(i) CNVb > raw CNV > SNP；(ii) 覆盖度越低差距越明显；(iii) 0.05× 时 CNVb 平均 recall 99.3%。

**0.05×–1.5× 的 recall / precision（Fig. 4d）**：在 0.05×、0.1×、0.5×、1.0×、1.5× 五个深度下，**每一份材料的最低 recall 均在 99.0% 以上，最低 precision 均在 97.9% 以上**：

> "Reliability tests of CNVb markers among various depths (**0.05×, 0.1×, 0.5×, 1.0×, and 1.5×**) showed that the **minimum recall and precision ratio observed at these reduced depths were above 99.0% and 97.9%**, respectively, for each accession (Fig. 4d)"——Results Par18

**0.1× 在 marker 筛选中的用法（关键点，容易误解）**：0.1× **不是**一个"recall 阈值"，而是**用于剔除在低深度下不稳定的 marker 的测试深度**。判据是：在 hcWGS 与 0.1× 两种数据上对每个 marker 做 present/absent 判定（重叠 ≥90% 且长度差 <1 Mb 判 present），**若某 marker 在超过 10 份材料中出现检测不一致，则该 marker 被删除**。这一步把 8134 个候选 marker 压缩到 1240 个。

> "CNV blocks were initially genotyped from hcWGS and simulated **0.1×** coverage data … **Markers with inconsistent detections in more than 10 accessions were removed.**"

**SNP 对照方法（Methods "Evaluating lcWGS recall for SNPs, raw CNVb, and CNVb markers"，Par35）**：在全部 100 份材料上用 **GATK v3.868 的 HaplotypeCaller 模块、GVCF 模式**检测 SNP；SNP、raw CNVb 与 CNVb marker 三者在低覆盖度下的 recall 均以高覆盖度结果为金标准（ground truth）进行基准测试。

> "SNPs were detected in all 100 accessions using **GATK v3.868's HaplotypeCaller module in GVCF mode**. To assess the recall rates for SNPs, raw CNVb, and CNVb markers identified via low-coverage sequencing, these findings were benchmarked against results from high-coverage sequencing."

---

## 8. 指纹编码与 QR-code 式二维指纹

**编码方式：0/1 presence–absence（每位 = 一个 CNVb marker）**。

- **每一位代表什么**：二维矩阵中**每个 cell 代表一个 CNVb marker**；marker 在材料中**存在（present）**表示该材料携带对应的 duplication 或 deletion 块；
- **单个样本指纹位数 = 1240 位**（对应 1240 个 CNVb marker）。原文："a QR-code-like representation of the digital present-absent status of **1240 CNVb markers**"；
- **二维指纹绘制规则（Fig. 4a 图注，原文明确）**：**marker 按染色体顺序排序，逐行填入矩阵，从左到右、从上到下**；
- **是否含定位图案（finder pattern）**：**未获取到 / 原文未提及**。原文只说"QR-code-like"（类二维码），未描述任何定位角标、静区或纠错机制；从"1240 位按行填充"的描述看，它只是**规则网格状的二值矩阵**，并非真正可被扫码器解码的 QR 码；
- Fig. 4a 展示的是 **Lunxuan987** 的 CNVb marker 指纹，并**用箭头标注了两个特定 marker**，注释分别为"种间渗入（interspecific introgression）"或"结构变异（structural variation）"；
- Fig. 5a 说明平台提供**两种可视化模式**：(i) **染色体图谱（chromosomal profile）**，用着色区段表示存在的 marker；(ii) **QR-code 式 1240 位 present-absent 矩阵**；示例为 **Jagger**。

> Fig. 4a 图注："The CNVb marker fingerprint of Lunxuan987. CNVb marker fingerprint consists of a **QR-code-like two-dimensional matrix, with each cell representing a CNVb marker. All the markers are ordered by chromosomes and are filled into the matrix by rows, from left to right and from top to bottom.** Two specific markers were highlighted by arrows with annotated descriptions as interspecific introgression or structural variation."

> "Moreover, we created a **QR-code-like two-dimensional CNVb markers profile** for each accession (Fig. 4a). The presence of a CNVb-duplication or a CNVb-deletion marker in a variety indicates that this variety contains the duplication or deletion block, respectively."

> "Two visualization modes were offered, as a chromosomal profile with colored regions representing the presented markers, and a **QR-code-like representation of the digital present-absent status of 1240 CNVb markers** (Fig. 5a)."

**平台上传文件的编码格式（WheatCNVbScan README，非论文正文）**：CNVb `.rd` 文件为 4 列——`chromosome`、`start_position`、`end_position`、`CNVb_Status`，其中 `CNVb_Status` 取值为 `deletion` / `white` / `duplication`（注意状态用 `white` 表示"无变化"）。

> "The output file includes four columns … `chromosome start_position end_position CNVb_Status` / `chr1A 0 100000 deletion` / `chr1A 200000 300000 white` / `chr1A 300000 400000 duplication`"

---

## 9. 相似度计算

**公式（Methods "Calculation of the pairwise similarity"，Par37）** ——**这是 Jaccard 相似系数**，基于 CNVb 指纹（presence–absence 集合）：

**similarity = M_share / (M_s1 + M_s2 − M_share)**

其中 **M_s1、M_s2 分别为第一、第二份材料的 marker 数**，**M_share 为两份材料共有的 marker 数**。

> "The pairwise similarity between accessions was calculated based on their CNVb fingerprints. The formula for similarity is defined as: **similarity = M_share / (M_s1 + M_s2 − M_share)**, where M_S1 and M_S2 represent the number of markers in the first and second accessions, respectively, and M_share denotes the number of markers shared between the two accessions."

**注意（重要，易混淆）**：原文**没有**"先算共享 marker 数、再算相似度"的两步阈值流程。流程是：

1. 由 ulcWGS（或 hcWGS）数据生成每份材料的 **CNVb 指纹（1240 位 present/absent 向量）**；
2. 对任意两份材料计算上述 **Jaccard 相似度**（等价于 shared markers / union of markers）；
3. 与 **85% 阈值**比较：≥85% 判为同一品种，<85% 判为不同品种。

**M_share（共享 marker 数）** 确实在文中有独立描述——用于品种区分能力的直观展示（"两两平均 199 个差异 marker"、"99.5% 材料对差异 >100 个"），但它**不是**判定流程中的一步阈值，而是区分力的证据。

**距离度量**：原文未使用 Hamming distance 或欧氏距离；相似度即 Jaccard。**是否为 1 − Jaccard 的距离：未获取到**。

**与 gIBD 的交叉验证**：CNVb 相似度与基于种质资源的 Identity-By-Descent（gIBD）块相似度高度相关，尤其在亲缘较近时（similarity > 0.4 的材料对，**Pearson r = 0.85，P < 2.2 × 10⁻¹²**，Fig. 4c；图中两条虚线均在 0.4 处）。

> "the similarity estimated by the CNVb-based strategy is highly correlated with gIBD-based similarity, and the correlation is especially significant for varieties with a close genetic relationship (**similarity > 0.4, Pearson's correlation = 0.85, P < 2.2 × 10⁻¹²**) (Fig. 4c)."

---

## 10. 品种判定与阈值

**85% similarity 阈值的原文出处与选取依据（Results "Boost germplasm identification with ultra-low-coverage sequencing"，Par18）**：

- 出处：Results 第 8 节第 1 段（Par18），以及 Methods "Assessing the accuracy of variety identification based on ulcWGS"（Par38–Par39）；
- **选取依据：基于"不同品种（distinct variety）"相似度分布的 99% 置信区间**；
- **使用场景**：ulcWGS（0.05× 起）条件下判定两份材料是否属于同一品种；也用于两批重复下采样数据的自我一致性验证。

> "A similarity of **85%** was selected as the threshold for variety differentiation **based on the 99% confidence interval of the "distinct variety" distribution** to ensure high accuracy in distinguishing varieties."

**不同品种区分准确率**：**当测序深度超过 0.05× 时，超过 99.9% 的品种可被准确分类**（Fig. 4e；Additional file 2: Fig. S12）。

> "The results showed that **more than 99.9% of varieties could be accurately classified when the sequencing depth surpassed 0.05×** (Fig. 4e, Additional file 2: Fig. S12)"

**品种内 vs 品种间的相似度分布**：呈**双峰分布（bimodal distribution），两个明显峰分别对应"同品种"与"不同品种"**（Additional file 2: Fig. S11）——这正是 85% 阈值能以 99% 置信区间切分的基础。

> "The similarity between pairwise accessions exhibited a **bimodal distribution with two distinct peaks**, which corresponded to the similarity between the same varieties and between different varieties (Additional file 2: Fig. S11)."

**评价指标定义（Methods Par38–39）**：

- **Power of variety identification（品种鉴定功效）** = 正确识别的"不同品种对"数 / 总"不同品种对"数；
- 另一处用 **statistical power (1 − β)** 作为品种鉴定准确性的评价标准。

> "**Power of variety identification** is defined as the proportion of correctly identified distinct variety pairs out of the total distinct pairs." / "The **statistical power (1 − β)** was also computed as the standard for evaluating the accuracy of varietal identification."

**是否有 ROC / AUC**：**未获取到**。全文未出现 ROC 曲线或 AUC 的表述；阈值基于置信区间而非 ROC 最优点。

**对近缘品种 / 同名异种的处理**：

- **近缘品种**：姊妹系 Bima1 与 Bima4 之间有 **117 个差异 marker**（Fig. S10）；能在 similarity **> 0.4** 的近缘范围内保持区分能力；Discussion 明确"capable of distinguishing even closely related accessions (>40% similarity)"；
- **同名异种（essentially derived varieties, EDV）**：Discussion 提出 CNVb 适合建立 EDV 评价体系——"It provides a low-cost, thousand-marker one-time, and rapid technical solution, ideal for establishing an evaluation system for essentially derived varieties."（原文未给出具体的同名异种案例数据）；
- **具体同名异种判别数字：未获取到。**

**与 SNP array / 其他标记的比较结论（Discussion 第 2 段，含 Additional file 2: Table S9 的五点对比）**：

1. 每个 marker 的基因分型成本**显著低于** Southern blot 类标记（RFLP）与芯片类标记（SNP array），**与 SSR、GBS 的成本效益相当**；
2. 支持超低深度高通量测序且**可全自动**，比 SSR 更省人力、更少依赖设备，更适合大规模应用；
3. 可靠性**很高，与 SNP array 相当，优于 GBS**；
4. 品种鉴定准确率高，可区分近缘材料（>40% similarity），**与基于高深度 WGS 的全基因组 gIBD 分析相当**；
5. 能捕获更大的基因组变异，提供 SNP 无法提供的结构变异相关信息——在六倍体小麦这类大结构变异普遍的多倍体作物中尤其有优势。

> "First, CNVb markers significantly reduced the cost for genotyping per marker compared to Southern blot-based markers like RFLP and chip-based markers like **SNP arrays**, while being comparable in cost-effectiveness to SSRs and GBS. … Third, CNVb markers provide **very high reliability, comparable to SNP arrays, and better performance than the GBS strategy**. Fourth, … capable of distinguishing even closely related accessions (>40% similarity), **comparable to genome-wide gIBD analysis using high-coverage whole genome sequencing**."

**成本数字（每样本测序成本、数据量）**：

- **每样本货币成本（元/美元）：未获取到。** 正文与 Methods 均无金额数字；定量成本对比在 **Additional file 2: Table S9**（无法下载）。原文只用定性表述，如"low-cost, thousand-marker one-time, and rapid technical solution"；
- **可确证的成本相关定量信息**：**0.05× 覆盖度约需 ~1 GB 数据量**（WheatCNVb Geno Scan 文档："A minimum coverage of 0.05x (~1GB) is required."）；数据集规模方面，公开数据 1599 份、测试用 100 份；
- 与 SNP array 的**单价对比数字：未获取到**。

> "Thus, CNVb markers represent a **low-cost, high-throughput, labor-saving, and highly reliable tool** for modern breeding and germplasm management."

---

## 11. 数据库与平台设计（WheatCNVb）

**平台地址**：**http://wheat.cau.edu.cn/WheatCNVb/**（含中文版 `/WheatCNVb/zh/`；教程页 http://wheat.cau.edu.cn/WheatCNVb/tutorial.html ）

**建库基础**："based on the profiling of **1599 hexaploid wheat accessions with 1240 CNVb markers**"。平台首页副标题为 "Database of read depth based fingerprint in wheat."，News 记录 "17 Aug 2023: WheatCNVb database is now open!"。

**四大功能模块（Results "WheatCNVb database for exploring and comparing CNVb profiles"，Par19–Par20）**：

1. **CNVb profile（CNVb 图谱）**：查询任一份材料的 CNVb 图谱，提供两种可视化模式——(i) **染色体图谱**，用着色区段表示存在的 marker；(ii) **QR-code 式 1240 位 present/absent 数字指纹**（示例：Jagger）（Fig. 5a）；
2. **CNVb marker info（marker 信息）**：给出每个 CNVb marker 的 **marker ID、位置、注释（含渗入来源）、以及携带该 marker 的材料清单**（Fig. 5b）；
3. **Variety compare（品种比较）**：对任意一对材料比较 CNVb 指纹，直观展示**共享与差异 marker**，并**基于 CNVb 图谱估算相似度**（Fig. 5c）。示例：**Jimai22 与 Jimai20 相似度 52.6%，各自有 90 与 80 个特有 marker**，从而判定为不同品种；
4. **Geno scan（自定义扫描）**：允许用户上传自己的材料数据进行分析（Fig. 5d）。

> "Generally, the WheatCNVb database offers four main functions. First, the "CNVb profile" function … Second, the "CNVb marker info" function … Third, the "Variety compare" function … Additionally, each variety possesses 90 and 80 unique CNVb markers, respectively (Fig. 5c), confirming their classification as distinct wheat varieties."

**上传新样本 → 比对 → 输出的完整流程（Results Par20 + 平台 Geno Scan 文档）**：

1. **做超低深度测序**：最低 **0.05×（约 1 GB 数据）**；
2. **比对到泛基因组**：从 `http://wheat.cau.edu.cn/WheatCNVb/data/WheatPanGenome.tar.gz` 下载 WheatCNVb 提供的**指定参考泛基因组**（"the specified reference genome WheatPanGenome.tar.gz provided by the WheatCNVb database should be used during resequencing alignment"），用自选比对工具（论文流程为 BWA-MEM）得到 **BAM 文件**；
3. **本地运行 CNVb 扫描脚本**：下载 `http://wheat.cau.edu.cn/WheatCNVb/data/CNVbGenoScan.gz`（即 WheatCNVbScan），脚本基于 BAM 计算 **bin-wise read depth**，产出 4 列 CNVb 文件（chromosome / start / end / CNVb_Status ∈ {deletion, white, duplication}）；
4. **上传 CNVb 文件**到 http://wheat.cau.edu.cn/WheatCNVb/userupload.html ；
5. **等待 1–2 分钟**，页面返回该品种的 **CNVb 指纹**，并可**与库内已有品种或其他已提交品种比较**，完成品种鉴定与相似度评估。

> "Users can perform an ulcWGS to their material, locally prepare the bin-wised read depth file of the accession locally with a pipeline provided on the webpage (http://wheat.cau.edu.cn/WheatCNVb/tutorial.html), and upload the file to the WheatCNVb database (Fig. 5d). The database will facilitate the identification of CNVb markers for the accession, obtaining a CNVb fingerprint that can be compared with varieties stored in the database or other submitted varieties for comprehensive variety identification."

> 平台文档："3. After submitting, wait for **1-2 minutes**, and the page will display the CNVb fingerprint of the wheat variety. 4. Compare your CNVb fingerprint with existing varieties in the database."

**数据库结构与实现**：

- 代码以 **MIT 许可**开源：数据库 https://github.com/Niujx98/WheatCNVbDB （数据存档 Zenodo 10.5281/zenodo.11403154）；检测流程 https://github.com/Niujx98/WheatCNVbScan （Zenodo 10.5281/zenodo.11401875）；
- **技术栈细节（后端语言、数据库引擎、表结构）：未获取到**——论文与 README 均未描述；README 仅一句话说明书库功能；
- 平台依赖：**WheatCNVbScan 需要 bedtools v2.26.0 并加入环境变量 PATH**。

**平台页面与论文数字不一致**：tutorial 页现写 "**1,171** wheat accessions with 1,240 CNVb markers"，与论文的 **1599** 不一致（见第 1 节）。

**输出内容与可视化小结**：输出 = (i) 该材料的 CNVb 指纹（染色体着色图 + QR-code 式矩阵）；(ii) 与库内品种的相似度数值与共享/差异 marker 明细；(iii) 品种鉴定结论。

---

## 12. 原文技术路线与软件/版本

### 12.1 作者给出的 workflow 步骤顺序（整理为流程图式文字）

```
[Pre-step] 泛基因组构建
  17 个小麦 de novo 组装（含 CS RefSeq v1）
    → 除 CS 外 16 个按 contig N50 + 是否 Hi-C 挂载排序
    → 全基因组迭代比对（1 Mb 滑动窗口 + read depth）
       起始参考 Aikang58 → Fielder → … → 16 个品种
    → 975 个 non-CS novel blocks，总长 2.7 Gb，按染色体顺序拼装
    → "chrNCP"
  pan-genome = CS 基因组 + chrNCP
        ↓
[Step 0] 数据准备
  1599 份重测序数据（建库用其中 528 份，平均 5.4×）
  Trimmomatic 去接头/低质量 → BWA-MEM 比对到 pan-genome
  → Bamtools v2.4 过滤异常插入片段（>10,000 bp 或 =0 bp）与低 MAPQ（<1）
  → Samtools v1.3 去 PCR 重复
        ↓
[Step 1] 原始 CNV bins / blocks 检测
  100 Kb 非重叠窗口 → bedtools v2.27.1 coverage 求平均深度
  → 除以全基因组深度众数归一化
  → <0.5 判 deletion 窗口，>1.5 判 duplication 窗口
  → 连续同类窗口合并为 CNV block
        ↓
[Step 2] HMM 平滑 + 低频/短片段过滤
  hmmlearn multinomial HMM（n_components=3, n_iter=60, tol=0.001；Baum-Welch fit；Viterbi decode）
  CS 区块：剔除 (length/100Kb + N) ≤ 10
  chrNCP 区块：剔除 (length/1Mb + N) ≤ 10 或 (length/1Mb + n) ≤ 10
        ↓
[Step 3] 合并去冗余
  重叠合并 ρo ≥ 0.8（ρo = Lo/(L1+L2−Lo)）
  连锁合并：间距 ≤5 Mb 且 ρlink ≥ 0.9（ρlink = Cs/(C1+C2−Cs)）
  chrNCP marker 与 CS marker 基因型高度相关者剔除
  → 初步 marker library；共 8134 个 CNVb marker
        ↓
[Step 4] ulcWGS 稳定性过滤（0.1×）
  hcWGS 与模拟 0.1×（Samtools v1.3.1 下采样）分别基因分型
  present 判据：重叠 ≥90% 且长度差 <1 Mb
  >10 份材料检测不一致 → 剔除
  → 最终 1240 个高质量 CNVb marker（1045 deletion + 195 duplication）
        ↓
[Step 5] 指纹图谱构建
  对 1599 份材料（528 建库 + 1071 公共）计算 CNVb present/absent
  → 每份材料一个 1240 位数字指纹 + QR-code 式二维矩阵
  → 平均每条染色体 59 个 marker，覆盖每条染色体最多 92.6%
        ↓
[Step 6] ulcWGS 扫描与品种鉴定
  新样品 ulcWGS（≥0.05×，约 1 GB）→ 比对 pan-genome → 检测 deletion/duplication blocks
  → 与 CNVb marker 集比对（重叠 ≥90% 且长度差 <100 Kb 判 present）
  → 生成指纹 → 两两 Jaccard 相似度 = M_share/(M_s1+M_s2−M_share)
  → 与 85% 阈值比较 → 同品种 / 不同品种
  → >99.9% 品种可准确分类（深度 >0.05×）
        ↓
[Step 7] 平台化
  WheatCNVb 数据库（CNVb profile / CNVb marker info / Variety compare / Geno scan）
  Geno scan：上传 bin-wise read-depth 文件 → 1–2 分钟返回指纹与比对结果
```

### 12.2 方法与软件版本清单（逐项注明原文是否给出）

| 软件/工具 | 版本（原文） | 用途 | 出处 |
|---|---|---|---|
| **Trimmomatic** | 版本号**未注明** | 原始 reads 修剪（去接头/低质量） | Methods Par26 / Par27 |
| **BWA-MEM** | 版本号**未注明** | 高质量 reads 比对到 wheat pan-genome | Methods Par26 / Par27 |
| **Bamtools** | **v2.4** | 过滤插入片段异常（>10,000 bp 或 =0 bp）与低 MAPQ（<1）的 reads 对 | Methods Par26 |
| **Samtools** | **v1.3**（去 PCR 重复）；**v1.3.1**（BAM 下采样） | 去重、下采样生成 ulcWGS | Methods Par26 / Par33 |
| **bedtools** | **v2.27.1** | `coverage` 函数计算 100 Kb 窗口平均 read depth | Methods Par28 |
| **bedtools**（平台脚本） | **v2.26.0** | WheatCNVbScan 运行依赖（README 要求） | WheatCNVbScan README |
| **hmmlearn（Python 库）** | 库版本**未注明**；模型参数 n_components=3, n_iter=60, tol=0.001 | multinomial HMM 平滑 CNV 信号（Baum-Welch fit + Viterbi decode） | Methods Par30 |
| **GATK** | **v3.868** | HaplotypeCaller 模块、GVCF 模式检测 SNP（对照） | Methods Par35 |
| **mosdepth** | **未使用/未提及** | —（原文用 bedtools coverage 而非 mosdepth） | — |
| **R 包** | **未提及** | —（原文未说明绘图/统计所用 R 包） | — |
| **samtools view -s** | **未提及** | 原文只说 "downsampled … using Samtools v1.3.1" | Methods Par33 |
| **PCR 试剂/条件** | M5 HiPer plus Taq HiFi PCR mix；20 μL 体系；95 ℃ 5 min → 35 循环（95 ℃ 30 s / 60 ℃ 30 s / 72 ℃ 5 min）→ 72 ℃ 5 min | PCR 验证三类 CNVb 等位型 | Methods Par36 |
| **参考基因组** | **Chinese Spring IWGSC RefSeq v1** + **chrNCP** | 比对与 CNV 检测 | Results Par9；Methods Par27 |

> "Trimming of raw reads was performed using **Trimmomatic**, followed by the mapping of high-quality reads to the wheat pan-genome via **BWA-MEM**. **Bamtools v2.4** was used to filter read pairs with either abnormal insert sizes (>10,000 bp or =0 bp) or low mapping quality scores (<1). **Samtools v1.3** was then employed to remove any potential PCR duplicate reads."

> "…utilizing the "coverage" function in **bedtools v2.27.1**."

> "…we employed a multinomial hidden Markov model (HMM) using the **hmmlearn** Python library …"

### 12.3 PCR 验证（三类等位型，Results Fig. 3g–i）

- **Type 1**：引物来自 Jagger 基因组的渗入片段，对应 **CNVb-deletion type 1（CNVb.139, chr2A: 0–24.7 Mb）**；F: 5′-TGCATGTCACTACCACGACC-3′，R: 5′-ACAACCCGTTTTCTTCACGG-3′；
- **Type 2**：引物来自 Zang1817 基因组渗入片段，对应 **CNVb-deletion type 2（CNVb.142, chr2A: 12.0–21.3 Mb）**；F: 5′-TACTTTCGGATTGACAATTATCCTCTTATC-3′，R: 5′-TGGAAAAATGGTCTTACGGTTATATGAAAT-3′；
- **Type 3**：引物来自 CS 基因组 2A: 0–24.7 Mb 区段；F: 5′-GAACTGATTACAAATGAATAGTTGTAGGGA-3′，R: 5′-TTAGTTACACCATGAGTTAGCATCATTTAG-3′；
- 验证结果：**Jagger、Lankao198、Zang1817、Bima4、CS、Aikang58 的扩增结果与 CNVb marker 预测的等位型一致**。

> "results showed the yielded amplification in Jagger, Lankao198, Zang1817, Bima4, CS, and Aikang58 matched with the predicted allele types by CNVb markers. This experiment validated the accuracy of the CNVb marker …"

---

## 参考文献

**目标论文**
1. Niu J, Wang W, Wang Z, Chen Z, Zhang X, Qin Z, Miao L, Yang Z, Xie C, Xin M, Peng H, Yao Y, Liu J, Ni Z, Sun Q, Guo W. Tagging large CNV blocks in wheat boosts digitalization of germplasm resources by ultra-low-coverage sequencing. *Genome Biology*. 2024;25:171. DOI: 10.1186/s13059-024-03315-6. PMID: 38951917. PMCID: PMC11218387.
2. Publisher Correction: Tagging large CNV blocks in wheat boosts digitalization of germplasm resources by ultra-low-coverage sequencing. *Genome Biology*. 2024;25:298. DOI: 10.1186/s13059-024-03442-0. PMCID: PMC11587774. PMID: 39587698.

**本文档实际使用的全文来源**
3. NCBI E-utilities EFetch（PMC 全文 JATS XML）：https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=11218387&retmode=xml
4. NCBI BioC-PMC OA API：https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC11218387/unicode
5. Europe PMC REST（metadata / core）：https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1186/s13059-024-03315-6%22&resultType=core&format=json
6. Unpaywall API：https://api.unpaywall.org/v2/10.1186/s13059-024-03315-6
7. Semantic Scholar Graph API：https://api.semanticscholar.org/graph/v1/paper/DOI:10.1186/s13059-024-03315-6

**平台与代码资源**
8. WheatCNVb 数据库：http://wheat.cau.edu.cn/WheatCNVb/
9. WheatCNVb 教程页：http://wheat.cau.edu.cn/WheatCNVb/tutorial.html
10. WheatCNVb Geno Scan 文档：http://wheat.cau.edu.cn/WheatCNVb/genoscan.html
11. 数据库代码库（MIT）：https://github.com/Niujx98/WheatCNVbDB ；Zenodo 10.5281/zenodo.11403154
12. CNVb 检测流程（MIT）：https://github.com/Niujx98/WheatCNVbScan ；Zenodo 10.5281/zenodo.11401875
13. 泛基因组下载：http://wheat.cau.edu.cn/WheatCNVb/data/WheatPanGenome.tar.gz

**论文内部引用（本次解析涉及的关键编号）**
14. 参考基因组 IWGSC RefSeq v1：International Wheat Genome Sequencing Consortium et al. Shifting the limits in wheat research and breeding using a fully annotated reference genome. *Science*. 2018;361(6403):eaar7191.（原文文献 28）
15. 17 个组装之一的 Aikang58/Fielder 等（原文文献 15, 26, 31–35）
16. Keilwagen J, et al. Detecting major introgressions in wheat and their putative origins using coverage analysis. *Sci Rep*. 2022;12:1908.（原文文献 24，低覆盖度 depth-based 检测大染色体变异的先行工作）

---

## 数据可信度说明

### A. 从全文直接读到（高可信，逐字可核对）

以下条目均来自可完整获取的 JATS 全文 XML（E-utilities EFetch）并经 BioC-PMC 全文分段交叉校验：

1. **数据规模**：186 modern cultivars、342 landraces、528、1071、1599、100 份 >5× 测试集、17 个组装 —— 全部为原文明确数字，且算术自洽（186+342=528；528+1071=1599）。
2. **BioProject 编号**：全部 11 个 SRA/ENA 编号 + CRA005878 + GWHANRF00000000 + PRJCA004332 —— 直接来自 Data availability 段落。
3. **5.4× 平均覆盖度**、**IWGSC RefSeq v1（IWGSCv1）**、**975 blocks / 2.7 Gb / chrNCP / 14 个基因组达平台期** —— 原文逐字。
4. **CNVb 定义**：100 Kb bin、bedtools v2.27.1 coverage、除以深度众数、<0.5 缺失 / >1.5 重复、CNV 块长度 ≥100 Kb。
5. **筛选流程全部阈值**：HMM 参数（n_components=3, n_iter=60, tol=0.001, Viterbi）、(length/100Kb+N)≤10、ρo≥0.8、5 Mb & ρlink≥0.9、8134 → 0.1× 过滤（>10 份不一致即剔除）→ 1240（1045+195）—— 全部为原文明确参数与公式。
6. **Marker 特征**：1240、1045/195、平均每染色体 59、覆盖每条染色体最多 92.6%、panel 达 230 时召回 95%（每轮加 5 份 × 100 次重复）。
7. **ulcWGS 梯度**：0.01×/0.05×/0.1×/0.5×/1×/1.5×；Samtools v1.3.1 下采样；两批 0.05× 重复。
8. **0.05× 结果**：平均 recall 99.3%；0.05×–1.5× 最低 recall >99.0%、最低 precision >97.9%。
9. **指纹编码**：QR-code-like 二维矩阵、每 cell 一个 marker、按染色体排序逐行从左到右从上到下、1240 位。
10. **相似度公式**：similarity = M_share/(M_s1+M_s2−M_share)（Jaccard），逐字含符号定义。
11. **85% 阈值**：出处与依据（distinct variety 分布的 99% 置信区间）；>99.9% 准确分类（深度 >0.05×）；双峰分布。
12. **平台四功能与上传流程**：CNVb profile / CNVb marker info / Variety compare / Geno scan；1–2 分钟返回；Jimai22 vs Jimai20 = 52.6%。
13. **软件版本**：Bamtools v2.4、Samtools v1.3 / v1.3.1、bedtools v2.27.1、GATK v3.868、hmmlearn（参数）。
14. **PCR 引物序列与反应条件**：全部逐字。
15. **Fig. 1–5 全部图注文字**、Table 1 全部数值。

### B. 来自官方平台/代码库（可信，但非论文正文）

16. WheatCNVb 网站四大模块链接、Geno Scan 四步流程、"minimum coverage of 0.05x (~1GB)"。
17. WheatCNVbScan README：bedtools v2.26.0 依赖、4 列 CNVb 文件格式、`WheatPanGenome.tar.gz` 下载地址。
18. 平台 News "17 Aug 2023: WheatCNVb database is now open!"。

### C. 推断或存在原文内部不一致（需谨慎引用）

19. **present 判据的长度差阈值不一致**：Methods "Identification of CNVb markers using ulcWGS"（Par34）写 **<100 Kb**，Methods "Development of CNVb markers" Step 3（Par32）写 **<1 Mb**。两者针对同一"block 匹配 marker"的动作。本文档两者并列如实报告，**未做取舍**。
20. **附表编号不一致**：Results 说 975 blocks 见 Additional file 1: Table S3，Methods 说 pan-genome 见 Table S4；实际编号归属需查附表（无法下载）。
21. **平台与论文样本数不一致**：网站 tutorial 页 "1,171 wheat accessions" vs 论文 "1599"。属网站版本差异，**以论文 1599 为准**。
22. **CNVb 命名前缀混用**：Results 与 Fig. 3 图注中同一 marker 有时写作 `CNVb.67.1`、有时写作 `CNV.67.1`（`CNVb` 与 `CNV` 混用），经上下文比对确认指同一物，属原文笔误。
23. **CNVb.67.1 材料数不一致**：Table 1 记 111 份，正文称"16 个经 FISH 确认携带 1RS·1BL 的材料 + 额外 95 份"（16+95=111，可与表一致，属表述而非矛盾）。

### D. 未获取到（明确缺失，禁止推测）

24. **测序平台型号与读长**（如 Illumina NovaSeq PE150 之类）—— 正文完全未提，仅在致谢中出现 "Illumina sequencing data"。
25. **Fig. 2c 中各覆盖度下 SNP / raw CNV / CNVb 的逐点 recall 数值** —— 仅以图形呈现；图片位于 PMC/Springer，本次抓取被 reCAPTCHA 与跨域重定向拦截，且 modlens 图像读取服务网络不可达。
26. **ROC 曲线 / AUC** —— 全文未出现，阈值基于置信区间。
27. **每样本测序成本的具体金额（货币单位）** —— 正文无任何金额；定量成本对比位于 Additional file 2: Table S9（无法下载）。仅有定性结论与 ~1 GB @0.05× 的数据量信息。
28. **Additional file 1（XLSX，含 Table S1–S8）、Additional file 2（PDF，含 Supplementary Figures S1–S12 与 Table S9）、Additional file 3（DOCX，审稿历史）** —— PMC 全部被 reCAPTCHA 拦截，**未下载到任何一个**。因此 Table S1 中的测序平台、读长、每份材料的深度、Table S9 的成本明细，均**未获取到**。
29. **HMM 平滑后的"short-length / low-frequency"过滤中，除 (length/100Kb+N)≤10 之外是否还有独立的长度下限或频率下限** —— 原文只给出该复合判据，**未给出单独的 bp 长度阈值或频率百分比阈值**。
30. **samtools 下采样的具体命令与随机种子** —— 原文只说 "downsampled … using Samtools v1.3.1"，未写 `samtools view -s` 或种子；重复批次仅明确 2 批。
31. **WheatCNVb 数据库的技术栈（后端框架、数据库引擎、表结构、API 设计）** —— 论文与 README 均未描述。
32. **QR 码式指纹是否含定位图案（finder pattern）/ 纠错机制** —— 原文未提及，仅有 "QR-code-like" 的类比描述。
33. **同名异种（EDV）的具体判别案例与数字** —— Discussion 仅提出应用设想，未给数据。
34. **Trimmomatic、BWA-MEM、hmmlearn 的具体版本号** —— 原文均未注明版本。
35. **R 包 / 统计绘图工具** —— 原文未提及。

### E. 解析方法学说明

- 主证据源为 **NCBI E-utilities EFetch 返回的完整 JATS XML**（正文 + Methods + Data availability + 参考文献），该请求返回 HTTP 200 且未被截断，保存于 `D:\dsh\RiceVar-ID\docs\methods\_raw\efetch_pmc11218387_raw.txt`；同时保存 BioC-PMC 全文 JSON 于同目录 `bioc_pmc11218387_raw.txt` 用于交叉校验。
- 因 PMC 网页版/PDF、BMC/Springer 站点、Europe PMC 站点三者分别被 reCAPTCHA、跨域重定向、Cloudflare 403 拦截，**PDF 版式与原刊 HTML 未获取**；但 JATS XML 与 PDF 的正文内容一致，不影响正文级信息完整性。
- 本地沙箱中 pwsh 无网络出口（`curl` 返回 http=000），所有网络抓取均通过 web_fetch / 专用 API 完成。
- 本文件所有英文引用均为原文逐字（仅统一了引号/连字符的排版差异），未做任何改写或补全。
