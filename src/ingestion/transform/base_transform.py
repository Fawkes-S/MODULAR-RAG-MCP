"""Transform 抽象基类定义（C5）。

该模块约束 Ingestion Transform 阶段的统一输入输出契约：
- 输入：`list[Chunk]`
- 输出：`list[Chunk]`
- 可选 trace：用于记录阶段处理统计与耗时
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.trace.trace_context import TraceContext
from core.types import Chunk


class BaseTransform(ABC):
    """Transform 抽象接口。

    约束目的：
    - 保证各类 Transform（ChunkRefiner/MetadataEnricher/ImageCaptioner）可插拔。
    - 让 Pipeline 只依赖稳定契约，而不绑定具体实现。
    """

    @abstractmethod
    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        """对 Chunk 列表进行转换并返回新列表。"""
        raise NotImplementedError

    @staticmethod
    def validate_chunks(chunks: list[Chunk]) -> list[Chunk]:
        """校验 Transform 输入 shape。"""
        if not isinstance(chunks, list):
            raise ValueError("chunks must be list[Chunk]")

        for idx, chunk in enumerate(chunks):
            if not isinstance(chunk, Chunk):
                raise ValueError(f"chunks[{idx}] must be Chunk")

        return chunks
