"""ChromaStore 回环集成测试。"""

from __future__ import annotations

import os
import shutil
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.vector_store.chroma_store import ChromaStore
from libs.vector_store.vector_store_factory import VectorStoreFactory


def _isolated_workdir() -> Path:
    """在项目目录下创建可写隔离工作目录，避免污染真实数据目录。"""
    workdir = PROJECT_ROOT / f"pytest-cache-files-chroma-{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def _stable_persist_dir(base_dir: Path) -> str:
    """在隔离工作目录内返回稳定持久化目录（固定为 data/db/chroma）。"""
    path = base_dir / "data" / "db" / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _new_collection(prefix: str) -> str:
    """为每次测试生成唯一 collection，避免互相污染。"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def test_chroma_store_roundtrip_upsert_query_with_filters() -> None:
    """
    Given:
        隔离工作目录下的稳定持久化目录（data/db/chroma）与 3 条 mock 向量记录（包含 metadata/text）。

    When:
        执行 upsert 后，用 query(vector, top_k, filters) 检索。

    Then:
        - 能完成完整 upsert→query 回环；
        - `top_k` 生效；
        - metadata filter 生效；
        - 返回项包含 id/score/metadata/text 且结果稳定可断言。
    """
    workdir = _isolated_workdir()
    persist_dir = _stable_persist_dir(workdir)
    collection_name = _new_collection("test_chunks")

    store = ChromaStore(persist_dir=persist_dir, collection_name=collection_name)
    try:
        records = [
            {
                "id": "c1",
                "vector": [1.0, 0.0, 0.0],
                "metadata": {"doc_id": "d1", "lang": "zh"},
                "text": "文档一",
            },
            {
                "id": "c2",
                "vector": [0.9, 0.1, 0.0],
                "metadata": {"doc_id": "d2", "lang": "zh"},
                "text": "文档二",
            },
            {
                "id": "c3",
                "vector": [0.0, 1.0, 0.0],
                "metadata": {"doc_id": "d3", "lang": "en"},
                "text": "doc three",
            },
        ]

        store.upsert(records)

        result_top2 = store.query(vector=[1.0, 0.0, 0.0], top_k=2, filters=None)
        assert len(result_top2) == 2
        assert set(result_top2[0].keys()) >= {"id", "score", "metadata", "text"}

        result_zh = store.query(vector=[1.0, 0.0, 0.0], top_k=5, filters={"lang": "zh"})
        assert len(result_zh) == 2
        assert all(item["metadata"].get("lang") == "zh" for item in result_zh)
    finally:
        store._client.delete_collection(collection_name)
        shutil.rmtree(workdir, ignore_errors=True)


def test_vector_store_factory_can_create_chroma() -> None:
    """
    Given:
        provider=chroma 配置，未显式设置 persist_dir（使用默认稳定目录 data/db/chroma）。

    When:
        调用 VectorStoreFactory.create。

    Then:
        返回 ChromaStore 实例，且默认持久化目录配置生效。
    """
    workdir = _isolated_workdir()
    _stable_persist_dir(workdir)
    collection_name = _new_collection("factory_collection")
    settings = {
        "vector_store": {
            "provider": "chroma",
            "collection_name": collection_name,
        }
    }

    old_cwd = Path.cwd()
    try:
        os.chdir(workdir)
        store = VectorStoreFactory.create(settings)
        assert isinstance(store, ChromaStore)
        assert store.persist_dir == "data/db/chroma"
        assert store.collection_name == collection_name
    finally:
        os.chdir(old_cwd)
        if "store" in locals():
            store._client.delete_collection(collection_name)
        shutil.rmtree(workdir, ignore_errors=True)


def test_chroma_store_get_by_ids_returns_records_in_requested_order() -> None:
    """
    Given:
        ChromaStore 中已写入两条记录，包含 text 与 metadata。
    When:
        调用 `get_by_ids(["c2", "c1"])` 按指定顺序批量读取。
    Then:
        返回结果应包含 `id/text/metadata`，且顺序与请求 ID 顺序一致。
    """
    workdir = _isolated_workdir()
    persist_dir = _stable_persist_dir(workdir)
    collection_name = _new_collection("test_get_by_ids")

    store = ChromaStore(persist_dir=persist_dir, collection_name=collection_name)
    try:
        store.upsert(
            [
                {
                    "id": "c1",
                    "vector": [1.0, 0.0],
                    "metadata": {"source_path": "docs/a.pdf"},
                    "text": "doc one",
                },
                {
                    "id": "c2",
                    "vector": [0.0, 1.0],
                    "metadata": {"source_path": "docs/b.pdf"},
                    "text": "doc two",
                },
            ]
        )

        rows = store.get_by_ids(["c2", "c1"])

        assert [row["id"] for row in rows] == ["c2", "c1"]
        assert rows[0]["text"] == "doc two"
        assert rows[1]["metadata"]["source_path"] == "docs/a.pdf"
    finally:
        store._client.delete_collection(collection_name)
        shutil.rmtree(workdir, ignore_errors=True)


def test_chroma_store_get_collection_stats_summarizes_chunks_documents_and_images() -> None:
    """
    Given:
        ChromaStore 中写入 3 条 chunk，分别属于两个业务 collection，
        并带有 source_path、image_refs/images 等统计字段。

    When:
        调用 `get_collection_stats()` 读取当前向量库概览统计。

    Then:
        - 返回总 chunk/document/image 数；
        - 能按业务 collection 维度拆出子统计；
        - 统计结果可直接供 Dashboard Overview 页面展示。
    """
    workdir = _isolated_workdir()
    persist_dir = _stable_persist_dir(workdir)
    collection_name = _new_collection("test_stats")

    store = ChromaStore(persist_dir=persist_dir, collection_name=collection_name)
    try:
        store.upsert(
            [
                {
                    "id": "c1",
                    "vector": [1.0, 0.0],
                    "metadata": {
                        "collection": "manual",
                        "source_path": "docs/a.pdf",
                        "image_refs": ["img-1"],
                    },
                    "text": "doc a / chunk 1",
                },
                {
                    "id": "c2",
                    "vector": [0.9, 0.1],
                    "metadata": {
                        "collection": "manual",
                        "source_path": "docs/a.pdf",
                        "images": ["img-2"],
                    },
                    "text": "doc a / chunk 2",
                },
                {
                    "id": "c3",
                    "vector": [0.0, 1.0],
                    "metadata": {
                        "collection": "faq",
                        "source_path": "docs/b.pdf",
                    },
                    "text": "doc b / chunk 1",
                },
            ]
        )

        stats = store.get_collection_stats()

        assert stats["chunk_count"] == 3
        assert stats["document_count"] == 2
        assert stats["image_count"] == 2
        assert [row["name"] for row in stats["collections"]] == ["faq", "manual"]
        assert stats["collections"][1]["chunk_count"] == 2
        assert stats["collections"][1]["document_count"] == 1
        assert stats["collections"][1]["image_count"] == 2
    finally:
        store._client.delete_collection(collection_name)
        shutil.rmtree(workdir, ignore_errors=True)


def test_chroma_store_get_by_metadata_and_delete_by_metadata_roundtrip() -> None:
    """
    Given:
        ChromaStore 中存在两份不同 `source_path/collection` 的 chunk 记录。
    When:
        先调用 `get_by_metadata()` 读取其中一份文档，再调用 `delete_by_metadata()` 删除它。
    Then:
        - 读取结果应只包含命中文档的 chunk；
        - 删除返回值应等于命中数量；
        - 删除后再次按相同 metadata 读取应为空列表。
    """
    workdir = _isolated_workdir()
    persist_dir = _stable_persist_dir(workdir)
    collection_name = _new_collection("test_metadata_ops")

    store = ChromaStore(persist_dir=persist_dir, collection_name=collection_name)
    try:
        store.upsert(
            [
                {
                    "id": "c1",
                    "vector": [1.0, 0.0],
                    "metadata": {
                        "source_path": "docs/a.pdf",
                        "collection": "manual",
                        "chunk_index": 1,
                    },
                    "text": "doc a / chunk 2",
                },
                {
                    "id": "c2",
                    "vector": [0.9, 0.1],
                    "metadata": {
                        "source_path": "docs/a.pdf",
                        "collection": "manual",
                        "chunk_index": 0,
                    },
                    "text": "doc a / chunk 1",
                },
                {
                    "id": "c3",
                    "vector": [0.0, 1.0],
                    "metadata": {
                        "source_path": "docs/b.pdf",
                        "collection": "faq",
                        "chunk_index": 0,
                    },
                    "text": "doc b / chunk 1",
                },
            ]
        )

        rows = store.get_by_metadata({"source_path": "docs/a.pdf", "collection": "manual"})
        removed = store.delete_by_metadata({"source_path": "docs/a.pdf", "collection": "manual"})
        after_rows = store.get_by_metadata({"source_path": "docs/a.pdf", "collection": "manual"})

        assert [row["id"] for row in rows] == ["c2", "c1"]
        assert removed == 2
        assert after_rows == []
        assert [row["id"] for row in store.get_by_metadata()] == ["c3"]
    finally:
        store._client.delete_collection(collection_name)
        shutil.rmtree(workdir, ignore_errors=True)
