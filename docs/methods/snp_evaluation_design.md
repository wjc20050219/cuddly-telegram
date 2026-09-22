# 本科版 SNP 指纹与验证设计（预注册草案）

> 本文件是分析方案，不是结果。所有数值结论等待真实 FASTQ 计算。

## 1. 真值与测试对象

- **高深度真值**：Pilot 30 每份样本经 QC、比对和联合 SNP calling 后的高置信基因型；
- **技术测试**：同一份 Pilot CRAM 按六档深度随机降采样，每档 3–5 个不同 seed；
- **开放集负样本**：品种零重叠的冻结独立面板 25 份；
- **更强外部验证（可选）**：同品种独立 BioSample/run。没有此类数据时，不把技术降采样称为独立生物学验证。

## 2. 防止一个关键分型错误

不能把多个“仅包含变异位点的单样本 VCF”直接拼成矩阵，并把其他 VCF 中未出现的位点记为 missing。未出现可能代表 `0/0`，也可能代表无覆盖，两者含义不同。

现行方案必须满足其一：

1. Pilot CRAM 联合 `bcftools mpileup/call`，在同一位点集合上输出所有样本 GT/DP/GQ；或
2. 先在 Pilot 发现并冻结候选位点，再对所有高深度/低深度样本用 `bcftools mpileup -R markers.bed` 定点分型。

历史 `server/build_matrices.py` 的单样本 variant-only VCF 合并命令已删除；正式矩阵统一由 `scripts/select_snp_markers.py` 从联合多样本 VCF 生成。

## 3. SNP QC 与 marker 筛选

所有阈值作为配置参数保存，不写死成科研结论。初始候选值：

- biallelic SNP；
- site QUAL、样本 DP/GQ 过滤；
- site missing rate；
- MAF（可从 0.05 起做敏感性检查）；
- 去除高度连锁/冗余位点；
- 只在 Pilot 中按区分度排序。

比较冻结的 500 / 1000 / 2000 SNP 集。marker 排序不得查看独立面板结果。

## 4. 指纹和相似度

- 主要编码：0/1/2 dosage，缺失为 NA；
- 主要相似度：IBS（仅在双方均有 call 的 marker 上计算）；
- Hamming：用于双方均有离散基因型的位点；
- Jaccard：只用于明确定义的二元 presence/absence 编码，不能直接把 0/1/2 不加说明地套入 Jaccard；
- 每次比较同时报告 `n_compared_markers`、`compared_marker_rate` 与 `n_different_markers`，防止极少位点偶然高相似。

### 4.1 PCA 图的输入与缺失值处理

PCA 图（TASK-036）读的是 `export_similarity_matrix.py` 导出的品种间方阵，不是
`per_query.tsv`——`per_query.tsv` 只记录每条查询的最佳匹配，无法给出全部品种的坐标。

| 情形 | 处理 | 理由 |
| --- | --- | --- |
| 方阵文件缺失或不是方阵 | 跳过该图 | 无数据不产图 |
| 品种数 < 3 | 跳过该图 | 两个点的主成分没有意义 |
| 格子未测量（可比位点不足） | 用该行**非对角**已测量值的均值填补 | 当作 0（"完全不相似"）会把两个品种仅因缺数据就拉到 PC1 两端 |
| 某品种除自身外没有可比对的格子 | 该品种从分析中剔除并记录 | 对角线恒为 1，不含"这个品种在哪"的信息；若用它填满整行，该品种会变成"与所有品种完全相同"，是凭空造出的相似度 |
| 所有品种指纹完全相同 | 跳过该图 | 没有方差，主成分方向任意 |

PCA 用**标准库**实现（对 `n × n` Gram 矩阵做幂迭代），不引入 numpy；本机与 ricevar
环境行为一致。解释方差比例随图一起写入 `fig_pca_coordinates.tsv`，因为脱离方差比例的
坐标在论文里无法解读。

### 4.2 必须显式声明的相似度方法，两条路径共用同一实现

`identify()`（识别）与 `compare_varieties()`（品种两两比较）**都**接受 `method`
参数，取值 `ibs` / `hamming` / `jaccard`，并复用 `src/ricevar_id/fingerprint.py`
中的同一组函数，因此两处报告的相似度处于**同一尺度**，论文中可以直接并列成表。

- 默认方法：**IBS**（`server/07_identify.sh` 的 `RV_METHOD` 默认 `ibs`）。
- 输出必须带上实际使用的方法名（`summary.json` 的 `parameters.method`；
  `compare_varieties()` 返回值中的 `method` 字段），否则无法从结果追溯尺度。
- **不得**把不同方法算出的相似度混入同一张表或同一条曲线。

方法选择会改变结论，必须报告：在 query `[0,0]`、参考 `[1,1]` 与 `[0,2]` 上，
IBS 判 Top-1 为前者（并列后按 id 打破），Hamming 判为后者。因此"用哪个方法"
属于**预先冻结的实验参数**，不得在看到结果后再挑选。

### 4.3 `n_different_markers` 的准确含义

`n_different_markers` 统计**双方均有 call 且基因型不同的位点数**，与
`(1 - similarity) × n_compared_markers` **不是同一个量**：IBS 的分子是
`Σ|a-b|`，一个 0/2 对贡献 2，而该位点只计 1 个"差异位点"。
例：query `[0,0]` vs ref `[1,2]`，IBS = 0.25，`n_different_markers` = 2，
而 `(1-0.25)×2 = 1.5`。论文中若同时引用相似度与差异位点数，必须说明二者定义。

## 5. 识别输出

每个 query 输出：Top-1、Top-5、相似度、比较 marker 数、差异 marker 数和是否拒识。

- 闭集 Top-1：降采样 query 的真实同源高深度 Pilot 样本是否排名第一；
- Top-5：真实同源样本是否在前五；
- 开放集：独立零重叠样本是否被阈值正确拒识；
- 阈值：仅用 Pilot 内部验证校准，不照搬小麦 85%。

## 6. 深度和重复

固定六档：1、0.5、0.2、0.1、0.05、0.02×。每档至少 3 次，论文正式结果优先 5 次。每条记录必须保存：样本、目标深度、原始估计深度、抽样比例、seed、实际抽样后深度、工具版本。

`samtools view -s` 的参数由整数 seed 与 0–1 抽样比例组成。实现时必须单独测试参数格式，不能把已经含小数点的比例简单拼成 `seed.fraction` 后未经验证地使用。

## 7. 两阶段执行约束

`server/05_simulate.sh` 在没有冻结 marker target 时只完成降采样和深度 BED；提供 target 后会追加固定等位基因分型。正式实验必须分两阶段：

1. Pilot 高深度联合 calling → 本机 QC/排序 → 冻结 marker 位点；
2. 用 `server/prepare_marker_targets.sh` 把冻结 marker VCF 转为等位基因 target（三列）和 region target（两列）；
3. 设置 `RV_MARKER_TARGET` 后重跑 `server/05_simulate.sh`，脚本会在临时降采样 BAM 删除前输出 `markers.vcf.gz`；
4. 运行 `server/07_identify.sh`：把低深度定点 VCF 投影到冻结 marker 集，输出 recall/concordance/Top-1/Top-5/拒识。

第 4 步的实现约定：

- `src/ricevar_id/genotypes.py` 负责读取 Pilot 矩阵和低深度 VCF，并把 query **投影到冻结 marker 集**：query 未覆盖的位点记为 missing，绝不记为参考基因型；出现冻结集之外的位点直接报错。
- `scripts/evaluate_identification.py` 只允许对自定义深度做技术重复评估，输出的 `summary.json` 固定写入闭集声明。
- 参考矩阵中不排除 query 自身所属样本，因此会同时报告 `top1_correct_sample` 与 `top1_correct_variety`：前者反映“能否回到原样本”，后者才是品种级准确率。
- `--min-compared` 默认 50：比较 marker 过少时 IBS 得分记 NaN，避免个别位点偶然全同被当作匹配。

这套评估的 query 是 Pilot 样本自身 CRAM 的降采样，属**闭集技术重复**，只能支持“深度–识别率”曲线，不能声称同品种独立 Top-1。冻结的独立 25 面板与 Pilot 品种零重叠，只能用于**开放集拒识**；同品种独立重复必须单独寻找并单独报告。

定点分型与评估代码已实现并通过合成输入测试，但尚未在真实服务器/BAM 上运行。在 1/5 样本 smoke test 通过前，不得把深度 BED 或未验证 VCF 当作 SNP 指纹/识别结果。`run_all.sh` 当前是基础设施冒烟编排，不是“一次运行即可得到论文最终准确率”的声明。

## 8. 主要表与图

- `identification_by_depth.tsv`：marker_count × depth 的 recall/concordance/Top-1/Top-5/accept；
- `per_query.tsv`：逐 query 的 marker recall、最佳匹配、比较位点数、差异位点数、拒识状态；
- `depth_accuracy.tsv`：depth × replicate × marker_count × Top-1/Top-5（由 `per_query.tsv` 派生）；
- `marker_recall.tsv`：可比较 marker、正确 GT、recall/concordance；
- `open_set.tsv`：known/unknown、score、threshold、accept/reject（独立面板，仅拒识）；
- PCA、相似度热图、指纹图、depth–recall、depth–accuracy、marker count–accuracy；
- 若同品种重复不足，ROC/AUC 的单位与正负样本构造必须在方法中明示，不制造“独立实验”措辞。
