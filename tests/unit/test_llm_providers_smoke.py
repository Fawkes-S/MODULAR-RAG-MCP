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
