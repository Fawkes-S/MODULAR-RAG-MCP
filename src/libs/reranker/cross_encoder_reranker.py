"""Cross-Encoder Reranker implementation.

实现目标：
- 支持对 Top-M candidates 进行打分排序；
- 默认提供可运行的占位 scorer（词项重叠分）；
- 当评分阶段异常/超时时抛出回退信号，供上层 fallback 使用。
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable

from libs.reranker.base_reranker import BaseReranker

# scorer 约定：输入 query 与候选列表，返回与 candidates 等长的 float 分数列表。
ScorerFn = Callable[[str, list[dict[str, Any]]], list[float]]


class CrossEncoderFallbackSignal(RuntimeError):
    """Cross-Encoder 重排失败回退信号。"""

    fallback = True

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CrossEncoderReranker(BaseReranker):
    """Cross-Encoder 风格重排器（当前阶段为可运行占位实现）。"""

    provider_name = "cross_encoder"
    # 专门重排模型，对每个 (query, candidate) 打分再排序。稳定、成本低。

    def __init__(
        self,
        top_m: int = 30,
        timeout: float = 10.0,
        scorer: ScorerFn | None = None,
    ) -> None:
        """初始化 CrossEncoderReranker。

        Args:
            top_m: 仅对前 Top-M 候选执行重排，其余候选保持相对顺序接在后面。
            timeout: 评分阶段超时阈值（秒）。
            scorer: 可注入评分函数；测试推荐注入 mock scorer 保证 deterministic。
        """
        if not isinstance(top_m, int) or top_m <= 0:
            raise ValueError("[cross_encoder] ValidationError: top_m must be positive int")
        if float(timeout) <= 0:
            raise ValueError("[cross_encoder] ValidationError: timeout must be positive")

        self.top_m = top_m
        self.timeout = float(timeout)
        self._scorer = scorer or self._default_scorer

    @classmethod
    def from_settings(cls, settings: Any) -> "CrossEncoderReranker":
        """根据配置创建 CrossEncoderReranker。"""
        top_m = cls._extract_top_m(settings)
        timeout = cls._extract_timeout(settings)
        return cls(top_m=top_m, timeout=timeout)

    @staticmethod
    def _extract_top_m(settings: Any) -> int:
        default = 30
        if isinstance(settings, dict):
            rerank_cfg = settings.get("rerank")
            if isinstance(rerank_cfg, dict):
                value = rerank_cfg.get("top_m", default)
                if isinstance(value, int) and value > 0:
                    return value
            return default

        rerank_obj = getattr(settings, "rerank", None)
        value = getattr(rerank_obj, "top_m", default)
        if isinstance(value, int) and value > 0:
            return value
        return default

    @staticmethod
    def _extract_timeout(settings: Any) -> float:
        default = 10.0
        if isinstance(settings, dict):
            rerank_cfg = settings.get("rerank")
            if isinstance(rerank_cfg, dict):
                value = rerank_cfg.get("timeout", default)
                try:
                    value_f = float(value)
                    if value_f > 0:
                        return value_f
                except Exception:
                    return default
            return default

        rerank_obj = getattr(settings, "rerank", None)
        value = getattr(rerank_obj, "timeout", default)
        try:
            value_f = float(value)
            if value_f > 0:
                return value_f
        except Exception:
            return default
        return default

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """对候选进行重排，失败时抛回退信号。"""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("[cross_encoder] ValidationError: query must be non-empty string")
        if not isinstance(candidates, list):
            raise ValueError("[cross_encoder] ValidationError: candidates must be list")
        if len(candidates) == 0:
            return []

        head = list(candidates[: self.top_m])
        tail = list(candidates[self.top_m :])

        start = time.perf_counter()
        try:
            scores = self._scorer(query, head)
        except Exception as exc:
            raise CrossEncoderFallbackSignal(
                f"[cross_encoder] FallbackSignal: scorer failed: {type(exc).__name__}: {exc}"
            ) from exc

        elapsed = time.perf_counter() - start
        if elapsed > self.timeout:
            raise CrossEncoderFallbackSignal(
                f"[cross_encoder] FallbackSignal: scorer timeout ({elapsed:.3f}s > {self.timeout:.3f}s)"
            )

        if not isinstance(scores, list) or len(scores) != len(head):
            raise ValueError("[cross_encoder] ResponseShapeError: scorer must return list[float] with same length")

        scored: list[tuple[int, dict[str, Any], float]] = []
        for idx, (item, score) in enumerate(zip(head, scores)):
            scored.append((idx, item, float(score)))

        # 按分数降序；同分时保持原顺序，确保输出稳定可复现。
        scored.sort(key=lambda x: (-x[2], x[0]))

        ranked_head = []
        for _, item, score in scored:
            ranked = dict(item)
            ranked["rerank_score"] = float(score)
            ranked_head.append(ranked)

        return ranked_head + tail

    @staticmethod
    def _default_scorer(query: str, candidates: list[dict[str, Any]]) -> list[float]:
        """默认占位 scorer：基于 query/text 的词项重叠率。"""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return [0.0 for _ in candidates]

        scores: list[float] = []
        for item in candidates:
            text = str(item.get("text", "")).lower()
            c_tokens = set(re.findall(r"\w+", text))
            overlap = len(q_tokens & c_tokens)
            score = overlap / max(len(q_tokens), 1)
            scores.append(float(score))
        return scores
