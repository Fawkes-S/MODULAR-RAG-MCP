"""Azure OpenAI embedding provider implementation.

Azure 的 embeddings 接口与 OpenAI 接近，但 URL 与认证方式不同。
本模块通过继承 `OpenAIEmbedding` 复用输入校验与响应解析逻辑，只覆盖 Azure 特有部分。
"""

from __future__ import annotations

from typing import Any

from libs.embedding.openai_embedding import OpenAIEmbedding, TransportFn


class AzureEmbedding(OpenAIEmbedding):
    """Azure Embedding 客户端实现。"""

    provider_name = "azure"

    def __init__(
        self,
        model: str = "text-embedding-ada-002",
        api_key: str = "",
        endpoint: str = "",
        deployment_name: str = "",
        api_version: str = "2024-02-01",
        timeout: float = 30.0,
        max_chars: int = 0,
        truncate_long_text: bool = False,
        transport: TransportFn | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=endpoint,
            timeout=timeout,
            max_chars=max_chars,
            truncate_long_text=truncate_long_text,
            transport=transport,
            **kwargs,
        )
        self.endpoint = endpoint
        self.deployment_name = deployment_name or model
        self.api_version = api_version

    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        """调用 Azure Embedding 接口（复用父类校验与解析逻辑）。

        关键差异：
        - URL：`{endpoint}/openai/deployments/{deployment}/embeddings?api-version=...`
        - 认证：`api-key` header

        Raises:
            ValueError: endpoint/deployment 缺失或输入 shape 非法。
            RuntimeError: transport 请求失败。
        """
        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise ValueError("[azure] ValidationError: endpoint must be non-empty string")
        if not isinstance(self.deployment_name, str) or not self.deployment_name.strip():
            raise ValueError("[azure] ValidationError: deployment_name must be non-empty string")

        normalized = self._normalize_texts(texts)
        payload = {"input": normalized}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key

        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment_name}"
            f"/embeddings?api-version={self.api_version}"
        )
        try:
            data = self._transport(url, payload, headers, self.timeout)
        except Exception as exc:  # pragma: no cover
            # 不回显 headers，避免 api_key 泄露。
            raise RuntimeError(f"[azure] RequestError: {type(exc).__name__}: {exc}") from exc

        return self._extract_vectors(data)
