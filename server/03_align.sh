#!/usr/bin/env bash
# 03_align.sh —— 参考基因组准备 + 逐样本 QC/比对（fastp → bwa-mem2 → CRAM）
# 用法: bash 03_align.sh           # 全部样本
#       bash 03_align.sh P01
# 产出: reference/IRGSP-1.0*.fa(.gz) + bwa 索引
#       qc/<sid>.fastp.{json,html}, qc/<sid>.flagstat.txt, qc/<sid>.stats.txt
#       bam/<sid>.cram(.crai)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

ONLY="${1:-}"
REF="$(ref_fasta)"
KEEP_BAM="${RV_KEEP_BAM:-0}"      # 1=保留中间 BAM（占空间）
KEEP_TRIM="${RV_KEEP_TRIM:-0}"    # 1=保留 trim 后 FASTQ（占空间）

# ---------- 参考基因组 ----------
prep_reference() {
  init_dirs
  if [ ! -s "$RV_REF/$(basename "$RV_REF_URL")" ]; then
    log "下载参考基因组 IRGSP-1.0 …"
    curl -fL --retry 3 -o "$RV_REF/$(basename "$RV_REF_URL")" "$RV_REF_URL" \
      || die "参考基因组下载失败: $RV_REF_URL"
  fi
  local gz="$RV_REF/$(basename "$RV_REF_URL")"
  gzip -t "$gz" || die "参考基因组 gzip 完整性检查失败: $gz"
  if [ ! -s "$REF" ]; then
    log "解压参考基因组"
    gunzip -c "$gz" > "$REF" || die "解压失败"
  fi
  [ -s "$REF.fai" ] || samtools faidx "$REF"
  if [ ! -s "$REF.bwt.2bit.64" ]; then
    log "构建 bwa-mem2 索引（约 30–60 分钟，内存峰值约 6–10 GB，仅需一次）"
    bwa-mem2 index "$REF" || die "bwa-mem2 index 失败"
  fi
  local nseq total_bp
  nseq=$(grep -c '^>' "$REF")
  total_bp=$(awk '{s+=$2} END{print s+0}' "$REF.fai")
  log "参考基因组就绪: $REF ($nseq 条序列；$total_bp bp)"
  {
    printf 'reference_name\turl\tdownload_recorded_at\tgzip_bytes\tgzip_sha256\tfasta_file\tfasta_sha256\tsequence_count\ttotal_bp\n'
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$RV_REF_NAME" "$RV_REF_URL" "$(date '+%F %T')" "$(stat -c%s "$gz")" \
      "$(sha256sum "$gz" | awk '{print $1}')" "$(basename "$REF")" \
      "$(sha256sum "$REF" | awk '{print $1}')" "$nseq" "$total_bp"
  } > "$RV_REF/reference_record.tsv"
}

# ---------- 单样本 ----------
do_sample() {
  local sid="$1"
  is_done align "$sid" && { log "[$sid] 已完成，跳过"; return 0; }

  local dir="$RV_RAW/$sid"
  [ -d "$dir" ] || { log "[$sid] 无原始数据目录，跳过"; return 1; }

  local r1 r2
  r1="$(ls "$dir"/*_1.fastq.gz 2>/dev/null | head -n1)"
  r2="$(ls "$dir"/*_2.fastq.gz 2>/dev/null | head -n1)"
  [ -n "$r1" ] || { log "[$sid] 找不到 *_1.fastq.gz，跳过"; return 1; }

  local trim="$RV_QC/$sid"
  mkdir -p "$trim"

  # ---- FastQC（原始 reads）----
  local fqcout="$RV_QC/fastqc_raw/$sid"
  mkdir -p "$fqcout"
  if [ ! -f "$fqcout/.done" ]; then
    log "[$sid] FastQC 原始数据"
    if [ -n "$r2" ]; then
      fastqc --threads "$((THREADS/2))" --outdir "$fqcout" "$r1" "$r2" > "$RV_LOG/$sid.fastqc.log" 2>&1 \
        || { log "[$sid] FastQC 失败"; return 1; }
    else
      fastqc --threads "$((THREADS/2))" --outdir "$fqcout" "$r1" > "$RV_LOG/$sid.fastqc.log" 2>&1 \
        || { log "[$sid] FastQC 失败"; return 1; }
    fi
    touch "$fqcout/.done"
  fi

  # ---- fastp ----
  if [ ! -s "$RV_QC/$sid.fastp.json" ]; then
    log "[$sid] fastp 质控"
    if [ -n "$r2" ]; then
      fastp -i "$r1" -I "$r2" -o "$trim/R1.fq.gz" -O "$trim/R2.fq.gz" \
            -w "$THREADS" -j "$RV_QC/$sid.fastp.json" -h "$RV_QC/$sid.fastp.html" \
            > "$RV_LOG/$sid.fastp.log" 2>&1 || { log "[$sid] fastp 失败"; return 1; }
    else
      fastp -i "$r1" -o "$trim/R1.fq.gz" \
            -w "$THREADS" -j "$RV_QC/$sid.fastp.json" -h "$RV_QC/$sid.fastp.html" \
            > "$RV_LOG/$sid.fastp.log" 2>&1 || { log "[$sid] fastp 失败"; return 1; }
    fi
  fi

  # ---- bwa-mem2 + sort ----
  if [ ! -s "$RV_BAM/$sid.cram" ]; then
    log "[$sid] bwa-mem2 比对（$THREADS 线程，约 10–30 分钟）"
    local platform rg
    platform="$(sample_value "$sid" platform)"
    [ -n "$platform" ] || platform="UNKNOWN"
    platform="${platform// /_}"
    rg="@RG\\tID:${sid}\\tSM:${sid}\\tPL:${platform}\\tLB:${sid}"
    if [ -n "$r2" ]; then
      bwa-mem2 mem -t "$THREADS" -R "$rg" "$REF" "$trim/R1.fq.gz" "$trim/R2.fq.gz" 2> "$RV_LOG/$sid.bwa.log" \
        | samtools sort -@ "$((THREADS/2))" -m "$SORT_MEM" -o "$RV_BAM/$sid.bam" - \
        || { log "[$sid] 比对/排序失败"; return 1; }
    else
      bwa-mem2 mem -t "$THREADS" -R "$rg" "$REF" "$trim/R1.fq.gz" 2> "$RV_LOG/$sid.bwa.log" \
        | samtools sort -@ "$((THREADS/2))" -m "$SORT_MEM" -o "$RV_BAM/$sid.bam" - \
        || { log "[$sid] 比对/排序失败"; return 1; }
    fi

    samtools flagstat -@ 4 "$RV_BAM/$sid.bam" > "$RV_QC/$sid.flagstat.txt"
    samtools stats   -@ 4 "$RV_BAM/$sid.bam" > "$RV_QC/$sid.stats.txt"

    log "[$sid] 转 CRAM（省约一半空间）"
    samtools view -@ "$((THREADS/2))" -C -T "$REF" -o "$RV_BAM/$sid.cram" "$RV_BAM/$sid.bam" \
      || { log "[$sid] CRAM 转换失败"; return 1; }
    samtools index -@ 4 "$RV_BAM/$sid.cram"
    [ "$KEEP_BAM" = "1" ] || rm -f "$RV_BAM/$sid.bam"
  fi

  [ "$KEEP_TRIM" = "1" ] || rm -rf "$trim"

  mark_done align "$sid"
  log "[$sid] ✓ 比对完成 -> $RV_BAM/$sid.cram"
}

log "=== 阶段 03：参考准备 + 比对 ==="
prep_reference

if [ -n "$ONLY" ]; then
  do_sample "$ONLY"
else
  export -f do_sample; export REF KEEP_BAM KEEP_TRIM
  par_each do_sample $(sample_ids)
fi

log "=== 03 完成 ==="
ls -lh "$RV_BAM"/*.cram 2>/dev/null | awk '{print "  "$9" "$5}'
