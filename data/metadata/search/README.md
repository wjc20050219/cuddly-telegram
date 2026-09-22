# 公开数据检索结果说明

> TASK-008 / TASK-009 / TASK-010 产出 · 2026-09-16
> 方法学与结论见 `docs/methods/data_source_survey.md`

## ⚠️ 引用前必读

本目录中**有一个文件的数据已作废**，引用历史数字时务必核对下表。

| 文件 | 有效性 | 说明 |
| --- | --- | --- |
| `ncbi_search_summary.tsv` | ✅ **有效（现行）** | NCBI 13 条查询的命中数 + **执行证据**（`querytranslation`，第 5 列） |
| `ncbi_count_verification.tsv` | ✅ 有效 | 同一查询连测 3 次的稳定性核验 |
| `ncbi_sra_esummary.json` | ✅ 有效 | 300 条 SRA 实验的原始响应（440 KB，分批抓取后合并） |
| `ncbi_sra_runs.tsv` | ✅ 有效 | 上者的解析结果（300 行 × 18 列） |
| ~~`ncbi_search_summary_round2.tsv`~~ | ❌ **已作废** | **参数传递缺陷产出的数据，请勿引用**（见下） |
| `ena_search_summary.tsv` | ✅ 有效 | ENA 7 条查询的命中数 |
| `ena_rice_wgs_runs.tsv` | ⚠️ 有效但**含抽样偏倚** | 5,000 条，默认排序；**73% 为 <1×**，仅作参照 |
| `ena_rice_wgs_deep_runs.tsv` | ✅ **有效（推荐）** | ★ **10,000 条 ≥5×，含 FASTQ 直链**，本项目主用清单 |

## ❌ 关于 `ncbi_search_summary_round2.tsv` 为何作废

第二轮检索的计数函数签名为 `(db, label, term)`，但函数体误用 `$2`（标签）
而非 `$3`（查询词），**实际检索的是标签字符串**（如 `"OS-plain"`、`"rice-genome"`）。

- **症状**：biosample 库同一查询两轮分别得 66,760 与 1,094；bioproject 的
  "Oryza sativa WGS" 只命中 1 条——明显异常。
- **处理**：该文件保留在此仅为**留存排查过程**，其数字**一律不可引用**；
  修正版为 `ncbi_search_summary.tsv`。
- **正确的数字**（如需要）：BioProject 9,450 · BioSample 218,272 · nuccore 2,300,483。

> 第一轮中 `count_sra`（2 参数版）参数正确，其结果与新结果**完全一致**
> （106,474 / 106,685），**可以采信**。

## 复现方式

```bash
wsl -d Ubuntu -u root

# NCBI
bash /mnt/d/dsh/RiceVar-ID/scripts/search_ncbi.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/fetch_ncbi_esummary.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/verify_ncbi_counts.sh

# ENA
bash /mnt/d/dsh/RiceVar-ID/scripts/search_ena.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/search_round2.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/analyze_deep.sh

# DDBJ（用于验证其 API 故障状态）
bash /mnt/d/dsh/RiceVar-ID/scripts/probe_ddbj2.sh
```

## 关键数字速查

| 指标 | 数值 |
| --- | ---: |
| ENA 水稻 WGS 记录 | 96,623 |
| NCBI SRA 水稻 WGS 实验 | 106,474 |
| NCBI BioProject | 9,450 |
| NCBI BioSample | 218,272 |

> **关于深度分档数字（≥5× / ≥10× / ≥20×）**：曾记录的 32,478 / 24,633 / 10,707
> **目前无法从仓库中复核**。它们来自 `search_round2.sh` 运行时打印到控制台的
> `limit=0` 计数查询，**未存档为任何机读文件**；表中现有清单文件是**分页拉取**的产物，
> 行数恰等于脚本中的 `limit=`（`ena_rice_wgs_runs.tsv` = 5,000，
> `ena_rice_wgs_deep_runs.tsv` = 10,000），属**截断**而非全量。
>
> 因此：
> - **不要**引用上述三个深度分档数字，除非重新运行计数查询并存档；
> - 需要深度分档时，应重新执行 `scripts/search_round2.sh` 并把计数写入
>   `ena_search_summary.tsv` 一并保存；
> - 各产物的来源与完整性状态见 `search_provenance.json`
>   （由 `scripts/record_search_provenance.py` 生成，`--check` 可校验）。
>
> 这一区分**不影响已冻结的两个面板**：面板样本取自
> `data/metadata/candidates/candidate_samples.tsv`（远大于被截断的清单），
> 且每个面板都有样本不在该清单中，见 `tests/test_search_provenance.py`。

## 品种名提取（TASK-012 关键）

**字段名不是 `cultivar`**，而是 ENA 样本 XML 中的：

```xml
<TAG>subspecific genetic lineage name</TAG><VALUE>Caravela</VALUE>
```

取数：`https://www.ebi.ac.uk/ena/browser/api/xml/{sample_accession}`

三级优先策略见 `docs/methods/data_source_survey.md` 第 2.4 节。
