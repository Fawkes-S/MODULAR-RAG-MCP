"""Core Reranker 回退编排测试（D6）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

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


class _OrderedBackend:
    """测试桩：返回固定顺序结果，用于验证正常重排路径。"""

    provider_name = "ordered_backend"

    def __init__(self, ordered_ids: list[str]) -> None:
        self.ordered_ids = ordered_ids
        self.calls: list[dict[str, Any]] = []

    def rerank(self, query: str, candidates: list[dict[str, Any]], trace: Any | None = None) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "candidates": list(candidates), "trace": trace})
        by_id = {str(item.get("id", "")): item for item in candidates}
        return [dict(by_id[item_id], rerank_score=1.0 / (idx + 1)) for idx, item_id in enumerate(self.ordered_ids)]


class _FallbackSignalBackend:
    """测试桩：抛出带 `fallback=True` 属性的异常。"""

    provider_name = "signal_backend"

    class _SignalError(RuntimeError):
        fallback = True

    def rerank(self, query: str, candidates: list[dict[str, Any]], trace: Any | None = None) -> list[dict[str, Any]]:
        raise self._SignalError("llm timeout")


class _CrashBackend:
    """测试桩：抛出普通异常，验证 Core 层兜底可用性。"""

    provider_name = "crash_backend"

    def rerank(self, query: str, candidates: list[dict[str, Any]], trace: Any | None = None) -> list[dict[str, Any]]:
        raise RuntimeError("unexpected crash")


def _make_settings() -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=8, sparse_top_k=20),
        rerank=RerankSettings(provider="llm", enabled=True, top_m=30, timeout=10.0),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(),
    )


def _make_candidates() -> list[RetrievalResult]:
    return [
        RetrievalResult(
            chunk_id="c1",
            score=0.91,
            text="chunk-1",
            metadata={"source_path": "a.pdf"},
        ),
        RetrievalResult(
            chunk_id="c2",
            score=0.88,
            text="chunk-2",
            metadata={"source_path": "b.pdf"},
        ),
        RetrievalResult(
            chunk_id="c3",
            score=0.85,
            text="chunk-3",
            metadata={"source_path": "c.pdf"},
        ),
    ]


def test_reranker_uses_backend_order_and_marks_non_fallback() -> None:
    """
    Given:
        一个返回固定顺序与 rerank_score 的后端测试桩。
    When:
        调用 `Reranker.rerank()` 对融合候选执行精排。
    Then:
        应按后端顺序返回结果，`fallback=False`，且写入 trace.rerank 阶段。
    """
    backend = _OrderedBackend(ordered_ids=["c2", "c1"])
    reranker = Reranker(settings=_make_settings(), backend=backend)  # type: ignore[arg-type]
    trace = TraceContext(trace_type="query")

    output = reranker.rerank(
        query="Azure OpenAI",
        candidates=_make_candidates(),
        top_k=2,
        trace=trace,
    )

    assert output.fallback is False
    assert output.fallback_reason is None
    assert [item.chunk_id for item in output.results] == ["c2", "c1"]
    assert output.results[0].metadata["rerank_score"] == pytest.approx(1.0)
    assert any(stage["stage_name"] == "rerank" for stage in trace.stages)


def test_reranker_fallback_on_signal_exception_keeps_original_order() -> None:
    """
    Given:
        后端抛出带 `fallback=True` 标记的异常（模拟超时/请求失败）。
    When:
        调用 `Reranker.rerank()`。
    Then:
        不应抛出异常，而应回退到 fusion 原顺序，并标记 `fallback=True`。
    """
    reranker = Reranker(settings=_make_settings(), backend=_FallbackSignalBackend())  # type: ignore[arg-type]

    output = reranker.rerank(query="Azure", candidates=_make_candidates())

    assert output.fallback is True
    assert "llm timeout" in str(output.fallback_reason)
    assert [item.chunk_id for item in output.results] == ["c1", "c2", "c3"]
    assert all(item.metadata.get("rerank_fallback") is True for item in output.results)


def test_reranker_fallback_on_unexpected_exception_still_returns_candidates() -> None:
    """
    Given:
        后端抛出普通 RuntimeError（非显式 fallback 信号）。
    When:
        调用 `Reranker.rerank()`。
    Then:
        Core 层应继续返回候选结果，避免上层查询链路中断。
    """
    reranker = Reranker(settings=_make_settings(), backend=_CrashBackend())  # type: ignore[arg-type]

    output = reranker.rerank(query="Azure", candidates=_make_candidates(), top_k=2)

    assert output.fallback is True
    assert "unexpected crash" in str(output.fallback_reason)
    assert [item.chunk_id for item in output.results] == ["c1", "c2"]


def test_reranker_validates_query_candidates_and_top_k() -> None:
    """
    Given:
        非法 query/candidates/top_k 输入。
    When:
        调用 `Reranker.rerank()`。
    Then:
        应抛出 `ValueError`，阻止非法输入进入后端。
    """
    reranker = Reranker(settings=_make_settings(), backend=_OrderedBackend(["c1"]))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="query must be non-empty string"):
        reranker.rerank(query="", candidates=_make_candidates())
    with pytest.raises(ValueError, match="candidates must be list"):
        reranker.rerank(query="ok", candidates="bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="top_k must be positive int"):
        reranker.rerank(query="ok", candidates=_make_candidates(), top_k=0)
