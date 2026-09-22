#!/usr/bin/env bash
# RiceVar-ID: 在 WSL Ubuntu 内安装 Miniforge 并创建 ricevar 环境
# 由 finish_setup.ps1 以 root 身份调用，全程写入 wsl_env_setup.log
set -uo pipefail

REPO=/mnt/d/dsh/RiceVar-ID
LOG=$REPO/wsl_env_setup.log
MF_PREFIX=/opt/miniforge3
CONDA=$MF_PREFIX/bin/conda

log() { echo "[$(date +%H:%M:%S)] $*"; }

{
echo "===== WSL env setup start: $(date) ====="
log "whoami=$(whoami)  uname=$(uname -r)"
log "distro=$( . /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" )"

log "--- STEP W1: base packages ---"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends wget bzip2 ca-certificates curl
log "apt exit=$?"

log "--- STEP W2: download Miniforge ---"
MF_URLS=(
  "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
  "https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-Linux-x86_64.sh"
)
MF_OK=0
for u in "${MF_URLS[@]}"; do
  log "try: $u"
  if wget -q --timeout=60 --tries=2 -O /tmp/Miniforge3.sh "$u"; then
    if head -c 200 /tmp/Miniforge3.sh | grep -q 'bash'; then MF_OK=1; break; fi
  fi
  log "  failed, next mirror"
done
if [ "$MF_OK" -ne 1 ]; then log "FATAL: cannot download Miniforge"; echo "FAILED_MINIFORGE_DOWNLOAD"; exit 20; fi
log "downloaded: $(wc -c < /tmp/Miniforge3.sh) bytes"

log "--- STEP W3: install Miniforge to $MF_PREFIX ---"
bash /tmp/Miniforge3.sh -b -p "$MF_PREFIX"
log "installer exit=$?"
"$CONDA" --version
"$CONDA" init bash
log "conda init exit=$?"

log "--- STEP W4: conda config + channel ToS ---"
"$CONDA" config --system --set channel_priority flexible
for ch in defaults conda-forge bioconda; do
  "$CONDA" tos accept --override-channels --channel "$ch" 2>&1 | tail -n 2
done
"$CONDA" config --show channels

log "--- STEP W5: conda env create -f environment.yml (this takes a while) ---"
"$CONDA" env create -f "$REPO/environment.yml"
RC=$?
log "conda env create exit=$RC"
if [ "$RC" -ne 0 ]; then
  log "retry once with mamba solver"
  "$CONDA" env create -f "$REPO/environment.yml" --solver=libmamba
  RC=$?
  log "retry exit=$RC"
fi

log "--- STEP W6: verify key tools ---"
"$CONDA" run -n ricevar bash -lc 'python -V; samtools --version | head -n1; bwa-mem2 version 2>&1 | head -n1; snakemake --version' 2>&1
log "verify exit=$?"

log "--- STEP W7: record versions into software_versions.txt ---"
"$CONDA" run -n ricevar bash "$REPO/scripts/record_versions.sh"
log "record exit=$?"

log "===== ALL_DONE_WSL ====="
} 2>&1 | tee -a "$LOG"
