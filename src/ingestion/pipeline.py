"""IngestionPipeline：离线摄取主流程编排（C14）。

这个模块的核心目标是把 C1-C13 的独立能力串起来，形成一个可直接调用的主闭环：
`integrity -> load -> split -> transform -> encode -> store`。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, TypeVar

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import ChunkRecord, Document
from ingestion.chunking.document_chunker import DocumentChunker
from ingestion.embedding.batch_processor import BatchProcessor
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from ingestion.storage.vector_upserter import VectorUpserter
from ingestion.transform.base_transform import BaseTransform
from ingestion.transform.chunk_refiner import ChunkRefiner
from ingestion.transform.image_captioner import ImageCaptioner
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.loader.base_loader import BaseLoader
from libs.loader.file_integrity import FileIntegrityChecker, SQLiteIntegrityChecker
from libs.loader.pdf_loader import PdfLoader
from observability.logger import get_logger

T = TypeVar("T")
LOGGER = get_logger("ingestion.pipeline")


@dataclass(frozen=True)
class IngestionResult:
    """单次摄取执行结果。

    字段说明：
    - `skipped=True` 表示命中增量跳过（文件未变化）；
    - `vector_ids` 是本次 upsert 后返回的向量主键列表（与输入记录顺序一致）；
    - `image_count` 是本次图片存储层成功落盘并建索引的数量；
    - `bm25_terms` 是 BM25 索引构建后词项总数（用于观测索引规模）。

    Example:
        >>> IngestionResult(
        ...   source_path="Q:/docs/a.pdf",
        ...   collection="default",
        ...   file_hash="abc...",
        ...   skipped=False,
        ...   document_id="pdf_xxx",
        ...   chunk_count=12,
        ...   vector_ids=["chunk_x1", "chunk_x2"],
        ...   image_count=3,
        ...   bm25_terms=256,
        ... )
    """

    source_path: str
    collection: str
    file_hash: str
    skipped: bool
    document_id: str | None
    chunk_count: int
    vector_ids: list[str] = field(default_factory=list)
    image_count: int = 0
    bm25_terms: int = 0
    trace_id: str | None = None


class IngestionPipeline:
    """串行编排摄取主链路：integrity -> load -> split -> transform -> encode -> store。

    做什么：
    - 在处理前执行完整性检查（SHA256 + should_skip）；
    - 按固定阶段顺序执行 loader/chunker/transforms/encoding/storage；
    - 输出统一 `IngestionResult`，并在失败时写入 `mark_failed`。

    为什么：
    - 把前序任务拆开的组件拼成“一次调用即可完成”的生产入口，
      供 CLI(`ingest.py`)、Dashboard、批处理任务复用。

    关键权衡：
    - Transform 用“列表顺序执行”，优先保证可插拔和可定位问题；
    - Storage 先落图片再落向量/BM25，保证 metadata 内图片路径最终一致。

    失败路径：
    - 任一阶段异常都包装成带阶段名的 `RuntimeError`；
    - 若 `file_hash` 已可得，失败时写入 `mark_failed`，便于后续排障与重试。

    Args:
        settings: 全局配置。
        integrity_checker: 文件完整性组件（默认 SQLite 实现）。
        loader: 文档加载器（默认 PdfLoader）。
        chunker: 文本切分适配器（默认 DocumentChunker）。
        transforms: 变换链（默认 ChunkRefiner -> MetadataEnricher -> ImageCaptioner）。
        batch_processor: Dense/Sparse 编排器（默认 BatchProcessor）。
        bm25_indexer: BM25 索引器。
        vector_upserter: 向量存储写入器。
        image_storage: 图片存储与索引组件。
    """

    _SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

    def __init__(
        self,
        settings: Settings,
        *,
        integrity_checker: FileIntegrityChecker | None = None,
        loader: BaseLoader | None = None,
        chunker: DocumentChunker | None = None,
        transforms: list[BaseTransform] | None = None,
        batch_processor: BatchProcessor | None = None,
        bm25_indexer: BM25Indexer | None = None,
        vector_upserter: VectorUpserter | None = None,
        image_storage: ImageStorage | None = None,
    ) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("IngestionPipeline requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.integrity_checker = integrity_checker or SQLiteIntegrityChecker()
        self.loader = loader or PdfLoader()
        self.chunker = chunker or DocumentChunker(settings=settings)
        self.transforms = transforms or [
            ChunkRefiner(settings=settings),
            MetadataEnricher(settings=settings),
            ImageCaptioner(settings=settings),
        ]
        self.batch_processor = batch_processor or BatchProcessor(settings=settings)
        self.bm25_indexer = bm25_indexer or BM25Indexer()
        self.vector_upserter = vector_upserter or VectorUpserter(settings=settings)
        self.image_storage = image_storage or ImageStorage()

    def run(
        self,
        source_path: str,
        collection: str = "default",
        *,
        force: bool = False,
        trace: TraceContext | None = None,
    ) -> IngestionResult:
        """执行一次完整摄取。

        Example:
            >>> settings = load_settings("config/settings.yaml")
            >>> pipeline = IngestionPipeline(settings)
            >>> result = pipeline.run("tests/fixtures/sample_documents/simple.pdf", collection="demo")
            >>> result.skipped
            False

        Args:
            source_path: 待摄取文件路径。
            collection: 目标集合名（用于向量库和图片索引分组）。
            force: 是否忽略完整性跳过直接重处理。
            trace: 可选追踪上下文；未提供时自动创建 `trace_type=ingestion`。

        Returns:
            IngestionResult: 本次执行结果摘要。

        Raises:
            RuntimeError: 任一阶段失败时抛出，错误信息包含阶段名与原始异常类型。
        """
        normalized_source = self._validate_source_path(source_path)
        normalized_collection = self._normalize_collection(collection)
        active_trace = trace or TraceContext(trace_type="ingestion")

        LOGGER.info(
            "[Pipeline] run.start source=%s collection=%s force=%s trace_id=%s",
            normalized_source,
            normalized_collection,
            bool(force),
            active_trace.trace_id,
        )

        file_path = Path(normalized_source)
        file_size = file_path.stat().st_size
        file_hash = ""

        try:
            file_hash = self._run_stage(
                stage_name="integrity.compute_sha256",
                trace=active_trace,
                action=lambda: self.integrity_checker.compute_sha256(normalized_source),
            )

            should_skip = self._run_stage(
                stage_name="integrity.should_skip",
                trace=active_trace,
                action=lambda: self.integrity_checker.should_skip(file_hash),
            )
            if should_skip and not force:
                active_trace.record_stage(
                    stage_name="pipeline.skip",
                    details={"reason": "integrity_hit", "file_hash": file_hash, "source_path": normalized_source},
                    elapsed_ms=0.0,
                )
                LOGGER.info(
                    "[Pipeline] run.skip source=%s file_hash=%s reason=integrity_hit",
                    normalized_source,
                    file_hash,
                )
                return IngestionResult(
                    source_path=normalized_source,
                    collection=normalized_collection,
                    file_hash=file_hash,
                    skipped=True,
                    document_id=None,
                    chunk_count=0,
                    vector_ids=[],
                    image_count=0,
                    bm25_terms=0,
                    trace_id=active_trace.trace_id,
                )

            document = self._run_stage(
                stage_name="load",
                trace=active_trace,
                action=lambda: self.loader.load(normalized_source),
            )

            chunks = self._run_stage(
                stage_name="split",
                trace=active_trace,
                action=lambda: self.chunker.split_document(document),
            )

            transformed_chunks = chunks
            for transform in self.transforms:
                transform_name = transform.__class__.__name__
                transformed_chunks = self._run_stage(
                    stage_name=f"transform.{transform_name}",
                    trace=active_trace,
                    action=lambda t=transform, c=transformed_chunks: t.transform(c, trace=active_trace),
                )

            records = self._run_stage(
                stage_name="encode",
                trace=active_trace,
                action=lambda: self.batch_processor.process(transformed_chunks, trace=active_trace),
            )

            image_count, image_path_map = self._run_stage(
                stage_name="store.images",
                trace=active_trace,
                action=lambda: self._store_images(document=document, collection=normalized_collection),
            )

            self._patch_record_image_paths(records=records, image_path_map=image_path_map)

            vector_ids = self._run_stage(
                stage_name="store.vector_upsert",
                trace=active_trace,
                action=lambda: self.vector_upserter.upsert(records, trace=active_trace),
            )

            bm25_stats = self._run_stage(
                stage_name="store.bm25",
                trace=active_trace,
                action=lambda: self.bm25_indexer.build(records, rebuild=False),
            )

            self._run_stage(
                stage_name="integrity.mark_success",
                trace=active_trace,
                action=lambda: self.integrity_checker.mark_success(
                    file_hash=file_hash,
                    file_path=normalized_source,
                    file_size=file_size,
                    chunk_count=len(records),
                ),
            )

            result = IngestionResult(
                source_path=normalized_source,
                collection=normalized_collection,
                file_hash=file_hash,
                skipped=False,
                document_id=document.id,
                chunk_count=len(records),
                vector_ids=vector_ids,
                image_count=image_count,
                bm25_terms=int(bm25_stats.get("terms", 0)) if isinstance(bm25_stats, dict) else 0,
                trace_id=active_trace.trace_id,
            )
            LOGGER.info(
                "[Pipeline] run.done source=%s chunks=%s vectors=%s images=%s bm25_terms=%s",
                result.source_path,
                result.chunk_count,
                len(result.vector_ids),
                result.image_count,
                result.bm25_terms,
            )
            return result

        except Exception as exc:
            if file_hash:
                try:
                    self.integrity_checker.mark_failed(
                        file_hash=file_hash,
                        error_msg=f"{type(exc).__name__}: {exc}",
                        file_path=normalized_source,
                        file_size=file_size,
                    )
                except Exception:
                    # 标记失败属于辅助行为：这里不能覆盖主异常，避免丢失真正错误源头。
                    pass

            LOGGER.exception(
                "[Pipeline] run.failed source=%s collection=%s error=%s:%s",
                normalized_source,
                normalized_collection,
                type(exc).__name__,
                exc,
            )
            raise

    def _run_stage(
        self,
        *,
        stage_name: str,
        trace: TraceContext | None,
        action: Callable[[], T],
    ) -> T:
        """执行单个阶段并统一处理日志、trace、异常包装。

        这个方法是 pipeline 的“统一门面”：
        - 进入阶段时记录 `stage.start` 日志；
        - 成功时记录 `stage.done` 日志并写 trace；
        - 失败时记录 `stage.error` 日志并抛出带阶段名的 RuntimeError。
        """
        LOGGER.info("[Pipeline] stage.start stage=%s", stage_name)
        started = perf_counter()

        try:
            result = action()
            elapsed_ms = (perf_counter() - started) * 1000.0
            summary = self._summarize_result_for_log(result)

            if trace is not None:
                trace.record_stage(
                    stage_name=f"pipeline.{stage_name}",
                    details={"status": "ok", **summary},
                    elapsed_ms=elapsed_ms,
                )

            LOGGER.info(
                "[Pipeline] stage.done stage=%s elapsed_ms=%.2f summary=%s",
                stage_name,
                elapsed_ms,
                summary,
            )
            return result
        except Exception as exc:
            elapsed_ms = (perf_counter() - started) * 1000.0
            if trace is not None:
                trace.record_stage(
                    stage_name=f"pipeline.{stage_name}",
                    details={"status": "error", "error_type": type(exc).__name__, "error": str(exc)},
                    elapsed_ms=elapsed_ms,
                    status="error",
                )

            LOGGER.exception(
                "[Pipeline] stage.error stage=%s elapsed_ms=%.2f error=%s:%s",
                stage_name,
                elapsed_ms,
                type(exc).__name__,
                exc,
            )
            raise RuntimeError(
                f"IngestionPipeline stage '{stage_name}' failed: {type(exc).__name__}: {exc}"
            ) from exc

    def _store_images(self, *, document: Document, collection: str) -> tuple[int, dict[str, str]]:
        """把 Loader 提取的图片文件纳入 C13 存储，并返回 `image_id -> stored_path` 映射。

        输入示例（来自 `document.metadata.images`）：
        - `{"id": "abc_1_0001", "path": ".../loader_images/abc_1_0001.png", "page": 1}`

        输出示例：
        - `(3, {"abc_1_0001": ".../data/images/test/abc_1_0001.png", ...})`

        这个映射会在后续 `_patch_record_image_paths` 中用于把 chunk metadata 里的旧路径
        替换成图片存储层最终路径。
        """
        raw_images = document.metadata.get("images")
        if not isinstance(raw_images, list) or not raw_images:
            return 0, {}

        image_path_map: dict[str, str] = {}
        for idx, image in enumerate(raw_images):
            if not isinstance(image, dict):
                raise ValueError(f"document.metadata.images[{idx}] must be dict")

            image_id = str(image.get("id", "")).strip()
            source_path = str(image.get("path", "")).strip()
            if not image_id or not source_path:
                raise ValueError(f"document.metadata.images[{idx}] missing id/path")

            source_file = Path(source_path)
            if not source_file.exists() or not source_file.is_file():
                raise FileNotFoundError(f"Image file not found for image_id={image_id}: {source_path}")

            page_num_raw = image.get("page")
            page_num = int(page_num_raw) if isinstance(page_num_raw, int) else None
            extension = source_file.suffix.lstrip(".") or "png"

            # image_id 约定形如 "{doc_hash}_{page}_{seq}"，这里取首段作为 doc_hash。
            doc_hash = image_id.split("_", 1)[0]

            stored_path = self.image_storage.save_image(
                image_id=image_id,
                image_bytes=source_file.read_bytes(),
                collection=collection,
                doc_hash=doc_hash,
                page_num=page_num,
                extension=extension,
            )
            image_path_map[image_id] = stored_path

        return len(image_path_map), image_path_map

    @staticmethod
    def _patch_record_image_paths(records: list[ChunkRecord], image_path_map: dict[str, str]) -> None:
        """把 ChunkRecord.metadata.images 中的旧路径替换为 ImageStorage 的最终路径。

        例子：
        - 输入 metadata.images: `[{"id":"a_1_0001","path":"loader_images/a_1_0001.png"}]`
        - 输出 metadata.images: `[{"id":"a_1_0001","path":"data/images/test/a_1_0001.png"}]`

        这样做的价值：
        - 检索命中 chunk 后，返回给上层的是“可直接访问的最终路径”，
          而不是 loader 中间目录路径。
        """
        if not image_path_map:
            return

        for record in records:
            metadata = dict(record.metadata)
            images = metadata.get("images")
            if not isinstance(images, list):
                continue

            patched_images: list[dict[str, object]] = []
            for image in images:
                if not isinstance(image, dict):
                    continue

                copied = dict(image)
                image_id = copied.get("id")
                if isinstance(image_id, str) and image_id in image_path_map:
                    copied["path"] = image_path_map[image_id]
                patched_images.append(copied)

            metadata["images"] = patched_images
            record.metadata = metadata

    @staticmethod
    def _validate_source_path(source_path: str) -> str:
        """校验并标准化源文件路径。"""
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError("source_path must be non-empty string")

        resolved = Path(source_path).resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"source_path not found or not file: {resolved}")
        return str(resolved)

    @classmethod
    def _normalize_collection(cls, collection: str) -> str:
        """校验 collection，避免非法路径片段。"""
        if not isinstance(collection, str) or not collection.strip():
            raise ValueError("collection must be non-empty string")
        normalized = collection.strip()
        if not cls._SAFE_SEGMENT_PATTERN.match(normalized):
            raise ValueError(f"collection contains unsafe characters: {collection!r}")
        return normalized

    @staticmethod
    def _summarize_result_for_log(result: Any) -> dict[str, object]:
        """把阶段返回值压缩为日志可读摘要，避免日志打印大对象。"""
        if result is None:
            return {"result": "none"}

        if isinstance(result, bool):
            return {"result": bool(result)}

        if isinstance(result, (str, int, float)):
            return {"result": result}

        if isinstance(result, list):
            return {"result_type": "list", "count": len(result)}

        if isinstance(result, tuple):
            return {"result_type": "tuple", "count": len(result)}

        if isinstance(result, dict):
            summary: dict[str, object] = {"result_type": "dict", "keys": sorted(result.keys())[:8]}
            if "terms" in result:
                summary["terms"] = result.get("terms")
            if "doc_count" in result:
                summary["doc_count"] = result.get("doc_count")
            return summary

        return {"result_type": type(result).__name__}
