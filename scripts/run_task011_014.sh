#!/usr/bin/env bash
# run_task011_014.sh —— 顺序执行 TASK-011 ~ TASK-014 全链路
#
# 依赖顺序：011 建候选表 -> 012 名称标准化 -> 013 重复检查 -> 014 建面板
# 任一步失败即停止并报告（不跳过失败步骤）。
set -uo pipefail
cd /mnt/d/dsh/RiceVar-ID || exit 1

STEPS=(
  "task011_build_candidates"
  "task012_variety_alias"
  "task013_duplicates"
  "task014_panels"
)

echo "===== TASK-011 ~ TASK-014 全链路 ====="
echo "时间：$(date '+%F %T')"
echo

FAIL=0
for s in "${STEPS[@]}"; do
  echo "--------------------------------------------------------------------"
  echo ">>> $s"
  echo "--------------------------------------------------------------------"
  if python3 -u "scripts/$s.py"; then
    echo ">>> $s : OK"
  else
    echo ">>> $s : *** 失败 ***"
    FAIL=1
    break
  fi
  echo
done

echo "====="
if [ "$FAIL" -eq 0 ]; then
  echo "全部完成"
else
  echo "中断：有步骤失败，未继续后续步骤"
fi
exit "$FAIL"
