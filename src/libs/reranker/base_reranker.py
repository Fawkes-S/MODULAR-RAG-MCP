"""Reranker 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseReranker(ABC):
    """重排器抽象基类。

    该层位于检索召回与最终输出之间，负责基于 query 对候选文档重新排序。
    上层只依赖统一 `rerank` 接口，从而可以在 `none`、`llm`、`cross_encoder`
    等后端之间无缝切换。
    """

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """根据 query 对候选列表重排序。

        Args:
            query: 用户查询文本。
            candidates: 候选文档列表，每项通常包含 `id`、`text`、`score` 等字段。
            trace: 可选链路上下文，预留给观测打点。

        Returns:
            list[dict[str, Any]]: 重排后的候选列表。
        """
        raise NotImplementedError


class NoneReranker(BaseReranker):
    """空重排实现：作为默认回退，保持输入顺序不变。"""

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """直接返回同序候选。

        这里返回浅拷贝，避免调用方后续原地修改时影响上游引用。
        """
        return list(candidates)
