#!/usr/bin/env bash
# bench2.sh v2 —— 水稻规模的真实吞吐基准（精确采集墙钟 + CPU 时间 + 峰值内存）
#
# 与 v1 的差别：
#   * 用 /usr/bin/time 采集每一步的 wall / user / sys / maxRSS，直接得出**核时**（成本模型的单位）
#   * 修正 v1 把"墙钟小时"误标为"核时"的 bug
#   * 读段模拟器写成独立 sim.py，便于纳入计时
#   * 输出明确的乐观性说明（合成读段与参考完全一致 → 无真实变异）
#
# 用法:
#   bash bench2.sh
#   FASTA=/path/ref.fa DEPTH=10 THREADS=16 bash bench2.sh
set -uo pipefail

FASTA=${FASTA:-/opt/ricevar/ref/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa}
DEPTH=${DEPTH:-10}
THREADS=${THREADS:-16}
RL=${RL:-150}
INS=${INS:-500}
SEED=${SEED:-42}
WORK=${WORK:-/opt/bench2}
GENOME_MB=${GENOME_MB:-375}

command -v bwa-mem2 >/dev/null || { echo "✗ 找不到 bwa-mem2（请先 conda activate ricevar）"; exit 1; }
[ -s "$FASTA" ] || { echo "✗ 参考序列不存在: $FASTA"; exit 1; }
[ -s "${FASTA}.fai" ] || samtools faidx "$FASTA"

rm -rf "$WORK"; mkdir -p "$WORK"; cd "$WORK" || exit 1
TLOG="$WORK/steps.tsv"; : > "$TLOG"

# /usr/bin/time 是 GNU time，能给出 user/sys/maxRSS；没有就退化到只测墙钟
if [ -x /usr/bin/time ]; then
  HAVE_GTIME=1
else
  HAVE_GTIME=0
  echo "⚠️  /usr/bin/time 不可用，只能测墙钟时间（核时不可得）"
fi

# timed_sh <label> <Gb> <shell命令字符串>
timed_sh() {
  local label="$1" gb="$2" cmd="$3" tf rc W U S M
  tf=$(mktemp)
  if [ "$HAVE_GTIME" = "1" ]; then
    /usr/bin/time -f "%e\t%U\t%S\t%M" -o "$tf" bash -c "$cmd" >/dev/null 2>&1
    rc=$?
    IFS=$'\t' read -r W U S M < "$tf" 2>/dev/null || true
  else
    local t0 t1; t0=$(date +%s.%N)
    bash -c "$cmd" >/dev/null 2>&1; rc=$?
    t1=$(date +%s.%N)
    W=$(python3 -c "print('%.2f'%($t1-$t0))"); U=0; S=0; M=0
  fi
  rm -f "$tf"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$label" "$gb" "${W:-0}" "${U:-0}" "${S:-0}" "${M:-0}" >> "$TLOG"
  return $rc
}

cat > sim.py <<'PY'
import numpy as np, sys
fasta, npairs, rl, ins, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
with open(fasta, 'rb') as f:
    f.readline(); seq = b''.join(l.strip() for l in f)
L = len(seq); arr = np.frombuffer(seq, dtype=np.uint8)
rng = np.random.default_rng(seed)
comp = np.full(256, ord('N'), dtype=np.uint8)
for a, b in ((65,84),(67,71),(71,67),(84,65),(97,116),(99,103),(103,99),(116,97)): comp[a] = b
mut = np.frombuffer(b'ACGT', dtype=np.uint8)
Q = b'I' * rl
o1 = open('r1.fq','wb'); o2 = open('r2.fq','wb')
CH, done, base = 100000, 0, 0
while done < npairs:
    n = min(CH, npairs - done)
    pos = rng.integers(0, L - ins, size=n).astype(np.int64)
    frag = np.empty((n, ins), dtype=np.uint8)
    for off in range(ins): frag[:, off] = arr[pos + off]
    for _ in range(max(1, int(0.004 * ins))):
        j = rng.integers(0, ins, size=n)
        frag[np.arange(n), j] = mut[rng.integers(0, 4, size=n)]
    a = frag[:, :rl]; b = comp[frag[:, -rl:]][:, ::-1]
    l1, l2 = [], []
    for i in range(n):
        l1 += [b'@r%d/1' % (base+i), a[i].tobytes(), b'+', Q]
        l2 += [b'@r%d/2' % (base+i), b[i].tobytes(), b'+', Q]
    o1.write(b'\n'.join(l1) + b'\n'); o2.write(b'\n'.join(l2) + b'\n')
    done += n; base += n
o1.close(); o2.close()
PY

echo "############################################################"
echo "# RiceVar-ID 真实吞吐基准 v2"
echo "#  时间     : $(date '+%F %T')"
echo "#  参考序列 : $FASTA"
echo "#  线程     : $THREADS | 深度: ${DEPTH}x | 读长: ${RL}bp | 插入: ${INS}bp"
echo "############################################################"
echo

CHROM=$(sort -k2,2nr "${FASTA}.fai" | awk '$1!="Pltd"&&$1!="Mt"&&$1!="Pt"&&$1!="MT"&&$1!="chloroplast"{print $1; exit}')
CHROM_LEN=$(awk -v c="$CHROM" '$1==c{print $2}' "${FASTA}.fai")
FACTOR=$(python3 -c "print('%.4f'%(${GENOME_MB}*1e6/${CHROM_LEN}))")
NPAIRS=$(python3 -c "print(int(${CHROM_LEN}*${DEPTH}/(2*${RL})))")
SEQ_GB=$(python3 -c "print('%.4f'%(${NPAIRS}*2*${RL}/1e9))")

echo "### 测试单元 : 染色体 $CHROM = $(python3 -c "print('%.2f'%(${CHROM_LEN}/1e6))") Mb @ ${DEPTH}x = ${SEQ_GB} Gb 序列（${NPAIRS} 对读段）"
echo "### 外推系数 : x${FACTOR} → ${GENOME_MB} Mb 全基因组"
echo

echo "### 1. 抽取染色体"
timed_sh "抽取染色体" "$SEQ_GB" "samtools faidx '$FASTA' '$CHROM' > chr.fa && samtools faidx chr.fa"
echo "### 2. 模拟读段"
timed_sh "读段模拟(numpy)" "$SEQ_GB" "python3 sim.py chr.fa $NPAIRS $RL $INS $SEED"
echo "### 3. bwa-mem2 index（一次性成本）"
timed_sh "bwa-mem2 index(一次性)" "$SEQ_GB" "bwa-mem2 index chr.fa"
echo "### 4. bwa-mem2 mem -t $THREADS"
timed_sh "bwa-mem2 mem -t$THREADS" "$SEQ_GB" "bwa-mem2 mem -t $THREADS chr.fa r1.fq r2.fq > aln.sam 2> map.log"
echo "### 5. samtools sort"
timed_sh "samtools sort" "$SEQ_GB" "samtools view -b aln.sam | samtools sort -m 1G -@ $THREADS -o aln.bam -"
samtools index aln.bam
echo "### 6. → CRAM"
timed_sh "→ CRAM" "$SEQ_GB" "samtools view -C -T chr.fa -@ $THREADS -o aln.cram aln.bam"
echo "### 7. mosdepth"
timed_sh "mosdepth" "$SEQ_GB" "mosdepth -t 4 -b 1000 depth_out aln.bam"
echo "### 8. bcftools mpileup|call"
timed_sh "bcftools mpileup|call" "$SEQ_GB" "bcftools mpileup -f chr.fa -Ou aln.bam | bcftools call -mv -Ov -o calls.vcf"
echo "### 9. KMC k=31"
timed_sh "KMC k=31" "$SEQ_GB" "kmc -k31 -t$THREADS -m4 -ci1 r1.fq kmc_out ."
echo

NVAR=$(grep -vc '^#' calls.vcf 2>/dev/null || echo 0)
echo "### 产物大小"
printf "  %-14s %s\n" "BAM" "$(du -h aln.bam 2>/dev/null | cut -f1)"
printf "  %-14s %s\n" "CRAM" "$(du -h aln.cram 2>/dev/null | cut -f1)"
printf "  %-14s %s\n" "检出变异" "$NVAR 个（⚠️ 合成读段源自参考本身，这些是测序错误造成的假阳性）"
printf "  %-14s %s\n" "工作目录" "$(du -sh "$WORK" | cut -f1)"
echo

python3 - "$TLOG" "$FACTOR" "$GENOME_MB" <<'PY'
import sys
log, factor, gmb = sys.argv[1], float(sys.argv[2]), sys.argv[3]
rows = []
for line in open(log):
    p = line.rstrip('\n').split('\t')
    if len(p) < 6: continue
    label, gb, W, U, S, M = p[0], float(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5])
    rows.append((label, gb, W, U, S, M))

print("############################################################")
print("# 本机实测（16 线程，1 号染色体 @ 10x）")
print("############################################################")
print(f"{'步骤':<24}{'墙钟(s)':>9}{'CPU(s)':>9}{'峰值内存':>10}{'墙钟吞吐':>13}")
print("-"*66)
for label, gb, W, U, S, M in rows:
    cpu = U + S
    tp = f"{gb/W*3600:.1f} Gb/h" if W > 0.05 else "太快无法测"
    print(f"{label:<24}{W:>9.1f}{cpu:>9.1f}{M/1024:>9.0f}M{tp:>13}")
print("-"*66)

print()
print("############################################################")
print(f"# 外推：单样本 {gmb} Mb 全基因组 @ 10x（x{factor:.3f}）")
print("#   核时 = (user+sys) x 外推系数 —— 成本模型的直接输入")
print("############################################################")
print(f"{'步骤':<24}{'墙钟(s)':>10}{'核时':>9}{'占比':>8}")
print("-"*53)
tw, tc, total_c, total_w = 0.0, 0.0, 0.0, 0.0
lines = []
for label, gb, W, U, S, M in rows:
    if label.endswith("(一次性)"):   # 索引是每参考一次，不算进每样本成本
        continue
    c = (U + S) * factor / 3600.0
    w = W * factor
    lines.append((label, w, c)); total_c += c; total_w += w
for label, w, c in lines:
    print(f"{label:<24}{w:>10.1f}{c:>9.3f}{c/total_c*100:>7.1f}%")
print("-"*53)
print(f"{'合计（串行）':<24}{total_w:>10.1f}{total_c:>9.3f}{100.0:>7.1f}%")
print()
print(f"  → 单样本 10x 全基因组：墙钟 {total_w/60:.1f} 分钟，CPU {total_c:.2f} 核时")
print(f"  → 10 个样本：CPU {total_c*10:.1f} 核时")
print(f"  → 100 个样本：CPU {total_c*100:.1f} 核时")
print(f"  → 1000 个样本：CPU {total_c*1000:.1f} 核时")
PY

echo
echo "############################################################"
echo "# ⚠️ 乐观性说明（务必在引用这些数字时一并说明）"
echo "# 1. 合成读段来自参考序列本身 → 无真实变异，mpileup 工作量偏小"
echo "# 2. CRAM 因此压得极小，**不能**用它推算存储需求"
echo "# 3. 均匀 10x 覆盖、读段唯一比对，真实数据更慢（重复序列/多重比对/接头）"
echo "# 4. 未包含 fastp 质控、去重、以及 ulcWGS 降采样等步骤"
echo "# 5. 结论：这是**成本下界**，真实数据预计再慢 2-3 倍"
echo "############################################################"
echo "### BENCH2_DONE"
