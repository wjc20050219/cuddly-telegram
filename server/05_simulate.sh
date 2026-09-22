#!/usr/bin/env bash
# 05_simulate.sh —— ulcWGS 超低深度模拟（Phase 13 核心）
# 从每个样本的高深度 CRAM 随机抽 reads 到目标深度，立刻算窗口深度，下采样 BAM 用完即删。
# 关键：绝不把下采样 BAM 落盘留存（否则会产生数 TB 垃圾）。
# 用法: bash 05_simulate.sh [sample_id]
# 产出: sim/<sid>/d<深度>_r<重复>/w<窗口>.regions.bed.gz
#       sim/simulation_manifest.tsv   ← 记录随机种子，保证可复现
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

ONLY="${1:-}"
REF="$(ref_fasta)"
SIMS="$RV_LOG/simulation_manifest.tsv"
DO_KMER="${RV_DO_KMER:-0}"        # 可选扩展；本科必做主线不启用
MARKER_TARGET="${RV_MARKER_TARGET:-$RV_META/frozen_markers.tsv.gz}"
MARKER_REGIONS="${RV_MARKER_REGIONS:-${MARKER_TARGET%.tsv.gz}.regions.tsv.gz}"
GENO_MANIFEST="$RV_LOG/marker_genotype_manifest.tsv"

SIM_HEADER='sample_id\tdepth\treplicate\tseed\tfraction\tactual_depth\twindow\tfile\tbytes\tcreated'
GENO_HEADER='sample_id\tdepth\treplicate\tseed\tfraction\tmarker_target\tvcf\tbytes\tcreated'
[ -f "$SIMS" ] || printf '%b\n' "$SIM_HEADER" > "$SIMS"
[ -f "$GENO_MANIFEST" ] || printf '%b\n' "$GENO_HEADER" > "$GENO_MANIFEST"
[ "$(head -n1 "$SIMS")" = "$(printf '%b' "$SIM_HEADER")" ] \
  || die "simulation manifest 表头为旧版或损坏；请先备份并移走 $SIMS"
[ "$(head -n1 "$GENO_MANIFEST")" = "$(printf '%b' "$GENO_HEADER")" ] \
  || die "genotype manifest 表头为旧版或损坏；请先备份并移走 $GENO_MANIFEST"

genome_size() { awk '{s+=$2} END{print s+0}' "$REF.fai"; }

# 估算样本实际深度（优先用 samtools stats，退化到 flagstat/idxstats）
sample_depth() {
  local sid="$1" bases="" gs
  gs="$(genome_size)"
  if [ -s "$RV_QC/$sid.stats.txt" ]; then
    bases=$(awk -F'\t' '$1=="SN" && $2 ~ /^bases mapped:/ {print $3}' "$RV_QC/$sid.stats.txt" | head -n1)
  fi
  if [ -z "$bases" ] || [ "$bases" = "0" ]; then
    local reads rl=150
    reads=$(samtools view -c -F 0x904 "$RV_BAM/$sid.cram" 2>/dev/null || echo 0)
    if [ -s "$RV_QC/$sid.fastp.json" ]; then
      rl=$(grep -o '"read1_mean_length":[0-9]*' "$RV_QC/$sid.fastp.json" 2>/dev/null | head -n1 | cut -d: -f2)
      [ -n "${rl:-}" ] || rl=150
    fi
    # samtools view -c 已把每条 mate 分别计为一条 alignment，不能再乘 2。
    bases=$(( reads * rl ))
  fi
  awk -v b="$bases" -v g="$gs" 'BEGIN{ if (g>0) printf "%.4f", b/g; else print "0" }'
}

do_sample() {
  local sid="$1"
  local cram="$RV_BAM/$sid.cram"
  [ -s "$cram" ] || { log "[$sid] 缺少 CRAM，跳过"; return 1; }
  [ -s "$cram.crai" ] || samtools index -@ 4 "$cram"

  local depth_actual
  depth_actual="$(sample_depth "$sid")"
  log "[$sid] 实际深度 ≈ ${depth_actual}×"

  local di=0
  for D in $RV_DEPTHS; do
    di=$((di+1))
    for R in $(seq 1 "$RV_REPS"); do
      local outdir="$RV_SIM/$sid/d${D}_r${R}"
      mkdir -p "$outdir"
      # 已全部产出则跳过
      local allok=1
      for W in $RV_WINDOWS; do [ -s "$outdir/w${W}.regions.bed.gz" ] || allok=0; done
      # marker target 可能在深度 BED 完成后才冻结；此时不能跳过，须补做固定位置分型。
      if [ -s "$MARKER_TARGET" ] && [ -s "$MARKER_REGIONS" ] && [ ! -s "$outdir/markers.vcf.gz" ]; then allok=0; fi
      if [ "$allok" = 1 ]; then log "[$sid] d=${D} r=${R} 已完成，跳过"; continue; fi

      # 目标分数（相对当前 CRAM），上限 1.0
      local frac
      frac=$(awk -v t="$D" -v a="$depth_actual" 'BEGIN{ f=(a>0)?t/a:1; if(f>1) f=1; printf "%.6f", f }')
      local seed=$(( R * 1000 + di ))

      log "[$sid] 抽 reads → ${D}× (frac=${frac}, seed=${seed}, rep=${R})"
      local tbam="$RV_TMP/${sid}_d${D}_r${R}.bam"
      # samtools -s 的格式为 INT.FRAC；frac 已是 0.xxxxxx，须去掉前导 0.
      local subsample_arg="${seed}.${frac#0.}"
      if awk -v f="$frac" 'BEGIN{exit !(f>=0.999999)}'; then
        if ! samtools view -@ "$((THREADS/2))" -T "$REF" -b "$cram" 2>/dev/null \
             | samtools sort -@ "$((THREADS/2))" -m 256M -o "$tbam" - 2>/dev/null; then
          log "[$sid] d=${D} r=${R} 全量复制失败"; continue
        fi
      elif ! samtools view -@ "$((THREADS/2))" -T "$REF" -s "$subsample_arg" -b "$cram" 2>/dev/null \
             | samtools sort -@ "$((THREADS/2))" -m 256M -o "$tbam" - 2>/dev/null; then
        log "[$sid] d=${D} r=${R} 下采样失败"; continue
      fi
      samtools index "$tbam" 2>/dev/null

      local W
      for W in $RV_WINDOWS; do
        if ! mosdepth -t "$((THREADS/4>1?THREADS/4:1))" -b "$W" -x "$outdir/w${W}" "$tbam" 2>/dev/null; then
          log "[$sid] d=${D} r=${R} w=${W} mosdepth 失败，本轮不计入清单"; continue
        fi
        local f="$outdir/w${W}.regions.bed.gz" summary="$outdir/w${W}.mosdepth.summary.txt" actual="" rel=""
        [ -s "$summary" ] && actual=$(awk '$1=="total"{print $4; exit}' "$summary")
        if [ -s "$f" ]; then
          rel="$(realpath --relative-to="$RV_SIM" "$f")"
          if ! awk -F'\t' -v p="$rel" 'NR>1 && $8==p{found=1} END{exit !found}' "$SIMS"; then
            printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
              "$sid" "$D" "$R" "$seed" "$frac" "$actual" "$W" "$rel" "$(stat -c%s "$f")" "$(date '+%F %T')" >> "$SIMS"
          fi
        fi
      done

      # 第二阶段：marker 已在 Pilot 内冻结后，才对降采样 BAM 做固定等位基因分型。
      if [ -s "$MARKER_TARGET" ] || [ -s "$MARKER_REGIONS" ]; then
        [ -s "$MARKER_TARGET" ] && [ -s "$MARKER_REGIONS" ] \
          || { log "[$sid] marker allele/region target 必须成对存在，跳过定点分型"; rm -f "$tbam" "$tbam.csi"; continue; }
        local gvcf="$outdir/markers.vcf.gz"
        if [ ! -s "$gvcf" ]; then
          bcftools mpileup -f "$REF" -q "${MAPQ:-20}" -Q "${BASEQ:-20}" \
            -R "$MARKER_REGIONS" -a FORMAT/AD,FORMAT/DP -Ou "$tbam" 2> "$RV_LOG/$sid.d${D}.r${R}.markers.mpileup.log" \
            | bcftools call -m -A -C alleles -T "$MARKER_TARGET" -f GQ -Oz -o "$gvcf" \
            || { log "[$sid] d=${D} r=${R} marker 定点分型失败"; rm -f "$gvcf"; }
          if ! [ -s "$gvcf" ] || ! bcftools index -t "$gvcf"; then
            log "[$sid] d=${D} r=${R} marker VCF 索引失败，不计入分型清单"; rm -f "$gvcf" "$gvcf.tbi" "$gvcf.csi"
          fi
        fi
        if [ -s "$gvcf" ]; then
          local grel
          grel="$(realpath --relative-to="$RV_SIM" "$gvcf")"
          if ! awk -F'\t' -v f="$grel" 'NR>1 && $7==f{found=1} END{exit !found}' "$GENO_MANIFEST"; then
            printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
              "$sid" "$D" "$R" "$seed" "$frac" "$(basename "$MARKER_TARGET")" \
              "$grel" "$(stat -c%s "$gvcf")" "$(date '+%F %T')" >> "$GENO_MANIFEST"
          fi
        fi
      fi

      # 可选：对模拟数据跑 KMC（低深度下只有几 MB，很便宜）
      if [ "$DO_KMER" = 1 ]; then
        local fq="$RV_TMP/${sid}_d${D}_r${R}.fq.gz"
        if ! samtools fastq -@ "$((THREADS/2))" "$tbam" 2>/dev/null | gzip -1 > "$fq" || [ ! -s "$fq" ]; then
          log "[$sid] d=${D} r=${R} fastq 导出失败，跳过 KMC"; rm -f "$fq"
        else
          local K
          for K in $RV_KMERS; do
            mkdir -p "$RV_KMER/$sid"
            kmc -k"$K" -t"$((THREADS/2))" -m"$KMC_MEM" -ci2 -cs100000 \
                "$fq" "$RV_KMER/$sid/d${D}_r${R}_k${K}" "$RV_TMP/kmc" > "$RV_LOG/$sid.kmc.k${K}.log" 2>&1 || log "[$sid] KMC k=$K 失败"
          done
          rm -f "$fq"
        fi
      fi

      rm -f "$tbam" "$tbam.csi" "$tbam.crai"      # ★ 不留下采样 BAM
      log "[$sid] d=${D} r=${R} ✓"
    done
  done
  mark_done simulate "$sid"
}

log "=== 阶段 05：ulcWGS 模拟（深度梯度: $RV_DEPTHS，每个 $RV_REPS 次重复）==="
log "    总量: $(echo $RV_DEPTHS | wc -w) 档 × $RV_REPS 重复 × 每样本 = 每样本 $(( $(echo $RV_DEPTHS | wc -w) * RV_REPS )) 次抽取"
[ -s "$REF.fai" ] || die "参考基因组未就绪，请先运行 03_align.sh"

if [ -n "$ONLY" ]; then
  do_sample "$ONLY"
else
  export -f do_sample sample_depth genome_size; export REF DO_KMER MARKER_TARGET MARKER_REGIONS GENO_MANIFEST
  par_each do_sample $(sample_ids)
fi

log "=== 05 完成 ==="
du -sh "$RV_SIM" 2>/dev/null
echo "种子表: $SIMS （$(wc -l < "$SIMS") 行）"
if [ -s "$MARKER_TARGET" ] && [ -s "$MARKER_REGIONS" ]; then
  echo "marker 分型表: $GENO_MANIFEST （$(wc -l < "$GENO_MANIFEST") 行）"
else
  echo "尚无冻结 marker target；本轮只生成降采样深度，不生成 SNP 识别结果。"
fi
