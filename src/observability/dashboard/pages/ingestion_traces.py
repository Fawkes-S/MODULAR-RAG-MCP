"""Dashboard Ingestion 追踪页面（G5）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from observability.dashboard.pages._table_utils import render_wrapped_dataframe
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
    """构造 G5 页面所需的完整数据快照。"""
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

    做什么：
    - 展示 ingestion 历史列表；
    - 让用户选中一条 trace；
    - 用“基础信息 / 汇总指标 / 阶段记录内容 / 原始阶段明细”的结构展开单次摄取。

    为什么：
    - `03-tech-stack.md` 的 `3.4.2` 不是只要求一个耗时图，而是要求人能看清
      “处理了什么、怎么处理、各阶段产出了什么”；
    - 所以 G5 页面不能停留在主阶段耗时摘要，必须把 trace 里已经记录下来的过程信息组织出来。

    关键权衡：
    - 页面会同时展示“稳定主阶段视图”和“原始细粒度阶段”；
    - 前者方便横向比较不同 ingestion，后者方便排障和理解实际执行过程。

    失败路径：
    - trace 文件为空或过滤后无结果时，展示提示而不是报错；
    - 历史 trace 若缺字段，页面统一回退为 `-`，避免老数据把整个页面打挂。
    """
    import streamlit as st

    active_st = st_module or st
    service = trace_service or TraceService()
    snapshot = build_snapshot(service)

    active_st.title("Ingestion 追踪")
    active_st.caption("按 trace_id 查看摄取历史、阶段细节与最终汇总指标。")
    active_st.caption(f"Trace 文件：`{snapshot.trace_file}`")
    active_st.caption(
        f"自动刷新配置：`{snapshot.auto_refresh}` / 间隔 `{snapshot.refresh_interval}s`"
    )

    if snapshot.skipped_lines:
        active_st.warning(
            f"读取 trace 时跳过了 {snapshot.skipped_lines} 行坏数据，其余合法记录仍会继续展示。"
        )

    if not snapshot.traces:
        active_st.info("当前还没有可展示的 Ingestion Trace。先执行一次 ingest，再回到这里查看追踪历史。")
        return

    active_st.subheader("摄取历史")
    render_wrapped_dataframe(active_st, _build_history_rows(snapshot.traces))

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
            "started_at": _format_datetime_text(item.started_at),
            "total_elapsed_ms": round(float(item.total_elapsed_ms), 2),
            "source_path": item.source_path,
            "processing_source_path": item.processing_source_path,
        }
        for item in traces
    ]


def _render_detail(st: Any, trace: DashboardTraceRecord) -> None:
    """渲染单条 Ingestion Trace 的完整过程视图。"""
    st.subheader("Trace 详情")
    st.markdown("**基础信息**")
    st.write(f"Trace ID：`{trace.trace_id}`")
    st.write('Trace Type：`ingestion`')
    st.write(f"Timestamp：`{_format_datetime_text(trace.started_at)}`")
    st.write(f"Source Path：`{trace.source_path}`")
    st.write(f"Processing Source Path：`{trace.processing_source_path}`")
    st.write(f"Collection：`{trace.collection}`")
    st.write(f"Status：`{trace.status}` / 总耗时：`{trace.total_elapsed_ms:.2f} ms`")

    st.markdown("**汇总指标**")
    for line in _build_summary_lines(trace):
        st.write(line)

    chart_rows = [
        {"stage": stage.stage_name, "elapsed_ms": round(stage.elapsed_ms, 2)}
        for stage in trace.stage_breakdown
        if stage.present
    ]
    if chart_rows:
        st.bar_chart(chart_rows, x="stage", y="elapsed_ms")
    else:
        st.info("当前 trace 尚未记录主阶段耗时。")

    st.subheader("各阶段记录内容")
    stage_rows = _build_stage_detail_rows(trace)
    if stage_rows:
        render_wrapped_dataframe(st, stage_rows)
    else:
        st.info("当前 trace 没有可展示的阶段记录内容。")

    st.subheader("原始阶段明细")
    raw_stage_rows = _build_raw_stage_rows(trace)
    if raw_stage_rows:
        render_wrapped_dataframe(st, raw_stage_rows)
    else:
        st.info("当前 trace 没有原始阶段明细。")


def _build_summary_lines(trace: DashboardTraceRecord) -> list[str]:
    """把 3.4.2 的汇总指标整理成逐行文本。

    为什么不用 metrics 卡片：
    - 这些指标里有布尔值、错误文本、可变来源字段，适合以可读文本形式一起呈现；
    - 这样老 trace 缺字段时也能平滑回退，而不是留下大片空卡片。
    """
    payload = trace.raw_payload
    stage_rows = payload.get("stages")
    stages = stage_rows if isinstance(stage_rows, list) else []

    total_chunks = _extract_upsert_metric(stages, key="upsert_count")
    if total_chunks == "-":
        total_chunks = _extract_stage_metric(stages, "split", "chunk_count")

    total_images = _extract_upsert_metric(stages, key="image_count")
    skipped = "yes" if trace.status == "skipped" else "no"
    error_text = _extract_error_text(stages) if trace.status == "failed" else "-"

    return [
        f"total_latency：`{trace.total_elapsed_ms:.2f} ms`",
        f"total_chunks：`{total_chunks}`",
        f"total_images：`{total_images}`",
        f"skipped：`{skipped}`",
        f"error：`{error_text}`",
    ]


def _build_stage_detail_rows(trace: DashboardTraceRecord) -> list[dict[str, object]]:
    """按 `3.4.2` 要求提炼可读的阶段记录内容。

    做什么：
    - 不是把原始 JSON 整包抛给用户，而是先按 Load/Split/Transform/Embed/Upsert
      五个稳定主阶段组织，再补出 transform/store 里的关键细分步骤；
    - 对于一个主阶段下存在多个原始子阶段的情况，页面优先展示“主阶段概览”，
      再补“关键子步骤明细”，让人既能横向比较，也能顺着细节排障。

    为什么：
    - `03-tech-stack.md` 里既要求统一追踪结构，也强调可观测性要能解释
      “做了什么、怎么做、产出了什么”；
    - 仅展示稳定主阶段耗时还不够，因为很多关键统计其实落在
      `transform.chunk_refiner`、`transform.image_captioner`、`pipeline.store.*`
      这些细粒度阶段里。
    """
    stage_rows = trace.raw_payload.get("stages")
    stages = stage_rows if isinstance(stage_rows, list) else []
    rows = [
        _build_stage_row(
            stage="Load",
            method=_join_unique(_find_stage_values(stages, "load", "method")),
            provider=_join_unique(_find_stage_values(stages, "load", "provider")),
            source_stage=_join_unique(_find_stage_values(stages, "load", "source_stage")),
            details=(
                f"文件大小={_format_file_size(_extract_request_value(stages, 'file_size'))}; "
                f"文档类型={_extract_stage_metric(stages, 'load', 'doc_type')}; "
                f"提取图片数={_extract_stage_metric(stages, 'load', 'image_count')}; "
                f"文本长度={_extract_stage_metric(stages, 'load', 'text_length')}"
            ),
            elapsed=_stage_elapsed(trace, "load"),
        ),
        _build_stage_row(
            stage="Split",
            method=_join_unique(_find_stage_values(stages, "split", "method")),
            provider=_join_unique(_find_stage_values(stages, "split", "provider")),
            source_stage=_join_unique(_find_stage_values(stages, "split", "source_stage")),
            details=(
                f"chunk数={_extract_stage_metric(stages, 'split', 'chunk_count')}; "
                f"平均chunk长度={_extract_stage_metric(stages, 'split', 'avg_chunk_length')}; "
                f"最大chunk长度={_extract_stage_metric(stages, 'split', 'max_chunk_length')}; "
                f"chunk_size={_extract_stage_metric(stages, 'split', 'chunk_size')}; "
                f"chunk_overlap={_extract_stage_metric(stages, 'split', 'chunk_overlap')}"
            ),
            elapsed=_stage_elapsed(trace, "split"),
        ),
        _build_stage_row(
            stage="Transform / 总览",
            method=_join_unique(_find_stage_values(stages, "transform", "transform_name")),
            provider=_join_unique(_find_stage_values(stages, "transform", "provider")),
            source_stage=_join_unique(_find_stage_values(stages, "transform", "source_stage")),
            details=(
                f"输出chunk数={_extract_stage_metric(stages, 'transform', 'chunk_count')}; "
                f"transform链路={_join_unique(_find_stage_values(stages, 'transform', 'transform_name'))}"
            ),
            elapsed=_stage_elapsed(trace, "transform"),
        ),
        _build_stage_row(
            stage="Embed",
            method=_join_unique(_find_stage_values(stages, "embed", "method")),
            provider=_join_unique(_find_stage_values(stages, "embed", "embedding_provider")),
            source_stage=_join_unique(_find_stage_values(stages, "embed", "source_stage")),
            details=(
                f"batch数={_extract_stage_metric(stages, 'embed', 'batch_count')}; "
                f"batch_size={_extract_stage_metric(stages, 'embed', 'batch_size')}; "
                f"向量维度={_extract_stage_metric(stages, 'embed', 'dense_dim')}; "
                f"sparse词项数={_extract_stage_metric(stages, 'embed', 'sparse_term_count')}; "
                f"编码记录数={_extract_stage_metric(stages, 'embed', 'record_count')}"
            ),
            elapsed=_stage_elapsed(trace, "embed"),
        ),
        _build_stage_row(
            stage="Upsert",
            method=_join_unique(_find_stage_values(stages, "upsert", "method")),
            provider=_join_unique(_find_stage_values(stages, "upsert", "provider")),
            source_stage=_join_unique(_find_stage_values(stages, "upsert", "source_stage")),
            details=(
                f"向量upsert数={_extract_upsert_metric(stages, 'upsert_count')}; "
                f"图片存储数={_extract_upsert_metric(stages, 'image_count')}; "
                f"BM25词项数={_extract_upsert_metric(stages, 'bm25_terms')}; "
                f"BM25文档数={_extract_upsert_metric(stages, 'bm25_doc_count')}"
            ),
            elapsed=_stage_elapsed(trace, "upsert"),
        ),
    ]

    # Transform 的很多关键统计不在稳定阶段 `transform` 自身，而在细粒度 raw stage。
    # 这里额外展开关键子步骤，让 Dashboard 能解释“具体做了哪些增强、各自处理成什么样”。
    rows.extend(_build_transform_detail_rows(stages))
    return rows


def _build_stage_row(
    *,
    stage: str,
    method: str,
    provider: str,
    source_stage: str,
    details: str,
    elapsed: str,
) -> dict[str, object]:
    """统一构造阶段详情表的单行。

    这样做的原因是页面现在不只展示一列“记录内容”，而是拆成
    “阶段 / 方法 / Provider / 来源子阶段 / 处理详情 / 耗时”六列。
    统一入口能减少后续扩展 G5/G6 时的重复样板代码。
    """
    return {
        "阶段": stage,
        "算法/方法": method or "-",
        "实现/Provider": provider or "-",
        "来源子阶段": source_stage or "-",
        "处理详情": details or "-",
        "耗时": elapsed or "-",
    }


def _build_transform_detail_rows(stages: list[Any]) -> list[dict[str, object]]:
    """补充 transform 子步骤的可读明细。

    关键逻辑：
    - 稳定阶段 `transform` 更适合做“横向比较”，但它只保留了压缩后的概览；
    - 真正反映规则回退、LLM 成功、caption 数量的，是
      `transform.chunk_refiner` / `transform.metadata_enricher` / `transform.image_captioner`；
    - 因此这里混合读取两层 trace：主阶段保留在上方，细节通过本 helper 下钻展示。
    """
    rows: list[dict[str, object]] = []
    raw_stage_specs = [
        (
            "transform.chunk_refiner",
            "Transform / ChunkRefiner",
            lambda details: (
                f"处理chunk数={details.get('total', '-')}; "
                f"LLM成功数={details.get('llm_success', '-')}; "
                f"规则回退数={details.get('rule_fallback', '-')}; "
                f"异常数={details.get('errors', '-')}"
            ),
        ),
        (
            "transform.metadata_enricher",
            "Transform / MetadataEnricher",
            lambda details: (
                f"处理chunk数={details.get('total', '-')}; "
                f"LLM成功数={details.get('llm_success', '-')}; "
                f"规则回退数={details.get('rule_fallback', '-')}; "
                f"异常数={details.get('errors', '-')}; "
                f"LLM启用={details.get('llm_enabled', '-')}; "
                f"LLM提供方={details.get('llm_provider', '-')}"
            ),
        ),
        (
            "transform.image_captioner",
            "Transform / ImageCaptioner",
            lambda details: (
                f"处理chunk数={details.get('total', '-')}; "
                f"含图chunk数={details.get('chunks_with_images', '-')}; "
                f"图片引用总数={details.get('image_refs_total', '-')}; "
                f"生成caption图片数={details.get('captioned_images', '-')}; "
                f"降级图片数={details.get('fallback_images', '-')}; "
                f"异常数={details.get('errors', '-')}; "
                f"Vision启用={details.get('vision_enabled', '-')}; "
                f"Vision提供方={details.get('vision_provider', '-')}"
            ),
        ),
    ]

    for raw_stage_name, stage_label, detail_builder in raw_stage_specs:
        raw_stage = _find_last_raw_stage(stages, raw_stage_name)
        if raw_stage is None:
            continue

        details = raw_stage.get("details")
        detail_dict = details if isinstance(details, dict) else {}
        rows.append(
            _build_stage_row(
                stage=stage_label,
                method=raw_stage_name,
                provider="-",
                source_stage=raw_stage_name,
                details=detail_builder(detail_dict),
                elapsed=f"{_coerce_float(raw_stage.get('elapsed_ms', 0.0)):.2f} ms",
            )
        )

    return rows


def _build_raw_stage_rows(trace: DashboardTraceRecord) -> list[dict[str, object]]:
    """把原始 trace 阶段列表摊平成排障友好的明细表。"""
    stage_rows = trace.raw_payload.get("stages")
    stages = stage_rows if isinstance(stage_rows, list) else []
    rows: list[dict[str, object]] = []
    for raw_stage in stages:
        if not isinstance(raw_stage, dict):
            continue
        details = raw_stage.get("details")
        detail_items = details.items() if isinstance(details, dict) else []
        rows.append(
            {
                "stage_name": str(raw_stage.get("stage_name", "-")),
                "status": str(raw_stage.get("status", "ok")),
                "elapsed_ms": round(float(raw_stage.get("elapsed_ms", 0.0)), 2),
                "details": "; ".join(f"{key}={value}" for key, value in detail_items) or "-",
            }
        )
    return rows


def _find_stage_values(stages: list[Any], stable_stage_name: str, detail_key: str) -> list[str]:
    """提取指定稳定阶段下某个 detail 字段的所有值。"""
    values: list[str] = []
    for raw_stage in stages:
        if not isinstance(raw_stage, dict):
            continue
        if str(raw_stage.get("stage_name", "")).strip() != stable_stage_name:
            continue
        details = raw_stage.get("details")
        if not isinstance(details, dict):
            continue
        value = details.get(detail_key)
        text = str(value).strip() if value is not None else ""
        if text:
            values.append(text)
    return values


def _find_last_raw_stage(stages: list[Any], raw_stage_name: str) -> dict[str, Any] | None:
    """按原始 stage_name 取最后一条记录。

    这里取“最后一条”是为了兼容未来可能出现的重试/多次记录场景：
    页面默认展示最终状态，而不是中途已被覆盖的旧统计。
    """
    for raw_stage in reversed(stages):
        if not isinstance(raw_stage, dict):
            continue
        if str(raw_stage.get("stage_name", "")).strip() == raw_stage_name:
            return raw_stage
    return None


def _extract_stage_metric(stages: list[Any], stable_stage_name: str, detail_key: str) -> object:
    """提取某个稳定阶段里最晚一次出现的 detail 指标。"""
    for raw_stage in reversed(stages):
        if not isinstance(raw_stage, dict):
            continue
        if str(raw_stage.get("stage_name", "")).strip() != stable_stage_name:
            continue
        details = raw_stage.get("details")
        if not isinstance(details, dict):
            continue
        value = details.get(detail_key)
        if value is not None:
            return value
    return "-"


def _extract_upsert_metric(stages: list[Any], key: str) -> object:
    """从 upsert 相关阶段里提取指标。

    为什么单独做这个 helper：
    - upsert 在 trace 中可能来自 `store.images`、`store.vector_upsert`、`store.bm25`
      三条不同原始阶段；
    - 这里按“谁记录了这个指标就取谁”的方式兜底，避免页面和具体存储步骤强耦合。
    """
    stage_names = {"upsert", "pipeline.store.images", "pipeline.store.vector_upsert", "pipeline.store.bm25"}
    for raw_stage in reversed(stages):
        if not isinstance(raw_stage, dict):
            continue
        if str(raw_stage.get("stage_name", "")).strip() not in stage_names:
            continue
        details = raw_stage.get("details")
        if not isinstance(details, dict):
            continue
        value = details.get(key)
        if value is not None:
            return value
    return "-"


def _extract_request_value(stages: list[Any], key: str) -> object:
    """提取 `pipeline.request` 中记录的入口上下文字段。"""
    for raw_stage in stages:
        if not isinstance(raw_stage, dict):
            continue
        if str(raw_stage.get("stage_name", "")).strip() != "pipeline.request":
            continue
        details = raw_stage.get("details")
        if isinstance(details, dict) and details.get(key) is not None:
            return details.get(key)
    return "-"


def _extract_error_text(stages: list[Any]) -> str:
    """提取第一条 error 阶段的错误摘要。"""
    for raw_stage in stages:
        if not isinstance(raw_stage, dict):
            continue
        if str(raw_stage.get("status", "")).strip().lower() != "error":
            continue
        details = raw_stage.get("details")
        if not isinstance(details, dict):
            continue
        error_type = str(details.get("error_type", "")).strip()
        error_text = str(details.get("error", "")).strip()
        combined = ": ".join(part for part in [error_type, error_text] if part)
        if combined:
            return combined
    return "-"


def _join_unique(values: list[str]) -> str:
    """去重并拼接多个可读值。"""
    ordered: list[str] = []
    for item in values:
        if item not in ordered:
            ordered.append(item)
    return ", ".join(ordered) if ordered else "-"


def _stage_elapsed(trace: DashboardTraceRecord, stage_name: str) -> str:
    """读取稳定主阶段耗时；缺失时返回 `-`。"""
    for stage in trace.stage_breakdown:
        if stage.stage_name == stage_name and stage.present:
            return f"{stage.elapsed_ms:.2f} ms"
    return "-"


def _format_trace_option(trace_id: str, traces: list[DashboardTraceRecord]) -> str:
    """把 selectbox 里的 `trace_id` 格式化成更易读的摘要。"""
    for item in traces:
        if item.trace_id == trace_id:
            return f"{item.file_name} | {item.collection} | {item.status} | {item.total_elapsed_ms:.2f} ms"
    return trace_id


def _format_datetime_text(raw_value: str | None) -> str:
    """把 ISO 时间戳转换为更适合普通人阅读的格式。

    例如：
    - `2026-06-11T10:00:00+00:00`
    - -> `2026-06-11 10:00:00 UTC+00:00`

    失败路径：
    - 若旧 trace 里的时间格式无法解析，就回退原文，避免页面直接丢值。
    """
    text = str(raw_value or "").strip()
    if not text:
        return "-"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text

    base_text = parsed.strftime("%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is None:
        return base_text

    offset_text = parsed.strftime("%z")
    if len(offset_text) == 5:
        offset_text = f"{offset_text[:3]}:{offset_text[3:]}"
    return f"{base_text} UTC{offset_text}" if offset_text else base_text


def _format_file_size(value: object) -> str:
    """把字节数格式化成“原始值 + 易读单位”。

    之所以同时保留两种表示：
    - 原始字节数适合精确排障；
    - KB/MB 适合用户快速扫一眼理解文件量级。
    """
    if not isinstance(value, (int, float)):
        return str(value) if value not in (None, "") else "-"

    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{int(value):,} B ({size:.2f} {units[unit_index]})"


def _coerce_float(value: object) -> float:
    """安全把任意对象转成 float，失败时回退到 0.0。"""
    try:
        return float(value)
    except Exception:
        return 0.0
