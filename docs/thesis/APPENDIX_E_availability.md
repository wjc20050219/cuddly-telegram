# 附录 E　代码与数据可获得性

> 本附录说明**代码如何获取与运行**、**数据从哪里来**、以及
> **哪些内容可以复现、哪些还不可以**。
> 最后一点尤其重要：本项目的实验尚未执行，因此本附录**不声称**结果可复现。

## E.1 代码

| 项目 | 说明 |
| --- | --- |
| 项目名 | RiceVar-ID |
| 工作目录 | `D:\dsh\RiceVar-ID`（开发机，Windows 11 + WSL2） |
| 版本控制 | **已建立本地 Git 仓库**（见 E.1.1）；`.gitignore` 见 E.4 |
| 许可证 | {{TODO: 待定（若公开需明确许可证，否则默认保留所有权利）}} |
| 归档 DOI | {{TODO: 待定（建议投稿/答辩前打 tag 并归档到 Zenodo 获取 DOI）}} |

**重要说明**：本项目已建立**本地** Git 仓库，但**尚未推送到任何远程托管平台**，
也**尚未归档**。把它当作"已经托管到某处"是不正确的。

### E.1.1 版本控制的实际状态（如实说明）

开发机上**没有可用的 `git` 可执行文件**（全盘检索无 `git.exe`）。
为获得可回滚的提交历史，本项目改用纯 Python 实现
`dulwich` 驱动 `.git`，驱动脚本为 `scripts/vcs.py`
（依赖安装在本机 `.tools/pylibs`，该目录被 `.gitignore` 排除）。

| 项 | 实际情况 |
| --- | --- |
| 仓库位置 | 工作目录下的 `.git`（本地，无远程） |
| 操作方式 | `python scripts/vcs.py status \| add \| commit \| log` |
| 提交者 | `RiceVar-ID <ricevar@localhost>` |
| 被排除的内容 | FASTQ/BAM/CRAM/VCF、`reference/*.fa*`、`.tools/`、`.tmp/` 等（见 E.4） |
| 未做的事 | **未推送远程**、**未打 tag**、**未归档 DOI** |

> **一个值得记录的坑**：`dulwich` 的 `porcelain.commit` **不会**自动把
> 已跟踪文件的改动写入索引。只 `add` 未跟踪文件时，会产生一个**有合法 SHA、
> 却不含任何修改**的提交——看起来提交成功了，实际改动全丢。
> 本项目确实发生过一次，靠对比父子树才发现。`scripts/vcs.py` 现已修正，
> 并由 `tests/test_vcs_script.py` 锁定"提交内容必须包含改动"。

## E.2 代码结构

```
RiceVar-ID/
├── server/           # 服务器端流水线（bash，按 NN_ 前缀排序执行）
│   ├── config.sh         # 所有路径与参数集中于此
│   ├── run_all.sh        # 总控；支持按阶段续跑
│   ├── 00_probe.sh       # 环境自检（必须先跑）
│   ├── 01_setup_env.sh   # conda 环境与工具安装
│   ├── 02_download.sh    # FASTQ 下载（带校验）
│   ├── 03_align.sh       # 参考准备 + FastQC/fastp + 比对 + CRAM
│   ├── 04_joint_snp.sh   # 联合 SNP calling 与规范化
│   ├── 04_variant_depth.sh
│   ├── 05_simulate.sh    # 降采样 + 固定位点分型
│   ├── 06_export.sh      # 导出分析用矩阵
│   └── 07_identify.sh    # 识别与评估
├── src/ricevar_id/   # 纯标准库 Python 库（不依赖 numpy/pandas）
│   ├── fingerprint.py    # 指纹与相似度（IBS/Hamming/Jaccard）
│   ├── database.py       # SQLite 层
│   └── dbquery.py        # 查询层
├── scripts/          # 分析、建库、出图、验证脚本
├── app/              # Streamlit 原型
├── data/metadata/    # 样本清单与检索/整理产物（**论文数据来源**）
├── docs/             # 文档、方法设计、论文与附录、任务报告
└── tests/            # 单元测试
```

## E.3 数据

### E.3.1 原始测序数据

| 项目 | 说明 |
| --- | --- |
| 来源 | ENA / NCBI SRA 公共数据（**非本项目产生**） |
| 检索条件 | `tax_eq(4530) AND library_strategy="WGS"`，`base_count ≥ 1,875,000,000` |
| 获取方式 | 按 run 号下载（`sra-tools` / ENA FTP） |
| 是否随文提供 | **否**——体积达数百 GB，且可按 run 号重新下载 |
| run 号清单 | 面板清单与附录 A 已列出**全部 55 个 run 号** |

**因此本文的样本可被独立复现**：附录 A 给出每个样本的
`sample_id`、`run_accession`、`platform`、`layout` 与 `BioProject`，
第三方可据此自行下载同一批数据。

### E.3.2 参考基因组

| 项目 | 说明 |
| --- | --- |
| 参考 | IRGSP-1.0（日本晴 / Nipponbare） |
| RefSeq | `GCF_001433935.1` |
| INSDC/ENA | `GCA_001433935` |
| 来源 | Ensembl Plants release-60 |
| 校验 | 下载后记录字节数、gzip SHA-256 与 FASTA SHA-256（**完整 64 位，不截断**） |

参考基因组**不随文提供**（可由上表地址重新下载）。
其完整性由 `server/03_align.sh` 写入的 `reference_record.tsv` 记录；
**该文件在真实下载发生后才会产生**——截至本文写作时**尚未生成**，
因此本文不给出任何校验和数值。

### E.3.3 随文提供的整理产物

以下文件**体积小且是论文数字的直接依据**，应当随代码一起提供
（`.gitignore` 已确保它们不被排除）：

| 文件 | 内容 |
| --- | --- |
| `pilot_manifest.tsv` | Pilot 30 样本完整元数据 |
| `independent_manifest.tsv` | 独立面板 25 样本完整元数据 |
| `pilot_smoke1.tsv` / `pilot_smoke5.tsv` | 预检样本集 |
| `manifest_build_summary.json` | 面板选取规则与预检记录 |
| `ena_search_summary.tsv` | ENA 各检索条件命中数（**检索事实的原始记录**） |
| `candidate_samples.tsv` | 32,564 条候选样本 |
| `sample_attrs.tsv` | 21,654 条唯一样本属性 |
| `variety_canonical.tsv` / `variety_alias.tsv` | 8,415 个规范品种名及 8,501 条别名 |
| `duplicate_samples.tsv` | 1,326 条重复样本记录 |

**未随文提供**：`data/metadata/candidates/xml_cache/`（约 110 MB 的
NCBI 批量查询原始 XML 响应）。它可由检索条件重新抓取，
其**派生结果**已在上表中提供。

## E.4 运行方式

```bash
# 1. 环境自检（必须先做，结果写入日志）
bash server/00_probe.sh

# 2. 建环境（conda + bioconda 工具链）
bash server/01_setup_env.sh

# 3. 全流程；也可按阶段续跑
bash server/run_all.sh          # 全部阶段
bash server/run_all.sh 03       # 从 03_align 阶段开始
```

参数集中在 `server/config.sh`，无需改动脚本本体即可调整线程数、深度梯度等。
全部默认值与实测软件版本见**附录 B**。

Python 依赖由两份文件共同确定：`environment.yml`（conda 侧，含 bioconda 工具链）
与 `requirements.txt`（pip 侧，供 `pip install -r` 使用）。
两者必须同时提供——只给其中一份都无法重建完整环境。

`.gitignore` 的作用：排除原始数据与大体积中间产物，
但**保留** `data/metadata/` 下的整理产物与各输出目录的 `.gitkeep` 占位文件
（`data/raw/.gitkeep` 等）——后者若被排除，克隆后目录不存在，
脚本会因找不到输出目录而失败。该规则由 `tests/test_gitignore.py` 的
10 项测试锁定，其中包含"任何 `data/metadata/` 下的文件都不得被排除
（`xml_cache` 除外）"这一条。

## E.5 可复现性现状（**关键声明**）

必须明确区分三件事：

| 类别 | 状态 |
| --- | --- |
| **样本选择与元数据整理** | ✅ **可复现**。检索条件、清单、别名归一化与附录 A 全部提供 |
| **方法设计与代码** | ✅ **已提供**。流程、参数、评分公式与相似度实现均在仓库中 |
| **实验结果（识别率、深度曲线等）** | ❌ **尚不存在**。实验**尚未执行** |

造成第三项的原因不是数据不可得，而是**运行环境前置条件未满足**：
学校服务器的调度器、网络访问与存储配额尚未确认，
`server/00_probe.sh` 尚未在目标服务器上运行。

因此本文**不提供、也不声称**任何准确率、召回率或最低可用深度的数值；
论文第 3 章相应位置均为占位符。**在实验真正执行之前，
本项目不能被引用为"已验证可行"。**

## E.6 复现本文结果需要什么

要在另一台机器上复现（或首次产生）本文的实验结果，需要：

1. 一台可通过网络访问 `ftp.ebi.ac.uk` 与 NCBI 的 Linux 机器；
2. 约 **334.71 GiB** 的下载空间（附录 A 中 55 个 run 的**声明**体积之和；
   实测量可能略有差异）；
3. conda / mamba（用于按 `environment.yml` 重建工具链）；
4. 8 线程、约 16 GB 内存（`config.sh` 的默认值，可调）。

第 2 项是**清单声明值**而非本项目实测值——本文从未下载过这些数据。
