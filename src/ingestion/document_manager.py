"""DocumentManager：跨存储的文档生命周期管理（G2）。

当前系统的“事实”分散在四个存储里：
- Chroma 负责 chunk 正文与 metadata；
- BM25 负责稀疏索引；
- ImageStorage 负责图片文件与图片索引；
- FileIntegrity 负责 file_hash 与处理历史。

Dashboard 想展示和删除的是“文档”，不是“chunk”。
这个模块的职责就是把底层的 chunk 视角重新聚合成文档视角，并在删除时协调四个后端。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from libs.loader.file_integrity import FileIntegrityChecker
from libs.vector_store.chroma_store import ChromaStore


@dataclass(frozen=True)
class DocumentInfo:
    """文档列表项。

    当前阶段将 `doc_id` 直接定义为 `source_path`。

    为什么这样做：
    - G2 需要一个跨存储稳定 ID；
    - 现阶段最稳定、所有存储都能对齐的标识其实就是源文件路径；
    - 这样可以避免为了“再造一个 doc_id”而额外引入映射表和同步复杂度。
    """

    doc_id: str
    source_path: str
    collection: str | None
    title: str
    doc_type: str
    chunk_count: int
    image_count: int
    processed_at: str | None
    file_hash: str | None
    doc_hash: str | None
    size_bytes: int


@dataclass(frozen=True)
class DocumentDetail:
    """单文档详情。"""

    doc_id: str
    source_path: str
    collection: str | None
    title: str
    doc_type: str
    chunk_count: int
    image_count: int
    processed_at: str | None
    file_hash: str | None
    doc_hash: str | None
    size_bytes: int
    chunks: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DeleteResult:
    """删除结果摘要。

    这里显式返回每个后端的删除计数，而不是只返回一个 success/fail。

    为什么：
    - 四个后端不是同一种存储，无法天然共享事务；
    - 一旦某一步已经执行，后续失败时就可能出现“部分删除”；
    - 把每个子动作的结果暴露出来，调用方才能准确看懂实际发生了什么。
    """

    doc_id: str
    source_path: str
    collection: str
    chunks_deleted: int
    bm25_deleted: int
    images_deleted: int
    integrity_deleted: int
    file_hash: str | None
    doc_hash: str | None
    fallback_used: bool = False
    fallback_reason: str | None = None


@dataclass(frozen=True)
class CollectionStats:
    """集合级统计结果。"""

    collection: str | None
    document_count: int
    chunk_count: int
    image_count: int
    size_bytes: int
    collections: list[dict[str, Any]] = field(default_factory=list)


class DocumentManager:
    """跨存储文档管理器。

    做什么：
    - 从 Chroma 读取 chunk，再按 `source_path` 聚合为文档列表；
    - 读取单文档详情时补齐 chunk 与图片；
    - 删除文档时协调 Chroma/BM25/ImageStorage/FileIntegrity。

    为什么：
    - 底层为了检索性能是“chunk 中心”；
    - 但人类在管理界面里关心的是“文档”；
    - 这个模块就是两种视角之间的翻译层。

    关键权衡：
    - 当前优先保证逻辑直接、可读、可调试，因此以“先读全部/再聚合”为主；
    - 对超大规模数据这不是最省资源的做法，但对当前 Dashboard 阶段更稳妥。
    """

    def __init__(
        self,
        chroma_store: ChromaStore,
        bm25_indexer: BM25Indexer,
        image_storage: ImageStorage,
        file_integrity: FileIntegrityChecker,
    ) -> None:
        self.chroma_store = chroma_store
        self.bm25_indexer = bm25_indexer
        self.image_storage = image_storage
        self.file_integrity = file_integrity

    def list_documents(self, collection: str | None = None) -> list[DocumentInfo]:
        """列出已摄入文档。

        做什么：
        - 读取 Chroma 中的 chunk；
        - 按 `source_path` 分组并聚合 chunk 数、标题、类型；
        - 再用图片索引和完整性记录补齐图片数、时间、hash。

        为什么主数据源选 Chroma：
        - 文档浏览器关心“现在库里实际可检索的内容”；
        - FileIntegrity 只知道文件是否处理过，不知道现在还剩多少 chunk。

        失败路径：
        - 空库直接返回空列表；
        - 坏 chunk 若缺失 `source_path`，只跳过该条，不污染整份列表。
        """
        chunk_rows = self.chroma_store.get_by_metadata()
        integrity_by_source = self._build_integrity_index()
        image_index = self._build_image_index(collection=collection)

        grouped: dict[str, dict[str, Any]] = {}
        for row in chunk_rows:
            metadata = self._normalize_chunk_metadata(row.get("metadata"))
            source_path = self._get_non_empty_string(metadata, "source_path")
            if not source_path:
                continue

            group = grouped.setdefault(
                source_path,
                {
                    "source_path": source_path,
                    "title": "",
                    "doc_type": "",
                    "chunk_count": 0,
                    "chunk_text_bytes": 0,
                    "collections": set(),
                    "file_hash": None,
                    "sha256": None,
                },
            )
            group["chunk_count"] += 1
            group["chunk_text_bytes"] += len(str(row.get("text", "")).encode("utf-8"))

            title = self._get_non_empty_string(metadata, "title")
            doc_type = self._get_non_empty_string(metadata, "doc_type")
            file_hash = self._get_non_empty_string(metadata, "file_hash")
            sha256 = self._get_non_empty_string(metadata, "sha256")
            collection_name = self._get_non_empty_string(metadata, "collection")

            if title and not group["title"]:
                group["title"] = title
            if doc_type and not group["doc_type"]:
                group["doc_type"] = doc_type
            if file_hash and not group["file_hash"]:
                group["file_hash"] = file_hash
            if sha256 and not group["sha256"]:
                group["sha256"] = sha256
            if collection_name:
                group["collections"].add(collection_name)

        documents: list[DocumentInfo] = []
        for source_path, group in grouped.items():
            integrity_row = integrity_by_source.get(source_path)
            file_hash = group["file_hash"] or self._row_text(integrity_row, "file_hash") or group["sha256"]
            doc_hash = self._to_doc_hash(file_hash)
            image_bucket = image_index.get(doc_hash or "", {})

            if collection is not None and not self._matches_requested_collection(
                requested_collection=collection,
                metadata_collections=group["collections"],
                image_collections=set(image_bucket.keys()),
            ):
                # 当调用方显式点名某个 collection 时，只有“现有证据显示它属于该 collection”
                # 才应该进入结果集；不能因为兜底逻辑把别的文档误算进来。
                continue

            resolved_collection = self._resolve_collection_name(
                requested_collection=collection,
                metadata_collections=group["collections"],
                image_collections=set(image_bucket.keys()),
            )

            image_rows = (
                image_bucket.get(resolved_collection, [])
                if resolved_collection is not None
                else self._flatten_image_rows(image_bucket)
            )
            image_count = len(image_rows)
            image_bytes = self._sum_image_bytes(image_rows)

            documents.append(
                DocumentInfo(
                    doc_id=source_path,
                    source_path=source_path,
                    collection=resolved_collection,
                    title=str(group["title"] or Path(source_path).stem),
                    doc_type=str(group["doc_type"] or "unknown"),
                    chunk_count=int(group["chunk_count"]),
                    image_count=image_count,
                    processed_at=self._row_text(integrity_row, "processed_at"),
                    file_hash=file_hash,
                    doc_hash=doc_hash,
                    size_bytes=int(group["chunk_text_bytes"]) + image_bytes,
                )
            )

        documents.sort(
            key=lambda item: (
                item.processed_at is None,
                item.processed_at or "",
                item.source_path.lower(),
            ),
            reverse=True,
        )
        return documents

    def get_document_detail(self, doc_id: str) -> DocumentDetail:
        """读取单文档详情。

        Args:
            doc_id: 当前实现中等同于 `source_path`。

        Raises:
            ValueError: 找不到文档时抛出。
        """
        normalized_doc_id = self._require_non_empty_string(doc_id, "doc_id")
        summary = next((item for item in self.list_documents() if item.doc_id == normalized_doc_id), None)
        if summary is None:
            raise ValueError(f"Document not found: {normalized_doc_id}")

        chunk_rows = self.chroma_store.get_by_metadata({"source_path": summary.source_path})
        chunks: list[dict[str, Any]] = []
        for row in chunk_rows:
            metadata = self._normalize_chunk_metadata(row.get("metadata"))
            row_collection = self._get_non_empty_string(metadata, "collection")
            if summary.collection is not None and row_collection not in {None, "", summary.collection}:
                continue

            chunks.append(
                {
                    "chunk_id": str(row.get("id", "")),
                    "text": str(row.get("text", "")),
                    "metadata": metadata,
                    "chunk_index": self._safe_int(metadata.get("chunk_index")),
                }
            )
        chunks.sort(key=lambda item: (item["chunk_index"], item["chunk_id"]))

        images = self._list_document_images(summary.collection, summary.doc_hash)
        return DocumentDetail(
            doc_id=summary.doc_id,
            source_path=summary.source_path,
            collection=summary.collection,
            title=summary.title,
            doc_type=summary.doc_type,
            chunk_count=summary.chunk_count,
            image_count=summary.image_count,
            processed_at=summary.processed_at,
            file_hash=summary.file_hash,
            doc_hash=summary.doc_hash,
            size_bytes=summary.size_bytes,
            chunks=chunks,
            images=images,
        )

    def delete_document(self, source_path: str, collection: str) -> DeleteResult:
        """删除文档相关数据，并返回各后端的删除结果。"""
        normalized_source = self._require_non_empty_string(source_path, "source_path")
        normalized_collection = self._require_non_empty_string(collection, "collection")

        summaries = self.list_documents()
        summary = next((item for item in summaries if item.source_path == normalized_source), None)

        chunks_deleted = self.chroma_store.delete_by_metadata(
            {"source_path": normalized_source, "collection": normalized_collection}
        )
        fallback_used = False
        fallback_reason: str | None = None

        if chunks_deleted == 0:
            # 兼容旧数据：如果老 chunk 没有 collection metadata，不能让它变成“删不掉”的脏数据。
            chunks_deleted = self.chroma_store.delete_by_metadata({"source_path": normalized_source})
            fallback_used = True
            fallback_reason = "legacy_records_missing_collection_metadata"

        bm25_deleted = int(self.bm25_indexer.remove_document(normalized_source))

        doc_hash = summary.doc_hash if summary is not None else None
        images_deleted = 0
        if doc_hash is not None:
            images_deleted = int(self.image_storage.delete_images(normalized_collection, doc_hash))

        file_hash = summary.file_hash if summary is not None else None
        integrity_deleted = 0
        if file_hash:
            self.file_integrity.remove_record(file_hash)
            integrity_deleted = 1

        return DeleteResult(
            doc_id=normalized_source,
            source_path=normalized_source,
            collection=normalized_collection,
            chunks_deleted=chunks_deleted,
            bm25_deleted=bm25_deleted,
            images_deleted=images_deleted,
            integrity_deleted=integrity_deleted,
            file_hash=file_hash,
            doc_hash=doc_hash,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    def get_collection_stats(self, collection: str | None = None) -> CollectionStats:
        """统计文档、chunk、图片和近似体积。"""
        documents = self.list_documents(collection=collection)
        if collection is not None:
            return CollectionStats(
                collection=collection,
                document_count=len(documents),
                chunk_count=sum(item.chunk_count for item in documents),
                image_count=sum(item.image_count for item in documents),
                size_bytes=sum(item.size_bytes for item in documents),
                collections=[],
            )

        grouped: dict[str, dict[str, int]] = {}
        for item in documents:
            group_name = item.collection or "<unknown>"
            group = grouped.setdefault(
                group_name,
                {"document_count": 0, "chunk_count": 0, "image_count": 0, "size_bytes": 0},
            )
            group["document_count"] += 1
            group["chunk_count"] += item.chunk_count
            group["image_count"] += item.image_count
            group["size_bytes"] += item.size_bytes

        collections = [{"name": name, **grouped[name]} for name in sorted(grouped)]
        return CollectionStats(
            collection=None,
            document_count=len(documents),
            chunk_count=sum(item.chunk_count for item in documents),
            image_count=sum(item.image_count for item in documents),
            size_bytes=sum(item.size_bytes for item in documents),
            collections=collections,
        )

    def _build_integrity_index(self) -> dict[str, dict[str, Any]]:
        """按 `file_path` 建立完整性记录索引。

        约定：
        - `list_processed()` 当前已按 processed_at 倒序返回；
        - 所以同一路径只取第一次出现的记录，就等于最新记录。
        """
        if not hasattr(self.file_integrity, "list_processed"):
            return {}

        rows = getattr(self.file_integrity, "list_processed")()
        if not isinstance(rows, list):
            return {}

        indexed: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            source_path = self._row_text(row, "file_path")
            if source_path and source_path not in indexed:
                indexed[source_path] = row
        return indexed

    def _build_image_index(self, collection: str | None = None) -> dict[str, dict[str, list[dict[str, Any]]]]:
        """按 `doc_hash -> collection -> images[]` 组织图片索引。"""
        rows = self.image_storage.list_images(collection=collection) if collection else self.image_storage.list_images()
        grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            doc_hash = self._row_text(row, "doc_hash")
            image_collection = self._row_text(row, "collection") or "<unknown>"
            if not doc_hash:
                continue
            grouped.setdefault(doc_hash, {}).setdefault(image_collection, []).append(row)
        return grouped

    def _list_document_images(self, collection: str | None, doc_hash: str | None) -> list[dict[str, Any]]:
        """按 collection/doc_hash 读取单文档图片。"""
        if not doc_hash:
            return []
        if collection:
            return self.image_storage.list_images(collection=collection, doc_hash=doc_hash)
        return self.image_storage.list_images(doc_hash=doc_hash)

    @staticmethod
    def _flatten_image_rows(grouped_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """把 `collection -> rows[]` 压平成一个列表。"""
        flattened: list[dict[str, Any]] = []
        for rows in grouped_rows.values():
            flattened.extend(rows)
        return flattened

    @staticmethod
    def _sum_image_bytes(rows: list[dict[str, Any]]) -> int:
        """统计图片文件大小。"""
        total = 0
        for row in rows:
            file_path = str(row.get("file_path", "")).strip()
            if not file_path:
                continue
            path = Path(file_path)
            if path.exists() and path.is_file():
                total += int(path.stat().st_size)
        return total

    @staticmethod
    def _resolve_collection_name(
        *,
        requested_collection: str | None,
        metadata_collections: set[str],
        image_collections: set[str],
    ) -> str | None:
        """解析文档所属 collection。

        优先级：
        1. 调用方显式指定；
        2. chunk metadata 中只有一个 collection；
        3. 图片索引中只有一个 collection；
        4. 仍无法确定则返回 `None`。
        """
        if requested_collection:
            return requested_collection
        if len(metadata_collections) == 1:
            return next(iter(metadata_collections))
        if len(image_collections) == 1:
            only_collection = next(iter(image_collections))
            return None if only_collection == "<unknown>" else only_collection
        return None

    @staticmethod
    def _matches_requested_collection(
        *,
        requested_collection: str,
        metadata_collections: set[str],
        image_collections: set[str],
    ) -> bool:
        """判断文档是否有足够证据属于调用方指定的 collection。

        规则：
        - metadata 明确命中则算命中；
        - 若 metadata 没写，但图片索引命中，也允许视为命中；
        - 两边都没有证据时，不把文档硬塞进用户指定集合，避免误统计。
        """
        if requested_collection in metadata_collections:
            return True
        if requested_collection in image_collections:
            return True
        return False

    @staticmethod
    def _normalize_chunk_metadata(raw_metadata: Any) -> dict[str, Any]:
        """把向量库中的 metadata 恢复成更适合页面展示的结构。"""
        if not isinstance(raw_metadata, dict):
            return {}

        metadata = dict(raw_metadata)
        for key in ("images", "heading_outline"):
            value = metadata.get(key)
            if isinstance(value, str):
                parsed = DocumentManager._try_parse_json(value)
                if parsed is not None:
                    metadata[key] = parsed
        return metadata

    @staticmethod
    def _try_parse_json(raw_text: str) -> Any | None:
        """尝试把 JSON 字符串恢复为 Python 对象。"""
        text = raw_text.strip()
        if not text or text[0] not in "[{":
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    @staticmethod
    def _to_doc_hash(file_hash: str | None) -> str | None:
        """把完整 file_hash 截断为图片目录常用的 16 位 doc_hash。"""
        if not isinstance(file_hash, str):
            return None
        normalized = file_hash.strip()
        if len(normalized) < 16:
            return None
        return normalized[:16]

    @staticmethod
    def _row_text(row: dict[str, Any] | None, key: str) -> str | None:
        """安全读取字典中的非空字符串字段。"""
        if not isinstance(row, dict):
            return None
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _get_non_empty_string(metadata: dict[str, Any], key: str) -> str | None:
        """从 metadata 中读取非空字符串。"""
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _safe_int(value: Any) -> int:
        """把可能缺失的 chunk_index 转为稳定排序值。"""
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 10**9

    @staticmethod
    def _require_non_empty_string(value: str, field_name: str) -> str:
        """统一的非空字符串校验。"""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be non-empty string")
        return value.strip()
