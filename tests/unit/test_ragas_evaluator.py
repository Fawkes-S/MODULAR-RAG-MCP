"""RagasEvaluator 单元测试（H1）。"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.evaluator.evaluator_factory import EvaluatorFactory
from core.settings import Settings, load_settings
from observability.evaluation.ragas_evaluator import (
    _ProjectRagasLLM,
    RagasEvaluator,
    _RagasEmbeddingCompat,
    _extract_json_object,
)


class _FakeRagasResult:
    """测试桩：模拟 Ragas 返回对象。"""

    def __init__(self, payload: dict[str, float]) -> None:
        self.payload = payload

    def to_dict(self) -> dict[str, float]:
        return dict(self.payload)


class _FakeInstructorBase:
    """测试桩：模拟 Ragas 的 InstructorBaseRagasLLM 抽象基类。"""


def _make_test_settings() -> Settings:
    """构造带假 API Key 的 Settings，避免单元测试触发真实网络。"""
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    profiles = {name: dict(value) for name, value in settings.llm.profiles.items()}
    profiles.setdefault("deepseek_chat", {})
    profiles["deepseek_chat"]["api_key"] = "test-key"
    profiles["deepseek_chat"].setdefault("provider", "deepseek")
    profiles["deepseek_chat"].setdefault("model", "deepseek-chat")
    profiles["deepseek_chat"].setdefault("base_url", "https://api.deepseek.com/v1")
    return replace(
        settings,
        llm=replace(
            settings.llm,
            api_key="test-key",
            base_url="https://example.test/v1",
            profiles=profiles,
        ),
    )


def _resolve_expected_ragas_llm(settings: Settings) -> Any:
    """解析当前配置下 Ragas 实际会选中的 LLM 配置。

    这个辅助函数专门给测试使用，目的不是重复业务逻辑，而是把断言目标
    明确绑定到 `settings.yaml -> evaluation.ragas.llm_profile` 的当前选择。
    这样当项目把评估模型从 `deepseek_chat` 切到 `deepseek`、`openai`
    或其他 OpenAI-compatible profile 时，测试只需要验证“解析结果被正确使用”，
    而不是被旧的写死字符串误伤。
    """
    return RagasEvaluator._resolve_ragas_llm_settings(settings)


def _make_fake_ragas_loader(result_payload: dict[str, float]):
    """构造可注入的假 Ragas runtime。

    Fake runtime 会记录适配层传入的 LLM、Embedding 和 metrics 参数，
    这样测试能验证“真实 Ragas 所需对象已被显式传入”，而不需要触网。
    """
    calls: dict[str, Any] = {}

    def _evaluate(
        dataset: list[dict[str, Any]],
        *,
        metrics: list[str],
        llm: dict[str, Any],
        embeddings: dict[str, Any],
        raise_exceptions: bool,
        show_progress: bool,
    ) -> _FakeRagasResult:
        # 这里直接断言 dataset 形状，确保适配层把字段转换成了 Ragas 预期结构。
        assert dataset[0]["question"] == "如何配置 Azure OpenAI？"
        assert dataset[0]["answer"] == "需要先配置 endpoint 和 key。"
        assert dataset[0]["ground_truth"] == "先填写 endpoint，再填写 key。"
        assert dataset[0]["contexts"] == ["Azure OpenAI setup guide", "endpoint and key"]
        calls["evaluate_kwargs"] = {
            "metrics": metrics,
            "llm": llm,
            "embeddings": embeddings,
            "raise_exceptions": raise_exceptions,
            "show_progress": show_progress,
        }
        return _FakeRagasResult(result_payload)

    def _dataset_from_list(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(rows)

    def _embedding_factory(**kwargs: Any) -> dict[str, Any]:
        calls["embedding_kwargs"] = dict(kwargs)
        return {"kind": "embedding", **kwargs}

    def _llm_factory(**kwargs: Any) -> dict[str, Any]:
        calls["llm_kwargs"] = dict(kwargs)
        return {"kind": "llm", **kwargs}

    def _metrics_factory() -> list[str]:
        return ["faithfulness", "answer_relevancy", "context_precision"]

    def _loader() -> tuple[Any, Any, Any, Any, Any, Any]:
        return (
            _evaluate,
            _dataset_from_list,
            _llm_factory,
            _FakeInstructorBase,
            _embedding_factory,
            _metrics_factory,
        )

    _loader.calls = calls  # type: ignore[attr-defined]
    return _loader


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
    fake_loader = _make_fake_ragas_loader(
        {
            "faithfulness": 0.91,
            "answer_relevancy": 0.87,
            "context_precision": 0.89,
        }
    )
    settings = _make_test_settings()
    evaluator = RagasEvaluator(
        settings=settings,
        ragas_loader=fake_loader,
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
    assert fake_loader.calls["evaluate_kwargs"]["metrics"] == [  # type: ignore[attr-defined]
        "faithfulness",
        "answer_relevancy",
        "context_precision",
    ]
    assert fake_loader.calls["evaluate_kwargs"]["raise_exceptions"] is True  # type: ignore[attr-defined]
    assert fake_loader.calls["evaluate_kwargs"]["show_progress"] is False  # type: ignore[attr-defined]
    llm = fake_loader.calls["evaluate_kwargs"]["llm"]  # type: ignore[attr-defined]
    expected_llm = _resolve_expected_ragas_llm(settings)
    # 这里既兼容“官方 Ragas llm_factory 返回 dict”的路径，
    # 也兼容“项目自带包装器对象”的路径。
    if isinstance(llm, dict):
        assert llm["model"] == expected_llm.model
        assert fake_loader.calls["llm_kwargs"]["max_tokens"] == 1536  # type: ignore[attr-defined]
    else:
        assert getattr(llm, "model", None) == expected_llm.model
        assert getattr(llm, "max_tokens", None) == 1536
    assert fake_loader.calls["embedding_kwargs"]["provider"] == "huggingface"  # type: ignore[attr-defined]


def test_ragas_evaluator_prefers_project_wrapper_for_deepseek_like_profiles() -> None:
    """
    Given:
        当前评估 profile 使用 DeepSeek 这类 OpenAI-compatible 但行为差异较大的模型。
    When:
        判断 Ragas LLM 路由策略。
    Then:
        应优先走项目自带包装器，而不是直接走 Ragas 官方 instructor 路径，
        从而降低真实评估时的结构化重试和超时放大风险。
    """
    settings = _make_test_settings()
    resolved = _resolve_expected_ragas_llm(settings)

    assert RagasEvaluator._should_use_project_llm_wrapper(resolved) is True


def test_ragas_evaluator_reports_missing_dependency_clearly() -> None:
    """
    Given:
        一个内部 loader 会抛出 `ImportError` 的 `RagasEvaluator`。
    When:
        调用 `evaluate(samples)`。
    Then:
        应抛出带安装提示的可读 `ImportError`，而不是底层模糊异常。
    """

    def _missing_loader() -> tuple[Any, Any, Any, Any, Any, Any]:
        raise ImportError("RagasEvaluator requires optional dependencies: install `ragas` and `datasets` first")

    evaluator = RagasEvaluator(settings=_make_test_settings(), ragas_loader=_missing_loader)

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
    evaluator = RagasEvaluator(settings=_make_test_settings(), ragas_loader=_make_fake_ragas_loader({}))

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
            "ragas": lambda **_: RagasEvaluator(settings=_make_test_settings(), ragas_loader=_make_fake_ragas_loader({})),
        }
    )

    evaluator = EvaluatorFactory.create({"evaluation": {"provider": "ragas"}})

    assert isinstance(evaluator, RagasEvaluator)


def test_ragas_evaluator_requires_real_llm_api_key() -> None:
    """
    Given:
        一个没有 `llm.api_key` 的真实 RagasEvaluator。
    When:
        调用 `evaluate(samples)`。
    Then:
        应 fail-fast 抛出可读 `ValueError`，
        防止用户误以为 Ragas 已经真实启用但实际没有任何 LLM 可调用。
    """
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    profiles = {name: dict(value) for name, value in settings.llm.profiles.items()}
    selected_profile = settings.evaluation.ragas.llm_profile
    if not selected_profile:
        selected_profile = settings.llm.profile
    profiles.setdefault(selected_profile, {})
    # 这里必须清空“当前评估实际选中的 profile”，否则测试会误清空一个未被使用的历史 profile，
    # 导致 Ragas 仍然能读到真实 key，进而错误地跑到外部后端。
    profiles[selected_profile]["api_key"] = ""
    evaluator = RagasEvaluator(
        settings=replace(settings, llm=replace(settings.llm, api_key="", profiles=profiles))
    )

    with pytest.raises(ValueError, match="llm.api_key"):
        evaluator.evaluate(
            [
                {
                    "query": "如何配置 Azure OpenAI？",
                    "retrieved_chunks": ["Azure OpenAI setup guide"],
                    "generated_answer": "需要配置 endpoint 和 key。",
                    "ground_truth": "先配置 endpoint，再配置 key。",
                }
            ]
        )


def test_extract_json_object_ignores_reasoning_trace() -> None:
    """
    Given:
        一个 reasoning 模型常见输出，正文先包含 `<think>...</think>`，
        后面才是 Ragas 需要的 JSON 对象。

    When:
        调用 `_extract_json_object(text)`。

    Then:
        应只返回可被 JSON 解析的对象字符串，
        证明项目包装器能处理 MiniMax/Qwen 这类模型的思考过程前缀。
    """
    payload = _extract_json_object(
        '<think>分析过程</think>\n\n{"question": "What is RAG?", "noncommittal": 0}\nextra'
    )

    assert payload == '{"question": "What is RAG?", "noncommittal": 0}'


def test_ragas_embedding_compat_adds_legacy_embed_query() -> None:
    """
    Given:
        一个只实现 Ragas 新版 `embed_text/embed_texts` 接口的 embedding provider。

    When:
        用 `_RagasEmbeddingCompat` 包装后调用旧接口 `embed_query/embed_documents`。

    Then:
        包装器应把旧接口转发到新版接口，
        以兼容 Ragas 0.4.3 中仍调用 `embed_query` 的旧指标实现。
    """

    class _ModernEmbedding:
        def embed_text(self, text: str) -> list[float]:
            return [float(len(text))]

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[float(len(text))] for text in texts]

    compat = _RagasEmbeddingCompat(_ModernEmbedding())

    assert compat.embed_query("abc") == [3.0]
    assert compat.embed_documents(["a", "abcd"]) == [[1.0], [4.0]]


def test_project_ragas_llm_reports_truncated_empty_content_clearly() -> None:
    """
    Given:
        一个 OpenAI-compatible completion 返回空 content，且 `finish_reason=length`，
        表示模型在结构化输出完成前就被截断了。
    When:
        调用 `_complete(...)`。
    Then:
        应抛出带 “truncated” 语义的可读错误，
        让上层第二轮修复提示能够针对“输出被截断”而不是“普通空响应”做补救。
    """

    class _FakeCompletions:
        def create(self, **kwargs: Any) -> Any:
            _ = kwargs
            choice = type(
                "_Choice",
                (),
                {
                    "message": type("_Message", (), {"content": ""})(),
                    "finish_reason": "length",
                },
            )()
            return type("_Completion", (), {"choices": [choice]})()

    class _FakeChat:
        def __init__(self) -> None:
            self.completions = _FakeCompletions()

    fake_client = type("_Client", (), {"chat": _FakeChat()})()
    llm = _ProjectRagasLLM(
        instructor_base_cls=_FakeInstructorBase,
        client=fake_client,
        model="deepseek-v4-flash",
        max_tokens=1536,
    )

    with pytest.raises(ValueError, match="truncated"):
        llm._complete([{"role": "user", "content": "q"}])


def test_ragas_evaluator_normalizes_evaluation_result_repr_dict() -> None:
    """
    Given:
        Ragas `evaluate()` 返回类似 `EvaluationResult` 的对象，
        指标均值保存在 `_repr_dict` 中。

    When:
        调用 `_normalize_metrics(raw_result)`。

    Then:
        适配层应能提取 faithfulness / answer_relevancy / context_precision，
        避免真实 Ragas 已完成但结果对象不能序列化。
    """

    class _FakeEvaluationResult:
        _repr_dict = {
            "faithfulness": 0.5,
            "answer_relevancy": 0.25,
            "context_precision": 0.75,
        }

    metrics = RagasEvaluator._normalize_metrics(_FakeEvaluationResult())

    assert metrics["faithfulness"] == pytest.approx(0.5)
    assert metrics["answer_relevancy"] == pytest.approx(0.25)
    assert metrics["context_precision"] == pytest.approx(0.75)
