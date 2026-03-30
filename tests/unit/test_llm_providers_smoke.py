"""OpenAI-compatible LLM providers 冒烟测试（全 mock HTTP）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.llm.azure_llm import AzureLLM
from libs.llm.deepseek_llm import DeepSeekLLM
from libs.llm.llm_factory import LLMFactory
from libs.llm.openai_llm import OpenAILLM


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，保证测试可重复执行且不依赖外部状态。"""
    snapshot = dict(LLMFactory._registry)
    snapshot_builtin = LLMFactory._builtin_loaded
    LLMFactory._registry.clear()
    LLMFactory._builtin_loaded = False
    try:
        yield snapshot
    finally:
        LLMFactory._registry.clear()
        LLMFactory._registry.update(snapshot)
        LLMFactory._builtin_loaded = snapshot_builtin


def _ok_transport(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    return {"choices": [{"message": {"content": f"ok:{payload.get('model', '')}"}}]}


def test_factory_routes_openai_azure_deepseek(isolated_registry: dict[str, object]) -> None:
    """验证工厂可按 provider 正确路由到 openai/azure/deepseek 实现。"""
    openai_client = LLMFactory.create(
        {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "k",
                "transport": _ok_transport,
            }
        }
    )
    azure_client = LLMFactory.create(
        {
            "llm": {
                "provider": "azure",
                "model": "gpt-4o-mini",
                "endpoint": "https://example.openai.azure.com",
                "deployment_name": "gpt4o-mini",
                "api_key": "k",
                "transport": _ok_transport,
            }
        }
    )
    deepseek_client = LLMFactory.create(
        {
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "k",
                "transport": _ok_transport,
            }
        }
    )

    assert isinstance(openai_client, OpenAILLM)
    assert isinstance(azure_client, AzureLLM)
    assert isinstance(deepseek_client, DeepSeekLLM)


def test_chat_validation_error_contains_provider_and_error_type(isolated_registry: dict[str, object]) -> None:
    """验证 `chat(messages)` 输入 shape 校验错误可读，且包含 provider 与错误类型。"""
    client = LLMFactory.create(
        {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "transport": _ok_transport,
            }
        }
    )

    with pytest.raises(ValueError, match=r"\[openai\].*ValidationError"):
        client.chat("not-a-list")  # type: ignore[arg-type]


def test_azure_chat_uses_mock_http_and_returns_content(isolated_registry: dict[str, object]) -> None:
    """验证 Azure 客户端在 mock 传输下可完成请求并解析响应文本，不触网。"""
    captured: dict[str, Any] = {}

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"choices": [{"message": {"content": "azure-ok"}}]}

    client = LLMFactory.create(
        {
            "llm": {
                "provider": "azure",
                "model": "gpt-4o-mini",
                "endpoint": "https://example.openai.azure.com",
                "deployment_name": "dep-1",
                "api_key": "k",
                "transport": transport,
            }
        }
    )

    text = client.chat([{"role": "user", "content": "hello"}])

    assert text == "azure-ok"
    assert "dep-1" in captured["url"]
    assert "api-version=" in captured["url"]
    assert captured["headers"]["api-key"] == "k"


def test_request_error_contains_provider_and_error_type(isolated_registry: dict[str, object]) -> None:
    """验证网络异常会被包装为可读错误，避免底层异常直接泄漏到业务层。"""

    def broken_transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        raise TimeoutError("network timeout")

    client = LLMFactory.create(
        {
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "transport": broken_transport,
            }
        }
    )

    with pytest.raises(RuntimeError, match=r"\[deepseek\].*RequestError.*TimeoutError"):
        client.chat([{"role": "user", "content": "hi"}])

def test_openai_retries_timeout_then_succeeds(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        首次请求抛出 TimeoutError，第二次返回正常响应的 mock transport。
    When:
        调用 OpenAI provider 的 `chat()`。
    Then:
        客户端应自动重试并成功返回内容，且 transport 调用次数为 2。
    """
    calls = {"count": 0}

    def flaky_transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("transient timeout")
        return {"choices": [{"message": {"content": "openai-recovered"}}]}

    client = LLMFactory.create(
        {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "transport": flaky_transport,
                "max_retries": 2,
                "retry_backoff_seconds": 0.0,
            }
        }
    )

    text = client.chat([{"role": "user", "content": "hi"}])

    assert text == "openai-recovered"
    assert calls["count"] == 2


def test_openai_non_retryable_error_does_not_retry(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        transport 抛出携带 `code=400` 的异常（不可重试错误）。
    When:
        调用 OpenAI provider 的 `chat()`。
    Then:
        不应重试，请求只发一次并直接失败。
    """

    class _BadRequestError(Exception):
        code = 400

    calls = {"count": 0}

    def broken_transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        calls["count"] += 1
        raise _BadRequestError("bad request")

    client = LLMFactory.create(
        {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "transport": broken_transport,
                "max_retries": 3,
                "retry_backoff_seconds": 0.0,
            }
        }
    )

    with pytest.raises(RuntimeError, match=r"\[openai\].*RequestError"):
        client.chat([{"role": "user", "content": "hi"}])

    assert calls["count"] == 1
