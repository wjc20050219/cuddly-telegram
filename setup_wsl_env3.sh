#!/usr/bin/env bash
# RiceVar-ID: env create retry (v3, ASCII-only)
# Run: wsl.exe -d Ubuntu -u root -- bash /mnt/d/dsh/RiceVar-ID/setup_wsl_env3.sh
set -uo pipefail

REPO=/mnt/d/dsh/RiceVar-ID
LOG=$REPO/wsl_env_setup.log
CONDA=/opt/miniconda3/bin/conda
export PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}
export DEBIAN_FRONTEND=noninteractive

log() { echo "[$(date +%H:%M:%S)] $*"; }

{
echo "===== WSL env setup v3 start: $(date) ====="
log "conda: $($CONDA --version)"

log "--- STEP V1: strict channel priority ---"
$CONDA config --system --set channel_priority strict
$CONDA config --system --set solver libmamba
$CONDA config --system --set show_channel_urls true
$CONDA config --system --get channel_priority

log "--- STEP V2: conda env create (long) ---"
cd "$REPO"
$CONDA env create -f environment.yml --solver=libmamba
RC=$?
log "conda env create exit=$RC"
if [ "$RC" -ne 0 ]; then
  log "--- STEP V2b: strip pip section, retry env create ---"
  python3 - <<'PY'
p = "/mnt/d/dsh/RiceVar-ID/environment.yml"
t = open(p).read()
if "  - pip\n      - -r requirements.txt\n" in t:
    t = t.replace("  - pip\n      - -r requirements.txt\n", "")
    open(p, "w").write(t)
    print("pip section stripped")
else:
    print("pip section already absent")
PY
  $CONDA env create -f environment.yml --solver=libmamba
  RC=$?
  log "fallback env create exit=$RC"
fi

log "--- STEP V3: pip install inside ricevar ---"
$CONDA run -n ricevar pip install --no-input -r "$REPO/requirements.txt" 2>&1 | tail -n 8 || true

log "--- STEP V4: verify key tools ---"
$CONDA run -n ricevar bash -lc 'python -V; samtools --version 2>/dev/null | head -n1; bwa-mem2 version 2>&1 | head -n1; bcftools --version 2>/dev/null | head -n1; mosdepth --version 2>/dev/null; kmc 2>&1 | head -n1; snakemake --version 2>/dev/null' 2>&1 | tail -n 14
log "verify exit=$?"

log "--- STEP V5: record versions ---"
if [ -f "$REPO/scripts/record_versions.sh" ]; then
  $CONDA run -n ricevar bash "$REPO/scripts/record_versions.sh" 2>&1 | tail -n 25 || log "record_versions failed"
fi

log "===== ALL_DONE_WSL3 ====="
} 2>&1 | tee -a "$LOG"
