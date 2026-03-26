"""文件完整性检查（C2）。

职责：
- 计算文件 SHA256；
- 基于 `ingestion_history` 判定是否可跳过重复处理；
- 使用 SQLite 作为默认持久化实现，开启 WAL 支持并发读写。
"""

from __future__ import annotations

import hashlib
import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing
from pathlib import Path
from typing import Any


class FileIntegrityChecker(ABC):
    """文件完整性检查抽象接口。"""

    @abstractmethod
    def compute_sha256(self, path: str) -> str:
        """计算文件 SHA256。"""
        raise NotImplementedError

    @abstractmethod
    def should_skip(self, file_hash: str) -> bool:
        """当 file_hash 已成功处理过时返回 True。"""
        raise NotImplementedError

    @abstractmethod
    def mark_success(
        self,
        file_hash: str,
        file_path: str,
        file_size: int | None = None,
        chunk_count: int | None = None,
    ) -> None:
        """记录成功处理状态。"""
        raise NotImplementedError

    @abstractmethod
    def mark_failed(
        self,
        file_hash: str,
        error_msg: str,
        file_path: str = "",
        file_size: int | None = None,
    ) -> None:
        """记录失败处理状态。"""
        raise NotImplementedError


class SQLiteIntegrityChecker(FileIntegrityChecker):
    """基于 SQLite 的文件完整性检查实现。"""

    def __init__(self, db_path: str = "data/db/ingestion_history.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        # 使用 closing 显式关闭连接，避免 Windows 下句柄滞留。
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ingestion_history (
                        file_hash TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        file_size INTEGER,
                        status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'processing')),
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        error_msg TEXT,
                        chunk_count INTEGER
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_status ON ingestion_history(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_processed_at ON ingestion_history(processed_at)"
                )

    def compute_sha256(self, path: str) -> str:
        """计算文件 SHA256，采用流式读取避免大文件内存峰值。"""
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def should_skip(self, file_hash: str) -> bool:
        """若该文件 hash 已有 success 记录，则可直接跳过。"""
        if not isinstance(file_hash, str) or not file_hash.strip():
            raise ValueError("file_hash must be non-empty string")

        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT status FROM ingestion_history WHERE file_hash = ? AND status = 'success'",
                (file_hash,),
            ).fetchone()
        return row is not None

    def mark_success(
        self,
        file_hash: str,
        file_path: str,
        file_size: int | None = None,
        chunk_count: int | None = None,
    ) -> None:
        """写入 success 记录，采用 UPSERT 保证幂等。"""
        if not isinstance(file_hash, str) or not file_hash.strip():
            raise ValueError("file_hash must be non-empty string")
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("file_path must be non-empty string")

        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO ingestion_history(file_hash, file_path, file_size, status, error_msg, chunk_count)
                    VALUES(?, ?, ?, 'success', NULL, ?)
                    ON CONFLICT(file_hash) DO UPDATE SET
                        file_path = excluded.file_path,
                        file_size = excluded.file_size,
                        status = 'success',
                        error_msg = NULL,
                        chunk_count = excluded.chunk_count,
                        processed_at = CURRENT_TIMESTAMP
                    """,
                    (file_hash, file_path, file_size, chunk_count),
                )

    def mark_failed(
        self,
        file_hash: str,
        error_msg: str,
        file_path: str = "",
        file_size: int | None = None,
    ) -> None:
        """写入 failed 记录，便于排障与重试策略判断。"""
        if not isinstance(file_hash, str) or not file_hash.strip():
            raise ValueError("file_hash must be non-empty string")
        if not isinstance(error_msg, str) or not error_msg.strip():
            raise ValueError("error_msg must be non-empty string")

        safe_path = file_path if isinstance(file_path, str) and file_path.strip() else "<unknown>"

        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO ingestion_history(file_hash, file_path, file_size, status, error_msg, chunk_count)
                    VALUES(?, ?, ?, 'failed', ?, NULL)
                    ON CONFLICT(file_hash) DO UPDATE SET
                        file_path = excluded.file_path,
                        file_size = excluded.file_size,
                        status = 'failed',
                        error_msg = excluded.error_msg,
                        chunk_count = NULL,
                        processed_at = CURRENT_TIMESTAMP
                    """,
                    (file_hash, safe_path, file_size, error_msg),
                )

    def list_processed(self) -> list[dict[str, Any]]:
        """返回已记录条目（辅助调试与后续文档管理能力）。"""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT file_hash, file_path, file_size, status, processed_at, error_msg, chunk_count "
                "FROM ingestion_history ORDER BY processed_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def remove_record(self, file_hash: str) -> None:
        """按 file_hash 删除记录（供后续生命周期管理使用）。"""
        if not isinstance(file_hash, str) or not file_hash.strip():
            raise ValueError("file_hash must be non-empty string")
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("DELETE FROM ingestion_history WHERE file_hash = ?", (file_hash,))
