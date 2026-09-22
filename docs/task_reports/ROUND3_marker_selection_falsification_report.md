# 第 3 轮报告：marker 选择逻辑的证伪式审查

**目标轮次**：goal round 3/40
**本轮主题**：`select_snp_markers.py` 是全项目**科学后果最重**的脚本（它冻结
500/1000/2000 位点集），却只有 **2 个测试**。本轮对其做证伪式审查。
**性质**：不依赖服务器；**没有产生任何实验结果数值**。

---

## 一、结论先行

我提出并**逐一证伪了 4 个看似严重的缺陷**，最终只找到 1 个真实（且较小）问题。

| # | 假设的缺陷 | 结论 | 证伪方式 |
| --- | --- | --- | --- |
| 1 | 堆淘汰顺序与贪心顺序不一致，会丢强位点 | **不成立** | 直接构造候选集验证 top-N 保留 |
| 2 | 贪心间距会"饿死"，达不到 `wanted` | **不成立** | **精确 DP + 20,000 次随机构造，0 例不符** |
| 3 | 间距按染色体独立计算，2000 会被放大成 N×2000 | **不成立** | 12 染色体 × 5 位点构造，返回恰好 5 |
| 4 | 缺失率高的位点被奖励（discrimination 忽略缺失） | **不成立** | 边界条件穷举 + 排序键顺序检查 |
| — | **`test_min_distance_is_respected` 用例间距过疏，形同虚设** | **成立** | 变异测试（见 §四） |

**为什么先证伪**：这 4 处若按"看起来可疑"就去改动，会**破坏本来正确的选择逻辑**，
而位点集一旦被改动，整条下游链路（定点分型、指纹、识别率）全部失效且难以察觉。

---

## 二、逐项证伪证据

### 假设 2（最严重的一个）：贪心会饿死

`apply_spacing` 是贪心首次适配：按质量降序，若与已选项距离 ≥ `min_distance` 就保留。
直觉上，一个强位点会挡住它附近所有位点，可能导致最终数量远低于请求数——
而 `main()` 在 `len(selected) < max(counts)` 时直接 `SystemExit`，**一个位点集都不会产出**。

真实水稻 SNP 密度极不均匀（着丝粒区贫乏、臂上密集），这看起来非常可能触发。

**证伪**：用**精确 DP**（单染色体上"两两间隔 ≥ d 的最大子集"可在 O(n log n) 内最优求解）
作为基准，对随机布局与真实密度形态做对比：

```
random trials: 20000
greedy < wanted while a feasible panel of size wanted EXISTS: 0

dense cluster only 100bp       wanted=10  min_d=1000  greedy=6   exact=6   ok
dense cluster + sparse tail    wanted=10  min_d=1000  greedy=10  exact=33  ok
two dense clusters             wanted=10  min_d=1000  greedy=6   exact=6   ok
uniform 1000bp                 wanted=25  min_d=1000  greedy=25  exact=60  ok
```

**贪心 = 精确最优**，20,000 次随机布局无一例外。贪心首次适配在"取最强优先"下
确实是最优的，饿死不会发生，`SystemExit` 只在请求数**本身**超过可行上限时才触发——
这正是它该有的行为。

### 假设 3：按染色体独立计算

`apply_spacing` 用 `positions[chrom]` 分染色体记录位置，看起来像"每条染色体各取 `wanted` 个"。
若如此，`wanted=2000` 会返回约 `2000 × 12` 个位点，而 `main()` 只检查**下界**，
这个错误会静默通过。

**证伪**：12 条染色体 × 每条 5 个互不冲突的强位点，`wanted=5`：

```
apply_spacing returned: 5 markers
per-chromosome breakdown: {'chr1': 5}
=> spacing is global
```

`break` 在达到全局 `wanted` 时触发，作用域正确。

### 假设 4：缺失率被奖励

`site_metrics` 中 `discrimination = 1 - concordant/pairs` **只在已分型样本上计算**，
而 `call_rate` 单独算。这看起来意味着"缺失越多、discrimination 越不受影响"，
且 `discrimination` 是候选元组的**第一排序键**：

```
( discrimination, call_rate, maf, qual, -ordinal, chrom, pos, ref, alt )
```

**证伪**：两个理由。

其一，`discrimination` 对缺失**天然不敏感**是设计意图而非缺陷——它衡量的是
"已分型样本的基因型类别是否均衡"，与缺失无关；`call_rate` 作为**第二排序键**
在同分时明确偏向高检出率位点：

```
sparse (5/15 missing): disc=0.5556 call_rate=0.667
dense  (0/10 missing): disc=0.5556 call_rate=1.000
tuple comparison puts call_rate SECOND -> dense wins ties: True
```

其二，稀疏位点在排序**之前**就已被过滤（`select_snp_markers.py:121`）：

```python
if call_rate < 1.0 - max_missing:   # 默认 0.8
    counts["missing"] += 1
```

方向正确（`<` 而非 `>`），`call_rate < 0.8` 直接剔除。

### 假设 1：堆顺序

`scan_candidates` 用 `heapreplace(heap, candidate)` 保留最大的 `pool_size` 个候选，
`heap[0]` 始终是最小元组，淘汰方向正确；随后 `sorted(heap, reverse=True)` 交给贪心。
验证 top-2 保留 `{0.9, 0.5}` 而非 `{0.9, 0.2}`，**正确**。

---

## 三、真实发现：测试用例形同虚设

原有 `test_min_distance_is_respected` 使用间隔 1500bp 的位点、`min_distance=1000`：

```python
sites = [cand(...) for o, p in enumerate([0, 1500, 3000, 4500])]
picked = ssm.apply_spacing(sorted(sites, reverse=True), 4, 1000)
```

**这 4 个位点本来就都满足 ≥1000 间隔**。把 `min_distance` 换成 `0`（等于完全忽略间距）
返回的仍是同样这 4 个位点——**测试无法检出"间距校验被整个删掉"这一最严重的回归**。

修复：改用**紧密排布**的位点（间隔 100bp），此时 `min_distance=1000` 只应保留 1 个：

```python
packed = [cand(0.9 - o * 1e-4, o, p) for o, p in enumerate([0, 100, 200, 300])]
picked = ssm.apply_spacing(sorted(packed, reverse=True), 4, 1000)
self.assertEqual(len(picked), 1)
self.assertEqual(picked[0][6], 0, "最强的位点必须是幸存者")
```

```
min_distance=1000 -> 1 markers
min_distance=0    -> 4 markers      ← 现在能区分了
```

---

## 四、测试增强：2 → 12 项

| 新增测试 | 锁定的性质 |
| --- | --- |
| `test_invariant_sites_score_zero_discrimination` | 不变位点 discrimination = 0 |
| `test_all_missing_site_scores_zero_and_is_never_eligible` | 全缺失位点返回 `(0,0,0)`，靠 `if not called` 早返回 |
| `test_metrics_stay_in_range_exhaustively` | 穷举 4^1…4^6，`call_rate∈[0,1]`、`maf∈[0,0.5]`、`disc∈[0,1]` |
| `test_discrimination_is_label_free` | 200 次置换样本顺序，得分不变 ⇒ 排序不看品种标签 |
| `test_balanced_site_outranks_a_rare_variant` | 均衡位点优于稀有变异 |
| `test_greedy_matches_the_exact_optimum_...` | 贪心 = 精确 DP（含紧密/均匀/双簇形态 + 300 随机布局） |
| `test_spacing_is_global_not_per_chromosome` | 12 染色体请求 5 个，必须返回恰好 5 |
| `test_min_distance_is_respected` | **紧密排布**下间距校验真实生效 |
| `test_tiers_are_nested_by_construction` | 500 ⊂ 1000 ⊂ 2000 前缀嵌套 |
| `test_too_few_spaced_sites_fails_loudly_and_writes_no_panel` | 请求不可满足时**必须失败且不产出位点集** |

同时修掉一个回归隐患：该测试文件仍在使用 `tempfile.TemporaryDirectory()`
（无 `dir=`），正是此前导致 20 个测试 `PermissionError` 的写法，已改为
`TemporaryDirectory(dir=str(TMP_ROOT))`。

---

## 五、变异测试：反向验证测试本身

新增 `tests/test_selector_invariants_reverse.py`，把真实模块行为**在内存中改坏**，
确认新测试会失败：

```
[OK] all-missing/invariant sites must score 0       AssertionError
[OK] spacing must be global                         AssertionError
[OK] min_distance must be enforced (packed layout)  AssertionError
[OK] nesting is structural                          未检出，符合预期
反向验证：4/4 项符合预期
```

### 第一次只有 2/4，诊断后如实区分两种原因

- **`invariant sites` 未被检出** ⇒ **变异本身无效**：把缺失当作一个基因型类别，
  对"全 0"或"全 2"的位点毫无影响（无论怎么算都只有 1 个类别，`1 - conc/pairs` 恒为 0）；
  全缺失位点则走 `if not called` 早返回。**测试没问题，变异是空操作。**
- **`min_distance` 未被检出** ⇒ **测试确实太弱**（即 §三 的真实发现）。

改为有效变异（去掉早返回 → 给全缺失位点恒定噪声；改用紧密排布位点）后 4/4 全部检出。

---

## 六、验证结果（本轮结束）

| 检查 | 结果 |
| --- | --- |
| `python -m unittest discover -s tests` | **82 项通过**（7 项需 matplotlib 跳过），exit 0 |
| `scripts/verify_undergraduate_scope.py` | 94 通过 / 0 失败，exit 0 |
| `scripts/verify_stage_order.py` | 23 通过 / 0 失败，exit 0 |
| `scripts/verify_thesis_placeholders.py` | 0 处虚构数值，exit 0 |
| `scripts/round1_verify.py` | 28 通过 / 0 失败，exit 0 |
| `scripts/verify_shell_static.py --strict` | 0 发现，exit 0 |
| `tests/test_shell_static_detects.py` | 4/4 缺陷被检出，exit 0 |
| `tests/test_selector_invariants_reverse.py` | 4/4 变异被检出，exit 0 |

测试总数 72 → **82**。`.tmp` 已清空（0 文件）。

---

## 七、诚实边界（**必须继续保持**）

- 本轮**没有执行任何真实数据流程**。所有验证都在合成 VCF 与内存构造上完成。
- **`select_snp_markers.py` 从未在真实 joint VCF 上运行过**：真实水稻的
  位点密度、MAF 分布、`discrimination` 实际取值区间**全部未知**。
  本轮只证明"给定输入，选择逻辑的性质成立"，**不证明真实数据上能选出合格位点集**。
- "贪心达到精确最优"是在**单染色体间隔约束**这一模型下证明的；
  真实数据下 `min_distance` 与候选池规模是否合适，仍未验证。
- 项目**仍然没有任何 ✅ 级实验任务**，**没有任何真实数值**。

---

## 八、硬阻塞（未变）

1. 调度器未知（SLURM / PBS / 直接 shell）
2. `www.ebi.ac.uk` 可达性未知
3. 存储配额未知（面板清单 334.71 GiB 为**声明值**）
4. `server/00_probe.sh` 从未在服务器运行
5. 本机无 Bash（已有静态分析部分兜底）

**唯一人工动作**：把 `docs/server_admin_questions.md` 交给管理员并运行
`server/00_probe.sh`。

---

## 九、下一步

本机侧核心代码的"性质验证"已接近完备：`select_snp_markers.py` 之后，
尚未做同等强度证伪审查的模块是 `evaluate_identification.py`（12.9 KB，
识别评估层，同样直接影响论文结论）与 `fingerprint.py` 的相似度边界行为。
但需注意：**这两个模块的真实行为同样只能在服务器上验证**，本机只能验证内部一致性。
