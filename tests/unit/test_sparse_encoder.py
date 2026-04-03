"""SparseEncoder 单元测试（C9）。"""

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
from ingestion.embedding.sparse_encoder import SparseEncoder  # noqa: E402


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
        source_ref="doc_sparse",
    )


def test_sparse_encoder_outputs_term_weights_for_bm25_contract() -> None:
    """
    Given:
        两个有效 chunk，内容分别包含英文重复词与中文重复词。
    When:
        调用 `SparseEncoder.encode()` 执行稀疏编码。
    Then:
        输出应是可供 BM25Indexer 消费的 `term -> tf(float)` 结构，且数量与输入一致。
    """
    encoder = SparseEncoder(settings=_make_settings(), batch_size=10)
    chunks = [_make_chunk("c1", "Alpha beta alpha BM25"), _make_chunk("c2", "中文 检索 中文")]

    records = encoder.encode(chunks)

    assert len(records) == 2
    assert all(isinstance(record, ChunkRecord) for record in records)

    assert records[0].dense_vector is None
    assert records[0].sparse_vector == {"alpha": 2.0, "beta": 1.0, "bm25": 1.0}

    assert records[1].dense_vector is None
    assert records[1].sparse_vector == {"中文": 2.0, "检索": 1.0}


def test_sparse_encoder_batches_and_preserves_order() -> None:
    """
    Given:
        `batch_size=2` 且输入 5 个 chunk。
    When:
        执行稀疏编码。
    Then:
        输出顺序应与输入稳定一致，确保后续批处理/存储阶段可按同序对齐。
    """
    encoder = SparseEncoder(settings=_make_settings(), batch_size=2)
    chunks = [_make_chunk(f"c{i}", f"token-{i} token") for i in range(1, 6)]

    records = encoder.encode(chunks)

    assert [record.id for record in records] == [chunk.id for chunk in chunks]
    assert all(record.sparse_vector for record in records)


def test_sparse_encoder_preserves_chunk_identity_and_metadata() -> None:
    """
    Given:
        带固定 id/source_ref/metadata 的 chunk。
    When:
        稀疏编码后生成 `ChunkRecord`。
    Then:
        `id/text/metadata` 应保持语义一致，仅新增 `sparse_vector`。
    """
    encoder = SparseEncoder(settings=_make_settings(), batch_size=10)
    chunk = _make_chunk("identity", "keep identity")

    record = encoder.encode([chunk])[0]

    assert record.id == chunk.id
    assert record.text == chunk.text
    assert record.metadata["source_path"] == chunk.metadata["source_path"]
    assert record.dense_vector is None
    assert record.sparse_vector == {"identity": 1.0, "keep": 1.0}


def test_sparse_encoder_empty_or_punctuation_text_returns_empty_vector() -> None:
    """
    Given:
        空文本、仅空白文本与仅标点文本。
    When:
        执行稀疏编码。
    Then:
        `sparse_vector` 应为空字典 `{}`，这是 C9 约定的明确行为。
    """
    encoder = SparseEncoder(settings=_make_settings(), batch_size=10)
    chunks = [_make_chunk("empty", ""), _make_chunk("blank", "   \n\t  "), _make_chunk("punct", "!!! ??? ...")]

    records = encoder.encode(chunks)

    assert [record.sparse_vector for record in records] == [{}, {}, {}]


def test_sparse_encoder_rejects_non_list_input() -> None:
    """
    Given:
        非 `list[Chunk]` 的非法输入。
    When:
        调用 `encode()`。
    Then:
        应抛出 ValueError，阻止错误 shape 进入编码阶段。
    """
    encoder = SparseEncoder(settings=_make_settings())

    with pytest.raises(ValueError, match="chunks must be list"):
        encoder.encode("not-a-list")  # type: ignore[arg-type]


def test_sparse_encoder_rejects_non_chunk_items() -> None:
    """
    Given:
        list 中混入非 Chunk 元素。
    When:
        调用 `encode()`。
    Then:
        应抛出 ValueError 并明确指出非法元素位置。
    """
    encoder = SparseEncoder(settings=_make_settings())

    with pytest.raises(ValueError, match=r"chunks\[0\] must be Chunk"):
        encoder.encode([{"id": "x"}])  # type: ignore[list-item]


def test_sparse_encoder_records_trace_stage_details() -> None:
    """
    Given:
        2 个 chunk 与一个 TraceContext。
    When:
        调用 `encode(chunks, trace=...)`。
    Then:
        trace 中应新增 `embedding.sparse_encoder` 阶段，并包含总数/批次/token 统计。
    """
    encoder = SparseEncoder(settings=_make_settings(), batch_size=2)
    trace = TraceContext(trace_type="ingestion")

    encoder.encode([_make_chunk("c1", "alpha beta"), _make_chunk("c2", "beta")], trace=trace)

    assert trace.stages
    stage = trace.stages[-1]
    assert stage["stage_name"] == "embedding.sparse_encoder"
    assert stage["details"]["total"] == 2
    assert stage["details"]["batches"] == 1
    assert stage["details"]["total_tokens"] == 3
    assert stage["details"]["backend"] == "bm25"
    assert "elapsed_ms" in stage


def test_sparse_encoder_returns_empty_list_for_empty_input() -> None:
    """
    Given:
        空 chunk 列表。
    When:
        调用 `encode()`。
    Then:
        应返回空列表，且不抛出异常。
    """
    encoder = SparseEncoder(settings=_make_settings(), batch_size=2)

    records = encoder.encode([])

    assert records == []
