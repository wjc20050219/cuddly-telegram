# 本科版范围迁移与无 FASTQ 准备报告

> 日期：2026-09-20  
> 性质：范围、元数据、方法预注册与工作流静态加固；不是测序实验报告。

## 完成本轮内容

1. 建立现行规范 C：`docs/UNDERGRADUATE_SCOPE.md` 与 `UNDERGRADUATE_TASK_LIST.md`；
2. 更新 `docs/TASK_NUMBERING.md`，明确 C 为现行编号，A/B 保留为历史；
3. 将必做路线收敛为 SNP，固定六档深度与 500/1000/2000 marker；
4. 写入开放集与数据泄漏防线：零重叠独立 25 仅能验证拒识，不能冒充同品种独立 Top-1；
5. 建立参考基因组选择与偏倚评估方案；
6. 从冻结面板确定性生成 1/5/30 份 Pilot 与独立 25 份服务器清单；
7. 加固服务器脚本：按表头读取 manifest、保守线程默认值、并行子进程函数导出、conda 激活、FastQC、MultiQC、完整 SHA256 参考/下载记录、联合 SNP calling、修正下载日志 run 变量、修正降采样 seed/fraction 与深度估计；
8. 加入 Pilot-only SNP QC/嵌套 marker 筛选、固定等位基因低深度分型和 IBS/Hamming/Jaccard/Top-k 算法骨架；
9. 加入 Snakemake 薄编排骨架与本科版静态/数据/合成单元验证。

## 发现并修复的关键方法问题

### 1. variant-only 单样本 VCF 不可直接拼正式矩阵

旧 `build_matrices.py` 以位点最多的单样本 VCF 为基准，其他样本中未出现的位点记为 missing。对只输出变异位点的 VCF，“未出现”可能是 0/0，也可能是无覆盖，无法区分。正式路线改为 Pilot 多样本联合 calling，并导出联合 VCF。

### 2. 下载日志使用了未定义的 `RUN`

`fetch_one` 在子流程中写 `$RUN`，但实际局部变量名是 `run`。现改为显式传参，确保 accession 日志不为空。

### 3. `samtools view -s` 参数拼接错误

旧写法把整数 seed 与已经含 `0.` 的比例拼成类似 `1001.0.050000` 的非法字符串。现改为 `INT.FRAC`，并对 fraction≈1 单独走不抽样路径。

### 4. 备用深度估计重复乘 2

`samtools view -c` 已逐条计算两端 alignment，旧代码再乘 2 会高估深度。现改为 `reads × read_length / genome_size`。

### 5. 深度矩阵路径约定不一致

mosdepth 输出位于 `depth/w<size>/<sample>.regions.bed.gz`，旧矩阵代码只查找 `dir/<sample>/<pattern>`。现同时支持直接文件与子目录两种布局，并修正模拟数据软链接名。

## 仍未完成

- 学校服务器 probe；
- 参考基因组与 FASTQ 的学校服务器下载；
- 任何真实 FastQC/fastp/mapping/SNP/降采样；
- marker、指纹、准确率、ROC/AUC、图表、SQLite、Streamlit、论文结果；
- 服务器端脚本的真实环境验证（当前仅静态与本机 Python 数据核验）；
- 冻结 marker 后的低深度定点 SNP 分型真实验证（代码骨架已加入 `05_simulate.sh`，但没有真实 marker/BAM，不能产出识别率）。

## 本轮新增：识别评估层（`07_identify.sh`）

在原有骨架之上补齐了"低深度 VCF → recall / 识别率 / 拒识"这一整段，使主线从数据准备一直贯通到可计算的指标：

1. `src/ricevar_id/genotypes.py`：读取 Pilot 基因型矩阵与低深度定点 VCF；
   `project()` 把 query 对齐到冻结 marker 集——未覆盖位点记 missing（不是 0/0），
   出现冻结集之外的位点直接报错；支持 `min_dp`/`min_gq` 低证据过滤。
2. `scripts/evaluate_identification.py`：输出 `per_query.tsv`（逐 query 的 marker recall、
   genotype concordance、最佳匹配、比较/差异位点数、拒识状态）与 `summary.json`
   （按深度聚合的 recall、Top-1/Top-5、accept rate，附输入 SHA256 与全部参数）。
3. `server/07_identify.sh`：从 `marker_genotype_manifest.tsv` 收集 VCF，生成真值表，
   对 500/1000/2000 三个 marker 数分别评估并汇总 `identification_by_depth.tsv`。
4. `server/06_export.sh`：导出 `markers/` 与 `identification/`。

### 修复的两个真实缺陷

1. `GenotypeMatrix.project` 用 query 自己的位点顺序建立列映射，导致投影后数值错列。
   该缺陷会让所有低深度指纹被静默打乱；合成测试已捕获并修复。
2. `run_all.sh` 用字符串比较判断"是否到达起始阶段"。由于
   `"04_joint_snp" < "04_variant_depth"`，从 04 续跑会**跳过联合 SNP calling**。
   现改为按数组下标判断，并新增 `scripts/verify_stage_order.py` 固化该行为。

### 评估口径（必须如实写入论文）

- query 是 Pilot 样本自身 CRAM 的降采样技术重复，属**闭集**结果；
- 同时报告 `top1_correct_sample`（能否回到原样本）与 `top1_correct_variety`（品种级准确率）；
- `--min-compared` 默认 50，比较位点不足时 IBS 记 NaN，不制造虚假匹配；
- 独立 25 面板与 Pilot 品种零重叠，只能做**开放集拒识**，不能当作同品种独立 Top-1。

## 验证记录

- `scripts/verify_undergraduate_scope.py`：60 项通过，0 失败；
- `scripts/round1_verify.py`：28 项通过，0 失败；
- `scripts/verify_stage_order.py`：23 项通过，0 失败；
- `python -m unittest discover -s tests -v`：20 项发现，18 项执行通过，2 项因本机 Python 缺 `numpy/pandas` 明确跳过；
- Python `py_compile`：本轮新建/修改 Python 模块全部通过；
- 尚未完成：Linux Bash 语法和 bcftools/samtools 命令实跑（当前 WSL 不可访问，须在学校服务器 smoke1 验证）。

## 下一步固定顺序

`00_probe.sh` → `pilot_smoke1.tsv` → `pilot_smoke5.tsv` → 审查日志/QC → `pilot_manifest.tsv` → Pilot 内冻结 marker/阈值 → `independent_manifest.tsv` 开放集验证。
