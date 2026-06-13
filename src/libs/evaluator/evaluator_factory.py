"""Evaluator 工厂：根据配置创建评估器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.custom_evaluator import CustomEvaluator


def _build_ragas_evaluator() -> BaseEvaluator:
    """懒加载构造 `RagasEvaluator`。

    做什么：
    - 仅在调用方真的选择 `provider=ragas` 时导入评估实现；
    - 避免模块导入阶段就触发可选依赖检查。

    为什么：
    - H1 的 Ragas 属于可选评估后端，不应影响 `custom` 等默认路径；
    - 这样没有安装 `ragas` 的环境仍能正常导入工程和运行其它测试。
    """
    from observability.evaluation.ragas_evaluator import RagasEvaluator

    return RagasEvaluator()


class EvaluatorFactory:
    """Evaluator 提供商注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseEvaluator]] = {
        "custom": lambda **_: CustomEvaluator(),
        "ragas": lambda **_: _build_ragas_evaluator(),
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
