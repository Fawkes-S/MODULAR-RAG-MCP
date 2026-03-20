"""Evaluator 工厂：根据配置创建评估器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.custom_evaluator import CustomEvaluator


class EvaluatorFactory:
    """Evaluator 提供商注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseEvaluator]] = {
        "custom": lambda **_: CustomEvaluator(),
    }

    @classmethod
    def register(cls, provider: str, builder: Callable[..., BaseEvaluator]) -> None:
        """注册评估器 provider 构造器。"""
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider key cannot be empty")
        cls._registry[key] = builder

    @classmethod
    def create(cls, settings: Any) -> BaseEvaluator:
        """根据配置创建评估器实例。"""
        provider = cls._extract_provider(settings)
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown evaluation provider: {provider}. Available: {available}")
        return cls._registry[key]()

    @staticmethod
    def _extract_provider(settings: Any) -> str:
        """提取 `evaluation.provider` 并在缺失时给出可读错误。"""
        if isinstance(settings, dict):
            evaluation_cfg = settings.get("evaluation")
            if isinstance(evaluation_cfg, dict):
                provider = evaluation_cfg.get("provider")
                if isinstance(provider, str) and provider.strip():
                    return provider
            raise ValueError("Missing required setting: evaluation.provider")

        evaluation_obj = getattr(settings, "evaluation", None)
        provider = getattr(evaluation_obj, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider
        raise ValueError("Missing required setting: evaluation.provider")
