"""EvalRunner 单元测试（H3）。"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import load_settings
from core.types import RetrievalResult
from libs.evaluator.base_evaluator import BaseEvaluator
from observability.evaluation.eval_runner import EvalRunner, GoldenTestCase


class _StubHybridSearch:
    """测试桩：根据 query 返回预设检索结果。"""

    def __init__(self, responses: dict[str, list[RetrievalResult] | Exception]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "filters": dict(filters or {}),
                "trace": trace,
            }
        )
        response = self._responses[query]
        if isinstance(response, Exception):
            raise response
        return list(response)


class _CapturingEvaluator(BaseEvaluator):
    """测试桩：记录收到的样本，并返回固定指标。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.samples_seen: list[dict[str, Any]] = []

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        self.samples_seen = list(samples)
        return dict(self.payload)


def _make_result(chunk_id: str, source_path: str, text: str, score: float = 1.0) -> RetrievalResult:
    """构造简化 RetrievalResult，避免测试里重复样板。"""
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        metadata={
            "source_path": source_path,
            "collection": "default",
        },
    )


def _write_temp_golden_set(tmp_path: Path) -> Path:
    """为单测生成隔离黄金集，避免依赖共享 fixture 被其他任务改动后漂移。

    为什么这样做：
    - H3 单测的目标是验证 `EvalRunner` 的指标计算与样本适配逻辑；
    - 如果直接依赖仓库里的共享 `golden_test_set.json`，一旦 H5 或人工调优改了 fixture，
      这里就会出现“实现没坏、测试先坏”的脆弱耦合。
    """
    payload = {
        "test_cases": [
            {
                "query": "如何配置 Azure OpenAI？",
                "expected_chunk_ids": ["chunk_config_001"],
                "expected_sources": ["config_guide.pdf"],
                "filters": {"collection": "default"},
                "ground_truth": "配置 Azure OpenAI 时，需要提供 endpoint、deployment name 和 api key。",
            },
            {
                "query": "RRF 融合是做什么的？",
                "expected_chunk_ids": ["chunk_retrieval_001"],
                "expected_sources": ["retrieval_design.pdf"],
                "filters": {"collection": "default"},
                "ground_truth": "RRF 会把 dense 和 sparse 两路召回结果按排名倒数融合，得到统一排序。",
            },
        ]
    }
    golden_path = tmp_path / "golden_test_set.json"
    golden_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return golden_path


@pytest.fixture()
def settings():
    """加载项目真实 Settings，保证 H3 配置映射可被测试覆盖。"""
    return load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))


def test_golden_test_case_normalizes_json_payload() -> None:
    """
    Given:
        一条来自黄金测试集 JSON 的原始 dict，包含 query、expected ids、source 和 filters。

    When:
        调用 `GoldenTestCase.from_dict()`。

    Then:
        应把输入标准化为强类型对象，去掉空白并保留后续 runner 所需字段，
        避免后面每个执行步骤重复做 shape 校验。
    """
    case = GoldenTestCase.from_dict(
        {
            "query": "  如何配置 Azure OpenAI？  ",
            "expected_chunk_ids": [" chunk_1 ", ""],
            "expected_sources": [" config_guide.pdf "],
            "filters": {"collection": "default"},
            "ground_truth": "gt",
        }
    )

    assert case.query == "如何配置 Azure OpenAI？"
    assert case.expected_chunk_ids == ("chunk_1",)
    assert case.expected_sources == ("config_guide.pdf",)
    assert case.filters == {"collection": "default"}
    assert case.ground_truth == "gt"


def test_golden_test_case_accepts_reference_answer_alias() -> None:
    """
    Given:
        一条黄金测试集条目没有填写 `ground_truth`，
        但填写了用户更常写的 `reference_answer` 字段。
    When:
        调用 `GoldenTestCase.from_dict()`。
    Then:
        评估集解析层应把 `reference_answer` 兼容映射到 `ground_truth`，
        避免答案已经写进 JSON，但 Ragas 实际拿到的却是空标准答案。
    """
    case = GoldenTestCase.from_dict(
        {
            "query": "What is Modular RAG?",
            "expected_chunk_ids": [],
            "expected_sources": ["modular_rag_overview.pdf"],
            "reference_answer": "Modular RAG is a pluggable retrieval-augmented generation system.",
        }
    )

    assert case.ground_truth == "Modular RAG is a pluggable retrieval-augmented generation system."


def test_eval_runner_calculates_hit_rate_and_mrr_and_builds_evaluator_samples(
    settings,
    tmp_path: Path,
) -> None:
    """
    Given:
        两条黄金测试用例：
        一条第一名就命中 expected_chunk_ids，另一条通过 expected_sources 在第二名命中。

    When:
        运行 `EvalRunner.run()`。

    Then:
        - hit_rate 应为 1.0；
        - mrr 应按 1 + 1/2 求平均；
        - 传给 evaluator 的样本应同时带有 retrieved_ids / golden_ids / retrieved_chunks / ground_truth，
          以兼容 custom 与 ragas 两类后端。
    """
    hybrid_search = _StubHybridSearch(
        responses={
            "如何配置 Azure OpenAI？": [
                _make_result("chunk_config_001", "config_guide.pdf", "Azure setup text"),
                _make_result("chunk_other_001", "misc.pdf", "Other text", score=0.4),
            ],
            "RRF 融合是做什么的？": [
                _make_result("chunk_other_002", "other.pdf", "Other retrieval text"),
                _make_result("chunk_irrelevant", "retrieval_design.pdf", "RRF merges rankings", score=0.7),
            ],
        }
    )
    evaluator = _CapturingEvaluator({"faithfulness": 0.88, "answer_relevancy": 0.77})
    runner = EvalRunner(settings=settings, hybrid_search=hybrid_search, evaluator=evaluator)

    golden_path = _write_temp_golden_set(tmp_path)
    report = runner.run(str(golden_path))

    assert report.total == 2
    assert report.hit_rate == pytest.approx(1.0)
    assert report.mrr == pytest.approx((1.0 + 0.5) / 2.0)
    assert report.evaluator_metrics["faithfulness"] == pytest.approx(0.88)
    assert report.details[0].first_match_rank == 1
    assert report.details[1].first_match_rank == 2

    assert hybrid_search.calls[0]["filters"] == {"collection": "default"}
    assert hybrid_search.calls[1]["filters"] == {"collection": "default"}

    first_sample = evaluator.samples_seen[0]
    assert first_sample["retrieved_ids"] == ["chunk_config_001", "chunk_other_001"]
    assert first_sample["golden_ids"] == ["chunk_config_001"]
    assert first_sample["retrieved_chunks"] == ["Azure setup text", "Other text"]
    assert first_sample["ground_truth"]


def test_eval_runner_keeps_running_when_single_query_retrieval_fails(
    settings,
    tmp_path: Path,
) -> None:
    """
    Given:
        黄金测试集中的一条 query 检索正常，另一条 query 在 HybridSearch 阶段抛出 RuntimeError。

    When:
        运行 `EvalRunner.run()`。

    Then:
        runner 不应整次中断，而应把失败 query 记为 miss，
        同时在 detail.error 里保留错误摘要，便于后续 Dashboard/CLI 排查。
    """
    hybrid_search = _StubHybridSearch(
        responses={
            "如何配置 Azure OpenAI？": [
                _make_result("chunk_config_001", "config_guide.pdf", "Azure setup text"),
            ],
            "RRF 融合是做什么的？": RuntimeError("bm25 index missing"),
        }
    )
    evaluator = _CapturingEvaluator({"hit_rate": 0.5})
    runner = EvalRunner(settings=settings, hybrid_search=hybrid_search, evaluator=evaluator)

    golden_path = _write_temp_golden_set(tmp_path)
    report = runner.run(str(golden_path))

    assert report.total == 2
    assert report.hit_rate == pytest.approx(0.5)
    assert report.mrr == pytest.approx(0.5)
    assert report.details[1].hit is False
    assert report.details[1].error is not None
    assert "bm25 index missing" in report.details[1].error


def test_eval_runner_rejects_invalid_golden_set_root(settings, tmp_path: Path) -> None:
    """
    Given:
        一个不包含 `test_cases` 列表的非法黄金测试集文件。

    When:
        调用 `EvalRunner.run()`。

    Then:
        应 fail-fast 抛出 `ValueError`，
        避免脚本表面成功但实际上没有任何有效测试用例被执行。
    """
    bad_file = tmp_path / "bad_golden_test_set.json"
    bad_file.write_text('{"items": []}', encoding="utf-8")

    runner = EvalRunner(
        settings=settings,
        hybrid_search=_StubHybridSearch(responses={}),
        evaluator=_CapturingEvaluator({}),
    )

    with pytest.raises(ValueError, match="test_cases"):
        runner.run(str(bad_file))
