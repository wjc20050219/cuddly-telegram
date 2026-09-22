#!/usr/bin/env bash
# RiceVar-ID: robust WSL env bootstrap (v2, ASCII-only, mirror-aware)
# Run as root inside Ubuntu: wsl.exe -d Ubuntu -u root -- bash /mnt/d/dsh/RiceVar-ID/setup_wsl_env2.sh
set -uo pipefail

REPO=/mnt/d/dsh/RiceVar-ID
LOG=$REPO/wsl_env_setup.log
PREFIX=${CONDA_PREFIX_INSTALL:-/opt/miniconda3}
CONDA=$PREFIX/bin/conda
export DEBIAN_FRONTEND=noninteractive
export PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}

log() { echo "[$(date +%H:%M:%S)] $*"; }

{
echo "===== WSL env setup v2 start: $(date) ====="
log "whoami=$(whoami)  uname=$(uname -r)"

log "--- STEP W0: ensure base tools ---"
apt-get update -y >/dev/null 2>&1 || true
apt-get install -y --no-install-recommends wget bzip2 ca-certificates curl >/dev/null 2>&1 || true
log "apt done"

log "--- STEP W2: download Miniconda3 (mirror-aware) ---"
MINI_URLS=(
  "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
  "https://mirrors.ustc.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
  "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
)
OK=0
for u in "${MINI_URLS[@]}"; do
  log "try miniconda: $u"
  if wget -q --timeout=60 --tries=2 -O /tmp/Miniconda3.sh "$u"; then
    if [ -s /tmp/Miniconda3.sh ] && head -c 400 /tmp/Miniconda3.sh | grep -qi 'conda\|installer\|anaconda'; then OK=1; break; fi
  fi
  log "  failed, next mirror"
done
if [ "$OK" -ne 1 ]; then log "FATAL: cannot download Miniconda3"; echo "FAILED_MINICONDA_DOWNLOAD"; exit 20; fi
log "downloaded: $(wc -c < /tmp/Miniconda3.sh) bytes"

log "--- STEP W3: install to $PREFIX ---"
bash /tmp/Miniconda3.sh -b -p "$PREFIX"
log "installer exit=$?"
"$CONDA" --version
"$CONDA" init bash >/dev/null 2>&1 || true

log "--- STEP W4: conda config + TUNA mirrors ---"
"$CONDA" config --system --set channel_priority flexible
"$CONDA" config --system --set show_channel_urls true
"$CONDA" config --system --remove-key default_channels 2>/dev/null || true
"$CONDA" config --system --add default_channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main || true
"$CONDA" config --system --add default_channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r || true
"$CONDA" config --system --set custom_channels.conda-forge https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud || true
"$CONDA" config --system --set custom_channels.bioconda https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud || true
"$CONDA" config --system --set custom_channels.msys2 https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud || true
"$CONDA" config --show channels | head -n 20

log "--- STEP W5: conda env create -f environment.yml (long) ---"
"$CONDA" env create -f "$REPO/environment.yml"
RC=$?
log "conda env create exit=$RC"
if [ "$RC" -ne 0 ]; then
  log "retry once with libmamba solver"
  "$CONDA" env create -f "$REPO/environment.yml" --solver=libmamba
  RC=$?
  log "retry exit=$RC"
fi

log "--- STEP W6: verify key tools ---"
"$CONDA" run -n ricevar bash -lc 'python -V; samtools --version 2>/dev/null | head -n1; bwa-mem2 version 2>&1 | head -n1; bcftools --version 2>/dev/null | head -n1; snakemake --version 2>/dev/null' 2>&1 | tail -n 12
log "verify exit=$?"

log "--- STEP W7: record versions ---"
if [ -f "$REPO/scripts/record_versions.sh" ]; then
  "$CONDA" run -n ricevar bash "$REPO/scripts/record_versions.sh" 2>&1 | tail -n 25 || log "record_versions failed"
fi

log "===== ALL_DONE_WSL2 ====="
} 2>&1 | tee -a "$LOG"
