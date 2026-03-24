"""Splitter 工厂：根据配置创建切分器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.splitter.base_splitter import BaseSplitter


class SplitterFactory:
    """Splitter 提供商注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseSplitter]] = {}
    _builtin_loaded = False

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseSplitter]) -> None:
        """注册 Splitter 提供商。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseSplitter:
        """根据配置创建 Splitter 实例。"""
        cls._ensure_builtin_providers()
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown splitter provider: {provider}. Available: {available}")

        kwargs = cls._extract_splitter_kwargs(settings)
        kwargs.pop("provider", None)
        return cls._registry[key](**kwargs)

    @classmethod
    def _ensure_builtin_providers(cls) -> None:
        """延迟注册内置 provider。"""
        if cls._builtin_loaded and "recursive" in cls._registry:
            return

        from libs.splitter.recursive_splitter import RecursiveSplitter

        cls._registry.setdefault("recursive", lambda **kwargs: RecursiveSplitter(**kwargs))
        cls._builtin_loaded = True

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `splitter.provider` 并提供可读错误。"""
        if isinstance(settings, dict):
            splitter_cfg = settings.get("splitter")
            if isinstance(splitter_cfg, dict):
                provider = splitter_cfg.get("provider")
                if isinstance(provider, str) and provider.strip():
                    return provider
            raise ValueError("Missing required setting: splitter.provider")

        splitter_obj = getattr(settings, "splitter", None)
        provider = getattr(splitter_obj, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: splitter.provider")

    @staticmethod
    def _extract_splitter_kwargs(settings: Any) -> dict[str, Any]:
        """提取 splitter 配置并转换为构造参数。"""
        if isinstance(settings, dict):
            splitter_cfg = settings.get("splitter")
            if isinstance(splitter_cfg, dict):
                return dict(splitter_cfg)
            return {}

        splitter_obj = getattr(settings, "splitter", None)
        if splitter_obj is None:
            return {}
        if hasattr(splitter_obj, "__dict__"):
            return dict(vars(splitter_obj))

        kwargs: dict[str, Any] = {}
        for name in ("provider", "chunk_size", "chunk_overlap", "separators", "use_langchain"):
            if hasattr(splitter_obj, name):
                kwargs[name] = getattr(splitter_obj, name)
        return kwargs
