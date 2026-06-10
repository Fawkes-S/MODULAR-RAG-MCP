"""Dashboard 数据浏览服务测试（G3）。"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ingestion.document_manager import DocumentManager
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.vector_store.chroma_store import ChromaStore
from observability.dashboard.services.data_service import DataService

pytest.importorskip("chromadb")


@pytest.fixture()
def data_service_bundle() -> dict[str, object]:
    """
    Given:
        一个隔离的临时工作目录，用来承载 G3 需要的 Chroma / ImageStorage / Integrity 数据。
    When:
        基于这些真实但隔离的依赖构造 `DocumentManager + DataService`。
    Then:
        - 测试可以覆盖真实的 metadata 过滤与图片索引读取逻辑；
        - 又不会污染项目默认的本地数据目录。
    """
    root = PROJECT_ROOT / ".pytest_tmp" / f"dashboard_data_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)

    chroma_store = ChromaStore(
        persist_dir=str(root / "data" / "db" / "chroma"),
        collection_name=f"g3_{uuid.uuid4().hex[:8]}",
    )
    bm25_indexer = BM25Indexer(persist_dir=str(root / "data" / "db" / "bm25"))
    image_storage = ImageStorage(
        image_root=str(root / "data" / "images"),
        db_path=str(root / "data" / "db" / "image_index.db"),
    )
    file_integrity = SQLiteIntegrityChecker(db_path=str(root / "data" / "db" / "ingestion_history.db"))
    document_manager = DocumentManager(
        chroma_store=chroma_store,
        bm25_indexer=bm25_indexer,
        image_storage=image_storage,
        file_integrity=file_integrity,
    )
    data_service = DataService(
        document_manager=document_manager,
        chroma_store=chroma_store,
        image_storage=image_storage,
    )

    try:
        yield {
            "root": root,
            "chroma_store": chroma_store,
            "image_storage": image_storage,
            "file_integrity": file_integrity,
            "data_service": data_service,
        }
    finally:
        chroma_store._client.delete_collection(chroma_store.collection_name)
        shutil.rmtree(root, ignore_errors=True)


def _seed_manual_document(bundle: dict[str, object]) -> str:
    """写入一份 manual 集合文档，包含乱序 chunk 与一张图片。"""
    chroma_store = bundle["chroma_store"]
    image_storage = bundle["image_storage"]
    file_integrity = bundle["file_integrity"]
    assert isinstance(chroma_store, ChromaStore)
    assert isinstance(image_storage, ImageStorage)
    assert isinstance(file_integrity, SQLiteIntegrityChecker)

    file_hash = "abcd" * 16
    doc_hash = file_hash[:16]
    source_path = "memory://docs/alpha.pdf"

    chroma_store.upsert(
        [
            {
                "id": "chunk-alpha-2",
                "vector": [0.9, 0.1],
                "metadata": {
                    "source_path": source_path,
                    "collection": "manual",
                    "doc_type": "pdf",
                    "title": "Alpha Guide",
                    "chunk_index": 1,
                    "file_hash": file_hash,
                    "images": '[{"id":"%s_1_0001","path":"loader/path.png"}]' % doc_hash,
                },
                "text": "Alpha chunk second",
            },
            {
                "id": "chunk-alpha-1",
                "vector": [1.0, 0.0],
                "metadata": {
                    "source_path": source_path,
                    "collection": "manual",
                    "doc_type": "pdf",
                    "title": "Alpha Guide",
                    "chunk_index": 0,
                    "file_hash": file_hash,
                },
                "text": "Alpha chunk first",
            },
        ]
    )

    image_storage.save_image(
        image_id=f"{doc_hash}_1_0001",
        image_bytes=b"alpha-image",
        collection="manual",
        doc_hash=doc_hash,
        page_num=1,
        extension="png",
    )
    file_integrity.mark_success(
        file_hash=file_hash,
        file_path=source_path,
        file_size=1024,
        chunk_count=2,
    )
    return source_path


def _seed_faq_document(bundle: dict[str, object]) -> str:
    """写入第二份 faq 集合文档，供集合过滤测试使用。"""
    chroma_store = bundle["chroma_store"]
    file_integrity = bundle["file_integrity"]
    assert isinstance(chroma_store, ChromaStore)
    assert isinstance(file_integrity, SQLiteIntegrityChecker)

    file_hash = "1234" * 16
    source_path = "memory://docs/beta.md"

    chroma_store.upsert(
        [
            {
                "id": "chunk-beta-1",
                "vector": [0.0, 1.0],
                "metadata": {
                    "source_path": source_path,
                    "collection": "faq",
                    "doc_type": "md",
                    "title": "Beta FAQ",
                    "chunk_index": 0,
                    "file_hash": file_hash,
                },
                "text": "Beta faq chunk",
            }
        ]
    )
    file_integrity.mark_success(
        file_hash=file_hash,
        file_path=source_path,
        file_size=256,
        chunk_count=1,
    )
    return source_path


def test_data_service_build_browser_snapshot_filters_documents_and_loads_detail(
    data_service_bundle: dict[str, object],
) -> None:
    """
    Given:
        两份属于不同 collection 的文档，其中 manual 文档包含 2 个 chunk 和 1 张图片。
    When:
        调用 `build_browser_snapshot(collection="manual", selected_doc_id=manual_doc)`。
    Then:
        - collection 选项应覆盖 `faq/manual`；
        - 文档列表只保留 manual 文档；
        - 选中文档的 chunk 详情与图片索引应被一并装配出来。
    """
    data_service = data_service_bundle["data_service"]
    assert isinstance(data_service, DataService)

    manual_doc = _seed_manual_document(data_service_bundle)
    _seed_faq_document(data_service_bundle)

    snapshot = data_service.build_browser_snapshot(collection="manual", selected_doc_id=manual_doc)

    assert snapshot.collection_options == ["faq", "manual"]
    assert [item.doc_id for item in snapshot.documents] == [manual_doc]
    assert snapshot.selected_document is not None
    assert snapshot.selected_document.doc_id == manual_doc
    assert len(snapshot.chunks) == 2
    assert len(snapshot.images) == 1


def test_data_service_list_document_chunks_sorts_and_parses_json_metadata(
    data_service_bundle: dict[str, object],
) -> None:
    """
    Given:
        一份 chunk 顺序乱序、且 `images` metadata 以 JSON 字符串形式存储的文档。
    When:
        调用 `list_document_chunks(source_path=...)` 读取 chunk 明细。
    Then:
        - 返回顺序应按 `chunk_index` 稳定排序；
        - `images` 字段应恢复为可直接展示的列表结构；
        - 页面后续无需再自行做 JSON 解析。
    """
    data_service = data_service_bundle["data_service"]
    assert isinstance(data_service, DataService)

    manual_doc = _seed_manual_document(data_service_bundle)

    chunks = data_service.list_document_chunks(source_path=manual_doc, collection="manual")

    assert [chunk.chunk_id for chunk in chunks] == ["chunk-alpha-1", "chunk-alpha-2"]
    assert isinstance(chunks[1].metadata["images"], list)
