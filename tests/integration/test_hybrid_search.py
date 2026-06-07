"""HybridSearch 集成测试（D5）。"""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter
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
from core.query_engine.reranker import Reranker  # noqa: E402
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

    def __init__(
        self,
        results: list[RetrievalResult] | None = None,
        should_fail: bool = False,
        provider: str = "openai",
        vector_store_provider: str = "chroma",
    ) -> None:
        self.results = list(results or [])
        self.should_fail = should_fail
        self.provider = provider
        self.vector_store_provider = vector_store_provider
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        started = perf_counter()
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
        if trace is not None:
            # F3 关注的是 Query 链路是否完整落下阶段，因此测试桩也要模拟真实 retriever 的打点契约。
            trace.record_stage(
                stage_name="dense_retrieval",
                details={
                    "method": "embedding_vector_query",
                    "provider": self.provider,
                    "query": query,
                    "top_k": top_k,
                    "returned_count": len(self.results),
                    "embedding_provider": self.provider,
                    "vector_store_provider": self.vector_store_provider,
                    "filters": dict(filters) if isinstance(filters, dict) else filters,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )
        return list(self.results)


class _FakeSparseRetriever:
    """测试桩：可控 Sparse 路由结果与失败行为。"""

    def __init__(
        self,
        results: list[RetrievalResult] | None = None,
        should_fail: bool = False,
        vector_store_provider: str = "chroma",
    ) -> None:
        self.results = list(results or [])
        self.should_fail = should_fail
        self.vector_store_provider = vector_store_provider
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        keywords: list[str],
        top_k: int,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        started = perf_counter()
        self.calls.append({"keywords": list(keywords), "top_k": top_k, "trace": trace})
        if self.should_fail:
            raise RuntimeError("sparse route temporary unavailable")
        if trace is not None:
            # Sparse 侧同样补齐 method/provider 等字段，确保集成测试验证的是统一 trace 契约。
            trace.record_stage(
                stage_name="sparse_retrieval",
                details={
                    "method": "bm25_get_by_ids",
                    "provider": "bm25",
                    "keywords": list(keywords),
                    "top_k": top_k,
                    "matched_ids": [item.chunk_id for item in self.results],
                    "returned_count": len(self.results),
                    "vector_store_provider": self.vector_store_provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )
        return list(self.results)


class _OrderedRerankBackend:
    """测试桩：返回固定顺序，用于验证 rerank trace 是否写出。"""

    provider_name = "ordered_backend"

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: TraceContext | None = None,
    ) -> list[dict[str, Any]]:
        _ = (query, trace)
        return [
            dict(item, rerank_score=1.0 / (index + 1))
            for index, item in enumerate(candidates)
        ]


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


def _get_stage(trace: TraceContext, stage_name: str) -> dict[str, Any]:
    for stage in trace.stages:
        if stage.get("stage_name") == stage_name:
            return stage
    raise AssertionError(f"missing trace stage: {stage_name}")


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
    query_stage = _get_stage(trace, "query_processing")
    dense_stage = _get_stage(trace, "dense_retrieval")
    sparse_stage = _get_stage(trace, "sparse_retrieval")
    fusion_stage = _get_stage(trace, "fusion")
    summary_stage = _get_stage(trace, "hybrid_search")

    assert query_stage["details"]["method"] == "rule_based_query_processor"
    assert query_stage["details"]["provider"] == "QueryProcessor"
    assert query_stage["details"]["filters"] == {"collection": "manual", "doc_type": "pdf"}
    assert "elapsed_ms" in query_stage

    assert dense_stage["details"]["method"] == "embedding_vector_query"
    assert dense_stage["details"]["provider"] == "openai"
    assert dense_stage["details"]["vector_store_provider"] == "chroma"
    assert "elapsed_ms" in dense_stage

    assert sparse_stage["details"]["method"] == "bm25_get_by_ids"
    assert sparse_stage["details"]["provider"] == "bm25"
    assert sparse_stage["details"]["vector_store_provider"] == "chroma"
    assert "elapsed_ms" in sparse_stage

    assert fusion_stage["details"]["method"] == "rrf"
    assert fusion_stage["details"]["provider"] == "RRFFusion"
    assert fusion_stage["details"]["fused_count"] == 3
    assert "elapsed_ms" in fusion_stage

    assert summary_stage["details"]["method"] == "query_processor_parallel_retrieval_rrf"
    assert summary_stage["details"]["provider"] == "RRFFusion"
    assert summary_stage["details"]["filtered_count"] == 2

    trace.finish()
    assert trace.to_dict()["trace_type"] == "query"


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


def test_reranker_records_method_provider_and_trace_payload() -> None:
    """
    Given:
        一个可正常执行的 Core Reranker，
        以及来自 HybridSearch 的两个候选结果。
    When:
        调用 `Reranker.rerank(..., trace=trace)` 执行精排。
    Then:
        trace 中应写入 `rerank` 阶段，
        且包含 `method/provider/fallback/input_count/output_count` 等 F3 关注字段。
    """
    reranker = Reranker(settings=_make_settings(), backend=_OrderedRerankBackend())  # type: ignore[arg-type]
    trace = TraceContext(trace_type="query")

    output = reranker.rerank(
        query="Azure OpenAI",
        candidates=[
            _make_result("c1", 0.91, collection="manual", doc_type="pdf", text="dense-c1"),
            _make_result("c2", 0.87, collection="manual", doc_type="pdf", text="dense-c2"),
        ],
        top_k=2,
        trace=trace,
    )

    assert [item.chunk_id for item in output.results] == ["c1", "c2"]
    rerank_stage = _get_stage(trace, "rerank")
    assert rerank_stage["details"]["method"] == "backend_rerank_with_fallback"
    assert rerank_stage["details"]["provider"] == "ordered_backend"
    assert rerank_stage["details"]["backend"] == "ordered_backend"
    assert rerank_stage["details"]["fallback"] is False
    assert rerank_stage["details"]["input_count"] == 2
    assert rerank_stage["details"]["output_count"] == 2
    assert "elapsed_ms" in rerank_stage
