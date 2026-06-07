"""SparseRetriever：BM25 稀疏检索编排（D3）。"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import RetrievalResult
from ingestion.storage.bm25_indexer import BM25Indexer
from libs.vector_store.vector_store_factory import VectorStoreFactory


class SparseRetriever:
    """基于 BM25 + VectorStore 的稀疏检索器。

    做什么：
    - 接收 `keywords` 并调用 BM25 索引获取 `(chunk_id, score)` 候选；
    - 通过 `vector_store.get_by_ids()` 回填每个候选的 `text/metadata`；
    - 产出统一 `RetrievalResult` 结果。

    为什么：
    - D3 需要把“关键词召回”与“正文回填”打通，形成可被 D5 直接编排的稀疏检索路径。

    关键权衡：
    - BM25 只负责分数和 ID，正文来源统一走 VectorStore，避免重复维护存储源。
    - 缺失正文记录的候选会被跳过，优先保证返回结果完整性。

    失败路径：
    - `keywords/top_k` 非法输入抛 `ValueError`；
    - `get_by_ids` 返回脏数据（缺 id/metadata）抛 `ValueError`，防止坏数据传播。
    """

    def __init__(
        self,
        settings: Settings,
        bm25_indexer: BM25Indexer | None = None,
        vector_store: Any | None = None,
    ) -> None:
        """初始化 SparseRetriever。"""
        if not isinstance(settings, Settings):
            raise TypeError("SparseRetriever requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.bm25_indexer = bm25_indexer or BM25Indexer()
        self.vector_store = vector_store or VectorStoreFactory.create(settings)

    def retrieve(
        self,
        keywords: list[str],
        top_k: int,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        """执行一次稀疏检索。"""
        normalized_keywords = self._normalize_keywords(keywords)
        normalized_top_k = self._normalize_top_k(top_k)
        started = perf_counter()

        if not normalized_keywords:
            return []

        bm25_hits = self.bm25_indexer.query(normalized_keywords, top_k=normalized_top_k)
        if not bm25_hits:
            return []

        chunk_ids = [chunk_id for chunk_id, _score in bm25_hits]
        score_by_id = {chunk_id: float(score) for chunk_id, score in bm25_hits}

        raw_documents = self.vector_store.get_by_ids(chunk_ids, trace=trace)
        docs_by_id = self._index_documents_by_id(raw_documents)

        results: list[RetrievalResult] = []
        for chunk_id in chunk_ids:
            doc = docs_by_id.get(chunk_id)
            if doc is None:
                continue
            results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    score=score_by_id.get(chunk_id, 0.0),
                    text=str(doc.get("text", "")),
                    metadata=dict(doc.get("metadata", {})),
                )
            )

        if trace is not None:
            trace.record_stage(
                stage_name="sparse_retrieval",
                details={
                    "method": "bm25_get_by_ids",
                    "provider": "bm25",
                    "keywords": normalized_keywords,
                    "top_k": normalized_top_k,
                    "bm25_hits": len(bm25_hits),
                    "result_count": len(results),
                    "backend": "bm25",
                    "vector_store_provider": self.settings.vector_store.provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return results

    @staticmethod
    def _normalize_keywords(keywords: list[str]) -> list[str]:
        if not isinstance(keywords, list):
            raise ValueError("keywords must be list[str]")

        normalized: list[str] = []
        seen: set[str] = set()
        for idx, token in enumerate(keywords):
            if not isinstance(token, str):
                raise ValueError(f"keywords[{idx}] must be string")
            value = token.strip().lower()
            if not value or value in seen:
                continue
            normalized.append(value)
            seen.add(value)
        return normalized

    @staticmethod
    def _normalize_top_k(top_k: int) -> int:
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be positive int")
        return top_k

    @staticmethod
    def _index_documents_by_id(raw_documents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if not isinstance(raw_documents, list):
            raise ValueError("vector_store.get_by_ids() must return list[dict]")

        indexed: dict[str, dict[str, Any]] = {}
        for idx, item in enumerate(raw_documents):
            if not isinstance(item, dict):
                raise ValueError(f"vector_store.get_by_ids() result[{idx}] must be dict")
            chunk_id = str(item.get("id", "")).strip()
            if not chunk_id:
                raise ValueError(f"vector_store.get_by_ids() result[{idx}] missing id")
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError(f"vector_store.get_by_ids() result[{idx}].metadata must be dict")
            indexed[chunk_id] = item
        return indexed
