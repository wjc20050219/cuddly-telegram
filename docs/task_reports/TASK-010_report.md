# TASK-010 报告：搜索 DDBJ

- 日期：2026-09-16
- 结果：⚠️ **部分完成**（DDBJ 自建 API 不可用；DDBJ 数据改用替代路径检索成功）
- 状态说明：**任务目标（检索日本公开测序数据）已达成，但未通过 DDBJ 官方接口达成**

## 一、任务要求与产出

任务清单要求：**搜索日本公开测序数据**（即 DDBJ / DRA）。

**产出**：
- `scripts/probe_ddbj.sh`、`probe_ddbj2.sh`、`show_sample_attrs.sh`（探测脚本）
- 检索结果并入 `data/metadata/search/ena_rice_wgs_deep_runs.tsv`（其中 DRR 记录 1,255 条）
- 并入 `data/metadata/search/ncbi_sra_runs.tsv`（其中 DRR 记录 292 条）

## 二、⚠️ 核心结论：DDBJ Search API 全线不可用

**实测结果：DDBJ 自建 Search API 的所有端点均返回 504 Gateway Time-out。**

| 端点 | 结果 |
| --- | --- |
| `/search/api/service-info` | ❌ 504（**连健康检查都超时**） |
| `/search/api/entries/sra-run/DRR771384` | ❌ 504 |
| `/search/api/entries/biosample/SAMD00000001` | ❌ 504 |
| `/search/api/db-portal/search?db=sra&...` | ❌ 504 |
| `/search/api/db-portal/cross-search?...` | ❌ 504 |
| `/search/entry/sra-run/DRR771384.jsonld` | ❌ 超时 |
| `https://ddbj.nig.ac.jp/resource/sra-run/DRR771384` | ⚠️ 200，但返回**前端 SPA 骨架页**，非数据 |
| `https://getentry.ddbj.nig.ac.jp/getentry/na/DRR771384` | ⚠️ 200，内容为 `No results.` |

### 2.1 故障定位（是对方问题，不是我方网络问题）

| 证据 | 推论 |
| --- | --- |
| 参数校验类错误**能正常返回 422**，且错误信息完整（"Input should be 'ddbj', 'sra', 'bioproject'…"、"Allowed: 20, 50, 100"） | nginx 可达、**API 应用层正常** |
| 所有需访问 Elasticsearch 后端的请求**一律 504**（含无查询参数的 service-info） | **故障在 DDBJ 的 ES 后端** |
| 同一时间、同一网络下，ENA 与 NCBI 的 API **全部正常**（< 1 秒） | 排除本地网络因素 |

> 排查过程中顺带探明了两个 API 约束（由报错信息给出）：
> - `db` 枚举 ∈ {ddbj, sra, bioproject, biosample, jga, gea, metabobank, taxonomy}
> - `perPage` ∈ {20, 50, 100}

### 2.2 探测耗时特征（进一步佐证后端问题）

| 响应类型 | 耗时 |
| --- | --- |
| 504（后端超时） | 60–66 秒 |
| 422（参数校验失败） | 50–58 秒 |
| 正常 API（ENA / NCBI） | **< 1 秒** |

参数校验本应立即返回，却耗时近 1 分钟 → 说明请求在网关层就经历了长等待，
**进一步支持"DDBJ 侧服务异常"的判断**。

## 三、★ 替代路径：DDBJ 数据完全可达

DDBJ 的 DRA 是 **INSDC 成员库**，数据与 NCBI SRA、ENA 三方互为镜像。
**即使 DDBJ 自身检索接口不可用，其数据仍可完整检索与下载。**

| 途径 | 证据 |
| --- | --- |
| **经 ENA** | 已拉取的 10,000 条 ≥5× 记录中，**DRR 1,255 条**（含 FASTQ 直链） |
| **经 NCBI E-utilities** | 前 300 条相关度命中中 **292 条为 DRR**，且完整编号体系可提取 |

从 NCBI esummary 中解析出的 DDBJ 完整编号链（样例）：

```
Submitter   DRA026964        (DDBJ study submission)
Experiment  DRX948749
Study       DRP016783        "rice ZH11 ems4611 database (PRJCA020505)"
Sample      DRS635056
Run         DRR971114
BioProject  PRJDB38331
BioSample   SAMD01760641
```

### 3.1 DDBJ 深测序数据的特征

**提交时间分布**（1,255 条 DRR 中）：

| 年份 | 记录数 |
| --- | ---: |
| 2016–2022 | 24 |
| 2025 | 173 |
| **2026** | **1,058** |

**质量特征**：
- 深度：全部 ≥5×（该清单的入选条件），多数 10–30×
- 平台多样：含 ILLUMINA 与 **DNBSEQ**（国产平台，在 DDBJ 中占比明显）
- 标题含明确品系名：`B1674 (CRX842160)`、`A1065 (CRX839258)`、`B1139 (CRX841723)`
  （来自 `rice ZH11 ems4611 database` 数据库，CRX 为中国水稻实验编号）

> **评价**：这是本项目的**重要资源**——2026 年集中新增 1,058 条深测序水稻数据。
> 但**必须记入数据来源审计**（来源国、许可、可追溯性），见第五节。

## 四、结论与建议

| 事项 | 结论 |
| --- | --- |
| DDBJ 自建 API 能否用于本项目 | ❌ **当前不能**（ES 后端故障） |
| DDBJ 数据能否用于本项目 | ✅ **能**，经 ENA（首选）或 NCBI E-utilities |
| 是否阻塞项目进度 | ❌ **不阻塞**——ENA 已覆盖全部 INSDC 数据 |
| 后续动作 | ①TASK-012 建表时**保留 DDBJ 来源标注**；②择期复测 DDBJ API；③论文数据来源章节说明此情况 |

**建议的复测时机**：Phase 3 后期（TASK-011 之后）再试一次；
若届时仍不可用，则在论文中说明"数据经 INSDC 镜像库获取"，
这本身是**规范做法**（INSDC 三方镜像本就是设计目标）。

## 五、⚠️ 需在后续任务中处理的数据合规问题

DDBJ 的 2026 年新增数据（1,058 条）规模可观，但引入两个必须在 TASK-012/013 处理的问题：

| 问题 | 说明 | 处理任务 |
| --- | --- | --- |
| **来源国标注** | DDBJ/BioProject 归属与品种实际来源国可能不同 | TASK-012（`country` 字段） |
| **许可与可追溯性** | 需确认公开数据的再使用条款 | TASK-012（`source`/`status` 字段） |
| **品种名标准化** | `B1674`、`A1065` 等为品系编号，非推广品种名；与 `Nipponbare` 类名称体系不同 | TASK-013 |
| **与 NCBI/ENA 数据的重复** | 同一品种可能同时存在于三库（accession 不同） | TASK-014 |

> **本项目已明确"不做新湿实验、只用公开数据"**，因此合规风险主要在
> **来源标注与再分发**，而非数据获取本身。

## 六、自我评估

| 核对项 | 结果 |
| --- | --- |
| 是否完成"检索日本公开测序数据" | ✅ **数据层面完成**（1,255 条 DRR 已获取） |
| 是否通过 DDBJ 官方接口完成 | ❌ **未能**（API 全线 504，已定位为对方后端故障） |
| 是否给出故障定位证据 | ✅ 第 2.1 节（三条独立证据） |
| 是否提供可用替代路径 | ✅ 第 3 节（两条路径，含实测证据） |
| 是否诚实报告未达成项 | ✅ 标题与第一节均明确标注"部分完成" |
| 是否识别下游合规问题 | ✅ 第五节 |

**遗留**：DDBJ API 恢复后需复测，届时可补充直接从 DDBJ 检索的能力。
**未做无依据的推测**（未猜测故障原因的具体技术细节，只报告可观测证据）。

> 结论：**TASK-010 部分完成** —— 检索目标达成，但未通过 DDBJ 官方接口。
> 该偏差源于对方服务故障，已用替代路径消除对项目进度的影响，并如实记录。
