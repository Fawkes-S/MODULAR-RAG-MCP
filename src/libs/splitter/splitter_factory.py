"""Splitter 工厂：根据配置创建切分器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.settings import Settings
from libs.splitter.base_splitter import BaseSplitter


class SplitterFactory:
    """Splitter 提供商注册与创建入口。

    约定（主路径）：
    - provider: `ingestion.splitter`
    - 通用参数: `ingestion.chunk_size` / `ingestion.chunk_overlap` / `ingestion.separators`
    - provider 专有参数: `ingestion.splitter_kwargs`（可选，dict）

    说明：
    - 真实运行路径应传入 `core.settings.Settings`；
    - 仍保留 dict 兼容分支，主要用于历史单元测试，后续可逐步移除。
    """

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
    def create(cls, settings: Any, **override_kwargs: Any) -> BaseSplitter:
        """根据配置创建 Splitter 实例。"""
        cls._ensure_builtin_providers()

        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown splitter provider: {provider}. Available: {available}")

        kwargs = cls._extract_splitter_kwargs(settings)
        kwargs.update(override_kwargs)
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
        """提取 `ingestion.splitter` provider。"""
        ingestion_cfg = SplitterFactory._extract_ingestion_config(settings)
        provider = ingestion_cfg.get("splitter")
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: ingestion.splitter")

    @staticmethod
    def _extract_splitter_kwargs(settings: Any) -> dict[str, Any]:
        """提取 splitter 构造参数。"""
        ingestion_cfg = SplitterFactory._extract_ingestion_config(settings)

        kwargs: dict[str, Any] = {}

        # provider 专有参数先放入，再由通用参数覆盖（确保通用键语义明确）。
        splitter_kwargs = ingestion_cfg.get("splitter_kwargs")
        if isinstance(splitter_kwargs, dict):
            kwargs.update(splitter_kwargs)

        for field in ("chunk_size", "chunk_overlap", "separators"):
            if field in ingestion_cfg:
                kwargs[field] = ingestion_cfg[field]

        return kwargs

    @staticmethod
    def _extract_ingestion_config(settings: Any) -> dict[str, Any]:
        """抽取 ingestion 配置并标准化为 dict。"""
        if isinstance(settings, Settings):
            ingestion = settings.ingestion
            return {
                "splitter": ingestion.splitter,
                "chunk_size": ingestion.chunk_size,
                "chunk_overlap": ingestion.chunk_overlap,
                "separators": list(ingestion.separators),
                "splitter_kwargs": dict(ingestion.splitter_kwargs),
                "batch_size": ingestion.batch_size,
            }

        if isinstance(settings, dict):
            ingestion = settings.get("ingestion")
            if isinstance(ingestion, dict):
                return dict(ingestion)
            return {}

        ingestion_obj = getattr(settings, "ingestion", None)
        if ingestion_obj is None:
            return {}

        if isinstance(ingestion_obj, dict):
            return dict(ingestion_obj)
        if hasattr(ingestion_obj, "__dict__"):
            return dict(vars(ingestion_obj))

        extracted: dict[str, Any] = {}
        for name in ("splitter", "chunk_size", "chunk_overlap", "separators", "splitter_kwargs"):
            if hasattr(ingestion_obj, name):
                extracted[name] = getattr(ingestion_obj, name)
        return extracted

    @classmethod
    def list_providers(cls) -> list[str]:
        """返回当前可用 provider 列表。"""
        cls._ensure_builtin_providers()
        return sorted(cls._registry.keys())