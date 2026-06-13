"""Dashboard Query 追踪页面测试（G6）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard.pages.query_traces import QueryTracesSnapshot, build_snapshot, render  # noqa: E402
from observability.dashboard.services.trace_service import (  # noqa: E402
    DashboardTraceRecord,
    QueryCandidatePreview,
    QueryTraceView,
    TraceReadResult,
    TraceRuntimeConfig,
    TraceStageBreakdown,
)


class _FakeStreamlit:
    """最小 fake Streamlit，只覆盖 G6 页面使用到的 API。"""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.dataframes: list[list[dict[str, Any]]] = []
        self.bar_charts: list[list[dict[str, Any]]] = []
        self.markdown_calls: list[dict[str, Any]] = []
        self._text_inputs = {"按 Query 关键词筛选": "azure"}
        self._selectboxes = {"选择一条 Query Trace": "trace-azure"}

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

    def markdown(self, text: str, **kwargs: Any) -> None:
        self.markdown_calls.append({"text": text, "kwargs": kwargs})
        self.messages.append(("markdown", text))

    def dataframe(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(rows)

    def bar_chart(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        _ = kwargs
        self.bar_charts.append(rows)

    def text_input(self, label: str, value: str = "", help: str | None = None) -> str:
        _ = (value, help)
        return self._text_inputs.get(label, value)

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
    """固定返回两条 query trace 与对应视图。"""

    def __init__(self) -> None:
        self.records = [
            DashboardTraceRecord(
                trace_id="trace-azure",
                trace_type="query",
                started_at="2026-06-12T10:00:00+00:00",
                finished_at="2026-06-12T10:00:01+00:00",
                total_elapsed_ms=120.0,
                status="success",
                source_path="-",
                processing_source_path="-",
                file_name="-",
                collection="manual",
                stage_breakdown=(),
                raw_payload={"trace_id": "trace-azure"},
            ),
            DashboardTraceRecord(
                trace_id="trace-gemini",
                trace_type="query",
                started_at="2026-06-12T09:00:00+00:00",
                finished_at="2026-06-12T09:00:01+00:00",
                total_elapsed_ms=98.0,
                status="success",
                source_path="-",
                processing_source_path="-",
                file_name="-",
                collection="manual",
                stage_breakdown=(),
                raw_payload={"trace_id": "trace-gemini"},
            ),
        ]
        self.views = {
            "trace-azure": _make_query_view("如何配置 Azure OpenAI", "manual"),
            "trace-gemini": _make_query_view("如何配置 Gemini", "manual"),
        }

    def load_traces(self, trace_type: str | None = None) -> TraceReadResult:
        assert trace_type == "query"
        return TraceReadResult(
            trace_file="Q:/tmp/logs/traces.jsonl",
            skipped_lines=1,
            records=list(self.records),
        )

    def get_runtime_config(self) -> TraceRuntimeConfig:
        return TraceRuntimeConfig(auto_refresh=True, refresh_interval=5)

    def build_query_trace_view(self, record: DashboardTraceRecord) -> QueryTraceView:
        return self.views[record.trace_id]


def _make_query_view(query_text: str, collection: str) -> QueryTraceView:
    lowered = query_text.lower()
    if "azure" in lowered:
        keywords = ("azure", "openai")
        dense_rows = (
            QueryCandidatePreview(1, "c1", 0.91, "docs/azure.pdf", collection, "dense candidate one"),
            QueryCandidatePreview(2, "c2", 0.87, "docs/setup.pdf", collection, "dense candidate two"),
        )
        sparse_rows = (
            QueryCandidatePreview(1, "c2", 1.10, "docs/setup.pdf", collection, "sparse candidate two"),
            QueryCandidatePreview(2, "c3", 1.02, "docs/ops.pdf", collection, "sparse candidate three"),
        )
        fusion_rows = (
            QueryCandidatePreview(1, "c2", 0.51, "docs/setup.pdf", collection, "fusion candidate two"),
            QueryCandidatePreview(2, "c1", 0.49, "docs/azure.pdf", collection, "fusion candidate one"),
        )
        rerank_rows = (
            QueryCandidatePreview(1, "c1", 0.99, "docs/azure.pdf", collection, "rerank candidate one"),
            QueryCandidatePreview(2, "c2", 0.88, "docs/setup.pdf", collection, "rerank candidate two"),
        )
    else:
        keywords = ("gemini", "vision")
        dense_rows = (
            QueryCandidatePreview(1, "g1", 0.83, "docs/gemini.pdf", collection, "dense gemini one"),
        )
        sparse_rows = (
            QueryCandidatePreview(1, "g2", 1.01, "docs/gemini_setup.pdf", collection, "sparse gemini two"),
        )
        fusion_rows = (
            QueryCandidatePreview(1, "g1", 0.48, "docs/gemini.pdf", collection, "fusion gemini one"),
            QueryCandidatePreview(2, "g2", 0.44, "docs/gemini_setup.pdf", collection, "fusion gemini two"),
        )
        rerank_rows = (
            QueryCandidatePreview(1, "g2", 0.97, "docs/gemini_setup.pdf", collection, "rerank gemini two"),
            QueryCandidatePreview(2, "g1", 0.86, "docs/gemini.pdf", collection, "rerank gemini one"),
        )

    return QueryTraceView(
        query_text=query_text,
        normalized_query=query_text.lower(),
        collection=collection,
        keywords=keywords,
        top_k=2,
        stage_breakdown=(
            TraceStageBreakdown("query_processing", 1.0, "ok", "rule_based_query_processor", "QueryProcessor", True, ("query_processing",)),
            TraceStageBreakdown("dense_retrieval", 3.0, "ok", "embedding_vector_query", "openai", True, ("dense_retrieval",)),
            TraceStageBreakdown("sparse_retrieval", 2.5, "ok", "bm25_get_by_ids", "bm25", True, ("sparse_retrieval",)),
            TraceStageBreakdown("fusion", 1.2, "ok", "rrf", "RRFFusion", True, ("fusion",)),
            TraceStageBreakdown("rerank", 4.4, "ok", "backend_rerank_with_fallback", "ordered_backend", True, ("rerank",)),
        ),
        query_processing_details={
            "original_query": query_text,
            "normalized_query": query_text.lower(),
            "keywords": list(keywords),
            "method": "rule_based_query_processor",
        },
        dense_details={"provider": "openai", "method": "embedding_vector_query"},
        sparse_details={"provider": "bm25", "method": "bm25_get_by_ids"},
        fusion_details={"provider": "RRFFusion", "method": "rrf"},
        rerank_details={"provider": "ordered_backend", "backend": "ordered_backend", "fallback": False},
        dense_results=dense_rows,
        sparse_results=sparse_rows,
        fusion_results=fusion_rows,
        rerank_results=rerank_rows,
        final_results=rerank_rows,
    )


def test_build_snapshot_filters_query_history_by_keyword() -> None:
    """
    Given:
        一个返回两条 query trace 的 fake TraceService，其中只有一条 query 文本包含 `azure`。
    When:
        调用 `build_snapshot(keyword_filter="azure")`。
    Then:
        页面快照应只保留命中的那条记录，并默认选中它。
    """
    service = _FakeTraceService()

    snapshot: QueryTracesSnapshot = build_snapshot(service, keyword_filter="azure")

    assert [item.trace_id for item in snapshot.traces] == ["trace-azure"]
    assert snapshot.selected_trace is not None
    assert snapshot.selected_trace.trace_id == "trace-azure"
    assert snapshot.selected_view is not None
    assert snapshot.selected_view.query_text == "如何配置 Azure OpenAI"


def test_query_traces_render_shows_basic_info_and_stage_details() -> None:
    """
    Given:
        一个会返回 query trace 历史和对应视图的 fake TraceService，
        以及一个预设筛选词与选中 trace 的 fake Streamlit。
    When:
        调用 `render(trace_service=fake_service, st_module=fake_streamlit)`。
    Then:
        - 页面应展示过滤后的历史列表；
        - 应出现 query 阶段耗时图；
        - 应展示基础信息区块；
        - 应展示阶段详情表，且包含 method/provider/backend/fallback/耗时等摘要；
        - 仍保留 Dense/Sparse 对比表、Fusion 结果表、Rerank 前后对比表和最终结果表；
        - 候选表中的 text 不应再被裁剪，且 source_path 应位于 text 后面。
    """
    fake_streamlit = _FakeStreamlit()
    service = _FakeTraceService()

    render(trace_service=service, st_module=fake_streamlit)

    assert len(fake_streamlit.dataframes) >= 6
    assert fake_streamlit.dataframes[0][0]["trace_id"] == "trace-azure"
    assert fake_streamlit.dataframes[1][0]["阶段"] == "Query Processing"
    assert "method=rule_based_query_processor" in fake_streamlit.dataframes[1][0]["记录内容"]
    assert "provider=openai" in fake_streamlit.dataframes[1][1]["记录内容"]
    assert "algorithm=rrf" in fake_streamlit.dataframes[1][3]["记录内容"]
    assert "backend=ordered_backend" in fake_streamlit.dataframes[1][4]["记录内容"]
    assert "fallback=False" in fake_streamlit.dataframes[1][4]["记录内容"]
    assert "耗时=" in fake_streamlit.dataframes[1][4]["记录内容"]
    assert fake_streamlit.dataframes[2][0]["text"] == "dense candidate one"
    assert list(fake_streamlit.dataframes[2][0].keys()) == [
        "rank",
        "chunk_id",
        "score",
        "collection",
        "text",
        "source_path",
    ]
    assert fake_streamlit.dataframes[4][0]["chunk_id"] == "c2"
    assert fake_streamlit.dataframes[5][0]["chunk_id"] == "c1"
    assert fake_streamlit.dataframes[4][0]["text"] == "fusion candidate two"

    assert fake_streamlit.bar_charts
    assert [row["stage"] for row in fake_streamlit.bar_charts[0]] == [
        "query_processing",
        "dense_retrieval",
        "sparse_retrieval",
        "fusion",
        "rerank",
    ]
    assert any(kind == "markdown" and "基础信息" in text for kind, text in fake_streamlit.messages)
    assert any(kind == "subheader" and "Fusion 结果" in text for kind, text in fake_streamlit.messages)
    assert any(kind == "write" and "algorithm=`rrf`" in text for kind, text in fake_streamlit.messages)
    assert any(kind == "write" and "Timestamp" in text for kind, text in fake_streamlit.messages)
    assert any(kind == "write" and "如何配置 Azure OpenAI" in text for kind, text in fake_streamlit.messages)
    assert all("trace_type" not in text.lower() for kind, text in fake_streamlit.messages if kind in {"write", "markdown"})
    assert any(call["kwargs"].get("unsafe_allow_html") is True for call in fake_streamlit.markdown_calls)
