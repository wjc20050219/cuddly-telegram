# TASK-012 报告：品种名称标准化

> **编号说明**：本报告采用**任务书 B 编号**。对应原 `TASK_LIST.md` 的 TASK-013。
> 见 `docs/TASK_NUMBERING.md`。

- 日期：2026-09-20
- 结果：✅ 完成
- 产出：`variety_alias.tsv`、`variety_canonical.tsv`、`unresolved_names.txt`

---

## 一、任务要求与产出

任务书第十节要求建立 `variety_alias.tsv` 处理 `IR64` / `IR 64` / `IR-64` 这类
名称问题，并检查同义词、历史名称、duplicate samples。

**产出**：

| 文件 | 内容 |
| --- | --- |
| `variety_alias.tsv` | 8,501 行：别名 → 规范名 |
| `variety_canonical.tsv` | **8,415 个规范品种**（含样本数、写法数、证据类型） |
| `unresolved_names.txt` | 待人工核对的编号型名称 |

## 二、★ 归并的证据分级（本任务的核心设计）

任务书要求做名称标准化，但**"看起来像"不等于"就是同一个品种"**。
因此本任务把归并分成两类，**证据强度不同，分开标注**：

| 证据类型 | `evidence` 值 | 依据 | 可否被推翻 |
| --- | --- | --- | --- |
| **机械规范化** | `mechanical_normalization` | 规范化后字符串相同（大小写/空格/连字符/括号）——**客观可验证** | 否 |
| **人工整理** | `curated_common_usage` | 领域公开惯用缩写（如 ZH11 = Zhonghua 11） | ✅ **可被人工复核推翻** |

> **绝不把"看起来像"的两个名字合并。** 无法确定的留在 `unresolved_names.txt` 等人看。

## 三、归并结果

### 3.1 总体

| 指标 | 数值 |
| --- | ---: |
| 原始写法 | 8,501 |
| **规范品种** | **8,415** |
| 发生归并的品种 | **84** |
| 其中 curated 归并 | 7 |

### 3.2 ★ 归并明细（前 12）

| 规范名 | run 数 | 证据 | 合并的写法 |
| --- | ---: | --- | --- |
| **Zhonghua 11** | **5,360** | curated | `ZH11` \| `Zhonghua11` |
| Nipponbare | 53 | curated | `NPB` \| `Nipponbare` |
| Samba Mahsuri | 28 | mechanical | `Samba Mahsuri` \| `samba mahsuri` |
| **Taichung Native 1** | 25 | curated | `Taichung Native 1 (TN1)` \| `TN1` |
| **93-11** | 18 | curated | `9311` \| `93-11` \| `9311(Wuhan)` |
| Y58S | 13 | curated | `Y58S` \| `Y58s` |
| **Minghui 63** | 12 | curated | `Minghui63` \| `Minghui_63` |
| Huanghuazhan | 11 | curated | `Huanghuazhan` \| `Huang Hua Zhan` |
| BPT-5204 | 8 | mechanical | `BPT-5204` \| `BPT 5204` |
| Wushansimiao | 7 | mechanical | `Wushansimiao` \| `Wu Shan Si Miao` |
| Huazhan | 6 | mechanical | `Huazhan` \| `Hua Zhan` |
| Yuetai B | 6 | mechanical | `Yuetai B` \| `YuetaiB` \| `Yuetai_B` |

### 3.3 规范品种 Top 12

| 规范名 | run 数 | 写法数 |
| --- | ---: | ---: |
| **Zhonghua 11** | 5,360 | 2 |
| Kitaake | 62 | 1 |
| Nipponbare | 53 | 2 |
| SK1 | 47 | 1 |
| DN416 | 36 | 1 |
| DG1 | 31 | 1 |
| Samba Mahsuri | 28 | 2 |
| NIPB | 27 | 1 |
| Taichung Native 1 | 25 | 2 |
| 93-11 | 18 | 3 |
| DN423 | 18 | 1 |
| Y58S | 13 | 2 |

---

## 四、⚠️ 发现并修复的一个 bug

**现象**：首次运行时 `Zhonghua 11` 只显示 11 个 run，但 `zh11` 单独就有 5,349。

**根因**：`canon_stats[canon] = {...}` 在**多个 norm_key 映射到同一规范名**时
（`zh11` 与 `zhonghua11` 都映射到 `Zhonghua 11`）是**覆盖而非累加**。

**修复**：改为累加（`n_runs +=`、`spellings` 拼接），并让 `evidence` 取更强的一级。
修复后 `Zhonghua 11` = **5,360**（5,349 + 11），与原始数据吻合。

---

## 五、★ 对建库的关键含义：94.9% 的品种只有 1 个 run

| 每个品种的 run 数 | 品种数 | 占比 |
| --- | ---: | ---: |
| **1** | 7,987 | **94.9%** |
| 2–3 | 359 | 4.3% |
| 4–9 | 50 | 0.6% |
| ≥10 | 19 | 0.2% |

**有 ≥2 个 run 的品种：428 个。**

> **这直接限定了能做什么实验**：
> - **428 个品种**可做「**同品种跨测序 run**」的指纹稳定性检验（真实生物学重复）；
> - **其余 7,987 个品种**只能做「**同一样本不同降采样**」的检验（技术重复）。
>
> 二者证据强度不同，论文中**必须区分表述**——前者能说明指纹在真实样本间稳定，
> 后者只能说明降采样过程稳定。**不可混为一谈。**

---

## 六、产出与复现

```bash
python3 scripts/task012_variety_alias.py
```

## 七、自我评估

| 核对项 | 结果 |
| --- | --- |
| 是否产出 `variety_alias.tsv` | ✅ 8,501 行 |
| 是否处理大小写/空格/连字符 | ✅ mechanical 类 |
| 是否区分证据强度 | ✅ §二，两类分开标注 |
| 是否避免了臆测合并 | ✅ 无法确定的进 `unresolved_names.txt` |
| 是否自查并修复 bug | ✅ §四 |
| 是否给出对下游的可执行结论 | ✅ §五（94.9% 单 run 的含义） |

**遗留**：
1. `curated` 同义词表目前仅 7 条，**范围保守**——因为超出公开常识的合并需要文献依据，
   本项目尚未做文献检索（原编号 TASK-011）；
2. 712 个编号型名称待人工核对；
3. `NIPB`(27) 与 `Nipponbare` 是否同一品种**未合并**——依据不足，留待核实。

> **结论：TASK-012 合格。**
