"""Embedding 工厂：根据配置创建具体向量化实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.embedding.base_embedding import BaseEmbedding


class EmbeddingFactory:
    """Embedding 提供商的注册与创建入口。

    设计说明：
    - 业务层通过抽象接口获取向量能力，避免绑定单一后端。
    - 创建逻辑统一收敛在工厂中，便于后续扩展重试、熔断和打点。
    """

    # Registry of supported providers
    _registry: dict[str, Callable[..., BaseEmbedding]] = {}

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseEmbedding]) -> None:
        """注册 Embedding 提供商构造器。

        Args:
            provider: 提供商标识（如 `openai`、`bge`）。
            builder: 构造函数，返回 `BaseEmbedding` 实例。

        Raises:
            ValueError: 当 provider 为空时抛出。

        Example:
            >>> EmbeddingFactory.register("fake", lambda model="": FakeEmbedding(model))
        """
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseEmbedding:
        """按配置创建 Embedding 客户端实例。

        Args:
            settings: 配置对象或字典。要求包含 `embedding.provider`，
                可选包含 `embedding.model`。

        Returns:
            BaseEmbedding: 已配置好的向量化客户端。

        Raises:
            ValueError: 当 `embedding.provider` 缺失，或 provider 未注册时抛出。

        Example:
            >>> settings = {"embedding": {"provider": "fake", "model": "m1"}}
            >>> emb = EmbeddingFactory.create(settings)
            >>> emb.embed(["hello", "world"])
            [[...], [...]]
        """
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown embedding provider: {provider}. Available: {available}")

        model = cls._extract_model(settings)
        return cls._registry[key](model=model)

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `embedding.provider` 并在缺失时给出可读错误。

        Args:
            settings: 配置对象或配置字典。

        Returns:
            str: provider 名称。

        Raises:
            ValueError: 当 `embedding.provider` 缺失或为空时抛出。
        """
        if isinstance(settings, dict):
            embedding_cfg = settings.get("embedding")
            if isinstance(embedding_cfg, dict):
                provider = embedding_cfg.get("provider")
                if isinstance(provider, str) and provider.strip():
                    return provider
            raise ValueError("Missing required setting: embedding.provider")

        embedding_obj = getattr(settings, "embedding", None)
        provider = getattr(embedding_obj, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: embedding.provider")

    @staticmethod
    def _extract_model(settings: Any) -> str:
        """提取可选模型名。

        Args:
            settings: 配置对象或配置字典。

        Returns:
            str: 模型名；若未配置则返回空字符串。
        """
        if isinstance(settings, dict):
            embedding_cfg = settings.get("embedding")
            if isinstance(embedding_cfg, dict):
                model = embedding_cfg.get("model", "")
                return model if isinstance(model, str) else ""
            return ""

        embedding_obj = getattr(settings, "embedding", None)
        model = getattr(embedding_obj, "model", "")
        return model if isinstance(model, str) else ""
