#!/usr/bin/env bash
# 01_setup_env.sh —— 在服务器上准备 conda 环境（幂等，可重复运行）
# 用法: bash 01_setup_env.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

ENV_YML="$HERE/environment.server.yml"
CONDA="$RV_CONDA_PREFIX/bin/conda"

log "开始准备环境"

# ---------- 1. 找 conda ----------
if command -v conda >/dev/null 2>&1; then
  CONDA="$(command -v conda)"
  log "使用系统已有 conda: $CONDA ($($CONDA --version))"
elif [ -x "$CONDA" ]; then
  log "使用已安装的 Miniconda: $CONDA ($($CONDA --version))"
else
  log "未发现 conda，开始安装 Miniconda 到 $RV_CONDA_PREFIX"
  URLS=()
  [ "$RV_MIRROR" = "1" ] && URLS+=("$RV_CONDA_MIRROR_URL")
  URLS+=(
    "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    "https://mirrors.ustc.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
  )
  OK=0
  for u in "${URLS[@]}"; do
    log "  尝试: $u"
    if curl -fsSL -m 600 --retry 2 -o "$RV_TMP/miniconda.sh" "$u" && [ -s "$RV_TMP/miniconda.sh" ]; then OK=1; break; fi
    log "    失败，换下一个源"
  done
  [ "$OK" = 1 ] || die "所有 Miniconda 源都下载失败，请手动下载安装包后设置 RV_CONDA_PREFIX"
  bash "$RV_TMP/miniconda.sh" -b -p "$RV_CONDA_PREFIX"
  CONDA="$RV_CONDA_PREFIX/bin/conda"
  "$CONDA" init bash >/dev/null 2>&1 || true
  log "Miniconda 安装完成: $($CONDA --version)"
fi

# ---------- 2. 镜像与求解器设置 ----------
"$CONDA" config --set channel_priority strict
"$CONDA" config --set solver libmamba 2>/dev/null || true
"$CONDA" config --set show_channel_urls true
if [ "$RV_MIRROR" = "1" ]; then
  log "配置国内镜像（TUNA）"
  "$CONDA" config --remove-key default_channels 2>/dev/null || true
  "$CONDA" config --add default_channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  "$CONDA" config --add default_channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  "$CONDA" config --set custom_channels.conda-forge https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  "$CONDA" config --set custom_channels.bioconda  https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
fi

# ---------- 3. 建环境 ----------
if "$CONDA" env list | awk '{print $1}' | grep -qx ricevar; then
  log "环境 ricevar 已存在，执行更新"
  "$CONDA" env update -n ricevar -f "$ENV_YML" --prune
else
  log "创建环境 ricevar（首次约需 5–15 分钟）"
  "$CONDA" env create -f "$ENV_YML" || {
    log "首次求解失败，剥离 pip 段后重试"
    python3 - "$ENV_YML" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read()
t = t.replace("  - pip\n  - pip:\n      - requests\n", "")
open(p, "w").write(t)
PY
    "$CONDA" env create -f "$ENV_YML"
  }
fi

# ---------- 4. 验证 ----------
log "验证关键工具："
"$CONDA" run -n ricevar bash -lc '
  for t in bwa-mem2 samtools bcftools bedtools mosdepth fastp fastqc multiqc snakemake kmc jellyfish seqkit; do
    if command -v $t >/dev/null 2>&1; then printf "  OK   %-12s %s\n" "$t" "$($t --version 2>&1 | head -n1 | cut -c1-60)";
    else printf "  MISS %s\n" "$t"; fi
  done
  python -c "import numpy,pandas,pysam,pyarrow;print(\"  OK   python deps\", numpy.__version__)"
' || log "验证有警告，请检查上方输出"

cat <<EOF

============================================================
环境准备完成。以后每个阶段请用：

  source $RV_CONDA_PREFIX/etc/profile.d/conda.sh
  conda activate ricevar

再运行 server/ 下的阶段脚本。
工作区: $RV_ROOT
============================================================
EOF
