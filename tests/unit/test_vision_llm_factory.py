"""Vision LLM 工厂与抽象接口测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import load_settings
from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse
from libs.llm.dashscope_vision_llm import DashScopeVisionLLM
from libs.llm.llm_factory import LLMFactory
from libs.llm.openai_vision_llm import OpenAIVisionLLM


class _FakeVisionLLM(BaseVisionLLM):
    """用于验证 Vision 工厂分流行为的测试桩。"""

    def __init__(self, model: str = "", max_image_size: int = 2048) -> None:
        self.model = model
        self.max_image_size = max_image_size
        self.last_text = ""
        self.last_image_input: str | bytes | None = None

    def chat_with_image(
        self,
        text: str,
        image_path: str | bytes,
        trace: Any | None = None,
    ) -> ChatResponse:
        self.last_text = text
        self.last_image_input = self.preprocess_image_input(image_path)
        return ChatResponse(content=f"fake-vision:{self.model}", metadata={"trace": trace})


@pytest.fixture()
def isolated_vision_registry() -> dict[str, object]:
    """隔离 Vision 注册表，避免测试间共享状态。"""
    snapshot = dict(LLMFactory._vision_registry)
    built_snapshot = LLMFactory._vision_builtin_loaded
    LLMFactory._vision_registry.clear()
    LLMFactory._vision_builtin_loaded = False
    try:
        yield snapshot
    finally:
        LLMFactory._vision_registry.clear()
        LLMFactory._vision_registry.update(snapshot)
        LLMFactory._vision_builtin_loaded = built_snapshot


def test_base_vision_llm_preprocess_hook_default_passthrough() -> None:
    """
    Given:
        一个实现了 `BaseVisionLLM` 的测试桩实例。

    When:
        调用默认 `preprocess_image_input` 处理 bytes 图像输入。

    Then:
        返回值应与原输入一致，证明基础抽象已预留扩展点且默认无副作用。
    """

    class _PassthroughVision(BaseVisionLLM):
        def chat_with_image(self, text: str, image_path: str | bytes, trace: Any | None = None) -> ChatResponse:
            return ChatResponse(content=text, metadata={})

    model = _PassthroughVision()
    raw = b"image-bytes"

    assert model.preprocess_image_input(raw) == raw


def test_factory_routes_registered_vision_provider(isolated_vision_registry: dict[str, object]) -> None:
    """
    Given:
        注册一个 fake vision provider，并在 settings 中指定 `vision_llm.provider=fake_vision`。

    When:
        调用 `LLMFactory.create_vision_llm(settings)` 并执行 `chat_with_image`。

    Then:
        - 工厂应路由到 `_FakeVisionLLM`；
        - provider 参数（model/max_image_size）应正确透传；
        - 输出类型为 `ChatResponse`。
    """
    LLMFactory.register_vision(
        "fake_vision",
        lambda model="", max_image_size=2048, **_: _FakeVisionLLM(
            model=model,
            max_image_size=int(max_image_size),
        ),
    )

    settings = {
        "vision_llm": {
            "provider": "fake_vision",
            "model": "vision-demo",
            "max_image_size": 1024,
        }
    }

    client = LLMFactory.create_vision_llm(settings)
    result = client.chat_with_image("describe", "image.png", trace={"trace_id": "t1"})

    assert isinstance(client, _FakeVisionLLM)
    assert client.model == "vision-demo"
    assert client.max_image_size == 1024
    assert isinstance(result, ChatResponse)
    assert result.content == "fake-vision:vision-demo"


def test_factory_missing_vision_provider_path_raises_readable_error(
    isolated_vision_registry: dict[str, object],
) -> None:
    """
    Given:
        settings 中缺失 `vision_llm.provider`。

    When:
        调用 `LLMFactory.create_vision_llm`。

    Then:
        抛出 `ValueError`，并包含明确字段路径 `vision_llm.provider`。
    """
    with pytest.raises(ValueError, match="vision_llm.provider"):
        LLMFactory.create_vision_llm({"vision_llm": {"model": "x"}})


def test_factory_unknown_vision_provider_raises(isolated_vision_registry: dict[str, object]) -> None:
    """
    Given:
        settings 指定未注册的 `vision_llm.provider`。

    When:
        调用 `LLMFactory.create_vision_llm`。

    Then:
        抛出可读错误，明确提示 unknown provider 与可用列表。
    """
    settings = {"vision_llm": {"provider": "unknown_vision", "model": "x"}}

    with pytest.raises(ValueError, match="Unknown vision llm provider: unknown_vision"):
        LLMFactory.create_vision_llm(settings)


def test_factory_can_create_vision_llm_from_loaded_settings_object() -> None:
    """
    Given:
        通过 `load_settings(config/settings.yaml)` 得到的强类型 Settings 对象。

    When:
        调用 `LLMFactory.create_vision_llm(settings)`。

    Then:
        工厂能从 Settings.vision_llm 读取 provider/model/base_url/api_key，
        并创建与当前 profile 对应的 Vision 客户端实现。
    """
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    client = LLMFactory.create_vision_llm(settings)

    if settings.vision_llm.provider == "dashscope":
        assert isinstance(client, DashScopeVisionLLM)
    elif settings.vision_llm.provider == "openai":
        assert isinstance(client, OpenAIVisionLLM)
    else:
        pytest.fail(f"unexpected vision provider in config/settings.yaml: {settings.vision_llm.provider}")

    assert client.provider_name == settings.vision_llm.provider
    assert client.model == settings.vision_llm.model
    assert client.base_url == settings.vision_llm.base_url
    assert client.api_key == settings.vision_llm.api_key


def test_factory_can_create_openai_compatible_vision_llm() -> None:
    """
    Given:
        `vision_llm.provider=openai` 的配置，base_url 指向 OpenAI-compatible 多模态端点。

    When:
        调用 `LLMFactory.create_vision_llm(settings)`。

    Then:
        返回 `OpenAIVisionLLM`，证明 Gemini 这类 OpenAI-compatible Vision 端点可复用同一实现。
    """
    settings = {
        "vision_llm": {
            "provider": "openai",
            "model": "gemini-2.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "api_key": "gemini-key",
        }
    }

    client = LLMFactory.create_vision_llm(settings)

    assert isinstance(client, OpenAIVisionLLM)
    assert client.provider_name == "openai"
    assert client.model == "gemini-2.5-flash"
    assert client.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_factory_passes_proxy_to_openai_compatible_vision_llm() -> None:
    """当 `vision_llm.proxy` 存在时，工厂应把代理地址透传到 Vision 客户端实例。"""
    settings = {
        "vision_llm": {
            "provider": "openai",
            "model": "gemini-2.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "api_key": "gemini-key",
            "proxy": "http://127.0.0.1:10809",
        }
    }

    client = LLMFactory.create_vision_llm(settings)

    assert isinstance(client, OpenAIVisionLLM)
    assert client.proxy == "http://127.0.0.1:10809"
