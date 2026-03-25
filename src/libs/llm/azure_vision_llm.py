"""Azure Vision LLM provider implementation.

实现目标：
- 通过 Azure OpenAI chat completions 接口执行图像理解；
- 支持图片路径与 base64 两种输入；
- 提供图片压缩扩展点（默认 max_image_size=2048）；
- 失败时抛出可读错误并包含 Azure 特有错误码。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Callable
from urllib import request

from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class AzureVisionLLM(BaseVisionLLM):
    """Azure OpenAI Vision 客户端实现。"""

    provider_name = "azure"

    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        endpoint: str = "",
        azure_endpoint: str = "",
        deployment_name: str = "",
        api_version: str = "2024-02-01",
        max_image_size: int = 2048,
        timeout: float = 30.0,
        transport: TransportFn | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint or azure_endpoint
        self.deployment_name = deployment_name or model
        self.api_version = api_version
        self.max_image_size = int(max_image_size)
        self.timeout = float(timeout)
        self._transport = transport or self._default_transport

    def chat_with_image(
        self,
        text: str,
        image_path: str | bytes,
        trace: Any | None = None,
    ) -> ChatResponse:
        """执行图文对话并返回结构化响应。"""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("[azure-vision] ValidationError: text must be non-empty string")
        if not self.endpoint.strip():
            raise ValueError("[azure-vision] ValidationError: endpoint must be non-empty string")
        if not self.deployment_name.strip():
            raise ValueError("[azure-vision] ValidationError: deployment_name must be non-empty string")

        processed = self.preprocess_image_input(image_path)
        image_bytes = self._load_image_bytes(processed)
        image_bytes = self._compress_image_if_needed(image_bytes)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }
            ]
        }

        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment_name}"
            f"/chat/completions?api-version={self.api_version}"
        )
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key

        try:
            data = self._transport(url, payload, headers, float(self.timeout))
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"[azure-vision] RequestError: {type(exc).__name__}: {exc}") from exc

        self._raise_if_error_payload(data)
        content = self._extract_content(data)
        return ChatResponse(content=content, metadata={"provider": "azure", "trace": trace})

    def _load_image_bytes(self, image_input: str | bytes) -> bytes:
        """加载图片字节：支持本地路径与 base64 文本。"""
        if isinstance(image_input, bytes):
            if not image_input:
                raise ValueError("[azure-vision] ValidationError: image bytes cannot be empty")
            return image_input

        if not isinstance(image_input, str) or not image_input.strip():
            raise ValueError("[azure-vision] ValidationError: image input must be non-empty path/base64")

        path = Path(image_input)
        if path.exists() and path.is_file():
            raw = path.read_bytes()
            if not raw:
                raise ValueError("[azure-vision] ValidationError: image file is empty")
            return raw

        text = image_input.strip()
        if text.startswith("data:") and "," in text:
            text = text.split(",", 1)[1]

        try:
            raw = base64.b64decode(text, validate=True)
        except Exception as exc:
            raise ValueError("[azure-vision] ValidationError: image input must be valid path or base64") from exc

        if not raw:
            raise ValueError("[azure-vision] ValidationError: decoded image bytes cannot be empty")
        return raw

    def _compress_image_if_needed(self, raw: bytes) -> bytes:
        """当图片尺寸超过阈值时执行压缩。

        默认实现使用 Pillow；若环境未安装 Pillow，则返回原图（保持可运行）。
        """
        if self.max_image_size <= 0:
            return raw

        try:
            from io import BytesIO

            from PIL import Image
        except Exception:
            return raw

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

    @staticmethod
    def _raise_if_error_payload(data: dict[str, Any]) -> None:
        """Azure error payload 映射为可读异常。"""
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            code = err.get("code", "unknown")
            message = err.get("message", "unknown error")
            raise RuntimeError(f"[azure-vision] AzureAPIError(code={code}): {message}")

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        """提取 Azure 响应文本内容。"""
        try:
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [str(x.get("text", "")) for x in content if isinstance(x, dict)]
                return "\n".join([t for t in texts if t])
            return str(content)
        except Exception as exc:
            raise ValueError("[azure-vision] ResponseShapeError: invalid vision response") from exc

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
