"""Evaluator 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    """评估器抽象基类。

    评估输入采用统一样本结构，便于后续替换不同评估后端（custom/ragas/composite）。
    每条样本建议至少包含：`query`、`retrieved_ids`、`golden_ids`。
    """

    @abstractmethod
    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        """执行评估并返回结构化指标。"""
        raise NotImplementedError
