"""Core Reranker：重排编排与回退策略（D6）。"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import RetrievalResult
from libs.reranker.base_reranker import BaseReranker
from libs.reranker.reranker_factory import RerankerFactory


@dataclass(frozen=True)
class RerankOutput:
    """重排输出契约。

    Attributes:
        results: 重排后的候选列表。
        fallback: 是否触发回退（True 表示本次使用了 fusion 原顺序）。
        fallback_reason: 回退原因；未回退时为 `None`。
        backend: 本次调用的后端标识（如 none/llm/cross_encoder）。
    """

    results: list[RetrievalResult]
    fallback: bool
    fallback_reason: str | None
    backend: str


class Reranker:
    """Core 层重排编排器。

    做什么：
    - 将 `RetrievalResult` 候选转换为 libs.reranker 后端输入格式；
    - 调用配置化后端执行精排；
    - 当后端失败/超时时回退到 fusion 原顺序，并显式标记 `fallback=true`。

    为什么：
    - D6 需要把“可插拔后端能力”与“系统可用性保护”统一在 Core 层，
      让上层入口（D7 CLI / E3 MCP Tool）无需重复写异常分支。

    关键权衡：
    - 任何后端异常都走可用性优先的回退分支，而不是向上抛出中断查询；
      代价是会牺牲本次精排质量，但保证主链路可持续响应。

    失败路径：
    - 输入 shape 非法（query/candidates/top_k）抛 `ValueError`；
    - 后端失败不会抛错，而是返回 `fallback=true` 与原顺序结果。
    """

    def __init__(
        self,
        settings: Settings,
        backend: BaseReranker | None = None,
    ) -> None:
        """初始化 Core Reranker。

        Args:
            settings: 全局配置对象。
            backend: 可选注入后端（测试推荐）；为空时由 `RerankerFactory` 创建。
        """
        if not isinstance(settings, Settings):
            raise TypeError("Reranker requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.backend = backend or RerankerFactory.create(settings)
        self.backend_name = str(getattr(self.backend, "provider_name", settings.rerank.provider or "unknown"))

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int | None = None,
        trace: TraceContext | None = None,
    ) -> RerankOutput:
        """执行重排；后端失败时自动回退 fusion 顺序。

        Args:
            query: 用户查询文本。
            candidates: 来自 HybridSearch 的融合候选。
            top_k: 可选返回上限；为空时返回全部候选。
            trace: 可选追踪上下文。

        Returns:
            RerankOutput: 包含结果、fallback 标记、回退原因与后端名。
        """
        normalized_query = self._normalize_query(query)
        normalized_candidates = self._normalize_candidates(candidates)
        normalized_top_k = self._normalize_top_k(top_k)
        started = perf_counter()

        if not normalized_candidates:
            output = RerankOutput(results=[], fallback=False, fallback_reason=None, backend=self.backend_name)
            self._record_trace(
                trace=trace,
                started=started,
                output=output,
                input_count=0,
                output_count=0,
            )
            return output

        backend_candidates = [self._to_backend_candidate(item) for item in normalized_candidates]
        fallback_reason: str | None = None
        fallback = False

        try:
            ranked_backend_candidates = self.backend.rerank(
                query=normalized_query,
                candidates=backend_candidates,
                trace=trace,
            )
            final_results = self._from_backend_candidates(
                original=normalized_candidates,
                ranked=ranked_backend_candidates,
                top_k=normalized_top_k,
            )
        except Exception as exc:
            # 可用性优先：后端任意异常都不阻断查询，统一回退至 fusion 原顺序。
            fallback = True
            fallback_reason = f"{type(exc).__name__}: {exc}"
            final_results = self._fallback_results(
                candidates=normalized_candidates,
                top_k=normalized_top_k,
                reason=fallback_reason,
            )

        output = RerankOutput(
            results=final_results,
            fallback=fallback,
            fallback_reason=fallback_reason,
            backend=self.backend_name,
        )
        self._record_trace(
            trace=trace,
            started=started,
            output=output,
            input_count=len(normalized_candidates),
            output_count=len(final_results),
        )
        return output

    @staticmethod
    def _normalize_query(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("query must be non-empty string")
        normalized = " ".join(query.strip().split())
        if not normalized:
            raise ValueError("query must be non-empty string")
        return normalized

    @staticmethod
    def _normalize_candidates(candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        if not isinstance(candidates, list):
            raise ValueError("candidates must be list[RetrievalResult]")
        normalized: list[RetrievalResult] = []
        for idx, item in enumerate(candidates):
            if not isinstance(item, RetrievalResult):
                raise ValueError(f"candidates[{idx}] must be RetrievalResult")
            normalized.append(item)
        return normalized

    @staticmethod
    def _normalize_top_k(top_k: int | None) -> int | None:
        if top_k is None:
            return None
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be positive int when provided")
        return top_k

    @staticmethod
    def _to_backend_candidate(item: RetrievalResult) -> dict[str, Any]:
        return {
            "id": item.chunk_id,
            "text": item.text,
            "score": item.score,
            "metadata": dict(item.metadata),
        }

    def _from_backend_candidates(
        self,
        original: list[RetrievalResult],
        ranked: Any,
        top_k: int | None,
    ) -> list[RetrievalResult]:
        """把后端排序结果映射回 `RetrievalResult` 列表。"""
        if not isinstance(ranked, list):
            raise ValueError("reranker backend must return list[dict]")

        by_id = {item.chunk_id: item for item in original}
        used_ids: set[str] = set()
        results: list[RetrievalResult] = []

        for idx, raw in enumerate(ranked):
            if not isinstance(raw, dict):
                raise ValueError(f"reranker backend result[{idx}] must be dict")
            chunk_id = str(raw.get("id", "")).strip()
            if not chunk_id or chunk_id in used_ids:
                continue

            base = by_id.get(chunk_id)
            if base is None:
                continue

            merged_metadata = dict(base.metadata)
            raw_metadata = raw.get("metadata")
            if isinstance(raw_metadata, dict):
                merged_metadata.update(raw_metadata)

            if "rerank_score" in raw:
                merged_metadata["rerank_score"] = float(raw["rerank_score"])

            results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    score=float(raw.get("rerank_score", raw.get("score", base.score))),
                    text=str(raw.get("text", base.text)),
                    metadata=merged_metadata,
                )
            )
            used_ids.add(chunk_id)

        for item in original:
            if item.chunk_id in used_ids:
                continue
            results.append(item)

        if top_k is not None:
            return results[:top_k]
        return results

    @staticmethod
    def _fallback_results(
        candidates: list[RetrievalResult],
        top_k: int | None,
        reason: str,
    ) -> list[RetrievalResult]:
        """回退到 fusion 原顺序，同时在 metadata 标记 fallback 信息。"""
        fallback_candidates = candidates if top_k is None else candidates[:top_k]
        results: list[RetrievalResult] = []
        for item in fallback_candidates:
            metadata = dict(item.metadata)
            metadata["rerank_fallback"] = True
            metadata["rerank_fallback_reason"] = reason
            results.append(
                RetrievalResult(
                    chunk_id=item.chunk_id,
                    score=item.score,
                    text=item.text,
                    metadata=metadata,
                )
            )
        return results

    def _record_trace(
        self,
        trace: TraceContext | None,
        started: float,
        output: RerankOutput,
        input_count: int,
        output_count: int,
    ) -> None:
        """记录重排阶段追踪信息。"""
        if trace is None:
            return
        trace.record_stage(
            stage_name="rerank",
            details={
                "backend": output.backend,
                "input_count": input_count,
                "output_count": output_count,
                "fallback": output.fallback,
                "fallback_reason": output.fallback_reason,
            },
            elapsed_ms=(perf_counter() - started) * 1000.0,
        )
