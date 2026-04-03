"""BatchProcessor 单元测试（C10）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import (  # noqa: E402
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
)
from core.trace.trace_context import TraceContext  # noqa: E402
from core.types import Chunk, ChunkRecord  # noqa: E402
from ingestion.embedding.batch_processor import BatchProcessor  # noqa: E402


class _FakeDenseEncoder:
    """可控 dense 编码器假实现，用于验证批处理编排行为。"""

    def __init__(self, *, drop_last_on_call: int | None = None, id_suffix: str = "") -> None:
        self.calls: list[list[str]] = []
        self._call_count = 0
        self._drop_last_on_call = drop_last_on_call
        self._id_suffix = id_suffix

    def encode(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[ChunkRecord]:
        _ = trace
        self._call_count += 1
        self.calls.append([chunk.id for chunk in chunks])

        records: list[ChunkRecord] = []
        for chunk in chunks:
            records.append(
                ChunkRecord(
                    id=f"{chunk.id}{self._id_suffix}",
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    dense_vector=[float(len(chunk.text)), 1.0],
                    sparse_vector=None,
                )
            )

        if self._drop_last_on_call is not None and self._call_count == self._drop_last_on_call and records:
            return records[:-1]
        return records


class _FakeSparseEncoder:
    """可控 sparse 编码器假实现，用于验证批处理编排行为。"""

    def __init__(self, *, drop_last_on_call: int | None = None, id_suffix: str = "") -> None:
        self.calls: list[list[str]] = []
        self._call_count = 0
        self._drop_last_on_call = drop_last_on_call
        self._id_suffix = id_suffix

    def encode(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[ChunkRecord]:
        _ = trace
        self._call_count += 1
        self.calls.append([chunk.id for chunk in chunks])

        records: list[ChunkRecord] = []
        for chunk in chunks:
            records.append(
                ChunkRecord(
                    id=f"{chunk.id}{self._id_suffix}",
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    dense_vector=None,
                    sparse_vector={"token": 1.0, chunk.id: 1.0},
                )
            )

        if self._drop_last_on_call is not None and self._call_count == self._drop_last_on_call and records:
            return records[:-1]
        return records


def _make_settings() -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=5, sparse_top_k=10),
        rerank=RerankSettings(provider="none", enabled=False, top_m=10),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(batch_size=2),
    )


def _make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        metadata={"source_path": f"memory://{chunk_id}.md", "doc_type": "md"},
        start_offset=0,
        end_offset=max(len(text), 0),
        source_ref="doc_batch",
    )


def test_batch_processor_splits_to_three_batches_and_preserves_order() -> None:
    """
    Given:
        `batch_size=2` 且输入 5 个 chunk。
    When:
        调用 `BatchProcessor.process()` 进行批处理编排。
    Then:
        dense/sparse 编码器都应被按 2/2/1 调用，共 3 批，且输出顺序与输入一致。
    """
    dense = _FakeDenseEncoder()
    sparse = _FakeSparseEncoder()
    processor = BatchProcessor(settings=_make_settings(), dense_encoder=dense, sparse_encoder=sparse, batch_size=2)
    chunks = [_make_chunk(f"c{i}", f"text-{i}") for i in range(1, 6)]

    records = processor.process(chunks)

    assert [len(call) for call in dense.calls] == [2, 2, 1]
    assert [len(call) for call in sparse.calls] == [2, 2, 1]
    assert [record.id for record in records] == [chunk.id for chunk in chunks]


def test_batch_processor_merges_dense_and_sparse_vectors() -> None:
    """
    Given:
        dense/sparse 编码器都返回与输入一一对应的记录。
    When:
        执行批处理。
    Then:
        输出记录应同时包含 `dense_vector` 与 `sparse_vector`，满足后续存储阶段契约。
    """
    processor = BatchProcessor(
        settings=_make_settings(),
        dense_encoder=_FakeDenseEncoder(),
        sparse_encoder=_FakeSparseEncoder(),
        batch_size=4,
    )

    records = processor.process([_make_chunk("c1", "alpha beta")])

    assert len(records) == 1
    assert records[0].dense_vector == [10.0, 1.0]
    assert records[0].sparse_vector == {"token": 1.0, "c1": 1.0}


def test_batch_processor_raises_when_dense_count_mismatch() -> None:
    """
    Given:
        dense 编码器在首批少返回一条记录。
    When:
        执行批处理。
    Then:
        应抛出 ValueError，阻止错位数据进入合并流程。
    """
    processor = BatchProcessor(
        settings=_make_settings(),
        dense_encoder=_FakeDenseEncoder(drop_last_on_call=1),
        sparse_encoder=_FakeSparseEncoder(),
        batch_size=2,
    )

    with pytest.raises(ValueError, match="dense result count mismatch"):
        processor.process([_make_chunk("c1", "a"), _make_chunk("c2", "b")])


def test_batch_processor_raises_when_sparse_count_mismatch() -> None:
    """
    Given:
        sparse 编码器在首批少返回一条记录。
    When:
        执行批处理。
    Then:
        应抛出 ValueError，保证 dense/sparse 结果严格对齐。
    """
    processor = BatchProcessor(
        settings=_make_settings(),
        dense_encoder=_FakeDenseEncoder(),
        sparse_encoder=_FakeSparseEncoder(drop_last_on_call=1),
        batch_size=2,
    )

    with pytest.raises(ValueError, match="sparse result count mismatch"):
        processor.process([_make_chunk("c1", "a"), _make_chunk("c2", "b")])


def test_batch_processor_raises_when_record_id_mismatch() -> None:
    """
    Given:
        dense 编码器返回的记录 ID 与输入 chunk ID 不一致。
    When:
        执行批处理合并。
    Then:
        应抛出 ValueError 并明确提示 ID 错位。
    """
    processor = BatchProcessor(
        settings=_make_settings(),
        dense_encoder=_FakeDenseEncoder(id_suffix="-x"),
        sparse_encoder=_FakeSparseEncoder(),
        batch_size=2,
    )

    with pytest.raises(ValueError, match="record id mismatch"):
        processor.process([_make_chunk("c1", "a")])


def test_batch_processor_rejects_non_list_input() -> None:
    """
    Given:
        非 `list[Chunk]` 的非法输入。
    When:
        调用 `process()`。
    Then:
        应抛出 ValueError，阻止错误 shape 进入编排流程。
    """
    processor = BatchProcessor(settings=_make_settings(), dense_encoder=_FakeDenseEncoder(), sparse_encoder=_FakeSparseEncoder())

    with pytest.raises(ValueError, match="chunks must be list"):
        processor.process("not-a-list")  # type: ignore[arg-type]


def test_batch_processor_rejects_non_chunk_items() -> None:
    """
    Given:
        list 中混入非 Chunk 元素。
    When:
        调用 `process()`。
    Then:
        应抛出 ValueError 并明确非法元素位置。
    """
    processor = BatchProcessor(settings=_make_settings(), dense_encoder=_FakeDenseEncoder(), sparse_encoder=_FakeSparseEncoder())

    with pytest.raises(ValueError, match=r"chunks\[0\] must be Chunk"):
        processor.process([{"id": "bad"}])  # type: ignore[list-item]


def test_batch_processor_records_batch_timing_trace() -> None:
    """
    Given:
        3 个 chunk、`batch_size=2` 与 TraceContext。
    When:
        调用 `process(chunks, trace=...)`。
    Then:
        trace 中应包含批次级与汇总级的 `embedding.batch_processor` 统计信息。
    """
    processor = BatchProcessor(
        settings=_make_settings(),
        dense_encoder=_FakeDenseEncoder(),
        sparse_encoder=_FakeSparseEncoder(),
        batch_size=2,
    )
    trace = TraceContext(trace_type="ingestion")

    processor.process([_make_chunk("c1", "a"), _make_chunk("c2", "b"), _make_chunk("c3", "c")], trace=trace)

    batch_stages = [stage for stage in trace.stages if stage["stage_name"] == "embedding.batch_processor.batch"]
    summary_stages = [stage for stage in trace.stages if stage["stage_name"] == "embedding.batch_processor"]

    assert len(batch_stages) == 2
    assert summary_stages
    assert summary_stages[-1]["details"]["total"] == 3
    assert summary_stages[-1]["details"]["batches"] == 2
    assert "elapsed_ms" in summary_stages[-1]


def test_batch_processor_returns_empty_for_empty_input() -> None:
    """
    Given:
        空 chunk 列表。
    When:
        调用 `process()`。
    Then:
        应返回空列表，且不会触发编码器调用。
    """
    dense = _FakeDenseEncoder()
    sparse = _FakeSparseEncoder()
    processor = BatchProcessor(settings=_make_settings(), dense_encoder=dense, sparse_encoder=sparse, batch_size=2)

    records = processor.process([])

    assert records == []
    assert dense.calls == []
    assert sparse.calls == []
