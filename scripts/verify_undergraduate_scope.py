#!/usr/bin/env python3
"""Static/data validation for the undergraduate RiceVar-ID scope."""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "data" / "metadata" / "server"
failures = []
passes = []


def check(condition, message):
    (passes if condition else failures).append(message)
    print("[%s] %s" % ("OK" if condition else "FAIL", message))


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


required_docs = [
    ROOT / "docs" / "UNDERGRADUATE_SCOPE.md",
    ROOT / "docs" / "methods" / "reference_genome_plan.md",
    ROOT / "docs" / "methods" / "snp_evaluation_design.md",
]
for path in required_docs:
    check(path.exists() and path.stat().st_size > 500, "document exists: %s" % path.relative_to(ROOT))

expected = {
    "pilot_manifest.tsv": 30,
    "pilot_smoke1.tsv": 1,
    "pilot_smoke5.tsv": 5,
    "independent_manifest.tsv": 25,
}
loaded = {}
for name, count in expected.items():
    path = SERVER / name
    rows = read_rows(path) if path.exists() else []
    loaded[name] = rows
    check(len(rows) == count, "%s has %d rows" % (name, count))
    check(all(r.get("run_accession") and r.get("fastq_ftp") for r in rows), "%s has accession and FASTQ URLs" % name)
    check(all(len(r.get("fastq_ftp", "").split(";")) == len(r.get("fastq_bytes", "").split(";")) for r in rows), "%s keeps URL/byte columns aligned" % name)
    check(all(r.get("paired_or_single") != "PAIRED" or len(r.get("fastq_ftp", "").split(";")) == 2 for r in rows), "%s paired rows contain exactly two FASTQs" % name)

pilot_names = {r["variety_name"] for r in loaded["pilot_manifest.tsv"]}
ind_names = {r["variety_name"] for r in loaded["independent_manifest.tsv"]}
check(not (pilot_names & ind_names), "Pilot and independent manifests have zero variety overlap")

pilot_ids = {r["sample_id"] for r in loaded["pilot_manifest.tsv"]}
check({r["sample_id"] for r in loaded["pilot_smoke1.tsv"]} <= pilot_ids, "smoke1 is a Pilot subset")
check({r["sample_id"] for r in loaded["pilot_smoke5.tsv"]} <= pilot_ids, "smoke5 is a Pilot subset")

summary_path = SERVER / "manifest_build_summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
check(summary.get("pilot_rows") == 30 and summary.get("independent_rows") == 25, "manifest summary records panel sizes")
check(summary.get("variety_overlap") == [], "manifest summary records zero overlap")

config = (ROOT / "server" / "config.sh").read_text(encoding="utf-8")
check('pilot_manifest.tsv' in config, "server default points to canonical Pilot manifest")
check('h["run_accession"]' in config, "server sample parsing is header based")
check('export -f log die marker' in config, "parallel workers inherit shared shell functions")

download = (ROOT / "server" / "02_download.sh").read_text(encoding="utf-8")
joint = (ROOT / "server" / "04_joint_snp.sh").read_text(encoding="utf-8")
export = (ROOT / "server" / "06_export.sh").read_text(encoding="utf-8")
matrix_builder = (ROOT / "server" / "build_matrices.py").read_text(encoding="utf-8")
run_all = (ROOT / "server" / "run_all.sh").read_text(encoding="utf-8")
check('sha256' in download and 'source_url' in download, "download log records SHA256 and source URL")
check('expected_ftps' in download, "downloader restricts files to the frozen manifest")
check('cohort.biallelic_snps.vcf.gz' in joint, "formal SNP stage creates a joint cohort VCF")
check('cohort_calling_state.tsv' in joint and 'signature' in joint, "joint VCF cache is keyed to the current cohort")
check('if [ "$n" -ge 2 ] && { [ -s "$RAW" ]' in joint, "single-sample smoke cannot invalidate a formal cohort VCF")
check('bm snp --vcf-glob' not in export, "export no longer merges variant-only single-sample VCFs")
check('--vcf-glob' not in matrix_builder and 'build_snp_matrix' not in matrix_builder, "unsafe legacy single-sample VCF merge command was removed")
check('rm -rf "$EX_GEN" "$EX_DEP" "$EX_SIM" "$EX_SIM_GENO" "$EX_MARKER" "$EX_IDENT"' in export, "export view is rebuilt to avoid stale cohort files")

sim = (ROOT / "server" / "05_simulate.sh").read_text(encoding="utf-8")
check('${seed}.${frac}' not in sim, "downsampling no longer creates an invalid seed.fraction string")
check('reads * rl * 2' not in sim, "fallback depth estimate does not double-count paired alignments")
check('-C alleles -T "$MARKER_TARGET"' in sim, "low-depth calling is constrained to frozen marker alleles")
check('-R "$MARKER_REGIONS"' in sim, "mpileup uses a separate two-column marker regions file")
check('actual_depth' in sim, "downsampling manifest records observed mosdepth depth")
check('markers.vcf.gz' in sim, "low-depth fixed-marker VCF output is defined")
target_script = (ROOT / "server" / "prepare_marker_targets.sh").read_text(encoding="utf-8")
check('cut -f1,2' in target_script and 'regions.tsv.gz' in target_script, "marker preparation separates allele and region targets")

fingerprint = ROOT / "src" / "ricevar_id" / "fingerprint.py"
check(fingerprint.exists(), "SNP fingerprint similarity module exists")
selector = (ROOT / "scripts" / "select_snp_markers.py").read_text(encoding="utf-8")
check('choices=["pilot"]' in selector, "marker selector enforces Pilot-only fitting")
check('500, 1000, 2000' in selector, "marker selector defaults to 500/1000/2000 nested panels")

# ---- 识别评估层：低深度 VCF → recall / 识别率 / 拒识 ----
genotypes = ROOT / "src" / "ricevar_id" / "genotypes.py"
check(genotypes.exists(), "genotype matrix reader module exists")
genotypes_text = genotypes.read_text(encoding="utf-8") if genotypes.exists() else ""
check("def project(" in genotypes_text, "query genotypes are aligned onto the frozen marker set")
check("outside the frozen set" in genotypes_text, "query VCFs outside the frozen marker set are rejected")

evaluate = ROOT / "scripts" / "evaluate_identification.py"
check(evaluate.exists(), "identification evaluation script exists")
evaluate_text = evaluate.read_text(encoding="utf-8") if evaluate.exists() else ""
check("marker_recall" in evaluate_text and "identify_top_k" in evaluate_text, "evaluation reports recall and identification together")
check("top1_correct_variety" in evaluate_text and "top5_correct_variety" in evaluate_text, "evaluation scores Top-1 and Top-5 variety recovery")
check("does not represent independent" in evaluate_text, "evaluation output states its closed-set limitation")

identify = ROOT / "server" / "07_identify.sh"
check(identify.exists(), "server identification stage exists")
identify_text = identify.read_text(encoding="utf-8") if identify.exists() else ""
check("genotypes_sim/" in identify_text or "marker_genotype_manifest" in identify_text, "identification stage reads low-depth fixed-marker VCFs")
check("identification_truth.tsv" in identify_text, "identification stage derives truth from the frozen manifest")
check("开放集" in identify_text and "闭集" in identify_text, "identification stage labels closed-set vs open-set claims")

check("07_identify" in run_all, "pipeline orchestrator schedules the identification stage")
check("stage_index" in run_all, "orchestrator resolves stages by index, not string prefix")
check('"$EX_MARKER"' in export and '"$EX_IDENT"' in export, "export package includes markers and identification results")
check("RV_MARKER" in config and "RV_ANALYSIS" in config, "server config defines marker and analysis roots")

# ---- SQLite 指纹数据库与识别原型 ----
database = ROOT / "src" / "ricevar_id" / "database.py"
check(database.exists(), "SQLite fingerprint database module exists")
database_text = database.read_text(encoding="utf-8") if database.exists() else ""
check("-1 = NA" in database_text and "不做插补" in database_text,
      "database records that missing calls are stored as NA without imputation")
check("missing_encoding" in database_text, "database metadata documents the missing-value encoding")
check("absent" in database_text, "database marks missing optional inputs as absent instead of inventing rows")
check("UNIQUE (variety_name)" not in database_text,
      "database allows several samples to share one variety name")
check("sha256_file" in database_text, "database fingerprints every build input")

dbquery = ROOT / "src" / "ricevar_id" / "dbquery.py"
check(dbquery.exists(), "read-only fingerprint query layer exists")
dbquery_text = dbquery.read_text(encoding="utf-8") if dbquery.exists() else ""
check("def identify(" in dbquery_text and "def compare_varieties(" in dbquery_text,
      "query layer supports single-query identification and variety comparison")
check("def evaluation_by_depth(" in dbquery_text, "query layer exposes the depth-accuracy table")
check("identify_top_k" in dbquery_text,
      "query layer delegates scoring to the shared fingerprint module")
# 比较位点数与比较率由 fingerprint.py 的命中字典提供，不能在这一层重新定义。
fingerprint_text = (ROOT / "src" / "ricevar_id" / "fingerprint.py").read_text(encoding="utf-8")
check("n_compared_markers" in fingerprint_text and "compared_marker_rate" in fingerprint_text,
      "fingerprint hits always report the number of compared markers and the comparison rate")
# 用户输入进 SQL LIKE 前必须转义，否则 % 和 _ 会变成通配符。
check("_escape_like" in dbquery_text and "ESCAPE" in dbquery_text,
      "fuzzy variety search escapes LIKE metacharacters instead of treating them as wildcards")
check("def unlabelled_samples(" in dbquery_text,
      "query layer can report reference samples that have genotypes but no variety name")
check("best_match_lacks_variety" in dbquery_text,
      "identify() flags a best match that carries no variety name")

build_db = ROOT / "scripts" / "build_database.py"
check(build_db.exists(), "database build CLI exists")

query_input = ROOT / "src" / "ricevar_id" / "query_input.py"
check(query_input.exists(), "query table parser exists as testable library code")
query_input_text = query_input.read_text(encoding="utf-8") if query_input.exists() else ""
check("MISSING_TOKENS" in query_input_text, "query parser treats NA tokens as missing, not as reference")

app = ROOT / "app" / "streamlit_app.py"
check(app.exists(), "Streamlit prototype exists")
app_text = app.read_text(encoding="utf-8") if app.exists() else ""
check("数据库不存在" in app_text, "prototype refuses to render results without a real database")
check("闭集" in app_text, "prototype labels its results as closed-set")
check("本页面不会显示任何示例结果" in app_text,
      "prototype never displays placeholder results as if they were measurements")
check("比较位点数" in app_text, "prototype surfaces the compared-marker count alongside similarity")
check("best_match_lacks_variety" in app_text,
      "prototype warns when the nearest reference sample has no variety name")
check("unlabelled_samples" in app_text,
      "prototype reports reference samples that carry genotypes but no variety name")

check((ROOT / "tests" / "test_fingerprint_db.py").exists(), "database layer has unit tests")
check((ROOT / "tests" / "test_query_input.py").exists(), "query parser has unit tests")

# ---- 图表与论文骨架 ----
figures_script = ROOT / "scripts" / "make_figures.py"
check(figures_script.exists(), "figure generation script exists")
figures_text = figures_script.read_text(encoding="utf-8") if figures_script.exists() else ""
check("无真实数据时不产图" in figures_text,
      "figure script refuses to draw anything without real result files")
check("read_tsv" in figures_text and "跳过" in figures_text,
      "figure script reports and skips figures whose inputs are missing")

# ---- 相似度全矩阵导出（TASK-036/037 前置）----
export_script = ROOT / "scripts" / "export_similarity_matrix.py"
check(export_script.exists(), "pairwise similarity matrix exporter exists")
export_text = export_script.read_text(encoding="utf-8") if export_script.exists() else ""
check("compare_varieties" in export_text or "pairwise" in export_text,
      "exporter reuses the audited pairwise comparison rather than reimplementing it")
check("未用 0 填充" in export_text or "绝不用 0" in export_text or "空单元格" in export_text,
      "exporter documents that unusable pairs stay blank instead of becoming 0")
check("is_empty" in export_text,
      "exporter refuses to run against a database with no reference genotypes")
check((ROOT / "tests" / "test_export_similarity_matrix.py").exists(),
      "similarity matrix exporter has unit tests")
check("--similarity-matrix" in figures_text,
      "heatmap figure is wired to the exported similarity matrix")
check("def pca_2d(" in figures_text and "def fig_pca(" in figures_text,
      "PCA figure exists and computes components without numpy")
check("import math" in figures_text.split("def ")[0],
      "PCA support code imports the standard library rather than a numeric package")
check("prepare_pca_rows" in figures_text,
      "PCA input preparation is a named function so its imputation can be tested")
check("def pca_2d(" in figures_text and '"pca"' in figures_text,
      "pca is registered as a selectable figure")

thesis_dir = ROOT / "docs" / "thesis"
check((thesis_dir / "THESIS_DRAFT.md").exists(), "thesis draft skeleton exists")
check((thesis_dir / "DEFENSE_SLIDES.md").exists(), "defense slide outline exists")
check((thesis_dir / "PLACEHOLDER_CONVENTIONS.md").exists(),
      "placeholder conventions are documented so no fake numbers enter the thesis")

# ---- shell 静态分析（本机无 Bash，用 Python 兜底） ----
shell_analyzer = ROOT / "scripts" / "verify_shell_static.py"
check(shell_analyzer.exists(), "shell static analyzer exists (no Bash locally)")
shell_text = shell_analyzer.read_text(encoding="utf-8") if shell_analyzer.exists() else ""
check("REVIEWED_UNGUARDED" in shell_text,
      "unguarded-command baseline is explicit and reasoned, not silent")
check("heredoc" in shell_text,
      "analyzer skips heredoc bodies so literal text is not mistaken for code")
check("未定义变量" in shell_text and "未见失败保护" in shell_text,
      "analyzer covers undefined variables and unguarded critical commands")
# 反向测试**必须真的贡献测试用例**。
# 这里曾经只检查文件存在，而三个"反向验证"文件其实是模块级脚本：
# `unittest discover` 会 import 它们（执行子进程、写文件），
# 却收集到 0 个用例，所有判定只 print、失败被静默丢弃。
# "文件存在"因此完全不能证明"反向验证成立"。
reverse_tests = [
    "test_shell_static_detects.py",
    "test_selector_invariants_reverse.py",
    "test_eval_reverse.py",
]
_reverse_ok = True
_reverse_detail = []
for _name in reverse_tests:
    _path = ROOT / "tests" / _name
    if not _path.exists():
        _reverse_ok = False
        _reverse_detail.append("%s 不存在" % _name)
        continue
    _suite = unittest.TestLoader().discover(str(ROOT / "tests"), pattern=_name)
    _n = _suite.countTestCases()
    if _n == 0:
        _reverse_ok = False
        _reverse_detail.append("%s 贡献 0 个用例（判定会被丢弃）" % _name)
    else:
        _reverse_detail.append("%s=%d" % (_name, _n))
check(_reverse_ok,
      "analyzer has a reverse test proving it detects injected defects (%s)"
      % ", ".join(_reverse_detail))

# ---- 文档命令可执行性（本机无法运行服务器命令，至少在文档层面兜底） ----
doc_verifier = ROOT / "scripts" / "verify_documented_commands.py"
check(doc_verifier.exists(),
      "documented server commands are checked against the real CLI definitions")
doc_text = doc_verifier.read_text(encoding="utf-8") if doc_verifier.exists() else ""
check("--help" in doc_text and "FLAG" in doc_text,
      "documented flags are validated by asking each script for its real --help")
check("GENERATED_PREFIXES" in doc_text,
      "paths that the pipeline has not produced yet are not reported as broken")
check((ROOT / "tests" / "test_verify_documented_commands.py").exists(),
      "documentation verifier has tests proving it detects stale flags and paths")

# 05_simulate.sh 必须对降采样/分型的关键步骤显式判断失败，
# 否则失败的轮次会与成功的轮次在清单里无法区分。
sim_text = (ROOT / "server" / "05_simulate.sh").read_text(encoding="utf-8")
check("mosdepth 失败，本轮不计入清单" in sim_text,
      "downsampling round reports mosdepth failure instead of silently skipping")
check("marker VCF 索引失败，不计入分型清单" in sim_text,
      "genotyping round reports index failure instead of recording an unusable VCF")

# ---- 校验和必须是完整摘要 ----
# 截断的 SHA256 无法用于核对上游文件；文档曾据此声称 03_align.sh 只存 16 位，
# 实际脚本早已改为完整摘要。这里把"不得截断"变成机械不变量，
# 防止以后回退，也防止文档再次与脚本不符。
TRUNCATION_PATTERNS = ("cut -c1-16", "cut -c 1-16", "head -c16", "head -c 16",
                       "cut -c1-8", "[0:16]", "[:16]")
align_text = (ROOT / "server" / "03_align.sh").read_text(encoding="utf-8")
truncated = [p for p in TRUNCATION_PATTERNS if p in align_text]
check(not truncated,
      "reference checksums are recorded in full, never truncated (found: %s)" % (truncated or "none"))
check("gzip_sha256" in align_text and "fasta_sha256" in align_text,
      "reference record names both the compressed and the uncompressed checksum")
check(align_text.count("sha256sum") >= 2,
      "reference record checksums the gzip and the extracted FASTA independently")

print("Result: %d passed, %d failed" % (len(passes), len(failures)))
raise SystemExit(1 if failures else 0)
