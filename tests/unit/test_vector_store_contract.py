"""BaseVectorStore 契约测试与工厂分流测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.vector_store.base_vector_store import BaseVectorStore
from libs.vector_store.vector_store_factory import VectorStoreFactory


class _FakeVectorStore(BaseVectorStore):
    """用于验证契约 shape 的内存版测试桩。"""

    def __init__(self, persist_dir: str = "") -> None:
        self.persist_dir = persist_dir
        self._records: dict[str, dict[str, Any]] = {}

    def upsert(self, records: list[dict[str, Any]], trace: Any | None = None) -> None:
        """按契约写入记录，并校验输入字段。"""
        for record in records:
            if "id" not in record or "vector" not in record or "metadata" not in record:
                raise ValueError("record must contain id, vector, metadata")
            if not isinstance(record["id"], str) or not record["id"].strip():
                raise ValueError("record.id must be non-empty string")
            if not isinstance(record["vector"], list):
                raise ValueError("record.vector must be list[float]")
            self._records[record["id"]] = {
                "id": record["id"],
                "vector": record["vector"],
                "metadata": record["metadata"],
            }

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """返回符合契约 shape 的检索结果。"""
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        items = list(self._records.values())
        if filters:
            items = [
                item
                for item in items
                if all(item["metadata"].get(key) == value for key, value in filters.items())
            ]

        scored: list[dict[str, Any]] = []
        for item in items:
            item_vector = item["vector"]
            same = sum(1 for i, value in enumerate(vector) if i < len(item_vector) and item_vector[i] == value)
            score = same / max(len(vector), 1)
            scored.append({"id": item["id"], "score": float(score), "metadata": item["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂全局注册表，避免测试互相污染。"""
    snapshot = dict(VectorStoreFactory._registry)
    VectorStoreFactory._registry.clear()
    try:
        yield snapshot
    finally:
        VectorStoreFactory._registry.clear()
        VectorStoreFactory._registry.update(snapshot)


def test_factory_routes_provider_and_passes_persist_dir(isolated_registry: dict[str, object]) -> None:
    """验证工厂会路由到已注册 provider，并把 persist_dir 正确传递给实例。"""
    VectorStoreFactory.register("fake", lambda persist_dir="": _FakeVectorStore(persist_dir=persist_dir))

    store = VectorStoreFactory.create(
        {"vector_store": {"provider": "fake", "persist_dir": "data/db/fake"}}
    )

    assert isinstance(store, _FakeVectorStore)
    assert store.persist_dir == "data/db/fake"


def test_contract_upsert_and_query_shape(isolated_registry: dict[str, object]) -> None:
    """验证 upsert/query 主链路的输入输出 shape 满足契约约定。"""
    VectorStoreFactory.register("fake", lambda persist_dir="": _FakeVectorStore(persist_dir=persist_dir))
    store = VectorStoreFactory.create({"vector_store": {"provider": "fake"}})

    records = [
        {"id": "c1", "vector": [0.1, 0.2, 0.3], "metadata": {"doc_id": "d1", "lang": "zh"}},
        {"id": "c2", "vector": [0.1, 0.2, 0.8], "metadata": {"doc_id": "d2", "lang": "en"}},
    ]
    store.upsert(records)

    result = store.query(vector=[0.1, 0.2, 0.3], top_k=2, filters={"lang": "zh"})

    assert isinstance(result, list)
    assert len(result) == 1
    assert set(result[0].keys()) >= {"id", "score", "metadata"}
    assert isinstance(result[0]["id"], str)
    assert isinstance(result[0]["score"], float)
    assert isinstance(result[0]["metadata"], dict)


def test_contract_upsert_rejects_invalid_shape(isolated_registry: dict[str, object]) -> None:
    """验证 upsert 会拒绝缺失关键字段的非法记录，避免脏数据进入向量库。"""
    VectorStoreFactory.register("fake", lambda persist_dir="": _FakeVectorStore(persist_dir=persist_dir))
    store = VectorStoreFactory.create({"vector_store": {"provider": "fake"}})

    with pytest.raises(ValueError, match="id, vector, metadata"):
        store.upsert([{"id": "bad", "vector": [0.1]}])


def test_factory_missing_provider_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证缺少 `vector_store.provider` 时，错误信息包含明确字段路径。"""
    with pytest.raises(ValueError, match="vector_store.provider"):
        VectorStoreFactory.create({"vector_store": {"persist_dir": "data/db/x"}})


def test_factory_unknown_provider_raises(isolated_registry: dict[str, object]) -> None:
    """验证未知 provider 会显式报错，防止工厂错误分流。"""
    with pytest.raises(ValueError, match="Unknown vector_store provider: unknown"):
        VectorStoreFactory.create({"vector_store": {"provider": "unknown"}})
