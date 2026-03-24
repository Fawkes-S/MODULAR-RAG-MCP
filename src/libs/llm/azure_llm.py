"""Azure OpenAI provider implementation.

Azure 的 chat completions 与 OpenAI-compatible 协议接近，但请求 URL、认证 header、部署参数不同。
本模块实现 `BaseLLM` 的 Azure 版本，并保持与 OpenAI 版本一致的输入/输出契约。
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from libs.llm.base_llm import BaseLLM

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class AzureLLM(BaseLLM):
    """Azure OpenAI 客户端实现。

    用途：
    - 通过 Azure endpoint + deployment 调用 chat completions，并返回文本。

    方法：
    - URL 形如：
      `{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}`
    - 认证使用 `api-key` header。

    关键约束：
    - `endpoint` 和 `deployment_name` 必须非空。
    - 错误信息需要可读，但不应泄露敏感配置（例如 api_key）。
    """

    provider_name = "azure"

    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        endpoint: str = "",
        deployment_name: str = "",
        api_version: str = "2024-02-01",
        timeout: float = 30.0,
        transport: TransportFn | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint
        # Azure 以 deployment 为主；如果未配置 deployment，尝试用 model 兜底。
        self.deployment_name = deployment_name or model
        self.api_version = api_version
        self.timeout = float(timeout)
        self._transport = transport or self._default_transport

    def chat(self, messages: list[dict[str, Any]]) -> str:
        """调用 Azure chat completions。

        Args:
            messages: chat 消息列表，shape 与 OpenAI 保持一致。

        Returns:
            str: assistant 文本。

        Raises:
            ValueError: 输入 shape 或必填配置（endpoint/deployment）非法；或响应 shape 非法。
            RuntimeError: 网络请求失败，错误信息包含 provider 与错误类型。
        """
        self._validate_messages(messages)

        if not self.endpoint.strip():
            raise ValueError("[azure] ValidationError: endpoint must be non-empty string")
        if not self.deployment_name.strip():
            raise ValueError("[azure] ValidationError: deployment_name must be non-empty string")

        payload = {"messages": messages}
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
            # 不回显 headers，避免 api_key 泄露。
            raise RuntimeError(f"[azure] RequestError: {type(exc).__name__}: {exc}") from exc

        return self._extract_content(data)

    def _extract_content(self, data: dict[str, Any]) -> str:
        """Azure 响应 shape 与 OpenAI 兼容：choices[0].message.content。"""
        try:
            return str(data["choices"][0]["message"]["content"])
        except Exception as exc:
            raise ValueError("[azure] ResponseShapeError: invalid chat completion response") from exc

    @staticmethod
    def _validate_messages(messages: list[dict[str, Any]]) -> None:
        """与 OpenAI 相同的 messages shape 校验。"""
        if not isinstance(messages, list):
            raise ValueError("[azure] ValidationError: messages must be list")
        for idx, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError(f"[azure] ValidationError: messages[{idx}] must be dict")
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str) or not role.strip():
                raise ValueError(
                    f"[azure] ValidationError: messages[{idx}].role must be non-empty string"
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"[azure] ValidationError: messages[{idx}].content must be non-empty string"
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
