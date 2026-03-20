"""Splitter 工厂：根据配置创建切分器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.splitter.base_splitter import BaseSplitter


class SplitterFactory:
    """Splitter 提供商注册与创建入口。

    设计说明：
    - 通过统一工厂管理策略路由，避免业务代码散落 `if/else` 分支。
    - 工厂错误信息必须包含字段路径，便于开发者快速修复配置。
    """

    _registry: dict[str, Callable[..., BaseSplitter]] = {}

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseSplitter]) -> None:
        """注册 Splitter 提供商。

        Args:
            provider: 提供商标识（如 `recursive`、`semantic`、`fixed`）。
            builder: 构造函数，返回 `BaseSplitter` 实例。

        Raises:
            ValueError: 当 provider 为空时抛出。
        """
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseSplitter:
        """根据配置创建 Splitter 实例。

        Args:
            settings: 配置对象或字典，要求包含 `splitter.provider`。

        Returns:
            BaseSplitter: 对应 provider 的切分器实例。

        Raises:
            ValueError: 当 `splitter.provider` 缺失，或 provider 未注册时抛出。

        Example:
            >>> settings = {"splitter": {"provider": "recursive"}}
            >>> splitter = SplitterFactory.create(settings)
            >>> splitter.split_text("a\\n\\nb")
            ['a', 'b']
        """
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown splitter provider: {provider}. Available: {available}")
        return cls._registry[key]()

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
