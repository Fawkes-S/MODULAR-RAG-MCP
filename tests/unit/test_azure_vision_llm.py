"""AzureVisionLLM 单元测试（全 mock HTTP）。"""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.llm.azure_vision_llm import AzureVisionLLM
from libs.llm.base_vision_llm import ChatResponse
from libs.llm.llm_factory import LLMFactory


def test_azure_vision_llm_supports_local_image_path() -> None:
    """
    Given:
        一个临时本地图片文件路径，和可观察请求体的 mock transport。

    When:
        调用 `AzureVisionLLM.chat_with_image()` 发送图文请求。

    Then:
        - 返回 `ChatResponse` 且内容正确；
        - 请求 URL 包含 Azure deployment 路径与 api-version；
        - 消息体使用 `image_url` data-uri 发送图片。
    """
    image_file = PROJECT_ROOT / "data" / "db" / "vision_test_img.bin"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_bytes(b"fake-image-bytes")

    captured: dict[str, Any] = {}

    def _transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"choices": [{"message": {"content": "vision-ok"}}]}

    client = AzureVisionLLM(
        endpoint="https://example.openai.azure.com",
        deployment_name="gpt-4o",
        api_key="k",
        transport=_transport,
    )

    try:
        result = client.chat_with_image(text="describe this", image_path=str(image_file))

        assert isinstance(result, ChatResponse)
        assert result.content == "vision-ok"
        assert "/openai/deployments/gpt-4o/chat/completions" in captured["url"]
        img_url = captured["payload"]["messages"][0]["content"][1]["image_url"]["url"]
        assert img_url.startswith("data:image/png;base64,")
    finally:
        if image_file.exists():
            image_file.unlink()


def test_azure_vision_llm_supports_base64_input() -> None:
    """
    Given:
        一段 base64 编码图片文本输入（非文件路径）。

    When:
        调用 `chat_with_image`。

    Then:
        能成功解析 base64 并完成请求，不抛输入校验错误。
    """
    b64 = base64.b64encode(b"img-b64-bytes").decode("utf-8")

    client = AzureVisionLLM(
        endpoint="https://example.openai.azure.com",
        deployment_name="gpt-4o",
        transport=lambda *_: {"choices": [{"message": {"content": "ok"}}]},
    )

    result = client.chat_with_image(text="what is this", image_path=b64)

    assert result.content == "ok"


def test_azure_vision_llm_calls_compress_hook_for_large_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Given:
        一个可观测的压缩函数替身（通过 monkeypatch 注入）。

    When:
        调用 `chat_with_image` 处理 bytes 图片输入。

    Then:
        压缩钩子会被调用，且发送到 API 的图片内容为压缩后结果。
    """
    called = {"ok": False}

    def _fake_compress(self: AzureVisionLLM, raw: bytes) -> bytes:
        called["ok"] = True
        assert raw == b"raw-bytes"
        return b"compressed-bytes"

    monkeypatch.setattr(AzureVisionLLM, "_compress_image_if_needed", _fake_compress)

    captured: dict[str, Any] = {}

    def _transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "ok"}}]}

    client = AzureVisionLLM(
        endpoint="https://example.openai.azure.com",
        deployment_name="gpt-4o",
        transport=_transport,
    )

    client.chat_with_image(text="compress please", image_path=b"raw-bytes")

    assert called["ok"] is True
    sent_url = captured["payload"]["messages"][0]["content"][1]["image_url"]["url"]
    assert base64.b64decode(sent_url.split(",", 1)[1]) == b"compressed-bytes"


def test_azure_vision_llm_timeout_raises_readable_error() -> None:
    """
    Given:
        一个会抛 TimeoutError 的 transport（模拟网络超时）。

    When:
        调用 `chat_with_image`。

    Then:
        抛出 `RuntimeError`，错误文本包含 `RequestError` 与 `TimeoutError`。
    """

    def _transport(*_: Any) -> dict[str, Any]:
        raise TimeoutError("network timeout")

    client = AzureVisionLLM(
        endpoint="https://example.openai.azure.com",
        deployment_name="gpt-4o",
        transport=_transport,
    )

    with pytest.raises(RuntimeError, match=r"RequestError.*TimeoutError"):
        client.chat_with_image(text="q", image_path=b"img")


def test_azure_vision_llm_auth_error_contains_azure_error_code() -> None:
    """
    Given:
        transport 返回 Azure 标准错误 payload（含 `error.code`）。

    When:
        调用 `chat_with_image`。

    Then:
        抛出 `RuntimeError`，错误信息包含 Azure 错误码，便于快速定位鉴权问题。
    """

    def _transport(*_: Any) -> dict[str, Any]:
        return {"error": {"code": "401", "message": "Unauthorized"}}

    client = AzureVisionLLM(
        endpoint="https://example.openai.azure.com",
        deployment_name="gpt-4o",
        transport=_transport,
    )

    with pytest.raises(RuntimeError, match=r"AzureAPIError\(code=401\)"):
        client.chat_with_image(text="q", image_path=b"img")


def test_factory_can_create_azure_vision_llm() -> None:
    """
    Given:
        `vision_llm.provider=azure` 的配置。

    When:
        调用 `LLMFactory.create_vision_llm(settings)`。

    Then:
        返回 `AzureVisionLLM` 实例，证明 B9 的工厂路由已接通。
    """
    settings = {
        "vision_llm": {
            "provider": "azure",
            "endpoint": "https://example.openai.azure.com",
            "deployment_name": "gpt-4o",
        }
    }

    client = LLMFactory.create_vision_llm(settings)

    assert isinstance(client, AzureVisionLLM)

def test_azure_vision_llm_retries_timeout_then_succeeds() -> None:
    """
    Given:
        transport 首次抛 TimeoutError，第二次返回正常响应。
    When:
        调用 `chat_with_image`。
    Then:
        客户端应自动重试并成功返回内容。
    """
    calls = {"count": 0}

    def _transport(*_: Any) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("vision timeout")
        return {"choices": [{"message": {"content": "azure-vision-recovered"}}]}

    client = AzureVisionLLM(
        endpoint="https://example.openai.azure.com",
        deployment_name="gpt-4o",
        transport=_transport,
        max_retries=2,
        retry_backoff_seconds=0.0,
    )

    result = client.chat_with_image(text="q", image_path=b"img")

    assert result.content == "azure-vision-recovered"
    assert calls["count"] == 2
