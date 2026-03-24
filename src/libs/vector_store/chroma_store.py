"""Chroma vector store implementation.

实现目标：
- 提供最小 `upsert(records)` 与 `query(vector, top_k, filters)` 能力；
- 支持本地持久化目录，满足开发环境下可复现回环测试；
- 保持 `BaseVectorStore` 契约，供上层流程无感切换。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from libs.vector_store.base_vector_store import BaseVectorStore


class ChromaStore(BaseVectorStore):
    """基于 ChromaDB 的向量存储实现。"""

    provider_name = "chroma"

    def __init__(
        self,
        persist_dir: str = "data/db/chroma",
        collection_name: str = "chunks",
        **_: Any,
    ) -> None:
        """初始化 ChromaStore，仅允许持久化模式。失败时直接抛错。

        Args:
            persist_dir: 本地持久化目录。默认固定为 `data/db/chroma`。
            collection_name: Chroma collection 名称。

        Raises:
            OSError: 目录创建失败（权限不足、路径非法等）。
            Exception: Chroma PersistentClient 初始化失败。
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.persist_dir)
        self._collection = self._client.get_or_create_collection(name=self.collection_name)

    def upsert(self, records: list[dict[str, Any]], trace: Any | None = None) -> None:
        """批量写入向量记录。

        Args:
            records: 记录列表，每项至少包含 `id`、`vector`、`metadata`；可选 `text`。
            trace: 预留链路参数（当前未使用）。

        Raises:
            ValueError: 输入 shape 非法时抛出。
        """
        if not isinstance(records, list) or len(records) == 0:
            raise ValueError("[chroma] ValidationError: records must be non-empty list")

        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        documents: list[str] = []

        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"[chroma] ValidationError: records[{idx}] must be dict")
            if "id" not in record or "vector" not in record or "metadata" not in record:
                raise ValueError(f"[chroma] ValidationError: records[{idx}] missing id/vector/metadata")

            record_id = record["id"]
            vector = record["vector"]
            metadata = record["metadata"]
            text = record.get("text", "")

            if not isinstance(record_id, str) or not record_id.strip():
                raise ValueError(f"[chroma] ValidationError: records[{idx}].id must be non-empty string")
            if not isinstance(vector, list) or len(vector) == 0:
                raise ValueError(f"[chroma] ValidationError: records[{idx}].vector must be non-empty list")
            if not isinstance(metadata, dict):
                raise ValueError(f"[chroma] ValidationError: records[{idx}].metadata must be dict")

            ids.append(record_id)
            embeddings.append([float(v) for v in vector])
            metadatas.append(metadata)
            documents.append(str(text))

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """向量检索。

        Returns:
            list[dict[str, Any]]: 每项包含 `id`、`score`、`metadata`、`text`。
        """
        if not isinstance(vector, list) or len(vector) == 0:
            raise ValueError("[chroma] ValidationError: vector must be non-empty list")
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("[chroma] ValidationError: top_k must be positive int")

        raw = self._collection.query(
            query_embeddings=[[float(v) for v in vector]],
            n_results=top_k,
            where=filters or None,
            include=["metadatas", "distances", "documents"],
        )

        ids = (raw.get("ids") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        documents = (raw.get("documents") or [[]])[0]

        results: list[dict[str, Any]] = []
        for i, item_id in enumerate(ids):
            distance = float(distances[i]) if i < len(distances) else 0.0
            score = 1.0 / (1.0 + max(distance, 0.0))
            metadata = metadatas[i] if i < len(metadatas) and isinstance(metadatas[i], dict) else {}
            text = documents[i] if i < len(documents) and isinstance(documents[i], str) else ""
            results.append(
                {
                    "id": str(item_id),
                    "score": score,
                    "metadata": metadata,
                    "text": text,
                }
            )

        return results
