# 第 2 轮报告：Shell 静态分析（补上本机唯一可验证的空白）

**目标轮次**：goal round 2/40
**本轮主题**：本机无 Bash ⇒ `server/*.sh` 从未被任何工具检查过；本轮补上，
并**发现并修复 3 处真实缺陷**。
**性质**：不依赖服务器；**没有产生任何实验结果数值**。

---

## 一、为什么做这件事

复核规范 C 后，本机可做的工作只剩一块真正没碰过的：`server/` 下 12 个 shell 脚本
（共约 60 KB）**从未通过 `bash -n`、shellcheck 或任何解析器**。

本机现状（本轮重新实测，非沿用旧结论）：

```
bash  -> C:\Windows\system32\bash.exe   （WSL 启动器）
& bash.exe -c "..."  ->  Bash/Service/CreateInstance/E_ACCESSDENIED
git   -> NOT FOUND
conda -> NOT FOUND
```

即 WSL 服务本身被拒，**本机确实没有任何可用 Bash**。`bash -n` 无法执行，
脚本的语法与变量错误会一路带到学校服务器才暴露——而那时排查成本最高。

因此本轮写了一个 Python 静态分析器，专门针对**本项目已经踩过的缺陷类别**。

---

## 二、产出

| 文件 | 作用 |
| --- | --- |
| `scripts/verify_shell_static.py` | 6 类 shell 静态检查，`--strict` 有发现即 exit 1 |
| `tests/test_shell_static_detects.py` | **反向验证**：注入 4 类缺陷，必须被检出 |

### 检查项

1. **未定义变量** —— 函数作用域感知，识别 `local`、`read`、`for`、
   `${X:-default}`、`declare -a`、`${arr[@]}`，并排除 bash 内建变量与被 source 的
   `/etc/os-release` 变量。
2. **未闭合命令替换** —— 真正的 `$(` 配对栈，跳过单引号与 heredoc 正文。
3. **并行上下文中的 mktemp** —— 模板是否含 `$!` 或样本名。
4. **关键命令失败保护** —— 仅当 bcftools/samtools/bwa-mem2/fastp/mosdepth
   等处于**命令位置**时才算调用（`log` 消息里提到不算）。
5. **heredoc 内 python 导入** —— 防止引用 conda 环境没装的模块。
6. **阶段覆盖** —— `run_all.sh` 的 `STAGES` 与 `server/*.sh` 双向对齐，
   有脚本没被调度即报错。

---

## 三、发现并修复的真实缺陷（3 处，均在 `server/05_simulate.sh`）

这三处是**同一类 bug**：循环体在失败时"什么都不产出"，于是**失败的轮次
和成功的轮次在清单里无法区分**。

### 缺陷 1：`mosdepth` 无保护（第 98 行）

```bash
# 修复前
mosdepth ... "$tbam" 2>/dev/null
if [ -s "$f" ]; then ... 记录进清单 ... fi
```

mosdepth 失败 ⇒ 没有 BED 文件 ⇒ `if` 静默跳过 ⇒ **该轮次既没进清单、也没报错**。
后果：深度梯度上会出现一个看不见的洞，最终准确率曲线是**基于比声称更少的重复数**
算出来的，而论文里不会体现这一点。

修复：失败时明确 log `mosdepth 失败，本轮不计入清单` 并 `continue`。

### 缺陷 2：`samtools fastq | gzip` 无保护（原第 138 行，KMC 分支）

```bash
# 修复前
samtools fastq ... "$tbam" 2>/dev/null | gzip -1 > "$fq"
for K in $RV_KMERS; do kmc ... "$fq" ... || log "KMC k=$K 失败"; done
```

导出失败 ⇒ **空 FASTQ** ⇒ KMC 报错，但错误信息指向 KMC，**掩盖了真正的失败点**。

修复：检查管道状态与非空，失败时明确 `fastq 导出失败，跳过 KMC`，不进入 KMC 循环。

### 缺陷 3：`bcftools index` 无保护（原第 122 行，定点分型分支）

```bash
# 修复前
[ -s "$gvcf" ] && bcftools index -t "$gvcf"
...
if [ -s "$gvcf" ]; then ... 写入 GENO_MANIFEST ... fi
```

索引失败 ⇒ VCF 存在但**不可按区间读取** ⇒ 仍被写进分型清单 ⇒
下游 `07_identify.sh` 的定点分型会在真实数据上批量失败。

修复：`if ! [ -s "$gvcf" ] || ! bcftools index -t "$gvcf"; then` 明确记录并清掉
不完整产物，绝不进清单。

> **这三处都不是我预先假设的"语法错误"，而是分析器跑出来的**。它们不会导致脚本
> 崩溃，只会让结果**静静地少几轮**——正是最该在本机拦下的那类问题。

---

## 四、关于误报：先降噪，再相信

第一版分析器报了 **44 处**，**全部是误报**：

- 把 `local sid="$1"`、`while read sid depth rep` 的参数当未定义变量；
- 把 `case` 分支、`awk` 体、`${W}bp` 里的括号算进配对；
- 把 markdown heredoc 里的反引号当命令替换（`06_export.sh` 整段文档）；
- 把 `log "...使用 fastp..."` 里的工具名当命令调用。

逐项对照真实脚本收紧后降到 **0 发现**。这一步是必要的：
**44 处误报的分析器会被直接忽略，0 发现的未调优分析器则会漏掉上面 3 个真 bug。**

### 反向验证（关键）

一个只会打印"0 发现"的检查器毫无价值。因此
`tests/test_shell_static_detects.py` 把真实脚本复制到临时目录，**注入**：

| 注入 | 结果 |
| --- | --- |
| `echo "$RV_TOTALLY_MISSING_VAR"` | ✅ 检出"未定义变量" |
| `BROKEN="$(echo hi"` | ✅ 检出"命令替换未闭合" |
| `fastp -i x -o y`（无保护） | ✅ 检出"未见失败保护" |
| 新增 `99_orphan.sh` 且不加入 `STAGES` | ✅ 检出"阶段未被调度" |

并断言**未注入时基线为 0 发现**。4/4 检出，基线干净。

---

## 五、验证结果（本轮结束）

| 检查 | 结果 |
| --- | --- |
| `python -m unittest discover -s tests` | **72 项通过**（7 项需 matplotlib 跳过），exit 0 |
| `scripts/verify_undergraduate_scope.py` | **94 通过 / 0 失败**（本轮 87→94），exit 0 |
| `scripts/verify_stage_order.py` | 23 通过 / 0 失败，exit 0 |
| `scripts/verify_thesis_placeholders.py` | 0 处虚构数值，exit 0 |
| `scripts/round1_verify.py` | 28 通过 / 0 失败，exit 0 |
| `scripts/verify_shell_static.py --strict` | **0 发现**，exit 0 |
| `tests/test_shell_static_detects.py` | 4/4 注入缺陷被检出，exit 0 |

新增 7 项 scope 检查覆盖：分析器存在、`REVIEWED_UNGUARDED` 基线显式且带理由、
heredoc 跳过、两类检查词存在、反向测试存在、以及上面 3 处修复的**字符串锚定**
（防止以后被改回去）。

---

## 六、诚实边界（**必须继续保持**）

- shell 静态分析**不能替代**服务器上的 `bash -n` 与真实执行。
  工具调用是否正确（flag 拼写、参数语义、版本差异）**仍未验证**。
- `REVIEWED_UNGUARDED` 里 15 条是**人工判断为可接受**的无保护命令
  （多为 index/faidx/QC 报告，失败会让下游读取器明确报错）。
  它们是**已复核的基线**，不是"自动通过"。
- 项目**仍然没有任何 ✅ 级实验任务**，**没有任何真实数值**：
  无准确率、无 ROC/AUC、无最低可用深度、无真实 marker、无真实 FASTQ。

---

## 七、硬阻塞（未变，需人工动作）

1. 调度器未知（SLURM / PBS / 直接 shell）
2. `www.ebi.ac.uk` 可达性未知
3. 存储配额未知（面板清单 334.71 GiB 为**声明值**）
4. `server/00_probe.sh` 从未在服务器运行
5. 本机无 Bash（已用静态分析部分兜底）

**唯一人工动作**：把 `docs/server_admin_questions.md` 交给管理员并运行
`server/00_probe.sh`。

---

## 八、下一步

本机可做的部分**已接近穷尽**。下一轮若仍在等服务器，候选：

- `docs/thesis/THESIS_DRAFT.md` 的 `{{CITE: ...}}` 文献位——**但**现有 11,040 条
  出版物记录带 `[MATCH]/[PLAUSIBLE]/[WEAK]/[?]` 前缀，**需人工核验后才能引用**，
  批量填充会引入不可验证的引用，本轮**刻意未做**。
- 把 `docs/server_admin_questions.md` 压成一页可直接发管理员的版本。

真正推进主线仍必须等服务器。
