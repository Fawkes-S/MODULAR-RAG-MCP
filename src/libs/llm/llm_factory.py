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


class LLMFactory:
    """`BaseLLM` 的注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseLLM]] = {}
    _builtin_loaded = False

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseLLM]) -> None:
        """注册 provider 构造器。

        Args:
            provider: provider 标识（大小写不敏感）。
            builder: 构造函数，接收 kwargs，返回 `BaseLLM` 实例。
        """
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseLLM:
        """根据配置创建 LLM 实例。

        方法：
        1. 确保内置 provider 已注册；
        2. 读取 `llm.provider`；
        3. 从 `llm` 节提取 kwargs 并透传给构造器。

        关键约束：
        - 配置缺失或未知 provider 必须显式报错，不做静默降级。
        """
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
    def _ensure_builtin_providers(cls) -> None:
        """延迟注册内置 provider。

        这样做的目的：
        - 避免模块导入阶段加载所有 provider；
        - 保留手动 `register()` 覆盖的灵活性（`setdefault` 不会覆盖已有注册）。
        """
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
