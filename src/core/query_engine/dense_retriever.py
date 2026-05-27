"""DenseRetriever：语义向量检索编排（D2）。"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import RetrievalResult
from libs.embedding.embedding_factory import EmbeddingFactory
from libs.vector_store.vector_store_factory import VectorStoreFactory


class DenseRetriever:
    """基于 Embedding + VectorStore 的稠密检索器。

    做什么：
    - 将用户 query 编码为 embedding 向量；
    - 调用向量存储执行相似度检索；
    - 把底层结果规范化为统一 `RetrievalResult` 契约。

    为什么：
    - D2 需要先打通 Dense 路径，为 D5 的 HybridSearch 提供可复用召回能力。
    - 统一返回类型能降低后续 Fusion/Rerank/Response 的适配复杂度。

    关键权衡：
    - 保持“编排层薄逻辑”，只做输入校验与结果规范化，不在这里耦合特定向量库细节。
    - 对 `embedding_client` 与 `vector_store` 支持依赖注入，便于单测隔离外部依赖。

    失败路径：
    - query、top_k、filters shape 非法时抛出 `ValueError`；
    - embedding 返回空向量时抛出 `ValueError`，阻止无意义检索；
    - 向量库结果缺关键字段（id/metadata）时抛出 `ValueError`，防止脏数据下传。
    """

    def __init__(
        self,
        settings: Settings,
        embedding_client: Any | None = None,
        vector_store: Any | None = None,
    ) -> None:
        """初始化 DenseRetriever。

        Args:
            settings: 全局配置对象。
            embedding_client: 可选注入 embedding 客户端；默认由工厂创建。
            vector_store: 可选注入向量存储；默认由工厂创建。
        """
        if not isinstance(settings, Settings):
            raise TypeError("DenseRetriever requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.embedding_client = embedding_client or EmbeddingFactory.create(settings)
        self.vector_store = vector_store or VectorStoreFactory.create(settings)

    def retrieve(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        """执行一次 Dense 检索。

        Args:
            query: 查询文本。
            top_k: 返回候选上限。
            filters: 元数据过滤条件。
            trace: 可选追踪上下文。

        Returns:
            list[RetrievalResult]: 规范化检索结果列表。
        """
        normalized_query = self._normalize_query(query)
        normalized_top_k = self._normalize_top_k(top_k)
        normalized_filters = self._normalize_filters(filters)
        started = perf_counter()

        query_vector = self._encode_query(normalized_query, trace=trace)
        raw_results = self.vector_store.query(
            vector=query_vector,
            top_k=normalized_top_k,
            filters=normalized_filters,
            trace=trace,
        )

        normalized_results = [
            self._normalize_result_item(item, index)
            for index, item in enumerate(raw_results)
        ]

        if trace is not None:
            trace.record_stage(
                stage_name="dense_retrieval",
                details={
                    "query": normalized_query,
                    "top_k": normalized_top_k,
                    "result_count": len(normalized_results),
                    "embedding_provider": self.settings.embedding.provider,
                    "vector_store_provider": self.settings.vector_store.provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return normalized_results

    @staticmethod
    def _normalize_query(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("query must be non-empty string")
        normalized = " ".join(query.strip().split())
        if not normalized:
            raise ValueError("query must be non-empty string")
        return normalized

    @staticmethod
    def _normalize_top_k(top_k: int) -> int:
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be positive int")
        return top_k

    @staticmethod
    def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any] | None:
        if filters is None:
            return None
        if not isinstance(filters, dict):
            raise ValueError("filters must be dict when provided")
        return dict(filters)

    def _encode_query(self, query: str, trace: TraceContext | None = None) -> list[float]:
        """把 query 编码为单条向量。"""
        embeddings = self.embedding_client.embed([query], trace=trace)
        if not isinstance(embeddings, list) or not embeddings:
            raise ValueError("embedding_client returned empty embeddings")

        vector = embeddings[0]
        if not isinstance(vector, list) or not vector:
            raise ValueError("embedding_client returned invalid query vector")
        return [float(value) for value in vector]

    @staticmethod
    def _normalize_result_item(item: dict[str, Any], index: int) -> RetrievalResult:
        """把向量存储原始项转换为 RetrievalResult。"""
        if not isinstance(item, dict):
            raise ValueError(f"vector_store.query() result[{index}] must be dict")

        raw_chunk_id = item.get("id", item.get("chunk_id", ""))
        raw_metadata = item.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raise ValueError(f"vector_store.query() result[{index}].metadata must be dict")

        # text 是 D2 的关键契约字段；缺失时回退为空字符串，保证返回 shape 稳定。
        raw_text = item.get("text", "")

        return RetrievalResult(
            chunk_id=str(raw_chunk_id),
            score=float(item.get("score", 0.0)),
            text=str(raw_text),
            metadata=dict(raw_metadata),
        )
