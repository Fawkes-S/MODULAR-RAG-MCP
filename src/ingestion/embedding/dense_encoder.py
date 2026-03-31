"""DenseEncoder：将 Chunk 批量编码为稠密向量（C8）。"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import Chunk, ChunkRecord
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory


class DenseEncoder:
    """将 `Chunk` 列表编码为带 `dense_vector` 的 `ChunkRecord`。

    做什么：
    - 从输入 chunk 提取 `text`，按 batch 调用 `libs.embedding` 的具体 provider。
    - 将编码结果映射回 `ChunkRecord`，保留 `id/text/metadata` 并填充 `dense_vector`。
    - 对 provider 输出做数量与维度一致性校验，提前暴露契约问题。

    为什么：
    - C8 的职责是把“文本 -> 稠密向量”从 pipeline 中解耦，形成可独立测试的编码组件。
    - 后续 C10（批处理编排）和 C12（向量写入）都依赖这里的稳定输出契约。

    关键权衡：
    - 采用“输入批处理 + 输出严格校验”策略，优先保证数据质量一致性。
    - 一旦发现数量/维度异常，直接抛错而不是静默修复，避免把坏数据带入存储层。

    失败路径：
    - 输入不是 `list[Chunk]`：抛 `ValueError`。
    - provider 返回向量数量不匹配或维度不一致：抛 `ValueError`。
    - provider 调用异常：透传异常给上层（由上层决定重试/降级）。

    Args:
        settings: 全局配置对象，用于读取 embedding provider 与 batch_size。
        embedding: 可注入 embedding 客户端（测试或定制场景）。
        batch_size: 可选批大小，未提供时使用 `settings.ingestion.batch_size`。
    """

    def __init__(
        self,
        settings: Settings,
        embedding: BaseEmbedding | None = None,
        batch_size: int | None = None,
    ) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("DenseEncoder requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.embedding = embedding or EmbeddingFactory.create(settings)

        configured_batch_size = int(settings.ingestion.batch_size)
        self.batch_size = int(batch_size) if batch_size is not None else configured_batch_size
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")

    def encode(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[ChunkRecord]:
        """批量编码 chunk 列表。

        Args:
            chunks: 待编码的 `Chunk` 列表。
            trace: 可选追踪上下文，用于记录编码统计。

        Returns:
            list[ChunkRecord]: 与输入顺序一致的编码结果。
        """
        normalized_chunks = self._validate_chunks(chunks)
        started = perf_counter()

        if not normalized_chunks:
            if trace is not None:
                trace.record_stage(
                    stage_name="embedding.dense_encoder",
                    details={
                        "total": 0,
                        "batches": 0,
                        "vector_dim": 0,
                        "batch_size": self.batch_size,
                        "provider": self.settings.embedding.provider,
                    },
                    elapsed_ms=0.0,
                )
            return []

        results: list[ChunkRecord] = []
        total_batches = 0
        vector_dim = 0

        for offset in range(0, len(normalized_chunks), self.batch_size):
            batch = normalized_chunks[offset : offset + self.batch_size]
            batch_vectors = self.embedding.embed([chunk.text for chunk in batch], trace=trace)
            total_batches += 1

            if len(batch_vectors) != len(batch):
                raise ValueError(
                    "DenseEncoder provider returned vector count mismatch: "
                    f"expected={len(batch)}, actual={len(batch_vectors)}"
                )

            current_dim = self._infer_vector_dim(batch_vectors=batch_vectors, batch_offset=offset)
            if vector_dim == 0:
                vector_dim = current_dim
            elif current_dim != vector_dim:
                raise ValueError(
                    "DenseEncoder provider returned inconsistent vector dimension across batches: "
                    f"expected={vector_dim}, actual={current_dim}, batch_offset={offset}"
                )

            for chunk, vector in zip(batch, batch_vectors):
                record = ChunkRecord(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    dense_vector=[float(v) for v in vector],
                    sparse_vector=None,
                )
                results.append(record)

        if trace is not None:
            trace.record_stage(
                stage_name="embedding.dense_encoder",
                details={
                    "total": len(normalized_chunks),
                    "batches": total_batches,
                    "vector_dim": vector_dim,
                    "batch_size": self.batch_size,
                    "provider": self.settings.embedding.provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return results

    @staticmethod
    def _validate_chunks(chunks: list[Chunk]) -> list[Chunk]:
        """校验输入 shape，确保编码阶段契约稳定。"""
        if not isinstance(chunks, list):
            raise ValueError("chunks must be list[Chunk]")

        for idx, chunk in enumerate(chunks):
            if not isinstance(chunk, Chunk):
                raise ValueError(f"chunks[{idx}] must be Chunk")

        return chunks

    @staticmethod
    def _infer_vector_dim(batch_vectors: list[list[float]], batch_offset: int) -> int:
        """校验批内向量维度一致并返回维度。"""
        if not batch_vectors:
            raise ValueError(f"DenseEncoder provider returned empty batch vectors at offset={batch_offset}")

        if not isinstance(batch_vectors[0], list) or len(batch_vectors[0]) == 0:
            raise ValueError(
                "DenseEncoder provider returned invalid first vector: "
                f"offset={batch_offset}, type={type(batch_vectors[0]).__name__}"
            )

        dim = len(batch_vectors[0])
        for idx, vector in enumerate(batch_vectors):
            if not isinstance(vector, list) or len(vector) == 0:
                raise ValueError(
                    "DenseEncoder provider returned invalid vector shape: "
                    f"index={batch_offset + idx}, type={type(vector).__name__}"
                )
            if len(vector) != dim:
                raise ValueError(
                    "DenseEncoder provider returned inconsistent vector dimension within batch: "
                    f"index={batch_offset + idx}, expected={dim}, actual={len(vector)}"
                )
        return dim
