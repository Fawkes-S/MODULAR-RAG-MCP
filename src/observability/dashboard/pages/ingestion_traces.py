"""Dashboard Ingestion 追踪页面（G5）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from observability.dashboard.services.trace_service import (
    DashboardTraceRecord,
    TraceReadResult,
    TraceRuntimeConfig,
    TraceService,
)


@dataclass(frozen=True)
class IngestionTracesSnapshot:
    """页面渲染前使用的聚合快照。"""

    trace_file: str
    skipped_lines: int
    auto_refresh: bool
    refresh_interval: int
    traces: list[DashboardTraceRecord]
    selected_trace: DashboardTraceRecord | None


def build_snapshot(
    trace_service: TraceService | None = None,
    *,
    selected_trace_id: str | None = None,
) -> IngestionTracesSnapshot:
    """构造 G5 页面需要的全部数据快照。

    做什么：
    - 读取 `trace_type == "ingestion"` 的历史记录；
    - 按选中的 `trace_id` 定位详情对象；
    - 同时把 trace 文件路径和自动刷新配置带给页面层。

    为什么：
    - `render()` 里如果直接混入文件读取、筛选、选中逻辑，测试会变得很笨重；
    - 先构造纯数据快照，再渲染 UI，单测就能直接验证核心行为。
    """
    service = trace_service or TraceService()
    read_result: TraceReadResult = service.load_traces(trace_type="ingestion")
    runtime: TraceRuntimeConfig = service.get_runtime_config()

    selected_trace = None
    if read_result.records:
        selected_trace = read_result.records[0]
        if selected_trace_id:
            matched = next((item for item in read_result.records if item.trace_id == selected_trace_id), None)
            if matched is not None:
                selected_trace = matched

    return IngestionTracesSnapshot(
        trace_file=read_result.trace_file,
        skipped_lines=read_result.skipped_lines,
        auto_refresh=runtime.auto_refresh,
        refresh_interval=runtime.refresh_interval,
        traces=read_result.records,
        selected_trace=selected_trace,
    )


def render(trace_service: TraceService | None = None, st_module: Any | None = None) -> None:
    """渲染 Ingestion 追踪页面。

    这个页面只负责三件事：
    - 展示摄取历史列表；
    - 让用户选中一条 trace；
    - 展示该 trace 的主阶段耗时分布与详情表。
    """
    import streamlit as st

    active_st = st_module or st
    service = trace_service or TraceService()
    snapshot = build_snapshot(service)

    active_st.title("Ingestion 追踪")
    active_st.caption("按 trace_id 查看摄取历史、状态以及 load/split/transform/embed/upsert 主阶段耗时分布。")
    active_st.caption(f"Trace 文件：`{snapshot.trace_file}`")
    active_st.caption(
        f"自动刷新配置：`{snapshot.auto_refresh}` / 间隔 `{snapshot.refresh_interval}s`"
    )

    if snapshot.skipped_lines:
        active_st.warning(
            f"读取 trace 时跳过了 {snapshot.skipped_lines} 行坏数据；其余合法记录仍会继续展示。"
        )

    if not snapshot.traces:
        active_st.info("当前还没有可展示的 Ingestion Trace。先执行一次 ingest，再回到这里查看追踪历史。")
        return

    active_st.subheader("摄取历史")
    active_st.dataframe(_build_history_rows(snapshot.traces), use_container_width=True, hide_index=True)

    selected_trace_id = active_st.selectbox(
        "选择一条摄取 Trace",
        options=[item.trace_id for item in snapshot.traces],
        index=0,
        format_func=lambda trace_id: _format_trace_option(trace_id, snapshot.traces),
        help="默认选中最新一条 trace，可切换查看单次摄取的细节。",
    )

    selected_trace = next((item for item in snapshot.traces if item.trace_id == selected_trace_id), None)
    if selected_trace is None:
        selected_trace = snapshot.selected_trace
    if selected_trace is None:
        active_st.info("未找到所选 trace 的详情，请刷新后重试。")
        return

    _render_detail(active_st, selected_trace)


def _build_history_rows(traces: list[DashboardTraceRecord]) -> list[dict[str, object]]:
    """把 trace 列表整理成历史表格行。"""
    return [
        {
            "trace_id": item.trace_id,
            "file_name": item.file_name,
            "collection": item.collection,
            "status": item.status,
            "started_at": item.started_at or "-",
            "total_elapsed_ms": round(float(item.total_elapsed_ms), 2),
            "source_path": item.source_path,
        }
        for item in traces
    ]


def _render_detail(st: Any, trace: DashboardTraceRecord) -> None:
    """渲染单条 Ingestion Trace 的阶段分布与详情。

    关键点：
    - 图表只画“实际出现过的阶段”，避免一堆 0ms 柱子干扰判断；
    - 表格仍保留全部稳定主阶段，方便快速看出哪个阶段缺失或失败。
    """
    st.subheader("Trace 详情")
    st.write(f"Trace ID：`{trace.trace_id}`")
    st.write(f"文件：`{trace.file_name}` / 集合：`{trace.collection}`")
    st.write(f"状态：`{trace.status}` / 总耗时：`{trace.total_elapsed_ms:.2f} ms`")
    st.write(f"源路径：`{trace.source_path}`")

    chart_rows = [
        {"stage": stage.stage_name, "elapsed_ms": round(stage.elapsed_ms, 2)}
        for stage in trace.stage_breakdown
        if stage.present
    ]
    if chart_rows:
        st.bar_chart(chart_rows, x="stage", y="elapsed_ms")
    else:
        st.info("当前 trace 尚未记录主阶段耗时。")

    stage_rows = [
        {
            "stage": stage.stage_name,
            "present": stage.present,
            "status": stage.status,
            "elapsed_ms": round(stage.elapsed_ms, 2),
            "method": stage.method or "-",
            "provider": stage.provider or "-",
            "source_stages": ", ".join(stage.source_stages) if stage.source_stages else "-",
        }
        for stage in trace.stage_breakdown
    ]
    st.dataframe(stage_rows, use_container_width=True, hide_index=True)


def _format_trace_option(trace_id: str, traces: list[DashboardTraceRecord]) -> str:
    """把 selectbox 里的 `trace_id` 格式化成更易读的摘要。"""
    for item in traces:
        if item.trace_id == trace_id:
            return f"{item.file_name} | {item.collection} | {item.status} | {item.total_elapsed_ms:.2f} ms"
    return trace_id
