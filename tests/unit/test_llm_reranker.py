"""LLMReranker 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.reranker.llm_reranker import LLMReranker, RerankFallbackSignal
from libs.reranker.reranker_factory import RerankerFactory


class _FakeLLM:
    """可注入返回值/异常的 LLM 测试桩。"""

    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.last_messages: list[dict[str, Any]] | None = None

    def chat(self, messages: list[dict[str, Any]]) -> str:
        self.last_messages = messages
        if self.error is not None:
            raise self.error
        return self.response


def test_llm_reranker_reranks_by_ranked_ids() -> None:
    """
    Given:
        一个可控 FakeLLM，返回结构化 JSON：{"ranked_ids": ["c2", "c1"]}；
        以及包含 query + candidates 的模板 prompt。

    When:
        调用 `LLMReranker.rerank()` 对候选列表进行重排。

    Then:
        - 返回顺序应与 `ranked_ids` 一致；
        - 未在 ranked_ids 中出现的候选保持原顺序并追加在末尾；
        - 发送给 LLM 的消息中包含 query 文本，便于排查 prompt 拼装正确性。
    """
    fake_llm = _FakeLLM(response='{"ranked_ids": ["c2", "c1"]}')
    reranker = LLMReranker(
        llm=fake_llm,
        prompt_template="请根据query重排。query={query}\ncandidates={candidates}",
    )

    result = reranker.rerank(
        query="什么是RAG",
        candidates=[
            {"id": "c1", "text": "第一段", "score": 0.9},
            {"id": "c2", "text": "第二段", "score": 0.7},
            {"id": "c3", "text": "第三段", "score": 0.6},
        ],
    )

    assert [item["id"] for item in result] == ["c2", "c1", "c3"]
    assert fake_llm.last_messages is not None
    assert "什么是RAG" in fake_llm.last_messages[0]["content"]


def test_llm_reranker_invalid_schema_raises_readable_error() -> None:
    """
    Given:
        FakeLLM 返回不符合契约的 JSON（缺失 `ranked_ids` 字段）。

    When:
        调用 `LLMReranker.rerank()`。

    Then:
        抛出 `ValueError`，且错误信息明确指向 `ResponseSchemaError`，
        便于调用方区分“模型输出结构问题”和“网络请求失败”。
    """
    fake_llm = _FakeLLM(response='{"ids": ["c1"]}')
    reranker = LLMReranker(llm=fake_llm, prompt_template="x")

    with pytest.raises(ValueError, match="ResponseSchemaError"):
        reranker.rerank(query="q", candidates=[{"id": "c1", "text": "t"}])


def test_llm_reranker_failure_raises_fallback_signal() -> None:
    """
    Given:
        FakeLLM 在 `chat()` 阶段抛出连接异常（模拟超时/网络错误）。

    When:
        调用 `LLMReranker.rerank()`。

    Then:
        抛出 `RerankFallbackSignal`，作为“上层可回退”的显式信号，
        并在错误信息中包含原始异常类型，方便日志排障。
    """
    fake_llm = _FakeLLM(error=TimeoutError("request timeout"))
    reranker = LLMReranker(llm=fake_llm, prompt_template="x")

    with pytest.raises(RerankFallbackSignal, match="FallbackSignal"):
        reranker.rerank(query="q", candidates=[{"id": "c1", "text": "t"}])


def test_reranker_factory_can_create_llm_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Given:
        工厂配置 `rerank.provider=llm`，并提供项目内临时 `prompt_path`；
        同时 monkeypatch `LLMFactory.create` 返回可控 FakeLLM。

    When:
        调用 `RerankerFactory.create(settings)` 创建实例并执行 rerank。

    Then:
        - 工厂返回 `LLMReranker`；
        - 实例可读取 prompt 文件并完成结构化重排；
        - 证明 `backend=llm` 路由与配置读取链路可用。
    """
    prompt_file = PROJECT_ROOT / "data" / "db" / "test_rerank_prompt.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("你是重排助手。query={query}\ncandidates={candidates}", encoding="utf-8")

    fake_llm = _FakeLLM(response='{"ranked_ids": ["x2", "x1"]}')

    def _fake_create(_settings: Any) -> _FakeLLM:
        return fake_llm

    monkeypatch.setattr("libs.reranker.llm_reranker.LLMFactory.create", _fake_create)

    settings = {
        "llm": {"provider": "openai", "model": "gpt-test"},
        "rerank": {
            "provider": "llm",
            "prompt_path": str(prompt_file),
        },
    }

    reranker = RerankerFactory.create(settings)

    try:
        result = reranker.rerank(
            query="test",
            candidates=[
                {"id": "x1", "text": "alpha"},
                {"id": "x2", "text": "beta"},
            ],
        )

        assert isinstance(reranker, LLMReranker)
        assert [item["id"] for item in result] == ["x2", "x1"]
    finally:
        if prompt_file.exists():
            prompt_file.unlink()


def test_llm_reranker_uses_default_prompt_when_file_missing() -> None:
    """
    Given:
        未提供 `prompt_template`，且 `prompt_path` 指向不存在的文件。

    When:
        初始化 `LLMReranker` 并执行 `rerank()`。

    Then:
        应回退到内置默认模板并正常完成重排，不因文件缺失报错。
    """
    fake_llm = _FakeLLM(response='{"ranked_ids": ["c1"]}')
    reranker = LLMReranker(llm=fake_llm, prompt_path="config/prompts/does_not_exist_for_test.txt")

    result = reranker.rerank(query="q", candidates=[{"id": "c1", "text": "t"}])

    assert [item["id"] for item in result] == ["c1"]
    assert fake_llm.last_messages is not None
    assert "ranked_ids" in fake_llm.last_messages[0]["content"]
