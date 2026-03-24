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
    _builtin_loaded = False

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
        cls._ensure_builtin_providers()
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown rerank backend: {provider}. Available: {available}")

        kwargs = cls._extract_rerank_kwargs(settings)
        kwargs.pop("provider", None)
        kwargs.pop("backend", None)

        builder = cls._registry[key]
        try:
            return builder(**kwargs)
        except TypeError:
            # 兼容历史测试桩（无参构造）。
            return builder()

    @classmethod
    def _ensure_builtin_providers(cls) -> None:
        """幂等确保内置 provider 注册完成。"""
        from libs.reranker.llm_reranker import LLMReranker

        cls._registry.setdefault("none", lambda **_: NoneReranker())
        cls._registry.setdefault("llm", lambda **kwargs: LLMReranker.from_settings(kwargs.get("settings")))
        cls._builtin_loaded = True

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

    @staticmethod
    def _extract_rerank_kwargs(settings: Any) -> dict[str, Any]:
        """提取 `rerank` 配置并注入 `settings`，供 provider 构造时读取全局配置。"""
        if isinstance(settings, dict):
            rerank_cfg = settings.get("rerank")
            if isinstance(rerank_cfg, dict):
                kwargs = dict(rerank_cfg)
                kwargs["settings"] = settings
                return kwargs
            return {"settings": settings}

        rerank_obj = getattr(settings, "rerank", None)
        kwargs: dict[str, Any] = {"settings": settings}
        if rerank_obj is None:
            return kwargs

        if hasattr(rerank_obj, "__dict__"):
            kwargs.update(dict(vars(rerank_obj)))
            return kwargs

        for name in ("provider", "backend", "prompt_path"):
            if hasattr(rerank_obj, name):
                kwargs[name] = getattr(rerank_obj, name)
        return kwargs
