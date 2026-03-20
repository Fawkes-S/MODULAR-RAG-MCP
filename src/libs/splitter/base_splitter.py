"""Splitter 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSplitter(ABC):
    """文本切分器抽象基类。

    用途：统一不同切分策略（递归切分、语义切分、定长切分）的调用契约，
    让上层流程只依赖一个稳定接口。
    """

    @abstractmethod
    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        """将输入文本切分为多个片段。"""
        raise NotImplementedError
