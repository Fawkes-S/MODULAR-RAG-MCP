"""VectorUpserter 单元测试（C12）。"""

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
from core.types import ChunkRecord  # noqa: E402
from ingestion.storage.vector_upserter import VectorUpserter  # noqa: E402
from libs.vector_store.base_vector_store import BaseVectorStore  # noqa: E402


class _FakeVectorStore(BaseVectorStore):
    """用于断言 upsert payload 的内存假实现。"""

    def __init__(self) -> None:
        self.upsert_calls: list[list[dict[str, Any]]] = []

    def upsert(self, records: list[dict[str, Any]], trace: Any | None = None) -> None:
        _ = trace
        self.upsert_calls.append(list(records))

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        _ = vector, top_k, filters, trace
        return []


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


def _make_record(
    *,
    chunk_id: str,
    text: str,
    source_path: str = "memory://doc.md",
    chunk_index: int | str | None = 0,
    dense_vector: list[float] | None = None,
) -> ChunkRecord:
    metadata: dict[str, object] = {"source_path": source_path, "doc_type": "md"}
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index

    return ChunkRecord(
        id=chunk_id,
        text=text,
        metadata=metadata,
        dense_vector=dense_vector or [0.1, 0.2, 0.3],
        sparse_vector={"token": 1.0},
    )


def test_vector_upserter_returns_same_id_for_same_content_twice() -> None:
    """
    Given:
        同一个 chunk（相同 source_path/chunk_index/text）被连续 upsert 两次。
    When:
        两次调用 `VectorUpserter.upsert()`。
    Then:
        两次返回的存储 ID 应完全一致，满足幂等写入要求。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    record = _make_record(chunk_id="doc_0000_aaaa1111", text="same content", chunk_index=0)

    first_ids = upserter.upsert([record])
    second_ids = upserter.upsert([record])

    assert first_ids == second_ids
    assert len(fake_store.upsert_calls) == 2
    assert fake_store.upsert_calls[0][0]["id"] == fake_store.upsert_calls[1][0]["id"]


def test_vector_upserter_changes_id_when_content_changes() -> None:
    """
    Given:
        两条记录具有相同 source_path/chunk_index，但正文内容不同。
    When:
        分别执行 upsert。
    Then:
        生成的存储 ID 应不同，确保“内容变化 -> 新版本主键变化”。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    old_record = _make_record(chunk_id="doc_0001_bbbb2222", text="old", chunk_index=1)
    new_record = _make_record(chunk_id="doc_0001_cccc3333", text="new", chunk_index=1)

    old_id = upserter.upsert([old_record])[0]
    new_id = upserter.upsert([new_record])[0]

    assert old_id != new_id


def test_vector_upserter_supports_batch_upsert_and_preserves_order() -> None:
    """
    Given:
        一个 3 条记录的 batch 输入，记录顺序为 c1 -> c2 -> c3。
    When:
        调用一次 `upsert(records)` 批量写入。
    Then:
        返回 ID 顺序与输入顺序一致，且 payload 中每条 metadata 都带有 source_chunk_id/chunk_id。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    records = [
        _make_record(chunk_id="doc_0000_aaaa1111", text="alpha", chunk_index=0),
        _make_record(chunk_id="doc_0001_bbbb2222", text="beta", chunk_index=1),
        _make_record(chunk_id="doc_0002_cccc3333", text="gamma", chunk_index=2),
    ]

    ids = upserter.upsert(records)

    assert len(ids) == 3
    assert len(fake_store.upsert_calls) == 1
    payload = fake_store.upsert_calls[0]
    assert [item["metadata"]["source_chunk_id"] for item in payload] == [record.id for record in records]
    assert [item["id"] for item in payload] == ids
    assert [item["metadata"]["chunk_id"] for item in payload] == ids


def test_vector_upserter_can_fallback_to_parse_chunk_index_from_chunk_id() -> None:
    """
    Given:
        metadata 中缺失 `chunk_index`，但 record.id 符合 `doc_0003_xxx` 模式。
    When:
        调用 upsert。
    Then:
        组件应能从上游 ID 解析出 chunk_index 并成功生成稳定存储 ID。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    record = _make_record(chunk_id="doc_0003_ffff9999", text="needs fallback", chunk_index=None)

    ids = upserter.upsert([record])

    assert len(ids) == 1
    assert ids[0].startswith("chunk_")


def test_vector_upserter_raises_when_source_path_missing() -> None:
    """
    Given:
        输入记录的 metadata 被破坏，缺失 `source_path`。
    When:
        调用 upsert。
    Then:
        应抛出 ValueError，阻止生成不可靠的存储主键。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    record = _make_record(chunk_id="doc_0000_aaaa1111", text="broken")
    record.metadata.pop("source_path", None)

    with pytest.raises(ValueError, match="missing metadata.source_path"):
        upserter.upsert([record])


def test_vector_upserter_records_trace_stage_details() -> None:
    """
    Given:
        一次正常 upsert 调用与 TraceContext。
    When:
        调用 `upsert(records, trace=...)`。
    Then:
        trace 中应新增 `storage.vector_upserter` 阶段，并记录 total/upserted/provider。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    trace = TraceContext(trace_type="ingestion")

    upserter.upsert([_make_record(chunk_id="doc_0000_aaaa1111", text="trace-case")], trace=trace)

    assert trace.stages
    stage = trace.stages[-1]
    assert stage["stage_name"] == "storage.vector_upserter"
    assert stage["details"]["total"] == 1
    assert stage["details"]["upserted"] == 1
    assert stage["details"]["provider"] == "chroma"
    assert "elapsed_ms" in stage

def test_vector_upserter_serializes_complex_metadata_for_vector_store_compatibility() -> None:
    """
    Given:
        metadata 中包含 `list[dict]` 等 Chroma 不接受的复杂结构。
    When:
        调用 `upsert()` 构建实际写入 payload。
    Then:
        复杂字段应被序列化为字符串，避免向量库 metadata 校验报错。
    """
    fake_store = _FakeVectorStore()
    upserter = VectorUpserter(settings=_make_settings(), vector_store=fake_store)
    record = _make_record(chunk_id="doc_0000_aaaa1111", text="complex-meta", chunk_index=0)
    record.metadata["heading_outline"] = [{"level": 1, "title": "Overview"}]
    record.metadata["images"] = [{"id": "img_1", "path": "data/images/img_1.png"}]
    record.metadata["tags"] = ["rag", "pipeline"]

    upserter.upsert([record])

    payload_meta = fake_store.upsert_calls[0][0]["metadata"]
    assert isinstance(payload_meta["heading_outline"], str)
    assert isinstance(payload_meta["images"], str)
    assert isinstance(payload_meta["tags"], list)
