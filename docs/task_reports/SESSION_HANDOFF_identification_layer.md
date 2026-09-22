任务：服务器流水线接线 + 评估层落地（完成）

## 本轮完成
1. `server/07_identify.sh`：新增识别评估阶段。从 `marker_genotype_manifest.tsv` 收集低深度定点 VCF，
   生成真值表，对 500/1000/2000 三个 marker 数分别调用
   `scripts/evaluate_identification.py`，汇总 `identification_by_depth.tsv`。
2. `server/config.sh`：新增 `RV_MARKER`（冻结 marker）与 `RV_ANALYSIS`（评估结果）根目录，并纳入 `init_dirs`。
3. `server/06_export.sh`：新增第 4 步导出 `markers/`（冻结 marker + ranking + selection.json）与
   `identification/`（per_query/summary/by_depth），README 写明闭集/开放集边界。
4. `server/run_all.sh`：阶段表加入 `07_identify`。
5. `scripts/verify_undergraduate_scope.py`：45 → 60 项检查。
6. `scripts/verify_stage_order.py`：新增 23 项阶段顺序检查。
7. 文档同步：`docs/STATUS.md`、`docs/methods/server_pilot_runbook.md`、
   `docs/methods/snp_evaluation_design.md`、`PROJECT_STRUCTURE.md`、
   `UNDERGRADUATE_TASK_LIST.md`（TASK-032/033 由 ⬜ 改为 🔶）、
   `docs/task_reports/UNDERGRADUATE_SCOPE_MIGRATION_report.md`。
8. `.learnings/LEARNINGS.md`：新增 LRN-003、LRN-004。

## 本轮发现并修复的两个真实缺陷
1. **`run_all.sh` 会静默跳过联合 SNP calling。**
   原用 `[ "$num" \< "$FROM" ]` 做字符串比较，而 `"04_joint_snp" < "04_variant_depth"`，
   因此 `bash run_all.sh 04` 会跳过 `04_joint_snp`——即产出 cohort VCF 的关键阶段。
   流水线会"成功"结束却没有 SNP 结果。已改为按数组下标判断，并加回归测试固化。
2. **`GenotypeMatrix.project` 投影错列。**
   列映射建立在 query 自己的位点顺序上，而非目标冻结 marker 顺序，导致投影后数值错位。
   后果是所有低深度指纹都拿错误位点比对：不会报错，只会给出看似合理但无意义的相似度。
   由合成测试的精确行断言 `[0, -1, 2]` 捕获，已修复。

## 验证结果
- `python scripts/verify_undergraduate_scope.py` → 60 passed, 0 failed
- `python scripts/round1_verify.py` → 0 failed（28 项）
- `python scripts/verify_stage_order.py` → 0 failed（23 项）
- `python -m unittest discover -s tests` → Ran 20 tests, OK (skipped=2)，退出码 0
- `python -m py_compile` 全部新建/修改模块通过
- 清理：删除重构遗留的死变量 `STARTED`；删除临时 `build/` 目录

## 未验证 / 硬阻塞（不得声称）
- 从未在真实服务器执行；无 FASTQ、无参考基因组、无 QC/比对/CRAM/联合 SNP/降采样真实结果
- 本机无可用 Bash，Linux `bash -n` 与 bcftools/samtools 命令仍未实跑
- 阻塞项：调度器未知、`www.ebi.ac.uk` 可达性未知、存储配额未知、`00_probe.sh` 未运行
- 尚无任何真实 recall / Top-1 / Top-5 / 拒识数字；TASK-032/033 仍为 🔶

## 下一步
1. 服务器管理员回答 `docs/server_admin_questions.md` 或运行 `server/00_probe.sh`
2. 上传 `server/` + `pilot_smoke1.tsv` → 单样本端到端 → `pilot_smoke5.tsv` → 审查 QC/联合 calling
3. `pilot_manifest.tsv`（30 份）→ 冻结 marker 与阈值（仅用 Pilot）→ `07_identify.sh` 出闭集曲线
4. 用独立 25 面板做开放集拒识
5. 之后：PCA/热图/指纹图、SQLite + Streamlit 原型、论文与 PPT
