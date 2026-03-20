"""Embedding 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseEmbedding(ABC):
    """向量化客户端抽象基类。

    设计意图：
    - 上层仅依赖统一的 `embed` 接口，避免绑定具体后端。
    - 通过可选 `trace` 参数为后续可观测性打点预留扩展位。
    """

    @abstractmethod
    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        """将文本批量编码为向量。"""
        raise NotImplementedError
