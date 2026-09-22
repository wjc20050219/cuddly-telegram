"""RiceVar-ID 品种识别原型（TASK-042~045，Streamlit）。

运行::

    streamlit run app/streamlit_app.py

设计原则
--------
* **没有数据库就明确报错**，不显示任何示例/编造的识别结果。
* 每个结果都同时展示**比较位点数**与**比较率**——少量位点偶然一致不能被
  当成"高置信匹配"。
* 页面固定标注这是闭集（closed-set）结果；开放集拒识只在独立面板上评估。
* 纯标准库 + streamlit；matplotlib 仅用于可选绘图，缺失时自动降级为表格。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ricevar_id.database import connect  # noqa: E402
from ricevar_id.dbquery import FingerprintDatabase  # noqa: E402
from ricevar_id.query_input import parse_genotype_table  # noqa: E402

DEFAULT_DB = ROOT / "database" / "ricevar_id.sqlite"

st.set_page_config(page_title="RiceVar-ID 品种识别原型", layout="wide")


# ---------- 数据访问 ----------
@st.cache_resource(show_spinner=False)
def open_database(path):
    """Open the fingerprint database. Resource-cached so queries stay cheap."""
    return connect(Path(path))


def get_api(path):
    conn = open_database(str(path))
    return FingerprintDatabase(conn)


def upload_to_matrix(uploaded):
    """Parse an uploaded genotype table via the unit-tested parser."""
    return parse_genotype_table(uploaded.getvalue().decode("utf-8"))


# ---------- 侧栏 ----------
st.sidebar.title("RiceVar-ID")
st.sidebar.caption("超低深度 WGS 水稻品种识别原型（本科毕业论文）")

db_path = st.sidebar.text_input("数据库路径", value=str(DEFAULT_DB))
method = st.sidebar.selectbox("相似度方法", ["ibs", "hamming", "jaccard"], index=0)
top_k = st.sidebar.slider("返回 Top-K", 1, 20, 5)
min_compared = st.sidebar.number_input("最少比较位点数", min_value=1, value=50, step=10)
use_threshold = st.sidebar.checkbox("启用拒识阈值", value=False)
threshold = st.sidebar.slider("拒识阈值", 0.0, 1.0, 0.90, 0.01, disabled=not use_threshold)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠ 本原型只做**闭集**识别：查询样本需属于数据库中的已知品种集合。"
    "独立面板的开放集拒识结论请见论文实验章节。"
)

if not Path(db_path).exists():
    st.title("RiceVar-ID 品种识别原型")
    st.error("数据库不存在：%s" % db_path)
    st.markdown(
        "请先构建数据库（需要真实的 Pilot 基因型矩阵）：\n\n"
        "```bash\n"
        "python scripts/build_database.py \\\n"
        "    --matrix   <pilot.genotypes_2000.tsv> \\\n"
        "    --manifest data/metadata/server/pilot_manifest.tsv \\\n"
        "    --out      database/ricevar_id.sqlite\n"
        "```\n\n"
        "**本页面不会显示任何示例结果**：没有真实数据时保持空白，"
        "以免把占位数值误当成实验结果。"
    )
    st.stop()

api = get_api(db_path)
counts = api.counts()

st.title("RiceVar-ID 品种识别原型")

if api.is_empty():
    st.error("数据库中没有任何参考基因型，无法识别。")
    st.markdown("请先完成 Pilot 联合 calling 与 marker 冻结，再重建数据库。")
    st.stop()

# ---------- 概览 ----------
st.subheader("数据库概览")
cols = st.columns(5)
cols[0].metric("样本", counts["samples"])
cols[1].metric("品种", counts["varieties"])
cols[2].metric("Marker", counts["markers"])
cols[3].metric("基因型记录", counts["genotypes"])
cols[4].metric("评估记录", counts["evaluation_rows"])

metadata = api.metadata()
with st.expander("溯源信息（建库输入与校验和）"):
    st.json(metadata)

tab_identify, tab_variety, tab_compare, tab_eval = st.tabs(
    ["品种识别", "品种查询", "品种比较", "深度–准确率"]
)

# ---------- 品种识别 ----------
with tab_identify:
    st.markdown(
        "上传一个样本的基因型矩阵（`sample_id` + `CHROM:POS:REF:ALT` 列）进行识别。"
        "未覆盖的位点请写 `NA` 或 `-1`；**未覆盖不会被视为参考基因型**。"
    )
    uploaded = st.file_uploader("查询基因型表（TSV）", type=["tsv", "txt"])
    if uploaded is None:
        st.info("尚未上传查询文件。")
    else:
        try:
            query = upload_to_matrix(uploaded)
        except Exception as exc:  # noqa: BLE001 - surface parse errors to the user
            st.error("解析失败：%s" % exc)
        else:
            st.caption(
                "查询样本 %s，位点 %d 个" % (query.samples[0], query.n_markers)
            )
            try:
                result = api.identify(
                    query,
                    method=method,
                    top_k=top_k,
                    min_compared=int(min_compared),
                    reject_threshold=float(threshold) if use_threshold else None,
                )
            except ValueError as exc:
                st.error("无法识别：%s" % exc)
            else:
                if result["best_match"]:
                    best = result["best_match"]
                    st.success("最近匹配：%s（品种 %s）" % (
                        best["reference_id"], best.get("variety_name") or "未知"))
                    if result.get("best_match_lacks_variety"):
                        st.warning(
                            "注意：最近匹配的参考样本**没有品种名**（清单中该字段为空）。"
                            "它仍参与比对，因此会排在有名字的品种之前。"
                            "请对照下方 Top 候选中有品种名的条目，不要把它当作识别结论。"
                        )
                    m = st.columns(4)
                    m[0].metric("相似度", "%.4f" % best["similarity"])
                    m[1].metric("比较位点数", best["n_compared_markers"])
                    m[2].metric("比较率", "%.2f%%" % (100 * best["compared_marker_rate"]))
                    m[3].metric("差异位点数", best["n_different_markers"])
                else:
                    st.warning(
                        "没有达到条件的匹配：或比较位点少于 %d，或相似度低于拒识阈值 %s。"
                        % (min_compared, threshold if use_threshold else "未启用")
                    )

                if result.get("n_unlabelled_reference_samples"):
                    st.info(
                        "数据库中有 %d 个参考样本没有品种名；它们不参与品种统计，"
                        "但会影响最近匹配。" % result["n_unlabelled_reference_samples"]
                    )

                if result["top_matches"]:
                    st.markdown("**Top-%d 候选**" % len(result["top_matches"]))
                    st.dataframe(
                        [
                            {
                                "样本": hit["reference_id"],
                                "品种": hit.get("variety_name"),
                                "亚种": hit.get("subspecies"),
                                "相似度": round(hit["similarity"], 4),
                                "比较位点": hit["n_compared_markers"],
                                "比较率": round(hit["compared_marker_rate"], 4),
                                "差异位点": hit["n_different_markers"],
                            }
                            for hit in result["top_matches"]
                        ],
                        use_container_width=True,
                    )
                    st.caption(
                        "筛选条件：方法 %s，最少比较位点 %d。"
                        "比较位点越多，相似度越可信。" % (method, min_compared)
                    )
                st.caption("⚠ 闭集结果：仅表示在已知品种集合中谁最接近。")

# ---------- 品种查询 ----------
with tab_variety:
    st.markdown("按品种名检索数据库中的样本。留空则列出全部品种。")
    keyword = st.text_input("品种名（支持部分匹配）", value="")
    if keyword:
        rows = api.find_variety(keyword, exact=False)
        if not rows:
            st.info("没有匹配 '%s' 的品种。" % keyword)
        else:
            st.dataframe(
                [{"品种": r[0], "亚种": r[1], "样本": r[2], "Run": r[3]} for r in rows],
                use_container_width=True,
            )
            st.caption(
                "共 %d 条匹配。包含匹配把 `%%` 和下划线当作普通字符，不作为通配符；"
                "大小写不敏感。" % len(rows)
            )
    else:
        varieties = api.list_varieties()
        st.dataframe(
            [{"品种": v[0], "亚种": v[1], "样本数": v[2]} for v in varieties],
            use_container_width=True,
        )
        st.caption("共 %d 个品种。" % len(varieties))

    unlabelled = api.unlabelled_samples()
    if unlabelled:
        st.warning(
            "另有 %d 个样本在清单中**没有品种名**（如 %s）。它们不进入上面的品种统计，"
            "但仍保留基因型并参与识别比对。"
            % (len(unlabelled), "、".join(unlabelled[:5]))
        )

# ---------- 品种比较 ----------
with tab_compare:
    st.markdown("比较两个品种的参考指纹相似度。")
    varieties = [v[0] for v in api.list_varieties()]
    if len(varieties) < 2:
        st.info("数据库中品种不足 2 个，无法比较。")
    else:
        c1, c2 = st.columns(2)
        a = c1.selectbox("品种 A", varieties, index=0)
        b = c2.selectbox("品种 B", varieties, index=min(1, len(varieties) - 1))
        cmp_min = st.number_input("最少比较位点数", min_value=1, value=int(min_compared), step=10,
                                  key="cmp_min")
        if st.button("比较"):
            if a == b:
                st.warning("请选择两个不同的品种。")
            else:
                try:
                    outcome = api.compare_varieties(a, b, method=method,
                                                    min_compared=int(cmp_min))
                except KeyError as exc:
                    st.error(str(exc))
                else:
                    if outcome["mean_similarity"] is None:
                        st.warning(outcome["note"])
                    else:
                        m = st.columns(4)
                        m[0].metric("平均相似度", "%.4f" % outcome["mean_similarity"])
                        m[1].metric("比较样本对", "%d / %d" % (
                            outcome["n_pairs_compared"], outcome["n_pairs_total"]))
                        m[2].metric("比较位点合计", outcome["n_compared_markers"])
                        m[3].metric("差异位点合计", outcome["n_different_markers"])
                        st.caption(
                            "样本对间取均值；每个位点只在双方都调用成功时才参与比较。"
                        )

# ---------- 深度–准确率 ----------
with tab_eval:
    st.markdown("低深度识别评估结果（来自 `07_identify.sh`）。")
    rows = api.evaluation_by_depth()
    if not rows:
        st.info(
            "尚无可用的识别评估结果。需要先在服务器完成：冻结 marker → "
            "重跑 `05_simulate.sh` → 运行 `07_identify.sh`，再把 per_query.tsv 导入数据库。"
        )
    else:
        table = [
            {
                "marker 数": r[0],
                "深度": r[1],
                "query 数": r[2],
                "平均 marker recall": None if r[3] is None else round(r[3], 4),
                "平均基因型一致率": None if r[4] is None else round(r[4], 4),
                "平均最佳相似度": None if r[5] is None else round(r[5], 4),
                "Top-1 品种准确率": None if r[6] is None else round(r[6], 4),
                "Top-5 品种准确率": None if r[7] is None else round(r[7], 4),
                "接受率": None if r[8] is None else round(r[8], 4),
            }
            for r in rows
        ]
        st.dataframe(table, use_container_width=True)
        st.caption(
            "⚠ 这些 query 是 Pilot 样本自身的高深度数据降采样得到的**技术重复**，"
            "属闭集评估；不代表独立同品种样本的准确率。"
        )
