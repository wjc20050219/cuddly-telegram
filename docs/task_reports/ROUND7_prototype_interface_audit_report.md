# Round 7 — Streamlit 原型接口审计（TASK-042~045）

## 为什么做这件事

TASK-042~045 的实现标记为"代码完成"，但**这个页面从未被启动过**——本机没有
`streamlit`（只在 `ricevar` conda 环境里）。这意味着所有只通过页面调用点暴露的
缺陷都是不可见的：单元测试覆盖的是 `dbquery` / `fingerprint` / `database` 的
函数本身，而不是"页面按用户会用的方式调用它们"。

因此本轮不新增功能，而是**按页面真实调用序列审计数据层契约**，用与用户输入
等价的参数去调用每一个被页面使用的接口。审计脚本见 `.tmp/audit_ui.py` 与
`.tmp/audit_null.py`（轮末已删除）。

## 发现 1（真实缺陷）：LIKE 通配符从用户输入泄漏

`FingerprintDatabase.find_variety(name, exact=False)` 把用户输入直接拼进
SQL `LIKE` 模式：

```python
("%" + name + "%",)          # 修复前
```

页面"品种查询"标签页正是用 `exact=False`（`app/streamlit_app.py`）。

实测（3 个品种 `Nipponbare` / `Zh11` / `Nip_pon_bare`）：

| 输入 | 修复前结果 | 说明 |
|---|---|---|
| `%` | 全部 3 个品种 | 单个 `%` 列出整个库 |
| `_` | 全部 3 个品种 | `_` 匹配任意单字符 |
| `N_p_pon_bare` | `Nip_pon_bare` | `_` 当通配符用，命中了下划线 |

危害不在于安全（参数化查询已经防住注入），而在于**结果被静默污染**：用户搜
`_` 看到"共 3 个品种"，会以为这是一次有效检索，实际上是查询语法泄漏到语义层。

**修复**：新增 `_escape_like()` 转义 `\`、`%`、`_`（反斜杠必须最先转义），
SQL 端加 `ESCAPE '\'`。修复后 SQL 语义与 Python 字面子串包含**在 7 个探针上
逐一相等**，且与修复前行为可区分（证明修复非空操作）。

注：SQLite `LIKE` 对 ASCII 默认不区分大小写，Python `in` 区分——这是**有意保留**
的差异（用户输品种名不该计较大小写），已在测试中显式记录并单独断言。

## 发现 2（真实缺陷）：无品种名的参考样本可以赢下识别，却对用户不可见

`sample.variety_name` 允许为 NULL，而这样的样本：

* **保留基因型**，因此**参与** `reference_matrix()` 与 `identify()`；
* 不出现在任何品种列表里（`list_varieties` / `counts["varieties"]` 都带
  `WHERE variety_name IS NOT NULL`）。

实测：查询样本基因型等于无名样本 `S3` 时，`identify()` 返回
`best_match = S3, similarity = 1.0, variety_name = None`——页面会显示
"最近匹配：S3（品种 未知）"，而真正同名品种 `Nip_pon_bare` 排在第二（0.75）。
用户看到"未知"却无从知道为什么，也无法在页面上找到 S3。

**这不是臆想的边界**：`database.load_manifest` 第 131 行 `cell()` 把空 TSV 字段
映射为 `None`，而 `variety_name` 只是"必需**列**"而非"必需**值**"。已在
`ManifestProducesEmptyVarietyTests` 中用真实 manifest 走通复现。

**修复**（不加篡改语义的过滤，只让事实可见）：

* 新增 `unlabelled_samples()`，返回无品种名的样本 ID；
* `identify()` 结果新增 `n_unlabelled_reference_samples` 与
  `best_match_lacks_variety` 两个字段；
* 页面在最佳匹配无名时给出明确警告，并在"品种查询"页常驻提示无名样本数量。

**没有**把无名样本从比对中剔除——那会改变实验语义（它们确实是参考基因组）。
本轮只解决"不可见"这一可观测性问题。

## 自己犯的错误（记录以免重犯）

1. 写测试时把期望值写错了两处：断言搜 `_` 应返回 `[]`、搜 `N_p_pon_bare` 应
   命中 `Nip_pon_bare`。**代码是对的，期望是错的**——`Nip_pon_bare` 确实含有
   下划线和 `p`，字面语义下命中是正确行为。改用"与 Python 字面包含逐一相等"
   这一不变量重写，比逐个硬编码期望更可靠。
2. 反向测试最初用 `spec_from_file_location` 直接加载突变副本，触发
   `ImportError: attempted relative import with no known parent package`——
   被审计模块使用相对导入，突变副本必须注册到 `ricevar_id` 包下。
3. 页面提示文案把 `%%`-格式化与 Markdown 反引号混用，`_` 会被 Markdown 当
   斜体标记。已改为明确说明"下划线"，不再用反引号包 `_`。

## 反向验证

`tests/test_dbquery_input_safety_reverse.py`（6 项，全部通过）：

* 先断言补丁锚点存在（否则突变是空的）；
* 把 `find_variety` 还原成拼接版 → `%` / `_` 通配符泄漏**重现**；
* 断言突变版与修复版在 `%`、`_`、`N_p_pon_bare` 三个输入上差异**恰好符合预期**
  （证明测试有鉴别力，而非两边都过）；
* 移除两个标记字段 → 页面再也拿不到任何线索判断最佳匹配是否无名。

## 验证状态

| 项目 | 结果 |
|---|---|
| 单元测试 | **137 项通过**（8 项需 matplotlib 跳过），轮初 115 |
| 新增测试 | `test_dbquery_input_safety.py` 16 项、`..._reverse.py` 6 项 |
| 范围静态检查 | **105/105**（轮初 100） |
| 阶段顺序 / 论文占位符 / round1 | 全部 exit 0 |
| shell 静态分析 `--strict` | 0 发现 |
| `py_compile app/streamlit_app.py` | exit 0 |

## 仍然没有做到的事（不得宣称）

* **页面从未真正渲染过**：本机无 `streamlit`，本轮只验证了它的数据层调用契约
  与语法/AST 接线（`api.unlabelled_samples` / `api.find_variety` /
  `best_match_lacks_variety` / `n_unlabelled_reference_samples` 均已确认被引用）。
  真正的浏览器级验证仍需在 `ricevar` 环境执行。
* 无真实数据库、无真实水稻数据；本轮全部结论来自合成 fixture。
* 项目**实验类任务仍为 0 项 ✅**。
