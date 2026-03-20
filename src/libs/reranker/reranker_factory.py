"""Reranker 工厂：根据配置创建重排器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.reranker.base_reranker import BaseReranker, NoneReranker


class RerankerFactory:
    """Reranker 提供商注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseReranker]] = {
        "none": lambda **_: NoneReranker(),
    }

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseReranker]) -> None:
        """注册重排器 provider 构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseReranker:
        """根据配置创建 Reranker。

        Args:
            settings: 配置对象或字典。支持两种字段别名：
                - `rerank.provider`（当前主字段）
                - `rerank.backend`（兼容字段）

        Returns:
            BaseReranker: 对应 provider 的重排器实例。

        Raises:
            ValueError: 当 provider/backend 缺失，或 provider 未注册时抛出。
        """
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown rerank backend: {provider}. Available: {available}")
        return cls._registry[key]()

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `rerank.provider`（兼容 `rerank.backend`）并给出可读错误。"""
        if isinstance(settings, dict):
            rerank_cfg = settings.get("rerank")
            if isinstance(rerank_cfg, dict):
                provider = rerank_cfg.get("provider")
                backend = rerank_cfg.get("backend")
                value = provider if provider is not None else backend
                if isinstance(value, str) and value.strip():
                    return value
            raise ValueError("Missing required setting: rerank.provider (or rerank.backend)")

        rerank_obj = getattr(settings, "rerank", None)
        provider = getattr(rerank_obj, "provider", None)
        backend = getattr(rerank_obj, "backend", None)
        value = provider if provider is not None else backend
        if isinstance(value, str) and value.strip():
            return value
        raise ValueError("Missing required setting: rerank.provider (or rerank.backend)")
