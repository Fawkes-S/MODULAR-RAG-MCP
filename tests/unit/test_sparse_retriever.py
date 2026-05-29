"""SparseRetriever 单元测试（D3）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.sparse_retriever import SparseRetriever  # noqa: E402
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


class _FakeBM25Indexer:
    """用于测试稀疏检索编排的 BM25 假实现。"""

    def __init__(self, hits: list[tuple[str, float]] | None = None) -> None:
        self.hits = hits if hits is not None else []
        self.calls: list[dict[str, Any]] = []

    def query(self, query: str | list[str], top_k: int = 10) -> list[tuple[str, float]]:
        self.calls.append({"query": query, "top_k": top_k})
        return list(self.hits)


class _FakeVectorStore:
    """用于测试正文回填的 VectorStore 假实现。"""

    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = docs if docs is not None else []
        self.calls: list[dict[str, Any]] = []

    def get_by_ids(self, ids: list[str], trace: TraceContext | None = None) -> list[dict[str, Any]]:
        self.calls.append({"ids": list(ids), "trace": trace})
        return list(self.docs)


def _make_settings() -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=8, sparse_top_k=20),
        rerank=RerankSettings(provider="none", enabled=False, top_m=30),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(),
    )


def test_sparse_retriever_orchestrates_bm25_and_get_by_ids() -> None:
    """
    Given:
        BM25 返回两个命中 ID，vector store 能回填对应 text/metadata。
    When:
        调用 `SparseRetriever.retrieve()`。
    Then:
        应保持 BM25 排名顺序，并返回标准 `RetrievalResult` 列表。
    """
    bm25 = _FakeBM25Indexer(hits=[("c2", 0.8), ("c1", 0.5)])
    vector_store = _FakeVectorStore(
        docs=[
            {"id": "c1", "text": "doc-1", "metadata": {"source_path": "a.pdf"}},
            {"id": "c2", "text": "doc-2", "metadata": {"source_path": "b.pdf"}},
        ]
    )
    retriever = SparseRetriever(settings=_make_settings(), bm25_indexer=bm25, vector_store=vector_store)
    trace = TraceContext(trace_type="query")

    results = retriever.retrieve(keywords=["Azure", "OpenAI"], top_k=2, trace=trace)

    assert bm25.calls[0]["query"] == ["azure", "openai"]
    assert bm25.calls[0]["top_k"] == 2
    assert vector_store.calls[0]["ids"] == ["c2", "c1"]
    assert len(results) == 2
    assert all(isinstance(item, RetrievalResult) for item in results)
    assert [item.chunk_id for item in results] == ["c2", "c1"]
    assert results[0].score == 0.8
    assert results[0].text == "doc-2"
    assert any(stage["stage_name"] == "sparse_retrieval" for stage in trace.stages)


def test_sparse_retriever_skips_missing_documents() -> None:
    """
    Given:
        BM25 命中两个 ID，但 vector store 仅回填一个。
    When:
        执行 `retrieve()`。
    Then:
        缺失正文的候选会被跳过，结果仅包含可回填项。
    """
    bm25 = _FakeBM25Indexer(hits=[("c1", 0.4), ("c2", 0.3)])
    vector_store = _FakeVectorStore(docs=[{"id": "c1", "text": "doc-1", "metadata": {"source_path": "a.pdf"}}])
    retriever = SparseRetriever(settings=_make_settings(), bm25_indexer=bm25, vector_store=vector_store)

    results = retriever.retrieve(keywords=["azure"], top_k=2)

    assert [item.chunk_id for item in results] == ["c1"]


def test_sparse_retriever_validates_keywords_and_top_k() -> None:
    """
    Given:
        非法 keywords 与 top_k 输入。
    When:
        调用 `retrieve()`。
    Then:
        应抛出 `ValueError`，防止错误输入进入检索后端。
    """
    retriever = SparseRetriever(
        settings=_make_settings(),
        bm25_indexer=_FakeBM25Indexer(),
        vector_store=_FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="keywords must be list"):
        retriever.retrieve(keywords="bad", top_k=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"keywords\[0\] must be string"):
        retriever.retrieve(keywords=[123], top_k=1)  # type: ignore[list-item]
    with pytest.raises(ValueError, match="top_k must be positive int"):
        retriever.retrieve(keywords=["ok"], top_k=0)


def test_sparse_retriever_returns_empty_when_no_keywords_or_no_hits() -> None:
    """
    Given:
        空关键词与 BM25 无命中的场景。
    When:
        调用 `retrieve()`。
    Then:
        都应返回空列表，并保持行为稳定。
    """
    retriever_empty_keywords = SparseRetriever(
        settings=_make_settings(),
        bm25_indexer=_FakeBM25Indexer(hits=[("c1", 0.1)]),
        vector_store=_FakeVectorStore(docs=[{"id": "c1", "text": "x", "metadata": {"source_path": "a.pdf"}}]),
    )
    retriever_no_hits = SparseRetriever(
        settings=_make_settings(),
        bm25_indexer=_FakeBM25Indexer(hits=[]),
        vector_store=_FakeVectorStore(docs=[]),
    )

    assert retriever_empty_keywords.retrieve(keywords=["   "], top_k=1) == []
    assert retriever_no_hits.retrieve(keywords=["azure"], top_k=3) == []


def test_sparse_retriever_rejects_invalid_get_by_ids_result_shape() -> None:
    """
    Given:
        vector store 返回缺失 `id` 的脏数据。
    When:
        调用 `retrieve()` 进行结果索引。
    Then:
        应抛出 `ValueError`，阻止不完整记录进入返回结果。
    """
    retriever = SparseRetriever(
        settings=_make_settings(),
        bm25_indexer=_FakeBM25Indexer(hits=[("c1", 0.2)]),
        vector_store=_FakeVectorStore(docs=[{"text": "x", "metadata": {"source_path": "a.pdf"}}]),
    )

    with pytest.raises(ValueError, match="missing id"):
        retriever.retrieve(keywords=["azure"], top_k=1)
