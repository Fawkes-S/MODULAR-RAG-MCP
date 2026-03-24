"""OpenAI embedding provider implementation.

本模块实现 `BaseEmbedding` 的 OpenAI 版本，支持批量 `embed(texts)`。

为什么需要更“显式”的输入策略：
- 不同 provider 对输入长度、空字符串等约束不同；
- 如果直接把原始输入透传给后端，错误会变得不可控且难排查；
- 因此这里把“空输入/超长输入”的行为前置并由配置控制。
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from libs.embedding.base_embedding import BaseEmbedding

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI Embedding 客户端实现。

    用途：
    - 将一批文本转换为向量（vectors），供向量库写入/检索。

    方法：
    - 请求：`POST {base_url}/embeddings`，payload：`{"model": model, "input": [text1, ...]}`。
    - 响应：`{"data": [{"embedding": [...]}, ...]}`。

    关键约束：
    - `texts` 必须非空且每项为非空字符串。
    - 超长文本的处理策略由 `max_chars` 与 `truncate_long_text` 决定：
      - `truncate_long_text=False`：超长直接报错（默认，更可控）；
      - `truncate_long_text=True`：按 `max_chars` 截断（保证流程继续）。
    """

    provider_name = "openai"

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        max_chars: int = 0,
        truncate_long_text: bool = False,
        transport: TransportFn | None = None,
        **_: Any,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = float(timeout)
        self.max_chars = int(max_chars)
        self.truncate_long_text = bool(truncate_long_text)
        self._transport = transport or self._default_transport

    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        """批量向量化文本。

        Args:
            texts: 待编码文本列表。
            trace: 预留可观测参数（当前实现未使用）。

        Returns:
            list[list[float]]: 向量列表（长度与 texts 相同）。

        Raises:
            ValueError: 输入 shape 非法或超长策略触发报错；或响应 shape 非法。
            RuntimeError: transport 层失败（连接/超时/解析失败等）。
        """
        normalized = self._normalize_texts(texts)
        payload = {"model": self.model, "input": normalized}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url.rstrip('/')}/embeddings"
        try:
            data = self._transport(url, payload, headers, self.timeout)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                f"[{self.provider_name}] RequestError: {type(exc).__name__}: {exc}"
            ) from exc

        return self._extract_vectors(data)

    def _normalize_texts(self, texts: list[str]) -> list[str]:
        """校验输入并处理空文本/超长文本策略。"""
        if not isinstance(texts, list):
            raise ValueError(f"[{self.provider_name}] ValidationError: texts must be list")
        if len(texts) == 0:
            raise ValueError(f"[{self.provider_name}] ValidationError: texts must not be empty")

        normalized: list[str] = []
        for idx, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"[{self.provider_name}] ValidationError: texts[{idx}] must be non-empty string"
                )
            value = text

            # 这里按“字符数”做最小约束（不依赖 tokenizer），保证行为稳定。
            if self.max_chars > 0 and len(value) > self.max_chars:
                if self.truncate_long_text:
                    value = value[: self.max_chars]
                else:
                    raise ValueError(
                        f"[{self.provider_name}] ValidationError: texts[{idx}] exceeds max_chars={self.max_chars}"
                    )

            normalized.append(value)
        return normalized

    def _extract_vectors(self, data: dict[str, Any]) -> list[list[float]]:
        """从响应中提取 embedding 向量列表。"""
        try:
            items = data["data"]
            vectors = [list(map(float, item["embedding"])) for item in items]
        except Exception as exc:
            raise ValueError(
                f"[{self.provider_name}] ResponseShapeError: invalid embedding response"
            ) from exc
        return vectors

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
