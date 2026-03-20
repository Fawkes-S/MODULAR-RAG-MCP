"""RerankerFactory 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.reranker.base_reranker import BaseReranker, NoneReranker
from libs.reranker.reranker_factory import RerankerFactory


class _ReverseScoreReranker(BaseReranker):
    """测试桩：按 score 倒序重排。"""

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        return sorted(candidates, key=lambda x: float(x.get("score", 0.0)), reverse=True)


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，保留内置 none provider。"""
    snapshot = dict(RerankerFactory._registry)
    RerankerFactory._registry.clear()
    RerankerFactory._registry.update({"none": lambda **_: NoneReranker()})
    try:
        yield snapshot
    finally:
        RerankerFactory._registry.clear()
        RerankerFactory._registry.update(snapshot)


def test_none_backend_keeps_original_order(isolated_registry: dict[str, object]) -> None:
    """验证 none 回退实现不会改变候选顺序，满足“关闭重排不改变排序”验收点。"""
    reranker = RerankerFactory.create({"rerank": {"backend": "none"}})
    candidates = [
        {"id": "a", "score": 0.2},
        {"id": "b", "score": 0.9},
        {"id": "c", "score": 0.4},
    ]

    result = reranker.rerank("query", candidates)

    assert [item["id"] for item in result] == ["a", "b", "c"]


def test_factory_routes_registered_provider(isolated_registry: dict[str, object]) -> None:
    """验证工厂会按 provider 路由到注册实现，并输出预期重排结果。"""
    RerankerFactory.register("reverse", _ReverseScoreReranker)
    reranker = RerankerFactory.create({"rerank": {"provider": "reverse"}})

    result = reranker.rerank(
        "q",
        [
            {"id": "x", "score": 0.1},
            {"id": "y", "score": 0.8},
        ],
    )

    assert isinstance(reranker, _ReverseScoreReranker)
    assert [item["id"] for item in result] == ["y", "x"]


def test_factory_unknown_backend_raises(isolated_registry: dict[str, object]) -> None:
    """验证未知 backend 会明确报错，避免静默回退导致结果不可控。"""
    with pytest.raises(ValueError, match="Unknown rerank backend: mystery"):
        RerankerFactory.create({"rerank": {"backend": "mystery"}})


def test_factory_missing_backend_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证缺少 provider/backend 时错误信息可直接指向配置字段。"""
    with pytest.raises(ValueError, match="rerank.provider"):
        RerankerFactory.create({"rerank": {}})
