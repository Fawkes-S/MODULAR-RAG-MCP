"""CompositeEvaluator 单元测试（H2）。"""

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
from libs.evaluator.evaluator_factory import EvaluatorFactory
from core.settings import EvaluationSettings
from observability.evaluation.composite_evaluator import CompositeEvaluator


class _StubEvaluator(BaseEvaluator):
    """测试桩：返回固定评估结果，并记录是否收到 trace。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        result = dict(self._payload)
        result.setdefault("total", len(samples))
        result.setdefault("details", [{"trace_seen": trace is not None}])
        return result


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离 EvaluatorFactory 注册表，防止污染其他用例。"""
    snapshot = dict(EvaluatorFactory._registry)
    try:
        yield snapshot
    finally:
        EvaluatorFactory._registry.clear()
        EvaluatorFactory._registry.update(snapshot)


def test_composite_evaluator_merges_distinct_metrics() -> None:
    """
    Given:
        两个返回不同指标字段的评估器，
        一个提供 `faithfulness`，另一个提供 `hit_rate/mrr`。

    When:
        调用 `CompositeEvaluator.evaluate(samples)`。

    Then:
        - 组合器应并行执行两个后端；
        - 顶层结果应同时包含两组不冲突指标；
        - 各后端完整结果应保留在 `details_by_backend` 中。
    """
    evaluator = CompositeEvaluator(
        evaluators=[
            _StubEvaluator({"faithfulness": 0.93, "details": [{"source": "ragas"}]}),
            _StubEvaluator({"hit_rate": 1.0, "mrr": 0.5, "details": [{"source": "custom"}]}),
        ]
    )

    result = evaluator.evaluate([{"query": "q"}], trace=object())

    assert result["faithfulness"] == pytest.approx(0.93)
    assert result["hit_rate"] == pytest.approx(1.0)
    assert result["mrr"] == pytest.approx(0.5)
    assert result["total"] == 1
    assert "details_by_backend" in result
    assert len(result["details_by_backend"]) == 2
    assert any("faithfulness" in payload for payload in result["details_by_backend"].values())
    assert any("hit_rate" in payload for payload in result["details_by_backend"].values())


def test_composite_evaluator_rejects_metric_name_conflict() -> None:
    """
    Given:
        两个后端都返回同名指标 `hit_rate`，但数值不同。

    When:
        执行组合评估。

    Then:
        应抛出 `ValueError`，显式暴露指标命名冲突，
        防止后端结果被静默覆盖。
    """
    evaluator = CompositeEvaluator(
        evaluators=[
            _StubEvaluator({"hit_rate": 1.0}),
            _StubEvaluator({"hit_rate": 0.5}),
        ]
    )

    with pytest.raises(ValueError, match="metric conflict"):
        evaluator.evaluate([{"query": "q"}])


def test_factory_builds_composite_evaluator_from_backends(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        `evaluation.backends` 配置为两个已注册后端，
        工厂注册表中各自有可构造的评估器实现。

    When:
        调用 `EvaluatorFactory.create(settings)`。

    Then:
        工厂应返回 `CompositeEvaluator`，
        并按配置顺序组装多个子评估器。
    """
    EvaluatorFactory._registry.clear()
    EvaluatorFactory._registry.update(
        {
            "ragas": lambda **_: _StubEvaluator({"faithfulness": 0.9}),
            "custom": lambda **_: _StubEvaluator({"hit_rate": 1.0}),
        }
    )

    evaluator = EvaluatorFactory.create({"evaluation": {"backends": ["ragas", "custom"]}})

    assert isinstance(evaluator, CompositeEvaluator)
    result = evaluator.evaluate([{"query": "q"}])
    assert result["faithfulness"] == pytest.approx(0.9)
    assert result["hit_rate"] == pytest.approx(1.0)


def test_factory_keeps_single_provider_compatibility(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        老配置只提供 `evaluation.provider=custom`，没有 `backends`。

    When:
        调用 `EvaluatorFactory.create(settings)`。

    Then:
        工厂仍应返回单个评估器实例，保证 H2 不破坏旧路径兼容性。
    """
    EvaluatorFactory._registry.clear()
    EvaluatorFactory._registry.update({"custom": lambda **_: _StubEvaluator({"hit_rate": 1.0})})

    evaluator = EvaluatorFactory.create({"evaluation": {"provider": "custom"}})

    assert not isinstance(evaluator, CompositeEvaluator)
    assert evaluator.evaluate([{"query": "q"}])["hit_rate"] == pytest.approx(1.0)


def test_factory_reads_backends_from_settings_object(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        一个带 `evaluation.backends` 的强类型 `EvaluationSettings` 容器对象。

    When:
        用该对象调用 `EvaluatorFactory.create()`。

    Then:
        工厂应和 dict 配置路径一样，返回 `CompositeEvaluator`，
        证明 H2 不只支持 YAML 原始 dict，也支持项目内部的 `Settings` 对象。
    """

    class _SettingsWrapper:
        def __init__(self) -> None:
            self.evaluation = EvaluationSettings(
                provider="",
                enabled=False,
                backends=("ragas", "custom"),
            )

    EvaluatorFactory._registry.clear()
    EvaluatorFactory._registry.update(
        {
            "ragas": lambda **_: _StubEvaluator({"faithfulness": 0.88}),
            "custom": lambda **_: _StubEvaluator({"hit_rate": 0.75}),
        }
    )

    evaluator = EvaluatorFactory.create(_SettingsWrapper())

    assert isinstance(evaluator, CompositeEvaluator)
    result = evaluator.evaluate([{"query": "q"}])
    assert result["faithfulness"] == pytest.approx(0.88)
    assert result["hit_rate"] == pytest.approx(0.75)


def test_composite_evaluator_degrades_when_optional_backend_missing_dependency() -> None:
    """
    Given:
        两个评估后端里，一个正常返回 retrieval 指标，
        另一个因为可选依赖缺失抛出 `ImportError`（例如 ragas 环境不完整）。

    When:
        执行 `CompositeEvaluator.evaluate(samples)`。

    Then:
        组合评估不应整次失败，而应保留可用后端结果继续返回，
        同时把失败后端写入 `backend_errors`，让 CLI/Dashboard 知道发生了什么降级。
    """

    class _MissingDependencyEvaluator(BaseEvaluator):
        def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
            raise ImportError("install `ragas` and `datasets` first")

    evaluator = CompositeEvaluator(
        evaluators=[
            _MissingDependencyEvaluator(),
            _StubEvaluator({"hit_rate": 1.0, "mrr": 0.5}),
        ]
    )

    result = evaluator.evaluate([{"query": "q"}])

    assert result["hit_rate"] == pytest.approx(1.0)
    assert result["mrr"] == pytest.approx(0.5)
    assert "backend_errors" in result
    assert "_missingdependency" in result["backend_errors"]


def test_composite_evaluator_degrades_when_ragas_backend_is_misconfigured() -> None:
    """
    Given:
        一个外部评估后端因为缺少 API Key 抛出 `ValueError`，
        另一个本地 custom 后端仍可正常返回指标。

    When:
        执行组合评估。

    Then:
        组合器应保留 custom 指标并记录外部后端错误，
        防止“Ragas 未真实运行”被误判为评估成功。
    """

    class _MisconfiguredRagasEvaluator(BaseEvaluator):
        def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
            raise ValueError("RagasEvaluator requires llm.api_key")

    evaluator = CompositeEvaluator(
        evaluators=[
            _MisconfiguredRagasEvaluator(),
            _StubEvaluator({"hit_rate": 0.5, "mrr": 0.25}),
        ]
    )

    result = evaluator.evaluate([{"query": "q"}])

    assert result["hit_rate"] == pytest.approx(0.5)
    assert result["mrr"] == pytest.approx(0.25)
    assert "_misconfiguredragas" in result["backend_errors"]
    assert "llm.api_key" in result["backend_errors"]["_misconfiguredragas"]
