"""Splitter 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSplitter(ABC):
    """文本切分器抽象基类。

    用途：统一不同切分策略（递归切分、语义切分、定长切分）的调用契约，
    让上层流程只依赖一个稳定接口。
    """

    @staticmethod
    def validate_text(text: Any) -> str:
        """校验并标准化输入文本。

        Raises:
            ValueError: 当输入不是字符串时抛出。
        """
        if not isinstance(text, str):
            raise ValueError("text must be str")
        return text

    @staticmethod
    def validate_chunks(chunks: Any) -> list[str]:
        """校验切分结果并过滤空白片段。

        Raises:
            ValueError: 当输出不是 `list[str]` 形状时抛出。
        """
        if not isinstance(chunks, list):
            raise ValueError("split result must be list[str]")

        normalized: list[str] = []
        for chunk in chunks:
            if not isinstance(chunk, str):
                raise ValueError("split result must be list[str]")
            if chunk.strip():
                normalized.append(chunk)
        return normalized

    @abstractmethod
    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        """将输入文本切分为多个片段。"""
        raise NotImplementedError
