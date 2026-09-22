#!/usr/bin/env bash
# bench_run.sh —— 激活 ricevar 环境后运行 bench.sh
# 存在的意义：避免 `wsl.exe ... bash -lc "..."` 的嵌套引号转义问题
source /opt/miniconda3/etc/profile.d/conda.sh
if ! conda activate ricevar 2>/dev/null; then
  echo "❌ conda activate ricevar 失败"; exit 1
fi
echo "### 环境: $CONDA_DEFAULT_ENV | python: $(python -V 2>&1) | 线程: $(nproc)"
echo
exec bash /mnt/d/dsh/RiceVar-ID/scripts/bench.sh
