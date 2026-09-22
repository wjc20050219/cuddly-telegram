# 公开数据源调研（NCBI / ENA / DDBJ）

> **TASK-008 / TASK-009 / TASK-010 输出** · 建立日期：2026-09-16
> 项目：RiceVar-ID（基于 ulcWGS 的水稻品种数字身份证系统）
> 检索脚本：`scripts/search_ncbi.sh`、`scripts/search_ena.sh`、`scripts/probe_ddbj*.sh`
> 原始证据：`data/metadata/search/`

---

## 0. 摘要（一页结论）

| 结论 | 内容 |
| --- | --- |
| **数据量充足** | INSDC 三个成员库合计有 **~10 万条**水稻 WGS 记录；深度 ≥5× 的仍有 **3.2 万条** |
| **主下载源选 ENA** | ENA 一次可查 INSDC 全量（含 NCBI 与 DDBJ 已同步数据），且 FASTQ 直链可用 |
| **DDBJ 自建 API 不可用** | DDBJ Search API **全部端点 504**（含 service-info），但**其数据仍可经 ENA / NCBI 检索到** |
| ★ **品种名字段的关键发现** | 主力字段是 **`cultivar`**（样本 XML 标签 72.4% / Portal 列 51.7%）；`subspecific genetic lineage name` 仅 0.1%（**初版结论有误，已更正，见 §2.4**） |
| ⚠️ **sample_title 不可直接用作品种名** | 大量为 `Plant sample from Oryza sativa`、育种行编号、`3K RGP mapping to ...` 等无信息值 |
| ★ **DDBJ 数据占比极高** | NCBI SRA 按相关度排序的前 300 条水稻 WGS 命中中，**292 条（97.3%）是 DDBJ 提交** |

---

## 1. TASK-008：NCBI 检索

### 1.1 检索矩阵（全部附执行证据）

> **方法学说明**：NCBI E-utilities 会把无法识别的字段限定符**静默降级为 All Fields**。
> 因此下表每条都记录了 NCBI 返回的 `querytranslation`——即"**实际执行的是什么查询**"，
> 而非"我以为执行的是什么查询"。完整数据见 `data/metadata/search/ncbi_search_summary.tsv`。

**A. 任务清单指定的 5 个关键词（对 SRA 做自由文本检索）**

| 关键词 | 命中数 | 实际执行（NCBI 翻译结果） |
| --- | ---: | --- |
| Oryza sativa WGS | **114,838** | `("Oryza sativa"[Organism] OR Oryza sativa[All Fields]) AND WGS[All Fields]` |
| rice whole genome sequencing | **41,465** | `("Oryza sativa"[Organism] OR rice[All Fields]) AND whole… AND genome… AND sequencing…` |
| rice variety WGS | **26,469** | `("Oryza sativa"[Organism] OR rice[All Fields]) AND variety… AND WGS…` |
| rice cultivar WGS | **44,168** | `("Oryza sativa"[Organism] OR rice[All Fields]) AND cultivar… AND WGS…` |
| rice genome resequencing | **32,753** | `("Oryza sativa"[Organism] OR rice…]) AND genome… AND resequencing…` |

> ⚠️ **自由文本检索的命中数偏高且不可比**：因为 `WGS` 等词被降级为 All Fields，
> 会命中摘要、注释等任意字段。**这些数字只用于说明"该领域数据量巨大"，不能当作样本数**。

**B. 精确检索（可信基线）**

| 库 | 查询 | 命中数 |
| --- | --- | ---: |
| **SRA**（实验） | `"Oryza sativa"[Organism]` | 193,516 |
| **SRA**（实验） | `+ AND WGS[Strategy]` | ★ **106,474** |
| SRA（实验） | `+ AND paired[Layout]` | 104,577 |
| SRA（实验） | `+ AND ILLUMINA[Platform]` | 103,166 |
| **BioProject** | `"Oryza sativa"[Organism]` | **9,450** |
| **BioSample** | `"Oryza sativa"[Organism]` | **218,272** |
| **nuccore（GenBank）** | `"Oryza sativa"[Organism]` | 2,300,483 |
| nuccore（GenBank） | `+ AND srcdb_refseq[prop]` | 55,746 |

### 1.2 run 级清单（主查询前 300 条）

查询：`"Oryza sativa"[Organism] AND WGS[Strategy]`，按相关度排序，取前 300 条。
见 `data/metadata/search/ncbi_sra_runs.tsv`。

| 维度 | 分布 |
| --- | --- |
| **文库策略** | WGS 300（100%） |
| **文库来源** | GENOMIC 300（100%） |
| **文库布局** | PAIRED 294 / SINGLE 6 |
| **测序平台** | ILLUMINA 213 / DNBSEQ 81 / OXFORD_NANOPORE 6 |
| **深度** | 5–10× 13 · 10–20× 137 · 20–30× 42 · **≥30× 108** |
| ★ **提交库** | **DRR (DDBJ) 292** · SRR (NCBI) 8 |

> ★ **最重要的发现**：按相关度排序的前 300 条命中中，**97.3% 是 DDBJ 提交的数据**
> （accession 为 `DRR`/`DRX`/`DRP`，BioProject 为 `PRJDB*`，BioSample 为 `SAMD*`）。
> 样例标题形如 `B1674 (CRX842160)`、`A1065 (CRX839258)`——来自一个中国水稻育种数据库
> （Study 名为 `rice ZH11 ems4611 database (PRJCA020505)`）。
>
> **这直接改变了 TASK-010 的处境**：DDBJ 自己的 API 虽然挂了，但**其数据完全可达**。

---

## 2. TASK-009：ENA 检索

### 2.1 命中数矩阵

| 查询 | 命中数 |
| --- | ---: |
| `tax_eq(4530)`（任意策略） | 141,538 |
| `+ library_strategy="WGS"` | ★ **96,623** |
| `+ library_source="GENOMIC"` | **96,497** |
| `+ library_layout="PAIRED"` | 95,261 |
| `tax_tree(4527)`（稻属全属）+ WGS | 114,131 |

### 2.2 ★ 按深度过滤（本项目真正关心的）

| 深度门槛 | 命中数 |
| --- | ---: |
| ≥1×（3.75e8 bp） | 61,751 |
| **≥5×（1.875e9 bp）** | ★ **32,478** |
| **≥10×（3.75e9 bp）** | ★ **24,633** |
| ≥20×（7.5e9 bp） | 10,707 |

> **含义**：本项目建库需要深度足够的材料（高深度数据用于建指纹库，再由计算机降采样模拟 ulcWGS）。
> **≥10× 有 2.4 万条**——远超 TASK-017 要求的 100–1000 份规模，**数据供给不是瓶颈**。

### 2.3 已拉取的 run 级清单

| 文件 | 内容 |
| --- | --- |
| `ena_rice_wgs_runs.tsv` | 5,000 行（默认排序，**73% 为 <1×，存在有序偏倚，仅作参照**） |
| `ena_rice_wgs_deep_runs.tsv` | **10,000 行**（≥5×，含 FASTQ 直链与字节数） |

**深度清单概况（10,000 条 ≥5×）**：

| 维度 | 分布 |
| --- | --- |
| 测序平台 | ILLUMINA 9,758 / DNBSEQ 120 / BGISEQ 72 / PACBIO 38 / ONT 12 |
| 文库布局 | PAIRED 9,942 / SINGLE 58 |
| 深度 | 5–10× 2,572 · 10–20× 4,055 · 20–30× 1,099 · 30–50× 1,363 · **≥50× 911** |
| ★ **提交库** | SRR 7,373 / ERR 1,372 / **DRR 1,255** |
| FASTQ 直链 | **10,000 / 10,000（100%）** |

### 2.4 ⚠️ 品种名可用性问题（影响 TASK-012）

**问题**：`sample_title` 字段质量差。随机抽样 30 例中大量为：

```
Plant sample from Oryza sativa        ← 无信息占位
3K RGP mapping to Os.XI-1A Reference  ← 研究项目名，非品种
N1-10-8D / Nx-2-44B / N5-3-42C        ← 育种行编号
1143 / 786 / X173                     ← 纯编号
Oryza sativa                          ← 物种名
```

**解决方案**：品种名可从 ENA 取到，但有两个层次，**主力字段是 `cultivar`**：

| 来源 | 字段 | 实测填写率（21,654 样本） |
| --- | --- | ---: |
| ENA Portal `read_run` | `cultivar` 列 | 51.7% |
| ENA 样本 XML | `<TAG>cultivar</TAG>` | ★ **72.4%** |
| ENA 样本 XML | `<TAG>subspecific genetic lineage name</TAG>` | 0.1% |
| ENA 样本 XML | `<DESCRIPTION>` 自由文本 | 28.8% |

> ### ⚠️ 更正说明（2026-09-20）
>
> 本文档初版曾写"品种名**不在** `cultivar` 字段，而在 `subspecific genetic lineage name`"。
> **该结论错误，现已更正。**
>
> **错误原因**：初版只验证了 **1 个样本**（`SAMEA114006088`，ITQB NOVA 提交），
> 该提交者恰好使用 `subspecific genetic lineage name` 这一写法，
> 我便据此推断为通用规律。**单样本不足以支撑字段层面的结论。**
>
> **实际情况**（扩大到 21,654 个样本后统计）：
> - `subspecific genetic lineage name` 仅 **20/21,654 = 0.1%**，是个别提交者的习惯；
> - **`cultivar` 标签才是主力字段（72.4%）**。
>
> **教训**：字段层面的结论必须基于全量或大样本统计，不能凭单例推断。

**取数方式**（两条路，实测均可用）：

```bash
# 路径 A：Portal API 一次取全量（快，含 cultivar 列）
#   https://www.ebi.ac.uk/ena/portal/api/search?result=read_run&query=...&fields=...,cultivar,...&format=tsv

# 路径 B：批量样本 XML（含 cultivar 标签，覆盖更全）
#   https://www.ebi.ac.uk/ena/browser/api/xml/{acc1},{acc2},...   实测 200 个/请求、1.7 秒
```

> **实测性能**：路径 B 批量拉取 **21,654 个样本仅需 241 秒**（109 批 × 200 个，0 失败）。
> ENA 对 NCBI（`SAMN`）与 DDBJ（`SAMD`）的 BioSample 同样提供 XML。

**★ 字段有值 ≠ 值是品种名**。实测高频伪值（必须先过滤）：

| 值 | 出现次数 | 性质 |
| --- | ---: | --- |
| `not applicable` | 9,904 | INSDC 官方缺失值词表 |
| `zh11` | 5,349 | ★ **不是伪值**——是"中花 11"的真实缩写，**不能丢弃** |
| `cultivar` | 575 | 字段名本身 |
| `rice` | 297 | 物种名 |
| `allotetraploid derived from nipponbare and 93-11` | 202 | 实验描述 |
| `rils from the cross between shennong265 and r99` | 153 | 群体描述 |
| `missing` / `n/a` / `not collected` | 218 | 缺失值 |
| `indica/japonica`、`indica rice`、`asian cultivated rice` | 数十 | 亚种而非品种 |

**对 TASK-012 的最终做法**：字段优先级为
`xml:cultivar_tag` → `portal:cultivar` → 自由文本提取，
每个候选值须过五道校验（亚种 / 占位符 / 编号 / 描述文本 / 词数）。
通过率与拒绝原因见 `data/metadata/candidates/name_quality_report.txt`。

---

## 3. TASK-010：DDBJ 检索

### 3.1 ⚠️ DDBJ Search API 当前不可用（实测）

**结论：DDBJ 自建的 Search API 全部端点返回 504 Gateway Time-out。**

| 端点 | 结果 |
| --- | --- |
| `/search/api/service-info` | ❌ 504（连健康检查都超时） |
| `/search/api/entries/sra-run/DRR771384` | ❌ 504 |
| `/search/api/entries/biosample/SAMD00000001` | ❌ 504 |
| `/search/api/db-portal/search?db=sra&...` | ❌ 504 |
| `/search/api/db-portal/cross-search?...` | ❌ 504 |
| `/search/entry/sra-run/DRR771384.jsonld` | ❌ 超时 |
| `https://ddbj.nig.ac.jp/resource/sra-run/DRR771384` | ⚠️ 200，但返回**前端 SPA 骨架页**，非数据 |
| `https://getentry.ddbj.nig.ac.jp/getentry/na/DRR771384` | ⚠️ 200，内容为 `No results.` |

**诊断依据**（用于判断是"我方网络问题"还是"对方服务问题"）：
- 参数校验类错误（如 `db` 枚举非法、`perPage` 取值非法）**能正常返回 422**，
  且错误信息完整（"Input should be 'ddbj', 'sra', 'bioproject'…"、"Allowed: 20, 50, 100"）
  → **说明 nginx 可达、API 应用层正常**；
- 但所有需要访问 Elasticsearch 后端的请求**一律 504**（含无查询的 service-info）
  → **结论：故障在 DDBJ 的 ES 后端，不在我方网络**；
- 同一时间、同一网络下，ENA 与 NCBI 的 API **全部正常**（响应 < 1 秒）
  → 排除本地网络因素。

> ⚠️ 另注：WSL 有 "localhost 代理配置未镜像" 的告警，但 ENA/NCBI 均正常，
> 说明该告警不影响本次判断。

### 3.2 ★ 替代路径：DDBJ 数据完全可达

DDBJ 的 DRA（Read Archive）是 **INSDC 成员库**，数据与 NCBI SRA、ENA 三方互为镜像。
即使 DDBJ 自身检索接口不可用，**其数据仍可通过另外两个库完整检索与下载**：

| 途径 | 证据 |
| --- | --- |
| **经 ENA** | 已拉取的 10,000 条 ≥5× 记录中，**DRR 1,255 条**（含 FASTQ 直链） |
| **经 NCBI E-utilities** | 前 300 条相关度命中中 **292 条为 DRR**，且 `expxml` 中含完整的 DDBJ 编号体系：`DRA026964`（Submitter）/ `DRX948749`（Experiment）/ `DRP016783`（Study）/ `DRS635056`（Sample）/ `DRR971114`（Run）/ `PRJDB38331`（BioProject）/ `SAMD01760641`（BioSample） |

**DDBJ 深测序记录的提交时间分布**（在 1,255 条 DRR 中）：

| 年份 | 记录数 |
| --- | ---: |
| 2016–2022 | 24 |
| 2025 | 173 |
| **2026** | **1,058** |

> **含义**：DDBJ 近期有**大规模新增水稻提交**（2026 年 1,058 条），
> 且这批数据深度高（≥5×）、平台多样（含 DNBSEQ）、标题含明确品种/品系名
> （如 `B1674`、`A1065`、`B1139`）。
> **这对本项目是重要资源**——但**必须记入数据来源审计**（来源国、许可、可追溯性）。

### 3.3 结论与建议

| 事项 | 结论 |
| --- | --- |
| DDBJ 自建 API 能否用于本项目 | ❌ **当前不能**，需等待其 ES 后端恢复 |
| DDBJ 数据能否用于本项目 | ✅ **能**，经 ENA（首选）或 NCBI E-utilities |
| 是否影响项目进度 | ❌ **不影响**——ENA 已能覆盖全部 INSDC 数据 |
| 后续动作 | ①TASK-012 建表时**保留 DDBJ 来源标注**；②择期复测 DDBJ API；③在论文数据来源章节说明这一情况 |

---

## 4. 三库横向对照（本项目选型）

| 维度 | NCBI SRA | **ENA** | DDBJ DRA |
| --- | --- | --- | --- |
| 水稻 WGS 记录数 | 106,474（实验） | ★ **96,623**（run） | 经 ENA 可见 1,255（≥5× 内） |
| ≥10× 可用量 | 未逐个统计 | ★ **24,633** | 含于 ENA 计数 |
| **API 可用性** | ✅ 正常 | ✅ **正常且最快（<1 s）** | ❌ **504（ES 后端故障）** |
| FASTQ 直链 | 需转 ENA/其它 | ★ **直接在 TSV 里** | 经 ENA 可得 |
| 元数据质量 | 中（需解析 XML） | ★ **高（含样本属性）** | 好（题为品种/品系名） |
| **本项目选型** | 🔶 辅助（交叉核验） | ★ **主下载源** | 🔶 数据可用，接口不用 |

> **选型结论**：**ENA 作为主下载源**，NCBI E-utilities 作为交叉核验与 BioProject/BioSample 补全，
> DDBJ 数据经 ENA 获取并单独标注来源。

---

## 5. ⚠️ 本次调研中的一次自我纠错（方法学记录）

调研过程中发现并修正了**脚本自身的参数传递缺陷**：

- **现象**：同一查询 `"Oryza sativa"[Organism]` 对 biosample 库，两轮分别返回 66,760 与 1,094；
  且 bioproject 的 "Oryza sativa WGS" 只命中 **1** 条——明显异常。
- **根因**：计数函数的签名是 `(db, label, term)`，但函数体内误用了 `$2`（标签）而非 `$3`（查询词），
  导致**实际检索的是标签字符串**（如 `"OS-organism"`、`"rice-plain"`）。
- **修正**：统一为 3 参数并显式引用 `$3`；同时**为每条查询抓取 NCBI 返回的 `querytranslation`**
  作为"实际执行了什么"的证据（`data/metadata/search/ncbi_search_summary.tsv` 第 5 列）。
- **影响范围**：所有 `count_db`（3 参数版）结果作废并已重跑；
  `count_sra`（2 参数版）参数正确，其结果与重跑结果**完全一致**（106,474 / 106,685），可采信。
- **副产物**：重跑后发现，由于 NCBI 把连字符视为空格，
  原先"作废"的 `rice-variety-WGS`(26,469) 与正确的 `rice variety WGS`(26,469) **恰好相等**——
  这也反向印证了修正后的结果可信。

> **教训**：涉及"检索结果计数"的工作，**必须记录查询的翻译/规范化形式**，
> 否则无法发现"搜的不是你以为的东西"。本项目的所有检索脚本已按此规范改造。

---

## 6. 对下游任务的直接输入

| 下游任务 | 从本文档取什么 |
| --- | --- |
| **TASK-011**（检索公开论文） | 第 1.2 节的 `PRJCA020505`、`rice ZH11 ems4611 database` 等线索；3K RGP 相关 study |
| **TASK-012**（候选样本表） | ①②见 TASK-011 报告；③品种名主力字段是 `cultivar`（**勿用** `subspecific genetic lineage name`，覆盖率仅 0.1%） |
| **TASK-013**（名称标准化） | 第 2.4 节的三级提取策略（别名问题在 `IR64`/`IR 64`/`IR-64` 之外，还有 `NIP`/`Nipponbare` 这类缩写） |
| **TASK-014**（样本去重） | 同一品种跨库重复：SRR/ERR/DRR 编号不同但可能是同一品种——需按品种名去重而非按 accession |
| **TASK-015**（Pilot Panel） | 已有 5 份（P01–P05）；第 2.3 节可扩展至 20–50 份 |
| **TASK-016**（独立测试集） | 从 ≥10× 的 24,633 条中预留，**建库前冻结** |
| **TASK-017**（正式数据集） | 数据供给充裕（≥10× 有 2.4 万条），**瓶颈在磁盘与算力，不在数据可得性** |

---

## 7. 复现方式

```bash
# 全部脚本在 WSL 内运行（Windows 侧用 wsl.exe 调用）
wsl -d Ubuntu -u root

# TASK-008 NCBI
bash /mnt/d/dsh/RiceVar-ID/scripts/search_ncbi.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/fetch_ncbi_esummary.sh   # 含 esummary 抓取与解析
bash /mnt/d/dsh/RiceVar-ID/scripts/verify_ncbi_counts.sh    # 命中数核验（含查询翻译）

# TASK-009 ENA
bash /mnt/d/dsh/RiceVar-ID/scripts/search_ena.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/search_round2.sh         # 按深度过滤
bash /mnt/d/dsh/RiceVar-ID/scripts/analyze_deep.sh          # 深清单分析
bash /mnt/d/dsh/RiceVar-ID/scripts/probe_ena_samples.sh     # 品种名字段验证

# TASK-010 DDBJ
bash /mnt/d/dsh/RiceVar-ID/scripts/probe_ddbj.sh
bash /mnt/d/dsh/RiceVar-ID/scripts/probe_ddbj2.sh           # 多路径探测
```

产出文件（`data/metadata/search/`）：

| 文件 | 内容 |
| --- | --- |
| `ncbi_search_summary.tsv` | NCBI 13 条查询的命中数 + 查询翻译 |
| `ncbi_count_verification.tsv` | 命中数稳定性核验（同一查询连测 3 次） |
| `ncbi_sra_esummary.json` | 300 条 SRA 实验的原始 esummary（440 KB） |
| `ncbi_sra_runs.tsv` | 解析后的 run 级表（300 行 × 18 列） |
| `ena_search_summary.tsv` | ENA 7 条查询的命中数 |
| `ena_rice_wgs_runs.tsv` | 5,000 条（默认排序，含低深度） |
| `ena_rice_wgs_deep_runs.tsv` | **10,000 条 ≥5×（含 FASTQ 直链）** |
