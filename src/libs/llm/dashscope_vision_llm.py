"""DashScope Vision LLM provider implementation.

实现目标：
- 通过阿里云百炼（DashScope）OpenAI-compatible 接口执行图像理解；
- 支持图片路径与 base64 两种输入；
- 提供图片压缩扩展点（默认 max_image_size=2048）；
- 失败时抛出可读错误并包含 provider 与错误类型/状态码。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Callable
from urllib import request

from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse
from libs.llm.retry_policy import (
    RetryPolicy,
    RetryableStatusError,
    execute_with_retry,
    summarize_exception,
)

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class DashScopeVisionLLM(BaseVisionLLM):
    """DashScope Vision 客户端实现（qwen3.5-plus 默认）。"""

    provider_name = "dashscope"

    def __init__(
        self,
        model: str = "qwen3.5-plus",
        api_key: str = "",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        max_image_size: int = 2048,
        timeout: float = 30.0,
        transport: TransportFn | None = None,
        retry_policy: RetryPolicy | None = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.25,
        retry_backoff_multiplier: float = 2.0,
        retry_max_backoff_seconds: float = 2.0,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_image_size = int(max_image_size)
        self.timeout = float(timeout)
        self._transport = transport or self._default_transport

        self.retry_policy = retry_policy or RetryPolicy(
            max_retries=max_retries,
            initial_backoff_seconds=retry_backoff_seconds,
            backoff_multiplier=retry_backoff_multiplier,
            max_backoff_seconds=retry_max_backoff_seconds,
        )

    def chat_with_image(
        self,
        text: str,
        image_path: str | bytes,
        trace: Any | None = None,
    ) -> ChatResponse:
        """执行图文对话并返回结构化响应。"""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("[dashscope-vision] ValidationError: text must be non-empty string")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("[dashscope-vision] ValidationError: model must be non-empty string")

        processed = self.preprocess_image_input(image_path)
        image_bytes = self._load_image_bytes(processed)
        image_bytes = self._compress_image_if_needed(image_bytes)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }
            ],
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        def _send_once() -> dict[str, Any]:
            data = self._transport(url, payload, headers, float(self.timeout))
            self._raise_if_error_payload(data)
            return data

        try:
            data = execute_with_retry(
                operation=_send_once,
                policy=self.retry_policy,
            )
        except Exception as exc:  # pragma: no cover
            # 401/403 这类业务错误直接透出，不包装成 RequestError。
            if isinstance(exc, RuntimeError) and "DashScopeAPIError" in str(exc):
                raise
            summary = summarize_exception(exc)
            suffix = f": {summary}" if summary else ""
            raise RuntimeError(f"[dashscope-vision] RequestError: {type(exc).__name__}{suffix}") from exc

        content = self._extract_content(data)
        return ChatResponse(content=content, metadata={"provider": "dashscope", "trace": trace})

    def _load_image_bytes(self, image_input: str | bytes) -> bytes:
        """加载图片字节：支持本地路径与 base64 文本。"""
        if isinstance(image_input, bytes):
            if not image_input:
                raise ValueError("[dashscope-vision] ValidationError: image bytes cannot be empty")
            return image_input

        if not isinstance(image_input, str) or not image_input.strip():
            raise ValueError("[dashscope-vision] ValidationError: image input must be non-empty path/base64")

        path = Path(image_input)
        if path.exists() and path.is_file():
            raw = path.read_bytes()
            if not raw:
                raise ValueError("[dashscope-vision] ValidationError: image file is empty")
            return raw

        text = image_input.strip()
        if text.startswith("data:") and "," in text:
            text = text.split(",", 1)[1]

        try:
            raw = base64.b64decode(text, validate=True)
        except Exception as exc:
            raise ValueError("[dashscope-vision] ValidationError: image input must be valid path or base64") from exc

        if not raw:
            raise ValueError("[dashscope-vision] ValidationError: decoded image bytes cannot be empty")
        return raw

    def _compress_image_if_needed(self, raw: bytes) -> bytes:
        """当图片尺寸超过阈值时执行压缩。"""
        if self.max_image_size <= 0:
            return raw

        try:
            from io import BytesIO

            from PIL import Image
        except Exception:
            return raw

        try:
            with Image.open(BytesIO(raw)) as img:
                width, height = img.size
                longest = max(width, height)
                if longest <= self.max_image_size:
                    return raw

                ratio = self.max_image_size / float(longest)
                new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
                resized = img.resize(new_size)
                out = BytesIO()
                resized.save(out, format="PNG")
                return out.getvalue()
        except Exception:
            # 输入并非可识别图片时，保持原字节，避免阻塞上层请求链路。
            return raw

    @staticmethod
    def _raise_if_error_payload(data: dict[str, Any]) -> None:
        """DashScope error payload 映射为可读异常。"""
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            code = err.get("code", "unknown")
            message = str(err.get("message", "unknown error"))

            status_code: int | None = None
            try:
                status_code = int(code)
            except Exception:
                status_code = None

            if status_code is not None and (status_code == 429 or status_code >= 500):
                raise RetryableStatusError(status_code=status_code, message=message)

            raise RuntimeError(f"[dashscope-vision] DashScopeAPIError(code={code}): {message}")

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        """提取 DashScope/OpenAI-compatible 响应文本内容。"""
        try:
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [str(x.get("text", "")) for x in content if isinstance(x, dict)]
                return "\n".join([t for t in texts if t])
            return str(content)
        except Exception as exc:
            raise ValueError("[dashscope-vision] ResponseShapeError: invalid vision response") from exc

    @staticmethod
    def _default_transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
