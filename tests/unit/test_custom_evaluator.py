"""CustomEvaluator 与 EvaluatorFactory 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.custom_evaluator import CustomEvaluator
from libs.evaluator.evaluator_factory import EvaluatorFactory


class _FixedMetricEvaluator(BaseEvaluator):
    """测试桩：返回固定评估结果，验证工厂分流。"""

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        return {"hit_rate": 1.0, "mrr": 1.0, "total": len(samples), "details": []}


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，保留内置 custom provider。"""
    snapshot = dict(EvaluatorFactory._registry)
    EvaluatorFactory._registry.clear()
    EvaluatorFactory._registry.update({"custom": lambda **_: CustomEvaluator()})
    try:
        yield snapshot
    finally:
        EvaluatorFactory._registry.clear()
        EvaluatorFactory._registry.update(snapshot)


def test_custom_evaluator_returns_stable_hit_rate_and_mrr(isolated_registry: dict[str, object]) -> None:
    """验证给定固定样本时 hit_rate/mrr 输出稳定且数值正确。"""
    evaluator = EvaluatorFactory.create({"evaluation": {"provider": "custom"}})
    samples = [
        {"query": "q1", "retrieved_ids": ["d1", "d2", "d3"], "golden_ids": ["d2"]},
        {"query": "q2", "retrieved_ids": ["a", "b", "c"], "golden_ids": ["z"]},
        {"query": "q3", "retrieved_ids": ["x", "y", "z"], "golden_ids": ["x", "z"]},
    ]

    result = evaluator.evaluate(samples)

    '''
    mrr 是什么
    
    含义：Mean Reciprocal Rank，平均倒数排名。
    看“第一个正确结果”排第几：
    排第1 -> 分数 1/1 = 1.0
    排第2 -> 分数 1/2 = 0.5
    排第3 -> 分数 1/3 ≈ 0.333
    没命中 -> 0
    最后对所有 query 取平均。
    还是上面的例子：
    
    q1 第一个命中在 rank=2 -> 0.5
    q2 没命中 -> 0
    q3 第一个命中在 rank=1 -> 1.0
    所以 mrr = (0.5 + 0 + 1.0) / 3 = 0.5。
    '''
    # q1 命中 rank=2(rr=0.5), q2 未命中(rr=0), q3 命中 rank=1(rr=1)
    assert result["total"] == 3
    assert result["hit_rate"] == pytest.approx(2 / 3)
    assert result["mrr"] == pytest.approx((0.5 + 0.0 + 1.0) / 3)
    assert len(result["details"]) == 3


def test_custom_evaluator_rejects_invalid_sample_shape(isolated_registry: dict[str, object]) -> None:
    """验证样本缺少关键字段时会显式报错，防止评估过程吞掉脏输入。"""
    evaluator = CustomEvaluator()

    with pytest.raises(ValueError, match="retrieved_ids/golden_ids"):
        evaluator.evaluate([{"query": "q", "retrieved_ids": ["d1"]}])


def test_factory_routes_registered_provider(isolated_registry: dict[str, object]) -> None:
    """验证工厂会按 provider 路由到注册评估器实现。"""
    EvaluatorFactory.register("fixed", _FixedMetricEvaluator)
    evaluator = EvaluatorFactory.create({"evaluation": {"provider": "fixed"}})

    result = evaluator.evaluate([{"query": "q", "retrieved_ids": [], "golden_ids": []}])

    assert isinstance(evaluator, _FixedMetricEvaluator)
    assert result["hit_rate"] == 1.0
    assert result["mrr"] == 1.0


def test_factory_missing_provider_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证缺少 `evaluation.provider` 时错误信息可直接定位配置字段。"""
    with pytest.raises(ValueError, match="evaluation.provider"):
        EvaluatorFactory.create({"evaluation": {}})


def test_factory_unknown_provider_raises(isolated_registry: dict[str, object]) -> None:
    """验证未知 provider 会明确报错，避免误用非预期评估后端。"""
    with pytest.raises(ValueError, match="Unknown evaluation provider: mystery"):
        EvaluatorFactory.create({"evaluation": {"provider": "mystery"}})
