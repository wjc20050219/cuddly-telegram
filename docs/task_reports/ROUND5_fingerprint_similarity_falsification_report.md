# Round 5 报告：指纹相似度与品种比较层证伪审查

日期：本轮（承接 Round 3 marker 选择层、Round 4 识别评估层）
对象：`src/ricevar_id/fingerprint.py`（相似度与排序核心）、`src/ricevar_id/dbquery.py::compare_varieties`（品种两两比较）
方法：延续前两轮——先把疑似缺陷写成**可否证的命题**，用精确计算证实或证伪，再决定是否改代码。

## 一、结论摘要

| 编号 | 命题 | 判定 | 处置 |
| --- | --- | --- | --- |
| H-A | `n_different_markers` 与 `(1-sim)*n` 是同一个量 | **证伪（两者确实是不同量）** | 未改代码；补文档说明 + 锁为测试 |
| H-C | IBS 与 Hamming 排序等价，方法选择不影响结论 | **证伪（可翻转 Top-1）** | 已补文档 + 锁为测试 |
| H-D | Jaccard 在 `union==0` 时丢弃完美匹配 | 证实（既定边界） | 未改代码；补文档 + 锁为测试 |
| H-E | 空 concordance 记为 0.0 而非 NaN | **证伪（代码正确记 NaN）** | 不改，锁为测试 |
| **H-G** | **`compare_varieties` 的 `method` 参数从未被使用** | **证实（真实缺陷）** | **已修复 + 回归测试 + 反向验证 3/3** |

本次修复 **1 个真实缺陷**；证伪 3 个命题并锁为测试；1 项既定科学边界补入文档。

## 二、H-G：`compare_varieties` 的 `method` 参数是死参数（真实缺陷）

### 命题
该函数签名 `compare_varieties(self, variety_a, variety_b, method="ibs", min_compared=50)`
接受并**默认** `method="ibs"`，但函数体可能从未引用它，实际硬编码 Hamming。
若成立，则：调用方选择任何方法都得到同一数值，而返回结果的"方法标签"是错的。

### 证据（`inspect.getsource` 检查函数体）
```
signature: (self, variety_a, variety_b, method='ibs', min_compared=50)
body lines mentioning method: (NONE)
```
函数体第 210–211 行无条件执行 `different = sum(1 for x, y in compared if x != y)` 与
`scores.append(1.0 - different / float(len(compared)))` —— 这正是 **Hamming** 公式，
而默认值声称是 IBS。参数被完全忽略。

### 影响（为什么这不是小事）
1. **UI 说谎**：`app/streamlit_app.py` 第 57 行提供 `["ibs","hamming","jaccard"]` 三选一，
   第 217 行把它传给 `compare_varieties(method=method)`。用户选 "jaccard" 实际得到 Hamming。
2. **论文章节尺度不一致**：`docs/thesis/THESIS_DRAFT.md` §3.7「品种间相似度」调用
   `compare_varieties`（实际 Hamming），而第 4 章识别结果来自
   `identify_top_k`（默认 IBS）。两列数字名义同名、尺度不同，且从输出无法察觉。
3. **无法审计**：返回值里没有方法字段，结果无法追溯。

### 两种方法确实会给出不同答案（不是等价改写）
query `[0,0]`，参考 `[1,1]` 与 `[0,2]`：
```
IBS     order: [('R1', 0.5), ('R2', 0.5)]   -> Top-1 = R1（并列，按 id 打破）
Hamming order: [('R2', 0.5), ('R1', 0.0)]   -> Top-1 = R2
```
**Top-1 结论本身会因方法而改变。** 因此"用哪个方法"属于必须预先冻结的实验参数。

### 修复
`dbquery.compare_varieties` 改为复用 `fingerprint` 中的
`ibs_similarity` / `hamming_similarity` / `binary_jaccard`：
- 与 `identify()` **共用同一实现**，两处尺度天然一致；
- 非法方法名 `raise ValueError`；
- 返回值新增 `"method": method` 字段，结果可追溯。

修复后实测：VarA{S1,S2} vs VarB{S3}，markers `S1=[0,0,0] S3=[1,0,0]`
```
固定实现: ibs=0.8333  hamming=0.6667   （两法确实不同）
修复前  : ibs=0.6667  hamming=0.6667   （两法恒等 -> 参数无效）
```

## 三、H-A：`n_different_markers` ≠ `(1-sim)×n`（证伪，补文档）

命题曾表述为"两个字段互相矛盾"。精确计算后**证伪**——两者定义不同，各自正确：

| query | ref | IBS 相似度 | `n_different_markers` | `(1-sim)×n` |
| --- | --- | --- | --- | --- |
| `[0,0]` | `[1,2]` | 0.2500 | 2 | **1.5** |
| `[0,0,0]` | `[1,1,2]` | 0.3333 | 3 | **2.0** |
| `[0,0,0]` | `[2,2,2]` | 0.0000 | 3 | 3.0（恰好相等） |

原因：IBS 分子是 `Σ|a-b|`，一个 0/2 对贡献 **2**；而 `n_different_markers`
统计**位点数**，该位点只计 **1**。二者只在"全部差异对都是 0/2"时偶然相等——
这正是初次用 `[0,0,0]` vs `[2,2,2]` 探测会误以为一致的原因（LRN-011 的同类陷阱）。
**代码正确，不改**；已在 `docs/methods/snp_evaluation_design.md` §4.3 写明定义，
并锁为测试（含"何时相等"的边界用例）。

## 四、H-C / H-D / H-E（证伪或既定边界，均未改代码）

- **H-C**：IBS 与 Hamming 排序不等价。3000 次随机试验中 **1454 次排序不同**。
  属真实实验参数差异，已写入设计文档 §4.2 要求显式声明。
- **H-D**：Jaccard 在 `union==0`（双方均无 1）时返回 NaN，候选被移出排序。
  这是 Jaccard 定义本身的边界，代码用 `else float("nan")` 正确处理了除零。
  已在文档中说明"Jaccard 只用于明确定义的二元 presence/absence 编码"。
- **H-E**：空 concordance 返回 **NaN 而非 0.0**（已用 `math.isnan` 验证），
  不会在求均值时被当作真实失败计入。**代码正确，不改。**

## 五、反向验证

`tests/test_dbquery_method_reverse.py`（已改写为正规 `TestCase`，纳入 discovery）：

```
test_baseline_fixture_really_discriminates_the_two_methods ... ok
test_buggy_implementation_ignores_the_method              ... ok
test_fixed_implementation_is_distinguishable_from_the_buggy_one ... ok
Ran 3 tests ... OK
```

第一个测试是**防"无效变异"的守卫**：先断言夹具本身能区分两种方法
（IBS 0.8333 vs Hamming 0.6667），否则后续反向检查全是空转。

### 过程中的一次自我纠错（第二次同类问题）
首版反向脚本用纯 0-vs-2 夹具（`S3=[2,2,2]`），结果 `baseline distinguishes the
methods: False`——因为纯 0/2 下 IBS 与 Hamming 恰好都等于 0.0，夹具**无法区分**，
反向验证因此失去意义。改用含 0-vs-1 的夹具（`S3=[1,0,0]`）后两法分别为 0.8333 / 0.6667。
这与 LRN-011、LRN-013 是同一类错误的第三次出现，已强化为**反向测试必须先验证夹具具备区分力**。

## 六、本轮交付物

| 文件 | 变更 |
| --- | --- |
| `src/ricevar_id/dbquery.py` | 修复 H-G：`compare_varieties` 真正使用 `method`，复用 fingerprint 实现，新增 `method` 字段与非法值校验 |
| `docs/methods/snp_evaluation_design.md` | 新增 §4.2（方法必须显式声明、两路径同尺度、方法会翻转结论）与 §4.3（`n_different_markers` 准确含义） |
| `tests/test_fingerprint.py` | 6 → 14 项测试；新增 `SimilarityBoundaryTests` 9 项 |
| `tests/test_fingerprint_db.py` | 20 → 22 项测试；新增 2 项方法参数回归测试 |
| `tests/test_dbquery_method_reverse.py` | 新增：3 项反向验证（含夹具区分力守卫） |
| `.learnings/LEARNINGS.md` | LRN-014、LRN-015 |

## 七、诚实边界

- 上述"修复验证"全部基于**合成基因型**，不构成任何真实识别率或品种间相似度结论。
- 项目**没有任何真实数据结果**：`compare_varieties` 与 `identify_top_k` **从未在真实
  水稻基因型矩阵上运行**。论文 §3.7 与第 4 章的数字仍必须保持 `{{RESULT: ...}}` 占位符。
- 本轮未触碰 `select_snp_markers.py` 与 `evaluate_identification.py` 的既有修复。
- `verify_thesis_placeholders.py` 仍为 exit 0：本轮未向论文骨架写入任何具体数值。
- 本机无可用 Bash，`bash -n` 与真实 bcftools/samtools 命令仍未在服务器上验证。
- `RV_METHOD` 默认值为 `ibs`，与设计文档一致；但该变量目前仅在 `07_identify.sh` 中定义，
  runbook 未说明如何覆盖，建议后续在 runbook 中补充。
