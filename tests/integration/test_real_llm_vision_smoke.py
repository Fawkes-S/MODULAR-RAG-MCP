"""真实 LLM / Vision LLM 冒烟测试（可选执行）。

执行门槛：
- 仅当环境变量 `RUN_REAL_LLM_TESTS=1` 时运行；
- 需要 `config/settings.yaml` 内配置真实可用的 API key/base_url/model。

用途：
- 验证“配置 -> load_settings -> LLMFactory -> 实际远端调用”链路可打通。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from pprint import pprint

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.llm]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import load_settings
from libs.llm.llm_factory import LLMFactory


def _require_real_tests_enabled() -> None:
    """避免在日常 `pytest` 中意外触发真实 API 调用。"""
    if os.getenv("RUN_REAL_LLM_TESTS", "").strip().lower() not in {"1", "true", "yes"}:
        pytest.skip("Set RUN_REAL_LLM_TESTS=1 to run real provider smoke tests")


def _has_real_key(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    # 常见占位符场景：YOUR_KEY / <...> / ***
    placeholders = ["your_", "<", ">", "***", "dummy", "example"]
    lowered = text.lower()
    return not any(token in lowered for token in placeholders)


def test_real_text_llm_chat_smoke() -> None:
    """
    Given:
        settings.yaml 中已配置可用的文本 LLM（OpenAI-compatible）。

    When:
        `load_settings -> LLMFactory.create -> chat()`。

    Then:
        返回非空字符串，说明真实调用链路可用。
    """
    _require_real_tests_enabled()
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    if not _has_real_key(settings.llm.api_key):
        pytest.skip("llm.api_key is empty or placeholder")

    client = LLMFactory.create(settings)
    reply = client.chat([
        {
            "role": "user",
            "content": "请回复两个英文大写字母OK，不要输出其他内容。",
        }
    ])
    pprint(" reply: "+ reply)

    assert isinstance(reply, str)
    assert reply.strip()


def test_real_vision_llm_chat_with_image_smoke() -> None:
    """
    Given:
        settings.yaml 中已配置可用的 Vision LLM，且存在测试图片。

    When:
        `load_settings -> LLMFactory.create_vision_llm -> chat_with_image()`。

    Then:
        返回非空文本，说明 Vision 真实调用链路可用。
    """
    _require_real_tests_enabled()
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    if not settings.vision_llm.enabled:
        pytest.skip("vision_llm.enabled=false")
    if not _has_real_key(settings.vision_llm.api_key):
        pytest.skip("vision_llm.api_key is empty or placeholder")

    image_path = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents" / "test_vision_llm.jpg"
    if not image_path.exists():
        pytest.skip(f"fixture image not found: {image_path}")

    client = LLMFactory.create_vision_llm(settings)
    response = client.chat_with_image(
        text="请用一句话描述这张图片的主要内容。",
        image_path=str(image_path),
    )
    pprint(" response: " + response.content.strip())

    assert isinstance(response.content, str)
    assert response.content.strip()

'''
-s：不捕获标准输出，print/pprint 会直接显示在控制台。
-q：精简输出（quiet），日志更短。
-rs：显示被 skip 的简要原因。
'''
