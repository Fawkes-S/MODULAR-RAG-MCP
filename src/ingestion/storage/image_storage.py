"""ImageStorage：图片文件存储与 SQLite 索引映射（C13）。"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class ImageStorage:
    """管理图片二进制落盘与 `image_id -> file_path` 映射。

    做什么：
    - 将图片二进制保存到本地目录：`data/images/{collection}/{doc_hash}/{image_id}.{ext}`。
    - 在 SQLite 中维护索引表 `image_index`，记录 `image_id/file_path/collection/doc_hash/page_num`。
    - 提供查询、列表与删除能力，供后续 Dashboard 浏览与文档删除流程复用。

    为什么：
    - C13 需要把“图片文件”和“可查询映射关系”统一落地，后续检索命中 `image_refs` 后才能快速定位本地文件。

    关键权衡：
    - 文件系统保存原始图片，SQLite 保存轻量索引：
      - 文件系统擅长二进制存储；
      - SQLite 擅长主键查询与过滤。
    - 数据库写入使用 UPSERT 语义，保证相同 `image_id` 重复写入不会产生脏重复行。

    失败路径：
    - 关键入参非法（空 image_id / 空 bytes / 非法 collection）时抛 `ValueError`。
    - 文件写入失败或 SQLite 异常时透传异常，交由上层决定重试与降级策略。

    Args:
        image_root: 图片存储根目录。
        db_path: 索引数据库文件路径。
    """

    _SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

    def __init__(self, image_root: str = "data/images", db_path: str = "data/db/image_index.db") -> None:
        self.image_root = Path(image_root)
        self.db_path = Path(db_path)

        self.image_root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用 WAL，保证并发读写场景稳定。"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """初始化索引表与查询索引。"""
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS image_index (
                        image_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        collection TEXT,
                        doc_hash TEXT,
                        page_num INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_collection ON image_index(collection)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_hash ON image_index(doc_hash)")

    def save_image(
        self,
        *,
        image_id: str,
        image_bytes: bytes,
        collection: str = "default",
        doc_hash: str | None = None,
        page_num: int | None = None,
        extension: str = "png",
    ) -> str:
        """保存图片并写入索引，返回落盘路径。

        Given 一个图片二进制输入，方法会先落盘，再 upsert 索引。
        若同一 `image_id` 再次保存，索引行会被覆盖到最新路径。
        """
        normalized_image_id = self._require_non_empty_string(image_id, "image_id")
        if not isinstance(image_bytes, (bytes, bytearray)) or len(image_bytes) == 0:
            raise ValueError("image_bytes must be non-empty bytes")

        normalized_collection = self._normalize_segment(collection, "collection")
        normalized_doc_hash = self._normalize_segment(
            doc_hash or self._infer_doc_hash(normalized_image_id),
            "doc_hash",
        )
        normalized_ext = self._normalize_extension(extension)

        out_dir = self.image_root / normalized_collection / normalized_doc_hash
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{normalized_image_id}.{normalized_ext}"
        out_path.write_bytes(bytes(image_bytes))

        self._upsert_index(
            image_id=normalized_image_id,
            file_path=out_path.as_posix(),
            collection=normalized_collection,
            doc_hash=normalized_doc_hash,
            page_num=page_num,
        )
        return out_path.as_posix()

    def get_path(self, image_id: str) -> str | None:
        """按 image_id 查询文件路径，不存在时返回 `None`。"""
        normalized_image_id = self._require_non_empty_string(image_id, "image_id")

        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT file_path FROM image_index WHERE image_id = ?",
                (normalized_image_id,),
            ).fetchone()

        if row is None:
            return None
        return str(row["file_path"])

    def get_record(self, image_id: str) -> dict[str, Any] | None:
        """按 image_id 查询完整索引记录。"""
        normalized_image_id = self._require_non_empty_string(image_id, "image_id")

        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT image_id, file_path, collection, doc_hash, page_num, created_at
                FROM image_index
                WHERE image_id = ?
                """,
                (normalized_image_id,),
            ).fetchone()

        return dict(row) if row is not None else None

    def list_images(self, collection: str | None = None, doc_hash: str | None = None) -> list[dict[str, Any]]:
        """按 collection/doc_hash 过滤返回图片索引列表。"""
        clauses: list[str] = []
        params: list[str] = []

        if collection is not None:
            clauses.append("collection = ?")
            params.append(self._normalize_segment(collection, "collection"))
        if doc_hash is not None:
            clauses.append("doc_hash = ?")
            params.append(self._normalize_segment(doc_hash, "doc_hash"))

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        sql = (
            "SELECT image_id, file_path, collection, doc_hash, page_num, created_at "
            f"FROM image_index {where_sql} ORDER BY image_id ASC"
        )

        with closing(self._connect()) as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        return [dict(row) for row in rows]

    def delete_images(self, collection: str, doc_hash: str | None = None) -> int:
        """删除 collection（可选 doc_hash）下的图片索引与本地文件。"""
        normalized_collection = self._normalize_segment(collection, "collection")

        clauses = ["collection = ?"]
        params: list[str] = [normalized_collection]
        if doc_hash is not None:
            clauses.append("doc_hash = ?")
            params.append(self._normalize_segment(doc_hash, "doc_hash"))

        where_sql = " AND ".join(clauses)

        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"SELECT image_id, file_path FROM image_index WHERE {where_sql}",
                tuple(params),
            ).fetchall()

        if not rows:
            return 0

        removed = 0
        for row in rows:
            file_path = Path(str(row["file_path"]))
            if file_path.exists():
                file_path.unlink()
            removed += 1

        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    f"DELETE FROM image_index WHERE {where_sql}",
                    tuple(params),
                )

        return removed

    def _upsert_index(
        self,
        *,
        image_id: str,
        file_path: str,
        collection: str,
        doc_hash: str,
        page_num: int | None,
    ) -> None:
        """写入/更新 SQLite 索引行。"""
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO image_index(image_id, file_path, collection, doc_hash, page_num)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(image_id) DO UPDATE SET
                        file_path = excluded.file_path,
                        collection = excluded.collection,
                        doc_hash = excluded.doc_hash,
                        page_num = excluded.page_num,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (image_id, file_path, collection, doc_hash, page_num),
                )

    @classmethod
    def _normalize_segment(cls, value: str, field_name: str) -> str:
        """校验目录段，仅允许安全字符，防止路径注入。"""
        text = cls._require_non_empty_string(value, field_name)
        if not cls._SAFE_SEGMENT_PATTERN.match(text):
            raise ValueError(f"{field_name} contains unsafe characters: {value!r}")
        return text

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        """标准化后缀名，去掉前导 `.`，限制为字母数字。"""
        text = ImageStorage._require_non_empty_string(extension, "extension").lower().lstrip(".")
        if not re.match(r"^[a-z0-9]+$", text):
            raise ValueError(f"extension must be alphanumeric: {extension!r}")
        return text

    @staticmethod
    def _infer_doc_hash(image_id: str) -> str:
        """从 image_id 推断 doc_hash（约定取首个 `_` 前缀）。"""
        head = image_id.split("_", 1)[0].strip()
        if not head:
            raise ValueError(f"Cannot infer doc_hash from image_id: {image_id!r}")
        return head

    @staticmethod
    def _require_non_empty_string(value: str, field_name: str) -> str:
        """确保字符串字段非空。"""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be non-empty string")
        return value.strip()
