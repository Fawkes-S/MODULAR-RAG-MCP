"""RRF Fusion 单元测试（D4）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.fusion import RRFFusion  # noqa: E402
from core.types import RetrievalResult  # noqa: E402


def _make_result(chunk_id: str, score: float = 0.0) -> RetrievalResult:
    """构造最小可用 RetrievalResult，减少测试样板代码。"""
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        text=f"text-{chunk_id}",
        metadata={"source_path": f"{chunk_id}.pdf"},
    )


def test_rrf_fusion_returns_deterministic_order_for_fixed_inputs() -> None:
    """
    Given:
        固定的 dense/sparse 排名输入，且两路存在部分重叠候选。
    When:
        执行 `RRFFusion.fuse()`。
    Then:
        输出顺序应 deterministic，并按 RRF 融合分数排序。
    """
    fusion = RRFFusion(default_k=60)
    dense_results = [_make_result("c1"), _make_result("c2"), _make_result("c3")]
    sparse_results = [_make_result("c2"), _make_result("c3"), _make_result("c4")]

    results = fusion.fuse(dense_results=dense_results, sparse_results=sparse_results, top_k=4)

    assert [item.chunk_id for item in results] == ["c2", "c3", "c1", "c4"]
    assert results[0].score > results[1].score > results[2].score > results[3].score


def test_rrf_fusion_supports_configurable_k_parameter() -> None:
    """
    Given:
        同一批 dense/sparse 候选输入。
    When:
        分别使用不同的 `k` 参数执行融合。
    Then:
        输出分数会随 `k` 变化，证明 RRF 平滑参数可配置。
    """
    fusion = RRFFusion(default_k=60)
    dense_results = [_make_result("c1"), _make_result("c2")]
    sparse_results = [_make_result("c2")]

    result_with_small_k = fusion.fuse(dense_results, sparse_results, top_k=2, k=1)
    result_with_large_k = fusion.fuse(dense_results, sparse_results, top_k=2, k=100)

    score_small_k = {item.chunk_id: item.score for item in result_with_small_k}
    score_large_k = {item.chunk_id: item.score for item in result_with_large_k}
    assert score_small_k["c2"] > score_large_k["c2"]
    assert score_small_k["c1"] > score_large_k["c1"]


def test_rrf_fusion_limits_by_top_k_and_handles_empty_routes() -> None:
    """
    Given:
        单路召回与双路均为空两种边界场景。
    When:
        调用 `fuse()` 并限制 `top_k`。
    Then:
        应正确截断结果；空输入应稳定返回空列表。
    """
    fusion = RRFFusion()

    limited = fusion.fuse(
        dense_results=[_make_result("c1"), _make_result("c2"), _make_result("c3")],
        sparse_results=[],
        top_k=2,
    )
    empty = fusion.fuse(dense_results=[], sparse_results=[], top_k=3)

    assert [item.chunk_id for item in limited] == ["c1", "c2"]
    assert empty == []


def test_rrf_fusion_validates_input_shapes() -> None:
    """
    Given:
        非法输入 shape（top_k、k、路由结果类型）场景。
    When:
        调用 `fuse()`。
    Then:
        应抛出 `ValueError`，阻止坏输入进入融合逻辑。
    """
    fusion = RRFFusion()

    with pytest.raises(ValueError, match="top_k must be positive int"):
        fusion.fuse(dense_results=[], sparse_results=[], top_k=0)
    with pytest.raises(ValueError, match="k must be non-negative int"):
        fusion.fuse(dense_results=[], sparse_results=[], top_k=1, k=-1)
    with pytest.raises(ValueError, match=r"dense_results\[0\] must be RetrievalResult"):
        fusion.fuse(dense_results=[{"chunk_id": "c1"}], sparse_results=[], top_k=1)  # type: ignore[list-item]
