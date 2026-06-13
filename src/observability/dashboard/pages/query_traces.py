"""Dashboard Query 追踪页面（G6）。

这个页面的职责不是重新执行查询，而是把已经落到 `traces.jsonl` 的历史查询记录
整理成“人能快速看懂”的排障视图，重点回答三个问题：
1. 这次 query 走了哪些阶段，各自花了多少时间；
2. Dense / Sparse 两条路各自召回了什么；
3. Rerank 是否真的改变了最终排序。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from observability.dashboard.services.trace_service import (
    DashboardTraceRecord,
    QueryTraceView,
    TraceReadResult,
    TraceRuntimeConfig,
    TraceService,
)
from observability.dashboard.pages._table_utils import render_wrapped_dataframe


@dataclass(frozen=True)
class QueryTracesSnapshot:
    """G6 页面渲染前使用的数据快照。

    做什么：
    - 把 trace 文件路径、自动刷新配置、过滤后的记录列表、选中项等页面状态一次性收口；
    - 让 `render()` 主要负责“展示”，而不是一边取数据一边做大量分支判断。

    为什么：
    - Query 追踪页有“关键字过滤 + 默认选中最新一条 + 切换指定 trace”这些状态组合；
    - 先把状态整理成不可变快照，更容易测试，也能避免页面代码里散落重复判断。
    """

    trace_file: str
    skipped_lines: int
    auto_refresh: bool
    refresh_interval: int
    keyword_filter: str
    traces: list[DashboardTraceRecord]
    trace_views: dict[str, QueryTraceView]
    selected_trace: DashboardTraceRecord | None
    selected_view: QueryTraceView | None


def build_snapshot(
    trace_service: TraceService | None = None,
    *,
    selected_trace_id: str | None = None,
    keyword_filter: str = "",
) -> QueryTracesSnapshot:
    """构造 G6 页面需要的完整数据快照。

    做什么：
    - 读取 `trace_type="query"` 的历史记录；
    - 把每条记录转换成 Query 页面专用视图；
    - 根据关键字过滤历史；
    - 选出当前应该展示的那一条 trace。

    为什么：
    - 页面既要显示“列表”，又要显示“详情”；
    - 如果每次渲染时都在页面层重复做筛选和选中逻辑，测试会很难写，状态也容易互相打架。

    关键权衡：
    - 关键字过滤只匹配 `query_text / normalized_query / keywords`，不去全文扫描候选片段；
      这样过滤规则稳定、成本低，也避免把“候选文本内容”误当成 query 本身。

    失败路径：
    - 若没有任何 query trace，返回空快照，交由页面层展示友好提示；
    - 若 `selected_trace_id` 不存在于过滤结果中，则自动回退到“最新一条”。
    """
    service = trace_service or TraceService()
    read_result: TraceReadResult = service.load_traces(trace_type="query")
    runtime: TraceRuntimeConfig = service.get_runtime_config()

    filtered_records: list[DashboardTraceRecord] = []
    trace_views: dict[str, QueryTraceView] = {}
    normalized_filter = str(keyword_filter).strip().lower()

    for record in read_result.records:
        view = service.build_query_trace_view(record)
        searchable_text = " ".join([view.query_text, view.normalized_query, " ".join(view.keywords)]).lower()
        # 过滤只针对“查询本身”，这样用户输入一个关键词时，看到的是相关 query 历史，
        # 而不是因为候选结果正文里恰好出现该词而把不相关 trace 混进来。
        if normalized_filter and normalized_filter not in searchable_text:
            continue
        filtered_records.append(record)
        trace_views[record.trace_id] = view

    selected_trace = None
    selected_view = None
    if filtered_records:
        # 默认展示最新一条 trace，保证页面打开时就有“可读详情”，而不是空白。
        selected_trace = filtered_records[0]
        selected_view = trace_views.get(selected_trace.trace_id)
        if selected_trace_id and selected_trace_id in trace_views:
            matched = next((item for item in filtered_records if item.trace_id == selected_trace_id), None)
            if matched is not None:
                selected_trace = matched
                selected_view = trace_views.get(matched.trace_id)

    return QueryTracesSnapshot(
        trace_file=read_result.trace_file,
        skipped_lines=read_result.skipped_lines,
        auto_refresh=runtime.auto_refresh,
        refresh_interval=runtime.refresh_interval,
        keyword_filter=keyword_filter,
        traces=filtered_records,
        trace_views=trace_views,
        selected_trace=selected_trace,
        selected_view=selected_view,
    )


def render(trace_service: TraceService | None = None, st_module: Any | None = None) -> None:
    """渲染 Query 追踪页面。

    做什么：
    - 展示 query 历史列表；
    - 展示单次 query 的阶段耗时；
    - 展示 Dense / Sparse / Fusion / Rerank 的候选对比。

    失败路径：
    - trace 文件不存在、为空，或过滤后无结果时，都展示提示信息而不是抛异常；
    - 单条 trace 若缺少详情，则回退到快照里默认选中的最新记录。
    """
    import streamlit as st

    active_st = st_module or st
    service = trace_service or TraceService()

    active_st.title("Query 追踪")
    active_st.caption("查看查询历史、各阶段耗时，以及 Dense/Sparse/Fusion/Rerank 的对比细节。")

    keyword_filter = active_st.text_input(
        "按 Query 关键词筛选",
        value="",
        help="输入关键词后，只保留 query 文本、规范化 query 或关键词列表中包含该词的记录。",
    )
    snapshot = build_snapshot(service, keyword_filter=keyword_filter)

    active_st.caption(f"Trace 文件：`{snapshot.trace_file}`")
    active_st.caption(
        f"自动刷新配置：`{snapshot.auto_refresh}` / 间隔 `{snapshot.refresh_interval}s`"
    )

    if snapshot.skipped_lines:
        active_st.warning(
            f"读取 trace 时跳过了 {snapshot.skipped_lines} 行坏数据，其余合法记录仍会继续展示。"
        )

    if not snapshot.traces:
        active_st.info("当前还没有可展示的 Query Trace。先执行一次 query，再回到这里查看追踪历史。")
        return

    active_st.subheader("查询历史")
    render_wrapped_dataframe(active_st, _build_history_rows(snapshot))

    selected_trace_id = active_st.selectbox(
        "选择一条 Query Trace",
        options=[item.trace_id for item in snapshot.traces],
        index=0,
        format_func=lambda trace_id: _format_trace_option(trace_id, snapshot),
        help="默认选中最新一条 trace，可切换查看单次查询的检索细节。",
    )

    selected_trace = next((item for item in snapshot.traces if item.trace_id == selected_trace_id), None)
    selected_view = snapshot.trace_views.get(selected_trace_id)
    # 这里保留一次回退，是为了防止 UI 选项和底层数据在刷新瞬间发生错位，
    # 避免页面因为短暂的不一致状态直接报错。
    if selected_trace is None:
        selected_trace = snapshot.selected_trace
    if selected_view is None:
        selected_view = snapshot.selected_view
    if selected_trace is None or selected_view is None:
        active_st.info("未找到所选 query trace 的详情，请刷新后重试。")
        return

    _render_detail(active_st, selected_trace, selected_view)


def _build_history_rows(snapshot: QueryTracesSnapshot) -> list[dict[str, object]]:
    """把 trace 列表转换成适合 DataFrame 展示的表格行。"""
    rows: list[dict[str, object]] = []
    for record in snapshot.traces:
        view = snapshot.trace_views[record.trace_id]
        rows.append(
            {
                "trace_id": record.trace_id,
                "query": view.query_text,
                "collection": view.collection,
                "status": record.status,
                "started_at": record.started_at or "-",
                "top_k": view.top_k if view.top_k is not None else "-",
                "total_elapsed_ms": round(float(record.total_elapsed_ms), 2),
            }
        )
    return rows


def _render_detail(st: Any, trace: DashboardTraceRecord, view: QueryTraceView) -> None:
    """渲染单条 query trace 的详情区域。"""
    st.subheader("Trace 详情")
    st.markdown("**基础信息**")
    # 这里把原先散落的顶部摘要收口成一个区块，避免用户来回扫多行文字拼信息。
    st.write(f"Trace ID：`{trace.trace_id}`")
    st.write(f"Timestamp：`{trace.started_at or '-'}`")
    st.write(f"User Query：`{view.query_text}`")
    st.write(f"Collection：`{view.collection}`")
    st.write(f"Status：`{trace.status}` / 总耗时：`{trace.total_elapsed_ms:.2f} ms`")

    chart_rows = [
        {"stage": stage.stage_name, "elapsed_ms": round(stage.elapsed_ms, 2)}
        for stage in view.stage_breakdown
        if stage.present
    ]
    if chart_rows:
        st.bar_chart(chart_rows, x="stage", y="elapsed_ms")
    else:
        # 旧 trace 或异常中断的 trace 可能没有完整阶段信息；
        # 页面层保持可用，比强行要求所有历史数据都符合最新版 schema 更重要。
        st.info("当前 trace 尚未记录查询阶段耗时。")

    st.subheader("各阶段详情")
    stage_rows = _build_stage_detail_rows(view)
    if stage_rows:
        render_wrapped_dataframe(st, stage_rows)
    else:
        st.info("当前 trace 没有可展示的阶段详情。")

    st.subheader("Dense vs Sparse 对比")
    st.markdown("**Dense Retrieval**")
    if view.dense_results:
        render_wrapped_dataframe(st, _candidate_rows(view.dense_results))
    else:
        st.info("Dense 路径没有可展示的候选预览。")
    st.markdown("**Sparse Retrieval**")
    if view.sparse_results:
        render_wrapped_dataframe(st, _candidate_rows(view.sparse_results))
    else:
        st.info("Sparse 路径没有可展示的候选预览。")

    st.subheader("Fusion 结果")
    st.write(
        "统一排名："
        f"algorithm=`{_value_or_dash(view.fusion_details.get('method'))}` / "
        f"elapsed=`{_stage_elapsed(view, 'fusion')}`"
    )
    if view.fusion_results:
        render_wrapped_dataframe(st, _candidate_rows(view.fusion_results))
    else:
        st.info("Fusion 阶段没有可展示的统一排名预览。")

    st.subheader("Rerank 前后对比")
    rerank_rows = _build_rerank_comparison_rows(view)
    if rerank_rows:
        render_wrapped_dataframe(st, rerank_rows)
    else:
        st.info("当前 trace 没有足够的 fusion/rerank 预览数据，无法展示名次变化。")

    st.subheader("最终结果")
    if view.final_results:
        render_wrapped_dataframe(st, _candidate_rows(view.final_results))
    else:
        st.info("当前 trace 没有最终结果预览。")


def _candidate_rows(candidates: tuple[Any, ...]) -> list[dict[str, object]]:
    """把候选预览模型转换成表格行。"""
    return [
        {
            "rank": item.rank,
            "chunk_id": item.chunk_id,
            "score": round(float(item.score), 4),
            "collection": item.collection,
            "text": str(item.text).strip(),
            "source_path": item.source_path,
        }
        for item in candidates
    ]


def _build_stage_detail_rows(view: QueryTraceView) -> list[dict[str, object]]:
    """构建 `3.4.2` 要求的阶段详情摘要表。

    这里不是把原始 JSON 原封不动展开，而是提取每个阶段最关键的可读字段：
    - 让页面对照开发文档；
    - 又避免把追踪页变成难读的原始 payload 浏览器。
    """
    query_keywords = ", ".join(view.keywords) if view.keywords else "-"

    return [
        {
            "阶段": "Query Processing",
            "记录内容": (
                f"原始 Query={view.query_text}; "
                f"规范化 Query={view.normalized_query}; "
                f"关键词={query_keywords}; "
                f"method={_value_or_dash(view.query_processing_details.get('method'))}; "
                f"耗时={_stage_elapsed(view, 'query_processing')}"
            ),
        },
        {
            "阶段": "Dense Retrieval",
            "记录内容": (
                f"Top-N={_summarize_candidates(view.dense_results)}; "
                f"provider={_value_or_dash(view.dense_details.get('provider'))}; "
                f"耗时={_stage_elapsed(view, 'dense_retrieval')}"
            ),
        },
        {
            "阶段": "Sparse Retrieval",
            "记录内容": (
                f"Top-N={_summarize_candidates(view.sparse_results)}; "
                f"method={_value_or_dash(view.sparse_details.get('method'))}; "
                f"耗时={_stage_elapsed(view, 'sparse_retrieval')}"
            ),
        },
        {
            "阶段": "Fusion",
            "记录内容": (
                f"统一排名={_summarize_candidates(view.fusion_results)}; "
                f"algorithm={_value_or_dash(view.fusion_details.get('method'))}; "
                f"耗时={_stage_elapsed(view, 'fusion')}"
            ),
        },
        {
            "阶段": "Rerank",
            "记录内容": (
                f"最终排名={_summarize_candidates(view.rerank_results or view.final_results)}; "
                f"backend={_value_or_dash(view.rerank_details.get('backend') or view.rerank_details.get('provider'))}; "
                f"fallback={_value_or_dash(view.rerank_details.get('fallback'))}; "
                f"耗时={_stage_elapsed(view, 'rerank')}"
            ),
        },
    ]


def _build_rerank_comparison_rows(view: QueryTraceView) -> list[dict[str, object]]:
    """构建 Rerank 前后名次变化表。

    做什么：
    - 用 fusion 结果作为“重排前”；
    - 用 rerank 结果作为“重排后”；
    - 计算每个 chunk 的名次变化方向。

    为什么：
    - 只看最终结果很难判断 rerank 有没有实际价值；
    - 名次变化表可以直接告诉我们：某个 chunk 是被提升、压低，还是根本没变。

    失败路径：
    - 如果 trace 缺少 fusion 或 rerank 预览，返回空列表，页面层展示提示即可。
    """
    if not view.fusion_results or not view.rerank_results:
        return []

    fusion_rank = {item.chunk_id: item.rank for item in view.fusion_results}
    rerank_rank = {item.chunk_id: item.rank for item in view.rerank_results}

    rows: list[dict[str, object]] = []
    for item in view.rerank_results:
        before = fusion_rank.get(item.chunk_id)
        after = rerank_rank.get(item.chunk_id)
        change = "-"
        if before is not None and after is not None:
            # 名次数字越小表示越靠前，所以要用 before - after 判断“提升还是下降”。
            delta = before - after
            if delta > 0:
                change = f"up {delta}"
            elif delta < 0:
                change = f"down {abs(delta)}"
            else:
                change = "same"

        rows.append(
            {
                "chunk_id": item.chunk_id,
                "fusion_rank": before if before is not None else "-",
                "rerank_rank": after if after is not None else "-",
                "change": change,
                "text": str(item.text).strip(),
                "source_path": item.source_path,
            }
        )
    return rows


def _format_trace_option(trace_id: str, snapshot: QueryTracesSnapshot) -> str:
    """把下拉框选项格式化成更易读的摘要。"""
    record = next((item for item in snapshot.traces if item.trace_id == trace_id), None)
    if record is None:
        return trace_id
    view = snapshot.trace_views[trace_id]
    return f"{view.query_text} | {record.status} | {record.total_elapsed_ms:.2f} ms"


def _summarize_candidates(candidates: tuple[Any, ...], limit: int = 3) -> str:
    """把候选列表压缩成适合单元格展示的短摘要。"""
    if not candidates:
        return "-"
    parts = [
        f"{item.rank}:{item.chunk_id}({float(item.score):.4f})"
        for item in candidates[:limit]
    ]
    return ", ".join(parts)


def _stage_elapsed(view: QueryTraceView, stage_name: str) -> str:
    """读取指定阶段耗时；缺失时返回 `-`。"""
    for stage in view.stage_breakdown:
        if stage.stage_name == stage_name and stage.present:
            return f"{stage.elapsed_ms:.2f} ms"
    return "-"


def _value_or_dash(value: Any) -> str:
    """把页面展示值统一规整成可读字符串。"""
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"
