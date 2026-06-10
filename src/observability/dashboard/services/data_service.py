"""Dashboard 数据浏览服务（G3）。

这个服务层专门把“底层存储视角”整理成“页面浏览视角”：
- 文档列表来自 `DocumentManager`，因为它已经把 chunk 聚合回了文档；
- chunk 详情直接读 `ChromaStore.get_by_metadata()`，避免页面层自己理解向量库返回结构；
- 图片列表直接读 `ImageStorage.list_images()`，让页面能拿到预览路径与索引信息。

这样做的目标是把 Dashboard 页面保持在“只关心展示”的层级，不把存储细节散落到 Streamlit 代码里。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ingestion.document_manager import DocumentInfo, DocumentManager
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.vector_store.chroma_store import ChromaStore
from observability.dashboard.services.config_service import ConfigService


@dataclass(frozen=True)
class BrowserChunk:
    """数据浏览页中单个 chunk 的展示模型。"""

    chunk_id: str
    chunk_index: int
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class BrowserImage:
    """数据浏览页中单张关联图片的展示模型。"""

    image_id: str
    file_path: str
    page_num: int | None
    created_at: str | None


@dataclass(frozen=True)
class DataBrowserSnapshot:
    """数据浏览页一次渲染所需的完整快照。"""

    collection_options: list[str] = field(default_factory=list)
    active_collection: str | None = None
    documents: list[DocumentInfo] = field(default_factory=list)
    selected_document: DocumentInfo | None = None
    chunks: list[BrowserChunk] = field(default_factory=list)
    images: list[BrowserImage] = field(default_factory=list)


class DataService:
    """为数据浏览页提供“文档 -> chunk -> 图片”三级浏览数据。

    做什么：
    - 统一构造 G3 页面需要的后端依赖；
    - 提供集合过滤后的文档列表；
    - 在用户选中某个文档后，继续补齐它的 chunk 正文、metadata 与图片预览路径。

    为什么单独做一层：
    - Streamlit 页面天然更适合描述布局，而不适合散落大量“查哪张表、按什么字段过滤”的细节；
    - G3 后续还会演进为 G4 的删除/刷新入口，把读取逻辑先沉到服务层，后面扩展成本更低。

    关键权衡：
    - 文档列表优先复用 `DocumentManager.list_documents()`，确保“文档视角”的定义与 G2 保持一致；
    - 但 chunk / 图片明细仍直接走 Chroma 与 ImageStorage，这样既满足 G3 对明细浏览的需求，也符合规格里
      “DataService 封装 `get_by_metadata()` / `list_images()`” 的要求。

    失败路径：
    - 如果底层存储初始化失败，会把异常直接抛出，让 Dashboard 明确暴露配置/环境问题；
    - 对单个 chunk metadata 的坏格式则尽量局部降级为原始字符串，避免一条脏数据拖垮整页浏览。
    """

    def __init__(
        self,
        *,
        settings_path: str | Path = "config/settings.yaml",
        config_service: ConfigService | None = None,
        document_manager: DocumentManager | None = None,
        chroma_store: ChromaStore | None = None,
        image_storage: ImageStorage | None = None,
    ) -> None:
        self.config_service = config_service or ConfigService(settings_path)
        self._document_manager = document_manager
        self._chroma_store = chroma_store
        self._image_storage = image_storage

    def build_browser_snapshot(
        self,
        *,
        collection: str | None = None,
        selected_doc_id: str | None = None,
    ) -> DataBrowserSnapshot:
        """构造数据浏览页的完整快照。

        做什么：
        - 先读取全量文档列表，生成稳定的 collection 过滤选项；
        - 再按当前过滤条件读取文档列表；
        - 如果页面已有选中文档，则继续装配该文档的 chunk 与图片详情。

        为什么分两次取列表：
        - collection 下拉框需要稳定展示“全局有哪些集合”；
        - 但文档明细又只应该展示过滤后的结果；
        - 这样可以避免切换过滤器时，下拉选项跟着抖动，页面交互更稳定。
        """
        all_documents = self.document_manager.list_documents()
        documents = self.document_manager.list_documents(collection=collection)
        collection_options = sorted({item.collection for item in all_documents if item.collection})

        selected_document = self._resolve_selected_document(documents, selected_doc_id)
        chunks: list[BrowserChunk] = []
        images: list[BrowserImage] = []
        if selected_document is not None:
            chunks = self.list_document_chunks(
                source_path=selected_document.source_path,
                collection=selected_document.collection,
            )
            images = self.list_document_images(
                collection=selected_document.collection,
                doc_hash=selected_document.doc_hash,
            )

        return DataBrowserSnapshot(
            collection_options=collection_options,
            active_collection=collection,
            documents=documents,
            selected_document=selected_document,
            chunks=chunks,
            images=images,
        )

    def list_document_chunks(self, *, source_path: str, collection: str | None = None) -> list[BrowserChunk]:
        """读取单个文档的全部 chunk，并整理成稳定顺序。

        为什么这里显式做排序与 metadata 解析：
        - Dashboard 浏览要求 chunk 顺序稳定，否则用户每次展开看到的顺序可能跳变；
        - Chroma metadata 中有些字段会以 JSON 字符串形式保存，页面直接展示会很难读，
          因此这里先恢复成 Python 结构，页面层只负责渲染。
        """
        filters: dict[str, Any] = {"source_path": source_path}
        if collection:
            filters["collection"] = collection

        rows = self.chroma_store.get_by_metadata(filters)
        if not rows and collection:
            # 兼容旧数据：部分历史 chunk 可能没有写入 collection metadata。
            rows = self.chroma_store.get_by_metadata({"source_path": source_path})

        chunks: list[BrowserChunk] = []
        for row in rows:
            metadata = self._normalize_chunk_metadata(row.get("metadata"))
            row_collection = self._get_non_empty_string(metadata, "collection")
            if collection is not None and row_collection not in {None, "", collection}:
                continue

            chunks.append(
                BrowserChunk(
                    chunk_id=str(row.get("id", "")),
                    chunk_index=self._safe_int(metadata.get("chunk_index")),
                    text=str(row.get("text", "")),
                    metadata=metadata,
                )
            )

        chunks.sort(key=lambda item: (item.chunk_index, item.chunk_id))
        return chunks

    def list_document_images(self, *, collection: str | None, doc_hash: str | None) -> list[BrowserImage]:
        """读取单个文档关联的图片索引记录。"""
        if not doc_hash:
            return []

        if collection:
            rows = self.image_storage.list_images(collection=collection, doc_hash=doc_hash)
        else:
            rows = self.image_storage.list_images(doc_hash=doc_hash)

        images = [
            BrowserImage(
                image_id=str(row.get("image_id", "")),
                file_path=str(row.get("file_path", "")),
                page_num=self._safe_optional_int(row.get("page_num")),
                created_at=str(row.get("created_at", "")).strip() or None,
            )
            for row in rows
        ]
        images.sort(key=lambda item: item.image_id)
        return images

    @property
    def document_manager(self) -> DocumentManager:
        """懒加载 `DocumentManager`，避免页面导入阶段就提前触发后端初始化。"""
        if self._document_manager is None:
            self._document_manager = self._build_document_manager()
        return self._document_manager

    @property
    def chroma_store(self) -> ChromaStore:
        """懒加载 ChromaStore，供 chunk 明细读取复用。"""
        if self._chroma_store is None:
            self._chroma_store = self._build_chroma_store()
        return self._chroma_store

    @property
    def image_storage(self) -> ImageStorage:
        """懒加载 ImageStorage，供图片明细读取复用。"""
        if self._image_storage is None:
            self._image_storage = self._build_image_storage()
        return self._image_storage

    def _build_document_manager(self) -> DocumentManager:
        """按项目默认路径构造 Dashboard 浏览需要的真实依赖。"""
        settings = self.config_service.load_settings()
        bm25_indexer = BM25Indexer(persist_dir=str(self._resolve_project_path("data/db/bm25")))
        file_integrity = SQLiteIntegrityChecker(
            db_path=str(self._resolve_project_path("data/db/ingestion_history.db"))
        )
        return DocumentManager(
            chroma_store=self._build_chroma_store(settings.vector_store.persist_dir),
            bm25_indexer=bm25_indexer,
            image_storage=self._build_image_storage(),
            file_integrity=file_integrity,
        )

    def _build_chroma_store(self, persist_dir: str | None = None) -> ChromaStore:
        """构造指向当前项目向量库目录的 ChromaStore。"""
        settings = self.config_service.load_settings()
        resolved_persist_dir = self._resolve_project_path(persist_dir or settings.vector_store.persist_dir)
        return ChromaStore(persist_dir=str(resolved_persist_dir))

    def _build_image_storage(self) -> ImageStorage:
        """构造指向当前项目图片目录与索引库的 ImageStorage。"""
        return ImageStorage(
            image_root=str(self._resolve_project_path("data/images")),
            db_path=str(self._resolve_project_path("data/db/image_index.db")),
        )

    def _resolve_project_path(self, raw_path: str) -> Path:
        """把相对路径解析到 settings 所在项目根目录下。"""
        path = Path(raw_path)
        if path.is_absolute():
            return path
        settings_path = self.config_service.settings_path.resolve()
        return (settings_path.parent.parent / path).resolve()

    @staticmethod
    def _resolve_selected_document(
        documents: list[DocumentInfo],
        selected_doc_id: str | None,
    ) -> DocumentInfo | None:
        """在过滤后的文档列表中解析当前选中的文档。"""
        if not documents:
            return None
        if selected_doc_id:
            for item in documents:
                if item.doc_id == selected_doc_id:
                    return item
        return documents[0]

    @staticmethod
    def _normalize_chunk_metadata(raw_metadata: Any) -> dict[str, Any]:
        """把常见 JSON 字符串字段恢复成可直接展示的结构。

        这里优先恢复 `images` / `heading_outline`，因为它们在 Dashboard 中最容易直接被用户看到。
        如果解析失败，就保留原始值，避免因为一条坏 metadata 影响整个页面。
        """
        if not isinstance(raw_metadata, dict):
            return {}

        metadata = dict(raw_metadata)
        for key in ("images", "heading_outline"):
            value = metadata.get(key)
            if isinstance(value, str):
                parsed = DataService._try_parse_json(value)
                if parsed is not None:
                    metadata[key] = parsed
        return metadata

    @staticmethod
    def _try_parse_json(raw_text: str) -> Any | None:
        """尝试把 JSON 字符串解析回 Python 结构。"""
        text = raw_text.strip()
        if not text or text[0] not in "[{":
            return None
        try:
            return json.loads(text)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _get_non_empty_string(metadata: dict[str, Any], key: str) -> str | None:
        """安全读取 metadata 中的非空字符串。"""
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _safe_int(value: Any) -> int:
        """把可能缺失的 chunk_index 转成稳定排序值。"""
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 10**9

    @staticmethod
    def _safe_optional_int(value: Any) -> int | None:
        """把可选页码安全转换为 int。"""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None
