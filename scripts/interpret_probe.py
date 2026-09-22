#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""interpret_probe.py —— 把 00_probe.sh 的输出翻译成可执行的决策。

为什么需要这个脚本
------------------
`server/00_probe.sh` 在服务器上跑完后会产出 `logs/probe_summary.tsv`。
在那之前，本项目对以下四件事**完全不知道**，而它们决定了后面所有脚本要怎么跑：

  1. 有没有作业调度器（决定用 Slurm 数组还是 nohup+xargs）
  2. 服务器能不能访问 ENA/NCBI（决定"服务器直接下载"还是"本机代下再上传"）
  3. 有多少磁盘空间（决定能否一次性放全部 55 个样本）
  4. 生信工具缺哪些（决定 01_setup_env 要装什么）

把判断规则写成代码而不是写在文档里，有两个好处：
  * 规则可以被测试（见 tests/test_probe_decision_rules.py）；
  * 拿到 probe 输出的**当天**就能得到结论，不需要重新推导一遍。

**本脚本不做任何假设**：probe_summary.tsv 不存在时它明确报告"尚未探测"，
而不是给出一套默认建议 —— 没有数据时的"建议"就是编造。

用法
----
    python scripts/interpret_probe.py --summary logs/probe_summary.tsv
    python scripts/interpret_probe.py --summary logs/probe_summary.tsv --json out.json
"""
import argparse
import json
import os
import sys

# --- 阈值：与 server/00_probe.sh 第 6 节的判定保持一致 -----------------------
# 脚本里写的是 <1 / <5 / >=5 MB/s 三档；这里不引入新阈值，只复用。
SPEED_FAIL = 0.0          # curl 失败或取到 <1MB
SPEED_SLOW = 1.0          # < 1 MB/s
SPEED_MEDIUM = 5.0        # < 5 MB/s
BYTES_PER_BASE = 1        # 单碱基测序数据 ~1 字节 FASTQ（压缩前粗估）

# 55 个样本的申报体积（manifest 声明值，非实测）。见附录 A。
PANEL_GIB = {"pilot": 170.70, "independent": 164.02}
GIB = 1024 ** 3

# 运行流水线所需的工具（缺任何一个都会让某阶段失败）
REQUIRED = {
    "bwa-mem2": "03_align（比对）",
    "samtools": "03_align / 04（CRAM、索引、下采样）",
    "bcftools": "04_joint_snp（联合 calling）",
    "bedtools": "标记位点区间操作",
    "mosdepth": "深度统计",
    "fastp": "03_align（质控）",
    "seqkit": "序列处理",
    "pigz": "并行压缩（可选但强烈建议）",
}
# 缺失不致命、但会改变实现方式的工具
OPTIONAL = {
    "fastqc": "质控报告（缺则只用 fastp 的 JSON）",
    "kmc": "可选 k-mer 分支，非主线",
    "jellyfish": "可选 k-mer 分支，非主线",
    "snakemake": "可选流程引擎，run_all.sh 不依赖",
    "fasterq-dump": "仅在本机代下 SRA 时需要",
    "prefetch": "仅在本机代下 SRA 时需要",
    "aria2c": "多线程下载加速",
    "axel": "多线程下载加速",
    "plink2": "群体遗传统计，可选",
    "bwa": "bwa-mem2 的替代（更慢）",
}


def read_summary(path):
    """读 probe_summary.tsv -> dict。文件不存在时返回 None（不是空 dict）。

    None 与 {} 的区别很重要：前者是"没探测过"，后者是"探测了但一无所获"。
    """
    if not path or not os.path.exists(path):
        return None
    out = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            key, val = parts[0].strip(), parts[1].strip()
            if key:
                out[key] = val
    return out


def parse_speed(raw):
    """'FAIL' / '' / 浮点字符串 -> 浮点 MB/s；FAIL 与不可解析都返回 None。"""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw or raw.upper() == "FAIL":
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    return val if val >= 0 else None


def parse_gib(raw):
    """df -hP 的 'Avail' 列（如 '1.2T'、'500G'）-> GiB 浮点；失败返回 None。"""
    if raw is None:
        return None
    s = raw.strip()
    if not s or s in ("-", "?"):
        return None
    unit = s[-1].upper()
    num = s[:-1] if unit.isalpha() else s
    try:
        val = float(num)
    except ValueError:
        return None
    factor = {"T": 1024.0, "G": 1.0, "M": 1.0 / 1024, "K": 1.0 / (1024 ** 2),
              "P": 1024.0 * 1024}.get(unit, 1.0)
    return val * factor


def decide(summary):
    """把 probe 原始键值翻译成决策。返回结构化结果。"""
    if summary is None:
        return {
            "probed": False,
            "verdict": "尚未探测",
            "reason": "未找到 probe_summary.tsv：请在服务器上运行 bash server/00_probe.sh",
            "actions": ["运行 bash server/00_probe.sh",
                        "或请管理员回答 docs/server_admin_questions.md"],
            "blocking": True,
        }

    d = {}
    sched = (summary.get("scheduler") or "").strip().lower()
    d["scheduler"] = sched or "unknown"
    # `use_slurm` must mirror what run_all.sh can actually do. That script
    # detects ONLY `sbatch`; qsub/bsub fall through to the single-machine
    # branch. Reporting them as Slurm would tell the operator "the orchestrator
    # will handle this" when in fact the pipeline would run on the login node.
    d["use_slurm"] = sched == "sbatch"
    d["scheduler_usable_by_run_all"] = sched == "sbatch"
    d["scheduler_note"] = {
        "sbatch": "Slurm：run_all.sh 会自动改用 sbatch 提交并串联依赖",
        "qsub": "PBS/SGE 存在，但 run_all.sh 只实现了 Slurm 分支；请用单机模式 + tmux",
        "bsub": "LSF 存在，同上：请用单机模式 + tmux",
        "none": "无调度器：用单机模式（nohup/tmux + xargs 并行）",
    }.get(sched, "未识别调度器，请人工确认后再跑")

    ena = parse_speed(summary.get("net_ena_speed"))
    ncbi = parse_speed(summary.get("net_ncbi_speed"))
    d["ena_mbs"] = ena
    d["ncbi_mbs"] = ncbi
    best = max([x for x in (ena, ncbi) if x is not None], default=None)
    d["best_speed_mbs"] = best

    if best is None:
        d["download_plan"] = "服务器外网不可用：必须本机代下后上传"
        d["download_ok"] = False
        d["parallel_hint"] = 1
    elif best < SPEED_SLOW:
        d["download_plan"] = "极慢（<1 MB/s）：本机代下更划算，或在服务器长时间后台拉取"
        d["download_ok"] = False
        d["parallel_hint"] = 2
    elif best < SPEED_MEDIUM:
        d["download_plan"] = "中等（1-5 MB/s）：服务器下载，4-8 线程并行"
        d["download_ok"] = True
        d["parallel_hint"] = 4
    else:
        d["download_plan"] = "良好（>=5 MB/s）：服务器直接下载，可高并行"
        d["download_ok"] = True
        d["parallel_hint"] = 8

    avail = parse_gib(summary.get("home_avail"))
    d["home_avail_gib"] = avail
    d["total_panel_gib"] = PANEL_GIB["pilot"] + PANEL_GIB["independent"]
    if avail is None:
        d["storage_plan"] = "磁盘空间未知，请人工提供 df -h 结果"
        d["storage_ok"] = False
    elif avail < PANEL_GIB["pilot"] * 1.5:
        d["storage_plan"] = ("空间不足以同时容纳两个面板；"
                             "先只跑 Pilot（%.1f GiB），完成后再单独下载独立面板"
                             % PANEL_GIB["pilot"])
        d["storage_ok"] = False
    elif avail < d["total_panel_gib"]:
        d["storage_plan"] = ("可容纳 Pilot，但不够两个面板共存（需 %.1f GiB）；"
                             "建议分两批下载、跑完一批删一批" % d["total_panel_gib"])
        d["storage_ok"] = False
    else:
        d["storage_plan"] = "空间充足，可同时容纳两个面板"
        d["storage_ok"] = True

    missing = [t for t in REQUIRED if summary.get("tool_" + t) != "yes"]
    present = [t for t in REQUIRED if summary.get("tool_" + t) == "yes"]
    d["tools_present"] = sorted(present)
    d["tools_missing_required"] = sorted(missing)
    d["tools_missing_optional"] = sorted(
        t for t in OPTIONAL if summary.get("tool_" + t) != "yes")
    d["tools_ok"] = not missing

    softs = {c: summary.get("soft_" + c) for c in
             ("conda", "mamba", "micromamba", "module", "singularity",
              "apptainer", "docker")}
    d["software"] = softs
    d["can_create_env"] = any(
        softs.get(c) == "yes" for c in ("conda", "mamba", "micromamba"))
    d["has_container"] = any(
        softs.get(c) == "yes" for c in ("singularity", "apptainer", "docker"))

    cpus = summary.get("nproc")
    try:
        d["nproc"] = int(cpus) if cpus else None
    except ValueError:
        d["nproc"] = None

    # --- 综合结论 ---
    actions = []
    blocking = False
    if not d["can_create_env"] and not d["has_container"]:
        actions.append("无 conda/mamba 也无容器：请管理员安装 Miniconda，"
                       "或用 module load 提供环境")
        blocking = True
    if not d["download_ok"]:
        actions.append("外网受限：改由本机代下 FASTQ 后上传到 data/raw/<sample_id>/")
        blocking = True
    if not d["storage_ok"]:
        # "unknown" and "too small" need different instructions; a generic
        # "follow the plan above" is useless when there is no plan yet.
        actions.append("磁盘空间未知：请提供 df -h 结果后再定分批方案"
                       if d["home_avail_gib"] is None
                       else "存储受限：按上面的分批方案执行")
    if missing:
        # 必需工具缺失会让 03/04 阶段直接失败。01_setup_env.sh 会尝试安装，
        # 但"尝试"不等于"成功"，因此这仍是一个需要在开跑前确认的阻塞项：
        # 在没有 conda 可用的机器上，01_setup_env 根本无法安装任何东西。
        actions.append("缺必需工具：" + "、".join(sorted(missing))
                       + ("（01_setup_env.sh 会尝试安装，但需先确认能装）"
                          if d["can_create_env"] else
                          "（且无 conda 可用，无法自动安装，必须管理员提供）"))
        if not d["can_create_env"]:
            blocking = True
    if sched in ("qsub", "bsub"):
        # run_all.sh 只实现了 Slurm 分支；qsub/bsub 会静默走单机模式，
        # 在登录节点上跑比对有被管理员杀进程的风险。必须显式提示。
        actions.append("检测到 %s（非 Slurm）：run_all.sh 不会使用它，"
                       "将按单机模式运行；建议改用 tmux 并确认登录节点允许长任务"
                       % sched)
    if not actions:
        actions.append("4 项前置条件均满足，可直接上传 server/ + pilot_smoke1.tsv 开跑")

    d["probed"] = True
    d["actions"] = actions
    d["blocking"] = blocking
    d["verdict"] = "就绪" if not blocking else "存在硬阻塞"
    return d


def format_report(d):
    L = []
    L.append("=" * 70)
    L.append(" 00_probe.sh 结果判读")
    L.append("=" * 70)
    if not d.get("probed"):
        L.append("状态：%s" % d["verdict"])
        L.append("原因：%s" % d["reason"])
        L.append("")
        L.append("下一步：")
        for a in d["actions"]:
            L.append("  - %s" % a)
        return "\n".join(L)

    L.append("调度器   : %s -> %s" % (d["scheduler"], d["scheduler_note"]))
    L.append("下载速度 : ENA=%s  NCBI=%s  MB/s" % (
        "FAIL" if d["ena_mbs"] is None else "%.2f" % d["ena_mbs"],
        "FAIL" if d["ncbi_mbs"] is None else "%.2f" % d["ncbi_mbs"]))
    L.append("下载方案 : %s" % d["download_plan"])
    L.append("剩余空间 : %s GiB（面板共需 %.1f GiB）" % (
        "未知" if d["home_avail_gib"] is None else "%.1f" % d["home_avail_gib"],
        d["total_panel_gib"]))
    L.append("存储方案 : %s" % d["storage_plan"])
    L.append("CPU 核心 : %s" % (d["nproc"] if d["nproc"] else "未知"))
    L.append("")
    L.append("工具（必需）:")
    for t in sorted(REQUIRED):
        mark = "OK " if t in d["tools_present"] else "缺失"
        L.append("  [%s] %-12s %s" % (mark, t, REQUIRED[t]))
    if d["tools_missing_optional"]:
        L.append("工具（可选，缺失不影响主线）: %s"
                 % "、".join(d["tools_missing_optional"]))
    L.append("")
    L.append("环境创建 : %s" % ("可（conda/mamba 存在）"
                               if d["can_create_env"] else "不可，需管理员介入"))
    L.append("")
    L.append("=" * 70)
    L.append(" 结论：%s" % d["verdict"])
    L.append("=" * 70)
    for a in d["actions"]:
        L.append("  - %s" % a)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="判读 00_probe.sh 的输出并给出可执行决策")
    ap.add_argument("--summary", default="logs/probe_summary.tsv",
                    help="probe_summary.tsv 路径（默认 logs/probe_summary.tsv）")
    ap.add_argument("--json", default=None, help="可选：把决策结果另存为 JSON")
    args = ap.parse_args(argv)

    d = decide(read_summary(args.summary))
    print(format_report(d))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("\n已写出: %s" % args.json)
    # 退出码：硬阻塞返回 1，便于脚本化调用；未探测返回 2（区别于"探测后发现阻塞"）
    if not d.get("probed"):
        return 2
    return 1 if d["blocking"] else 0


if __name__ == "__main__":
    sys.exit(main())
