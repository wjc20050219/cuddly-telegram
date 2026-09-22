# 附录 B　软件版本与运行参数

> 本附录的版本号来自仓库内的实测记录 `software_versions.txt`
> （检测日期 2026-09-15，2026-09-16 复核），**不是转抄自文档或凭印象填写**。
> 运行参数从 `server/config.sh`、`server/03_align.sh`、`server/04_joint_snp.sh`
> 的实际代码中提取。

## B.1 计算环境

| 项目 | 配置 |
| --- | --- |
| 宿主系统 | Windows 11 23H2 (10.0.22631 x64) |
| 运行环境 | WSL2（内核 6.18.33.2-microsoft-standard-WSL2） |
| 发行版 | Ubuntu 26.04.1 LTS |
| 环境管理器 | Miniconda3（`/opt/miniconda3`，conda 26.7.1，内置 libmamba 求解器） |
| 项目环境名 | conda env `ricevar` |
| 通道镜像 | TUNA（conda-forge / bioconda / PyPI），`channel_priority: strict` |

环境版本记录文件：`software_versions.txt`；
环境定义文件：`environment.yml`（v2）与 `requirements.txt`。

> ⚠️ **环境部署位置说明**：上述版本清单是在**本机 WSL2** 的 conda 环境中实测得到的，
> 用于确认流程可解、依赖完整。**学校服务器上的最终运行环境可能不同**
> （取决于管理员提供的调度器、镜像源与已有模块）。因此本文报告实验时，
> 应同时记录**实际运行主机**上的版本，命令见 B.5。

## B.2 测序数据处理工具

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| FastQC | v0.12.1 | 原始 reads 质量报告 |
| fastp | 1.3.7 | 接头与低质量碱基过滤 |
| bwa-mem2 | 2.3 | 比对到参考基因组 |
| minimap2 | 2.31-r1302 | 长读/备用比对（论文主线未使用） |
| samtools | 1.24 | 排序、flagstat/stats、CRAM 转换与索引 |
| bcftools | 1.24 | mpileup / call / norm / view / index |
| bedtools | v2.31.1 | 区间运算 |
| mosdepth | 0.3.14 | 深度统计（降采样验证与窗口深度） |
| seqkit | 2.13.0 | FASTA/FASTQ 统计与格式转换 |
| sra-tools (fasterq-dump) | 3.4.1 | SRA 数据获取 |
| entrez-direct | 26.0 | 元数据检索 |

## B.3 k-mer 工具与工作流（可选项）

| 工具 | 版本 | 备注 |
| --- | --- | --- |
| KMC | 3.2.4 (2024-02-09) | k-mer 计数 |
| jellyfish（k-mer CLI） | 2.3.1 | 包名为 `kmer-jellyfish`（bioconda） |
| Snakemake | 9.24.0 | 工作流编排 |
| snakemake-executor-plugin-cluster-generic | 1.0.9 | 集群提交插件 |

> **包名踩坑记录**：conda-forge 的 `jellyfish` 只是 Python 绑定库，
> **不含** `jellyfish` 可执行文件；k-mer CLI 需安装 `kmer-jellyfish`。
> 首版 `environment.yml` 只写了 `jellyfish`，会导致**照 yml 重建环境拿不到 CLI**，
> 已修复为两者同时声明。详见 `software_versions.txt` 第三节问题 5。

## B.4 基础环境与 Python 依赖

| 组件 | 版本 | 组件 | 版本 |
| --- | --- | --- | --- |
| Python | 3.11.16 | numpy | 2.4.6 |
| pip | 26.2.1 | pandas | 3.0.5 |
| R / Rscript | 4.3.3 | scipy | 1.17.1 |
| git | 2.55.0 | pyarrow | 25.0.1 |
| pysam | 0.24.1 | matplotlib | 3.11.2 |
| biopython | 1.88 | seaborn | 0.13.2 |
| scikit-allel | 1.3.13 | adjustText | 1.4.0 |
| scikit-learn | 1.9.1 | pytest | 9.1.1 |
| hmmlearn | 0.3.3 | joblib | 1.6.0 |

> 完整清单可用 `conda list -n ricevar` 与 `pip list` 复核。
> 本项目论文主线（SNP 路线）只依赖上表前两列中的通用工具；
> hmmlearn 属 CNV 可选分析依赖，论文主线**不使用**。

## B.5 运行参数

### B.5.1 资源与工作区（`server/config.sh`）

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `THREADS` | 8 | 单样本线程数；**不使用整节点 `nproc`**，避免越过共享节点调度配额 |
| `PAR` | 2 | 并行样本数 |
| `SORT_MEM` | 1G | `samtools sort -m` |
| `RV_ROOT` | `$HOME/ricevar` | 工作区根目录（可用环境变量覆盖） |
| `RV_SAMPLES` | `$RV_META/pilot_manifest.tsv` | 样本清单（可覆盖为预检清单） |

> 资源默认值刻意保守：本文全部参数以"能在共享服务器上跑完"为目标，
> 而非追求单机极限速度。实际运行时如节点资源更充裕，可在不改流程的前提下调高。

### B.5.2 参考基因组

| 项目 | 值 |
| --- | --- |
| 参考 | IRGSP-1.0（日本晴 / Nipponbare） |
| RefSeq 组装号 | `GCF_001433935.1` |
| INSDC/ENA 组装号 | `GCA_001433935` |
| 序列数 | 参考 FASTA 的 `sequence_count`（由 `03_align.sh` 写入 `reference_record.tsv`） |
| 基因组大小（估算用） | 374,495,335 bp |
| 下载地址 | `https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-60/fasta/oryza_sativa/dna/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz` |

参考基因组的完整性由 `server/03_align.sh` 写入的 `reference_record.tsv` 记录，
共 9 列：`reference_name / url / download_recorded_at / gzip_bytes / gzip_sha256 /
fasta_file / fasta_sha256 / sequence_count / total_bp`。
其中 `gzip_sha256` 与 `fasta_sha256` 均为**完整 64 位十六进制摘要**，
不截断；该不变量由 `scripts/verify_undergraduate_scope.py` 机械校验。

> 该记录文件在**真实下载发生后**才会产生。截至本文写作时**尚未生成**，
> 因此本文**不声明**任何校验和数值。

### B.5.3 比对与 calling 参数

| 步骤 | 命令要点 | 参数值 |
| --- | --- | --- |
| 去接头/质控 | `fastp` | **默认参数**（见下方说明） |
| 比对 | `bwa-mem2 mem -t $THREADS -R <RG>` | 读组含样本号 |
| 排序 | `samtools sort -@ $((THREADS/2)) -m $SORT_MEM` | |
| 统计 | `samtools flagstat` / `samtools stats` | |
| 存储 | `samtools view -C -T $REF`（BAM→CRAM）+ `samtools index` | |
| 联合 calling | `bcftools mpileup -f $REF -q 20 -Q 20 -a FORMAT/AD,FORMAT/DP` | `MAPQ=20`，`BASEQ=20` |
| 变异调用 | `bcftools call -mv -f GQ` | 多等位简并模式 |
| 规范化 | `bcftools norm -f $REF -m -any` | 拆分多等位 |
| SNP 筛选 | `bcftools view -m2 -M2 -v snps` | 只保留**二等位 SNP** |

> **关于 fastp**：流程使用 fastp **默认参数**，未额外指定质量阈值、
> 长度过滤或接头序列。这是一个有意的保守选择——默认参数覆盖面广、
> 不需要针对特定建库方式调参，便于复现。其代价是可能不如针对性调参精细。
> 相关 QC 指标（Q30、过滤比例等）由 fastp 的 JSON 报告输出，
> 将作为 3.1 节的**实测结果**呈现，本文不预先假设其数值。

> **关于 QC 阈值**：`04_joint_snp.sh` 的注释明确指出
> "其余 QC 在 Pilot 分布审查后执行"——即 MAF、缺失率、深度等位点级过滤
> **将在看到 Pilot 真实分布之后**再确定，而不是预先拍定阈值。
> 这是为了避免用臆测的阈值筛掉真实信号。相应阈值将在 2.4 节与 3.2 节
> 按实际结果补充。

### B.5.4 降采样与评估

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `RV_DEPTHS` | 0.02 0.05 0.10 0.20 0.50 1.00 | 六个目标深度梯度 |
| `RV_REPS` | 3 | 每梯度重复次数（正式论文建议 ≥3，优先 5） |
| `RV_WINDOWS` | 10000 50000 100000 1000000 | mosdepth 窗口大小 |
| 相似度方法 | IBS（主）、Hamming、Jaccard | 见 2.6 节 |
| marker 档位 | 500 / 1000 / 2000（嵌套） | 由 Pilot 冻结 |

> 降采样以固定随机种子执行，种子值记录于运行清单，保证可复现。
> **实测深度**由 `mosdepth` 在降采样 BAM 上测量，用于验证目标深度是否达成；
> 该数值属实验结果，在 3.3 节呈现。

## B.6 本地开发与验证环境（非实验环境）

论文写作与代码验证所用的本机环境，**不用于产生实验数据**：

| 项目 | 版本 | 说明 |
| --- | --- | --- |
| 系统 Python | 3.7.3 | 仅用于运行单元测试与静态检查 |
| SQLite | 3.21.0 | 随 Python 3.7 提供；**不支持 `ON CONFLICT ... DO UPDATE`**，故数据库层统一使用 `INSERT OR REPLACE` |

> 本机**没有** bash、matplotlib 与 streamlit，
> 因此 shell 脚本的语法、出图代码与 Web 原型**未在本机实际运行**。
> 相关验证为静态检查（AST 解析、命令可达性检查），
> 不等同于执行验证——这一点在 4.3 节局限性中亦有说明。

## B.7 版本记录规则

`software_versions.txt` 顶部写明规则：**每次安装或升级任何软件后，
更新该文件的对应条目与日期**。本附录 B.2–B.4 的数值即该文件的实测结果。

若学校服务器上的版本与本附录不同，应**以服务器实测为准**并更新本附录，
不得沿用本机版本冒充服务器版本。
