"""Read-only queries over the RiceVar-ID fingerprint database (TASK-043~045).

The query layer is deliberately thin and honest: every function either returns
real stored data or an explicit empty result. It never fabricates a row, never
imputes a missing genotype, and always reports how many markers were actually
compared so a caller cannot mistake "few markers agreed" for "strong match".

Similarity is computed with :mod:`ricevar_id.fingerprint`, so the numbers a
query returns match the numbers in the evaluation tables exactly.
"""

from __future__ import annotations

from .fingerprint import identify_top_k
from .genotypes import MISSING, GenotypeMatrix


def _escape_like(text):
    """Escape SQL ``LIKE`` metacharacters so user input is matched literally.

    Backslash must be escaped first, otherwise the escapes added for ``%`` and
    ``_`` would themselves be doubled. Used together with ``ESCAPE '\\'``.
    """
    return (text.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_"))


class FingerprintDatabase:
    """Thin read-only wrapper around the SQLite fingerprint database."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False

    def close(self):
        self.conn.close()

    # ---------- 元信息 ----------
    def metadata(self):
        rows = self.conn.execute("SELECT key, value FROM metadata ORDER BY key").fetchall()
        return {key: value for key, value in rows}

    def counts(self):
        def one(sql):
            return self.conn.execute(sql).fetchone()[0]

        return {
            "samples": one("SELECT COUNT(*) FROM sample"),
            "varieties": one("SELECT COUNT(DISTINCT variety_name) FROM sample WHERE variety_name IS NOT NULL"),
            "markers": one("SELECT COUNT(*) FROM marker"),
            "genotypes": one("SELECT COUNT(*) FROM genotype"),
            "called_genotypes": one("SELECT COUNT(*) FROM genotype WHERE dosage >= 0"),
            "evaluation_rows": one("SELECT COUNT(*) FROM evaluation"),
        }

    def is_empty(self):
        """True when no reference genotypes exist — queries must then refuse."""
        return self.counts()["genotypes"] == 0

    # ---------- 品种与样本 ----------
    def list_varieties(self):
        """(variety_name, subspecies, n_samples)，按品种名排序。"""
        return self.conn.execute(
            "SELECT variety_name, MIN(subspecies), COUNT(*) FROM sample "
            "WHERE variety_name IS NOT NULL "
            "GROUP BY variety_name ORDER BY variety_name"
        ).fetchall()

    def find_variety(self, name, exact=True):
        """按名称查品种；默认精确匹配，否则做不区分大小写的包含匹配。

        模糊匹配必须转义 SQL ``LIKE`` 的通配符：用户输入的 ``%`` 或 ``_``
        是**字面字符**，不是通配符。否则搜 "Nip_pon" 会额外命中 "Nipponbare"
        （``_`` 匹配任意单字符），只输一个 ``%`` 更会列出整个库——那看起来
        像"查到了很多品种"，实际是查询语法泄漏。
        """
        if exact:
            return self.conn.execute(
                "SELECT variety_name, subspecies, sample_id, run_accession FROM sample "
                "WHERE variety_name = ? ORDER BY sample_id",
                (name,),
            ).fetchall()
        pattern = "%" + _escape_like(name) + "%"
        return self.conn.execute(
            "SELECT variety_name, subspecies, sample_id, run_accession FROM sample "
            "WHERE variety_name LIKE ? ESCAPE '\\' ORDER BY variety_name, sample_id",
            (pattern,),
        ).fetchall()

    def samples_of(self, variety_name):
        return self.conn.execute(
            "SELECT sample_id, run_accession FROM sample WHERE variety_name = ? ORDER BY sample_id",
            (variety_name,),
        ).fetchall()

    def unlabelled_samples(self):
        """Samples with no variety name.

        These are legitimate ENA records (an empty ``variety_name`` cell in the
        frozen manifest) and they still carry genotypes, so they take part in
        identification. They are excluded from every variety listing, which
        means a user cannot see them in the UI and cannot tell why a query
        matched "unknown". Callers must surface this count instead of silently
        presenting an unattributable best match.
        """
        return [row[0] for row in self.conn.execute(
            "SELECT sample_id FROM sample "
            "WHERE variety_name IS NULL OR TRIM(variety_name) = '' "
            "ORDER BY sample_id")]

    def reference_samples(self):
        """样本 ID 列表，顺序与参考矩阵一致（按 sample_id 排序保证可复现）。"""
        return [row[0] for row in self.conn.execute("SELECT sample_id FROM sample ORDER BY sample_id")]

    # ---------- 参考矩阵 ----------
    def reference_matrix(self, marker_ids=None):
        """构建参考 :class:`GenotypeMatrix`。

        ``marker_ids`` 为空时使用库中全部 marker。样本或 marker 顺序都显式
        排序，保证同一数据库多次查询得到完全一致的列序。
        """
        if marker_ids is None:
            marker_ids = [row[0] for row in self.conn.execute(
                "SELECT marker_id FROM marker ORDER BY marker_id")]
        else:
            marker_ids = list(marker_ids)
        samples = self.reference_samples()

        position = {marker: index for index, marker in enumerate(marker_ids)}
        table = {sample: [MISSING] * len(marker_ids) for sample in samples}
        for sample_id, marker_id, dosage in self.conn.execute(
            "SELECT sample_id, marker_id, dosage FROM genotype"
        ):
            column = position.get(marker_id)
            if column is None or sample_id not in table:
                continue
            table[sample_id][column] = dosage

        return GenotypeMatrix(samples, marker_ids, [table[s] for s in samples],
                              marker_set=self.metadata().get("marker_set"))

    def marker_ids(self, marker_set=None):
        if marker_set:
            rows = self.conn.execute(
                "SELECT marker_id FROM marker WHERE marker_set = ? ORDER BY marker_id", (marker_set,))
        else:
            rows = self.conn.execute("SELECT marker_id FROM marker ORDER BY marker_id")
        return [row[0] for row in rows]

    # ---------- 识别 ----------
    def identify(self, query, method="ibs", top_k=5, min_compared=50, reject_threshold=None,
                 marker_ids=None):
        """对一个 query :class:`GenotypeMatrix` 做闭集识别。

        query 会被投影到参考 marker 集上；投影会拒绝冻结集之外的位点，
        并把未覆盖位点记为缺失（绝不记为参考基因型）。

        返回 ``identify_top_k`` 的结果字典，其中每个命中都标注了对应品种名。
        """
        if self.is_empty():
            raise ValueError("数据库中没有参考基因型，无法识别；请先运行建库脚本")

        if isinstance(query, GenotypeMatrix):
            if query.n_markers == 0:
                raise ValueError("query 没有任何 marker")
            if len(query.samples) > 1:
                raise ValueError("一次只能识别一个 query 样本，收到 %d 个" % len(query.samples))
            query_id = query.samples[0] if query.samples else "query"
            # 投影把 query 对齐到参考 marker 集；集合外位点会被拒绝。
            query_row = query.project(self.reference_matrix(marker_ids=marker_ids).markers).rows[0]
        else:
            query_id = "query"
            query_row = [int(value) for value in query]

        reference = self.reference_matrix(marker_ids=marker_ids)
        if reference.n_markers == 0:
            raise ValueError("数据库中没有 marker")

        result = identify_top_k(
            query_row,
            reference.rows,
            reference.samples,
            method=method,
            top_k=top_k,
            min_compared=min_compared,
            reject_threshold=reject_threshold,
        )
        result["query_id"] = query_id
        result["n_reference_samples"] = len(reference.samples)
        result["n_reference_markers"] = reference.n_markers
        self._annotate_varieties(result.get("top_matches", []))
        if result.get("best_match"):
            self._annotate_varieties([result["best_match"]])

        # An unlabelled reference sample can legitimately be the nearest
        # neighbour, but presenting it as an identification would be misleading:
        # the caller asked "which variety" and the answer would be "unknown",
        # while a named variety sits right below it. Flag it loudly instead.
        result["n_unlabelled_reference_samples"] = len(self.unlabelled_samples())
        best = result.get("best_match")
        result["best_match_lacks_variety"] = bool(
            best and not (best.get("variety_name") or "").strip())
        return result

    def _annotate_varieties(self, hits):
        cache = {}
        for hit in hits:
            reference_id = hit.get("reference_id")
            if reference_id is None:
                continue
            if reference_id not in cache:
                row = self.conn.execute(
                    "SELECT variety_name, subspecies FROM sample WHERE sample_id = ?",
                    (reference_id,),
                ).fetchone()
                cache[reference_id] = row if row else (None, None)
            hit["variety_name"], hit["subspecies"] = cache[reference_id]

    # ---------- 品种比较 ----------
    def compare_varieties(self, variety_a, variety_b, method="ibs", min_compared=50):
        """比较两个品种的参考指纹。

        返回比较位点数与差异位点数；比较位点不足时相似度为 ``None``，
        避免用少量位点的偶然一致宣称"高度相似"。

        ``method`` 与 ``identify()`` 使用同一组实现（``fingerprint`` 中的
        IBS/Hamming/Jaccard），因此两处报告的相似度处于同一尺度，可直接
        对照。此前本函数接受 ``method`` 却硬编码 Hamming，默认值 "ibs"
        与实际计算不符，会让论文中"品种间相似度"与"识别相似度"两列
        使用不同尺度且无法察觉。
        """
        from ricevar_id import fingerprint as _fp

        methods = {
            "ibs": _fp.ibs_similarity,
            "hamming": _fp.hamming_similarity,
            "jaccard": _fp.binary_jaccard,
        }
        if method not in methods:
            raise ValueError("method must be one of: ibs, hamming, jaccard")
        similarity_of = methods[method]

        samples_a = [row[0] for row in self.samples_of(variety_a)]
        samples_b = [row[0] for row in self.samples_of(variety_b)]
        if not samples_a or not samples_b:
            raise KeyError("未知品种: %s" % (variety_a if not samples_a else variety_b))

        reference = self.reference_matrix()
        index = {sample: i for i, sample in enumerate(reference.samples)}
        rows_a = [reference.rows[index[s]] for s in samples_a]
        rows_b = [reference.rows[index[s]] for s in samples_b]

        # 品种级比较取两两样本对的均值，并记录每个位点被比较的次数。
        scores = []
        compared_union = 0
        different_union = 0
        for row_a in rows_a:
            for row_b in rows_b:
                compared = [(x, y) for x, y in zip(row_a, row_b) if x >= 0 and y >= 0]
                if len(compared) < min_compared:
                    continue
                pair_similarity = similarity_of(row_a, [row_b], min_compared=min_compared)[0][0]
                if pair_similarity != pair_similarity:  # NaN
                    continue
                scores.append(float(pair_similarity))
                compared_union += len(compared)
                different_union += sum(1 for x, y in compared if x != y)

        return {
            "variety_a": variety_a,
            "variety_b": variety_b,
            "method": method,
            "samples_a": samples_a,
            "samples_b": samples_b,
            "n_pairs_compared": len(scores),
            "n_pairs_total": len(rows_a) * len(rows_b),
            "n_compared_markers": compared_union,
            "n_different_markers": different_union,
            "mean_similarity": (sum(scores) / len(scores)) if scores else None,
            "min_compared": min_compared,
            "note": None if scores else "样本对比较位点均少于 %d，未给出相似度" % min_compared,
        }

    # ---------- 评估结果 ----------
    def evaluation_by_depth(self):
        return self.conn.execute(
            "SELECT marker_count, depth_label, COUNT(*), "
            "       AVG(marker_recall), AVG(genotype_concordance), "
            "       AVG(best_similarity), AVG(top1_correct_variety), "
            "       AVG(top5_correct_variety), AVG(accepted) "
            "FROM evaluation GROUP BY marker_count, depth_label "
            "ORDER BY marker_count, depth_label"
        ).fetchall()
