# 本科版参考基因组选择与偏倚评估方案

> 对应现行规范 C：TASK-014（参考基因组下载）及其前置调查。  
> 当前状态：选择与下载方案已确定；学校服务器尚未执行下载，因此不把本文件写成“服务器下载已完成”。

## 1. 主参考选择

主流程固定使用 **Oryza sativa Japonica Group cv. Nipponbare, IRGSP-1.0**。

| 项目 | 记录 |
| --- | --- |
| Assembly | IRGSP-1.0 |
| NCBI RefSeq accession | `GCF_001433935.1` |
| ENA/INSDC assembly | `GCA_001433935` |
| Ensembl Plants FASTA | `Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz` |
| 主下载地址 | `https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-60/fasta/oryza_sativa/dna/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz` |
| 服务器存放位置 | `$RV_ROOT/reference/` |
| 完整性 | 下载后执行 `gzip -t`、来源 checksum 核对、另记本地 SHA256 |

选择理由：IRGSP-1.0 是 Nipponbare 主流参考，现有脚本和历史基准均使用该版本；单参考方案更符合本科工作量，也便于统一坐标、bcftools calling 与 marker 导出。官方/权威入口包括 [NCBI IRGSP-1.0 assembly 文件目录](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/001/433/935/GCF_001433935.1_IRGSP-1.0/)、[ENA assembly 记录](https://www.ebi.ac.uk/ena/browser/view/GCA_001433935) 和 [Ensembl Plants FASTA 目录](https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-60/fasta/oryza_sativa/dna/)。

## 2. 版本冻结规则

1. 论文主分析不得混用 Ensembl、NCBI 或 RAP-DB 的不同 FASTA 坐标/序列命名；
2. 服务器首次下载后生成 `reference_record.tsv`，至少记录 URL、下载日期、压缩文件字节数、来源 checksum、SHA256、解压 FASTA SHA256、序列数与总长度；
3. 后续若上游 release 目录内容变化，仍以首次冻结的 SHA256 为准；
4. VCF、BED、marker 数据库必须记录 reference accession 与 FASTA SHA256；
5. 参考文件和索引不提交 Git，只提交记录文件。

## 3. 本科范围内的 reference bias 处理

本科版不做泛基因组重比对，也不声称消除了参考偏倚。采用“检测、分层报告、限制解释”的最低充分方案：

- 按提交元数据中的 indica / japonica / aus / unknown 分层汇总 mapping rate、properly paired、有效深度与缺失率；
- 检查 indica 与 japonica 的 mapping rate、SNP missingness 是否存在系统差异；
- marker 过滤时剔除跨亚种缺失严重或深度依赖明显的位点；
- PCA 与相似度结果按亚种着色，判断识别是否主要由籼粳分化驱动；
- 若某亚种明显低 mapping/高 missing，只报告限制，不把它解释成品种特异信号；
- 论文讨论中明确：单一 japonica 参考可能对 indica/aus 产生 reference bias，泛基因组是后续工作，不是本论文已完成内容。

### 预先定义的诊断表

数据到位后生成 `results/statistics/reference_bias_qc.tsv`，建议字段：

```text
sample_id  subspecies  mapping_rate  properly_paired_rate
mean_depth  breadth_1x  snp_call_rate  heterozygosity
```

这里只预定义输出，不预设显著性或方向。阈值应结合 Pilot 实际分布确定，并记录排除理由。

## 4. 下载后验收

```bash
# 学校服务器
cd ~/ricevar/server
bash 03_align.sh <smoke_sample_id>   # prep_reference 会下载并建索引

gzip -t "$RV_ROOT/reference/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz"
sha256sum "$RV_ROOT/reference/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz"
sha256sum "$RV_ROOT/reference/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa"
samtools faidx "$RV_ROOT/reference/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa"
```

必须把**完整** SHA256 写入记录，不能只保存前 16 位。

`server/03_align.sh` 的 `prep_reference` 现已写入完整摘要（9 列：
`reference_name / url / download_recorded_at / gzip_bytes / gzip_sha256 /
fasta_file / fasta_sha256 / sequence_count / total_bp`），
使用 `sha256sum "$f" | awk '{print $1}'` 取全部 64 位十六进制，
**不截断**。该不变量由 `verify_undergraduate_scope.py` 机械检查：
若脚本回退成 `cut -c1-16`、`head -c16` 等截断写法，检查会失败。
**仍未在真实服务器产出过 `reference_record.tsv`**，因此该记录本身尚无真实值。

## 5. 当前证据边界

- 已确认公开目录中存在目标 IRGSP-1.0 FASTA 与 NCBI assembly 文件；
- 历史状态文档报告本机 WSL 曾下载并统计为 375,049,285 bp；
- 本轮 WSL 服务访问返回 `E_ACCESSDENIED`，故未重新读取本机缓存、未重新计算 SHA256；
- 学校服务器尚未运行 probe，也尚未下载 reference/FASTQ。以上均不得写成已经完成的服务器实验。
