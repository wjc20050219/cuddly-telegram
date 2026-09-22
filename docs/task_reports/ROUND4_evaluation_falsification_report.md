# Round 4 报告：识别评估层证伪审查

日期：本轮（承接 Round 3 marker 选择层证伪审查）
对象：`scripts/evaluate_identification.py`（产出论文核心指标 Top-1/Top-5/召回率/拒识率）
方法：与 Round 3 相同——先把疑似缺陷写成**可否证的命题**，用精确计算证实或证伪，再决定是否改代码。

## 一、结论摘要

| 编号 | 命题 | 判定 | 处置 |
| --- | --- | --- | --- |
| H-A | 未标注查询被计入准确率分母，压低准确率 | **证实（真实缺陷）** | 已修复 + 回归测试 |
| H-B | 真值表与参考矩阵 id 空间不一致时静默产出 0.0 准确率 | **证实（真实缺陷）** | 已修复 + 回归测试 |
| H-C | `top1_correct_sample` 对技术重复样本恒为真，不可当泛化准确率 | 证实（表述风险，非代码缺陷） | 文档既定边界已覆盖，未改代码 |
| H-D | `depth_from_name` 在真实路径上解析错误 | **证伪（代码正确）** | 不改，锁为测试 |

本次实际修复 **2 个真实缺陷**；证伪 1 个命题并锁为回归测试；1 项记为表述边界。

## 二、H-A：未标注查询稀释准确率（真实缺陷）

### 命题
`summarize()` 用 `row.get("top1_correct_variety") is not None` 挑选计分行；而 `main()` 中
`row["top1_correct_variety"] = bool(true_variety and ...)`，当查询样本在真值表中没有品种名时
`bool(None and ...)` 得到 **`False`**（不是 `None`），于是该行**进入分母并必然计为错误**。
命题：这会使报告准确率系统性偏低。

### 证据
构造 3 个查询，其中 2 个有标注且都识别正确、1 个无标注：

```
n_scored = 3   -> top1_variety_accuracy = 0.667
（若未标注查询被排除，应为 2/2 = 1.000）
```

### 可达性（关键：不是理论问题）
`server/07_identify.sh` 第 44–49 行用 `sample_ids` 生成真值表，逐样本写
`sample_value "$sid" variety_name`。而 `read_truth()` 第 90 行
`if sample and variety:` 会**静默丢弃品种名为空的样本**。因此只要 Pilot 清单中有一个样本
品种名为空，该样本就变成未标注查询，其低深度 VCF 仍会被评分——每多一个这样的样本，
准确率就凭空下降 `1/n_scored`。本项目已知品种名规范化填充率不完整，该路径可达。

### 修复
`scripts/evaluate_identification.py` 第 227–237 行：品种名未知时显式置 `None`（保留在
`per_query.tsv` 中可见，但不进分母），仅在 `true_variety` 为真时计算布尔判定。

## 三、H-B：id 空间不一致静默产出 0.0（真实缺陷）

### 命题
`truth.get(best)` 以**参考矩阵的样本 id** 查真值表。若真值表用另一套 id（例如 run accession
而非 sample id），所有查询都查不到品种名 → 全部 `None` → 准确率 0.0，**但脚本不报错**，
产出一份格式完全合法、内容全错的 `summary.json`。命题：这会被误当作"真实实验结果"。

### 证据
真值表写 `NOT_A_SAMPLE`、查询样本为 `S1` 时，反向副本 exit 0 且写出 `summary.json`。

### 修复
第 240–254 行新增守卫：当 `truth` 非空但**没有任何**查询匹配到品种名时，`SystemExit`
并提示检查 `sample_id` 列；部分未标注时在 stderr 打印
`[warn] N/M 个查询在真值表中无品种名，这些查询不计入准确率分母`。

### 同时补强可审计性
`summary.json` 新增 `n_labelled_queries`；每个深度新增 `n_scored` 与 `n_unlabelled`。
论文引用准确率时必须同时给出分母，避免"分母被悄悄改动"这类不可复现问题。

## 四、H-D：`depth_from_name`（证伪）

命题：该函数用 `for part in reversed(path.parts)` 取第一个 `d`+数字开头且长度 >2 的路径段，
可能在真实路径上误判。精确测试结果：

| 路径 | 解析 |
| --- | --- |
| `.../d0.05_r1/ERR1.markers.vcf.gz` | `0.05` |
| `.../d1_r2/ERR1.markers.vcf.gz` | `1.0` |
| `.../d0.02_r1/S1.vcf.gz` | `0.02` |
| `.../results/depth/ERR1.vcf.gz` | `None` |

结论：在 `05_simulate.sh` / `07_identify.sh` 实际产生的目录形状上**解析正确**，且无法识别时
返回 `None` 而非臆造深度。**代码正确，不改**；已锁为回归测试防止日后破坏。

## 五、H-C：`top1_correct_sample` 的表述边界（未改代码）

对技术重复样本，查询样本就是参考样本本身，`best == sample` 近乎恒真。该指标**不是泛化准确率**。
现有 `summary.json` 的 `note` 字段与 `07_identify.sh` 收尾 echo 已声明"closed-set"，
`docs/methods/snp_evaluation_design.md` 亦已写明。属既定科学边界，本轮不改代码，
但论文中不得把 `top1_sample_accuracy` 当作识别准确率报告。

## 六、反向验证（证明新测试真的能抓错）

仅"改完测试通过"不足以证明测试有效。`tests/test_eval_reverse.py` 把两处修复**还原成原始写法**
（并删除新守卫），再跑同一组数据：

```
[OK] unlabelled dilution      buggy accuracy=0.667 (test expects 1.0)
[OK] mismatched id space      buggy copy exit=0, summary written=True
反向验证：2/2 个新测试确实能检出原缺陷
```

### 过程中的一次自我纠错
首版反向脚本报 2/2 未检出。诊断为**测试脚手架自身的 bug**：移除守卫时用的文本跨度是
"守卫注释 → `depths: Dict`"，而 `by_depth = defaultdict(list)` 恰好落在该跨度内（它在
`summarize` 开头，不在守卫之后），导致反向副本以 `NameError` 崩溃——退出码非 0 被误判为
"未检出"。修正跨度并加入断言（`assert "by_depth = defaultdict" not in removed`）后 2/2 检出。
教训：反向验证脚本本身也会骗人，必须确认反向副本是**以正确原因**失败。

## 七、本轮交付物

| 文件 | 变更 |
| --- | --- |
| `scripts/evaluate_identification.py` | 修复 H-A、H-B；新增 `n_labelled_queries`/`n_scored`/`n_unlabelled` |
| `tests/test_evaluate_identification.py` | 10 → 13 项测试；3 项新增回归；4 处 `TemporaryDirectory` 改走 `.tmp`（修 Windows `PermissionError` 隐患） |
| `tests/test_eval_reverse.py` | 新增：反向验证 2/2 |
| `.learnings/LEARNINGS.md` | LRN-012、LRN-013 |

## 八、诚实边界

- 上述"修复验证"全部基于**合成数据**，不构成任何真实识别率结论。
- 项目**没有任何真实数据结果**：`evaluate_identification.py` **从未在真实低深度 VCF 上运行**。
  论文中 Top-1/Top-5/召回率/拒识率仍必须保持 `{{RESULT: ...}}` 占位符。
- 本轮未触碰 `select_snp_markers.py`；冻结 marker 集合与阈值选择逻辑不受影响。
- `verify_thesis_placeholders.py` 仍为 exit 0：本轮未向论文骨架写入任何具体数值。
- 本机无可用 Bash，`bash -n` 与真实 bcftools/samtools 命令仍未在服务器上验证。
