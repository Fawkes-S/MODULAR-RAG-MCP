"""Ollama embedding provider implementation.

本模块实现本地 Ollama Embedding 适配，目标是与 `BaseEmbedding` 契约保持一致：
`embed(texts) -> list[list[float]]`。

设计原则：
- 配置驱动：`base_url + model` 可通过配置切换；
- 可测试：支持注入 `transport`，单测不触网；
- 可读错误：输入 shape、响应 shape、请求失败分层报错。
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from libs.embedding.base_embedding import BaseEmbedding

TransportFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class OllamaEmbedding(BaseEmbedding):
    """Ollama Embedding 客户端实现。"""

    provider_name = "ollama"

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
        max_chars: int = 0,
        truncate_long_text: bool = False,
        transport: TransportFn | None = None,
        **_: Any,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = float(timeout)
        self.max_chars = int(max_chars)
        self.truncate_long_text = bool(truncate_long_text)
        self._transport = transport or self._default_transport

    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        """批量向量化文本。

        Args:
            texts: 待向量化文本列表。
            trace: 预留可观测参数（当前未使用）。

        Returns:
            list[list[float]]: 向量列表，顺序与输入文本一致。

        Raises:
            ValueError: 输入或响应 shape 非法。
            RuntimeError: 网络连接失败/超时等请求错误。
        """
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("[ollama] ValidationError: model must be non-empty string")

        normalized = self._normalize_texts(texts)
        url = f"{self.base_url.rstrip('/')}/api/embeddings"
        headers = {"Content-Type": "application/json"}

        vectors: list[list[float]] = []
        for idx, text in enumerate(normalized):
            payload = {"model": self.model, "prompt": text}
            try:
                data = self._transport(url, payload, headers, self.timeout)
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    f"[ollama] RequestError: {type(exc).__name__}: {exc}"
                ) from exc

            vectors.append(self._extract_vector(data, index=idx))

        return vectors

    def _normalize_texts(self, texts: list[str]) -> list[str]:
        """输入校验与超长文本策略处理。"""
        if not isinstance(texts, list):
            raise ValueError("[ollama] ValidationError: texts must be list")
        if len(texts) == 0:
            raise ValueError("[ollama] ValidationError: texts must not be empty")

        normalized: list[str] = []
        for idx, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"[ollama] ValidationError: texts[{idx}] must be non-empty string"
                )
            value = text
            if self.max_chars > 0 and len(value) > self.max_chars:
                if self.truncate_long_text:
                    value = value[: self.max_chars]
                else:
                    raise ValueError(
                        f"[ollama] ValidationError: texts[{idx}] exceeds max_chars={self.max_chars}"
                    )
            normalized.append(value)
        return normalized

    @staticmethod
    def _extract_vector(data: dict[str, Any], index: int) -> list[float]:
        """从单次响应中提取 embedding 向量。"""
        try:
            vector = data["embedding"]
            return [float(v) for v in vector]
        except Exception as exc:
            raise ValueError(
                f"[ollama] ResponseShapeError: invalid embedding response at texts[{index}]"
            ) from exc

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
