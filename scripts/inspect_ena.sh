#!/usr/bin/env bash
# inspect_ena.sh —— 检查 ENA 检索结果的数据质量（TASK-009 辅助）
set -uo pipefail
DIR="/mnt/d/dsh/RiceVar-ID/data/metadata/search"
F="$DIR/ena_rice_wgs_runs.tsv"
GS=375000000   # IRGSP-1.0 单倍体基因组大小

echo "===== ENA 检索结果数据质量检查 ====="
echo "文件：$F"
echo "总行数（不含表头）：$(( $(wc -l < "$F") - 1 ))"
echo

echo "----- 1. 前 3 行原始样例（按列裁剪）-----"
head -4 "$F" | cut -c1-300
echo

echo "----- 2. 推算深度 >= 5x 且为 Illumina 配对的 run（按深度降序前 20）-----"
awk -F'\t' 'NR==1{next} $12!="" && $12/375000000>=5 && $6=="ILLUMINA" && $8=="PAIRED" {printf "%.1fx\t%s\t%s\t%s\t%s\t%s\t%s\n", $12/375000000, $1, $7, $13, $15, $16, $17}' "$F" \
  | sort -rn | head -20 \
  | awk -F'\t' '{printf "  %-8s %-13s %-24s %-16s %-22s %s\n", $1, $2, $3, $4, $6, $7}'
echo

echo "----- 3. sample_title 非空的样本数 -----"
awk -F'\t' 'NR>1 && $16!="" {n++} END{print "  " n+0}' "$F"

echo "----- 4. sample_title 长度分布（反映品种名可用性）-----"
awk -F'\t' 'NR>1 && $16!="" {L=length($16); if(L<=3)b["<=3 字符"]++; else if(L<=8)b["4-8 字符"]++; else if(L<=20)b["9-20 字符"]++; else b[">20 字符"]++} END{for(k in b) printf "  %-14s %d\n", k, b[k]}' "$F" | sort

echo "----- 5. sample_title 随机 25 例（看是否含品种名）-----"
awk -F'\t' 'NR>1 && $16!="" {print $16}' "$F" | shuf -n 25 | sed 's/^/  /'

echo "----- 6. 按 center_name 统计（提交中心，识别 DDBJ 来源）-----"
awk -F'\t' 'NR>1 && $13!="" {c[$13]++} END{for(k in c) printf "  %-46s %d\n", k, c[k]}' "$F" | sort -k2 -rn | head -20

echo "----- 7. 各深度区间可用的品种名样本数（>=5x）-----"
awk -F'\t' 'NR>1 && $12!="" {d=$12/375000000; if(d>=5 && $16!="") n++} END{printf "  >=5x 且有 sample_title：%d\n", n+0}' "$F"
awk -F'\t' 'NR>1 && $12!="" {d=$12/375000000; if(d>=10 && $16!="") n++} END{printf "  >=10x 且有 sample_title：%d\n", n+0}' "$F"
awk -F'\t' 'NR>1 && $12!="" {d=$12/375000000; if(d>=10 && $16!="" && $17!="") n++} END{printf "  >=10x 且有 title+alias：%d\n", n+0}' "$F"
