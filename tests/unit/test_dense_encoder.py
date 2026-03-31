"""DenseEncoder 单元测试（C8）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
from ingestion.embedding.dense_encoder import DenseEncoder  # noqa: E402
from libs.embedding.base_embedding import BaseEmbedding  # noqa: E402


class _FakeEmbedding(BaseEmbedding):
    """可控 embedding 假实现，支持记录调用和自定义输出。"""

    def __init__(self, vectors_per_call: list[list[list[float]]] | None = None) -> None:
        self.vectors_per_call = vectors_per_call or []
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        self.calls.append(list(texts))
        _ = trace
        if self.vectors_per_call:
            return self.vectors_per_call.pop(0)

        # 默认：基于文本长度生成稳定三维向量。
        vectors: list[list[float]] = []
        for idx, text in enumerate(texts):
            vectors.append([float(len(text)), float(idx), 1.0])
        return vectors


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
        source_ref="doc_dense",
    )


def test_dense_encoder_outputs_count_and_dimension_consistent() -> None:
    """
    Given:
        3 个有效 chunk，FakeEmbedding 返回每条三维向量。
    When:
        调用 `DenseEncoder.encode()` 执行编码。
    Then:
        输出 `ChunkRecord` 数量与输入一致，且每条 `dense_vector` 维度一致。
    """
    encoder = DenseEncoder(settings=_make_settings(), embedding=_FakeEmbedding(), batch_size=10)
    chunks = [_make_chunk("c1", "alpha"), _make_chunk("c2", "beta"), _make_chunk("c3", "gamma")]

    records = encoder.encode(chunks)

    assert len(records) == 3
    assert all(isinstance(record, ChunkRecord) for record in records)
    assert all(record.dense_vector is not None for record in records)
    assert all(len(record.dense_vector or []) == 3 for record in records)


def test_dense_encoder_batches_requests_and_preserves_order() -> None:
    """
    Given:
        `batch_size=2` 且输入 5 个 chunk。
    When:
        执行编码。
    Then:
        embedding 应被调用 3 次（2/2/1），且输出顺序与输入 chunk 顺序一致。
    """
    fake = _FakeEmbedding(
        vectors_per_call=[
            [[1.0, 0.0, 1.0], [2.0, 0.0, 1.0]],
            [[3.0, 0.0, 1.0], [4.0, 0.0, 1.0]],
            [[5.0, 0.0, 1.0]],
        ]
    )
    encoder = DenseEncoder(settings=_make_settings(), embedding=fake, batch_size=2)
    chunks = [_make_chunk(f"c{i}", f"text-{i}") for i in range(1, 6)]

    records = encoder.encode(chunks)

    assert [len(call) for call in fake.calls] == [2, 2, 1]
    assert [record.id for record in records] == [chunk.id for chunk in chunks]


def test_dense_encoder_preserves_chunk_identity_and_metadata() -> None:
    """
    Given:
        带固定 id/source_ref/metadata 的 chunk。
    When:
        编码后生成 `ChunkRecord`。
    Then:
        `id/text/metadata` 应保持语义一致，仅新增 `dense_vector`。
    """
    encoder = DenseEncoder(settings=_make_settings(), embedding=_FakeEmbedding(), batch_size=10)
    chunk = _make_chunk("identity", "hello dense")

    record = encoder.encode([chunk])[0]

    assert record.id == chunk.id
    assert record.text == chunk.text
    assert record.metadata["source_path"] == chunk.metadata["source_path"]
    assert record.sparse_vector is None
    assert record.dense_vector is not None


def test_dense_encoder_rejects_non_list_input() -> None:
    """
    Given:
        非 `list[Chunk]` 的非法输入。
    When:
        调用 `encode()`。
    Then:
        应抛出 ValueError，阻止错误 shape 进入编码阶段。
    """
    encoder = DenseEncoder(settings=_make_settings(), embedding=_FakeEmbedding())

    with pytest.raises(ValueError, match="chunks must be list"):
        encoder.encode("not-a-list")  # type: ignore[arg-type]


def test_dense_encoder_rejects_non_chunk_items() -> None:
    """
    Given:
        list 中混入非 Chunk 元素。
    When:
        调用 `encode()`。
    Then:
        应抛出 ValueError 并明确指出非法元素位置。
    """
    encoder = DenseEncoder(settings=_make_settings(), embedding=_FakeEmbedding())

    with pytest.raises(ValueError, match=r"chunks\[0\] must be Chunk"):
        encoder.encode([{"id": "x"}])  # type: ignore[list-item]


def test_dense_encoder_raises_when_vector_count_mismatch() -> None:
    """
    Given:
        一个 batch 输入 2 条文本，但 embedding 仅返回 1 条向量。
    When:
        执行编码。
    Then:
        应抛出 ValueError，避免静默写入错位向量。
    """
    fake = _FakeEmbedding(vectors_per_call=[[[1.0, 0.0, 1.0]]])
    encoder = DenseEncoder(settings=_make_settings(), embedding=fake, batch_size=2)

    with pytest.raises(ValueError, match="vector count mismatch"):
        encoder.encode([_make_chunk("c1", "a"), _make_chunk("c2", "b")])


def test_dense_encoder_raises_when_vector_dimension_inconsistent() -> None:
    """
    Given:
        第一个 batch 返回三维向量，第二个 batch 返回二维向量。
    When:
        执行多批次编码。
    Then:
        应抛出 ValueError，阻止维度不一致的数据流入后续存储。
    """
    fake = _FakeEmbedding(
        vectors_per_call=[
            [[1.0, 0.0, 1.0], [2.0, 0.0, 1.0]],
            [[3.0, 0.0]],
        ]
    )
    encoder = DenseEncoder(settings=_make_settings(), embedding=fake, batch_size=2)

    with pytest.raises(ValueError, match="inconsistent vector dimension across batches"):
        encoder.encode([_make_chunk("c1", "a"), _make_chunk("c2", "b"), _make_chunk("c3", "c")])


def test_dense_encoder_records_trace_stage_details() -> None:
    """
    Given:
        2 个 chunk 和一个 TraceContext。
    When:
        调用 `encode(chunks, trace=...)`。
    Then:
        trace 中应新增 `embedding.dense_encoder` 阶段，并包含总数/批次/维度统计。
    """
    encoder = DenseEncoder(settings=_make_settings(), embedding=_FakeEmbedding(), batch_size=2)
    trace = TraceContext(trace_type="ingestion")

    encoder.encode([_make_chunk("c1", "alpha"), _make_chunk("c2", "beta")], trace=trace)

    assert trace.stages
    stage = trace.stages[-1]
    assert stage["stage_name"] == "embedding.dense_encoder"
    assert stage["details"]["total"] == 2
    assert stage["details"]["batches"] == 1
    assert stage["details"]["vector_dim"] == 3
    assert "elapsed_ms" in stage


def test_dense_encoder_returns_empty_list_for_empty_input() -> None:
    """
    Given:
        空 chunk 列表。
    When:
        调用 `encode()`。
    Then:
        应返回空列表，且不调用 embedding 客户端。
    """
    fake = _FakeEmbedding()
    encoder = DenseEncoder(settings=_make_settings(), embedding=fake, batch_size=2)

    records = encoder.encode([])

    assert records == []
    assert fake.calls == []
