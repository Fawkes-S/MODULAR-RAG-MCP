"""DenseRetriever 单元测试（D2）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.dense_retriever import DenseRetriever  # noqa: E402
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


class _FakeEmbeddingClient:
    """用于测试编排调用的 embedding 假实现。"""

    def __init__(self, vectors: list[list[float]] | None = None) -> None:
        self.vectors = vectors if vectors is not None else [[0.1, 0.2, 0.3]]
        self.calls: list[dict[str, Any]] = []

    def embed(self, texts: list[str], trace: TraceContext | None = None) -> list[list[float]]:
        self.calls.append({"texts": list(texts), "trace": trace})
        return self.vectors


class _FakeVectorStore:
    """用于测试编排调用的 vector store 假实现。"""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self.results = results if results is not None else []
        self.calls: list[dict[str, Any]] = []

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "vector": list(vector),
                "top_k": top_k,
                "filters": dict(filters) if isinstance(filters, dict) else filters,
                "trace": trace,
            }
        )
        return list(self.results)


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


def test_dense_retriever_orchestrates_embed_and_vector_query() -> None:
    """
    Given:
        一个可控 embedding 假实现与 vector store 假实现，且 vector store 返回两条命中结果。
    When:
        调用 `DenseRetriever.retrieve()` 执行稠密检索。
    Then:
        应按 `query -> embed -> vector_store.query` 顺序完成编排，并返回标准 `RetrievalResult` 列表。
    """
    embedding_client = _FakeEmbeddingClient(vectors=[[0.9, 0.1, 0.0]])
    vector_store = _FakeVectorStore(
        results=[
            {
                "id": "chunk_1",
                "score": 0.91,
                "text": "Azure OpenAI 配置说明",
                "metadata": {"source_path": "docs/a.pdf", "page": 1},
            },
            {
                "id": "chunk_2",
                "score": 0.73,
                "text": "Embedding 参数解释",
                "metadata": {"source_path": "docs/b.pdf", "page": 3},
            },
        ]
    )
    retriever = DenseRetriever(
        settings=_make_settings(),
        embedding_client=embedding_client,
        vector_store=vector_store,
    )
    trace = TraceContext(trace_type="query")

    results = retriever.retrieve(
        query="如何配置 Azure OpenAI Embedding",
        top_k=2,
        filters={"collection": "manual"},
        trace=trace,
    )

    assert len(embedding_client.calls) == 1
    assert embedding_client.calls[0]["texts"] == ["如何配置 Azure OpenAI Embedding"]

    assert len(vector_store.calls) == 1
    assert vector_store.calls[0]["vector"] == [0.9, 0.1, 0.0]
    assert vector_store.calls[0]["top_k"] == 2
    assert vector_store.calls[0]["filters"] == {"collection": "manual"}

    assert all(isinstance(item, RetrievalResult) for item in results)
    assert results[0].chunk_id == "chunk_1"
    assert results[0].text == "Azure OpenAI 配置说明"
    assert results[0].metadata["source_path"] == "docs/a.pdf"

    assert any(stage["stage_name"] == "dense_retrieval" for stage in trace.stages)


def test_dense_retriever_rejects_invalid_query_or_top_k() -> None:
    """
    Given:
        非法输入（空 query、非字符串 query、非法 top_k）。
    When:
        调用 `retrieve()`。
    Then:
        应抛出 `ValueError`，阻止错误输入进入检索后端。
    """
    retriever = DenseRetriever(
        settings=_make_settings(),
        embedding_client=_FakeEmbeddingClient(),
        vector_store=_FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="query must be non-empty string"):
        retriever.retrieve(query="", top_k=1)
    with pytest.raises(ValueError, match="query must be non-empty string"):
        retriever.retrieve(query=123, top_k=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="top_k must be positive int"):
        retriever.retrieve(query="ok", top_k=0)


def test_dense_retriever_rejects_non_dict_filters() -> None:
    """
    Given:
        `filters` 不是 dict。
    When:
        调用 `retrieve()`。
    Then:
        应抛出 `ValueError`，确保过滤条件契约稳定。
    """
    retriever = DenseRetriever(
        settings=_make_settings(),
        embedding_client=_FakeEmbeddingClient(),
        vector_store=_FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="filters must be dict"):
        retriever.retrieve(query="azure openai", top_k=2, filters=["bad"])  # type: ignore[arg-type]


def test_dense_retriever_rejects_empty_embedding_output() -> None:
    """
    Given:
        embedding 客户端返回空向量列表。
    When:
        调用 `retrieve()`。
    Then:
        应抛出 `ValueError`，避免把空向量传给向量库。
    """
    retriever = DenseRetriever(
        settings=_make_settings(),
        embedding_client=_FakeEmbeddingClient(vectors=[]),
        vector_store=_FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="empty embeddings"):
        retriever.retrieve(query="azure", top_k=1)


def test_dense_retriever_rejects_invalid_result_shape() -> None:
    """
    Given:
        vector store 返回的结果缺失 `id`。
    When:
        执行 `retrieve()` 的结果规范化。
    Then:
        由于 `RetrievalResult.chunk_id` 非空校验，应抛出 `ValueError`。
    """
    retriever = DenseRetriever(
        settings=_make_settings(),
        embedding_client=_FakeEmbeddingClient(),
        vector_store=_FakeVectorStore(results=[{"score": 0.1, "text": "x", "metadata": {"source_path": "a.pdf"}}]),
    )

    with pytest.raises(ValueError, match="chunk_id"):
        retriever.retrieve(query="azure", top_k=1)


def test_dense_retriever_returns_empty_list_when_no_hits() -> None:
    """
    Given:
        vector store 查询无命中结果。
    When:
        调用 `retrieve()`。
    Then:
        应返回空列表，不抛异常。
    """
    retriever = DenseRetriever(
        settings=_make_settings(),
        embedding_client=_FakeEmbeddingClient(),
        vector_store=_FakeVectorStore(results=[]),
    )

    results = retriever.retrieve(query="azure", top_k=3)

    assert results == []
