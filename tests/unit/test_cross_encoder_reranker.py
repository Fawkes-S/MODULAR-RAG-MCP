"""CrossEncoderReranker 单元测试。"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.reranker.cross_encoder_reranker import CrossEncoderFallbackSignal, CrossEncoderReranker
from libs.reranker.reranker_factory import RerankerFactory


def test_cross_encoder_reranker_sorts_top_m_with_mock_scorer() -> None:
    """
    Given:
        一个 CrossEncoderReranker，配置 `top_m=2`，并注入 deterministic mock scorer，
        使得候选 c2 的分数高于 c1，c3 位于 top_m 之外。 

    When:
        调用 rerank 对 3 条候选执行重排。

    Then:
        - 仅前 2 条候选参与打分重排；
        - 前两条顺序按分数降序变为 c2 -> c1；
        - 超出 top_m 的 c3 保持在尾部；
        - 被重排的候选包含 `rerank_score` 字段。
    """

    def _mock_scorer(query: str, candidates: list[dict[str, Any]]) -> list[float]:
        assert query == "test query"
        assert [x["id"] for x in candidates] == ["c1", "c2"]
        return [0.1, 0.9]

    reranker = CrossEncoderReranker(top_m=2, scorer=_mock_scorer, timeout=1.0)
    result = reranker.rerank(
        query="test query",
        candidates=[
            {"id": "c1", "text": "alpha"},
            {"id": "c2", "text": "beta"},
            {"id": "c3", "text": "gamma"},
        ],
    )

    assert [x["id"] for x in result] == ["c2", "c1", "c3"]
    assert "rerank_score" in result[0]
    assert "rerank_score" in result[1]
    assert "rerank_score" not in result[2]


def test_cross_encoder_reranker_scorer_failure_raises_fallback_signal() -> None:
    """
    Given:
        一个会抛异常的 mock scorer（模拟模型推理失败/后端错误）。

    When:
        调用 rerank。

    Then:
        抛出 `CrossEncoderFallbackSignal`，并在信息中包含 `FallbackSignal` 标识，
        供上层 Core 在 D6 阶段识别并回退到 fusion 排序。
    """

    def _broken_scorer(query: str, candidates: list[dict[str, Any]]) -> list[float]:
        raise RuntimeError("model crash")

    reranker = CrossEncoderReranker(top_m=3, scorer=_broken_scorer, timeout=1.0)

    with pytest.raises(CrossEncoderFallbackSignal, match="FallbackSignal"):
        reranker.rerank(query="q", candidates=[{"id": "c1", "text": "t"}])


def test_cross_encoder_reranker_timeout_raises_fallback_signal() -> None:
    """
    Given:
        一个故意 sleep 的 mock scorer，耗时超过 timeout 阈值。

    When:
        调用 rerank。

    Then:
        抛出 `CrossEncoderFallbackSignal`，并明确标记为 timeout，
        保障上层可按统一回退分支处理。
    """

    def _slow_scorer(query: str, candidates: list[dict[str, Any]]) -> list[float]:
        time.sleep(0.03)
        return [0.5 for _ in candidates]

    reranker = CrossEncoderReranker(top_m=2, scorer=_slow_scorer, timeout=0.001)

    with pytest.raises(CrossEncoderFallbackSignal, match="timeout"):
        reranker.rerank(query="q", candidates=[{"id": "c1", "text": "t"}])


def test_reranker_factory_can_create_cross_encoder_backend() -> None:
    """
    Given:
        工厂配置 `rerank.provider=cross_encoder` 且指定 `top_m`。

    When:
        调用 `RerankerFactory.create(settings)`。

    Then:
        返回 `CrossEncoderReranker` 实例，且配置参数正确注入实例。
    """
    settings = {
        "rerank": {
            "provider": "cross_encoder",
            "top_m": 12,
            "timeout": 3.5,
        }
    }

    reranker = RerankerFactory.create(settings)

    assert isinstance(reranker, CrossEncoderReranker)
    assert reranker.top_m == 12
    assert reranker.timeout == 3.5
