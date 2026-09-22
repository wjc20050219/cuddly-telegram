# TASK-011 报告：候选样本整理

> **编号说明**：本报告采用**任务书 B 编号**（TASK-001~080）。
> 对应原 `TASK_LIST.md` 的 TASK-012（建立候选样本表）。见 `docs/TASK_NUMBERING.md`。

- 日期：2026-09-20
- 结果：✅ 完成
- 产出：`data/metadata/candidates/candidate_samples.tsv`（**32,564 行 × 34 列**）

---

## 一、任务要求与产出

任务书第九节要求建立 `metadata/candidate_samples.tsv`，至少含 22 个字段。
本任务产出 **34 列**（22 个规定字段 + 12 个可追溯附加字段）。

## 二、取数过程

### 2.1 数据源与查询

**主源：ENA Portal API**（一次请求取全量）

```
result  = read_run
query   = tax_eq(4530) AND library_strategy="WGS" AND base_count>=1875000000
fields  = run/experiment/sample/study accession, study_title, sample_title,
          sample_alias, scientific_name, cultivar, ecotype, strain, isolate,
          country, collection_date, center_name, first_public,
          instrument_platform/model, library_*, read_count, base_count,
          fastq_ftp/bytes/md5
limit   = 0（全量）
```

**结果**：**32,564 条 run**，29 列，18.3 MB，**耗时 8.5 秒**。

> **为什么取 ≥5×**：本项目要从较高深度数据降采样模拟 ulcWGS，
> 深度不足的材料无法当参考。≥5× 有 32,564 条，留出筛选余量。

### 2.2 品种名补齐（关键难点）

Portal 的 `cultivar` 列只覆盖 **51.7%**，故用批量样本 XML 补齐。

**批量 XML 实测**（`scripts/probe_sample_batch.sh`）：

| 每请求样本数 | HTTP | 返回样本数 | 耗时 |
| ---: | --- | ---: | ---: |
| 1 | 200 | 1 | 0.84 s |
| 3 | 200 | 3 | 0.90 s |
| 50 | 200 | 50 | 1.39 s |
| **200** | **200** | **200** | **1.71 s** |

→ **21,654 个唯一样本，109 批 × 200，实测 241 秒，0 失败批次。**

> 意外收获：ENA 对 **NCBI（`SAMN`）与 DDBJ（`SAMD`）** 的 BioSample 同样提供 XML，
> 不限于 ENA 自有样本。

### 2.3 样本来源构成

| 提交库 | 样本数 | 占比 |
| --- | ---: | ---: |
| `SAMN`（NCBI） | 12,386 | 57.2% |
| `SAMD`（DDBJ） | 5,630 | 26.0% |
| `SAME`（ENA） | 3,638 | 16.8% |

---

## 三、★ 品种名提取：从 72.4% 的原始字段到 45.5% 的可用值

### 3.1 字段命中率（21,654 样本实测）

| 来源 | 字段 | 命中率 |
| --- | --- | ---: |
| ENA 样本 XML | `<TAG>cultivar</TAG>` | ★ **72.4%** |
| ENA Portal | `cultivar` 列 | 51.7% |
| ENA 样本 XML | `<DESCRIPTION>` | 28.8% |
| ENA 样本 XML | `<TAG>subspecific genetic lineage name</TAG>` | **0.1%** |
| ENA 样本 XML | `<TAG>ecotype</TAG>` | 16.7% |

### 3.2 ⚠️ 我上一轮的一个错误结论（已更正）

> **上一轮（TASK-009）我写的是**："品种名**不在** `cultivar` 字段，
> 而在 `subspecific genetic lineage name`"。
>
> **这是错的。** 那个结论基于**单个样本**（`SAMEA114006088`，ITQB NOVA 提交），
> 该提交者恰好使用这一写法。扩大到 21,654 个样本后：
> `subspecific genetic lineage name` 只有 **20 个（0.1%）**，
> 而 **`cultivar` 标签有 15,688 个（72.4%）**。
>
> **已更正** `docs/methods/data_source_survey.md` §2.4 与 `TASK-009_report.md` §3.3。
> **教训**：字段层面的结论必须基于大样本统计，单例只能作为线索。

### 3.3 ★ 字段有值 ≠ 值是品种名

这是本任务最耗时的一步。实测高频伪值：

| 原始值 | 次数 | 性质 |
| --- | ---: | --- |
| `not applicable` | **9,904** | INSDC 官方缺失值词表 |
| `zh11` | 5,349 | ★ **不是伪值**——"中花 11"的真实缩写 |
| `cultivar` | 575 | 字段名本身 |
| `rice` | 297 | 物种名 |
| `allotetraploid derived from nipponbare and 93-11` | 202 | 实验描述 |
| `rils from the cross between shennong265 and r99` | 153 | 群体描述 |
| `missing` / `n/a` / `not collected` | 218 | 缺失值 |
| `78a03 x rb05` | 60 | 杂交组合 |
| `oryza sativa japonica cv nipponbare` | 44 | 学名串（含品种名，可提取） |
| `indica/japonica` | 14 | 亚种 |

**五道校验**（`is_subpop` / `looks_placeholder` / `looks_code` /
`looks_description` / `looks_too_long`）后：

| 分级 | run 数 | 占比 | 含义 |
| --- | ---: | ---: | --- |
| **good** | 7,773 | 23.9% | 干净的字母品种名 |
| **caveat** | 32 | 0.1% | 杂交组合 / 派生长名 / 来自自由文本 |
| **code** | 7,025 | 21.6% | ★ 短字母数字编号，待 TASK-012 解析 |
| **unusable** | 17,734 | 54.5% | 占位符 / 缺失值 / 描述文本 |

**可用合计：14,830 条 run（45.5%）**

### 3.4 ★ 一个差点犯下的错误：不要丢弃 `code` 类

`code` 类（`^[a-z]{1,2}\d+$` 等）最初被我**判为无效而丢弃**，直到诊断脚本发现：
**被丢弃的 7,026 条里有 5,349 条是 `zh11`**——那是**中花 11**，真实且常用的水稻品种。

`ir64`、`dn416`、`9311`、`y58s` 都是这种形态。
**正确做法是保留并降级，交由 TASK-012 解析**，而不是丢弃。

### 3.5 被拒原因诊断（`task011_name_diagnostics.py`）

| 原因 | run 数 | 占比 |
| --- | ---: | ---: |
| INSDC 缺失值词表 | 10,122 | 31.1% |
| 纯编号/代码（已改为保留） | 7,026 | 21.6% |
| 三个结构化字段全为空 | 5,571 | 17.1% |
| 占位/无信息值 | 1,116 | 3.4% |
| 实验/群体描述 | 919 | 2.8% |
| 亚种名 | 55 | 0.2% |
| 词数过多 | 3 | 0.0% |

> **不可改善的部分**：结构化字段全空（17.1%）+ 提交者明确填了缺失值（31.1%）
> = **48.2%**。这是数据本身的限制，**不是校验过严**。

---

## 四、产出文件

| 文件 | 内容 |
| --- | --- |
| `candidate_samples.tsv` | **32,564 行 × 34 列**主表 |
| `ena_candidates_raw.tsv` | ENA 原始响应（29 列，未加工） |
| `sample_attrs.tsv` | 21,654 个样本的 XML 属性 |
| `name_quality_report.txt` | 品种名质量报告 |
| `xml_cache/` | 109 个 XML 批次缓存（支持断点续跑） |

**主表字段**（34 列）：
22 个规定字段（sample_id / variety_name / variety_alias / species / subspecies /
accession / BioProject / BioSample / SRA_accession / ENA_accession / publication /
country / population / cultivar_or_landrace / sequencing_platform / read_length /
paired_or_single / estimated_depth / reference_genome / data_source /
download_status / qc_status）
\+ 12 个可追溯字段（name_source / name_quality / source_db / instrument_model /
base_count / fastq_ftp / fastq_bytes / sample_title / **study_title** /
sample_alias / center_name / first_public）

> `publication` 字段已在原编号 TASK-A011 补做后回填 **11,040/32,564 行（33.9%）**。
> 但 ENA/Europe PMC 未提供可靠的结构化 accession→publication 链接；
> 主表中的值带 `[MATCH]` / `[PLAUSIBLE]` / `[PARTIAL]` / `[WEAK]` / `[?]` 证据前缀，
> 正式引用前仍需人工核验。详见 `TASK-A011_literature_report.md`。

---

## 五、自我评估

| 核对项 | 结果 |
| --- | --- |
| 是否覆盖 22 个规定字段 | ✅ 含全部 + 12 个附加 |
| 数据是否真实可追溯 | ✅ 每条含 accession + FASTQ 直链 + BioProject |
| 是否编造任何数据 | ❌ 无。无值即留空并标 `unusable` |
| 品种名提取是否有多来源交叉 | ✅ 4 个来源 + 5 道校验 |
| 是否记录质量分级与来源 | ✅ `name_quality` + `name_source` |
| 是否自查并更正上一轮错误结论 | ✅ §3.2 |
| 是否避免了"丢弃真实品种缩写" | ✅ §3.4 |

**遗留**：
1. `publication` 字段待补（依赖原编号 TASK-011 的文献检索）；
2. `subspecies` 字段填写率低（仅约 10%），其余样本的亚种需后续由群体结构分析判定，
   **不得凭品种名臆测**；
3. 品种名标准化（`code` 类解析）由 TASK-012 完成。

> **结论：TASK-011 合格。**
