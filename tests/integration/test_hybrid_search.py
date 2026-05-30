"""HybridSearch 集成测试（D5）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.fusion import RRFFusion  # noqa: E402
from core.query_engine.hybrid_search import HybridSearch  # noqa: E402
from core.query_engine.query_processor import QueryProcessor  # noqa: E402
from core.settings import (  # noqa: E402
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
)
from core.trace.trace_context import TraceContext  # noqa: E402
from core.types import RetrievalResult  # noqa: E402


class _FakeDenseRetriever:
    """测试桩：可控 Dense 路由结果与失败行为。"""

    def __init__(self, results: list[RetrievalResult] | None = None, should_fail: bool = False) -> None:
        self.results = list(results or [])
        self.should_fail = should_fail
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "filters": dict(filters) if isinstance(filters, dict) else filters,
                "trace": trace,
            }
        )
        if self.should_fail:
            raise RuntimeError("dense route temporary unavailable")
        return list(self.results)


class _FakeSparseRetriever:
    """测试桩：可控 Sparse 路由结果与失败行为。"""

    def __init__(self, results: list[RetrievalResult] | None = None, should_fail: bool = False) -> None:
        self.results = list(results or [])
        self.should_fail = should_fail
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        keywords: list[str],
        top_k: int,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append({"keywords": list(keywords), "top_k": top_k, "trace": trace})
        if self.should_fail:
            raise RuntimeError("sparse route temporary unavailable")
        return list(self.results)


def _make_settings() -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=4, sparse_top_k=6),
        rerank=RerankSettings(provider="none", enabled=False, top_m=30),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(),
    )


def _make_result(chunk_id: str, score: float, *, collection: str, doc_type: str, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        metadata={
            "source_path": f"{chunk_id}.pdf",
            "collection": collection,
            "doc_type": doc_type,
        },
    )


def test_hybrid_search_returns_top_k_with_text_and_metadata() -> None:
    """
    Given:
        可控的 Dense/Sparse 召回结果，且 query 含内联过滤条件与外部 filters。
    When:
        调用 `HybridSearch.search()` 执行完整编排。
    Then:
        应完成 QueryProcessor->双路召回->RRF 融合->过滤并返回 Top-K，
        且结果包含 chunk 文本与 metadata。
    """
    settings = _make_settings()
    dense = _FakeDenseRetriever(
        results=[
            _make_result("c1", 0.91, collection="manual", doc_type="pdf", text="dense-c1"),
            _make_result("c2", 0.87, collection="manual", doc_type="pdf", text="dense-c2"),
        ]
    )
    sparse = _FakeSparseRetriever(
        results=[
            _make_result("c2", 1.20, collection="manual", doc_type="pdf", text="sparse-c2"),
            _make_result("c3", 1.10, collection="manual", doc_type="pdf", text="sparse-c3"),
        ]
    )
    searcher = HybridSearch(
        settings=settings,
        query_processor=QueryProcessor(settings=settings),
        dense_retriever=dense,  # type: ignore[arg-type]
        sparse_retriever=sparse,  # type: ignore[arg-type]
        fusion=RRFFusion(default_k=60),
    )
    trace = TraceContext(trace_type="query")

    results = searcher.search(
        query="collection:manual Azure OpenAI how to configure",
        top_k=2,
        filters={"doc_type": "pdf"},
        trace=trace,
    )

    assert dense.calls[0]["query"] == "collection:manual Azure OpenAI how to configure"
    assert dense.calls[0]["filters"] == {"collection": "manual", "doc_type": "pdf"}
    assert dense.calls[0]["top_k"] == 4
    assert sparse.calls[0]["keywords"] == ["azure", "openai", "configure"]
    assert sparse.calls[0]["top_k"] == 6

    assert len(results) == 2
    assert [item.chunk_id for item in results] == ["c2", "c1"]
    assert all(item.text for item in results)
    assert all("source_path" in item.metadata for item in results)
    assert any(stage["stage_name"] == "hybrid_search" for stage in trace.stages)


def test_hybrid_search_applies_metadata_filters_as_post_filter_safety_net() -> None:
    """
    Given:
        融合候选中既有 `doc_type=pdf` 也有 `doc_type=md` 的记录。
    When:
        传入 filters={"doc_type": "pdf"} 执行检索。
    Then:
        应通过后置过滤兜底，仅保留满足条件的候选结果。
    """
    settings = _make_settings()
    dense = _FakeDenseRetriever(
        results=[
            _make_result("c1", 0.90, collection="manual", doc_type="pdf", text="dense-c1"),
            _make_result("c2", 0.89, collection="manual", doc_type="md", text="dense-c2"),
        ]
    )
    sparse = _FakeSparseRetriever(
        results=[
            _make_result("c3", 1.05, collection="manual", doc_type="pdf", text="sparse-c3"),
            _make_result("c2", 1.00, collection="manual", doc_type="md", text="sparse-c2"),
        ]
    )
    searcher = HybridSearch(
        settings=settings,
        query_processor=QueryProcessor(settings=settings),
        dense_retriever=dense,  # type: ignore[arg-type]
        sparse_retriever=sparse,  # type: ignore[arg-type]
        fusion=RRFFusion(default_k=60),
    )

    results = searcher.search(
        query="Azure OpenAI docs",
        top_k=3,
        filters={"doc_type": "pdf"},
    )

    assert [item.chunk_id for item in results] == ["c1", "c3"]
    assert all(item.metadata.get("doc_type") == "pdf" for item in results)


def test_hybrid_search_degrades_to_single_route_when_dense_fails() -> None:
    """
    Given:
        Dense 路由抛异常，Sparse 路由仍可正常返回结果。
    When:
        调用 `search()`。
    Then:
        应触发单路降级并返回 Sparse 结果，而不是整体失败。
    """
    settings = _make_settings()
    dense = _FakeDenseRetriever(should_fail=True)
    sparse = _FakeSparseRetriever(
        results=[
            _make_result("c8", 1.1, collection="manual", doc_type="pdf", text="sparse-c8"),
            _make_result("c9", 1.0, collection="manual", doc_type="pdf", text="sparse-c9"),
        ]
    )
    searcher = HybridSearch(
        settings=settings,
        query_processor=QueryProcessor(settings=settings),
        dense_retriever=dense,  # type: ignore[arg-type]
        sparse_retriever=sparse,  # type: ignore[arg-type]
        fusion=RRFFusion(default_k=60),
    )

    results = searcher.search(query="OpenAI fallback", top_k=1)

    assert [item.chunk_id for item in results] == ["c8"]


def test_hybrid_search_raises_when_both_routes_fail() -> None:
    """
    Given:
        Dense 与 Sparse 两路都抛异常。
    When:
        调用 `search()`。
    Then:
        应抛出 `RuntimeError`，并包含双路失败摘要。
    """
    settings = _make_settings()
    searcher = HybridSearch(
        settings=settings,
        query_processor=QueryProcessor(settings=settings),
        dense_retriever=_FakeDenseRetriever(should_fail=True),  # type: ignore[arg-type]
        sparse_retriever=_FakeSparseRetriever(should_fail=True),  # type: ignore[arg-type]
        fusion=RRFFusion(default_k=60),
    )

    with pytest.raises(RuntimeError, match="both dense and sparse routes failed"):
        searcher.search(query="OpenAI", top_k=2)
