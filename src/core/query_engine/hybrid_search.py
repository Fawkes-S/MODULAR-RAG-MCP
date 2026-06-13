"""HybridSearch：Dense + Sparse + Fusion 检索编排（D5）。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

from core.query_engine.dense_retriever import DenseRetriever
from core.query_engine.fusion import RRFFusion
from core.query_engine.query_processor import QueryProcessor
from core.query_engine.sparse_retriever import SparseRetriever
from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import RetrievalResult


def _build_results_preview(results: list[RetrievalResult], limit: int = 5) -> list[dict[str, Any]]:
    """构建融合结果的轻量预览。

    Query 追踪页需要展示“融合前后的排名变化”，
    因此这里把前几个候选的顺序、分数和来源路径一起记进 trace。
    """
    preview: list[dict[str, Any]] = []
    for index, item in enumerate(results[:limit], start=1):
        preview.append(
            {
                "rank": index,
                "chunk_id": item.chunk_id,
                "score": float(item.score),
                "source_path": str(item.metadata.get("source_path", "-")),
                "collection": str(item.metadata.get("collection", "-")),
                "text": str(item.text),
            }
        )
    return preview


class HybridSearch:
    """混合检索编排器。

    做什么：
    - 统一执行 QueryProcessor -> Dense/Sparse 并行召回 -> RRF 融合 -> 后置过滤；
    - 在 Dense/Sparse 任一路失败时自动降级到单路可用结果；
    - 输出稳定的 `RetrievalResult` 列表供后续 Reranker/Response 复用。

    为什么：
    - D5 的核心目标是把 D1-D4 串成完整在线查询主链路，形成可直接被 CLI/MCP 调用的能力。
    - 通过降级策略把“单路暂时失败”从致命错误降为可用性抖动，保证查询入口韧性。

    关键权衡：
    - 并行执行 Dense/Sparse 以降低总延迟，但仍在编排层串行做融合与过滤，便于控制输出契约。
    - 后置过滤默认对 metadata 缺失字段采取“放行”策略，避免因为索引字段不完整造成误杀召回。

    失败路径：
    - 输入参数 shape 非法时抛 `ValueError`；
    - 双路都失败时抛 `RuntimeError`（包含路由错误摘要）；
    - 若调用方传入 trace，会记录 `hybrid_search` 阶段与降级信息。
    """

    def __init__(
        self,
        settings: Settings,
        query_processor: QueryProcessor | None = None,
        dense_retriever: DenseRetriever | None = None,
        sparse_retriever: SparseRetriever | None = None,
        fusion: RRFFusion | None = None,
    ) -> None:
        """初始化 HybridSearch。

        Args:
            settings: 全局配置对象。
            query_processor: 可选注入查询预处理器。
            dense_retriever: 可选注入稠密检索器。
            sparse_retriever: 可选注入稀疏检索器。
            fusion: 可选注入融合器。
        """
        if not isinstance(settings, Settings):
            raise TypeError("HybridSearch requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.query_processor = query_processor or QueryProcessor(settings=settings)
        self.dense_retriever = dense_retriever or DenseRetriever(settings=settings)
        self.sparse_retriever = sparse_retriever or SparseRetriever(settings=settings)
        self.fusion = fusion or RRFFusion()

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        """执行完整混合检索流程并返回 Top-K。

        做什么：
        - 调用 QueryProcessor 生成 `normalized_query/keywords/merged_filters`；
        - 并行执行 dense.retrieve 与 sparse.retrieve；
        - 使用 RRF 对双路候选融合，再做后置 metadata 过滤；
        - 失败时按“单路降级优先、双路失败抛错”策略处理。

        为什么：
        - 将检索策略收敛到单入口，可显著降低上层调用方（CLI/MCP）编排复杂度。

        关键权衡：
        - Dense/Sparse 的候选深度使用“max(请求 top_k, 配置阈值)”策略，
          以提高融合后命中率，代价是单次查询候选规模略增。

        失败路径：
        - `query/top_k/filters` 非法会抛 `ValueError`；
        - 两路都失败抛 `RuntimeError`，并把路由错误摘要回传给调用方。

        Args:
            query: 用户查询文本。
            top_k: 最终返回数量上限。
            filters: 可选 metadata 过滤条件。
            trace: 可选追踪上下文。

        Returns:
            list[RetrievalResult]: 融合并过滤后的结果。
        """
        normalized_top_k = self._normalize_top_k(top_k)
        query_processing_started = perf_counter()
        processed = self.query_processor.process(query=query, filters=filters)
        if trace is not None:
            trace.record_stage(
                stage_name="query_processing",
                details={
                    "method": "rule_based_query_processor",
                    "provider": type(self.query_processor).__name__,
                    "original_query": query,
                    "normalized_query": processed.normalized_query,
                    "keywords": processed.keywords,
                    "filters": processed.filters,
                },
                elapsed_ms=(perf_counter() - query_processing_started) * 1000.0,
            )

        dense_candidate_k = max(normalized_top_k, int(self.settings.retrieval.top_k))
        sparse_candidate_k = max(normalized_top_k, int(self.settings.retrieval.sparse_top_k))
        fusion_candidate_k = max(dense_candidate_k, sparse_candidate_k)
        started = perf_counter()

        dense_results, sparse_results, route_errors = self._retrieve_candidates_parallel(
            normalized_query=processed.normalized_query,
            keywords=processed.keywords,
            merged_filters=processed.filters,
            dense_top_k=dense_candidate_k,
            sparse_top_k=sparse_candidate_k,
            trace=trace,
        )

        if not dense_results and not sparse_results:
            error_summary = "; ".join(f"{route}={message}" for route, message in route_errors.items())
            raise RuntimeError(f"hybrid search failed: both dense and sparse routes failed ({error_summary})")

        fusion_started = perf_counter()
        fused_results = self.fusion.fuse(
            dense_results=dense_results,
            sparse_results=sparse_results,
            top_k=fusion_candidate_k,
        )
        fusion_elapsed_ms = (perf_counter() - fusion_started) * 1000.0
        if trace is not None:
            trace.record_stage(
                stage_name="fusion",
                details={
                    "method": "rrf",
                    "provider": type(self.fusion).__name__,
                    "top_k": fusion_candidate_k,
                    "dense_count": len(dense_results),
                    "sparse_count": len(sparse_results),
                    "fused_count": len(fused_results),
                    "degraded_routes": sorted(route_errors.keys()),
                    "results_preview": _build_results_preview(fused_results),
                },
                elapsed_ms=fusion_elapsed_ms,
            )
        filtered_results = self._apply_metadata_filters(
            candidates=fused_results,
            filters=processed.filters,
        )
        final_results = filtered_results[:normalized_top_k]

        if trace is not None:
            trace.record_stage(
                stage_name="hybrid_search",
                details={
                    "method": "query_processor_parallel_retrieval_rrf",
                    "provider": type(self.fusion).__name__,
                    "query": processed.normalized_query,
                    "keywords": processed.keywords,
                    "top_k": normalized_top_k,
                    "dense_candidate_k": dense_candidate_k,
                    "sparse_candidate_k": sparse_candidate_k,
                    "dense_count": len(dense_results),
                    "sparse_count": len(sparse_results),
                    "fused_count": len(fused_results),
                    "filtered_count": len(final_results),
                    "degraded_routes": sorted(route_errors.keys()),
                    "results_preview": _build_results_preview(final_results),
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return final_results

    def _retrieve_candidates_parallel(
        self,
        normalized_query: str,
        keywords: list[str],
        merged_filters: dict[str, Any],
        dense_top_k: int,
        sparse_top_k: int,
        trace: TraceContext | None = None,
    ) -> tuple[list[RetrievalResult], list[RetrievalResult], dict[str, str]]:
        """并行执行 Dense/Sparse 检索并收集路由异常。

        返回值中的 `route_errors` 用于触发单路降级或双路失败判定。
        """

        def _run_dense() -> list[RetrievalResult]:
            return self.dense_retriever.retrieve(
                query=normalized_query,
                top_k=dense_top_k,
                filters=merged_filters,
                trace=trace,
            )

        def _run_sparse() -> list[RetrievalResult]:
            return self.sparse_retriever.retrieve(
                keywords=keywords,
                top_k=sparse_top_k,
                trace=trace,
            )

        dense_results: list[RetrievalResult] = []
        sparse_results: list[RetrievalResult] = []
        route_errors: dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="hybrid-search") as pool:
            futures = {
                "dense": pool.submit(_run_dense),
                "sparse": pool.submit(_run_sparse),
            }

            for route, future in futures.items():
                try:
                    route_results = future.result()
                    if route == "dense":
                        dense_results = route_results
                    else:
                        sparse_results = route_results
                except Exception as exc:  # pragma: no cover - 由集成测试覆盖行为分支
                    # 记录可读错误摘要，供上层决定“单路降级”或“双路失败抛错”。
                    route_errors[route] = f"{type(exc).__name__}: {exc}"

        return dense_results, sparse_results, route_errors

    @staticmethod
    def _normalize_top_k(top_k: int) -> int:
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be positive int")
        return top_k

    @staticmethod
    def _apply_metadata_filters(
        candidates: list[RetrievalResult],
        filters: dict[str, Any] | None,
    ) -> list[RetrievalResult]:
        """对融合候选执行后置 metadata 过滤兜底。

        过滤规则：
        - `filters is None` 或空 dict：直接放行；
        - filter 值为 `None`：跳过该条件；
        - metadata 缺失对应字段：默认放行（missing -> include）；
        - 支持标量等值匹配与集合型（list/tuple/set）包含匹配。
        """
        if not isinstance(candidates, list):
            raise ValueError("candidates must be list[RetrievalResult]")
        if filters is None:
            return list(candidates)
        if not isinstance(filters, dict):
            raise ValueError("filters must be dict when provided")
        if not filters:
            return list(candidates)

        filtered: list[RetrievalResult] = []
        for idx, item in enumerate(candidates):
            if not isinstance(item, RetrievalResult):
                raise ValueError(f"candidates[{idx}] must be RetrievalResult")

            keep = True
            for key, expected in filters.items():
                if expected is None:
                    continue

                actual = item.metadata.get(str(key))
                if actual is None:
                    # 兜底策略：字段缺失时放行，避免索引字段不齐全导致误杀召回。
                    continue

                if isinstance(expected, (list, tuple, set)):
                    normalized_expected = {str(value).strip().lower() for value in expected}
                    if str(actual).strip().lower() not in normalized_expected:
                        keep = False
                        break
                else:
                    if str(actual).strip().lower() != str(expected).strip().lower():
                        keep = False
                        break

            if keep:
                filtered.append(item)
        return filtered
