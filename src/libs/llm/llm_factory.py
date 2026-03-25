"""Factory for creating LLM providers from runtime settings.

工厂职责：
- 读取 `settings.llm` 配置，解析 provider。
- 路由到对应 provider 构造器并创建实例。
- 统一处理未知 provider / 配置缺失等错误。

这样业务层只需要依赖 `BaseLLM`，不用关心具体 provider 初始化细节。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.llm.base_llm import BaseLLM
from libs.llm.base_vision_llm import BaseVisionLLM


class LLMFactory:
    """`BaseLLM` / `BaseVisionLLM` 的注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseLLM]] = {}
    _vision_registry: dict[str, Callable[..., BaseVisionLLM]] = {}
    _builtin_loaded = False
    _vision_builtin_loaded = False

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseLLM]) -> None:
        """注册文本 LLM provider 构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def register_vision(cls, provider: str, builder: Callable[..., BaseVisionLLM]) -> None:
        """注册 Vision LLM provider 构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._vision_registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseLLM:
        """根据配置创建文本 LLM 实例。"""
        cls._ensure_builtin_providers()
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown llm provider: {provider}. Available: {available}")

        kwargs = cls._extract_llm_kwargs(settings)
        kwargs.pop("provider", None)
        return cls._registry[key](**kwargs)

    @classmethod
    def create_vision_llm(cls, settings: Any) -> BaseVisionLLM:
        """根据配置创建 Vision LLM 实例。"""
        cls._ensure_builtin_vision_providers()
        provider = cls._extract_vision_provider(settings)
        key = provider.strip().lower()
        if key not in cls._vision_registry:
            available = ", ".join(sorted(cls._vision_registry)) or "<none>"
            raise ValueError(f"Unknown vision llm provider: {provider}. Available: {available}")

        kwargs = cls._extract_vision_llm_kwargs(settings)
        kwargs.pop("provider", None)
        return cls._vision_registry[key](**kwargs)

    @classmethod
    def _ensure_builtin_providers(cls) -> None:
        """延迟注册内置文本 LLM provider。"""
        if cls._builtin_loaded:
            return

        from libs.llm.azure_llm import AzureLLM
        from libs.llm.deepseek_llm import DeepSeekLLM
        from libs.llm.ollama_llm import OllamaLLM
        from libs.llm.openai_llm import OpenAILLM

        cls._registry.setdefault("openai", lambda **kwargs: OpenAILLM(**kwargs))
        cls._registry.setdefault("azure", lambda **kwargs: AzureLLM(**kwargs))
        cls._registry.setdefault("deepseek", lambda **kwargs: DeepSeekLLM(**kwargs))
        cls._registry.setdefault("ollama", lambda **kwargs: OllamaLLM(**kwargs))
        cls._builtin_loaded = True

    @classmethod
    def _ensure_builtin_vision_providers(cls) -> None:
        """延迟注册内置 Vision LLM provider。"""
        if cls._vision_builtin_loaded:
            return

        from libs.llm.azure_vision_llm import AzureVisionLLM

        cls._vision_registry.setdefault("azure", lambda **kwargs: AzureVisionLLM(**kwargs))
        cls._vision_builtin_loaded = True

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `llm.provider` 并输出可读错误。"""
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
    def _extract_vision_provider(settings: Any) -> str:
        """提取 `vision_llm.provider` 并输出可读错误。"""
        if isinstance(settings, dict):
            vision_cfg = settings.get("vision_llm")
            if isinstance(vision_cfg, dict):
                provider = vision_cfg.get("provider")
                if isinstance(provider, str) and provider.strip():
                    return provider
            raise ValueError("Missing required setting: vision_llm.provider")

        vision_obj = getattr(settings, "vision_llm", None)
        provider = getattr(vision_obj, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: vision_llm.provider")

    @staticmethod
    def _extract_llm_kwargs(settings: Any) -> dict[str, Any]:
        """提取 `llm` 配置并转换为 provider 构造参数。"""
        if isinstance(settings, dict):
            llm_cfg = settings.get("llm")
            if isinstance(llm_cfg, dict):
                return dict(llm_cfg)
            return {}

        llm_obj = getattr(settings, "llm", None)
        if llm_obj is None:
            return {}
        if hasattr(llm_obj, "__dict__"):
            return dict(vars(llm_obj))

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
            "transport",
        ):
            if hasattr(llm_obj, name):
                kwargs[name] = getattr(llm_obj, name)
        return kwargs

    @staticmethod
    def _extract_vision_llm_kwargs(settings: Any) -> dict[str, Any]:
        """提取 `vision_llm` 配置并转换为 provider 构造参数。"""
        if isinstance(settings, dict):
            vision_cfg = settings.get("vision_llm")
            if isinstance(vision_cfg, dict):
                return dict(vision_cfg)
            return {}

        vision_obj = getattr(settings, "vision_llm", None)
        if vision_obj is None:
            return {}
        if hasattr(vision_obj, "__dict__"):
            return dict(vars(vision_obj))

        kwargs: dict[str, Any] = {}
        for name in (
            "provider",
            "model",
            "api_key",
            "base_url",
            "endpoint",
            "azure_endpoint",
            "deployment_name",
            "api_version",
            "timeout",
            "transport",
            "max_image_size",
        ):
            if hasattr(vision_obj, name):
                kwargs[name] = getattr(vision_obj, name)
        return kwargs
