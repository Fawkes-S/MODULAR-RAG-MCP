"""DocumentManager 单元测试（G2）。"""

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

from ingestion.document_manager import CollectionStats, DeleteResult, DocumentDetail, DocumentInfo, DocumentManager
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.vector_store.chroma_store import ChromaStore

pytest.importorskip("chromadb")


@pytest.fixture()
def manager_workspace() -> Path:
    """创建隔离工作目录，避免污染真实数据目录。"""
    root = PROJECT_ROOT / ".pytest_tmp" / f"document_manager_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture()
def manager_bundle(manager_workspace: Path) -> dict[str, object]:
    """构造一套真实但隔离的 G2 依赖。"""
    chroma_store = ChromaStore(
        persist_dir=str(manager_workspace / "data" / "db" / "chroma"),
        collection_name=f"g2_{uuid.uuid4().hex[:8]}",
    )
    bm25_indexer = BM25Indexer(persist_dir=str(manager_workspace / "data" / "db" / "bm25"))
    image_storage = ImageStorage(
        image_root=str(manager_workspace / "data" / "images"),
        db_path=str(manager_workspace / "data" / "db" / "image_index.db"),
    )
    file_integrity = SQLiteIntegrityChecker(
        db_path=str(manager_workspace / "data" / "db" / "ingestion_history.db")
    )
    manager = DocumentManager(
        chroma_store=chroma_store,
        bm25_indexer=bm25_indexer,
        image_storage=image_storage,
        file_integrity=file_integrity,
    )

    yield {
        "manager": manager,
        "chroma_store": chroma_store,
        "bm25_indexer": bm25_indexer,
        "image_storage": image_storage,
        "file_integrity": file_integrity,
    }

    chroma_store._client.delete_collection(chroma_store.collection_name)


def _seed_document_a(bundle: dict[str, object]) -> str:
    """写入一份带两个 chunk 和两张图片的文档。"""
    chroma_store = bundle["chroma_store"]
    bm25_indexer = bundle["bm25_indexer"]
    image_storage = bundle["image_storage"]
    file_integrity = bundle["file_integrity"]
    assert isinstance(chroma_store, ChromaStore)
    assert isinstance(bm25_indexer, BM25Indexer)
    assert isinstance(image_storage, ImageStorage)
    assert isinstance(file_integrity, SQLiteIntegrityChecker)

    file_hash = "abcd" * 16
    source_path = "memory://docs/alpha.pdf"
    doc_hash = file_hash[:16]

    chroma_store.upsert(
        [
            {
                "id": "chunk-a-1",
                "vector": [1.0, 0.0],
                "metadata": {
                    "source_path": source_path,
                    "collection": "manual",
                    "doc_type": "pdf",
                    "title": "Alpha Guide",
                    "chunk_index": 0,
                    "file_hash": file_hash,
                    "sha256": file_hash,
                    "image_refs": [f"{doc_hash}_1_0001"],
                },
                "text": "Alpha chunk 1",
            },
            {
                "id": "chunk-a-2",
                "vector": [0.9, 0.1],
                "metadata": {
                    "source_path": source_path,
                    "collection": "manual",
                    "doc_type": "pdf",
                    "title": "Alpha Guide",
                    "chunk_index": 1,
                    "file_hash": file_hash,
                    "sha256": file_hash,
                    "images": '[{"id":"%s_1_0002","path":"loader/path.png"}]' % doc_hash,
                },
                "text": "Alpha chunk 2",
            },
        ]
    )

    image_storage.save_image(
        image_id=f"{doc_hash}_1_0001",
        image_bytes=b"img-1",
        collection="manual",
        doc_hash=doc_hash,
        page_num=1,
        extension="png",
    )
    image_storage.save_image(
        image_id=f"{doc_hash}_1_0002",
        image_bytes=b"img-2",
        collection="manual",
        doc_hash=doc_hash,
        page_num=1,
        extension="png",
    )

    file_integrity.mark_success(
        file_hash=file_hash,
        file_path=source_path,
        file_size=2048,
        chunk_count=2,
    )
    bm25_indexer._doc_term_freqs = {
        "chunk-a-1": {"alpha": 1.0},
        "chunk-a-2": {"guide": 1.0},
    }
    bm25_indexer._doc_lengths = {"chunk-a-1": 1.0, "chunk-a-2": 1.0}
    bm25_indexer._doc_sources = {"chunk-a-1": source_path, "chunk-a-2": source_path}
    bm25_indexer._rebuild_inverted_index()
    bm25_indexer.save()
    return source_path


def _seed_document_b(bundle: dict[str, object]) -> str:
    """写入第二份文档，便于测试分组和过滤。"""
    chroma_store = bundle["chroma_store"]
    file_integrity = bundle["file_integrity"]
    assert isinstance(chroma_store, ChromaStore)
    assert isinstance(file_integrity, SQLiteIntegrityChecker)

    file_hash = "1234" * 16
    source_path = "memory://docs/beta.md"

    chroma_store.upsert(
        [
            {
                "id": "chunk-b-1",
                "vector": [0.0, 1.0],
                "metadata": {
                    "source_path": source_path,
                    "collection": "faq",
                    "doc_type": "md",
                    "title": "Beta FAQ",
                    "chunk_index": 0,
                    "file_hash": file_hash,
                    "sha256": file_hash,
                },
                "text": "Beta chunk 1",
            }
        ]
    )
    file_integrity.mark_success(
        file_hash=file_hash,
        file_path=source_path,
        file_size=128,
        chunk_count=1,
    )
    return source_path


def test_document_manager_list_documents_groups_chunks_and_counts_images(manager_bundle: dict[str, object]) -> None:
    """
    Given:
        两份文档数据，其中第一份文档包含 2 个 chunk、2 张图片、完整的完整性记录。
    When:
        调用 `list_documents()` 读取文档列表。
    Then:
        - 应按 source_path 聚合成 2 条文档；
        - 第一条文档的 chunk/image/title/collection 统计正确；
        - 返回项类型满足 G2 的文档列表契约。
    """
    manager = manager_bundle["manager"]
    assert isinstance(manager, DocumentManager)
    source_a = _seed_document_a(manager_bundle)
    _seed_document_b(manager_bundle)

    documents = manager.list_documents()

    assert len(documents) == 2
    assert all(isinstance(item, DocumentInfo) for item in documents)

    alpha = next(item for item in documents if item.source_path == source_a)
    assert alpha.doc_id == source_a
    assert alpha.collection == "manual"
    assert alpha.title == "Alpha Guide"
    assert alpha.doc_type == "pdf"
    assert alpha.chunk_count == 2
    assert alpha.image_count == 2
    assert alpha.file_hash is not None
    assert alpha.doc_hash == alpha.file_hash[:16]


def test_document_manager_get_document_detail_returns_chunks_and_images(manager_bundle: dict[str, object]) -> None:
    """
    Given:
        一份包含 2 个 chunk 且第二个 chunk 的 `images` 字段被 JSON 字符串化的文档。
    When:
        调用 `get_document_detail(doc_id)`。
    Then:
        - 返回的 detail 包含全部 chunk 和图片；
        - chunk 按 chunk_index 排序；
        - JSON 字符串化的 metadata 字段会被恢复为可读结构。
    """
    manager = manager_bundle["manager"]
    assert isinstance(manager, DocumentManager)
    source_a = _seed_document_a(manager_bundle)

    detail = manager.get_document_detail(source_a)

    assert isinstance(detail, DocumentDetail)
    assert detail.doc_id == source_a
    assert detail.chunk_count == 2
    assert detail.image_count == 2
    assert len(detail.chunks) == 2
    assert [chunk["chunk_id"] for chunk in detail.chunks] == ["chunk-a-1", "chunk-a-2"]
    assert isinstance(detail.chunks[1]["metadata"]["images"], list)
    assert len(detail.images) == 2


def test_document_manager_delete_document_coordinates_four_storages(manager_bundle: dict[str, object]) -> None:
    """
    Given:
        一份已经写入 Chroma/BM25/ImageStorage/FileIntegrity 四个后端的文档。
    When:
        调用 `delete_document(source_path, collection)`。
    Then:
        - 四个后端都应删除对应数据；
        - 返回的 DeleteResult 记录各自删除数量；
        - 删除后 `list_documents()` 不再包含该文档。
    """
    manager = manager_bundle["manager"]
    chroma_store = manager_bundle["chroma_store"]
    bm25_indexer = manager_bundle["bm25_indexer"]
    image_storage = manager_bundle["image_storage"]
    file_integrity = manager_bundle["file_integrity"]
    assert isinstance(manager, DocumentManager)
    assert isinstance(chroma_store, ChromaStore)
    assert isinstance(bm25_indexer, BM25Indexer)
    assert isinstance(image_storage, ImageStorage)
    assert isinstance(file_integrity, SQLiteIntegrityChecker)

    source_a = _seed_document_a(manager_bundle)
    _seed_document_b(manager_bundle)

    result = manager.delete_document(source_a, "manual")

    assert isinstance(result, DeleteResult)
    assert result.source_path == source_a
    assert result.collection == "manual"
    assert result.chunks_deleted == 2
    assert result.bm25_deleted == 2
    assert result.images_deleted == 2
    assert result.integrity_deleted == 1

    assert chroma_store.get_by_metadata({"source_path": source_a}) == []
    assert image_storage.list_images(collection="manual", doc_hash=result.doc_hash) == []
    assert all(row["file_path"] != source_a for row in file_integrity.list_processed())
    assert source_a not in bm25_indexer._doc_sources.values()
    assert all(item.source_path != source_a for item in manager.list_documents())


def test_document_manager_get_collection_stats_supports_total_and_single_collection(
    manager_bundle: dict[str, object],
) -> None:
    """
    Given:
        `manual` 与 `faq` 两个 collection 下分别存在文档。
    When:
        分别调用 `get_collection_stats()` 和 `get_collection_stats("manual")`。
    Then:
        - 总统计应包含两个 collection 的聚合结果；
        - 单 collection 统计应只返回指定集合的数据。
    """
    manager = manager_bundle["manager"]
    assert isinstance(manager, DocumentManager)
    _seed_document_a(manager_bundle)
    _seed_document_b(manager_bundle)

    total_stats = manager.get_collection_stats()
    manual_stats = manager.get_collection_stats("manual")

    assert isinstance(total_stats, CollectionStats)
    assert total_stats.document_count == 2
    assert total_stats.chunk_count == 3
    assert total_stats.image_count == 2
    assert [row["name"] for row in total_stats.collections] == ["faq", "manual"]

    assert isinstance(manual_stats, CollectionStats)
    assert manual_stats.collection == "manual"
    assert manual_stats.document_count == 1
    assert manual_stats.chunk_count == 2
    assert manual_stats.image_count == 2
    assert manual_stats.collections == []
