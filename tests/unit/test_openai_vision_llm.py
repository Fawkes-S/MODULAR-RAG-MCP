"""OpenAI-compatible Vision LLM 单元测试。"""

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

from libs.llm.base_vision_llm import ChatResponse
from libs.llm.openai_vision_llm import OpenAIVisionLLM


def test_openai_vision_llm_supports_local_image_path() -> None:
    """
    Given:
        一个本地图片文件和可控 transport。

    When:
        调用 `chat_with_image()`。

    Then:
        应走 OpenAI-compatible `/chat/completions` 接口，
        并返回结构化 `ChatResponse`。
    """
    image_file = PROJECT_ROOT / "data" / "db" / "openai_vision_test_img.bin"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_bytes(b"fake-image")

    captured: dict[str, Any] = {}

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"choices": [{"message": {"content": "openai-vision-ok"}}]}

    client = OpenAIVisionLLM(
        model="gemini-2.5-flash",
        api_key="key-123",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        transport=transport,
    )

    try:
        result = client.chat_with_image("describe image", str(image_file))

        assert isinstance(result, ChatResponse)
        assert result.content == "openai-vision-ok"
        assert captured["url"].endswith("/chat/completions")
        assert captured["headers"]["Authorization"] == "Bearer key-123"
    finally:
        if image_file.exists():
            image_file.unlink()


def test_openai_vision_llm_supports_base64_input() -> None:
    """
    Given:
        base64 编码图片输入。

    When:
        调用 `chat_with_image()`。

    Then:
        payload 中应包含 `data:image/png;base64,...` 形式的 `image_url`。
    """
    captured: dict[str, Any] = {}

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        _ = url, headers, timeout
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "ok"}}]}

    client = OpenAIVisionLLM(
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        transport=transport,
    )

    result = client.chat_with_image(
        "describe",
        base64.b64encode(b"vision-bytes").decode("utf-8"),
    )

    image_url = captured["payload"]["messages"][0]["content"][1]["image_url"]["url"]
    assert isinstance(result, ChatResponse)
    assert image_url.startswith("data:image/png;base64,")


def test_openai_vision_llm_invalid_response_raises_readable_error() -> None:
    """当响应缺少 `choices[0].message.content` 时，应抛出可读错误。"""

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        _ = url, payload, headers, timeout
        return {"unexpected": True}

    client = OpenAIVisionLLM(
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        transport=transport,
    )

    with pytest.raises(ValueError, match="ResponseShapeError"):
        client.chat_with_image("describe", base64.b64encode(b"vision-bytes").decode("utf-8"))
