"""ImageStorage 单元测试（C13）。"""

from __future__ import annotations

import sqlite3
import shutil
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ingestion.storage.image_storage import ImageStorage


@pytest.fixture()
def storage_workspace() -> Path:
    """在项目目录内创建独立临时目录，避免污染默认 data 目录。"""
    root = PROJECT_ROOT / ".pytest_tmp" / f"image_storage_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _new_storage(workspace: Path) -> ImageStorage:
    image_root = workspace / "images"
    db_path = workspace / "db" / "image_index.db"
    return ImageStorage(image_root=str(image_root), db_path=str(db_path))


def test_image_storage_save_then_lookup_path_and_file_exists(storage_workspace: Path) -> None:
    """
    Given:
        一个空的 ImageStorage 实例与一段图片二进制内容。
    When:
        调用 `save_image()` 保存图片，再用 `get_path()` 按 image_id 查询路径。
    Then:
        返回路径应与查询路径一致，且该文件在磁盘上真实存在。
    """
    storage = _new_storage(storage_workspace)

    stored_path = storage.save_image(
        image_id="doca_1_0001",
        image_bytes=b"\\x89PNGfake",
        collection="demo",
        doc_hash="doca",
        page_num=1,
        extension="png",
    )

    resolved_path = storage.get_path("doca_1_0001")

    assert resolved_path == stored_path
    assert Path(stored_path).exists()


def test_image_storage_mapping_is_persistent_after_reopen(storage_workspace: Path) -> None:
    """
    Given:
        首次实例已保存一条图片索引记录。
    When:
        重新创建一个新的 ImageStorage 实例并查询同一 image_id。
    Then:
        新实例仍能查到同一路径，证明映射关系已持久化到 SQLite。
    """
    first = _new_storage(storage_workspace)
    first_path = first.save_image(
        image_id="docb_2_0001",
        image_bytes=b"first",
        collection="demo",
        doc_hash="docb",
        page_num=2,
        extension="jpg",
    )

    second = _new_storage(storage_workspace)
    second_path = second.get_path("docb_2_0001")

    assert second_path == first_path
    assert (storage_workspace / "db" / "image_index.db").exists()


def test_image_storage_list_images_supports_collection_and_doc_hash_filter(storage_workspace: Path) -> None:
    """
    Given:
        三条索引记录，分别位于不同 collection/doc_hash 组合。
    When:
        分别调用 `list_images(collection=...)` 与 `list_images(collection=..., doc_hash=...)`。
    Then:
        返回结果应只包含过滤条件命中的记录。
    """
    storage = _new_storage(storage_workspace)
    storage.save_image(image_id="docx_1_0001", image_bytes=b"a", collection="c1", doc_hash="docx")
    storage.save_image(image_id="docy_1_0001", image_bytes=b"b", collection="c1", doc_hash="docy")
    storage.save_image(image_id="docz_1_0001", image_bytes=b"c", collection="c2", doc_hash="docz")

    c1_images = storage.list_images(collection="c1")
    c1_docx_images = storage.list_images(collection="c1", doc_hash="docx")

    assert [item["image_id"] for item in c1_images] == ["docx_1_0001", "docy_1_0001"]
    assert [item["image_id"] for item in c1_docx_images] == ["docx_1_0001"]


def test_image_storage_delete_images_removes_files_and_index_rows(storage_workspace: Path) -> None:
    """
    Given:
        同一 collection/doc_hash 下已有两张图片及索引记录。
    When:
        调用 `delete_images(collection, doc_hash)` 批量删除。
    Then:
        应返回删除数量，文件被删除，且查询列表为空。
    """
    storage = _new_storage(storage_workspace)
    p1 = storage.save_image(image_id="dock_1_0001", image_bytes=b"1", collection="demo", doc_hash="dock")
    p2 = storage.save_image(image_id="dock_1_0002", image_bytes=b"2", collection="demo", doc_hash="dock")

    removed = storage.delete_images(collection="demo", doc_hash="dock")

    assert removed == 2
    assert not Path(p1).exists()
    assert not Path(p2).exists()
    assert storage.list_images(collection="demo", doc_hash="dock") == []


def test_image_storage_uses_sqlite_wal_mode(storage_workspace: Path) -> None:
    """
    Given:
        一个新建的 ImageStorage（内部 SQLite 已初始化）。
    When:
        读取数据库 `PRAGMA journal_mode`。
    Then:
        应为 `wal`，满足 C13 并发安全要求。
    """
    storage = _new_storage(storage_workspace)

    with sqlite3.connect(str(storage.db_path)) as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]

    assert str(mode).lower() == "wal"


def test_image_storage_rejects_unsafe_collection_value(storage_workspace: Path) -> None:
    """
    Given:
        一个包含路径跳转字符的非法 collection 值。
    When:
        调用 `save_image()`。
    Then:
        应抛出 ValueError，阻止路径注入到文件系统层。
    """
    storage = _new_storage(storage_workspace)

    with pytest.raises(ValueError, match="unsafe characters"):
        storage.save_image(
            image_id="docp_1_0001",
            image_bytes=b"x",
            collection="../escape",
            doc_hash="docp",
        )
