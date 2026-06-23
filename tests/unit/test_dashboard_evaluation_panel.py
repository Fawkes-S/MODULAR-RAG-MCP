"""Dashboard 评估面板页面测试（H4）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings
from libs.evaluator.base_evaluator import BaseEvaluator
from observability.dashboard.pages.evaluation_panel import (
    EvaluationPanelService,
    EvaluationPanelSnapshot,
    render,
)
from observability.evaluation.eval_runner import EvalQueryDetail, EvalReport


class _FakeEvaluator(BaseEvaluator):
    """测试桩：不执行真实评估，只满足 `BaseEvaluator` 契约。"""

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        return {"total": len(samples)}


class _FakeConfigService:
    """测试桩：返回固定 Settings，避免测试自己读写配置文件。"""

    def __init__(self, settings: Settings) -> None:
        self.settings_path = PROJECT_ROOT / "config" / "settings.yaml"
        self._settings = settings

    def load_settings(self) -> Settings:
        return self._settings


class _FakeRunner:
    """测试桩：模拟 EvalRunner，只记录收到的 golden set 路径。"""

    def __init__(self, report: EvalReport, calls: dict[str, Any]) -> None:
        self.report = report
        self.calls = calls

    def run(self, test_set_path: str) -> EvalReport:
        self.calls["test_set_path"] = test_set_path
        return self.report


class _FakeEvaluationService:
    """测试桩：给页面渲染测试提供固定配置快照和报告。"""

    def __init__(self, report: EvalReport) -> None:
        self.report = report
        self.run_calls: list[dict[str, str]] = []

    def build_snapshot(self) -> EvaluationPanelSnapshot:
        return EvaluationPanelSnapshot(
            evaluation_enabled=False,
            configured_backends=("ragas", "custom"),
            configured_provider="ragas",
            backend_options=["<config>", "custom", "ragas+custom"],
            backend_labels={
                "<config>": "使用配置默认 (ragas, custom)",
                "custom": "custom",
                "ragas+custom": "ragas+custom",
            },
            default_test_set_path=str(PROJECT_ROOT / "tests" / "fixtures" / "golden_test_set.json"),
            retrieval_top_k=8,
            ragas_llm_profile="deepseek_chat",
        )

    def run_evaluation(self, *, test_set_path: str, backend_selection: str) -> EvalReport:
        self.run_calls.append(
            {
                "test_set_path": test_set_path,
                "backend_selection": backend_selection,
            }
        )
        return self.report


class _FakeStreamlit:
    """最小 fake Streamlit，只覆盖评估面板用到的 API。"""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.dataframes: list[list[dict[str, Any]]] = []
        self.metrics: list[tuple[str, Any]] = []
        self.markdown_calls: list[dict[str, Any]] = []
        self.session_state: dict[str, Any] = {}

    def title(self, text: str) -> None:
        self.messages.append(("title", text))

    def caption(self, text: str) -> None:
        self.messages.append(("caption", text))

    def subheader(self, text: str) -> None:
        self.messages.append(("subheader", text))

    def warning(self, text: str) -> None:
        self.messages.append(("warning", text))

    def error(self, text: str) -> None:
        self.messages.append(("error", text))

    def success(self, text: str) -> None:
        self.messages.append(("success", text))

    def info(self, text: str) -> None:
        self.messages.append(("info", text))

    def markdown(self, text: str, **kwargs: Any) -> None:
        self.markdown_calls.append({"text": text, "kwargs": kwargs})
        self.messages.append(("markdown", text))

    def dataframe(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(rows)

    def columns(self, count: int) -> list["_FakeStreamlit"]:
        return [self for _ in range(count)]

    def metric(self, label: str, value: Any) -> None:
        self.metrics.append((label, value))

    def selectbox(
        self,
        label: str,
        options: list[Any],
        index: int = 0,
        format_func: Any | None = None,
        help: str | None = None,
    ) -> Any:
        _ = (label, format_func, help)
        return options[index]

    def text_input(self, label: str, value: str = "", help: str | None = None) -> str:
        _ = (label, help)
        return value

    def button(self, label: str, **kwargs: Any) -> bool:
        _ = (label, kwargs)
        return True


def _make_report() -> EvalReport:
    """构造一份覆盖 retrieval 指标、后端指标和后端错误的评估报告。"""
    return EvalReport(
        test_set_path=str(PROJECT_ROOT / "tests" / "fixtures" / "golden_test_set.json"),
        generated_at="2026-06-15T12:00:00+00:00",
        total=2,
        hit_rate=0.5,
        mrr=0.25,
        details=(
            EvalQueryDetail(
                query="如何配置 Azure OpenAI？",
                filters={"collection": "default"},
                expected_chunk_ids=("chunk_config_001",),
                expected_sources=("config_guide.pdf",),
                retrieved_chunk_ids=("chunk_config_001", "chunk_other"),
                retrieved_sources=("config_guide.pdf", "other.pdf"),
                hit=True,
                reciprocal_rank=1.0,
                first_match_rank=1,
            ),
            EvalQueryDetail(
                query="RRF 是什么？",
                filters={"collection": "default"},
                expected_chunk_ids=("chunk_retrieval_001",),
                expected_sources=("retrieval_design.pdf",),
                retrieved_chunk_ids=("chunk_other",),
                retrieved_sources=("other.pdf",),
                hit=False,
                reciprocal_rank=0.0,
                first_match_rank=None,
                error="RuntimeError: bm25 index missing",
            ),
        ),
        evaluator_metrics={
            "context_precision": 0.0,
            "details_by_backend": {
                "custom": {
                    "hit_rate": 0.5,
                    "mrr": 0.25,
                    "total": 2,
                    "details": [{"query": "q1"}, {"query": "q2"}],
                }
            },
            "backend_errors": {
                "ragas": "ValueError: RagasEvaluator requires llm.api_key",
            },
        },
    )


@pytest.fixture()
def settings() -> Settings:
    """加载真实 Settings，保证 H4 服务测试覆盖项目配置映射。"""
    return load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))


def test_evaluation_panel_service_builds_snapshot_from_settings(settings: Settings) -> None:
    """
    Given:
        一个使用项目真实 Settings 的 `EvaluationPanelService`。
    When:
        调用 `build_snapshot()`。
    Then:
        - 快照应包含配置里的 evaluation.backends；
        - 默认 golden test set 应解析为项目内路径；
        - 后端选择项应包含配置默认项和常用候选项。
    """
    service = EvaluationPanelService(config_service=_FakeConfigService(settings))

    snapshot = service.build_snapshot()

    assert snapshot.configured_backends == ("ragas", "custom")
    assert snapshot.default_test_set_path.endswith("tests\\fixtures\\golden_test_set.json") or snapshot.default_test_set_path.endswith(
        "tests/fixtures/golden_test_set.json"
    )
    assert "<config>" in snapshot.backend_options
    assert "custom" in snapshot.backend_options
    assert snapshot.ragas_llm_profile == settings.evaluation.ragas.llm_profile


def test_evaluation_panel_service_runs_eval_with_selected_backend(settings: Settings) -> None:
    """
    Given:
        一个注入 fake HybridSearch、fake Evaluator 和 fake EvalRunner 的评估面板服务。
    When:
        用 `backend_selection="custom"` 调用 `run_evaluation()`。
    Then:
        - 本次运行的 Settings 应临时切到 custom 后端；
        - golden set 路径应解析为绝对路径；
        - 返回值应是 runner 产出的报告。
    """
    calls: dict[str, Any] = {}
    expected_report = _make_report()

    def _hybrid_factory(run_settings: Settings) -> object:
        calls["hybrid_backends"] = run_settings.evaluation.backends
        return object()

    def _evaluator_factory(run_settings: Settings) -> BaseEvaluator:
        calls["evaluator_backends"] = run_settings.evaluation.backends
        return _FakeEvaluator()

    def _runner_factory(run_settings: Settings, hybrid_search: Any, evaluator: BaseEvaluator) -> _FakeRunner:
        calls["runner_backends"] = run_settings.evaluation.backends
        calls["hybrid_search"] = hybrid_search
        calls["evaluator"] = evaluator
        return _FakeRunner(expected_report, calls)

    service = EvaluationPanelService(
        config_service=_FakeConfigService(settings),
        hybrid_search_factory=_hybrid_factory,
        evaluator_factory=_evaluator_factory,
        runner_factory=_runner_factory,
    )

    report = service.run_evaluation(
        test_set_path="tests/fixtures/golden_test_set.json",
        backend_selection="custom",
    )

    assert report is expected_report
    assert calls["hybrid_backends"] == ("custom",)
    assert calls["evaluator_backends"] == ("custom",)
    assert calls["runner_backends"] == ("custom",)
    assert Path(calls["test_set_path"]).is_absolute()


def test_evaluation_panel_render_runs_eval_and_shows_metrics() -> None:
    """
    Given:
        一个返回固定报告的 fake 评估服务，以及一个按钮默认点击的 fake Streamlit。
    When:
        调用 `render(evaluation_service=fake_service, st_module=fake_streamlit)`。
    Then:
        - 页面应调用服务执行评估；
        - 聚合指标应显示 Test Cases、Hit Rate、MRR；
        - evaluator 指标、后端明细、后端错误、逐 query 明细和会话历史都应渲染成表格。
    """
    fake_streamlit = _FakeStreamlit()
    service = _FakeEvaluationService(_make_report())

    render(evaluation_service=service, st_module=fake_streamlit)

    assert service.run_calls == [
        {
            "test_set_path": str(PROJECT_ROOT / "tests" / "fixtures" / "golden_test_set.json"),
            "backend_selection": "<config>",
        }
    ]
    assert ("Test Cases", 2) in fake_streamlit.metrics
    assert ("Hit Rate", "0.5000") in fake_streamlit.metrics
    assert ("MRR", "0.2500") in fake_streamlit.metrics
    assert any(kind == "warning" and "Ragas" in text for kind, text in fake_streamlit.messages)
    assert any(kind == "success" and "完成" in text for kind, text in fake_streamlit.messages)

    assert fake_streamlit.dataframes[0][0]["configured_backends"] == "ragas, custom"
    evaluator_metric_rows = next(rows for rows in fake_streamlit.dataframes if rows and rows[0].get("metric") == "context_precision")
    assert evaluator_metric_rows[0]["value"] == 0.0
    backend_rows = next(rows for rows in fake_streamlit.dataframes if rows and rows[0].get("backend") == "custom")
    assert backend_rows[0]["detail_count"] == 2
    error_rows = next(rows for rows in fake_streamlit.dataframes if rows and rows[0].get("backend") == "ragas")
    assert "llm.api_key" in error_rows[0]["error"]
    detail_rows = next(rows for rows in fake_streamlit.dataframes if rows and rows[0].get("query") == "如何配置 Azure OpenAI？")
    assert detail_rows[0]["hit"] is True
    assert detail_rows[1]["error"] == "RuntimeError: bm25 index missing"
    history_rows = next(rows for rows in fake_streamlit.dataframes if rows and rows[0].get("backend_errors") == "ragas")
    assert history_rows[0]["hit_rate"] == 0.5
    assert any(call["kwargs"].get("unsafe_allow_html") is True for call in fake_streamlit.markdown_calls)
