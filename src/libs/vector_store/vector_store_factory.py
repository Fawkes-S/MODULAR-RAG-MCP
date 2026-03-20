"""VectorStore 工厂：根据配置创建向量存储实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.vector_store.base_vector_store import BaseVectorStore


class VectorStoreFactory:
    """VectorStore 提供商注册与创建入口。

    设计说明：
    - 业务层只依赖抽象接口，不感知底层 DB 细节。
    - 所有 provider 分流收敛到工厂，便于统一错误处理和后续可观测增强。
    """

    _registry: dict[str, Callable[..., BaseVectorStore]] = {}

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseVectorStore]) -> None:
        """注册 VectorStore 提供商构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseVectorStore:
        """根据配置创建 VectorStore 实例。

        Args:
            settings: 配置对象或字典。要求包含 `vector_store.provider`，
                可选包含 `vector_store.persist_dir`。

        Returns:
            BaseVectorStore: 对应 provider 的向量存储实例。

        Raises:
            ValueError: 当 `vector_store.provider` 缺失，或 provider 未注册时抛出。
        """
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown vector_store provider: {provider}. Available: {available}")

        persist_dir = cls._extract_persist_dir(settings)
        return cls._registry[key](persist_dir=persist_dir)

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
    def _extract_persist_dir(settings: Any) -> str:
        """提取可选持久化目录。"""
        if isinstance(settings, dict):
            vector_cfg = settings.get("vector_store")
            if isinstance(vector_cfg, dict):
                persist_dir = vector_cfg.get("persist_dir", "")
                return persist_dir if isinstance(persist_dir, str) else ""
            return ""

        vector_obj = getattr(settings, "vector_store", None)
        persist_dir = getattr(vector_obj, "persist_dir", "")
        return persist_dir if isinstance(persist_dir, str) else ""
