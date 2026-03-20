"""Factory for creating LLM providers from runtime settings."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.llm.base_llm import BaseLLM


class LLMFactory:
    """`BaseLLM` 的注册与创建入口。

    设计说明：
    - 通过工厂集中管理 provider 路由，避免业务层直接依赖具体实现。
    - 通过统一的创建入口，后续可以在此注入监控、重试、降级等横切能力。
    """

    _registry: dict[str, Callable[..., BaseLLM]] = {}

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseLLM]) -> None:
        """注册 LLM 提供商构造器。

        Args:
            provider: 提供商标识（如 `openai`、`azure`），大小写不敏感。
            builder: 构造函数，接收命名参数并返回 `BaseLLM` 实例。

        Raises:
            ValueError: 当 `provider` 为空字符串时抛出。

        Example:
            >>> LLMFactory.register("fake", lambda model="": FakeLLM(model))
        """
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseLLM:
        """根据配置创建 LLM 实例。

        Args:
            settings: 应用配置对象或字典。要求至少包含 `llm.provider`，
                可选包含 `llm.model`。

        Returns:
            BaseLLM: 已初始化的 LLM 客户端实例。

        Raises:
            ValueError: 当 `llm.provider` 缺失，或 provider 未注册时抛出。

        Example:
            >>> settings = {"llm": {"provider": "fake", "model": "demo"}}
            >>> llm = LLMFactory.create(settings)
            >>> llm.chat([{"role": "user", "content": "你好"}])
            '...'
        """
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown llm provider: {provider}. Available: {available}")

        model = cls._extract_model(settings)
        return cls._registry[key](model=model)

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `llm.provider` 并输出可读错误。

        Args:
            settings: 配置对象或配置字典。

        Returns:
            str: provider 名称。

        Raises:
            ValueError: 当 `llm.provider` 不存在或为空时抛出，错误信息会包含字段路径。
        """
        if isinstance(settings, dict):
            llm_cfg = settings.get("llm")
            if isinstance(llm_cfg, dict):
                provider = llm_cfg.get("provider")
                if isinstance(provider, str) and provider.strip():
                    return provider
            raise ValueError("Missing required setting: llm.provider")

        llm_obj = getattr(settings, "llm", None)
        provider = getattr(llm_obj, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: llm.provider")

    @staticmethod
    def _extract_model(settings: Any) -> str:
        """提取可选模型名。

        Args:
            settings: 配置对象或配置字典。

        Returns:
            str: 模型名；若未配置则返回空字符串。
        """
        if isinstance(settings, dict):
            llm_cfg = settings.get("llm")
            if isinstance(llm_cfg, dict):
                model = llm_cfg.get("model", "")
                return model if isinstance(model, str) else ""
            return ""

        llm_obj = getattr(settings, "llm", None)
        model = getattr(llm_obj, "model", "")
        return model if isinstance(model, str) else ""
