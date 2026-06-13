"""RagasEvaluator 单元测试（H1）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.evaluator.evaluator_factory import EvaluatorFactory
from observability.evaluation.ragas_evaluator import RagasEvaluator


class _FakeRagasResult:
    """测试桩：模拟 Ragas 返回对象。"""

    def __init__(self, payload: dict[str, float]) -> None:
        self.payload = payload

    def to_dict(self) -> dict[str, float]:
        return dict(self.payload)


def _make_fake_ragas_loader(result_payload: dict[str, float]):
    """构造可注入的假 Ragas runtime。"""

    def _evaluate(dataset: list[dict[str, Any]]) -> _FakeRagasResult:
        # 这里直接断言 dataset 形状，确保适配层把字段转换成了 Ragas 预期结构。
        assert dataset[0]["question"] == "如何配置 Azure OpenAI？"
        assert dataset[0]["answer"] == "需要先配置 endpoint 和 key。"
        assert dataset[0]["ground_truth"] == "先填写 endpoint，再填写 key。"
        assert dataset[0]["contexts"] == ["Azure OpenAI setup guide", "endpoint and key"]
        return _FakeRagasResult(result_payload)

    def _dataset_from_list(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(rows)

    return lambda: (_evaluate, _dataset_from_list)


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离 EvaluatorFactory 注册表，避免污染其它测试。"""
    snapshot = dict(EvaluatorFactory._registry)
    try:
        yield snapshot
    finally:
        EvaluatorFactory._registry.clear()
        EvaluatorFactory._registry.update(snapshot)


def test_ragas_evaluator_returns_standardized_metrics() -> None:
    """
    Given:
        一个注入 fake Ragas runtime 的 `RagasEvaluator`，
        且样本包含 query / retrieved_chunks / generated_answer / ground_truth。
    When:
        调用 `evaluate(samples)`。
    Then:
        - 适配层应把样本转换成 question/answer/ground_truth/contexts；
        - 返回结果应标准化为 faithfulness / answer_relevancy / context_precision / total / details。
    """
    evaluator = RagasEvaluator(
        ragas_loader=_make_fake_ragas_loader(
            {
                "faithfulness": 0.91,
                "answer_relevancy": 0.87,
                "context_precision": 0.89,
            }
        )
    )

    result = evaluator.evaluate(
        [
            {
                "query": "如何配置 Azure OpenAI？",
                "retrieved_chunks": ["Azure OpenAI setup guide", "endpoint and key"],
                "generated_answer": "需要先配置 endpoint 和 key。",
                "ground_truth": "先填写 endpoint，再填写 key。",
            }
        ]
    )

    assert result["faithfulness"] == pytest.approx(0.91)
    assert result["answer_relevancy"] == pytest.approx(0.87)
    assert result["context_precision"] == pytest.approx(0.89)
    assert result["total"] == 1
    assert result["details"][0]["question"] == "如何配置 Azure OpenAI？"


def test_ragas_evaluator_reports_missing_dependency_clearly() -> None:
    """
    Given:
        一个内部 loader 会抛出 `ImportError` 的 `RagasEvaluator`。
    When:
        调用 `evaluate(samples)`。
    Then:
        应抛出带安装提示的可读 `ImportError`，而不是底层模糊异常。
    """

    def _missing_loader() -> tuple[Any, Any]:
        raise ImportError("RagasEvaluator requires optional dependencies: install `ragas` and `datasets` first")

    evaluator = RagasEvaluator(ragas_loader=_missing_loader)

    with pytest.raises(ImportError, match="install `ragas` and `datasets`"):
        evaluator.evaluate(
            [
                {
                    "query": "q",
                    "retrieved_chunks": ["ctx"],
                    "generated_answer": "a",
                    "ground_truth": "g",
                }
            ]
        )


def test_ragas_evaluator_rejects_invalid_sample_shape() -> None:
    """
    Given:
        一个缺少 `retrieved_chunks` 的脏样本。
    When:
        调用 `evaluate(samples)`。
    Then:
        应抛出 `ValueError`，明确指出缺失的关键字段。
    """
    evaluator = RagasEvaluator(ragas_loader=_make_fake_ragas_loader({}))

    with pytest.raises(ValueError, match="retrieved_chunks"):
        evaluator.evaluate(
            [
                {
                    "query": "q",
                    "generated_answer": "a",
                    "ground_truth": "g",
                }
            ]
        )


def test_evaluator_factory_routes_ragas_provider(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        将 `ragas` provider 注册到 `EvaluatorFactory`，并让其返回带 fake loader 的 `RagasEvaluator`。
    When:
        调用 `EvaluatorFactory.create({"evaluation": {"provider": "ragas"}})`。
    Then:
        工厂应按 provider 路由到 `RagasEvaluator` 实例，而不是回退到其它 evaluator。
    """
    EvaluatorFactory._registry.clear()
    EvaluatorFactory._registry.update(
        {
            "custom": lambda **_: object(),  # type: ignore[dict-item]
            "ragas": lambda **_: RagasEvaluator(ragas_loader=_make_fake_ragas_loader({})),
        }
    )

    evaluator = EvaluatorFactory.create({"evaluation": {"provider": "ragas"}})

    assert isinstance(evaluator, RagasEvaluator)
