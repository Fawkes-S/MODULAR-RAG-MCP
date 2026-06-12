"""Dashboard Ingestion 追踪页面测试（G5）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard.pages.ingestion_traces import IngestionTracesSnapshot, build_snapshot, render  # noqa: E402
from observability.dashboard.services.trace_service import (  # noqa: E402
    DashboardTraceRecord,
    TraceReadResult,
    TraceRuntimeConfig,
    TraceStageBreakdown,
)


class _FakeStreamlit:
    """最小 fake Streamlit，只覆盖 G5 页面用到的 API。"""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.dataframes: list[list[dict[str, Any]]] = []
        self.bar_charts: list[list[dict[str, Any]]] = []
        self._selectboxes = {"选择一条摄取 Trace": "trace-new"}

    def title(self, text: str) -> None:
        self.messages.append(("title", text))

    def caption(self, text: str) -> None:
        self.messages.append(("caption", text))

    def subheader(self, text: str) -> None:
        self.messages.append(("subheader", text))

    def warning(self, text: str) -> None:
        self.messages.append(("warning", text))

    def info(self, text: str) -> None:
        self.messages.append(("info", text))

    def write(self, text: str) -> None:
        self.messages.append(("write", text))

    def dataframe(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(rows)

    def bar_chart(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        _ = kwargs
        self.bar_charts.append(rows)

    def selectbox(
        self,
        label: str,
        options: list[Any],
        index: int = 0,
        format_func: Any | None = None,
        help: str | None = None,
    ) -> Any:
        _ = (index, format_func, help)
        selected = self._selectboxes.get(label, options[0] if options else None)
        return selected if selected in options else (options[0] if options else None)


class _FakeTraceService:
    """测试桩：固定返回两条 ingestion trace 与运行配置。"""

    def __init__(self) -> None:
        self.records = [
            _make_trace_record(
                trace_id="trace-new",
                file_name="beta.pdf",
                collection="prod",
                total_elapsed_ms=220.0,
                status="success",
            ),
            _make_trace_record(
                trace_id="trace-old",
                file_name="alpha.pdf",
                collection="demo",
                total_elapsed_ms=150.0,
                status="failed",
            ),
        ]

    def load_traces(self, trace_type: str | None = None) -> TraceReadResult:
        assert trace_type == "ingestion"
        return TraceReadResult(
            trace_file="Q:/tmp/logs/traces.jsonl",
            skipped_lines=1,
            records=list(self.records),
        )

    def get_runtime_config(self) -> TraceRuntimeConfig:
        return TraceRuntimeConfig(auto_refresh=True, refresh_interval=5)


def _make_trace_record(
    *,
    trace_id: str,
    file_name: str,
    collection: str,
    total_elapsed_ms: float,
    status: str,
) -> DashboardTraceRecord:
    return DashboardTraceRecord(
        trace_id=trace_id,
        trace_type="ingestion",
        started_at="2026-06-11T10:00:00+00:00",
        finished_at="2026-06-11T10:00:01+00:00",
        total_elapsed_ms=total_elapsed_ms,
        status=status,
        source_path=f"Q:/docs/{file_name}",
        file_name=file_name,
        collection=collection,
        stage_breakdown=(
            TraceStageBreakdown(
                stage_name="load",
                elapsed_ms=10.0,
                status="ok",
                method="pdf",
                provider="PdfLoader",
                present=True,
                source_stages=("load",),
            ),
            TraceStageBreakdown(
                stage_name="split",
                elapsed_ms=15.0,
                status="ok",
                method="recursive",
                provider="RecursiveCharacterTextSplitter",
                present=True,
                source_stages=("split",),
            ),
            TraceStageBreakdown(
                stage_name="transform",
                elapsed_ms=20.0,
                status="ok",
                method="ChunkRefiner",
                provider="ChunkRefiner",
                present=True,
                source_stages=("transform.ChunkRefiner", "transform.MetadataEnricher"),
            ),
            TraceStageBreakdown(
                stage_name="embed",
                elapsed_ms=30.0,
                status="ok",
                method="batch_dense_sparse_encode",
                provider="huggingface_local",
                present=True,
                source_stages=("encode",),
            ),
            TraceStageBreakdown(
                stage_name="upsert",
                elapsed_ms=25.0,
                status="error" if status == "failed" else "ok",
                method="vector_store_upsert",
                provider="chroma",
                present=True,
                source_stages=("store.vector_upsert",),
            ),
        ),
        raw_payload={"trace_id": trace_id},
    )


def test_build_snapshot_defaults_to_latest_trace_and_supports_explicit_selection() -> None:
    """
    Given:
        一个固定返回两条按时间倒序 trace 的 fake TraceService。
    When:
        分别调用 `build_snapshot()` 默认模式与显式传入 `selected_trace_id`。
    Then:
        - 默认应选中第一条（最新）trace；
        - 显式传入 trace_id 时，应切换到对应详情对象；
        - 页面还应拿到 trace 文件路径与自动刷新配置。
    """
    service = _FakeTraceService()

    latest_snapshot: IngestionTracesSnapshot = build_snapshot(service)
    selected_snapshot: IngestionTracesSnapshot = build_snapshot(service, selected_trace_id="trace-old")

    assert latest_snapshot.selected_trace is not None
    assert latest_snapshot.selected_trace.trace_id == "trace-new"
    assert latest_snapshot.trace_file == "Q:/tmp/logs/traces.jsonl"
    assert latest_snapshot.auto_refresh is True
    assert latest_snapshot.refresh_interval == 5

    assert selected_snapshot.selected_trace is not None
    assert selected_snapshot.selected_trace.trace_id == "trace-old"


def test_ingestion_traces_render_shows_history_warning_and_stage_chart() -> None:
    """
    Given:
        一个会返回两条 trace 与 1 条坏行计数的 fake TraceService，
        以及一个预设选择最新 trace 的 fake Streamlit。
    When:
        调用 `render(trace_service=fake_service, st_module=fake_streamlit)`。
    Then:
        - 页面应展示历史列表；
        - 因坏行计数应出现 warning；
        - 应为选中的 trace 画出阶段耗时图；
        - 详情区应展示文件名、集合与总耗时等关键信息。
    """
    fake_streamlit = _FakeStreamlit()
    service = _FakeTraceService()

    render(trace_service=service, st_module=fake_streamlit)

    assert fake_streamlit.dataframes
    assert fake_streamlit.dataframes[0][0]["trace_id"] == "trace-new"
    assert any(kind == "warning" and "跳过了 1 行坏数据" in text for kind, text in fake_streamlit.messages)
    assert fake_streamlit.bar_charts
    assert [row["stage"] for row in fake_streamlit.bar_charts[0]] == [
        "load",
        "split",
        "transform",
        "embed",
        "upsert",
    ]
    assert any(kind == "write" and "beta.pdf" in text for kind, text in fake_streamlit.messages)
