# 服务器 Pilot 运行手册（本科版：1 → 5 → 30 份逐级跑通）

- 初建：2026-09-15；本科版修订：2026-09-20
- 目标：用最小代价把「下载 → 比对 → 分型 → 深度 → ulcWGS 模拟 → 导出 → 本机导入」整条链路跑通
- 配套架构文档：`docs/methods/server_local_split_design.md`
- 算力评估：`docs/methods/compute_feasibility_assessment.md`

---

## 一、为什么先跑 Pilot

pilot 的目的**不是出结果，而是排错**。整条流水线涉及 7 个阶段、十几种工具、跨境下载、跨机传输，
如果在 180 份的规模上才发现某个参数写错，重跑代价是几天。用 5 份跑一遍，半天内就能暴露全部问题。

---

## 二、Pilot 样本（已落实的真实公开数据）

规范样本表由 `scripts/build_server_manifests.py` 从冻结面板生成：

- `data/metadata/server/pilot_smoke1.tsv`：1 份最小下载样本，只做全链路冒烟；
- `data/metadata/server/pilot_smoke5.tsv`：5 份，覆盖主要标签的工程测试；
- `data/metadata/server/pilot_manifest.tsv`：正式 Pilot 30 份；
- `data/metadata/server/independent_manifest.tsv`：冻结独立 25 份，最后才运行。

历史 `data/metadata/pilot_samples.tsv` 仅作早期记录，不再作为本手册输入。现行清单的元数据值为：smoke1 2,799,458,993 bytes；smoke5 24,895,801,496 bytes（约 23.18 GiB 压缩 FASTQ）。下载时重新查询 ENA、匹配冻结清单文件，并记录 MD5、SHA256、URL、字节数与时间。

> 单样本试跑直接使用 `pilot_smoke1.tsv`；不要手工裁表。

---

## 三、需要上传到服务器的文件

```
server/                       ← 整个目录
├── config.sh
├── 00_probe.sh
├── 01_setup_env.sh
├── environment.server.yml
├── 02_download.sh
├── 03_align.sh
├── 04_variant_depth.sh
├── 04_joint_snp.sh
├── prepare_marker_targets.sh
├── 05_simulate.sh
├── 06_export.sh
├── 07_identify.sh
├── build_matrices.py
└── run_all.sh

data/metadata/server/*.tsv
```

上传命令（本机执行；按实际 WSL 路径调整）：

```bash
rsync -avP /mnt/d/dsh/RiceVar-ID/server/ user@server:~/ricevar/server/
rsync -avP /mnt/d/dsh/RiceVar-ID/data/metadata/server/*.tsv user@server:~/ricevar/metadata/
```

> **上传前的本机预检**（本机没有可用 Bash，WSL 报 `E_ACCESSDENIED`，因此
> `bash -n` 跑不了；用 Python 静态分析兜底）：
>
> ```bash
> python scripts/verify_shell_static.py            # 6 类检查，期望 0 发现
> python tests/test_shell_static_detects.py        # 反向验证：注入缺陷必须被检出
> ```
>
> 这两步**不能替代**服务器上的真实执行验证，只能提前拦住未定义变量、
> 未闭合命令替换、并行 mktemp 冲突、关键命令失败被吞、阶段未被调度这几类问题。
> 到服务器后**仍须**先跑 `bash -n` 与单样本冒烟。

---

## 四、操作流程（五步）

### 第 0 步：探测服务器（5 分钟，**先跑这个**）

```bash
cd ~/ricevar/server
bash 00_probe.sh
```

它回答四个关键问题：**有没有调度器 / 外网能不能下 / 有多少存储 / 有哪些软件**。

看报告末尾的"自动判定建议"：
- ENA 速度 < 1 MB/s → 设 `RV_MIRROR=1`，并考虑本机代下
- 有 `sbatch` → `run_all.sh` 会自动切换成 Slurm 提交模式
- HOME 可用空间 < 50 GB → 设 `RV_ROOT=/scratch/$USER/ricevar`

### 第 1 步：建环境

```bash
bash 01_setup_env.sh          # 无 conda 会自动装 Miniconda
```

耗时：有 conda 约 5–15 分钟；需装 Miniconda 再加 5 分钟。
**国内服务器建议**：`RV_MIRROR=1 bash 01_setup_env.sh`（走 TUNA 镜像，快很多）

### 第 2 步：跑全流程

```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate ricevar
tmux new -s ricevar                     # 防断线
source ~/miniconda3/etc/profile.d/conda.sh && conda activate ricevar
RV_SAMPLES="$HOME/ricevar/metadata/pilot_smoke1.tsv" \
  bash run_all.sh 02 2>&1 | tee logs/run_smoke1.log
```

单样本只验证下载/QC/比对/bcftools/降采样链路，不产出正式 marker。通过后改为 `pilot_smoke5.tsv`；5 份通过并审查 QC 后，才改为 `pilot_manifest.tsv`。

### 第 3 步：看导出包

```bash
du -sh ~/ricevar/export
cat ~/ricevar/export/README.md
head -n 3 ~/ricevar/export/MANIFEST.tsv
```

### 第 4 步：传回本机

本机（WSL 内）执行：

```bash
bash /mnt/d/dsh/RiceVar-ID/local/import_export.sh user@server:~/ricevar/export
```

会自动 rsync + SHA256 校验 + 打印矩阵形状。**校验通过才算跑通。**

---

## 五、预期耗时与体积（Pilot 5 份）

| 阶段 | 耗时估算 | 产物 | 体积 |
| --- | --- | --- | --- |
| 00 probe | < 5 min | 报告 | KB |
| 01 setup_env | 5–20 min | conda 环境 | ~2 GB |
| 02 download | 取决于带宽，待实测 | FASTQ | smoke5 清单约 23.18 GiB |
| 03 align | 待学校服务器实测 | CRAM | 未预先断言 |
| 04 depth + joint SNP | 1–3 h | 联合 VCF + BED | ~1 GB |
| 05 simulate | 1–2 h（6 档 × 3 重复 × 5 样本） | 降采样深度 BED + seed manifest | ~200 MB |
| 06 export | 5–20 min | **export/** | **~50–100 MB** |
| 合计 | **待 smoke1/smoke5 实测** | 过网 | 仅传导出特征，大小待实测 |

> 对比：如果按常规做法把 CRAM 传回来，过网量是 **5 GB**；
> 如果连下采样 BAM 一起传，是 **数百 GB**。这就是"特征矩阵过网"设计的意义。

---

## 六、常见故障与处理

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `00_probe.sh` 里 ENA 测速 FAIL | 服务器无外网 | 改本机下载后上传；或申请网络白名单（`ftp.sra.ebi.ac.uk`、`www.ebi.ac.uk`） |
| `01_setup_env.sh` 求解很久不结束 | 通道优先级/flexible | 脚本已设 `channel_priority strict`；仍慢则加 `RV_MIRROR=1` |
| `bwa-mem2 index` 被 OOM killer 杀 | 内存 < 12 GB | 分区内存不够时改用 `bwa index`（慢但省内存），或申请大内存节点 |
| `samtools sort` 报内存不足 | `SORT_MEM` 太大 | `SORT_MEM=512M PAR=2 bash run_all.sh` |
| 下载频繁中断 | 跨境链路不稳 | 脚本已带 `--retry 3 -C -`；可改用 `aria2c -x8` |
| Slurm 作业被墙钟杀掉 | 默认时限 | `SLURM_TIME=168:00:00 bash run_all.sh` |
| rsync 校验失败 | 传输中断 | 重跑 `import_export.sh`（带 `--checksum`，会补齐差异文件） |

---

## 七、Pilot 跑通后的扩展路径

| 步骤 | 操作 | 说明 |
| --- | --- | --- |
| 扩到 5 份 | `RV_SAMPLES=.../pilot_smoke5.tsv bash run_all.sh 02` | 验证并行、联合 VCF 与 QC |
| 扩到 Pilot 30 | `RV_SAMPLES=.../pilot_manifest.tsv RV_REPS=5 bash run_all.sh 02` | 本科正式 Pilot；先审查 5 份结果 |
| 冻结 marker | 用 `scripts/select_snp_markers.py --panel-role pilot` 从 Pilot 联合 VCF固定嵌套 500/1000/2000 位点 | 禁止查看独立面板后重选 |
| 低深度定点分型 | 用 2000 位点 VCF 执行 `prepare_marker_targets.sh`，再重跑 `05_simulate.sh` | 500/1000 是排序前缀；代码仍需真实服务器验证 |
| 识别评估 | `bash 07_identify.sh`（或 `bash run_all.sh 07`） | 输出 recall / Top-1 / Top-5 / 拒识；**闭集**技术重复结果 |
| 相似度全矩阵 | `python scripts/export_similarity_matrix.py --database database/ricevar_id.sqlite --method ibs --out data/processed/similarity/pilot_pairwise_ibs.tsv` | 供热图/PCA；`per_query.tsv` 只有最佳匹配，构不成矩阵 |
| 出图 | `python scripts/make_figures.py --analysis-dir <结果目录> --out-dir figures --similarity-matrix <上一步的 _matrix.tsv>` | 缺文件即跳过该图，绝不用示意数据代替；`--only pca` 生成主成分图 |
| 独立 25 | 最后使用 `independent_manifest.tsv` | 只作开放集拒识；品种零重叠 |

> **相似度方法（须冻结并写入论文）**：`07_identify.sh` 的 `RV_METHOD` 默认 `ibs`，
> 可用 `RV_METHOD=hamming bash 07_identify.sh` 覆盖。方法选择会**改变 Top-1 结论**
> （同一 query 在 IBS 与 Hamming 下可给出不同首位品种），因此必须在看到结果前定好，
> 并按实际使用方法报告。`compare_varieties`（品种两两比较）与本阶段共用同一实现，
> 两处相似度处于同一尺度；若改方法，两处必须同时改，不得混用。详见
> `docs/methods/snp_evaluation_design.md` §4.2。

> 断点续跑可用阶段名或编号：`bash run_all.sh 04` 从 `04_variant_depth` 开始，
> `bash run_all.sh 07` 只跑识别评估。编排按下标而非字符串比较，避免跳过 `04_joint_snp`。

---

## 八、当前状态与前置条件

- 🔶 基础流水线脚本和 Snakemake 薄骨架已就绪（静态实现；真实服务器未验证）
- ✅ Pilot 样本表已用 ENA API 落实为真实可下载数据
- ✅ 本机侧导入脚本已就绪
- ⚠️ **尚未在真实服务器上执行过**（服务器信息待确认），首次运行请务必先跑 `00_probe.sh`
- ⚠️ 脚本语法自检会在 `run_all.sh` 启动时自动执行；本机 WSL 目前卡死，无法在本机做 `bash -n` 预检
- ⚠️ 本机 WSL 需先恢复（见 `docs/task_reports/TASK-002_report.md` 第五节），否则无法运行 `local/import_export.sh`
