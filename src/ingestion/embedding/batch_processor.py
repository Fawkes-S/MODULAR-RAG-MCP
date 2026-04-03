"""BatchProcessor：批处理编排 dense/sparse 编码（C10）。"""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import Chunk, ChunkRecord
from ingestion.embedding.dense_encoder import DenseEncoder
from ingestion.embedding.sparse_encoder import SparseEncoder


class _RecordEncoder(Protocol):
    """编码器协议：输入 `Chunk`，输出对应顺序的 `ChunkRecord`。"""

    def encode(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[ChunkRecord]:
        ...


class BatchProcessor:
    """按批编排 Dense/Sparse 编码并合并为统一记录。

    做什么：
    - 将输入 chunk 列表按 `batch_size` 分批，逐批调用 `DenseEncoder` 与 `SparseEncoder`。
    - 对每批结果执行数量与 ID 对齐校验，合并为同时包含 dense/sparse 向量的 `ChunkRecord`。
    - 记录批次级与整体级耗时统计，供后续 Trace 可视化与性能优化使用。

    为什么：
    - C8/C9 已分别完成 dense/sparse 编码，C10 负责“编排层”把两路编码稳定串起来。
    - 先固化批处理契约，可以让后续 C11/C12 专注索引和存储，不再关心编码协同细节。

    关键权衡：
    - 采用“外层批处理 + 内层编码器复用”策略：优先复用现有编码器实现，降低重复逻辑。
    - 合并阶段执行严格对齐校验，宁可快速失败，也不静默写入错位向量。

    失败路径：
    - 输入不是 `list[Chunk]` 或元素类型错误：抛 `ValueError`。
    - dense/sparse 编码返回数量不匹配或 ID 不一致：抛 `ValueError`。
    - dense/sparse 向量缺失：抛 `ValueError`，阻止坏数据流入下游。

    Args:
        settings: 全局配置对象，用于读取默认 `ingestion.batch_size`。
        dense_encoder: 可注入稠密编码器（测试/定制场景）。
        sparse_encoder: 可注入稀疏编码器（测试/定制场景）。
        batch_size: 可选批大小；未提供时使用 `settings.ingestion.batch_size`。
    """

    def __init__(
        self,
        settings: Settings,
        dense_encoder: _RecordEncoder | None = None,
        sparse_encoder: _RecordEncoder | None = None,
        batch_size: int | None = None,
    ) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("BatchProcessor requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        configured_batch_size = int(settings.ingestion.batch_size)
        self.batch_size = int(batch_size) if batch_size is not None else configured_batch_size
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        self.dense_encoder = dense_encoder or DenseEncoder(settings=settings, batch_size=self.batch_size)
        self.sparse_encoder = sparse_encoder or SparseEncoder(settings=settings, batch_size=self.batch_size)

    def process(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[ChunkRecord]:
        """对输入 chunks 执行双路批处理编码并合并结果。"""
        normalized_chunks = self._validate_chunks(chunks)
        started = perf_counter()

        if not normalized_chunks:
            if trace is not None:
                trace.record_stage(
                    stage_name="embedding.batch_processor",
                    details={
                        "total": 0,
                        "batches": 0,
                        "batch_size": self.batch_size,
                        "dense_stage": "embedding.dense_encoder",
                        "sparse_stage": "embedding.sparse_encoder",
                    },
                    elapsed_ms=0.0,
                )
            return []

        merged_records: list[ChunkRecord] = []
        total_batches = 0
        total_dense_elapsed = 0.0
        total_sparse_elapsed = 0.0

        for batch_index, batch in enumerate(self._iter_batches(normalized_chunks), start=1):
            batch_started = perf_counter()

            dense_started = perf_counter()
            dense_records = self.dense_encoder.encode(batch, trace=trace)
            dense_elapsed = (perf_counter() - dense_started) * 1000.0
            total_dense_elapsed += dense_elapsed

            sparse_started = perf_counter()
            sparse_records = self.sparse_encoder.encode(batch, trace=trace)
            sparse_elapsed = (perf_counter() - sparse_started) * 1000.0
            total_sparse_elapsed += sparse_elapsed

            merged_batch = self._merge_batch_records(
                batch=batch,
                dense_records=dense_records,
                sparse_records=sparse_records,
                batch_index=batch_index,
            )
            merged_records.extend(merged_batch)
            total_batches += 1

            if trace is not None:
                trace.record_stage(
                    stage_name="embedding.batch_processor.batch",
                    details={
                        "batch_index": batch_index,
                        "batch_size": len(batch),
                        "dense_elapsed_ms": dense_elapsed,
                        "sparse_elapsed_ms": sparse_elapsed,
                    },
                    elapsed_ms=(perf_counter() - batch_started) * 1000.0,
                )

        if trace is not None:
            trace.record_stage(
                stage_name="embedding.batch_processor",
                details={
                    "total": len(normalized_chunks),
                    "batches": total_batches,
                    "batch_size": self.batch_size,
                    "dense_total_elapsed_ms": total_dense_elapsed,
                    "sparse_total_elapsed_ms": total_sparse_elapsed,
                    "dense_stage": "embedding.dense_encoder",
                    "sparse_stage": "embedding.sparse_encoder",
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return merged_records

    @staticmethod
    def _validate_chunks(chunks: list[Chunk]) -> list[Chunk]:
        """校验输入 shape，避免编排层接收非法数据。"""
        if not isinstance(chunks, list):
            raise ValueError("chunks must be list[Chunk]")

        for idx, chunk in enumerate(chunks):
            if not isinstance(chunk, Chunk):
                raise ValueError(f"chunks[{idx}] must be Chunk")

        return chunks

    def _iter_batches(self, chunks: list[Chunk]) -> list[list[Chunk]]:
        """按配置批大小切分输入列表，保持原始顺序。"""
        return [chunks[offset : offset + self.batch_size] for offset in range(0, len(chunks), self.batch_size)]

    @staticmethod
    def _merge_batch_records(
        batch: list[Chunk],
        dense_records: list[ChunkRecord],
        sparse_records: list[ChunkRecord],
        batch_index: int,
    ) -> list[ChunkRecord]:
        """合并单批次 dense/sparse 编码结果。

        约束：
        - dense 与 sparse 输出数量必须与 batch 完全一致。
        - 三方 ID 必须逐位置一致，确保上游/下游不会发生错位写入。
        """
        if len(dense_records) != len(batch):
            raise ValueError(
                "BatchProcessor dense result count mismatch: "
                f"batch_index={batch_index}, expected={len(batch)}, actual={len(dense_records)}"
            )
        if len(sparse_records) != len(batch):
            raise ValueError(
                "BatchProcessor sparse result count mismatch: "
                f"batch_index={batch_index}, expected={len(batch)}, actual={len(sparse_records)}"
            )

        merged: list[ChunkRecord] = []
        for row_index, (chunk, dense, sparse) in enumerate(zip(batch, dense_records, sparse_records), start=1):
            if dense.id != chunk.id or sparse.id != chunk.id:
                raise ValueError(
                    "BatchProcessor record id mismatch: "
                    f"batch_index={batch_index}, row_index={row_index}, "
                    f"chunk_id={chunk.id}, dense_id={dense.id}, sparse_id={sparse.id}"
                )
            if dense.dense_vector is None:
                raise ValueError(
                    "BatchProcessor dense_vector missing: "
                    f"batch_index={batch_index}, row_index={row_index}, id={chunk.id}"
                )
            if sparse.sparse_vector is None:
                raise ValueError(
                    "BatchProcessor sparse_vector missing: "
                    f"batch_index={batch_index}, row_index={row_index}, id={chunk.id}"
                )

            merged.append(
                ChunkRecord(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    dense_vector=list(dense.dense_vector),
                    sparse_vector=dict(sparse.sparse_vector),
                )
            )

        return merged
