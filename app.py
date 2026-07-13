"""Streamlit 人名清洗审阅工作台。"""

from io import BytesIO

import pandas as pd
import streamlit as st

from advanced_name_cleaner import AdvancedNameCleaner


st.set_page_config(
    page_title="姓名清洗审阅工作台",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1500px; padding-top: 1.5rem;}
    [data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, .25);
        border-radius: .65rem;
        padding: .65rem 1rem;
    }
    .evidence-note {
        padding: .75rem 1rem;
        border-left: 4px solid #4f8bf9;
        background: rgba(79, 139, 249, .08);
        border-radius: .25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def read_uploaded_file(uploaded_file):
    """读取 CSV/XLSX，并对常见中文 CSV 编码做降级处理。"""
    data = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()
    if file_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(data))

    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return pd.read_csv(BytesIO(data), encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error
    raise ValueError("无法识别 CSV 编码，请另存为 UTF-8 后重试") from last_error


def collect_mapping(decisions):
    """按组号顺序汇总审阅决定中的修正映射。"""
    mapping = {}
    for group_index in sorted(decisions):
        mapping.update(decisions[group_index]["mapping"])
    return mapping


def save_decision(group_index, action, mapping, description):
    """保存或覆盖当前组决定，并将审阅焦点移到下一组。"""
    state = st.session_state.review
    if group_index not in state["decisions"]:
        state["decision_order"].append(group_index)
    state["decisions"][group_index] = {
        "action": action,
        "mapping": mapping,
        "description": description,
    }
    if group_index < len(state["groups"]) - 1:
        state["index"] = group_index + 1


def format_differences(differences):
    if not differences:
        return "—"
    return "，".join(
        f"第{item['position']}字 {item['variant'] or '∅'}→{item['reference'] or '∅'}"
        for item in differences
    )


def build_variant_table(evidence):
    rows = []
    for variant in evidence["variants"]:
        year_range = "—"
        if variant["year_min"] is not None:
            year_range = str(variant["year_min"])
            if variant["year_max"] != variant["year_min"]:
                year_range += f"–{variant['year_max']}"
        rows.append({
            "姓名": variant["name"],
            "建议": "建议保留" if variant["is_suggested"] else "",
            "频次": variant["frequency"],
            "组内占比": f"{variant['frequency_ratio']:.1%}",
            "年份范围": year_range,
            "拼音": variant["pinyin"],
            "与建议写法差异": format_differences(variant["differences"]),
        })
    return pd.DataFrame(rows)


def render_review_workspace():
    state = st.session_state.review
    total = len(state["groups"])
    current_index = min(state["index"], total - 1)
    state["index"] = current_index
    reviewed = len(state["decisions"])

    top_left, top_middle, top_right = st.columns([2, 2, 3])
    top_left.metric("候选组", f"{current_index + 1} / {total}")
    top_middle.metric("已完成审阅", f"{reviewed} / {total}")
    top_right.progress(reviewed / total, text=f"总体进度 {reviewed / total:.0%}")

    cleaner = AdvancedNameCleaner(
        aux_columns=state["context_columns"],
        threshold=state["threshold"],
    )
    group = state["groups"][current_index]
    evidence = cleaner.build_group_evidence(
        state["df"],
        group,
        name_col=state["name_column"],
        year_col=state["year_column"],
        context_columns=state["context_columns"],
    )

    current_decision = state["decisions"].get(current_index)
    if current_decision:
        st.success(f"本组已记录：{current_decision['description']}")

    st.subheader("姓名变体对比")
    st.dataframe(
        build_variant_table(evidence),
        width="stretch",
        hide_index=True,
        column_config={
            "频次": st.column_config.NumberColumn(width="small"),
            "组内占比": st.column_config.TextColumn(width="small"),
        },
    )
    st.markdown(
        f'<div class="evidence-note">系统仅按频次推荐保留“<b>{evidence["suggested_name"]}</b>”。'
        "频次是线索，不代表该写法一定正确，请结合年份、职位和单位连续性判断。</div>",
        unsafe_allow_html=True,
    )

    evidence_col, action_col = st.columns([3, 2], gap="large")
    with evidence_col:
        if evidence["timeline"]:
            st.subheader("年份—职位 / 单位时间线")
            timeline_df = pd.DataFrame(evidence["timeline"]).rename(
                columns={
                    "year": state["year_column"],
                    "name": state["name_column"],
                    "frequency": "当年频次",
                }
            )
            st.dataframe(
                timeline_df,
                width="stretch",
                hide_index=True,
                height=min(520, 36 * (len(timeline_df) + 1)),
            )
        else:
            st.subheader("上下文")
            st.info("未选择可用的年份列，当前按原始记录展示上下文。")

        with st.expander(f"查看本组 {len(evidence['raw_records'])} 条原始记录"):
            st.dataframe(
                pd.DataFrame(evidence["raw_records"]),
                width="stretch",
                hide_index=True,
            )

        with st.expander("查看拼音相似度"):
            similarities = pd.DataFrame(evidence["pairwise_similarities"]).rename(
                columns={"name_a": "姓名 A", "name_b": "姓名 B", "similarity": "相似度"}
            )
            st.dataframe(
                similarities,
                width="stretch",
                hide_index=True,
                column_config={
                    "相似度": st.column_config.ProgressColumn(
                        min_value=0.0, max_value=1.0, format="%.3f"
                    )
                },
            )

    with action_col:
        st.subheader("记录判断")
        target_name = st.selectbox(
            "如果属于同一人，选择应保留的标准写法",
            evidence["names"],
            index=evidence["names"].index(evidence["suggested_name"]),
            key=f"target_{current_index}",
        )
        if st.button("全组合并到该写法", type="primary", width="stretch"):
            mapping = {name: target_name for name in evidence["names"] if name != target_name}
            save_decision(current_index, "merge", mapping, f"合并为 {target_name}")
            st.rerun()

        if st.button("判定为不同人 / 暂不合并", width="stretch"):
            save_decision(current_index, "pass", {}, "不合并")
            st.rerun()

        st.divider()
        st.caption("自定义映射")
        custom_sources = st.multiselect(
            "把这些写法",
            [name for name in evidence["names"] if name != target_name],
            key=f"sources_{current_index}",
        )
        st.write(f"改为：**{target_name}**")
        if st.button(
            "保存自定义映射",
            disabled=not custom_sources,
            width="stretch",
        ):
            mapping = {name: target_name for name in custom_sources}
            detail = "；".join(f"{source}→{target_name}" for source in custom_sources)
            save_decision(current_index, "custom", mapping, detail)
            st.rerun()

    st.divider()
    previous_col, next_col, undo_col, reset_col = st.columns(4)
    if previous_col.button("上一组", disabled=current_index == 0, width="stretch"):
        state["index"] -= 1
        st.rerun()
    if next_col.button("下一组", disabled=current_index == total - 1, width="stretch"):
        state["index"] += 1
        st.rerun()
    if undo_col.button(
        "撤销最近决定",
        disabled=not state["decision_order"],
        width="stretch",
    ):
        undone_index = state["decision_order"].pop()
        state["decisions"].pop(undone_index, None)
        state["index"] = undone_index
        st.rerun()
    if reset_col.button("重新配置", width="stretch"):
        del st.session_state.review
        st.rerun()

    st.subheader("结果与导出")
    mapping = collect_mapping(state["decisions"])
    cleaned_df = cleaner.apply_corrections(state["df"], mapping, state["name_column"])
    mapping_df = pd.DataFrame(
        [{"原始姓名": source, "标准姓名": target} for source, target in mapping.items()]
    )

    result_left, result_right = st.columns(2)
    result_left.download_button(
        "下载清洗后 CSV",
        cleaned_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="name_cleaned.csv",
        mime="text/csv",
        width="stretch",
    )
    result_right.download_button(
        "下载修正映射 CSV",
        mapping_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="name_mapping.csv",
        mime="text/csv",
        disabled=mapping_df.empty,
        width="stretch",
    )
    with st.expander("预览当前修正映射", expanded=bool(mapping)):
        if mapping_df.empty:
            st.caption("尚未产生姓名修正。")
        else:
            st.dataframe(mapping_df, width="stretch", hide_index=True)


st.title("姓名清洗审阅工作台")
st.caption("用频次、年份连续性和职位 / 单位上下文辅助判断同音异形姓名。")

uploaded_file = st.file_uploader("上传待清洗数据", type=["csv", "xlsx", "xls"])

if "review" in st.session_state:
    render_review_workspace()
elif uploaded_file is None:
    st.info("请上传 CSV 或 Excel 文件开始。数据仅在当前 Streamlit 会话中处理。")
else:
    try:
        uploaded_df = read_uploaded_file(uploaded_file)
    except Exception as error:
        st.error(f"文件读取失败：{error}")
        st.stop()

    if uploaded_df.empty or len(uploaded_df.columns) == 0:
        st.warning("文件中没有可供审阅的数据。")
        st.stop()

    st.success(f"已读取 {len(uploaded_df):,} 行、{len(uploaded_df.columns)} 列")
    with st.expander("预览原始数据", expanded=True):
        st.dataframe(uploaded_df.head(50), width="stretch", hide_index=True)

    columns = list(uploaded_df.columns)
    default_name_index = columns.index("p_name") if "p_name" in columns else 0
    name_column = st.selectbox("姓名列", columns, index=default_name_index)

    year_candidates = ["（不使用年份）"] + columns
    guessed_year = next(
        (column for column in ("year", "datayr", "年份", "年度") if column in columns),
        None,
    )
    default_year_index = year_candidates.index(guessed_year) if guessed_year else 0
    selected_year = st.selectbox("年份列", year_candidates, index=default_year_index)
    year_column = None if selected_year == "（不使用年份）" else selected_year

    suggested_context = [
        column
        for column in ("post1", "post_rank", "company", "w_name", "cityname", "distname")
        if column in columns and column not in {name_column, year_column}
    ]
    available_context = [
        column for column in columns if column not in {name_column, year_column}
    ]
    context_columns = st.multiselect(
        "辅助判断列（职位、单位、地区等）",
        available_context,
        default=suggested_context,
    )
    threshold = st.slider(
        "拼音相似度阈值",
        min_value=0.50,
        max_value=1.00,
        value=0.85,
        step=0.01,
        help="阈值越低，候选更宽松，也越可能出现误报。",
    )

    if st.button("扫描疑似姓名", type="primary"):
        with st.spinner("正在构建拼音候选组…"):
            cleaner = AdvancedNameCleaner(context_columns, threshold)
            groups = cleaner.find_potential_groups(
                uploaded_df, name_col=name_column, verbose=False
            )
        if not groups:
            st.warning("当前阈值下未发现疑似姓名组。")
        else:
            st.session_state.review = {
                "df": uploaded_df,
                "name_column": name_column,
                "year_column": year_column,
                "context_columns": context_columns,
                "threshold": threshold,
                "groups": groups,
                "index": 0,
                "decisions": {},
                "decision_order": [],
            }
            st.rerun()
