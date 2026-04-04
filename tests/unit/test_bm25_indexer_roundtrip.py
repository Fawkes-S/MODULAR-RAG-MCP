"""BM25Indexer roundtrip 单元测试（C11）。"""

from __future__ import annotations

import math
import shutil
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.types import ChunkRecord  # noqa: E402
from ingestion.storage.bm25_indexer import BM25Indexer  # noqa: E402


@pytest.fixture
def workspace_tmp_dir() -> Path:
    """在项目工作区创建临时目录，避免系统 TEMP 目录权限限制。"""
    base = PROJECT_ROOT / ".pytest_tmp"
    base.mkdir(parents=True, exist_ok=True)

    temp_dir = base / f"bm25_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _make_record(chunk_id: str, source_path: str, sparse_vector: dict[str, float]) -> ChunkRecord:
    return ChunkRecord(
        id=chunk_id,
        text=f"content::{chunk_id}",
        metadata={"source_path": source_path, "doc_type": "md"},
        dense_vector=None,
        sparse_vector=sparse_vector,
    )


def _sample_records() -> list[ChunkRecord]:
    return [
        _make_record("c1", "memory://doc-a.md", {"azure": 2.0, "openai": 1.0}),
        _make_record("c2", "memory://doc-b.md", {"azure": 1.0, "api": 1.0}),
        _make_record("c3", "memory://doc-c.md", {"bm25": 2.0, "retrieval": 1.0}),
    ]


def test_bm25_indexer_build_load_and_query_roundtrip_is_stable(workspace_tmp_dir: Path) -> None:
    """
    Given:
        一组固定语料（3 条 sparse records）与临时索引目录。
    When:
        先 build+save，再新建 indexer 执行 load，并查询相同关键词。
    Then:
        两次查询返回的 top ids 顺序应稳定一致，满足 C11 roundtrip 验收要求。
    """
    index_dir = workspace_tmp_dir / "bm25"
    records = _sample_records()

    indexer = BM25Indexer(persist_dir=str(index_dir))
    indexer.build(records)
    first_query = indexer.query("azure openai", top_k=3)
    print(f"first_query:\n{first_query}")
    loaded = BM25Indexer(persist_dir=str(index_dir))
    loaded.load()
    second_query = loaded.query("azure openai", top_k=3)
    print(f"\nsecond_query:\n{second_query}")

    assert [chunk_id for chunk_id, _ in first_query] == [chunk_id for chunk_id, _ in second_query]
    assert [chunk_id for chunk_id, _ in first_query][:2] == ["c1", "c2"]


def test_bm25_indexer_idf_matches_spec_formula(workspace_tmp_dir: Path) -> None:
    """
    Given:
        N=3 的语料，其中 term=azure 出现在 2 条文档中。
    When:
        build 后读取 `get_idf("azure")`。
    Then:
        应满足规格公式：`log((N - df + 0.5) / (df + 0.5))`。
    """
    indexer = BM25Indexer(persist_dir=str(workspace_tmp_dir / "bm25"))
    indexer.build(_sample_records(), rebuild=True)

    actual = indexer.get_idf("azure")
    expected = math.log((3 - 2 + 0.5) / (2 + 0.5))

    assert actual is not None
    assert actual == pytest.approx(expected)


def test_bm25_indexer_supports_incremental_update(workspace_tmp_dir: Path) -> None:
    """
    Given:
        初始索引仅包含 c1/c2，不包含 term=newterm。
    When:
        以 rebuild=False 增量 build 一条带 newterm 的新记录。
    Then:
        查询 newterm 应命中新记录，且旧记录仍可查询。
    """
    index_dir = workspace_tmp_dir / "bm25"
    base_records = _sample_records()[:2]
    new_record = _make_record("c3", "memory://doc-c.md", {"newterm": 3.0})

    indexer = BM25Indexer(persist_dir=str(index_dir))
    indexer.build(base_records, rebuild=True)
    assert indexer.query("newterm") == []

    indexer.build([new_record], rebuild=False)

    query_new = indexer.query("newterm", top_k=3)
    query_old = indexer.query("azure", top_k=3)

    assert query_new and query_new[0][0] == "c3"
    assert query_old and query_old[0][0] in {"c1", "c2"}


def test_bm25_indexer_supports_rebuild_mode(workspace_tmp_dir: Path) -> None:
    """
    Given:
        先 build 一份旧语料，再使用 rebuild=True 写入全新语料。
    When:
        对旧词与新词分别执行查询。
    Then:
        旧词结果应清空，新词结果应仅来自新语料。
    """
    index_dir = workspace_tmp_dir / "bm25"

    indexer = BM25Indexer(persist_dir=str(index_dir))
    indexer.build(_sample_records()[:2], rebuild=True)
    assert indexer.query("azure")

    only_new = [_make_record("n1", "memory://new.md", {"fresh": 2.0})]
    indexer.build(only_new, rebuild=True)

    assert indexer.query("azure") == []
    new_result = indexer.query("fresh", top_k=3)
    assert new_result and new_result[0][0] == "n1"


def test_bm25_indexer_remove_document_by_source(workspace_tmp_dir: Path) -> None:
    """
    Given:
        两条记录分别来自不同 source_path。
    When:
        调用 `remove_document(source)` 删除其中一个 source。
    Then:
        该 source 对应 chunk 应从索引中移除，其他 source 保持可查询。
    """
    index_dir = workspace_tmp_dir / "bm25"
    records = _sample_records()[:2]

    indexer = BM25Indexer(persist_dir=str(index_dir))
    indexer.build(records, rebuild=True)

    removed = indexer.remove_document("memory://doc-a.md")
    remained_query = indexer.query("azure", top_k=5)

    assert removed == 1
    assert all(chunk_id != "c1" for chunk_id, _ in remained_query)
    assert any(chunk_id == "c2" for chunk_id, _ in remained_query)


def test_bm25_indexer_rejects_invalid_build_input(workspace_tmp_dir: Path) -> None:
    """
    Given:
        非 `list[ChunkRecord]` 的非法输入。
    When:
        调用 `build()`。
    Then:
        应抛出 ValueError，保证索引构建入口的契约稳定。
    """
    indexer = BM25Indexer(persist_dir=str(workspace_tmp_dir / "bm25"))

    with pytest.raises(ValueError, match="records must be list"):
        indexer.build("not-a-list")  # type: ignore[arg-type]


def test_bm25_indexer_load_missing_file_returns_empty_index(workspace_tmp_dir: Path) -> None:
    """
    Given:
        索引目录存在但尚未生成索引文件。
    When:
        直接调用 `load()` 并执行查询。
    Then:
        应保持空索引状态并返回空查询结果，不应抛异常。
    """
    indexer = BM25Indexer(persist_dir=str(workspace_tmp_dir / "bm25"))
    indexer.load()

    assert indexer.query("anything") == []
