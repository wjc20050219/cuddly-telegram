#!/usr/bin/env bash
# 07_identify.sh —— 冻结 marker 后，用低深度定点 VCF 计算 recall / 识别率 / 拒识
#
# 前置条件（缺一不可）：
#   1. Pilot 联合 VCF（04_joint_snp.sh 产出）
#   2. 冻结 marker（scripts/select_snp_markers.py --panel-role pilot 产出）
#   3. 低深度定点 VCF（05_simulate.sh 在 marker 冻结后重跑产出）
#
# 本阶段只做"技术重复"闭集评估：query 是 Pilot 样本自身的高深度 CRAM 降采样，
# 因此结果不代表独立同品种准确率。独立 25 面板只能用于开放集拒识。
#
# 用法: bash 07_identify.sh [--marker-count 500] [--reject-threshold 0.9]
# 产出: $RV_ANALYSIS/identification/per_query.tsv 与 summary.json
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

PY="${RV_PYTHON:-python}"
MARKER_PREFIX="${RV_MARKER_PREFIX:-$RV_MARKER/pilot}"
MARKER_COUNTS="${RV_MARKER_COUNTS:-500 1000 2000}"
REJECT_THRESHOLD="${RV_REJECT_THRESHOLD:-}"
MIN_COMPARED="${RV_MIN_COMPARED:-50}"
MIN_DP="${RV_MIN_DP:-1}"
MIN_GQ="${RV_MIN_GQ:-0}"
TOPK="${RV_TOPK:-5}"
METHOD="${RV_METHOD:-ibs}"

ANALYSIS="${RV_ANALYSIS:-$RV_ROOT/analysis}"
OUT="$ANALYSIS/identification"
GENO_MANIFEST="$RV_LOG/marker_genotype_manifest.tsv"

# ---------- 输入检查 ----------
REF_MATRIX="$(ls "$MARKER_PREFIX".genotypes_*.tsv 2>/dev/null | sort -V | tail -n1)"
[ -s "${REF_MATRIX:-}" ] || die "找不到 Pilot 基因型矩阵；请先运行 scripts/select_snp_markers.py"
[ -s "$GENO_MANIFEST" ] || die "找不到 $GENO_MANIFEST；请先冻结 marker 并重跑 05_simulate.sh"

n_vcf=$(awk -F'\t' 'NR>1 && $7!="" {c++} END{print c+0}' "$GENO_MANIFEST")
[ "$n_vcf" -gt 0 ] || die "marker_genotype_manifest.tsv 中没有低深度定点 VCF；genotypes_sim/ 为空时不得计算识别率"

# ---------- 真值表 ----------
TRUTH="$RV_META/identification_truth.tsv"
{
  printf 'sample_id\tvariety_name\tsubspecies\n'
  for sid in $(sample_ids); do
    printf '%s\t%s\t%s\n' "$sid" "$(sample_value "$sid" variety_name)" "$(sample_value "$sid" subspecies)"
  done
} > "$TRUTH"

mkdir -p "$OUT"
log "=== 阶段 07：低深度识别评估 ==="
log "  参考矩阵: $REF_MATRIX"
log "  低深度 VCF: $n_vcf 份"
log "  真值表: $TRUTH"

# ---------- 逐 marker 数评估 ----------
args=()
while IFS=$'\t' read -r sid depth rep seed frac target rel bytes created; do
  [ "$sid" = "sample_id" ] && continue
  src="$RV_SIM/$rel"
  [ -s "$src" ] || { log "  [跳过] 缺少 $src"; continue; }
  label="${sid}_d${depth}_r${rep}"
  args+=("${label}=${src}")
done < "$GENO_MANIFEST"

[ "${#args[@]}" -gt 0 ] || die "marker_genotype_manifest.tsv 未指向任何存在的 VCF 文件"

for N in $MARKER_COUNTS; do
  odir="$OUT/markers_${N}"
  mkdir -p "$odir"
  cmd=( "$PY" "$HERE/../scripts/evaluate_identification.py"
        --reference-matrix "$REF_MATRIX"
        --query-vcf "${args[@]}"
        --truth "$TRUTH"
        --out-dir "$odir"
        --marker-count "$N"
        --method "$METHOD"
        --top-k "$TOPK"
        --min-compared "$MIN_COMPARED"
        --min-dp "$MIN_DP"
        --min-gq "$MIN_GQ" )
  [ -n "$REJECT_THRESHOLD" ] && cmd+=( --reject-threshold "$REJECT_THRESHOLD" )
  log "  marker=$N → $odir"
  "${cmd[@]}" > "$RV_LOG/identify_markers_${N}.log" 2>&1 \
    || { log "  marker=$N 评估失败，见 $RV_LOG/identify_markers_${N}.log"; continue; }
  [ -s "$odir/summary.json" ] && log "  marker=$N ✓"
done

# ---------- 汇总 ----------
{
  printf 'marker_count\tdepth\tn_queries\tmean_marker_recall\tmean_genotype_concordance\tmean_best_similarity\ttop1_variety_accuracy\ttop5_variety_accuracy\taccept_rate\n'
  for N in $MARKER_COUNTS; do
    s="$OUT/markers_${N}/summary.json"
    [ -s "$s" ] || continue
    "$PY" - "$s" "$N" <<'PYEOF'
import json, sys
path, n = sys.argv[1], sys.argv[2]
data = json.load(open(path, encoding="utf-8"))
for depth, row in sorted(data.get("by_depth", {}).items()):
    def fmt(value):
        return "" if value is None else ("%.6f" % value)
    print("\t".join([
        n, depth, str(row["n_queries"]),
        fmt(row["mean_marker_recall"]), fmt(row["mean_genotype_concordance"]),
        fmt(row["mean_best_similarity"]), fmt(row["top1_variety_accuracy"]),
        fmt(row["top5_variety_accuracy"]), fmt(row["accept_rate"]),
    ]))
PYEOF
  done
} > "$OUT/identification_by_depth.tsv"

log "=== 07 完成 ==="
[ -s "$OUT/identification_by_depth.tsv" ] && cat "$OUT/identification_by_depth.tsv"
echo
echo "注意：以上为技术重复闭集结果；独立面板仅支持开放集拒识。"
