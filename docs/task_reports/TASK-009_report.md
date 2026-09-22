# TASK-009 报告：搜索 ENA

- 日期：2026-09-16
- 结果：✅ 完成

## 一、任务要求与产出

任务清单要求：搜索 ENA，关键词 `Oryza sativa WGS`、`rice cultivar sequencing`、
`rice variety resequencing`。

**产出**：
- `data/metadata/search/ena_search_summary.tsv`（7 条查询命中数）
- `data/metadata/search/ena_rice_wgs_runs.tsv`（5,000 条，默认排序）
- `data/metadata/search/ena_rice_wgs_deep_runs.tsv`（★ **10,000 条 ≥5×，含 FASTQ 直链**）
- 脚本：`scripts/search_ena.sh`、`search_round2.sh`、`analyze_deep.sh`、`inspect_ena.sh`、`probe_ena_samples.sh`

## 二、检索结果

### 2.1 命中数矩阵

| 查询 | 命中数 |
| --- | ---: |
| `tax_eq(4530)`（任意策略） | 141,538 |
| `+ library_strategy="WGS"` | ★ **96,623** |
| `+ library_source="GENOMIC"` | 96,497 |
| `+ library_layout="PAIRED"` | 95,261 |
| `tax_tree(4527)`（稻属全属）+ WGS | 114,131 |

### 2.2 ★ 按深度过滤（本项目真正关心的）

| 深度门槛 | 命中数 |
| --- | ---: |
| ≥1× | 61,751 |
| **≥5×** | ★ **32,478** |
| **≥10×** | ★ **24,633** |
| ≥20× | 10,707 |

> **结论：数据供给不是瓶颈。** ≥10× 有 24,633 条，远超 TASK-017 要求的 100–1000 份规模。

### 2.3 已拉取清单概况（10,000 条 ≥5×）

| 维度 | 分布 |
| --- | --- |
| 平台 | ILLUMINA 9,758 / DNBSEQ 120 / BGISEQ 72 / PACBIO 38 / ONT 12 |
| 布局 | PAIRED 9,942 / SINGLE 58 |
| 深度 | 5–10× 2,572 · 10–20× 4,055 · 20–30× 1,099 · 30–50× 1,363 · **≥50× 911** |
| **提交库** | SRR 7,373 / ERR 1,372 / **DRR 1,255** |
| FASTQ 直链 | **10,000 / 10,000（100%）** |

## 三、★ 关键发现：品种名字段

### 3.1 问题：`sample_title` 不可直接用作品种名

对 5,000 条记录抽样，大量 `sample_title` 为无信息值：

```
Plant sample from Oryza sativa        ← 无信息占位符
3K RGP mapping to Os.XI-1A Reference  ← 研究项目名，非品种
N1-10-8D / Nx-2-44B / N5-3-42C        ← 育种行编号
1143 / 786 / X173                     ← 纯编号
Oryza sativa                          ← 物种名
```

**若不处理，TASK-012 的 `variety_name` 字段将有大量垃圾值。**

### 3.2 解决方案

**品种名可取到，主力字段是 `cultivar`**（有两个层次）：

| 来源 | 字段 | 实测填写率（21,654 样本） |
| --- | --- | ---: |
| ENA Portal `read_run` | `cultivar` 列 | 51.7% |
| ENA 样本 XML | `<TAG>cultivar</TAG>` | ★ **72.4%** |
| ENA 样本 XML | `<TAG>subspecific genetic lineage name</TAG>` | **0.1%** |
| ENA 样本 XML | `<DESCRIPTION>` 自由文本 | 28.8% |

取数方式（两条路实测均可用）：
```
# 路径 A：Portal API 一次取全量（含 cultivar 列）
result=read_run&fields=...,cultivar,...&format=tsv

# 路径 B：批量样本 XML（200 个/请求、1.7 秒）
https://www.ebi.ac.uk/ena/browser/api/xml/{acc1},{acc2},...
```
**实测性能**：路径 B 拉取 21,654 个样本**仅需 241 秒**（109 批，0 失败）。

### 3.3 ⚠️ 本报告初版的结论有误（已更正）

> **初版写的是**："品种名在 ENA 样本 XML 中，但**字段名不是 `cultivar`**"，
> 并据此把 `subspecific genetic lineage name` 列为第一优先级。
>
> **这是错的。** 2026-09-20 扩大到 **21,654 个样本**统计后：
> - `subspecific genetic lineage name` 仅 **20 个（0.1%）**——是个别提交者的写法；
> - **`cultivar` 标签有 15,688 个（72.4%）**，才是主力字段。
>
> **错误是怎么产生的**：初版只验证了 **1 个样本**（`SAMEA114006088`，ITQB NOVA 提交），
> 该提交者恰好用了 `subspecific genetic lineage name`。
> 我据此推断为通用规律——**单样本不足以支撑字段层面的结论**。
> 更糟的是，初版把这个推断写成了"验证过程：用 `<TAG>cultivar</TAG>` 检索 → 无命中
> （说明该字段不存在）"，而实际上那只是**在这一个样本上**无命中。
>
> **教训**：字段层面的结论必须基于全量或大样本统计；单例观察只能作为线索，
> 必须标注为"待验证"而非"已验证"。

### 3.4 TASK-011 实际采用的提取策略

| 优先级 | 来源 | 说明 |
| --- | --- | --- |
| 1 | `xml:cultivar_tag` | 覆盖率最高（72.4%） |
| 2 | `portal:cultivar` | 与上者有重叠，用于互补 |
| 3 | `xml:lineage_name` | 覆盖率极低，仅作补充 |
| 4 | 自由文本（description / alias / title） | 兜底，一律降级为 `caveat` |

每个候选值须过**五道校验**：亚种名 / 占位符 / 纯编号 / 描述文本 / 词数。
实测通过率：good 23.9% + caveat 0.1% + code 21.6%（详见 TASK-011 报告）。

## 四、⚠️ 发现的偏倚（已修正）

第一轮用 `limit=5000` 按默认排序拉取，结果 **73%（3,672/5,000）为 <1× 数据**——
存在**有序偏倚**（按 accession 顺序，早期多为低深度）。

**修正方式**：第二轮改用 `base_count` 范围过滤（`base_count>=1875000000`）直接取 ≥5× 数据，
得到目标明确的高质量清单。原 5,000 条文件保留作参照，但**标注为存在偏倚**。

## 五、⚠️ 第二次自我纠错：FASTQ 直链可用数

**现象**：报告初稿写"FASTQ 直链 9,996 / 10,000 可用"。
**核验**：`scripts/check_fastq_links.py` 逐行统计 → **`fastq_ftp` 与 `fastq_bytes`
两列均无空值，实为 10,000 / 10,000（100%）**。
**处理**：文档中的 9,996 已全部改正为 10,000，并纳入 `scripts/final_verify.py` 的自动核验项。

**可验证的样例直链**（`ERR10906858`）：
```
ftp.sra.ebi.ac.uk/vol1/fastq/ERR109/058/ERR10906858/ERR10906858_1.fastq.gz
ftp.sra.ebi.ac.uk/vol1/fastq/ERR109/058/ERR10906858/ERR10906858_2.fastq.gz
字节数：2,337,340,837 ; 2,172,357,682
```

## 六、ENA 作为主下载源的选型依据

| 优势 | 证据 |
| --- | --- |
| **一次覆盖 INSDC 全量** | ENA 含 NCBI 与 DDBJ 已同步数据（10,000 条中 SRR 7,373 + DRR 1,255） |
| **API 稳定快速** | 实测响应 < 1 秒（DDBJ 同时为 504） |
| **FASTQ 直链直接在结果里** | `fastq_ftp` + `fastq_bytes` 字段，**10,000/10,000 全部可用** |
| **支持深度范围查询** | `base_count>=...` 直接过滤，避免拉全量 |
| **样本属性可取** | 含结构化品种名字段 |

## 七、自我评估

| 核对项 | 结果 |
| --- | --- |
| 是否覆盖 3 个指定关键词 | ✅（并以精确的 tax_eq + library_strategy 补充） |
| 是否取得可用的 run 级清单 | ✅ 10,000 条，**FASTQ 直链 100% 可用** |
| 是否发现并解决品种名问题 | ✅ 第 3 节，含实测验证 |
| 是否发现并修正抽样偏倚 | ✅ 第四节 |
| 是否自查并改正统计错误 | ✅ 第五节（FASTQ 直链可用数） |
| 是否给出对 TASK-012 的可执行建议 | ✅ 三级提取策略 |

**遗留**：`subspecific genetic lineage name` 的填写率已在 TASK-011 统计完毕（**0.1%**，
远低于 `cultivar` 的 72.4%），该遗留项**已关闭**；正式结论见 §3.3。

> 结论：**TASK-009 合格。** ENA 确立为本项目主下载源。
