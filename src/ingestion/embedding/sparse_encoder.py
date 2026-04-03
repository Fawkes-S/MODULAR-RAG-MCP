"""SparseEncoder：将 Chunk 批量编码为 BM25 稀疏权重（C9）。"""

from __future__ import annotations

import re
from collections import Counter
from time import perf_counter

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import Chunk, ChunkRecord

_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class SparseEncoder:
    """将 `Chunk` 列表编码为带 `sparse_vector` 的 `ChunkRecord`。

    做什么：
    - 对每个 chunk 文本执行轻量 tokenization，统计词频并输出为 `term -> tf` 的稀疏权重字典。
    - 生成与输入顺序一致的 `ChunkRecord`，保留 `id/text/metadata`，仅补充 `sparse_vector`。
    - 支持按 `batch_size` 分批处理，确保与后续 C10 批处理编排方式一致。

    为什么：
    - C9 的目标是产出可被 BM25Indexer 消费的“term weights 契约”，让 C11 直接基于该结构计算 DF/IDF。
    - 先在编码阶段输出稳定的稀疏表示，可把“文本解析”与“索引构建”职责解耦，降低后续模块耦合度。

    关键权衡：
    - 采用“原始词频 tf（float）”作为权重，而非在此阶段提前做 IDF/BM25 归一化；
      这样 C11 仍能拿到最基础统计信息，避免在 C9 固化过早的评分公式。
    - tokenization 使用统一正则 `\\w+`，追求稳定和可预测，不依赖额外分词库。

    失败路径：
    - 输入不是 `list[Chunk]` 或列表项类型错误：抛 `ValueError`，阻止错误数据进入索引链路。
    - 空文本/仅标点文本：返回空 `sparse_vector`（`{}`），这是显式约定的降级行为，不抛异常。

    Args:
        settings: 全局配置对象，用于读取默认 `ingestion.batch_size`。
        batch_size: 可选批大小；未提供时使用 `settings.ingestion.batch_size`。
    """

    def __init__(self, settings: Settings, batch_size: int | None = None) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("SparseEncoder requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        configured_batch_size = int(settings.ingestion.batch_size)
        self.batch_size = int(batch_size) if batch_size is not None else configured_batch_size
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")

    def encode(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[ChunkRecord]:
        """批量编码 chunk 列表为稀疏权重结构。"""
        normalized_chunks = self._validate_chunks(chunks)
        started = perf_counter()

        if not normalized_chunks:
            if trace is not None:
                trace.record_stage(
                    stage_name="embedding.sparse_encoder",
                    details={
                        "total": 0,
                        "batches": 0,
                        "total_tokens": 0,
                        "non_empty_chunks": 0,
                        "batch_size": self.batch_size,
                        "backend": "bm25",
                    },
                    elapsed_ms=0.0,
                )
            return []

        results: list[ChunkRecord] = []
        total_batches = 0
        total_tokens = 0
        non_empty_chunks = 0

        for offset in range(0, len(normalized_chunks), self.batch_size):
            batch = normalized_chunks[offset : offset + self.batch_size]
            total_batches += 1

            for chunk in batch:
                sparse_vector, token_count = self._build_term_weights(chunk.text)
                total_tokens += token_count
                if sparse_vector:
                    non_empty_chunks += 1

                results.append(
                    ChunkRecord(
                        id=chunk.id,
                        text=chunk.text,
                        metadata=dict(chunk.metadata),
                        dense_vector=None,
                        sparse_vector=sparse_vector,
                    )
                )

        if trace is not None:
            trace.record_stage(
                stage_name="embedding.sparse_encoder",
                details={
                    "total": len(normalized_chunks),
                    "batches": total_batches,
                    "total_tokens": total_tokens,
                    "non_empty_chunks": non_empty_chunks,
                    "batch_size": self.batch_size,
                    "backend": "bm25",
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return results

    @staticmethod
    def _validate_chunks(chunks: list[Chunk]) -> list[Chunk]:
        """校验输入 shape，保证稀疏编码契约的可预测性。"""
        if not isinstance(chunks, list):
            raise ValueError("chunks must be list[Chunk]")

        for idx, chunk in enumerate(chunks):
            if not isinstance(chunk, Chunk):
                raise ValueError(f"chunks[{idx}] must be Chunk")

        return chunks

    @staticmethod
    def _build_term_weights(text: str) -> tuple[dict[str, float], int]:
        """从文本构建 BM25 基础统计所需的词频字典。

        返回值说明：
        - `sparse_vector`：`term -> tf`（float），供后续 C11 计算 DF/IDF 和倒排索引。
        - `token_count`：文档长度（词级别），用于 trace 统计和后续评分数据准备。
        """
        tokens = [token for token in _TOKEN_PATTERN.findall(text.lower()) if token.strip("_")]
        if not tokens:
            return {}, 0

        counts = Counter(tokens)
        # 对 term 做排序，保证序列化与测试断言稳定。
        sparse_vector = {term: float(freq) for term, freq in sorted(counts.items())}
        return sparse_vector, len(tokens)
