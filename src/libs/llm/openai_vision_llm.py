"""OpenAI-compatible Vision LLM provider implementation.

实现目标：
- 通过 OpenAI-compatible chat completions 接口执行图像理解；
- 支持图片路径与 base64 两种输入；
- 兼容 Gemini / OpenAI / 其他支持 `image_url` 的兼容端点；
- 失败时抛出可读错误并包含 provider 与错误类型。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Callable
from urllib import request

from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse
from libs.llm.retry_policy import RetryPolicy, execute_with_retry, summarize_exception

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class OpenAIVisionLLM(BaseVisionLLM):
    """OpenAI-compatible Vision 客户端实现。"""

    provider_name = "openai"

    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        proxy: str = "",
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
        self.proxy = proxy
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
            raise ValueError("[openai-vision] ValidationError: text must be non-empty string")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("[openai-vision] ValidationError: model must be non-empty string")

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
        if self.proxy:
            # 仅在 transport 内部消费，不会实际发到远端。
            headers["__proxy__"] = self.proxy

        try:
            data = execute_with_retry(
                operation=lambda: self._transport(url, payload, headers, float(self.timeout)),
                policy=self.retry_policy,
            )
        except Exception as exc:  # pragma: no cover
            summary = summarize_exception(exc)
            suffix = f": {summary}" if summary else ""
            raise RuntimeError(f"[openai-vision] RequestError: {type(exc).__name__}{suffix}") from exc

        content = self._extract_content(data)
        return ChatResponse(content=content, metadata={"provider": "openai", "trace": trace})

    def _load_image_bytes(self, image_input: str | bytes) -> bytes:
        """加载图片字节：支持本地路径与 base64 文本。"""
        if isinstance(image_input, bytes):
            if not image_input:
                raise ValueError("[openai-vision] ValidationError: image bytes cannot be empty")
            return image_input

        if not isinstance(image_input, str) or not image_input.strip():
            raise ValueError("[openai-vision] ValidationError: image input must be non-empty path/base64")

        path = Path(image_input)
        if path.exists() and path.is_file():
            raw = path.read_bytes()
            if not raw:
                raise ValueError("[openai-vision] ValidationError: image file is empty")
            return raw

        text = image_input.strip()
        if text.startswith("data:") and "," in text:
            text = text.split(",", 1)[1]

        try:
            raw = base64.b64decode(text, validate=True)
        except Exception as exc:
            raise ValueError("[openai-vision] ValidationError: image input must be valid path or base64") from exc

        if not raw:
            raise ValueError("[openai-vision] ValidationError: decoded image bytes cannot be empty")
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
            return raw

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        """提取 OpenAI-compatible 响应文本内容。"""
        try:
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [str(x.get("text", "")) for x in content if isinstance(x, dict)]
                return "\n".join([t for t in texts if t])
            return str(content)
        except Exception as exc:
            raise ValueError("[openai-vision] ResponseShapeError: invalid vision response") from exc

    @staticmethod
    def _default_transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        proxy = headers.pop("__proxy__", "")
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, data=body, headers=headers, method="POST")
        opener = OpenAIVisionLLM._build_url_opener(proxy)
        with opener.open(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    @staticmethod
    def _build_url_opener(proxy: str):
        """按需构造 urllib opener，支持为 OpenAI-compatible Vision 请求显式指定代理。"""
        proxy_value = str(proxy or "").strip()
        if not proxy_value:
            return request.build_opener()

        handler = request.ProxyHandler(
            {
                "http": proxy_value,
                "https": proxy_value,
            }
        )
        return request.build_opener(handler)
