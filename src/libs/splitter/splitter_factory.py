"""Splitter 工厂：根据配置创建切分器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.splitter.base_splitter import BaseSplitter


class SplitterFactory:
    """Splitter 提供商注册与创建入口。

    约定（主路径）：
    - provider: `ingestion.splitter`
    - 通用参数: `ingestion.chunk_size` / `ingestion.chunk_overlap`
    - provider 专有参数: `ingestion.splitter_kwargs`（可选，dict）
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
        """根据配置创建 Splitter 实例。

        做什么：
        - 从配置中读取 provider 与构造参数；
        - 路由到对应注册实现并实例化。

        为什么：
        - 统一管理对象创建逻辑，保证“改配置不改代码”。

        关键权衡：
        - 仅暴露 ingestion 下的最小必要字段，避免把无关配置传入构造器导致类型错误。

        失败路径：
        - provider 缺失/未知时抛出可读 ValueError；
        - provider 构造失败时，透传原始异常信息。
        """
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
        """提取 splitter 构造参数。

        来源：
        - 通用参数：`ingestion.chunk_size` / `ingestion.chunk_overlap` / `ingestion.separators`
        - 专有参数：`ingestion.splitter_kwargs`（dict，可选）
        """
        ingestion_cfg = SplitterFactory._extract_ingestion_config(settings)

        kwargs: dict[str, Any] = {}

        # provider 专有参数先放入，再由通用参数覆盖（确保通用键语义明确）。
        splitter_kwargs = ingestion_cfg.get("splitter_kwargs")
        if isinstance(splitter_kwargs, dict):
            kwargs.update(splitter_kwargs)

        for field in ("chunk_size", "chunk_overlap", "separators", "use_langchain"):
            if field in ingestion_cfg:
                kwargs[field] = ingestion_cfg[field]

        return kwargs

    @staticmethod
    def _extract_ingestion_config(settings: Any) -> dict[str, Any]:
        """抽取 ingestion 配置并标准化为 dict。"""
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
        for name in ("splitter", "chunk_size", "chunk_overlap", "separators", "use_langchain", "splitter_kwargs"):
            if hasattr(ingestion_obj, name):
                extracted[name] = getattr(ingestion_obj, name)
        return extracted

    @classmethod
    def list_providers(cls) -> list[str]:
        """返回当前可用 provider 列表。"""
        cls._ensure_builtin_providers()
        return sorted(cls._registry.keys())
