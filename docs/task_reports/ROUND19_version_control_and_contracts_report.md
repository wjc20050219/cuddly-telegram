# 第十九轮工作报告

> 本轮主题：**版本控制从无到有**，以及由此暴露的一类"承诺失真"缺陷。
> 全程未产生任何实验数据；服务器仍不可用，真实数据工作依旧阻塞。

## 1 环境复核（先验证旧结论，再动新东西）

本轮开场先复核了过去十几轮反复引用的几条"阻塞结论"，
结果发现其中一条**已经不再成立**：

| 项 | 上轮结论 | 本轮实测 | 结论 |
| --- | --- | --- | --- |
| WSL 可用性 | 不可用 | `bash.exe -c "echo OK"` → 退出码 **1** | 仍阻塞 |
| `wsl_recovery.log` | 不存在 | 仍不存在 | 用户未运行恢复脚本 |
| `git` 可执行文件 | 全盘无 `git.exe` | 仍无 | 仍阻塞 |
| `logs/probe_summary.tsv` | 不存在 | 仍不存在 | 探测未运行 |
| **PyPI 可达性** | **假定不可安装** | **`pip download` 成功** | **旧结论错误** |
| `.git` | 不存在 | 不存在（本轮建立） | 本轮的起点 |

**教训**：一个长期阻塞可能在环境变化后自行解除。连续 13 轮把"装不了依赖"
当作既定事实，而它其实从未被真正重测过。凡是要在报告里重述的阻塞，
都应在本轮重新验证一次——成本极低，收益是避免在错误前提下做规划。

## 2 主要工作

### 2.1 建立版本控制（消除"改坏了无法回滚"的风险）

本机**没有任何 `git` 可执行文件**（已全盘检索 `git.exe`）。
这是本项目长期存在的真实风险：此前曾用 PowerShell 覆写文件导致
中文内容损坏且**无备份可恢复**，只能靠对话记录人工还原。

本轮发现 PyPI 可达后，改用纯 Python 实现 `dulwich`：

- `pip install --target .tools\pylibs dulwich`（→ dulwich 0.22.1）
- 新增 `scripts/vcs.py`，提供 `status / add / commit / log`
- `Repo.init(ROOT, mkdir=False)` 建立 `.git`
- 首个提交 `e99642e`：**257 个 blob**
- `.gitignore` 增加 `.tools/`（本机依赖，可由 requirements 重建）

**独立校验**：不信退出码，直接遍历提交树逐一确认关键文件在库内，
且 `.tools/`、`.tmp/`、`xml_cache`、`*.fastq/*.bam/*.vcf/*.sra` 均**不在**库内。

### 2.2 一个"成功但为空"的提交（本轮最值得记录的缺陷）

第二次提交返回退出码 0，输出 `committed edc35dc...`，看起来完全正常。
但对**父子树做内容对比**后发现：`added` 只有 1 个文件，`changed` 为 **空**——
一页纸的修复与 `vcs.py` 自身的修复**都没有进库**。

根因：`dulwich` 的 `porcelain.commit` **不会**把已跟踪文件的工作区改动
写入索引。只 `add` 未跟踪文件时，会生成一个**有合法 SHA 却不含任何修改**的提交。

> 这比"提交失败"危险得多：失败会报错，而它会**安静地**给出一个 SHA，
> 让人以为改动已经安全保存。若不是主动对比树内容，这个空提交会被当成成功。

修复后，第三次提交正确记录了两个被修改文件。并由
`tests/test_vcs_script.py` 锁定"提交内容必须包含改动"这条不变式。

同时修掉 `GitStatus` 字段类型不一致的问题：`untracked` 是 `list`，
而 `unstaged/staged` 在不同版本间可能是 `list` 也可能是 `dict`。
我最初按 `dict` 迭代，拿到的是**整数下标**，
直到 `porcelain.add` 抛 `TypeError: expected str ... not int` 才暴露。

### 2.3 一页纸的"承诺失真"（第 22 项缺陷）

`docs/server_request_onepager.md` 是**发给外部管理员**的材料，
它写的每一句"脚本会/不会做什么"，都是对第三方作出的承诺。

原文写道：

> ❌ 不产生大于 30 MB 的下载。**全程只读**，唯一的写操作是在当前目录下建 `logs/`。

但 `server/config.sh` 的 `init_dirs()` 实际创建 **13 个子目录**：

```
metadata/ raw/ qc/ bam/ vcf/ depth/ kmer/ sim/ export/ logs/
reference/ markers/ analysis/
```

外加临时目录 `$TMPDIR/ricevar_tmp`；默认根目录是 `$HOME/ricevar`，
**不是**"当前目录"。管理员正是据此判断是否授予写权限，
所以这是承诺失真，性质比内部文档写错更严重。

修复：如实披露真实写入范围、默认根目录、以及"删除 `$RV_ROOT` 即可完全清除"。
并新增 `tests/test_admin_onepager_contract.py`（**17 项**）锁定：
资源数字可回源、四个必答问题齐全、工具数与脚本循环一致、
下载上限与 `TEST_BYTES` 一致、以及写入范围与 `init_dirs` 逐个对齐。

### 2.4 论文引用了两张不存在的图（第 23 项缺陷）

第 3 章引用了 `figures/fig_snp_density.png` 与 `figures/fig_prototype.png`，
但 `scripts/make_figures.py` **根本不产出这两张**；
反过来，真正承载核心结果的 `fig_pca.png` 与 `fig_confusion.png`
**一次都没被引用**。

即"做了的图没写进论文，写进论文的图不存在"——双向都错。

修复：改为引用 6 张真实图，新增 §3.9 给出"图 → `--only` 命令"对应表，
并**明说**哪两张图（质控图、Streamlit 截图）在服务器可用前做不出来，
而不是留一个指向空产物的占位。

`tests/test_thesis_figure_references.py`（**7 项**）双向锁定这条不变式。

### 2.5 一条"本身过期"的测试

`test_appendix_availability.py` 曾断言"工作目录下**没有** `.git`"。
这在写它的那轮是**事实**，但本轮建立仓库后，这条断言自己成了过期陈述。

改为**双向一致**：磁盘上有 `.git` 就必须说有，没有就必须说没有。
附录 E 也据此改写，并如实记录"已建立本地仓库，但**未推送远程、未打 tag、未归档 DOI**"。

## 3 变异测试（证明守卫真的能失败）

| # | 变异 | 期望 | 结果 |
| --- | --- | --- | --- |
| 1 | 把一页纸的写入范围改回"唯一的写操作…`logs/`" | 失败 | **GUARDED**（4 项触发） |
| 2 | 把 `fig_snp_density.png` 塞回论文 | 失败 | **GUARDED**（2 项触发） |
| 3 | 还原后重跑 | 通过 | rc=0 |

三次变异均由 Python 施加（PowerShell 的 `[IO.File]::WriteAllText`
在 ConstrainedLanguage 下会被**静默忽略**，曾导致变异跑在未修改的源码上）。

## 4 我自己的错误期望（诚实记录）

1. **断言 `net_ncbi_speed` 字面量存在**——错。该键由 `probe_get ncbi`
   拼成 `net_${name}_speed`，源码里没有拼好的字面量。
   应检查**调用点**而非结果字符串。属"测试写错"，非代码缺陷。
2. **把 `{{FILE:}}` 限定为 `figures/*.png`**——错。该占位符也用于
   `qc/multiqc_report.html` 等其他产物。已放宽为"必须是路径形式"。
3. **假设 `porcelain.commit` 会自动暂存已跟踪文件的修改**——错，
   且正是这个错误假设制造了空提交。

## 5 本轮交付

| 产物 | 说明 |
| --- | --- |
| `scripts/vcs.py` | dulwich 驱动的版本控制（新增，后修复暂存缺陷） |
| `.git` | 本地仓库，**4 个提交**，含 257+ blob 的初始提交（**已过期**：后重建为 `main` 上单一提交，259 个 blob，见 §6 补记） |
| `tests/test_admin_onepager_contract.py` | 17 项，新增 |
| `tests/test_vcs_script.py` | 10 项，新增 |
| `tests/test_thesis_figure_references.py` | 7 项，新增 |
| `docs/server_request_onepager.md` | 修复写入范围承诺（第 22 项） |
| `docs/thesis/THESIS_DRAFT.md` | 修复图表引用 + §3.9 对应表（第 23 项） |
| `docs/thesis/APPENDIX_E_availability.md` | 如实记录版本控制状态 |
| `tests/test_appendix_availability.py` | 改为双向一致断言 |

**全量测试**：`tests/` **34 个文件，465 项通过，9 项跳过**（缺 matplotlib）。
**静态检查**：6 个 `verify_*.py` **全部退出码 0**。

## 6 本轮**没有**做到的事

- **没有产生任何实验结果**。没有任何 recall / Top-1 / 拒识率 / 实测深度数值。
- **服务器探测仍未运行**：`logs/probe_summary.tsv` 依旧不存在，
  因此 `interpret_probe.py` **仍不能**给出任何建议——没有探测就下结论即造假。
- **未推送远程、未打 tag、未归档 DOI**。`.git` 只在本机，磁盘损坏仍会丢失。

> **后续更新（推送完成后补记）**：上面两条已被推翻。仓库已重建为单一干净提交
> （259 个 blob）并推送到 <https://github.com/wjc20050219/cuddly-telegram>
> （分支 `main`），同时排除了 `.learnings/` 与 `docs/methods/_raw/`。
> **仍未打 tag、未归档 DOI**——这两项至今成立。本节其余内容为上轮原始记录，未改动。
- `fig_pca` 与 `fig_confusion` **从未产出过 PNG**（本机无 matplotlib）。
- Streamlit 页面**从未渲染过**。
- `bash -n` 与真实 bcftools/samtools 命令验证**仍未执行**（本机无可用 shell）。

## 7 下一步

1. **用户动作（恢复环境）**：以管理员运行 `fix_wsl.cmd`；若成功，
   本地即可跑完整流程与出图。
2. **用户动作（必需）**：把 `docs/server_request_onepager.md` 发给管理员，
   或上传 `server/` + 清单后运行 `bash server/00_probe.sh`；
   随后 `python scripts/interpret_probe.py --summary logs/probe_summary.tsv` 判读。
3. 探测通过后按既定顺序推进：单样本 → 5 样本 → Pilot 30 → 冻结 marker
   → 深度曲线 → 独立面板拒识。
