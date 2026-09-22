#!/usr/bin/env bash
# fetch_rice_ref.sh —— 测试 WSL 外网连通性并下载水稻参考基因组 IRGSP-1.0
# 参考序列是 TASK-007 的硬依赖；顺带验证服务器下载路径所依赖的网络能力。
set -uo pipefail

REFDIR=${REFDIR:-/opt/ricevar/ref}
FA=Oryza_sativa.IRGSP-1.0.dna.toplevel.fa.gz
URL="https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-60/fasta/oryza_sativa/dna/${FA}"

mkdir -p "$REFDIR"; cd "$REFDIR" || exit 1

echo "=== 1. 网络连通性 ==="
for u in https://www.ebi.ac.uk/ https://ftp.ebi.ac.uk/ https://mirrors.tuna.tsinghua.edu.cn/ https://www.ncbi.nlm.nih.gov/ ; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "$u" 2>/dev/null)
  printf "  %-42s -> %s\n" "$u" "${code:-FAIL}"
done
echo

echo "=== 2. 下载参考基因组 ==="
if [ -s "$FA" ]; then
  echo "  已存在，跳过下载: $(du -h "$FA" | cut -f1)"
else
  echo "  来源: $URL"
  if curl -L --retry 3 --retry-delay 3 -m 1800 -# -o "$FA" "$URL"; then
    echo "  ✅ 下载完成: $(du -h "$FA" | cut -f1)"
  else
    echo "  ✗ 下载失败（退出码 $?）"; exit 1
  fi
fi
echo

echo "=== 3. 完整性校验 ==="
if gzip -t "$FA" 2>/dev/null; then
  echo "  ✅ gzip 完整性 OK"
else
  echo "  ✗ gzip 损坏"; exit 1
fi

echo
echo "=== 4. 解压 ==="
FASTA=${FA%.gz}
if [ -s "$FASTA" ]; then
  echo "  已存在: $(du -h "$FASTA" | cut -f1)"
else
  gunzip -kf "$FA"
  echo "  ✅ 解压完成: $(du -h "$FASTA" | cut -f1)"
fi

echo
echo "=== 5. 序列统计 ==="
if command -v seqkit >/dev/null 2>&1; then
  seqkit stats -a "$FASTA" 2>/dev/null | head -n 5
else
  echo "  (seqkit 不可用，用 grep 粗算)"
  echo "  序列条数: $(grep -c '^>' "$FASTA")"
  echo "  总碱基数: $(grep -v '^>' "$FASTA" | tr -d '\n' | wc -c)"
fi

echo
echo "=== 6. 各染色体长度（前 15 条）==="
awk '/^>/{if(n)print n": "l; n=$1; l=0; next}{l+=length($0)}END{if(n)print n": "l}' "$FASTA" | head -n 15

echo
echo "=== 7. fai 索引 ==="
if command -v samtools >/dev/null 2>&1; then
  samtools faidx "$FASTA" && echo "  ✅ samtools faidx 完成"
  head -n 14 "${FASTA}.fai" | awk '{printf "  %-16s %12s bp\n", $1, $2}'
fi

echo
echo "=== 8. 磁盘占用 ==="
du -sh "$REFDIR"
df -h /opt | tail -n1
echo "=== FETCH_DONE ==="
