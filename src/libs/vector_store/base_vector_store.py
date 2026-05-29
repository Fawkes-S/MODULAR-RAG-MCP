"""VectorStore 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseVectorStore(ABC):
    """向量存储抽象基类。

    上层流程只依赖 `upsert` 和 `query` 两个稳定能力：
    - `upsert` 负责幂等写入向量记录；
    - `query` 负责按向量相似度检索候选结果。
    """

    @abstractmethod
    def upsert(self, records: list[dict[str, Any]], trace: Any | None = None) -> None:
        """批量写入向量记录。

        Args:
            records: 待写入记录列表。每条记录至少应包含 `id`、`vector`、`metadata` 三个字段。
            trace: 可选链路上下文，预留给观测打点。

        Raises:
            ValueError: 当记录 shape 不满足约定时，具体实现应抛出可读错误。
        """
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """向量检索。

        Args:
            vector: 查询向量。
            top_k: 返回候选上限，必须为正整数。
            filters: 元数据过滤条件；若为 `None` 表示不过滤。
            trace: 可选链路上下文。

        Returns:
            list[dict[str, Any]]: 检索结果列表。每条结果至少包含 `id` 与 `score` 字段。
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_ids(self, ids: list[str], trace: Any | None = None) -> list[dict[str, Any]]:
        """按 chunk ID 批量读取记录。

        Args:
            ids: 待查询的 chunk ID 列表。
            trace: 可选链路上下文。

        Returns:
            list[dict[str, Any]]: 每条记录至少包含 `id`、`text`、`metadata`。
        """
        raise NotImplementedError
