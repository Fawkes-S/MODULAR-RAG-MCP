"""VectorStore 工厂：根据配置创建向量存储实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.vector_store.base_vector_store import BaseVectorStore


class VectorStoreFactory:
    """VectorStore 提供商注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseVectorStore]] = {}
    _builtin_loaded = False

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseVectorStore]) -> None:
        """注册 VectorStore 提供商构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseVectorStore:
        """根据配置创建 VectorStore 实例。"""
        cls._ensure_builtin_providers()
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown vector_store provider: {provider}. Available: {available}")

        kwargs = cls._extract_vector_store_kwargs(settings)
        kwargs.pop("provider", None)
        return cls._registry[key](**kwargs)

    @classmethod
    def _ensure_builtin_providers(cls) -> None:
        """幂等确保内置 provider 存在，避免测试清空 registry 后状态漂移。"""
        from libs.vector_store.chroma_store import ChromaStore

        cls._registry.setdefault("chroma", lambda **kwargs: ChromaStore(**kwargs))
        cls._builtin_loaded = True

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `vector_store.provider` 并提供可读错误。"""
        if isinstance(settings, dict):
            vector_cfg = settings.get("vector_store")
            if isinstance(vector_cfg, dict):
                provider = vector_cfg.get("provider")
                if isinstance(provider, str) and provider.strip():
                    return provider
            raise ValueError("Missing required setting: vector_store.provider")

        vector_obj = getattr(settings, "vector_store", None)
        provider = getattr(vector_obj, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: vector_store.provider")

    @staticmethod
    def _extract_vector_store_kwargs(settings: Any) -> dict[str, Any]:
        """提取 vector_store 配置并转换为 provider 构造参数。"""
        if isinstance(settings, dict):
            vector_cfg = settings.get("vector_store")
            if isinstance(vector_cfg, dict):
                return dict(vector_cfg)
            return {}

        vector_obj = getattr(settings, "vector_store", None)
        if vector_obj is None:
            return {}
        if hasattr(vector_obj, "__dict__"):
            return dict(vars(vector_obj))

        kwargs: dict[str, Any] = {}
        for name in ("provider", "persist_dir", "collection_name"):
            if hasattr(vector_obj, name):
                kwargs[name] = getattr(vector_obj, name)
        return kwargs
