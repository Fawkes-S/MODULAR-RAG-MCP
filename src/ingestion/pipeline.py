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
        on_progress: Callable[[str, int, int], None] | None = None,
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
            on_progress: 可选进度回调，签名为 `(stage_name, current, total)`。
                - `stage_name` 使用 F5 统一阶段名：`load/split/transform/embed/upsert`
                - `current` 表示当前已完成的进度步数
                - `total` 表示本次运行总步数（随 transform 数量动态变化）

        Returns:
            IngestionResult: 本次执行结果摘要。

        Raises:
            RuntimeError: 任一阶段失败时抛出，错误信息包含阶段名与原始异常类型。
        """
        normalized_source = self._validate_source_path(source_path)
        normalized_collection = self._normalize_collection(collection)
        active_trace = trace or TraceContext(trace_type="ingestion")
        progress_callback = self._normalize_on_progress(on_progress)
        progress_state = self._make_progress_state()

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
            self._attach_runtime_metadata(
                document=document,
                collection=normalized_collection,
                file_hash=file_hash,
            )
            self._emit_progress(
                on_progress=progress_callback,
                progress_state=progress_state,
                stage_name="load",
            )

            chunks = self._run_stage(
                stage_name="split",
                trace=active_trace,
                action=lambda: self.chunker.split_document(document),
            )
            self._emit_progress(
                on_progress=progress_callback,
                progress_state=progress_state,
                stage_name="split",
            )

            transformed_chunks = chunks
            for transform in self.transforms:
                transform_name = transform.__class__.__name__
                transformed_chunks = self._run_stage(
                    stage_name=f"transform.{transform_name}",
                    trace=active_trace,
                    action=lambda t=transform, c=transformed_chunks: t.transform(c, trace=active_trace),
                )
                # transform 链通常由多个独立子步骤组成；这里每完成一个子步骤就推进一次进度，
                # 让 Dashboard 能看到比“整个 transform 结束后一次跳变”更平滑的反馈。
                self._emit_progress(
                    on_progress=progress_callback,
                    progress_state=progress_state,
                    stage_name="transform",
                )

            records = self._run_stage(
                stage_name="encode",
                trace=active_trace,
                action=lambda: self.batch_processor.process(transformed_chunks, trace=active_trace),
            )
            self._emit_progress(
                on_progress=progress_callback,
                progress_state=progress_state,
                stage_name="embed",
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
            self._emit_progress(
                on_progress=progress_callback,
                progress_state=progress_state,
                stage_name="upsert",
            )

            bm25_records = self._build_bm25_records_with_storage_ids(records=records, vector_ids=vector_ids)

            bm25_stats = self._run_stage(
                stage_name="store.bm25",
                trace=active_trace,
                action=lambda: self.bm25_indexer.build(bm25_records, rebuild=False),
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

        finally:
            # F4 要求 ingestion 入口显式形成完整 trace 类型；这里统一在入口收口，
            # 既兼容外部传入 trace，也避免调用方忘记 finish 导致 trace 处于“未完成”状态。
            active_trace.finish()

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
                self._record_f4_stage(
                    trace=trace,
                    stage_name=stage_name,
                    elapsed_ms=elapsed_ms,
                    summary=summary,
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
                self._record_f4_stage(
                    trace=trace,
                    stage_name=stage_name,
                    elapsed_ms=elapsed_ms,
                    summary={"error_type": type(exc).__name__, "error": str(exc)},
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
    def _attach_runtime_metadata(document: Document, collection: str, file_hash: str) -> None:
        """把运行期 metadata 补到 Document 上，供后续 chunk 继承。

        做什么：
        - 注入 `collection`，让每个 chunk 在向量库中都可按业务集合过滤；
        - 注入 `file_hash`，让后续 DocumentManager 更容易把向量库记录和完整性记录对齐。

        为什么放在 split 前：
        - DocumentChunker 会把文档级 metadata 复制到每个 chunk；
        - 所以这里补一次，就能自动贯穿后续 transform/encode/upsert 全链路。
        """
        metadata = dict(document.metadata)
        metadata["collection"] = collection
        metadata["file_hash"] = file_hash
        document.metadata = metadata

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
    def _build_bm25_records_with_storage_ids(
        *,
        records: list[ChunkRecord],
        vector_ids: list[str],
    ) -> list[ChunkRecord]:
        """为 BM25 构建生成与向量库存储主键对齐的记录视图。

        为什么需要这个转换：
        - `BatchProcessor`/上游 chunker 产出的 `record.id` 代表“切分阶段 ID”；
        - `VectorUpserter` 会基于 source_path/chunk_index/content 重新生成真实存储主键 `chunk_xxx`；
        - 如果 BM25 仍索引旧 `record.id`，而 SparseRetriever 再用这些 ID 去向量库回填正文，就会出现
          “BM25 命中有结果，但 get_by_ids() 查不到正文”的错位问题。

        这里的做法：
        - 复制一份 `ChunkRecord` 视图给 BM25 使用；
        - 把复制对象的 `id` 替换为 `vector_ids` 中对应的真实存储主键；
        - 原始 `records` 保持不变，避免影响上游 trace/调试语义。
        """
        if len(records) != len(vector_ids):
            raise ValueError(
                "vector_ids length mismatch after vector upsert: "
                f"records={len(records)}, vector_ids={len(vector_ids)}"
            )

        aligned_records: list[ChunkRecord] = []
        for idx, (record, storage_id) in enumerate(zip(records, vector_ids)):
            if not isinstance(storage_id, str) or not storage_id.strip():
                raise ValueError(f"vector_ids[{idx}] must be non-empty string")

            aligned_records.append(
                ChunkRecord(
                    id=storage_id,
                    text=record.text,
                    metadata=dict(record.metadata),
                    dense_vector=list(record.dense_vector) if record.dense_vector is not None else None,
                    sparse_vector=dict(record.sparse_vector) if record.sparse_vector is not None else None,
                )
            )

        return aligned_records

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

    def _record_f4_stage(
        self,
        *,
        trace: TraceContext,
        stage_name: str,
        elapsed_ms: float,
        summary: dict[str, object],
        status: str = "ok",
    ) -> None:
        """为 F4 产出稳定的 ingestion 通用阶段名与 method/provider 字段。

        做什么：
        - 将现有细粒度 `pipeline.*` 阶段映射为 F4 验收要求的通用阶段：
          `load/split/transform/embed/upsert`。
        - 保留现有细粒度 trace 不变，同时补一层更稳定的“面向 Dashboard/验收”的入口级阶段。

        为什么：
        - 细粒度阶段适合排障，但阶段名会随着内部实现细分而波动；
          F4 和后续 Dashboard 需要一组稳定、可横向比较的 ingestion 主阶段名。

        关键权衡：
        - 这里不会删除或覆盖 `pipeline.*`，而是额外追加一层汇总阶段，
          避免破坏已有调试信息与历史测试。

        失败路径：
        - 未命中 F4 关注的阶段时直接跳过，不抛错；这样不会把非 F4 阶段强行塞进统一模型。
        """
        mapped = self._map_f4_stage(stage_name=stage_name, summary=summary)
        if mapped is None:
            return

        trace.record_stage(
            stage_name=mapped["stage_name"],
            details={
                "method": mapped["method"],
                "provider": mapped["provider"],
                "source_stage": stage_name,
                **mapped["details"],
            },
            elapsed_ms=elapsed_ms,
            status=status,
        )

    def _map_f4_stage(
        self,
        *,
        stage_name: str,
        summary: dict[str, object],
    ) -> dict[str, object] | None:
        """把 pipeline 内部阶段映射为 F4 统一 ingestion 阶段。

        说明：
        - `load`、`split`、`transform.*`、`encode`、`store.vector_upsert` 是 F4 的核心观察面。
        - `store.images`、`store.bm25`、完整性检查等仍保留在 `pipeline.*` 细粒度 trace 中，
          但不纳入本轮 F4 的统一主阶段集合。
        """
        if stage_name == "load":
            return {
                "stage_name": "load",
                "method": "pdf_to_markdown_with_images",
                "provider": type(self.loader).__name__,
                "details": {
                    "result_type": summary.get("result_type", "Document"),
                    "document_id": getattr(summary, "document_id", None),
                    **summary,
                },
            }

        if stage_name == "split":
            return {
                "stage_name": "split",
                "method": str(self.settings.ingestion.splitter).strip().lower() or "recursive",
                "provider": type(getattr(self.chunker, "splitter", self.chunker)).__name__,
                "details": {
                    "chunk_size": int(self.settings.ingestion.chunk_size),
                    "chunk_overlap": int(self.settings.ingestion.chunk_overlap),
                    **summary,
                },
            }

        if stage_name.startswith("transform."):
            transform_name = stage_name.split(".", 1)[1]
            return {
                "stage_name": "transform",
                "method": transform_name,
                "provider": transform_name,
                "details": {
                    "transform_name": transform_name,
                    **summary,
                },
            }

        if stage_name == "encode":
            return {
                "stage_name": "embed",
                "method": "batch_dense_sparse_encode",
                "provider": self.settings.embedding.provider,
                "details": {
                    "batch_size": int(self.settings.ingestion.batch_size),
                    "embedding_provider": self.settings.embedding.provider,
                    **summary,
                },
            }

        if stage_name == "store.vector_upsert":
            return {
                "stage_name": "upsert",
                "method": "vector_store_upsert",
                "provider": self.settings.vector_store.provider,
                "details": {
                    "vector_store_provider": self.settings.vector_store.provider,
                    **summary,
                },
            }

        return None

    def _make_progress_state(self) -> dict[str, int]:
        """构造 F5 进度计数器。

        做什么：
        - 计算本次 pipeline 预计会产生多少个可观测进度步；
        - 返回一个可在 `run()` 生命周期内原地递增的轻量状态字典。

        为什么：
        - transform 链长度是可配置的，不能把总步数写死成常量；
        - 用简单字典而不是专门类，能减少额外样板代码，保持入口层实现直接可读。
        """
        return {
            "current": 0,
            "total": len(self.transforms) + 4,
        }

    @staticmethod
    def _normalize_on_progress(
        on_progress: Callable[[str, int, int], None] | None,
    ) -> Callable[[str, int, int], None] | None:
        """校验进度回调签名入口。

        失败路径：
        - 当调用方传入了非空但不可调用对象时，立即抛 `ValueError`，
          避免 pipeline 跑到中途才因为回调对象错误而暴露问题。
        """
        if on_progress is None:
            return None
        if not callable(on_progress):
            raise ValueError("on_progress must be callable when provided")
        return on_progress

    def _emit_progress(
        self,
        *,
        on_progress: Callable[[str, int, int], None] | None,
        progress_state: dict[str, int],
        stage_name: str,
    ) -> None:
        """触发一次 F5 进度回调。

        做什么：
        - 在指定阶段完成后推进 `current` 计数；
        - 调用外部回调，把当前阶段与 `(current, total)` 发送出去。

        为什么：
        - 回调属于“可观测性增强”而不是核心业务，因此实现应尽量集中在入口层，
          避免把回调逻辑散落到各子组件里。

        关键权衡：
        - 外部回调异常不会中断 ingestion 主链路，只记录 warning。
          这样 UI/展示层的问题不会反向拖垮数据摄取。
        """
        if on_progress is None:
            return

        progress_state["current"] += 1
        current = int(progress_state["current"])
        total = int(progress_state["total"])

        try:
            on_progress(stage_name, current, total)
        except Exception as exc:
            LOGGER.warning(
                "[Pipeline] progress.callback_error stage=%s current=%s total=%s error=%s:%s",
                stage_name,
                current,
                total,
                type(exc).__name__,
                exc,
            )
