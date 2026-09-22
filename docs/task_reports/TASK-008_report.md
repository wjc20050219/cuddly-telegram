# TASK-008 报告：搜索 NCBI SRA

- 日期：2026-09-16
- 结果：✅ 完成

## 一、任务要求与产出

任务清单要求：自主搜索 **NCBI SRA / BioProject / BioSample / GenBank** 四个库，
关键词为 `Oryza sativa WGS`、`rice whole genome sequencing`、`rice variety WGS`、
`rice cultivar WGS`、`rice genome resequencing`。

**产出**：
- `data/metadata/search/ncbi_search_summary.tsv`（13 条查询 + 查询翻译）
- `data/metadata/search/ncbi_count_verification.tsv`（稳定性核验）
- `data/metadata/search/ncbi_sra_esummary.json`（300 条原始响应，440 KB）
- `data/metadata/search/ncbi_sra_runs.tsv`（解析后 run 级表，300 行 × 18 列）
- 脚本：`scripts/search_ncbi.sh`、`fetch_ncbi_esummary.sh`、`verify_ncbi_counts.sh`、`parse_ncbi_esummary.py`

## 二、检索结果

### 2.1 任务清单的 5 个关键词（SRA 自由文本）

| 关键词 | 命中数 |
| --- | ---: |
| Oryza sativa WGS | 114,838 |
| rice whole genome sequencing | 41,465 |
| rice variety WGS | 26,469 |
| rice cultivar WGS | 44,168 |
| rice genome resequencing | 32,753 |

⚠️ **这些数字不可直接用作样本数**：NCBI 把 `WGS` 等词降级为 `All Fields`
（见 `querytranslation` 证据），会命中摘要等任意字段。仅用于说明数据量规模。

### 2.2 精确检索（可信基线）

| 库 | 查询 | 命中数 |
| --- | --- | ---: |
| SRA | `"Oryza sativa"[Organism]` | 193,516 |
| SRA | `+ AND WGS[Strategy]` | ★ **106,474** |
| BioProject | `"Oryza sativa"[Organism]` | **9,450** |
| BioSample | `"Oryza sativa"[Organism]` | **218,272** |
| GenBank (nuccore) | `"Oryza sativa"[Organism]` | 2,300,483 |
| GenBank (nuccore) | `+ refseq[prop]` | 55,746 |

### 2.3 run 级清单（前 300 条）

全部为 WGS/GENOMIC；PAIRED 294 / SINGLE 6；
ILLUMINA 213 / DNBSEQ 81 / OXFORD_NANOPORE 6；
深度 5–10× 13、10–20× 137、20–30× 42、**≥30× 108**。

## 三、★ 两项关键发现

### 3.1 前 300 条命中中 97.3% 是 DDBJ 提交的数据

| 提交库 | 记录数 |
| --- | ---: |
| **DRR（DDBJ DRA）** | **292** |
| SRR（NCBI SRA） | 8 |

完整 DDBJ 编号体系可从中提取：`DRA026964`（Submitter）· `DRX948749`（Experiment）·
`DRP016783`（Study）· `DRS635056`（Sample）· `DRR971114`（Run）·
`PRJDB38331`（BioProject）· `SAMD01760641`（BioSample）。

**这直接决定了 TASK-010 的处境**：DDBJ 自建 API 虽全部 504，
但**其数据经 NCBI / ENA 完全可达**。

### 3.2 E-utilities 的字段限定符会被静默降级

NCBI 对无法识别的字段限定符**不报错，而是降级为 `All Fields`**，
导致"以为在精确检索，实际在全文检索"。因此本任务为**每条查询都抓取了
`querytranslation`** 作为执行证据，存入结果表第 5 列。

## 四、⚠️ 自我纠错记录（重要）

第一轮检索结果中，biosample 库的同一查询两轮分别得 **66,760** 与 **1,094**，
bioproject 的 "Oryza sativa WGS" 只命中 **1** 条——明显异常，故启动核验。

- **根因**：计数函数签名为 `(db, label, term)`，但函数体误用 `$2`（标签）而非 `$3`（查询词），
  **实际检索的是标签字符串**（如 `"OS-organism"`、`"rice-plain"`）。
- **影响**：所有 `count_db`（3 参数版）结果作废并已重跑；
  `count_sra`（2 参数版）参数正确，其结果与新结果完全一致（106,474 / 106,685），可采信。
- **结论**：**v1 的数字已全部作废，本文档只报告 v2 修正后的结果。**
- **副产物**：重跑时发现，由于 NCBI 把连字符当空格分词，
  原先"作废"的 `rice-variety-WGS`(26,469) 与正确的 `rice variety WGS`(26,469) **恰好相等**——
  反向印证了修正后结果可信。

**方法学教训**：涉及检索计数的工作**必须记录查询的规范化形式**，
否则无法发现"搜的不是你以为的东西"。相关脚本已按此规范改造。

## 五、自我评估

| 核对项 | 结果 |
| --- | --- |
| 是否覆盖 4 个库（SRA/BioProject/BioSample/GenBank） | ✅ |
| 是否覆盖 5 个指定关键词 | ✅ |
| 是否取得 run 级实际清单（非仅计数） | ✅ 300 条，含 accession 与深度 |
| 命中数是否可复现 | ✅ 同一查询连测 3 次结果一致 |
| 是否附执行证据 | ✅ querytranslation 逐条可查 |
| 是否诚实记录自查发现的缺陷 | ✅ 第四节 |

**遗留**：esummary 仅取前 300 条（按相关度），非全量抽样；
全量 run 级清单以 ENA 为准（见 TASK-009）。

> 结论：**TASK-008 合格。**
