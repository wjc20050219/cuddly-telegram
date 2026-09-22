# 服务器 / 本机 分工架构设计

- 日期：2026-09-15
- 决策：**重活（下载 + 比对 + 逐样本分型）放学校服务器；分析与写作放本机**
- 核心目标：不让 400 GB 的中间数据过网——把"reads/BAM 空间"在服务器上压成"特征矩阵空间"再传回

---

## 一、分工总表

| 阶段 | 步骤 | 放哪 | 理由 |
| --- | --- | --- | --- |
| Phase 3–4 | SRA/ENA 检索、样本表、去重 | 本机 | 只查元数据，流量小 |
| Phase 5 | **FASTQ 下载**（~113 GB） | **服务器** | 网络 + 磁盘都在服务器 |
| Phase 6 | FastQC / fastp | **服务器** | 读级操作 |
| Phase 7 | 参考基因组下载、建 BWA 索引 | **服务器**（本机留一份序列文件） | 索引 4–5 GB、加载 5–6 GB 内存 |
| Phase 8 | BWA-MEM2 比对 + sort + index | **服务器** | 最重的一步（40–75 小时） |
| Phase 8 | bcftools mpileup + call（逐样本） | **服务器** | 读级操作 |
| Phase 8 | 合并 + 过滤 → 变异矩阵 | 服务器算，**产物传回** | 产物只有 ~1 GB（PLINK 格式） |
| Phase 9 | KMC / Jellyfish k-mer 计数 | **服务器** | 读级操作 |
| Phase 9 | k-mer 降维 → 样本×k-mer 矩阵 | 服务器算，**产物传回** | ~50–200 MB |
| Phase 10 | **mosdepth 窗口深度** | **服务器** | 读级操作，但**产物极小** |
| Phase 11 | SV/PAV：公开 VCF 直接下载 | 本机 | 无需 reads |
| Phase 13 | **ulcWGS 下采样 + 各档深度矩阵** | **服务器** | 需要 BAM；产物 ~900 MB |
| Phase 8–13 | **全部统计、标记筛选、指纹、相似度、阈值、ROC/AUC、图** | **本机** | 纯矩阵运算，本机绰绰有余 |
| 数据库 / Web / 论文 | 全部 | **本机** | 轻量 |

---

## 二、核心设计：只让"特征矩阵"过网

### 2.1 为什么不能传 BAM

| 若按常规做法 | 体积 |
| --- | --- |
| 180 份 FASTQ | 113 GB |
| 180 份 BAM | 180 GB |
| 7 档 ×10 重复的下采样 BAM | **数 TB** |
| 合计过网 | **~3 TB → 不可行** |

### 2.2 实际需要过网的东西

关键认识：**本项目的下游分析根本不需要 reads，只需要"每个样本在每个标记/窗口上的信号"。**
把这一步在服务器上完成，过网体积直接掉三个数量级。

| 服务器产物 | 计算方式 | 体积 | 传回 |
| --- | --- | --- | --- |
| **窗口深度矩阵**（10 kb） | mosdepth → 37,500 窗口 × 180 样本 × int16 | **13 MB** | ✅ 必传 |
| 窗口深度矩阵（50 kb / 100 kb / 1 Mb） | 同上，聚合 | 2.6 / 1.3 / 0.13 MB | ✅ |
| **ulcWGS 各档深度矩阵** | 7 档 × 10 重复 × 13 MB | **910 MB** | ✅ 必传（Phase 13 的核心） |
| **SNP 基因型矩阵**（PLINK bed） | 合并 VCF → MAF/缺失过滤 → plink2 | **~200 MB**（180 × 4M SNP） | ✅ 必传 |
| 分析就绪 VCF（供本地重筛） | bcftools 过滤后 | ~1 GB | ✅ 建议传 |
| k-mer 矩阵（稀疏） | KMC → 筛选 → 稀疏矩阵 | 50–200 MB | ✅ |
| SV/PAV 基因型矩阵 | 公开 SV VCF | 几–几十 MB | ✅ |
| mapping / depth QC 汇总表 | samtools stats / mosdepth | < 1 MB | ✅ |
| 标记召回、鉴定准确率汇总 | 服务器端预计算 | < 1 MB | ✅ |
| 原始 FASTQ / BAM / 下采样 BAM | — | 数 TB | ❌ **留在服务器** |

> **过网总量：约 2 GB（必传）+ 1 GB（VCF）≈ 3 GB**，而不是 3 TB。
> 本机 424 GB 磁盘完全无压力；矩阵尺寸对 16 GB 内存也毫无压力（180 × 4M 的 int8 矩阵仅 720 MB）。

### 2.3 一个重要的架构后果

**本机的内存/磁盘瓶颈在矩阵阶段自动消失。**
之前的评估里，16 GB 内存和 424 GB 磁盘是瓶颈——那两个瓶颈**全部来自读级操作（比对、排序）**。一旦这些留在服务器，本机处理的只是 MB–GB 级矩阵：

| 分析 | 本机内存需求 |
| --- | --- |
| 180 样本 × 4M SNP PCA | ~1–2 GB |
| 180 × 37,500 深度矩阵 CNV 分块 | < 100 MB |
| 3000 样本 × 1M SNP（扩到 3K 水稻公开数据） | ~3 GB |
| ROC/AUC/阈值扫描 | < 1 GB |

→ **在服务器方案下，本机不需要加内存也能完成论文**（加内存只是让并行更舒服）。

---

## 三、服务器侧流水线（阶段划分）

```
[S0] 数据获取     fasterq-dump / prefetch / ENA FTP   →  data/raw/*.fastq.gz   (~113 GB)
       ↓
[S1] 质控         fastqc + fastp                      →  data/qc/*             (~100 GB)
       ↓
[S2] 比对         bwa-mem2 mem -t 32 | samtools sort -m 2G
                                                      →  data/bam/*.cram      (~90 GB CRAM)
       ↓
[S3] 分型         bcftools mpileup -Ou | bcftools call -mv    （逐样本并行）
                                                      →  data/vcf/*.vcf.gz    (~5 GB)
       ↓
[S4] 深度         mosdepth -b 10000/50000/100000/1000000      （逐样本并行）
                                                      →  data/depth/*.bed.gz  (~3 GB)
       ↓
[S5] k-mer        kmc -k21/31/51 → 筛选 → 矩阵        →  data/kmer/*          (~50 GB，筛后小)
       ↓
[S6] 汇总导出     ① bcftools merge + 过滤 → plink2 bed
                 ② 深度 BED → 窗口×样本矩阵（parquet）
                 ③ k-mer → 稀疏矩阵
                 ④ QC 汇总表
                                                      →  export/  (~3 GB)  ★过网点
       ↓
[S7] ulcWGS 模拟  for depth in 0.01 0.02 0.05 0.1 0.2 0.5 1.0:
                     for rep in 1..10:
                       samtools view -s <seed> -b sample.cram     ← 抽 reads
                       mosdepth -b 10000                          ← 立刻算深度
                       rm 下采样 BAM                              ← 不落盘
                                                      →  export/depth_sim/  (~900 MB)  ★过网点
```

**关键实现要点**

1. **下采样 BAM 绝不落盘**：`samtools view -s` 直接管道进 mosdepth，用完即弃，否则会产生数 TB 垃圾。
2. **CRAM 替代 BAM**：服务器上比对结果存 CRAM，体积约为 BAM 的 50%，且可无损还原。
3. **随机种子必须记录**：`samtools view -s <int>.<frac>` 的种子写入 `simulation_manifest.tsv`，否则 10 次重复不可复现。
4. **逐样本并行**：S2–S4 按样本并行（每样本 1–8 线程），S4/S6 按染色体分块可再加速。
5. **幂等**：每个阶段以"产物存在则跳过"为准，断点续跑。

---

## 四、本地侧分析栈

| 分析 | 输入 | 工具 |
| --- | --- | --- |
| 样本质控汇总、深度分布 | QC 表 | pandas + matplotlib |
| SNP 路线：PCA、系统树、pairwise 距离、信息量 | PLINK bed / VCF | scikit-allel、scikit-learn |
| CNV 路线：归一化、阈值、CNV block 合并 | 窗口深度矩阵 | pandas + numpy + HMM（hmmlearn） |
| k-mer 路线：特异性、区分度 | 稀疏 k-mer 矩阵 | scipy.sparse |
| SV/PAV 路线 | SV 矩阵 | pandas |
| 标记筛选与指纹编码 | 四条路线的标记集 | numpy |
| **阈值重算（ROC/AUC/F1）** | 同品种/不同品种相似度分布 | scikit-learn |
| **深度 → 召回 → 准确率曲线** | ulcWGS 各档深度矩阵 | numpy + pandas |
| 图表 / 论文 | 以上全部 | matplotlib + seaborn |

**环境**：本机 WSL2 的 `ricevar` 环境已装齐全部依赖（scikit-allel、scipy、scikit-learn、pandas、pyarrow、matplotlib、seaborn、hmmlearn 待补）。

---

## 五、传输协议

**目录约定**

```
服务器  /scratch/ricevar/            （工作区，含原始数据）
        /scratch/ricevar/export/     （唯一需要传回的目录）
```

**export/ 结构**

```
export/
├── MANIFEST.tsv            每个文件：相对路径、字节数、sha256、生成脚本、日期
├── README.md               本次导出的参数（样本数、参考版本、窗口、k 值、种子表）
├── qc_summary.tsv
├── genotypes/
│   ├── snp_filtered.bed/bim/fam      PLINK2 格式（最紧凑）
│   ├── snp_filtered.vcf.gz           供本地重新过滤
│   └── sv_pav.tsv.gz
├── depth/
│   ├── w10kb.parquet               窗口 × 样本（全深度）
│   ├── w50kb.parquet
│   ├── w100kb.parquet
│   └── w1mb.parquet
├── depth_sim/
│   ├── d0.05_r1_w10kb.parquet      … 7 档 × 10 重复
│   └── simulation_manifest.tsv     深度、重复号、随机种子、样本表
└── kmer/
    ├── k31_matrix.npz               稀疏
    └── kmer_meta.tsv
```

**传输方式**

```bash
# 服务器 → 本机（断点续传、校验）
rsync -avP --partial --checksum \
      user@server:/scratch/ricevar/export/ \
      /mnt/d/RiceVar-ID/data/processed/server_export/
```

**校验**：本机收到后跑一遍 `sha256sum -c MANIFEST.sha256`，确认无损坏。

---

## 六、风险与回退

| 风险 | 影响 | 回退方案 |
| --- | --- | --- |
| 服务器无外网 / 下载极慢 | S0 卡住 | 本机用 sra-tools 下载后上传；或走 ENA FTP / 国内镜像 |
| 服务器无 conda / 无软件 | S1–S6 跑不了 | 用 Singularity/Apptainer 容器镜像；或用 `conda-pack` 打包含环境的 tar 包上传 |
| 无作业调度器 | 长任务易被踢 | 用 tmux + nohup + 断点续跑；每阶段幂等 |
| 存储配额不足（<500 GB） | 存不下 FASTQ+BAM | 严格"下载→比对→删 FASTQ"流水；CRAM；只做 100–150 份 |
| 服务器中途被清理 | 数据丢失 | export/ 每完成一个阶段就同步回本机；原始 FASTQ 保留 accession 清单可重下 |
| 本地 WSL 再次卡死 | 分析中断 | 矩阵阶段依赖很轻，必要时可迁到纯 Windows Python 跑 |

---

## 七、待确认（影响脚本细节）

1. 服务器是否有作业调度器（Slurm/PBS）还是单机 nohup；
2. 服务器能否直连 NCBI SRA / ENA（国内校园网常见受限）；
3. 服务器可用存储配额；
4. 第一阶段打算跑多少份样本。

拿到这四点即可产出**可直接上传运行**的服务端流水线脚本（含调度器提交模板）与导出/校验脚本。
