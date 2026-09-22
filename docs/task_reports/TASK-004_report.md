# TASK-004 报告：阅读并解析参考论文

- 日期：2026-09-15
- 结果：✅ 完成（12 项要求全部提取，其中 4 项原文缺失已显式标注）
- 阶段：Phase 1 · 解析小麦论文技术路线

## 0. 解析对象与证据来源

| 项目 | 内容 |
| --- | --- |
| 论文 | Niu J, Wang W, Wang Z, et al. *Tagging large CNV blocks in wheat boosts digitalization of germplasm resources by ultra-low-coverage sequencing.* **Genome Biology**, 2024, 25:171 |
| DOI / PMID / PMCID | 10.1186/s13059-024-03315-6 / 38951917 / PMC11218387 |
| 勘误 | 存在 Publisher Correction（10.1186/s13059-024-03442-0, Genome Biol 25:298），内容仅为同等贡献声明，不影响技术参数 |
| 全文获取路径 | PMC / BMC 网页与 PDF 被 reCAPTCHA 与跨域重定向拦截；改用 **NCBI E-utilities EFetch**（`eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=11218387&retmode=xml`）取得完整 JATS 全文，并以 BioC-PMC OA API 交叉校验 |
| 逐字证据留档 | `docs/methods/paper_niu2024_extraction.md`（601 行，含 12 节 + 英文原文引用块 + 可信度分级）；原始 XML 证据在 `docs/methods/_raw/` |

> 本报告是**执行报告**（结论与参数索引）；逐字原文引用、公式推导与"未获取到"清单见上述解析文档，两者配合使用。

## 1. 数据规模

| 批次 | 数量 | 用途 |
| --- | --- | --- |
| 本研究新测/收集高深度重测序 | **528**（186 现代品种 + 342 地方品种） | CNVb marker 建库 |
| 并入公开重测序数据 | **+1071** | 扩充指纹图 |
| 合计指纹图 | **1599** | 全基因组 CNVb 指纹图谱 |
| 深度 >5× 的随机子集 | **100** | ulcWGS 模拟测试集 |
| 非建库材料随机子集 | **100** | 泛化能力测试（0.05× × 2 批） |

- 数据来源：文中列出 11 个 SRA/ENA BioProject（PRJNA544491、PRJNA722149、PRJNA476679、PRJNA597250、PRJNA596843、PRJNA439156、PRJNA663409、PRJEB48988、PRJEB48738 等）与 NGDC CRA005878。
- **测序平台型号与读长：原文未给出**（仅在致谢出现 "Illumina sequencing data"）；相关明细在补充材料 Table S1（被 reCAPTCHA 拦截，未获取到）。

## 2. WGS 深度与参考基因组

- 建库 panel 的**平均测序深度 5.4×**；测试集要求 **>5×**。
- 主参考基因组：**Chinese Spring IWGSC RefSeq v1**（注意：不是 v2.0）。
- **泛基因组（pan-genome）构建**：以 16 个 *de novo* 组装（不含 CS）按组装质量排序，用 **1 Mb 滑动窗口**迭代比对，收集 CS 中缺失的序列，得到 **975 个 novel blocks / 总计 2.7 Gb**，拼装为一条人工染色体 **"chrNCP"**；饱和分析显示纳入 **14 个**基因组后趋于平台期，最终整合 **17 个**组装。
- 参考基因组选型动机：**缓解单参考基因组带来的 CNVb 识别偏倚**——这一动机对水稻同样成立（RiceVar-ID 的 TASK-025 将复现同类评估）。

## 3. CNVb 定义

- **窗口**：基因组切为 **100 Kb 非重叠窗口**；用 bedtools v2.27.1 `coverage` 计算平均 read depth。
- **归一化**：每个窗口深度 **除以全基因组深度的众数（mode）**，得到 relative read depth。
- **判定**：normalized depth **< 0.5 → deletion 窗口**；**> 1.5 → duplication 窗口**；连续同类窗口合并成 CNV block。
- **CNVb 长度阈值：≥ 100 Kb**（Fig. 1e 图注）。
- **扫描阶段的 present 判据**：样品中的 block 与 marker **重叠 ≥ 90%**，且**长度差 < 100 Kb**（Methods Par34）；但 Methods Par32（建库 Step 3）写的是**长度差 < 1 Mb** —— **原文内部不一致，引用时须并列注明**。
- 规模背景（说明小麦为何适合此路线）：至少 1 份材料中判为 deletion/duplication 的非冗余 bin 合计 **8430 Mb / 3375 Mb**；各品种 CNV 总长 139–1567 Mb，81.6% 材料 >500 Mb，平均每材料 2061 个 CNV 区域；对照 **水稻平均总长仅 142 Kb、平均 19 个 CNV 区域**。

## 4. CNVb 筛选流程（8134 → 1240）

在 **528 份**材料上三阶段完成：

| 步骤 | 操作 | 阈值/参数 | 输出 |
| --- | --- | --- | --- |
| — | 100 Kb 窗口 read depth ÷ 全基因组众数 | <0.5 缺失 / >1.5 重复 | 原始 CNV bins |
| Step 1 | **HMM 平滑**（multinomial HMM，Python `hmmlearn`） | `n_components=3, n_iter=60, tol=0.001`，Baum-Welch 训练，Viterbi 解码 | 连续 CNV blocks |
| Step 1 | 长度 + 频率联合过滤 | CS 区：剔除 **(len/100 Kb + N) ≤ 10**；chrNCP 区：剔除 **(len/1 Mb + N) ≤ 10** 或 **(len/1 Mb + n) ≤ 10**（N=含该 blocks 的材料数，n=不含的材料数） | — |
| Step 2 | 重叠合并 + 连锁合并 | **ρ_o ≥ 0.8** 合并重叠块；**间距 ≤ 5 Mb 且 ρ_link ≥ 0.9** 合并连锁块；chrNCP marker 若与某 CS marker 基因型高度相关则剔除 | **8134 CNVb** |
| Step 3 | **0.1× ulcWGS 稳定性过滤** | 重叠 ≥90% 且长度差 <1 Mb 判 present；**在 >10 份材料中检测不一致的 marker 剔除** | **1240 CNVb（1045 deletion + 195 duplication）** |

其中 ρ_o = L_o/(L_1+L_2−L_o)，ρ_link = C_s/(C_1+C_2−C_s)。

## 5. Marker 数量与特征

- **最终 1240 个**非冗余高质量 CNVb marker = **1045 个 deletion + 195 个 duplication**（缺失型 84.3%）。
- 分布于全部染色体，**平均每条染色体 59 个**；覆盖每条染色体最多 **92.6%** 的区域。
- **饱和分析**：每轮随机加 5 份材料、每点 100 次重复；**panel 达 230 份时即可召回 95% 的 CNVb marker**。
- 命名规则：`CNVb.<整数>`，同区段不同亚型用小数后缀（`CNVb.67.1` / `CNVb.67.2`）。**原文存在 `CNVb.` 与 `CNV.` 前缀混用**（同一 marker 两种写法）。
- 指纹层面：每份材料 present 的 marker 数 **119–322**；两两材料平均 **199 个** marker 基因型不同；**99.5% 的材料对差异 marker 数 >100**；姊妹系 Bima1 vs Bima4 差异 **117 个**。
- 与已知变异/优异等位基因挂钩（可用于功能解释）：1RS·1BL（CNVb.67.1）、2NvS（CNVb.189）、*Glu-D1d*（CNVb.162）、*r-e-z* 半矮秆缺失（CNVb.647）、perInv-6B（CNVb.989）等。

## 6. ulcWGS 方法

- **并非新测序**，而是对已有高深度 BAM **随机下采样**，工具 **Samtools v1.3.1**（原文未给具体子命令与随机种子）。
- 测试集：**100 份 >5× 材料**下采样至 **6 档：0.01× / 0.05× / 0.1× / 0.5× / 1× / 1.5×**。
  - 核对：任务清单与前期讨论中设想的 0.02×、0.2× **在原文中不存在**；可靠性统计实际只报告 **0.05×、0.1×、0.5×、1.0×、1.5×** 五档。
- **重复设计**：品种鉴定模拟以"0.05× 低深度数据（replicate 1）vs 同批高深度数据（replicate 2）"两两比较；泛化测试另取 100 份非建库材料，**分 2 批**下采样到 0.05× 互为重复。**>2 次的技术重复：原文未做**。
- **建库筛选阶段使用的 ulcWGS 深度 = 0.1×**。
- 平台侧最低要求：**0.05× ≈ 1 GB 数据量/sample**。

## 7. 0.05× 分析结果

- **核心数字：0.05× 下 CNVb marker 平均 recall = 99.3%**，且优于 raw CNV 与 SNP（Fig. 2c）。
- **Fig. 2c 的逐点数值未在正文给出**（且图片抓取被拦截）→ 逐点 recall：未获取到；可确证的是 CNVb > raw CNV > SNP，且深度越低差距越大。
- 0.05×–1.5× 五档：**每份材料的最低 recall >99.0%、最低 precision >97.9%**（Fig. 4d）。
- **0.1× 的作用容易被误解**：它不是 recall 阈值，而是"剔除低深度不稳定 marker 的测试深度"（判据见第 4 节 Step 3）。
- SNP 对照：**GATK v3.868 HaplotypeCaller（GVCF 模式）**，以高深度结果为金标准比较三者 recall。

## 8. 指纹编码

- **编码：0/1 presence–absence，每位 = 1 个 CNVb marker，单样本指纹共 1240 位。**
- 二维可视化：marker **按染色体排序**，**从左到右、从上到下逐行填入**矩阵（Fig. 4a 图注）。
- **"QR-code-like" 仅为类比**：原文未描述定位图案、静区或纠错机制；按"1240 位规则网格"理解，它是二值指纹矩阵而非可被扫码器解码的真 QR 码。
- 平台提供两种可视化：染色体图谱（着色区段）+ 1240 位 QR-like 矩阵。
- 平台上传的中间文件格式（来自 WheatCNVb 官方代码库，非论文正文）：4 列 `chromosome / start_position / end_position / CNVb_Status`，状态取值 `deletion | white | duplication`。

## 9. 相似度计算

- **公式（Jaccard 相似系数）**：`similarity = M_share / (M_s1 + M_s2 − M_share)`，M_s1、M_s2 为两份材料的 marker 总数，M_share 为共有 marker 数。
- **原文没有**"先算共享 marker 数、再算相似度"的两步阈值流程；判定只有一步：指纹 → Jaccard → 与阈值比较。
- 外部校验：CNVb 相似度与基于种质的 gIBD 相似度高度相关（similarity >0.4 时 **Pearson r = 0.85, P < 2.2×10⁻¹²**）。
- 距离度量：原文只用 Jaccard，未使用 Hamming/欧氏距离。

## 10. 品种判定与阈值

- **阈值 = 85% similarity**，选取依据是 **"distinct variety" 相似度分布的 99% 置信区间**（Results Par18），而非 ROC 最优点。
- **相似度呈双峰分布**（同品种 / 不同品种两个峰），这是 85% 能干净切分的基础。
- **准确率：>0.05× 时 >99.9% 的品种可被准确分类**。
- 评价指标：**Power of variety identification** = 正确识别的"不同品种对"/总"不同品种对"；另用 statistical power (1−β)。
- **ROC / AUC：全文未使用（未获取到）**；**每样本成本金额：未获取到**（定量对比在 Additional file 2: Table S9，被拦截）；可确证的只有"0.05× ≈ 1 GB"与定性结论（成本显著低于 SNP array，与 SSR/GBS 相当；可靠性"与 SNP array 相当、优于 GBS"）。
- 近缘材料：可区分 similarity >40% 的近缘材料；**同名异种（EDV）只给出方向性论述，无具体案例数字**。

## 11. 数据库与平台设计

- 平台：**WheatCNVb**，http://wheat.cau.edu.cn/WheatCNVb/
- 四大模块：CNVb profile / CNVb marker info / Variety compare / Geno scan。
- 新样本流程：**0.05× 测序 → 比对到 WheatPanGenome 参考包 → 本地运行 CNVbGenoScan 生成 4 列 CNVb 状态文件 → 网页上传 → 1–2 分钟返回指纹与库内品种比对结果**。
- 平台后端技术栈与数据库表结构：**未获取到**。
- 一致性提示：官网 tutorial 现写 "1,171 wheat accessions"，与论文 **1599** 不符（以论文为准）。

## 12. 原文技术路线与软件版本

```
Trimmomatic（质控）
   ↓
BWA-MEM（比对 CS / pan-genome）→ Bamtools v2.4（BAM 处理）
   ↓
Samtools v1.3 / v1.3.1（排序、去重、下采样）
   ↓
bedtools v2.27.1（100 Kb 窗口 read depth）
   ↓
hmmlearn HMM（n_components=3, n_iter=60, tol=0.001, Viterbi）
   ↓
CNV block → 过滤/合并 → 8134 CNVb → 0.1× 稳定性过滤 → 1240 CNVb
   ↓
0/1 二进制指纹（1240 位）→ Jaccard 相似度 → 85% 阈值判定 → WheatCNVb 平台
```

- 对照方法：GATK v3.868（SNP recall 基准）。
- **原文未使用 mosdepth，也未提及 R 包**；Trimmomatic / BWA-MEM / hmmlearn 的版本号未给出。
- 验证：对 2A 端部三种等位型做 **PCR 验证**，与 CNVb 预测一致（Fig. 3g–i）。

## 13. 原文内部不一致与缺失项（引用风险清单）

**内部不一致（2 处）**
1. present 判据的"长度差"阈值：Methods Par34 写 **<100 Kb**，Par32（Step 3）写 **<1 Mb**。
2. marker 前缀混用：`CNVb.67.1` 与 `CNV.67.1` 指同一 marker。

**未获取到（禁止推测，RiceVar-ID 需自行确定）**
- 测序平台型号与读长；samtools 下采样具体命令与随机种子；
- Fig. 2c 各覆盖度下 SNP / raw CNV / CNVb 的逐点 recall 数值；
- ROC / AUC（全文无）；每样本成本金额；同名异种（EDV）具体案例数字；
- **全部补充材料**（Additional file 1 XLSX / 2 PDF / 3 DOCX）：Table S1 平台与深度明细、Table S9 成本对比表；
- WheatCNVb 后端技术栈与表结构；真 QR 码所需的定位图案设计。

## 14. 对 RiceVar-ID 的直接影响（移交 TASK-005 / TASK-006）

1. **可直接迁移**：窗口化 relative read depth 的思路、HMM 平滑、重叠/连锁合并逻辑、0/1 指纹 + Jaccard + 单阈值判定、二维码式指纹展示、平台"上传—比对—返回 Top 候选"的交互范式。
2. **必须重新优化**：
   - **CNV 尺度完全不同**——小麦平均每材料 2061 个 CNV 区域、CNV 总长可达 GB 级；**水稻平均仅 19 个 CNV 区域、总长 142 Kb**。照搬 100 Kb 窗口 + ≥100 Kb 长度阈值，水稻几乎筛不出 marker。→ 需要在 TASK-038 系统比较 **10 kb / 50 kb / 100 kb** 窗口（任务清单已列出）并重新确定长度阈值。
   - **倍性与重复序列**：六倍体 16 Gb → 二倍体 ~400 Mb，CNV 检测的信噪比基础不同。
   - **85% 阈值不可照搬**：必须按 TASK-053 后续要求，用水稻真实数据重算同品种/不同品种相似度分布，给出 ROC/AUC/F1（小麦论文没有 ROC/AUC，恰好是水稻项目的增量贡献点）。
   - **ulcWGS 深度梯度**：小麦用了 0.01/0.05/0.1/0.5/1/1.5×，本任务清单要求 **0.01/0.02/0.05/0.10/0.20/0.50/1.00× 共 7 档且每档 ≥5 重复**——比小麦论文更细、重复更多（小麦只做了 2 批），这是本项目的方法学增量。
   - **标记类型不能预设 CNV 最优**：小麦的 CNVb 优势来自其超大 CNV 块这一物种特性；水稻必须在 SNP / k-mer / CNV / SV 四条路线间实测比较（Phase 12）。
3. **可直接作为 benchmark 的部分**：小麦的"低深度下 marker recall vs SNP recall"对比设计、marker 饱和分析、panel 规模—marker 召回曲线，均可原样移植到水稻，用于 TASK-051/TASK-052。

## 15. 产出物与后续

| 产出 | 路径 |
| --- | --- |
| 本执行报告 | `docs/task_reports/TASK-004_report.md` |
| 论文全文技术解析（12 节 + 原文引用 + 可信度分级） | `docs/methods/paper_niu2024_extraction.md` |
| 原始全文证据 | `docs/methods/_raw/efetch_pmc11218387_raw.txt`、`docs/methods/_raw/bioc_pmc11218387_raw.txt` |

下一步（Phase 1 剩余）：**TASK-005** 输出 `paper_workflow.md`（论文技术路线图）；**TASK-006** 建立"小麦 → 水稻"技术迁移表，明确哪些方法可直接迁移、哪些必须重新优化——本报告第 14 节已给出可直接复用的结论要点。
