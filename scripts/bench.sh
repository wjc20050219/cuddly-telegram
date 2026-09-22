#!/usr/bin/env bash
# bench.sh - measure real mapping/sort throughput on THIS machine (rice-scaled estimate)
# Run: wsl -d Ubuntu -u root -- bash -lc 'source /opt/miniconda3/etc/profile.d/conda.sh && conda activate ricevar && bash /mnt/d/dsh/RiceVar-ID/scripts/bench.sh'
set -uo pipefail

WORK=${WORK:-/opt/bench}
THREADS=${THREADS:-16}
REF_MB=${REF_MB:-20}          # synthetic reference size
NPAIRS=${NPAIRS:-100000}      # read pairs (100k pairs x 150bp x2 = 30 Mb sequence)
READLEN=150

rm -rf "$WORK"; mkdir -p "$WORK"; cd "$WORK"

echo "=== ENV ==="
nproc; free -g | head -n2; df -h /opt | tail -n1

echo "=== STEP 1: make synthetic reference (${REF_MB} Mb) ==="
python3 - "$REF_MB" <<'PY'
import random, sys
mb = int(sys.argv[1])
random.seed(42)
out = open("ref.fa", "w")
out.write(">chrSyn\n")
chunk = 100000
written = 0
while written < mb * 1_000_000:
    n = min(chunk, mb * 1_000_000 - written)
    out.write("".join(random.choices("ACGT", k=n)))
    out.write("\n")
    written += n
out.close()
print("reference written:", mb, "Mb")
PY
ls -la ref.fa

echo "=== STEP 2: bwa-mem2 index build (timed) ==="
/usr/bin/time -v bwa-mem2 index ref.fa 2>&1 | grep -E "Elapsed|Maximum resident" || { t0=$(date +%s); bwa-mem2 index ref.fa; t1=$(date +%s); echo "INDEX_SECONDS=$((t1-t0))"; }

echo "=== STEP 3: simulate ${NPAIRS} read pairs ==="
python3 - "$NPAIRS" "$READLEN" <<'PY'
import random, sys
npairs, rl = int(sys.argv[1]), int(sys.argv[2])
random.seed(7)
seq = []
with open("ref.fa") as f:
    f.readline()
    for line in f:
        seq.append(line.strip())
seq = "".join(seq)
L = len(seq)
comp = str.maketrans("ACGT", "TGCA")
r1 = open("r1.fq", "w"); r2 = open("r2.fq", "w")
for i in range(npairs):
    p = random.randrange(0, L - 500)
    frag = list(seq[p:p+500])
    for _ in range(3):                      # ~0.6% error
        j = random.randrange(0, 500)
        frag[j] = random.choice("ACGT")
    a = "".join(frag[:rl])
    b = "".join(frag[500-rl:])[::-1].translate(comp)
    r1.write(f"@r{i}/1\n{a}\n+\n{'I'*rl}\n")
    r2.write(f"@r{i}/2\n{b}\n+\n{'I'*rl}\n")
r1.close(); r2.close()
print("simulated pairs:", npairs, "=> sequence Mb:", npairs*2*rl/1e6)
PY

echo "=== STEP 4: bwa-mem2 mem mapping -t $THREADS (timed) ==="
t0=$(date +%s)
bwa-mem2 mem -t "$THREADS" ref.fa r1.fq r2.fq > aln.sam 2> map.log
t1=$(date +%s)
MAP_SECONDS=$((t1-t0))
SEQ_MB=$(python3 -c "print($NPAIRS*2*$READLEN/1e6)")
echo "MAP_SECONDS=$MAP_SECONDS  SEQ_MB=$SEQ_MB"
python3 -c "print('THROUGHPUT_Gb_per_hour=%.2f' % ($SEQ_MB/1000*3600/$MAP_SECONDS))"
grep -E "real|CPU" map.log | head -n3 || true

echo "=== STEP 5: samtools sort -m 1G -@ 8 (timed) ==="
t0=$(date +%s)
samtools view -b aln.sam 2>/dev/null | samtools sort -m 1G -@ 8 -o aln.sorted.bam - 2>/dev/null
t1=$(date +%s)
SORT_SECONDS=$((t1-t0))
echo "SORT_SECONDS=$SORT_SECONDS"
python3 -c "print('SORT_THROUGHPUT_Gb_per_hour=%.2f' % ($SEQ_MB/1000*3600/$SORT_SECONDS))"

echo "=== STEP 6: index + depth (mosdepth, timed) ==="
samtools index aln.sorted.bam
t0=$(date +%s); mosdepth -t 4 -b 1000 depth_out aln.sorted.bam 2>/dev/null; t1=$(date +%s)
echo "MOSDOWDEX_SECONDS=$((t1-t0))"
head -n 3 depth_out.mosdepth.summary.txt || true

echo "=== STEP 7: KMC k=31 on r1.fq (timed) ==="
t0=$(date +%s)
kmc -k31 -t8 -m4 -ci1 r1.fq kmc_out . >/dev/null 2>&1
t1=$(date +%s)
echo "KMC_SECONDS=$((t1-t0))"
ls -la kmc_out* 2>/dev/null | head -n3

echo "=== STEP 8: bcftools mpileup|call (timed) ==="
t0=$(date +%s)
bcftools mpileup -f ref.fa -Ou aln.sorted.bam 2>/dev/null | bcftools call -mv -Ov -o calls.vcf 2>/dev/null
t1=$(date +%s)
echo "BCFTOOLS_SECONDS=$((t1-t0))"
grep -vc "^#" calls.vcf || true

echo "=== DISK USED BY BENCH ==="
du -sh "$WORK"
echo "=== BENCH_DONE ==="
