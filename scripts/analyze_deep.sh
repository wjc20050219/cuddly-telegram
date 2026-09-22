#!/usr/bin/env bash
# analyze_deep.sh —— 分析 ENA 深测序清单，产出可用候选池
# 服务于 TASK-009（ENA 检索）与 TASK-010（DDBJ 数据可达性）
set -uo pipefail
DIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
F="$DIR/ena_rice_wgs_deep_runs.tsv"
GS=375000000

echo "===== ENA 深度清单（>=5x）分析 ====="
echo "总记录：$(( $(wc -l < "$F") - 1 ))"
echo

echo "----- 1. 测序平台 -----"
awk -F'\t' 'NR>1{p[$6]++} END{for(k in p) printf "  %-20s %d\n", k, p[k]}' "$F" | sort -k2 -rn

echo
echo "----- 2. 文库布局 -----"
awk -F'\t' 'NR>1{p[$8]++} END{for(k in p) printf "  %-20s %d\n", k, p[k]}' "$F" | sort -k2 -rn

echo
echo "----- 3. 深度分布（>=5x 内部再分箱）-----"
awk -F'\t' 'NR>1 && $12!="" {d=$12/375000000; if(d<10)b["5-10x"]++; else if(d<20)b["10-20x"]++; else if(d<30)b["20-30x"]++; else if(d<50)b["30-50x"]++; else b[">=50x"]++} END{for(k in b) printf "  %-20s %d\n", k, b[k]}' "$F" | sort

echo
echo "----- 4. ★ 按数据库来源统计（accession 前缀 = 提交库）-----"
echo "  INSDC 三个成员库的 accession 前缀约定："
echo "    SRR/SRP/SRS = NCBI SRA (美国)"
echo "    ERR/ERP/ERS = ENA (欧洲)"
echo "    DRR/DRP/DRS = DDBJ DRA (日本)   ← TASK-010 关注"
awk -F'\t' 'NR>1{acc=$1; p=substr(acc,1,3); if(p=="SRR")b["NCBI SRA (SRR)"]++; else if(p=="ERR")b["ENA (ERR)"]++; else if(p=="DRR")b["DDBJ DRA (DRR)"]++; else b["other: "p]++} END{for(k in b) printf "  %-24s %d\n", k, b[k]}' "$F" | sort -k2 -rn
echo

echo "----- 5. 深清单中 DDBJ (DRR) 记录的提交时间分布 -----"
awk -F'\t' 'NR>1 && substr($1,1,3)=="DRR" && $14!="" {split($14,a,"-"); y[a[1]]++} END{for(k in y) printf "  %-8s %d\n", k, y[k]}' "$F" | sort

echo
echo "----- 6. 品种名可用性筛选 -----"
echo "  6.1 剔除疑似"育种行编号"（形如 N1-10-8D / Nx-2-44B）后的可用样本（深度 >=10x）："
awk -F'\t' 'NR>1 && $12/375000000>=10 && $16!"" {
  t=$16
  if (t ~ /^N[0-9xX]+-[0-9]+-[0-9]+[A-Z]$/) next      # 育种行编号
  if (t ~ /^Plant sample from Oryza sativa$/) next    # 无信息占位
  if (t ~ /^WGS sequence of/) next                    # 无信息占位
  n++
} END{printf "    %d\n", n+0}' "$F"

echo "  6.2 可用样本按提交中心（前 15）："
awk -F'\t' 'NR>1 && $12/375000000>=10 && $16!"" {
  t=$16
  if (t ~ /^N[0-9xX]+-[0-9]+-[0-9]+[A-Z]$/) next
  if (t ~ /^Plant sample from Oryza sativa$/) next
  if (t ~ /^WGS sequence of/) next
  c[$13]++
} END{for(k in c) printf "  %-46s %d\n", k, c[k]}' "$F" | sort -k2 -rn | head -15

echo
echo "----- 7. 深度 >=10x 的随机 30 个品种名 -----"
awk -F'\t' 'NR>1 && $12/375000000>=10 && $16!"" {print $16}' "$F" | shuf -n 30 | sed 's/^/  /'

echo
echo "----- 8. 已知栽培品种名是否命中（抽查知名度高的品种）-----"
for v in Nipponbare Koshihikari IR64 IR8 NIP 93-11 Basmati Huanghuazhan Kitaake Zhonghua11 Kasalath; do
  n=$(awk -F'\t' -v V="$v" 'NR>1 && tolower($16) ~ tolower(V) {n++} END{print n+0}' "$F")
  printf '  %-16s %s\n' "$v" "$n"
done
