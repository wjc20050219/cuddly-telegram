#!/usr/bin/env bash
# 06_export.sh —— 把服务器产物汇总成"特征矩阵"并打包（★ 唯一需要传回本机的目录）
# 设计要点：过网的不是 BAM，而是 窗口×样本 / 标记×样本 矩阵，体积从 TB 降到 GB。
# 用法: bash 06_export.sh
# 产出: export/  (含 MANIFEST.tsv 与 sha256，供本机校验)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

PY=python
command -v conda >/dev/null 2>&1 && : # 假定已 conda activate ricevar

EX_GEN="$RV_EXPORT/genotypes"
EX_DEP="$RV_EXPORT/depth"
EX_SIM="$RV_EXPORT/depth_sim"
EX_SIM_GENO="$RV_EXPORT/genotypes_sim"
EX_MARKER="$RV_EXPORT/markers"
EX_IDENT="$RV_EXPORT/identification"
# 每次按当前 manifest 重建导出视图，避免 smoke/正式批次的旧文件残留。
rm -rf "$EX_GEN" "$EX_DEP" "$EX_SIM" "$EX_SIM_GENO" "$EX_MARKER" "$EX_IDENT"
mkdir -p "$EX_GEN" "$EX_DEP" "$EX_SIM" "$EX_SIM_GENO" "$EX_MARKER" "$EX_IDENT"

SIM_WINDOWS="${RV_SIM_EXPORT_WINDOWS:-10000 100000}"

bm() { $PY "$HERE/build_matrices.py" "$@"; }

# ---------- 1. 全深度窗口深度矩阵 ----------
log "=== 1/5 汇总全深度窗口深度矩阵 ==="
for W in $RV_WINDOWS; do
  src="$RV_DEPTH/w${W}"
  [ -d "$src" ] || { log "  跳过 ${W}bp（无数据）"; continue; }
  bm depth --depth-dir "$src" --pattern "*.regions.bed.gz" \
           --out "$EX_DEP/w${W}.parquet" || log "  ${W}bp 汇总失败"
done

# ---------- 2. ulcWGS 各档深度矩阵 ----------
log "=== 2/5 汇总 ulcWGS 模拟深度矩阵（各深度 × 各重复）==="
for D in $RV_DEPTHS; do
  for R in $(seq 1 "$RV_REPS"); do
    for W in $SIM_WINDOWS; do
      # 模拟数据的目录结构是 sim/<sid>/d<D>_r<R>/w<W>.regions.bed.gz
      # build_matrices.py 用 <dir>/<sample>/<pattern> 约定，这里先造一层符号链接视图
      view="$RV_TMP/simview_d${D}_r${R}_w${W}"
      rm -rf "$view"; mkdir -p "$view"
      for d in "$RV_SIM"/*/d"${D}"_r"${R}"; do
        [ -d "$d" ] || continue
        sid="$(basename "$(dirname "$d")")"
        [ -s "$d/w${W}.regions.bed.gz" ] && ln -sf "$d/w${W}.regions.bed.gz" "$view/$sid.regions.bed.gz"
      done
      n=$(ls "$view" 2>/dev/null | wc -l)
      [ "$n" -gt 0 ] || { rm -rf "$view"; continue; }
      bm depth --depth-dir "$view" --pattern "*.regions.bed.gz" \
               --out "$EX_SIM/d${D}_r${R}_w${W}.parquet" || log "  d${D}_r${R}_w${W} 汇总失败"
      rm -rf "$view"
    done
  done
done

# 若已冻结 marker 并完成低深度定点分型，保留 sample/depth/replicate 目录结构导出。
if [ -s "$RV_LOG/marker_genotype_manifest.tsv" ]; then
  cp -f "$RV_LOG/marker_genotype_manifest.tsv" "$EX_SIM_GENO/"
  for meta in "$RV_META"/frozen_markers*.tsv.gz "$RV_META"/frozen_markers*.tbi "$RV_META"/frozen_markers*.record.tsv; do
    [ -s "$meta" ] && cp -f "$meta" "$EX_SIM_GENO/"
  done
  while IFS=$'\t' read -r sid depth rep seed frac target rel bytes created; do
    [ "$sid" = "sample_id" ] && continue
    src="$RV_SIM/$rel"
    [ -s "$src" ] || continue
    dst="$EX_SIM_GENO/$(dirname "$rel")"
    mkdir -p "$dst"
    cp -f "$src" "$dst/markers.vcf.gz"
    [ -s "$src.tbi" ] && cp -f "$src.tbi" "$dst/markers.vcf.gz.tbi"
  done < "$RV_LOG/marker_genotype_manifest.tsv"
fi
[ -s "$RV_LOG/simulation_manifest.tsv" ] && cp -f "$RV_LOG/simulation_manifest.tsv" "$EX_SIM/"

# ---------- 3. 联合 SNP VCF ----------
log "=== 3/5 导出联合 SNP VCF ==="
JOINT="$RV_VCF/cohort.biallelic_snps.vcf.gz"
if [ -s "$JOINT" ]; then
  cp -f "$JOINT" "$EX_GEN/cohort.biallelic_snps.vcf.gz"
  [ -s "$JOINT.tbi" ] && cp -f "$JOINT.tbi" "$EX_GEN/cohort.biallelic_snps.vcf.gz.tbi"
  [ -s "$RV_VCF/cohort_calling_summary.tsv" ] && cp -f "$RV_VCF/cohort_calling_summary.tsv" "$EX_GEN/"
  [ -s "$RV_VCF/cohort_calling_state.tsv" ] && cp -f "$RV_VCF/cohort_calling_state.tsv" "$EX_GEN/"
  bcftools query -l "$JOINT" > "$EX_GEN/cohort.samples.txt"
  log "  已导出联合 VCF；正式 SNP 矩阵在本机按预注册 QC 生成"
else
  log "  无联合 VCF（单样本 smoke test 属正常；正式 Pilot ≥2 样本须运行 04_joint_snp.sh）"
fi

# ---------- 4. 冻结 marker 与识别评估结果 ----------
log "=== 4/5 导出冻结 marker 与识别评估 ==="
if [ -d "$RV_MARKER" ] && [ -n "$(ls -A "$RV_MARKER" 2>/dev/null)" ]; then
  cp -f "$RV_MARKER"/pilot.markers_*.vcf "$EX_MARKER/" 2>/dev/null
  cp -f "$RV_MARKER"/pilot.marker_ranking.tsv "$EX_MARKER/" 2>/dev/null
  cp -f "$RV_MARKER"/pilot.selection.json "$EX_MARKER/" 2>/dev/null
  cp -f "$RV_MARKER"/*.record.tsv "$EX_MARKER/" 2>/dev/null
  log "  已导出冻结 marker（Pilot-only 拟合）"
else
  log "  无冻结 marker：尚未在 Pilot 内完成 QC/排序，不能计算识别率"
fi
if [ -s "$RV_ANALYSIS/identification/identification_by_depth.tsv" ]; then
  cp -f "$RV_ANALYSIS/identification/identification_by_depth.tsv" "$EX_IDENT/"
  for d in "$RV_ANALYSIS/identification"/markers_*; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    mkdir -p "$EX_IDENT/$name"
    cp -f "$d/per_query.tsv" "$d/summary.json" "$EX_IDENT/$name/" 2>/dev/null
  done
  log "  已导出识别评估结果"
else
  log "  无识别评估结果：需先冻结 marker、重跑 05_simulate.sh，再运行 07_identify.sh"
fi

# ---------- 5. QC 汇总 + 清单 ----------
log "=== 5/5 QC 汇总 + MultiQC + MANIFEST ==="
{
  printf 'sample_id\trun\tvariety\tsubspecies\traw_reads\tclean_reads\tq30_rate\tgc_rate\tmapped_rate\test_depth\tcram_bytes\n'
  for sid in $(sample_ids); do
    run="$(sid_to_run "$sid")"
    variety="$(sample_value "$sid" variety_name)"
    sub="$(sample_value "$sid" subspecies)"
    j="$RV_QC/$sid.fastp.json"; f="$RV_QC/$sid.flagstat.txt"
    raw=""; clean=""; q30=""; gc=""
    if [ -s "$j" ]; then
      raw=$(grep -o '"total_reads":[0-9]*' "$j" | head -n1 | cut -d: -f2)
      clean=$(grep -o '"total_reads":[0-9]*' "$j" | sed -n 2p | cut -d: -f2)
      q30=$(grep -o '"q30_rate":[0-9.]*' "$j" | head -n1 | cut -d: -f2)
      gc=$(grep -o '"gc_content":[0-9.]*' "$j" | head -n1 | cut -d: -f2)
    fi
    mapped=""
    [ -s "$f" ] && mapped=$(awk '/mapped \(/{printf "%.4f", $5}' "$f" | tr -d '()')
    dep=""
    [ -s "$RV_QC/$sid.stats.txt" ] && dep=$(awk -F'\t' '$1=="SN" && $2 ~ /^bases mapped:/{print $3}' "$RV_QC/$sid.stats.txt" | head -n1)
    csz=0; [ -s "$RV_BAM/$sid.cram" ] && csz=$(stat -c%s "$RV_BAM/$sid.cram")
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$sid" "$run" "$variety" "$sub" "$raw" "$clean" "$q30" "$gc" "$mapped" "$dep" "$csz"
  done
} > "$RV_EXPORT/qc_summary.tsv"
log "  qc_summary.tsv 已生成"

if command -v multiqc >/dev/null 2>&1; then
  rm -rf "$RV_EXPORT/multiqc"
  multiqc --force --outdir "$RV_EXPORT/multiqc" "$RV_QC" > "$RV_LOG/multiqc.log" 2>&1 \
    || log "  MultiQC 生成失败（见 $RV_LOG/multiqc.log）"
else
  log "  MultiQC 未安装，跳过汇总报告"
fi

# 参数说明
cat > "$RV_EXPORT/README.md" <<EOF
# RiceVar-ID 服务器导出包

- 导出时间: $(date '+%F %T')
- 主机: $(hostname)
- 参考基因组: $RV_REF_NAME ($(basename "$(ref_fasta)"))
- 样本数: $(sample_ids | wc -l)
- 窗口大小: $RV_WINDOWS
- ulcWGS 深度梯度: $RV_DEPTHS
- 重复次数: $RV_REPS
- 随机种子表: 见服务器 $RV_LOG/simulation_manifest.tsv

## 矩阵约定
- 深度矩阵: 行=窗口(chrom,start,end)，列=样本；**数值 = 真实深度 × 10**（int16，反算除以 10）
- SNP: `genotypes/cohort.biallelic_snps.vcf.gz` 为多样本联合 VCF；正式矩阵须按预注册 QC 从该文件生成
- 禁止用 variant-only 单样本 VCF 拼接正式矩阵，因为“位点未出现”不等于可确认的 0/0
- ulcWGS 深度矩阵: 文件名 d<深度>_r<重复>_w<窗口>.parquet
- 冻结 marker 后的低深度定点 VCF: `genotypes_sim/<sample>/d<深度>_r<重复>/markers.vcf.gz`
- 未提供冻结 marker target 时，`genotypes_sim/` 为空是预期行为，不能计算识别率
- 冻结 marker 集: `markers/pilot.markers_<n>.vcf`、`pilot.marker_ranking.tsv`、`pilot.selection.json`
- 识别评估: `identification/markers_<n>/per_query.tsv` 与 `summary.json`；
  `identification_by_depth.tsv` 为按深度汇总
- ⚠ 识别评估的 query 是 Pilot 样本自身 CRAM 的降采样技术重复，属**闭集**结果；
  冻结的独立面板（与 Pilot 品种零重叠）只能报告**开放集拒识**，不能当作同品种独立 Top-1

## 校验
\`\`\`bash
sha256sum -c MANIFEST.sha256
\`\`\`
EOF

# MANIFEST
( cd "$RV_EXPORT" && find . -type f ! -name 'MANIFEST*' -printf '%P\n' | sort | while read -r f; do
    printf '%s\t%s\t%s\n' "$f" "$(stat -c%s "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"
  done ) > "$RV_EXPORT/MANIFEST.tsv"
( cd "$RV_EXPORT" && awk -F'\t' '{print $3"  "$1}' MANIFEST.tsv > MANIFEST.sha256 )
printf 'file\tsize_bytes\tsha256\n' | cat - "$RV_EXPORT/MANIFEST.tsv" > "$RV_EXPORT/MANIFEST.tmp" && mv "$RV_EXPORT/MANIFEST.tmp" "$RV_EXPORT/MANIFEST.tsv"

log "=== 导出完成 ==="
echo
echo "export/ 内容:"
du -sh "$RV_EXPORT"/* 2>/dev/null
echo
echo "总大小: $(du -sh "$RV_EXPORT" | cut -f1)"
echo "文件数: $(find "$RV_EXPORT" -type f | wc -l)"
echo
cat <<EOF
下一步——在本机执行（把 user@server 换成你的登录方式）:

  rsync -avP --partial user@server:$RV_EXPORT/ /mnt/d/dsh/RiceVar-ID/data/processed/server_export/
  cd /mnt/d/dsh/RiceVar-ID/data/processed/server_export && sha256sum -c MANIFEST.sha256

或用本仓库的 local/import_export.sh 一步完成。
EOF
