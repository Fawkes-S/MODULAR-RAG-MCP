"""Ollama provider implementation (local HTTP backend).

本模块为本地 Ollama 服务提供最小可用的 chat 适配，重点保证：
- 配置驱动创建（base_url + model）；
- 请求/响应 shape 可校验；
- 错误可读且不泄露敏感 endpoint 细节。
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from libs.llm.base_llm import BaseLLM

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class OllamaLLM(BaseLLM):
    """Ollama LLM 客户端实现。"""

    provider_name = "ollama"

    def __init__(
        self,
        model: str = "",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
        transport: TransportFn | None = None,
        **_: Any,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = float(timeout)
        self._transport = transport or self._default_transport

    def chat(self, messages: list[dict[str, Any]]) -> str:
        """调用 Ollama chat 接口并返回文本。

        Args:
            messages: 消息列表，要求与 OpenAI 风格保持一致。

        Returns:
            str: assistant 文本。

        Raises:
            ValueError: 输入或响应 shape 非法。
            RuntimeError: 连接/超时等请求失败。

        关键约束：
        - 报错不回显完整 `base_url`，避免泄露内部网络地址细节。
        """
        self._validate_messages(messages)
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("[ollama] ValidationError: model must be non-empty string")

        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            # 默认关闭流式，简化调用方与测试断言。
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}

        try:
            data = self._transport(url, payload, headers, float(self.timeout))
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                f"[ollama] RequestError: {type(exc).__name__}: {exc}"
            ) from exc

        return self._extract_content(data)

    def _extract_content(self, data: dict[str, Any]) -> str:
        """从 Ollama 响应中提取 assistant 文本。"""
        try:
            return str(data["message"]["content"])
        except Exception as exc:
            raise ValueError("[ollama] ResponseShapeError: invalid chat response") from exc

    @staticmethod
    def _validate_messages(messages: list[dict[str, Any]]) -> None:
        """校验消息 shape，保证错误可读。"""
        if not isinstance(messages, list):
            raise ValueError("[ollama] ValidationError: messages must be list")
        for idx, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError(f"[ollama] ValidationError: messages[{idx}] must be dict")
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str) or not role.strip():
                raise ValueError(
                    f"[ollama] ValidationError: messages[{idx}].role must be non-empty string"
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"[ollama] ValidationError: messages[{idx}].content must be non-empty string"
                )

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
