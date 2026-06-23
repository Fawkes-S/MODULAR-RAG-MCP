"""Evaluator 工厂：根据配置创建评估器实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.custom_evaluator import CustomEvaluator


def _build_ragas_evaluator(settings: Any | None = None) -> BaseEvaluator:
    """懒加载构造 `RagasEvaluator`。

    做什么：
    - 仅在调用方真的选择 `provider=ragas` 时导入评估实现；
    - 避免模块导入阶段就触发可选依赖检查。

    为什么：
    - H1 的 Ragas 属于可选评估后端，不应影响 `custom` 等默认路径；
    - 这样没有安装 `ragas` 的环境仍能正常导入工程和运行其它测试。
    """
    from observability.evaluation.ragas_evaluator import RagasEvaluator

    return RagasEvaluator(settings=settings)


class EvaluatorFactory:
    """Evaluator 提供商注册与创建入口。"""

    _registry: dict[str, Callable[..., BaseEvaluator]] = {
        "custom": lambda **_: CustomEvaluator(),
        "ragas": lambda **kwargs: _build_ragas_evaluator(settings=kwargs.get("settings")),
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
        """根据配置创建单评估器或组合评估器。

        路由规则：
        - 若配置了 `evaluation.backends`，优先走多后端组合模式；
        - 否则回退到旧的 `evaluation.provider` 单后端模式，保持兼容。
        """
        backends = cls._extract_backends(settings)
        if backends:
            evaluators = [cls._create_single(provider, settings=settings) for provider in backends]
            if len(evaluators) == 1:
                return evaluators[0]

            from observability.evaluation.composite_evaluator import CompositeEvaluator

            return CompositeEvaluator(evaluators=evaluators)

        provider = cls._extract_provider(settings)
        return cls._create_single(provider, settings=settings)

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

    @classmethod
    def _create_single(cls, provider: str, settings: Any | None = None) -> BaseEvaluator:
        """创建单个评估器实例，并复用统一的 provider 校验逻辑。

        `settings` 会透传给具体 provider。Ragas 这类真实后端需要读取 LLM/Embedding
        配置来创建第三方客户端；custom 后端会忽略该参数，保持轻量纯本地计算。
        """
        key = provider.strip().lower()
        if key not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "<none>"
            raise ValueError(f"Unknown evaluation provider: {provider}. Available: {available}")
        builder = cls._registry[key]
        try:
            return builder(settings=settings)
        except TypeError:
            # 与 Reranker/VectorStore 工厂保持一致：兼容历史无参测试桩或极简实现。
            return builder()

    @staticmethod
    def _extract_backends(settings: Any) -> list[str]:
        """提取 `evaluation.backends`。

        兼容 dict 配置和 `Settings` 对象。空列表表示调用方未启用多后端模式。
        """
        if isinstance(settings, dict):
            evaluation_cfg = settings.get("evaluation")
            if isinstance(evaluation_cfg, dict):
                backends = evaluation_cfg.get("backends")
                if isinstance(backends, list):
                    return [str(item).strip() for item in backends if str(item).strip()]
            return []

        evaluation_obj = getattr(settings, "evaluation", None)
        backends = getattr(evaluation_obj, "backends", ())
        if isinstance(backends, (list, tuple)):
            return [str(item).strip() for item in backends if str(item).strip()]
        return []
