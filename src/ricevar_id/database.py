"""RiceVar-ID 品种指纹数据库（TASK-041）。

设计约束
--------
* **只写入真实产物**。任何缺失的输入都只会让对应表为空，绝不生成占位数据、
  也绝不用模拟值填充——空库比假库更诚实，查询层会明确回报"无数据"。
* 纯标准库（sqlite3），与 ``src/ricevar_id`` 其余模块保持一致；
  本机 Python 3.7 无 numpy/pandas，不能依赖它们。
* 基因型编码沿用全项目约定：``0/1/2`` 为剂量，``-1`` 为缺失(NA)。
  数据库层不做任何插补。

表结构
------
``sample``      样本 → 品种/亚种/run 的映射（来自冻结 manifest）
``marker``      冻结 marker 集（来自 pilot.markers_<n>.vcf）
``genotype``    参考基因型矩阵（来自 pilot.genotypes_<n>.tsv）
``evaluation``  低深度识别评估结果（来自 identification per_query.tsv）
``metadata``    建库溯源：输入文件 SHA256、行数、建库时间
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from .genotypes import MISSING, parse_marker_id, read_matrix_tsv

SCHEMA_VERSION = "1"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS metadata (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sample (
    sample_id    TEXT PRIMARY KEY,
    variety_name TEXT,
    subspecies   TEXT,
    run_accession TEXT,
    panel_role   TEXT
);

CREATE INDEX IF NOT EXISTS idx_sample_variety ON sample (variety_name);

CREATE TABLE IF NOT EXISTS marker (
    marker_id TEXT PRIMARY KEY,
    chrom     TEXT NOT NULL,
    pos       INTEGER NOT NULL,
    ref       TEXT NOT NULL,
    alt       TEXT NOT NULL,
    marker_set TEXT NOT NULL          -- 例如 'pilot.2000'
);

CREATE INDEX IF NOT EXISTS idx_marker_set ON marker (marker_set);

CREATE TABLE IF NOT EXISTS genotype (
    sample_id TEXT NOT NULL,
    marker_id TEXT NOT NULL,
    dosage    INTEGER NOT NULL,       -- 0/1/2，-1 = 缺失(NA)
    PRIMARY KEY (sample_id, marker_id),
    FOREIGN KEY (sample_id) REFERENCES sample (sample_id),
    FOREIGN KEY (marker_id) REFERENCES marker (marker_id)
);

CREATE INDEX IF NOT EXISTS idx_genotype_marker ON genotype (marker_id);

CREATE TABLE IF NOT EXISTS evaluation (
    query_id             TEXT NOT NULL,
    marker_count         INTEGER NOT NULL,
    depth_label          TEXT,
    best_reference_id    TEXT,
    best_similarity      REAL,
    n_compared_markers   INTEGER,
    compared_marker_rate REAL,
    n_different_markers  INTEGER,
    marker_recall        REAL,
    genotype_concordance REAL,
    top1_correct_sample  INTEGER,
    top1_correct_variety INTEGER,
    top5_correct_variety INTEGER,
    accepted             INTEGER,
    PRIMARY KEY (query_id, marker_count)
);

CREATE INDEX IF NOT EXISTS idx_evaluation_depth ON evaluation (depth_label);
"""


def sha256_file(path):
    """流式计算 SHA256，避免把大文件读进内存。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connect(db_path):
    """打开（或创建）数据库并确保 schema 存在。"""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn


def _set_metadata(conn, key, value):
    # ``INSERT OR REPLACE`` rather than ``ON CONFLICT DO UPDATE``: upsert syntax
    # needs SQLite >= 3.24, and the bundled SQLite on the local Python is 3.21.
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", (key, str(value)))


def load_manifest(conn, manifest_path):
    """从冻结服务器清单导入样本。返回导入行数。"""
    with open(manifest_path, encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        index = {name: i for i, name in enumerate(header)}
        required = {"sample_id", "variety_name"}
        missing = required - set(index)
        if missing:
            raise ValueError("清单缺少必需列: %s" % ", ".join(sorted(missing)))

        def cell(fields, name):
            position = index.get(name)
            if position is None or position >= len(fields):
                return None
            value = fields[position]
            return value or None

        rows = []
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if not fields or not fields[0]:
                continue
            rows.append((
                cell(fields, "sample_id"),
                cell(fields, "variety_name"),
                cell(fields, "subspecies"),
                cell(fields, "run_accession"),
                cell(fields, "panel_role"),
            ))

    conn.executemany(
        "INSERT OR REPLACE INTO sample "
        "(sample_id, variety_name, subspecies, run_accession, panel_role) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def load_markers(conn, matrix):
    """把基因型矩阵的位点写入 marker 表。返回位点数。"""
    rows = []
    for marker_id in matrix.markers:
        chrom, pos, ref, alt = parse_marker_id(marker_id)
        rows.append((marker_id, chrom, pos, ref, alt, matrix.marker_set))
    conn.executemany(
        "INSERT OR IGNORE INTO marker (marker_id, chrom, pos, ref, alt, marker_set) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def load_genotypes(conn, matrix):
    """写入参考基因型矩阵。返回 (样本数, 位点数, 非缺失记录数)。

    缺失值以 ``-1`` 原样入库，不做插补——识别时的缺失语义必须在查询层保留。
    """
    rows = []
    called = 0
    for sample_id in matrix.samples:
        row = matrix.row_for(sample_id)
        for marker_id, dosage in zip(matrix.markers, row):
            if dosage != MISSING:
                called += 1
            rows.append((sample_id, marker_id, int(dosage)))
    conn.executemany(
        "INSERT OR REPLACE INTO genotype (sample_id, marker_id, dosage) VALUES (?, ?, ?)",
        rows,
    )
    return len(matrix.samples), len(matrix.markers), called


def load_evaluation(conn, per_query_path):
    """导入识别评估的 per_query.tsv。返回导入行数。

    只接受脚本真实产出的列；缺失列按 NULL 处理，不臆造数值。
    """
    wanted = [
        "query_id", "marker_count", "depth_label", "best_reference_id",
        "best_similarity", "n_compared_markers", "compared_marker_rate",
        "n_different_markers", "marker_recall", "genotype_concordance",
        "top1_correct_sample", "top1_correct_variety", "top5_correct_variety",
        "accepted",
    ]
    with open(per_query_path, encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        index = {name: i for i, name in enumerate(header)}
        if "query_id" not in index:
            raise ValueError("per_query.tsv 缺少 query_id 列")

        def value(fields, name):
            position = index.get(name)
            if position is None or position >= len(fields):
                return None
            text = fields[position]
            if text in ("", "nan", "NaN", "None"):
                return None
            if name in ("marker_count", "n_compared_markers", "n_different_markers"):
                return int(float(text))
            if name in ("top1_correct_sample", "top1_correct_variety",
                        "top5_correct_variety", "accepted"):
                return int(text.lower() in ("1", "true", "yes"))
            if name == "depth_label":
                return text
            if name in ("best_reference_id",):
                return text
            return float(text)

        rows = [tuple(value(line.rstrip("\n").split("\t"), name) for name in wanted)
                for line in handle if line.strip()]

    conn.executemany(
        "INSERT OR REPLACE INTO evaluation (%s) VALUES (%s)"
        % (", ".join(wanted), ", ".join("?" * len(wanted))),
        rows,
    )
    return len(rows)


def build_database(db_path, matrix_tsv, manifest_path,
                   marker_vcf=None, per_query_path=None, marker_set=None):
    """构建数据库。返回统计字典。

    ``matrix_tsv`` 与 ``manifest_path`` 必需；``marker_vcf`` 与 ``per_query_path``
    为可选——缺失时对应来源信息记为 ``absent``，不伪造。
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    matrix = read_matrix_tsv(matrix_tsv, marker_set=marker_set)
    conn = connect(db_path)
    try:
        stats = {}
        stats["samples"] = load_manifest(conn, manifest_path)
        stats["markers_declared"] = load_markers(conn, matrix)
        n_samples, n_markers, called = load_genotypes(conn, matrix)
        stats["matrix_samples"] = n_samples
        stats["matrix_markers"] = n_markers
        stats["called_genotypes"] = called
        stats["total_genotypes"] = n_samples * n_markers
        stats["call_rate"] = (called / float(n_samples * n_markers)) if n_samples and n_markers else None
        stats["evaluation_rows"] = load_evaluation(conn, per_query_path) if per_query_path else 0

        _set_metadata(conn, "schema_version", SCHEMA_VERSION)
        _set_metadata(conn, "matrix_tsv", matrix_tsv)
        _set_metadata(conn, "matrix_sha256", sha256_file(matrix_tsv))
        _set_metadata(conn, "manifest", manifest_path)
        _set_metadata(conn, "manifest_sha256", sha256_file(manifest_path))
        _set_metadata(conn, "marker_set", matrix.marker_set)
        _set_metadata(conn, "marker_vcf", marker_vcf or "absent")
        if marker_vcf:
            _set_metadata(conn, "marker_vcf_sha256", sha256_file(marker_vcf))
        _set_metadata(conn, "per_query", per_query_path or "absent")
        if per_query_path:
            _set_metadata(conn, "per_query_sha256", sha256_file(per_query_path))
        _set_metadata(conn, "missing_encoding", "-1 = NA（不做插补）")
        conn.commit()
        return stats
    finally:
        conn.close()
