"""IngestionPipeline 集成测试（C14）。"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import uuid
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("markitdown")
pytest.importorskip("fitz")
pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings
from core.trace.trace_context import TraceContext
from core.types import Chunk, ChunkRecord, Document
from ingestion.chunking.document_chunker import DocumentChunker
from ingestion.pipeline import IngestionPipeline
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from ingestion.storage.vector_upserter import VectorUpserter
from ingestion.transform.chunk_refiner import ChunkRefiner
from ingestion.transform.image_captioner import ImageCaptioner
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.loader.base_loader import BaseLoader
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.loader.pdf_loader import PdfLoader
from libs.vector_store.chroma_store import ChromaStore

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents"
COMPLEX_PDF = FIXTURE_DIR / "complex_technical_doc.pdf"
SIMPLE_PDF = FIXTURE_DIR / "simple.pdf"


class _FakeBatchProcessor:
    """测试用编码器：避免真实 Embedding 依赖，输出稳定 dense+sparse 向量。"""

    _TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)

    def process(self, chunks: list[Chunk], trace: Any | None = None) -> list[ChunkRecord]:
        _ = trace
        records: list[ChunkRecord] = []
        for idx, chunk in enumerate(chunks):
            tokens = [token for token in self._TOKEN_PATTERN.findall(chunk.text.lower()) if token.strip("_")]
            counts = Counter(tokens)
            sparse_vector = {term: float(freq) for term, freq in sorted(counts.items())}
            if not sparse_vector:
                sparse_vector = {"__empty__": 1.0}

            records.append(
                ChunkRecord(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    dense_vector=[float(len(chunk.text) or 1), float(idx + 1)],
                    sparse_vector=sparse_vector,
                )
            )
        return records


class _FailingLoader(BaseLoader):
    """测试桩：用于验证 pipeline 的阶段异常包装是否清晰。"""

    def load(self, path: str) -> Document:
        raise RuntimeError(f"simulated_load_failure:{path}")


@pytest.fixture()
def integration_workspace() -> Path:
    """创建隔离工作目录，避免污染真实 data/db。"""
    root = PROJECT_ROOT / ".pytest_tmp" / f"ingestion_pipeline_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _build_settings(workspace: Path) -> Settings:
    """构造测试专用 Settings：关闭 LLM，重定向持久化目录。"""
    base = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    ingestion_cfg = replace(
        base.ingestion,
        batch_size=16,
        chunk_refiner=replace(base.ingestion.chunk_refiner, use_llm=False),
        metadata_enricher=replace(base.ingestion.metadata_enricher, use_llm=False),
    )

    return replace(
        base,
        vector_store=replace(base.vector_store, persist_dir=str(workspace / "data" / "db" / "chroma")),
        vision_llm=replace(base.vision_llm, enabled=False),
        ingestion=ingestion_cfg,
    )


def _build_real_settings(workspace: Path) -> Settings:
    """构造“全真配置”测试专用 Settings。

    目标：
    - 不关闭真实功能开关（chunk_refiner/metadata_enricher/vision 保持原样）；
    - 仅重定向持久化目录到隔离目录；
    - 适度提高超时，避免因为网络抖动导致“全链路误判失败”。
    """
    base = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    llm_cfg = replace(
        base.llm,
        timeout=max(float(base.llm.timeout), 60.0),
        max_retries=max(int(base.llm.max_retries), 1),
        retry_backoff_seconds=max(float(base.llm.retry_backoff_seconds), 0.25),
        retry_backoff_multiplier=max(float(base.llm.retry_backoff_multiplier), 1.0),
        retry_max_backoff_seconds=max(float(base.llm.retry_max_backoff_seconds), 1.0),
    )
    vision_cfg = replace(
        base.vision_llm,
        timeout=max(float(base.vision_llm.timeout), 60.0),
        max_retries=max(int(base.vision_llm.max_retries), 1),
        retry_backoff_seconds=max(float(base.vision_llm.retry_backoff_seconds), 0.25),
        retry_backoff_multiplier=max(float(base.vision_llm.retry_backoff_multiplier), 1.0),
        retry_max_backoff_seconds=max(float(base.vision_llm.retry_max_backoff_seconds), 1.0),
    )
    ingestion_cfg = replace(
        base.ingestion,
        # 适度放大 chunk，减少 API 请求次数，但避免超大 prompt。
        chunk_size=max(int(base.ingestion.chunk_size), 3000),
        chunk_overlap=min(int(base.ingestion.chunk_overlap), 200),
    )

    return replace(
        base,
        llm=llm_cfg,
        vision_llm=vision_cfg,
        ingestion=ingestion_cfg,
        vector_store=replace(base.vector_store, persist_dir=str(workspace / "data" / "db" / "chroma")),
    )


def _build_pipeline(
    workspace: Path,
    *,
    collection_name: str,
) -> tuple[IngestionPipeline, ImageStorage, ChromaStore, SQLiteIntegrityChecker]:
    """组装一套可测试的 Pipeline 实例（默认走 FakeBatchProcessor）。"""
    settings = _build_settings(workspace)
    integrity_checker = SQLiteIntegrityChecker(db_path=str(workspace / "data" / "db" / "ingestion_history.db"))
    loader = PdfLoader(image_root=str(workspace / "loader_images"))
    chunker = DocumentChunker(settings=settings)
    image_storage = ImageStorage(
        image_root=str(workspace / "data" / "images"),
        db_path=str(workspace / "data" / "db" / "image_index.db"),
    )
    bm25_indexer = BM25Indexer(persist_dir=str(workspace / "data" / "db" / "bm25"))
    vector_store = ChromaStore(
        persist_dir=str(workspace / "data" / "db" / "chroma"),
        collection_name=collection_name,
    )
    vector_upserter = VectorUpserter(settings=settings, vector_store=vector_store)
    transforms = [
        ChunkRefiner(settings=settings),
        MetadataEnricher(settings=settings),
        ImageCaptioner(settings=settings),
    ]

    pipeline = IngestionPipeline(
        settings=settings,
        integrity_checker=integrity_checker,
        loader=loader,
        chunker=chunker,
        transforms=transforms,
        batch_processor=_FakeBatchProcessor(),
        bm25_indexer=bm25_indexer,
        vector_upserter=vector_upserter,
        image_storage=image_storage,
    )
    return pipeline, image_storage, vector_store, integrity_checker


def _build_real_pipeline(
    workspace: Path,
    *,
    collection_name: str,
) -> tuple[IngestionPipeline, ImageStorage, ChromaStore, SQLiteIntegrityChecker, Settings]:
    """组装“全真 settings”Pipeline：显式注入真实 transforms，避免默认值语义歧义。"""
    settings = _build_real_settings(workspace)
    integrity_checker = SQLiteIntegrityChecker(db_path=str(workspace / "data" / "db" / "ingestion_history.db"))
    loader = PdfLoader(image_root=str(workspace / "loader_images"))
    chunker = DocumentChunker(settings=settings)
    image_storage = ImageStorage(
        image_root=str(workspace / "data" / "images"),
        db_path=str(workspace / "data" / "db" / "image_index.db"),
    )
    bm25_indexer = BM25Indexer(persist_dir=str(workspace / "data" / "db" / "bm25"))
    vector_store = ChromaStore(
        persist_dir=str(workspace / "data" / "db" / "chroma"),
        collection_name=collection_name,
    )
    vector_upserter = VectorUpserter(settings=settings, vector_store=vector_store)
    transforms = [
        ChunkRefiner(settings=settings),
        MetadataEnricher(settings=settings),
        ImageCaptioner(settings=settings),
    ]

    pipeline = IngestionPipeline(
        settings=settings,
        integrity_checker=integrity_checker,
        loader=loader,
        chunker=chunker,
        transforms=transforms,
        bm25_indexer=bm25_indexer,
        vector_upserter=vector_upserter,
        image_storage=image_storage,
    )
    return pipeline, image_storage, vector_store, integrity_checker, settings


def _has_real_key(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False

    placeholders = ["your_", "<", ">", "***", "dummy", "example"]
    lowered = text.lower()
    return not any(token in lowered for token in placeholders)


def _required_llm_env_keys(provider: str) -> list[str]:
    mapping = {
        "openai": ["LLM_API_KEY", "OPENAI_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "azure": ["AZURE_API_KEY", "AZURE_OPENAI_API_KEY"],
        "dashscope": ["LLM_API_KEY", "DASHSCOPE_API_KEY"],
    }
    return mapping.get(provider, ["LLM_API_KEY"])


def _required_vision_env_keys(provider: str) -> list[str]:
    mapping = {
        "dashscope": ["VISION_LLM_API_KEY", "DASHSCOPE_API_KEY"],
        "azure": ["VISION_LLM_API_KEY", "AZURE_API_KEY", "AZURE_OPENAI_API_KEY"],
        "openai": ["VISION_LLM_API_KEY", "OPENAI_API_KEY"],
    }
    return mapping.get(provider, ["VISION_LLM_API_KEY"])


def _ensure_text_llm_runtime_ready(settings: Settings) -> None:
    provider = settings.llm.provider.strip().lower()
    if not provider:
        pytest.skip("settings.llm.provider 为空，跳过真实 Pipeline 集成测试")

    if not _has_real_key(settings.llm.api_key):
        env_keys = _required_llm_env_keys(provider)
        if not any(_has_real_key(os.getenv(key)) for key in env_keys):
            pytest.skip(
                "llm.api_key 为空或占位符，且缺少可用环境变量 "
                f"{', '.join(env_keys)}，跳过真实 Pipeline 集成测试"
            )


def _ensure_vision_runtime_ready(settings: Settings) -> None:
    if not settings.vision_llm.enabled:
        return

    provider = settings.vision_llm.provider.strip().lower()
    if not provider:
        pytest.skip("vision_llm.enabled=true 但 provider 为空，跳过真实 Pipeline 集成测试")

    if not _has_real_key(settings.vision_llm.api_key):
        env_keys = _required_vision_env_keys(provider)
        if not any(_has_real_key(os.getenv(key)) for key in env_keys):
            pytest.skip(
                "vision_llm.api_key 为空或占位符，且缺少可用环境变量 "
                f"{', '.join(env_keys)}，跳过真实 Pipeline 集成测试"
            )


def _get_stage(trace: TraceContext, stage_name: str) -> dict[str, Any] | None:
    for stage in trace.stages:
        if stage.get("stage_name") == stage_name:
            return stage
    return None


def _assert_pipeline_stage_trace_complete(trace: TraceContext) -> None:
    """校验 pipeline.* 阶段都出现且状态为 ok。"""
    stage_names = [stage.get("stage_name") for stage in trace.stages]
    expected_pipeline_stages = [
        "pipeline.integrity.compute_sha256",
        "pipeline.integrity.should_skip",
        "pipeline.load",
        "pipeline.split",
        "pipeline.transform.ChunkRefiner",
        "pipeline.transform.MetadataEnricher",
        "pipeline.transform.ImageCaptioner",
        "pipeline.encode",
        "pipeline.store.images",
        "pipeline.store.vector_upsert",
        "pipeline.store.bm25",
        "pipeline.integrity.mark_success",
    ]
    for stage_name in expected_pipeline_stages:
        assert stage_name in stage_names, f"missing stage: {stage_name}"

    for stage in trace.stages:
        if str(stage.get("stage_name", "")).startswith("pipeline."):
            assert stage.get("status") == "ok", f"pipeline stage failed: {stage}"


def _collect_real_fail_reasons(trace: TraceContext, settings: Settings) -> list[str]:
    """根据 transform 统计判断“全真链路是否达到严格标准”，返回失败原因列表。"""
    reasons: list[str] = []

    if settings.ingestion.chunk_refiner.use_llm:
        stage = _get_stage(trace, "transform.chunk_refiner")
        if stage is None:
            reasons.append("missing transform.chunk_refiner stage")
        else:
            details = stage.get("details", {})
            llm_success = int(details.get("llm_success", 0))
            if llm_success <= 0:
                reasons.append(f"chunk_refiner llm_success<=0 details={details}")

    if settings.ingestion.metadata_enricher.use_llm:
        stage = _get_stage(trace, "transform.metadata_enricher")
        if stage is None:
            reasons.append("missing transform.metadata_enricher stage")
        else:
            details = stage.get("details", {})
            llm_success = int(details.get("llm_success", 0))
            if llm_success <= 0:
                reasons.append(f"metadata_enricher llm_success<=0 details={details}")

    if settings.vision_llm.enabled:
        stage = _get_stage(trace, "transform.image_captioner")
        if stage is None:
            reasons.append("missing transform.image_captioner stage")
        else:
            details = stage.get("details", {})
            chunks_with_images = int(details.get("chunks_with_images", 0))
            captioned_images = int(details.get("captioned_images", 0))
            if chunks_with_images > 0 and captioned_images <= 0:
                reasons.append(f"image_captioner captioned_images<=0 details={details}")

    return reasons


def _format_attempt_diagnostics(attempt_index: int, trace: TraceContext) -> str:
    tracked = [
        "transform.chunk_refiner",
        "transform.metadata_enricher",
        "transform.image_captioner",
    ]
    lines = [f"attempt={attempt_index}"]
    for name in tracked:
        stage = _get_stage(trace, name)
        if stage is None:
            lines.append(f"  - {name}: <missing>")
        else:
            lines.append(f"  - {name}: {stage.get('details')}")
    return "\n".join(lines)


def test_ingestion_pipeline_runs_end_to_end_on_complex_pdf(integration_workspace: Path) -> None:
    """
    Given:
        `complex_technical_doc.pdf` 与一套隔离目录下的 Pipeline 组件。
    When:
        执行 `pipeline.run(..., collection="test")` 完整摄取链路。
    Then:
        - 返回非跳过结果且 chunk/vector 数量一致；
        - Chroma 持久化目录存在文件；
        - BM25 索引文件存在；
        - ImageStorage 中有可查询图片记录且文件真实存在。
    """
    collection_name = f"it_c14_{uuid.uuid4().hex[:8]}"
    pipeline, image_storage, vector_store, integrity_checker = _build_pipeline(
        integration_workspace,
        collection_name=collection_name,
    )

    try:
        result = pipeline.run(str(COMPLEX_PDF), collection="test")

        assert result.skipped is False
        assert result.chunk_count > 0
        assert len(result.vector_ids) == result.chunk_count

        chroma_dir = integration_workspace / "data" / "db" / "chroma"
        assert chroma_dir.exists()
        assert any(path.is_file() for path in chroma_dir.rglob("*"))

        bm25_file = integration_workspace / "data" / "db" / "bm25" / "bm25_index.pkl"
        assert bm25_file.exists()

        stored_images = image_storage.list_images(collection="test")
        assert stored_images
        assert all(Path(item["file_path"]).exists() for item in stored_images)

        assert integrity_checker.should_skip(result.file_hash) is True
    finally:
        vector_store._client.delete_collection(collection_name)


def test_ingestion_pipeline_skips_unchanged_file_and_force_can_override(integration_workspace: Path) -> None:
    """
    Given:
        同一 `simple.pdf` 文件与同一套完整性数据库。
    When:
        连续运行两次（默认 force=False），再运行一次 force=True。
    Then:
        - 第二次应命中增量跳过（skipped=True）；
        - force=True 时应重新执行处理（skipped=False）。
    """
    collection_name = f"it_c14_skip_{uuid.uuid4().hex[:8]}"
    pipeline, _image_storage, vector_store, _checker = _build_pipeline(
        integration_workspace,
        collection_name=collection_name,
    )

    try:
        first = pipeline.run(str(SIMPLE_PDF), collection="test")
        second = pipeline.run(str(SIMPLE_PDF), collection="test")
        forced = pipeline.run(str(SIMPLE_PDF), collection="test", force=True)

        assert first.skipped is False
        assert second.skipped is True
        assert second.chunk_count == 0
        assert second.vector_ids == []
        assert forced.skipped is False
    finally:
        vector_store._client.delete_collection(collection_name)


def test_ingestion_pipeline_wraps_stage_error_with_readable_message(integration_workspace: Path) -> None:
    """
    Given:
        一个故意失败的 Loader（load 阶段抛异常）与独立完整性数据库。
    When:
        执行 `pipeline.run()`。
    Then:
        应抛出包含阶段名 `load` 的 RuntimeError，且完整性表会记录 failed 状态。
    """
    settings = _build_settings(integration_workspace)
    checker = SQLiteIntegrityChecker(db_path=str(integration_workspace / "data" / "db" / "ingestion_history.db"))
    collection_name = f"it_c14_fail_{uuid.uuid4().hex[:8]}"
    vector_store = ChromaStore(
        persist_dir=str(integration_workspace / "data" / "db" / "chroma"),
        collection_name=collection_name,
    )

    pipeline = IngestionPipeline(
        settings=settings,
        integrity_checker=checker,
        loader=_FailingLoader(),
        chunker=DocumentChunker(settings=settings),
        batch_processor=_FakeBatchProcessor(),
        bm25_indexer=BM25Indexer(persist_dir=str(integration_workspace / "data" / "db" / "bm25")),
        vector_upserter=VectorUpserter(settings=settings, vector_store=vector_store),
        image_storage=ImageStorage(
            image_root=str(integration_workspace / "data" / "images"),
            db_path=str(integration_workspace / "data" / "db" / "image_index.db"),
        ),
    )

    try:
        with pytest.raises(RuntimeError, match="stage 'load' failed"):
            pipeline.run(str(SIMPLE_PDF), collection="test", force=True)

        file_hash = checker.compute_sha256(str(SIMPLE_PDF.resolve()))
        rows = [row for row in checker.list_processed() if row.get("file_hash") == file_hash]
        assert rows
        assert rows[0]["status"] == "failed"
    finally:
        vector_store._client.delete_collection(collection_name)


def test_ingestion_pipeline_emits_readable_stage_progress_logs(integration_workspace: Path) -> None:
    """
    Given:
        一条可正常执行的 Pipeline（使用 FakeBatchProcessor 保证稳定）。
    When:
        执行 `pipeline.run(simple.pdf)`。
    Then:
        日志中应清晰出现 run.start/run.done 以及阶段级 stage.start/stage.done 文本，
        便于人工快速定位当前执行进度。
    """
    collection_name = f"it_c14_log_{uuid.uuid4().hex[:8]}"
    pipeline, _image_storage, vector_store, _checker = _build_pipeline(
        integration_workspace,
        collection_name=collection_name,
    )

    logger = logging.getLogger("ingestion.pipeline")
    captured_messages: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured_messages.append(record.getMessage())

    handler = _ListHandler(level=logging.INFO)
    logger.addHandler(handler)

    try:
        pipeline.run(str(SIMPLE_PDF), collection="test", force=True)
    finally:
        logger.removeHandler(handler)
        vector_store._client.delete_collection(collection_name)

    assert any("[Pipeline] run.start" in msg for msg in captured_messages)
    assert any("stage.start stage=load" in msg for msg in captured_messages)
    assert any("stage.done stage=split" in msg for msg in captured_messages)
    assert any("stage.done stage=store.vector_upsert" in msg for msg in captured_messages)
    assert any("stage.done stage=store.bm25" in msg for msg in captured_messages)
    assert any("[Pipeline] run.done" in msg for msg in captured_messages)


@pytest.mark.llm
def test_ingestion_pipeline_full_real_settings_run_reports_stage_results(integration_workspace: Path) -> None:
    """
    Given:
        `RUN_REAL_LLM_TESTS=1` 且 `config/settings.yaml` 中真实配置可用。
    When:
        使用“全真 settings”（不关闭 chunk_refiner/metadata_enricher/vision_llm）执行完整 pipeline；
        若首轮遇到瞬时超时，允许最多 N 次重试（默认 3 次）。
    Then:
        - `pipeline.*` 各阶段都被执行并写入 trace；
        - 返回结果非 skipped 且有 chunk/vector；
        - 严格标准：启用 LLM/Vision 的 transform 阶段必须至少成功一次，
          否则在重试耗尽后 fail，并输出完整诊断信息。
    """
    if os.getenv("RUN_REAL_LLM_TESTS", "") != "1":
        pytest.skip("Set RUN_REAL_LLM_TESTS=1 to run full real ingestion pipeline test")

    collection_name = f"it_c14_real_{uuid.uuid4().hex[:8]}"
    pipeline, image_storage, vector_store, _checker, settings = _build_real_pipeline(
        integration_workspace,
        collection_name=collection_name,
    )

    _ensure_text_llm_runtime_ready(settings)
    _ensure_vision_runtime_ready(settings)

    # 默认用 simple.pdf 提高稳定性；需要完整图文场景时可设 REAL_PIPELINE_SAMPLE=complex。
    sample_mode = os.getenv("REAL_PIPELINE_SAMPLE", "complex").strip().lower()
    source_pdf = COMPLEX_PDF if sample_mode == "complex" else SIMPLE_PDF

    raw_attempts = os.getenv("REAL_PIPELINE_MAX_ATTEMPTS", "3")
    try:
        max_attempts = max(1, int(raw_attempts))
    except Exception:
        max_attempts = 3

    diagnostics: list[str] = []
    last_trace: TraceContext | None = None
    last_result = None

    try:
        for attempt in range(1, max_attempts + 1):
            trace = TraceContext(trace_type="ingestion")
            result = pipeline.run(
                str(source_pdf),
                collection="real",
                force=True,
                trace=trace,
            )

            assert result.skipped is False
            assert result.chunk_count > 0
            assert len(result.vector_ids) == result.chunk_count

            _assert_pipeline_stage_trace_complete(trace)

            fail_reasons = _collect_real_fail_reasons(trace=trace, settings=settings)
            diagnostics.append(_format_attempt_diagnostics(attempt, trace))

            last_trace = trace
            last_result = result

            if not fail_reasons:
                break

            if attempt == max_attempts:
                pytest.fail(
                    "全真 pipeline 在所有重试后仍未满足严格标准。\n"
                    f"source={source_pdf}\n"
                    f"max_attempts={max_attempts}\n"
                    f"last_fail_reasons={fail_reasons}\n"
                    "---- attempt diagnostics ----\n"
                    + "\n\n".join(diagnostics)
                )

        assert last_result is not None
        assert last_trace is not None

        stored_images = image_storage.list_images(collection="real")
        if sample_mode == "complex":
            assert stored_images
    finally:
        vector_store._client.delete_collection(collection_name)

