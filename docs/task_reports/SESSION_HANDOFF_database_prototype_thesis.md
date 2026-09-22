# 会话交接报告：指纹数据库、识别原型、图表层与论文骨架

**范围**：规范 C（`UNDERGRADUATE_TASK_LIST.md`）TASK-036~045、TASK-047/048
**本轮性质**：把**不依赖学校服务器**的部分全部做完并验证
**结论**：代码与验证就绪；**项目仍然没有任何真实实验数值**

---

## 一、本轮新增（全部为 🔶「代码完成、无真实数据结果」）

| 任务 | 产出 | 验证方式 |
| --- | --- | --- |
| TASK-041 | `src/ricevar_id/database.py`、`scripts/build_database.py` | 20 项单测 |
| TASK-043~045 | `src/ricevar_id/dbquery.py` | 同上 + 端到端 7 项 |
| TASK-042 | `app/streamlit_app.py`、`src/ricevar_id/query_input.py` | 14 项解析单测 + 7 项链路单测 |
| TASK-036~040 | `scripts/make_figures.py` | 11 项单测（含真实绘图） |
| TASK-047 | `docs/thesis/THESIS_DRAFT.md`、`PLACEHOLDER_CONVENTIONS.md` | 占位符机械检查 |
| TASK-048 | `docs/thesis/DEFENSE_SLIDES.md` | 同上 |

### 关键设计决定

1. **数据库永不编造行**：可选输入缺失记为 `absent`；`-1` 原样存为 NA 且不插补；
   数据库为空时 `identify()` **抛错**而不是返回偶然匹配。
2. **识别结果必须自带可信度**：每个命中都返回 `n_compared_markers` 与
   `compared_marker_rate`；比较位点少于阈值（默认 50）→ 判为无法识别。
3. **原型无数据即拒绝显示**：数据库不存在时页面只显示报错与建库命令，
   不显示任何示例数值。
4. **图表无数据即不产图**：`make_figures.py` 在结果文件缺失时跳过并说明原因。
5. **论文骨架零虚构数值**：所有结果位为 `{{RESULT: ...}}` 占位符。

---

## 二、本轮发现并修复的真实缺陷

### 缺陷 1：SQLite 版本不兼容（`database.py` 全部写入失败）

本地 Python 3.7.3 自带 SQLite **3.21.0**，而代码用了
`INSERT ... ON CONFLICT(...) DO UPDATE`（需 3.24+），导致
**全部 20 项单测以 `near "ON": syntax error` 失败**。
改为 `INSERT OR REPLACE`（此处语义等价且全版本可用）。

> 若未先跑测试，这批代码会在服务器上以同样方式全线失败。

### 缺陷 2：图中中文标签静默变成方框（`make_figures.py`）

matplotlib 默认 DejaVu Sans **没有 CJK 字形**，中文标题与轴标签会渲染成空方框；
渲染仍"成功"（有效 PNG、退出码 0），只伴随非致命 `UserWarning: Glyph missing`。
即**退出码无法暴露该问题**。

修复：按可用性挑选中文字体（`Microsoft YaHei` → `SimHei` → `Noto Sans CJK SC` →
`Source Han Sans SC` → `WenQuanYi Zen Hei` → `Arial Unicode MS`），并设
`axes.unicode_minus = False`。

**验证**：由独立子代理在隔离 venv 中安装 matplotlib 3.5.3 实际渲染 4 张图；
随后确认告警消失、文件体积显著增大（159KB→215KB 等），并用
`FT2Font.get_charmap()` 逐字校验所用汉字与 `×` 均在字体中。

### 其他修正

- 测试用 `tempfile.TemporaryDirectory()` 因系统临时目录不可写在仓库根生成
  `tmpXXXX` 文件并失败；改为在仓库内 `.tmp/` 下建临时目录。
- 验证脚本中原有一处检查指向错误（在 `dbquery.py` 里找 `compared_marker_rate`，
  而该字段实际由 `fingerprint.py` 的命中字典提供）；已改为检查真实来源。

---

## 三、验证结果（本轮结束状态）

| 检查 | 结果 |
| --- | --- |
| `python -m unittest discover -s tests` | **72 项通过**（7 项因无 matplotlib 跳过），exit 0 |
| 同上，在装有 matplotlib 的 venv 中 | 图相关 11 项**全通过、0 跳过** |
| `scripts/verify_undergraduate_scope.py` | **87 通过 / 0 失败**，exit 0 |
| `scripts/verify_stage_order.py` | **23 通过 / 0 失败**，exit 0 |
| `scripts/verify_thesis_placeholders.py` | 0 处虚构数值，exit 0 |
| `scripts/round1_verify.py` | 28 通过 / 0 失败，exit 0 |
| `py_compile`（全部新增 Python 文件） | exit 0 |

**反向验证**：向论文骨架注入 "识别准确率达到 97.3%" 后，占位符检查
**以 exit 1 报出两处并给出文件行号**，随后文件已还原。
即该检查确实有效，而非恒过。

---

## 四、硬阻塞（未变）

1. 学校服务器**调度器未知**（SLURM / PBS / 直接 shell）
2. `www.ebi.ac.uk` 网络可达性未知
3. 存储配额未知（面板清单声明 334.71 GiB）
4. `server/00_probe.sh` **从未在服务器上运行**
5. **没有任何 FASTQ 被下载**；无真实 QC / 比对 / 联合 calling / 降采样 / 识别
6. 本地**无可用 Bash**（WSL 被拒），`bash -n` 与真实 bcftools/samtools 命令
   **仍未验证**

因此：**至今没有识别准确率、ROC/AUC、最低可用深度的任何真实结论。**

---

## 五、下一步

**A. 本机可继续做（不依赖服务器）**
- 用 `Pilot` 设计文档补齐论文的文献综述章节（`{{CITE: ...}}` 位）
- 把 `docs/server_admin_questions.md` 精简成一页可直接发给管理员的版本

**B. 必须等服务器**
1. 管理员回答 `docs/server_admin_questions.md` 或运行 `server/00_probe.sh`
2. 上传 `server/` + `data/metadata/server/pilot_smoke1.tsv`
3. 单样本端到端跑通（下载→校验→QC→比对→calling）
4. 扩到 `pilot_smoke5.tsv`，复核 QC 与 calling
5. 跑 Pilot 30
6. **仅在 Pilot 内**冻结 marker 与阈值 → `07_identify.sh` 出闭集深度曲线
7. 独立面板 25 份 → **仅用于开放集拒识**

**C. 结果到手后**
- `python scripts/build_database.py --matrix ... --manifest ... --per-query ...`
- `python scripts/make_figures.py --analysis-dir analysis --out-dir figures`
- 用真实数值替换论文与 PPT 中的 `{{RESULT: ...}}`

---

## 六、诚实边界（不得在论文/答辩中越界）

- Pilot 六个深度是**同批样本降采样得到的技术重复**，只能支撑**闭集**
  Top-1/Top-5 结论，**不是**独立同品种样本的准确率。
- 零品种重叠的独立面板**只能评估开放集拒识**，不能用来声称
  "独立同品种识别准确率"。
- 面板 FASTQ 总量 334.71 GiB 是**清单声明值**，不是实际落盘值。
- 当前项目**没有任何 ✅ 级任务**；全部为 🔶「实现就绪、未在真实数据上运行」。
