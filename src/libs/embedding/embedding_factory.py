"""Embedding 工厂：根据配置创建具体向量化实现。

工厂职责：
- 从 `settings.embedding` 中读取 provider 与 provider-specific 参数；
- 按 provider 路由创建具体 Embedding 实现。

设计原则：
- 配置驱动：切换 provider 不改业务代码；
- 可测试：provider 实现可注入 transport，工厂只负责路由与参数透传。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.embedding.base_embedding import BaseEmbedding


class EmbeddingFactory:
    """Embedding 提供商的注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseEmbedding]] = {}
    _builtin_loaded = False

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseEmbedding]) -> None:
        """注册 provider 构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseEmbedding:
        """按配置创建 Embedding 客户端实例。"""
        cls._ensure_builtin_providers()
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown embedding provider: {provider}. Available: {available}")

        kwargs = cls._extract_embedding_kwargs(settings)
        kwargs.pop("provider", None)
        return cls._registry[key](**kwargs)

    @classmethod
    def _ensure_builtin_providers(cls) -> None:
        """延迟注册内置 provider。"""
        if cls._builtin_loaded:
            return

        from libs.embedding.azure_embedding import AzureEmbedding
        from libs.embedding.ollama_embedding import OllamaEmbedding
        from libs.embedding.openai_embedding import OpenAIEmbedding

        cls._registry.setdefault("openai", lambda **kwargs: OpenAIEmbedding(**kwargs))
        cls._registry.setdefault("azure", lambda **kwargs: AzureEmbedding(**kwargs))
        cls._registry.setdefault("ollama", lambda **kwargs: OllamaEmbedding(**kwargs))
        cls._builtin_loaded = True

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `embedding.provider` 并在缺失时给出可读错误。"""
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
    def _extract_embedding_kwargs(settings: Any) -> dict[str, Any]:
        """提取 embedding 配置并转换为 provider 构造参数。"""
        if isinstance(settings, dict):
            embedding_cfg = settings.get("embedding")
            if isinstance(embedding_cfg, dict):
                return dict(embedding_cfg)
            return {}

        embedding_obj = getattr(settings, "embedding", None)
        if embedding_obj is None:
            return {}
        if hasattr(embedding_obj, "__dict__"):
            return dict(vars(embedding_obj))

        kwargs: dict[str, Any] = {}
        for name in (
            "provider",
            "model",
            "api_key",
            "base_url",
            "endpoint",
            "deployment_name",
            "api_version",
            "timeout",
            "max_chars",
            "truncate_long_text",
            "transport",
        ):
            if hasattr(embedding_obj, name):
                kwargs[name] = getattr(embedding_obj, name)
        return kwargs
