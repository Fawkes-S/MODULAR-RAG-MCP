"""文件完整性检查（C2）单元测试。"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.loader.file_integrity import SQLiteIntegrityChecker


def _new_db_path() -> Path:
    base = PROJECT_ROOT / "data" / "db"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"test_ingestion_history_{uuid.uuid4().hex}.db"


def _cleanup_db(path: Path) -> None:
    # Windows + SQLite(WAL) 场景下文件句柄释放可能有短暂延迟，采用重试并在最终失败时忽略。
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(path) + suffix)
        if not p.exists():
            continue
        for _ in range(5):
            try:
                p.unlink()
                break
            except PermissionError:
                time.sleep(0.05)
            except FileNotFoundError:
                break


def test_compute_sha256_is_stable_for_same_file() -> None:
    """
    Given:
        一个固定内容的文件与 `SQLiteIntegrityChecker` 实例。

    When:
        对同一文件重复调用 `compute_sha256` 两次。

    Then:
        两次结果应一致，且与标准 `hashlib.sha256` 计算值相同。
    """
    db_path = _new_db_path()
    test_file = PROJECT_ROOT / "data" / "db" / f"sha_stable_{uuid.uuid4().hex}.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("hello integrity", encoding="utf-8")

    checker = SQLiteIntegrityChecker(db_path=str(db_path))

    try:
        h1 = checker.compute_sha256(str(test_file))
        h2 = checker.compute_sha256(str(test_file))
        expected = hashlib.sha256(test_file.read_bytes()).hexdigest()

        assert h1 == h2
        assert h1 == expected
    finally:
        if test_file.exists():
            test_file.unlink()
        _cleanup_db(db_path)


def test_mark_success_then_should_skip_returns_true() -> None:
    """
    Given:
        一个新的 SQLiteIntegrityChecker 与未记录的 file_hash。

    When:
        先调用 `mark_success`，再调用 `should_skip`。

    Then:
        `should_skip` 应返回 True，说明增量跳过判定链路可用。
    """
    db_path = _new_db_path()
    checker = SQLiteIntegrityChecker(db_path=str(db_path))

    try:
        file_hash = "abc123"
        assert checker.should_skip(file_hash) is False

        checker.mark_success(file_hash=file_hash, file_path="docs/a.pdf", file_size=10, chunk_count=2)

        assert checker.should_skip(file_hash) is True
    finally:
        _cleanup_db(db_path)


def test_default_db_path_is_created_under_data_db() -> None:
    """
    Given:
        默认构造 `SQLiteIntegrityChecker()`。

    When:
        初始化对象并触发数据库建表。

    Then:
        数据库文件应创建在 `data/db/ingestion_history.db`。
    """
    checker = SQLiteIntegrityChecker()
    assert checker.db_path == Path("data/db/ingestion_history.db")
    assert checker.db_path.exists()


def test_sqlite_journal_mode_is_wal() -> None:
    """
    Given:
        一个独立测试数据库。

    When:
        读取 SQLite `PRAGMA journal_mode`。

    Then:
        应为 `wal`，满足并发读写配置要求。
    """
    db_path = _new_db_path()
    checker = SQLiteIntegrityChecker(db_path=str(db_path))

    try:
        with sqlite3.connect(str(checker.db_path)) as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert str(mode).lower() == "wal"
    finally:
        _cleanup_db(db_path)


def test_concurrent_mark_success_writes_are_supported() -> None:
    """
    Given:
        一个开启 WAL 的 SQLiteIntegrityChecker 与多组 file_hash。

    When:
        通过线程池并发执行 `mark_success` 写入。

    Then:
        所有写入均成功，且每个 file_hash 的 `should_skip` 都返回 True。
    """
    db_path = _new_db_path()
    checker = SQLiteIntegrityChecker(db_path=str(db_path))

    hashes = [f"h_{i}" for i in range(12)]

    try:
        def _worker(h: str) -> None:
            checker.mark_success(file_hash=h, file_path=f"docs/{h}.pdf", file_size=1, chunk_count=1)

        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(_worker, hashes))

        assert all(checker.should_skip(h) for h in hashes)
    finally:
        _cleanup_db(db_path)
