"""IngestionPipeline 进度回调测试（F5）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import (  # noqa: E402
    ChunkRefinerSettings,
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    MetadataEnricherSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
    VisionLLMSettings,
)
from core.types import Chunk, ChunkRecord, Document  # noqa: E402
from ingestion.pipeline import IngestionPipeline  # noqa: E402
from libs.loader.base_loader import BaseLoader  # noqa: E402
from libs.loader.file_integrity import FileIntegrityChecker  # noqa: E402


class _FakeIntegrityChecker(FileIntegrityChecker):
    """测试桩：稳定返回 hash/skip 结果，避免触发真实 SQLite。"""

    def __init__(self, should_skip: bool = False) -> None:
        self.should_skip_value = should_skip
        self.success_calls: list[dict[str, Any]] = []
        self.failed_calls: list[dict[str, Any]] = []

    def compute_sha256(self, path: str) -> str:
        return f"hash::{Path(path).name}"

    def should_skip(self, file_hash: str) -> bool:
        _ = file_hash
        return self.should_skip_value

    def mark_success(self, file_hash: str, file_path: str, file_size: int, chunk_count: int) -> None:
        self.success_calls.append(
            {
                "file_hash": file_hash,
                "file_path": file_path,
                "file_size": file_size,
                "chunk_count": chunk_count,
            }
        )

    def mark_failed(self, file_hash: str, error_msg: str, file_path: str, file_size: int) -> None:
        self.failed_calls.append(
            {
                "file_hash": file_hash,
                "error_msg": error_msg,
                "file_path": file_path,
                "file_size": file_size,
            }
        )


class _FakeLoader(BaseLoader):
    """测试桩：返回固定 Document。"""

    def load(self, path: str) -> Document:
        return Document(
            id="pdf_demo",
            text="# Demo\n\nAzure OpenAI progress callback demo.",
            metadata={"source_path": str(Path(path).resolve()), "doc_type": "pdf"},
        )


class _FakeChunker:
    """测试桩：把文档稳定切成一个 Chunk。"""

    def split_document(self, document: Document) -> list[Chunk]:
        return [
            Chunk(
                id="pdf_demo_0000_abcd1234",
                text=document.text,
                metadata=dict(document.metadata),
                start_offset=0,
                end_offset=len(document.text),
                source_ref=document.id,
            )
        ]


class _FakeTransform:
    """测试桩：模拟 transform 链中的单个步骤。"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def transform(self, chunks: list[Chunk], trace: Any | None = None) -> list[Chunk]:
        _ = trace
        self.calls += 1
        updated: list[Chunk] = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            metadata[f"transform_{self.name.lower()}"] = True
            updated.append(
                Chunk(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=metadata,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    source_ref=chunk.source_ref,
                )
            )
        return updated

    @property
    def __class__(self) -> type:  # type: ignore[override]
        return type(self.name, (), {})


class _FakeBatchProcessor:
    """测试桩：返回一条稳定 ChunkRecord。"""

    def process(self, chunks: list[Chunk], trace: Any | None = None) -> list[ChunkRecord]:
        _ = trace
        return [
            ChunkRecord(
                id=chunk.id,
                text=chunk.text,
                metadata=dict(chunk.metadata),
                dense_vector=[1.0, 2.0],
                sparse_vector={"azure": 1.0},
            )
            for chunk in chunks
        ]


class _FakeVectorUpserter:
    """测试桩：返回稳定存储 ID。"""

    def upsert(self, records: list[ChunkRecord], trace: Any | None = None) -> list[str]:
        _ = trace
        return [f"stored::{record.id}" for record in records]


class _FakeImageStorage:
    """测试桩：避免真实图片落盘。"""

    def save_image(
        self,
        image_id: str,
        image_bytes: bytes,
        collection: str,
        doc_hash: str,
        page_num: int | None,
        extension: str,
    ) -> str:
        _ = (image_bytes, collection, doc_hash, page_num, extension)
        return f"images/{image_id}.png"


class _FakeBM25Indexer:
    """测试桩：返回固定 BM25 统计。"""

    def build(self, records: list[ChunkRecord], rebuild: bool = False) -> dict[str, Any]:
        _ = rebuild
        return {"terms": len(records) * 3, "doc_count": len(records)}


def _make_settings(trace_file: str = "logs/traces.jsonl") -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=8, sparse_top_k=20),
        rerank=RerankSettings(provider="none", enabled=False, top_m=30),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file=trace_file),
        vision_llm=VisionLLMSettings(enabled=False, provider=""),
        ingestion=IngestionSettings(
            splitter="recursive",
            batch_size=16,
            chunk_refiner=ChunkRefinerSettings(use_llm=False),
            metadata_enricher=MetadataEnricherSettings(use_llm=False),
        ),
    )


@pytest.fixture()
def sample_pdf_file(tmp_path: Path) -> Path:
    """提供一个真实存在的文件路径，满足 pipeline 的 source_path 校验。"""
    pdf_path = tmp_path / "demo.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake test pdf\n")
    return pdf_path


def _build_pipeline(
    *,
    should_skip: bool = False,
    transform_count: int = 3,
    trace_file: str = "logs/traces.jsonl",
) -> IngestionPipeline:
    transforms = [_FakeTransform(f"Transform{index}") for index in range(1, transform_count + 1)]
    return IngestionPipeline(
        settings=_make_settings(trace_file=trace_file),
        integrity_checker=_FakeIntegrityChecker(should_skip=should_skip),
        loader=_FakeLoader(),
        chunker=_FakeChunker(),  # type: ignore[arg-type]
        transforms=transforms,  # type: ignore[arg-type]
        batch_processor=_FakeBatchProcessor(),  # type: ignore[arg-type]
        bm25_indexer=_FakeBM25Indexer(),  # type: ignore[arg-type]
        vector_upserter=_FakeVectorUpserter(),  # type: ignore[arg-type]
        image_storage=_FakeImageStorage(),  # type: ignore[arg-type]
    )


def test_pipeline_run_emits_progress_for_each_main_stage(sample_pdf_file: Path) -> None:
    """
    Given:
        一条使用 3 个 transform 测试桩的可稳定执行 Pipeline。
    When:
        传入 `on_progress` 回调执行 `pipeline.run()`。
    Then:
        回调应按 `load/split/transform/embed/upsert` 对应的完成顺序被调用，
        且 `current/total` 参数正确递增，其中 transform 会按每个子步骤单独推进。
    """
    pipeline = _build_pipeline(transform_count=3)
    progress_events: list[tuple[str, int, int]] = []

    result = pipeline.run(
        str(sample_pdf_file),
        collection="demo",
        force=True,
        logical_source_path="blogger_intro.pdf",
        on_progress=lambda stage_name, current, total: progress_events.append((stage_name, current, total)),
    )

    assert result.skipped is False
    assert progress_events == [
        ("load", 1, 7),
        ("split", 2, 7),
        ("transform", 3, 7),
        ("transform", 4, 7),
        ("transform", 5, 7),
        ("embed", 6, 7),
        ("upsert", 7, 7),
    ]


def test_pipeline_run_without_progress_callback_keeps_existing_behavior(sample_pdf_file: Path) -> None:
    """
    Given:
        一条可稳定执行的 Pipeline，且未传入 `on_progress`。
    When:
        调用 `pipeline.run()`。
    Then:
        行为应与原先一致：正常返回结果，不因缺少回调而报错或改变输出。
    """
    pipeline = _build_pipeline(transform_count=2)

    result = pipeline.run(str(sample_pdf_file), collection="demo", force=True)

    assert result.skipped is False
    assert result.chunk_count == 1
    assert result.vector_ids == ["stored::pdf_demo_0000_abcd1234"]


def test_pipeline_run_rejects_non_callable_progress_callback(sample_pdf_file: Path) -> None:
    """
    Given:
        非可调用对象作为 `on_progress` 输入。
    When:
        调用 `pipeline.run()`。
    Then:
        应立即抛出 `ValueError`，阻止错误回调对象进入执行流程。
    """
    pipeline = _build_pipeline()

    with pytest.raises(ValueError, match="on_progress must be callable"):
        pipeline.run(  # type: ignore[arg-type]
            str(sample_pdf_file),
            collection="demo",
            force=True,
            on_progress="not-callable",
        )


def test_pipeline_run_progress_callback_failure_does_not_break_ingestion(sample_pdf_file: Path) -> None:
    """
    Given:
        一个会在第二次调用时抛异常的 `on_progress` 回调。
    When:
        执行 `pipeline.run()`。
    Then:
        Pipeline 主链路不应被回调异常中断，仍应正常返回摄取结果。
    """
    pipeline = _build_pipeline(transform_count=1)
    call_count = {"value": 0}

    def _flaky_progress(stage_name: str, current: int, total: int) -> None:
        _ = (stage_name, current, total)
        call_count["value"] += 1
        if call_count["value"] == 2:
            raise RuntimeError("ui temporarily disconnected")

    result = pipeline.run(
        str(sample_pdf_file),
        collection="demo",
        force=True,
        logical_source_path="blogger_intro.pdf",
        on_progress=_flaky_progress,
    )

    assert result.skipped is False
    assert result.chunk_count == 1
    assert call_count["value"] >= 2


def test_pipeline_run_persists_ingestion_trace_jsonl(sample_pdf_file: Path, tmp_path: Path) -> None:
    """
    Given:
        一条使用 fake 组件的稳定 Pipeline，
        且 `observability.trace_file` 指向测试临时目录下的 `traces.jsonl`。
    When:
        执行一次 `pipeline.run()`。
    Then:
        - 应真实创建 `traces.jsonl`；
        - 文件内应追加一条 `trace_type == "ingestion"` 的 JSON Lines 记录；
        - 记录里应包含 G5 页面依赖的 `source_path/processing_source_path/collection` 上下文与主阶段数据。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"
    pipeline = _build_pipeline(trace_file=str(trace_file))

    result = pipeline.run(
        str(sample_pdf_file),
        collection="demo",
        force=True,
        logical_source_path="blogger_intro.pdf",
    )

    assert trace_file.exists() is True
    records = [
        json.loads(line)
        for line in trace_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    payload = records[0]

    assert payload["trace_id"] == result.trace_id
    assert payload["trace_type"] == "ingestion"
    assert float(payload["total_elapsed_ms"]) >= 0.0

    stage_names = [stage["stage_name"] for stage in payload["stages"]]
    assert "pipeline.request" in stage_names
    assert "load" in stage_names
    assert "split" in stage_names
    assert "transform" in stage_names
    assert "embed" in stage_names
    assert "upsert" in stage_names

    request_stage = next(stage for stage in payload["stages"] if stage["stage_name"] == "pipeline.request")
    assert request_stage["details"]["collection"] == "demo"
    assert request_stage["details"]["source_path"] == "blogger_intro.pdf"
    assert request_stage["details"]["processing_source_path"] == str(sample_pdf_file.resolve())
    assert request_stage["details"]["file_name"] == "blogger_intro.pdf"
