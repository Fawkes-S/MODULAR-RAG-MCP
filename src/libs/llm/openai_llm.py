"""OpenAI provider implementation for chat completions.

本模块实现 `BaseLLM` 的 OpenAI-compatible 版本，供上层通过 `LLMFactory` 按配置创建。

设计目标（面向工程落地）：
- 把不同云端 Provider 统一到同一抽象接口：`chat(messages) -> str`。
- 可测试：通过注入 `transport`，单元测试不触网、不依赖 API Key。
- 可排障：对输入/输出 shape 做显式校验，报错包含 provider 与错误类型。
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from libs.llm.base_llm import BaseLLM

# transport 约定：输入为 url/payload/headers/timeout，返回解析后的 JSON(dict)。
TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class OpenAILLM(BaseLLM):
    """OpenAI LLM 客户端实现（OpenAI-compatible 协议）。

    用途（做什么）：
    - 向 OpenAI-compatible 后端发送 chat 请求，返回 assistant 文本。

    方法（怎么做）：
    1. 校验 `messages` 的输入 shape（list[dict] 且每项包含非空 `role/content`）。
    2. 组装 `POST {base_url}/chat/completions` 请求体：`{"model": ..., "messages": ...}`。
    3. 调用 `transport` 发送请求（默认实现基于 `urllib.request`）。
    4. 从响应中提取 `choices[0].message.content`。

    关键约束：
    - 本实现只覆盖最小可用字段，不负责 tools/function calling 等扩展；后续可在保持接口不变的前提下增强。
    - 报错信息必须可读：包含 provider 与错误类型；不应泄露敏感信息（例如 API Key）。
    """

    provider_name = "openai"

    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        transport: TransportFn | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = float(timeout)
        self._transport = transport or self._default_transport

    def chat(self, messages: list[dict[str, Any]]) -> str:
        """发送 chat 请求并返回文本结果。

        Args:
            messages: Chat 消息列表。每条消息必须包含：
                - `role`: 角色（user/assistant/system 等）
                - `content`: 文本内容

        Returns:
            str: assistant 的文本内容。

        Raises:
            ValueError:
                - 输入 `messages` shape 非法；或
                - 响应 JSON 不符合预期 shape（缺少 `choices[0].message.content`）。
            RuntimeError:
                - 网络请求失败（超时/连接错误/transport 抛异常等）。错误信息包含 provider 与错误类型。
        """
        self._validate_messages(messages)

        payload = {"model": self.model, "messages": messages}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            # 只在 header 写入 Bearer token；避免把 key 拼进 URL 或错误信息。
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url.rstrip('/')}/chat/completions"

        try:
            data = self._transport(url, payload, headers, float(self.timeout))
        except Exception as exc:  # pragma: no cover
            # 这里不回显 headers，以免敏感信息泄露到日志/报错。
            raise RuntimeError(
                f"[{self.provider_name}] RequestError: {type(exc).__name__}: {exc}"
            ) from exc

        return self._extract_content(data)

    def _extract_content(self, data: dict[str, Any]) -> str:
        """从 OpenAI-compatible 响应中提取文本内容。"""
        try:
            return str(data["choices"][0]["message"]["content"])
        except Exception as exc:
            raise ValueError(
                f"[{self.provider_name}] ResponseShapeError: invalid chat completion response"
            ) from exc

    def _validate_messages(self, messages: list[dict[str, Any]]) -> None:
        """校验 messages 输入 shape，并生成可读错误。"""
        if not isinstance(messages, list):
            raise ValueError(f"[{self.provider_name}] ValidationError: messages must be list")

        for idx, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError(
                    f"[{self.provider_name}] ValidationError: messages[{idx}] must be dict"
                )

            role = message.get("role")
            content = message.get("content")

            if not isinstance(role, str) or not role.strip():
                raise ValueError(
                    f"[{self.provider_name}] ValidationError: messages[{idx}].role must be non-empty string"
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"[{self.provider_name}] ValidationError: messages[{idx}].content must be non-empty string"
                )

    @staticmethod
    def _default_transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """默认 HTTP 传输实现（生产环境可用，测试可替换）。"""
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
