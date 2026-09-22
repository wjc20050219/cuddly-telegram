#!/usr/bin/env bash
# 02_download.sh —— 按冻结样本表从 ENA 下载 FASTQ（断点续传、MD5/SHA256 记录）
# 用法: bash 02_download.sh            # 下载全部
#       bash 02_download.sh P01        # 只下载某个 sample_id
# 产出: raw/<sample_id>/*.fastq.gz
#       metadata/download_log.tsv   ← TASK-018 要求的下载日志
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"
init_dirs

ONLY="${1:-}"
DLLOG="$RV_META/download_log.tsv"

[ -f "$RV_SAMPLES" ] || die "找不到样本表: $RV_SAMPLES"

# 初始化下载日志
DL_HEADER='sample_id\trun_accession\tfile_name\tfile_size\tmd5\tsha256\tsource_url\tdownload_time\tstatus'
if [ ! -f "$DLLOG" ]; then
  printf '%b\n' "$DL_HEADER" > "$DLLOG"
elif [ "$(head -n1 "$DLLOG")" != "$(printf '%b' "$DL_HEADER")" ]; then
  die "下载日志表头为旧版或损坏；请先备份并移走 $DLLOG"
fi

# ---------- 单文件下载 + 校验 ----------
fetch_one() {
  local sid="$1" run="$2" url="$3" md5="$4" bytes="$5"
  local dir="$RV_RAW/$sid"
  local fn; fn="$(basename "$url")"
  local out="$dir/$fn"
  mkdir -p "$dir"

  if [ -s "$out" ] && [ "$(stat -c%s "$out" 2>/dev/null || echo 0)" = "$bytes" ]; then
    if [ -n "$md5" ] && echo "$md5  $out" | md5sum -c --quiet - 2>/dev/null; then
      log "  已存在且校验通过: $fn"
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$sid" "$run" "$fn" "$bytes" "$md5" "$(sha256sum "$out" | awk '{print $1}')" "$url" "$(date '+%F %T')" "skip_ok" >> "$DLLOG"
      return 0
    fi
  fi

  log "  下载 $fn ($(awk -v b="$bytes" 'BEGIN{printf "%.0f", b/1048576}') MB)"
  if curl -fL --retry 3 --retry-delay 5 -C - -o "$out" "$url"; then
    if [ -n "$md5" ]; then
      if echo "$md5  $out" | md5sum -c --quiet - 2>/dev/null; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$sid" "$run" "$fn" "$bytes" "$md5" "$(sha256sum "$out" | awk '{print $1}')" "$url" "$(date '+%F %T')" "ok" >> "$DLLOG"
        log "  ✓ $fn 校验通过"
        return 0
      else
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$sid" "$run" "$fn" "$bytes" "$md5" "$(sha256sum "$out" | awk '{print $1}')" "$url" "$(date '+%F %T')" "md5_mismatch" >> "$DLLOG"
        log "  ✗ $fn MD5 不匹配，已保留文件供排查"
        return 1
      fi
    fi
    printf '%s\t%s\t%s\t%s\t\t%s\t%s\t%s\t%s\n' \
      "$sid" "$run" "$fn" "$bytes" "$(sha256sum "$out" | awk '{print $1}')" "$url" "$(date '+%F %T')" "ok_no_md5" >> "$DLLOG"
    return 0
  else
    printf '%s\t%s\t%s\t%s\t\t\t%s\t%s\t%s\n' \
      "$sid" "$run" "$fn" "$bytes" "$url" "$(date '+%F %T')" "failed" >> "$DLLOG"
    log "  ✗ $fn 下载失败"
    return 1
  fi
}

# ---------- 单个样本 ----------
do_sample() {
  local sid="$1"
  local run; run="$(sid_to_run "$sid")"
  [ -n "$run" ] || { log "跳过 $sid：样本表中没有 run_accession"; return 1; }

  if is_done download "$sid"; then log "[$sid] 已完成，跳过"; return 0; fi
  log "[$sid] run=$run 查询 ENA 元数据…"

  local api="https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${run}&result=read_run&fields=fastq_ftp,fastq_md5,fastq_bytes&format=tsv"
  local line
  line="$(curl -fsSL -m 60 "$api" | awk -F'\t' 'NR==2')"
  [ -n "$line" ] || { log "[$sid] ENA 查询失败"; return 1; }

  local ftps md5s bytes expected_ftps expected_n
  ftps="$(echo "$line"  | awk -F'\t' '{print $2}')"
  md5s="$(echo "$line"  | awk -F'\t' '{print $3}')"
  bytes="$(echo "$line" | awk -F'\t' '{print $4}')"
  expected_ftps="$(sample_value "$sid" fastq_ftp)"
  [ -n "$ftps" ] || { log "[$sid] ENA 无 FASTQ 链接（可能是 BAM-only 项目）"; return 1; }
  [ -n "$expected_ftps" ] || { log "[$sid] manifest 无 FASTQ 链接"; return 1; }
  expected_n=$(awk -F';' '{print NF}' <<< "$expected_ftps")

  local IFS=';'
  local -a U=($ftps) M=($md5s) B=($bytes)
  unset IFS

  local i rc=0 matched=0
  for i in "${!U[@]}"; do
    # 只下载冻结 manifest 列出的文件；排除 ENA 某些 paired run 额外暴露的冗余 unsuffixed FASTQ。
    case ";$expected_ftps;" in
      *";${U[$i]};"*)
        matched=$((matched+1))
        fetch_one "$sid" "$run" "https://${U[$i]}" "${M[$i]:-}" "${B[$i]:-0}" || rc=1
        ;;
    esac
  done
  if [ "$matched" -ne "$expected_n" ]; then
    log "[$sid] manifest/API FASTQ 不一致：期望 $expected_n，匹配 $matched"
    rc=1
  fi

  [ "$rc" = 0 ] && mark_done download "$sid"
  return $rc
}

log "=== 开始下载（样本表: $RV_SAMPLES）==="
if [ -n "$ONLY" ]; then
  do_sample "$ONLY"
else
  for sid in $(sample_ids); do do_sample "$sid"; done
fi

log "=== 下载汇总 ==="
if [ -f "$DLLOG" ]; then
  awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}{c[$(h["status"])]++} END{for(s in c) printf "  %-14s %d\n", s, c[s]}' "$DLLOG"
  log "日志: $DLLOG"
fi
log "各样本数据量:"
du -sh "$RV_RAW"/* 2>/dev/null || true
