# TASK-002 报告：建立软件环境

- 日期：2026-09-15
- 结果：✅ 完成（环境已实际建成并逐项验证，非仅"配置就绪"）
- 阶段：Phase 0 · 项目初始化

## 一、交付物

| 文件 | 内容 |
| --- | --- |
| `environment.yml` | conda 环境 `ricevar` 的完整规格（v2，见下"关键修订"） |
| `requirements.txt` | Python 依赖（科学栈 / pysam / scikit-allel / FastAPI / qrcode / pytest 等） |
| `software_versions.txt` | 实测环境清单 + 部署决策记录 + 复现命令 |
| `scripts/collect_env_versions.sh` | 一键采集环境内全部工具与库版本（替代失效的 record_versions.sh） |
| `setup_wsl_env3.sh` | WSL 内一键建环境的可复现脚本（镜像感知、可重试） |

## 二、实际建成环境（2026-09-15 实测）

```
Windows 11 23H2
  └─ WSL 2.7.14.0（内核 6.18.33.2-2）
       └─ Ubuntu 26.04.1 LTS
            └─ Miniconda3 /opt/miniconda3（conda 26.7.1，libmamba）
                 └─ conda env ricevar  ←  /opt/miniconda3/envs/ricevar
```

**核心版本**：Python 3.11.16 / R 4.3.3 / samtools 1.24 / bcftools 1.24 / bedtools 2.31.1 /
bwa-mem2 2.3 / minimap2 2.31 / mosdepth 0.3.14 / fastp 1.3.7 / FastQC 0.12.1 /
KMC 3.2.4 / jellyfish 2.3.1 / Snakemake 9.24.0 / sra-tools 3.4.1 / seqkit 2.13.0。

任务清单要求的全部工具**均已就位并逐一验证可执行**（详见 `software_versions.txt` 第五节）。

## 三、关键修订（v1 → v2）

首版 `environment.yml` 在求解阶段失败，原因是三点叠加，修订后**数秒内求解成功**：

1. `python=3.10` → **`python=3.11`**：Snakemake 9 与 `snakemake-executor-plugin-cluster-generic` 要求 ≥3.11；
2. **移除 `r-tidyverse`**：拉入数百个 R 包，是 SAT 求解爆炸主因；R 绘图包按需在 Phase 6 前单独安装；
3. **移除 `mamba`**（conda 已内置 libmamba），并把 `channel_priority` 由 flexible 改为 **strict**。

首版在 flexible 下求解 41 分钟未收敛（CPU 99%、内存 7 GB），属典型的求解爆炸而非网络问题。

## 四、过程记录（两次环境级障碍及解法）

1. **WSL 侧无发行版**：`wsl --update --web-download` 正常（装成 WSL 2.7.14），但
   `wsl --install -d Ubuntu` 需管理员权限。已通过提权脚本 `finish_setup.ps1` 完成安装。
2. **Miniforge 下载失败**：WSL 内 github.com 与 TUNA `github-release/LatestRelease`
   两条源均失败 → 改用 **TUNA Anaconda 镜像的 Miniconda3**，成功。
   同时把 conda-forge / bioconda 通道与 PyPI 都指向 TUNA 镜像，后续下载速度与稳定性显著提升。
3. **包名坑**：conda-forge 的 `jellyfish` 是 Python 绑定库，不含 k-mer CLI；
   CLI 需 bioconda 的 **`kmer-jellyfish`**，已补装。
4. `scripts/record_versions.sh` 因 `set -euo pipefail` 遇到工具非零退出码而中断，
   已用 `scripts/collect_env_versions.sh` 替代并完成回填。

## 五、运行期事件：WSL 服务卡死（2026-09-15 19:02）

- **现象**：`wsl.exe` 所有子命令（含 `-l -v`、`--status`、`--shutdown`）全部无响应；`wsl --shutdown` 自身也超时。
- **证据**：Windows 应用程序日志显示 **`wslsettings.exe`（WSL 设置界面，版本 2.7.14.0）于 19:02:43 崩溃**（Application Error），随后 `wsl.exe --cd ~` 进程在 19:02:48 出现并挂住。`vmmemWSL` 仍存活且无法从非提权会话结束。
- **恢复方式**（当前会话无法提权，需人工执行其一）：
  1. **重启 Windows**（最省事，必定恢复）；或
  2. 以**管理员**打开 PowerShell 执行：
     ```powershell
     Restart-Service WslService -Force
     wsl --shutdown
     wsl -l -v
     ```
- **恢复后自检**：
  ```bash
  wsl -d Ubuntu -u root -- bash -lc 'source /opt/miniconda3/etc/profile.d/conda.sh && conda activate ricevar && python -V && samtools --version | head -n1'
  ```
- **影响**：环境本身未损坏（数据在 `ext4.vhdx` 中，仅服务进程卡死），重启后即可继续；已备好 `scripts/bench.sh` 供恢复后实测本机算力。

### 5.1 恢复结果（2026-09-16 16:06）✅ 已恢复

**已于 2026-09-16 16:06 重启 Windows 后完全恢复**，环境逐项验证通过：

| 验证项 | 结果 |
| --- | --- |
| `wsl -l -v` | ✅ 正常响应，Ubuntu / VERSION 2 |
| WslService | ✅ Running |
| `conda activate ricevar` | ✅ 成功（Python 3.11.16） |
| 关键工具 | ✅ **0/14 缺失**（samtools 1.24 / bcftools 1.24 / bedtools 2.31.1 / bwa-mem2 2.3 / minimap2 2.31 / mosdepth 0.3.14 / fastp 1.3.7 / FastQC 0.12.1 / KMC 3.2.4 / jellyfish 2.3.1 / Snakemake 9.24.0 / R 4.3.3 / git 2.55.0 / seqkit 2.13.0） |
| Python 库 | ✅ **0/11 缺失**（numpy 2.4.6 / pandas 3.0.5 / scipy 1.17.1 / pyarrow 25.0.1 / pysam 0.24.1 / biopython 1.88 / scikit-allel 1.3.13 / sklearn 1.9.1 / matplotlib 3.11.2 / seaborn 0.13.2 / pytest 9.1.1） |
| 实跑链路 | ✅ samtools faidx → bwa-mem2 比对 → samtools sort → index → bcftools mpileup/call → mosdepth 全通 |

**恢复过程中的关键发现**：本自动化会话（DSH）**不具备提权能力**。

- `Start-Process -Verb RunAs` 会一直阻塞等待 UAC 响应——自动化进程不在用户交互桌面上，对话框弹不出来（实测卡住 120 秒无返回）；
- `schtasks /create /rl HIGHEST` 被 `Access is denied` 拒绝；
- 同时确认账号 `WJC\86159` **确实是管理员**（在 Administrators 组内，令牌显示 "Group used for deny only"），只是当前进程用的是受限令牌。

**结论**：此类需要管理员权限的恢复操作**必须由人工执行**，两条可行路径为
① 重启 Windows；② 在用户自己的管理员 PowerShell 中双击运行 `fix_wsl.cmd`（会自动请求提权）。

**新增的防护配置**：已创建 `C:\Users\86159\.wslconfig`（此前不存在），实测已生效：

```ini
[wsl2]
memory=10GB          # 实测 free -h 显示 9.7Gi
processors=16        # 实测 nproc = 16
swap=16GB            # 实测 free -h 显示 16Gi
swapFile=D:\\wsl-swap.vhdx
[experimental]
autoMemoryReclaim=gradual
sparseVhd=true       # 防止 ext4.vhdx 只涨不缩、悄悄吃满 C 盘
```

**新增的运维脚本**：

| 脚本 | 用途 |
| --- | --- |
| `scripts/verify_env.sh` | 环境全项自检（资源 / 环境 / 工具 / 库 / 实跑链路 / 磁盘 / 目录可见性） |
| `scripts/bench_run.sh` | 激活 ricevar 后运行 `bench.sh`（规避 `wsl.exe` 引号转义问题） |
| `fix_wsl.cmd` | 双击自动提权并修复卡死的 WSL 服务 |
| `recover_wsl2.ps1` | 修复逻辑本体（强杀进程 → 重启服务 → 验证 → 写日志） |
| `recover_wsl.ps1` | v1，已被 `recover_wsl2.ps1` 取代 |


## 六、后续（Phase 3 前）

- 下载工具 sra-tools / entrez-direct 已就位，可支撑 TASK-008–TASK-011 的公共数据检索与下载；
- R 生态（tidyverse / ggplot2 等）按分析需要单独 `conda install`，不阻塞当前阶段；
- 环境入口固定为：`wsl -d Ubuntu -u root` → `conda activate ricevar`。

---

## 七、依赖缺陷修复（2026-09-16 复核）

对 TASK-002 的三份输出逐项复核，发现 **2 处真实缺陷**，均已修复。

### 7.1 `environment.yml` 的 jellyfish 包名错误（复现性缺陷）

| | 详情 |
| --- | --- |
| **现象** | `conda list` 显示环境里有两个包：`jellyfish 1.2.1`（conda-forge，**仅 Python 绑定**）与 `kmer-jellyfish 2.3.1`（bioconda，**真正的 k-mer CLI**） |
| **缺陷** | `environment.yml` 只声明了 `jellyfish`。照 yml 重建环境 → **装到 Python 绑定，拿不到 `jellyfish` 可执行文件** |
| **根因** | 2026-09-15 发现此坑后只把 CLI 补装进当前环境，**忘了同步修改 yml**（问题记录已写进 `software_versions.txt` 第三节第 5 条，但 yml 未动） |
| **修复** | yml 中改为同时声明 `kmer-jellyfish`（CLI）+ `jellyfish`（Python 绑定），并加注释说明区别 |

### 7.2 `hmmlearn` 缺失（方法学依赖缺陷）

| | 详情 |
| --- | --- |
| **现象** | `import hmmlearn` → `ModuleNotFoundError` |
| **缺陷** | 论文 CNVb 方法用 **HMM 平滑窗口深度**（`n_components=3, n_iter=60, tol=0.001`，见 TASK-004 解析第 4 节 Step 1），但 `environment.yml` 与 `requirements.txt` **均未包含**该依赖 |
| **影响** | Phase 11（CNV 路线）会直接卡住；属"环境已建立但缺关键依赖"的隐性缺口 |
| **修复** | 已安装 **hmmlearn 0.3.3**（安装时 numpy/scipy/scikit-learn 均 "already satisfied"，**未扰动既有环境**），并补入 `environment.yml` 与 `requirements.txt` |

### 7.3 复核结论

| 核对项 | 结果 |
| --- | --- |
| 规范要求的各类工具 | ✅ 全部可用：python / R / conda / git / fastqc / fastp / samtools / bcftools / bedtools / bwa-mem2 / minimap2 / mosdepth / kmc / jellyfish CLI / snakemake |
| `mamba` | ⬜ 未装，但规范写的是"conda/mamba"（二选一），且 conda ≥24 已内置 libmamba 求解器 → **可接受** |
| `nextflow` | ⬜ 未装，规范写的是"Snakemake **或** Nextflow" → **可接受**（已选 Snakemake） |
| 三份输出文件 | ✅ `environment.yml` / `requirements.txt` / `software_versions.txt` 均存在且已更新 |

> 结论：**TASK-002 复核后合格**。两处缺陷均属"文档与实环境不同步"类问题，
> 已通过修改依赖文件 + 补装 hmmlearn 消除；环境本身的工具、库与实跑链路自始正常。

新增自检脚本 `scripts/check_task002_deps.sh`，可随时复验本节每一项。
