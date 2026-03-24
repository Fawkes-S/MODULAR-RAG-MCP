"""OllamaLLM 单元测试（mock HTTP）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.llm.llm_factory import LLMFactory
from libs.llm.ollama_llm import OllamaLLM


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，保证每个测试用例互不污染。"""
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


def test_factory_can_create_ollama_provider(isolated_registry: dict[str, object]) -> None:
    """验证 provider=ollama 时，工厂能正确创建 OllamaLLM 实例。"""
    client = LLMFactory.create(
        {
            "llm": {
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "base_url": "http://localhost:11434",
                "transport": lambda *_: {"message": {"content": "ok"}},
            }
        }
    )

    assert isinstance(client, OllamaLLM)


def test_chat_success_with_mock_transport(isolated_registry: dict[str, object]) -> None:
    """验证在 mock transport 下，chat 能正常返回解析后的 assistant 文本。"""
    captured: dict[str, Any] = {}

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"message": {"role": "assistant", "content": "hello from ollama"}}

    client = LLMFactory.create(
        {
            "llm": {
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "base_url": "http://localhost:11434",
                "timeout": 12,
                "transport": transport,
            }
        }
    )

    text = client.chat([{"role": "user", "content": "hi"}])

    assert text == "hello from ollama"
    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["model"] == "qwen2.5:7b"
    assert captured["payload"]["stream"] is False
    assert captured["headers"]["Content-Type"] == "application/json"


def test_chat_validation_error_is_readable(isolated_registry: dict[str, object]) -> None:
    """验证 messages 输入 shape 非法时，报错包含 provider 与 ValidationError。"""
    client = LLMFactory.create(
        {
            "llm": {
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "transport": lambda *_: {"message": {"content": "ok"}},
            }
        }
    )

    with pytest.raises(ValueError, match=r"\[ollama\].*ValidationError"):
        client.chat("bad-input")  # type: ignore[arg-type]


def test_connection_error_is_readable_and_not_leak_sensitive_config(isolated_registry: dict[str, object]) -> None:
    """验证连接失败时错误可读，且不会泄露 base_url 等敏感配置细节。"""

    def broken_transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        raise TimeoutError("connect timeout")

    base_url = "http://127.0.0.1:11434/internal-token-should-not-leak"
    client = LLMFactory.create(
        {
            "llm": {
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "base_url": base_url,
                "transport": broken_transport,
            }
        }
    )

    with pytest.raises(RuntimeError, match=r"\[ollama\].*RequestError.*TimeoutError") as exc_info:
        client.chat([{"role": "user", "content": "hi"}])

    # 错误字符串里不应出现完整 base_url，避免泄露内部地址/路径。
    assert base_url not in str(exc_info.value)
