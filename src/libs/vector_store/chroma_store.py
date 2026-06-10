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
            where=self._normalize_where(filters),
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

    def get_by_ids(self, ids: list[str], trace: Any | None = None) -> list[dict[str, Any]]:
        """按 ID 批量读取记录。"""
        _ = trace
        if not isinstance(ids, list):
            raise ValueError("[chroma] ValidationError: ids must be list[str]")

        normalized_ids: list[str] = []
        for idx, item in enumerate(ids):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"[chroma] ValidationError: ids[{idx}] must be non-empty string")
            normalized_ids.append(item.strip())

        if not normalized_ids:
            return []

        raw = self._collection.get(ids=normalized_ids, include=["metadatas", "documents"])
        found_ids = raw.get("ids") or []
        metadatas = raw.get("metadatas") or []
        documents = raw.get("documents") or []

        by_id: dict[str, dict[str, Any]] = {}
        for i, item_id in enumerate(found_ids):
            item_key = str(item_id)
            metadata = metadatas[i] if i < len(metadatas) and isinstance(metadatas[i], dict) else {}
            text = documents[i] if i < len(documents) and isinstance(documents[i], str) else ""
            by_id[item_key] = {"id": item_key, "text": text, "metadata": metadata}

        # 返回顺序与入参 ids 一致，便于上层稳定对齐分数与正文。
        return [by_id[item_id] for item_id in normalized_ids if item_id in by_id]

    def get_by_metadata(
        self,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """按 metadata 条件批量读取记录。

        做什么：
        - 支持 Dashboard/DocumentManager 以“文档视角”读取 chunk；
        - `filters=None` 时返回当前 collection 下全部记录；
        - 统一输出为 `id/text/metadata`，避免上层直接依赖 Chroma 原始返回结构。

        关键权衡：
        - 当前仅支持精确匹配过滤，不做复杂表达式；
        - 返回顺序按 `chunk_index -> id` 稳定排序，便于页面渲染和测试断言。
        """
        _ = trace
        if filters is not None and not isinstance(filters, dict):
            raise ValueError("[chroma] ValidationError: filters must be dict or None")

        raw = self._collection.get(
            where=self._normalize_where(filters),
            include=["metadatas", "documents"],
        )
        ids = raw.get("ids") or []
        metadatas = raw.get("metadatas") or []
        documents = raw.get("documents") or []

        rows: list[dict[str, Any]] = []
        for idx, item_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
            text = documents[idx] if idx < len(documents) and isinstance(documents[idx], str) else ""
            rows.append(
                {
                    "id": str(item_id),
                    "text": text,
                    "metadata": metadata,
                }
            )

        rows.sort(
            key=lambda row: (
                self._safe_int(row["metadata"].get("chunk_index")),
                str(row["id"]),
            )
        )
        return rows

    def delete_by_metadata(self, filters: dict[str, Any], trace: Any | None = None) -> int:
        """按 metadata 条件批量删除记录。

        为什么先查再删：
        - 上层需要明确知道删掉了多少条；
        - Chroma 的 delete 调用本身不直接给出“实际删除数量”，
          因此这里先查命中集，再按 ID 精确删除。
        """
        _ = trace
        normalized_filters = self._validate_non_empty_filters(filters)
        rows = self.get_by_metadata(normalized_filters)
        if not rows:
            return 0

        self._collection.delete(ids=[row["id"] for row in rows])
        return len(rows)

    def get_collection_stats(self) -> dict[str, Any]:
        """汇总当前 collection 的概览统计。

        做什么：
        - 读取当前 Chroma collection 中的 metadata；
        - 聚合 chunk 数、文档数、图片数；
        - 按业务 `metadata.collection` 维度拆出子统计，供 Dashboard 总览页直接展示。

        为什么：
        - G1 只需要“能看清当前库里有什么”的轻量统计，还不需要等到 G2 的
          `DocumentManager` 完成后再读取跨存储信息；
        - 因此这里先提供一个只依赖 Chroma 的只读统计方法，降低页面首版接入成本。

        关键权衡：
        - 这里优先复用现有 metadata 做近似统计，不额外访问 BM25、图片索引或文件完整性库；
        - 因为 Chroma 里每条 chunk 都有 metadata，所以 chunk 数最准确，文档数和图片数
          则通过去重后的 metadata 字段推导，足够支持 Overview 的趋势判断。

        失败路径：
        - 若 collection 为空，返回全 0 统计，而不是抛错阻断 Dashboard 启动；
        - 若某些 metadata 字段缺失，则按“跳过该字段、保留其余统计”的策略降级。

        Returns:
            dict[str, Any]: 包含总量统计和按 collection 拆分的明细列表。
        """
        total_chunks = int(self._collection.count())
        if total_chunks == 0:
            return {
                "collection_name": self.collection_name,
                "chunk_count": 0,
                "document_count": 0,
                "image_count": 0,
                "collections": [],
            }

        raw = self._collection.get(include=["metadatas"])
        metadatas = raw.get("metadatas") or []
        grouped: dict[str, dict[str, Any]] = {}

        for metadata in metadatas:
            if not isinstance(metadata, dict):
                continue

            # 优先使用业务 collection；若旧数据没有该字段，就回退到 Chroma collection 名称。
            group_name = str(metadata.get("collection") or self.collection_name).strip() or self.collection_name
            group = grouped.setdefault(
                group_name,
                {
                    "name": group_name,
                    "chunk_count": 0,
                    "sources": set(),
                    "images": set(),
                },
            )
            group["chunk_count"] += 1

            source_path = str(metadata.get("source_path") or metadata.get("source") or "").strip()
            if source_path:
                group["sources"].add(source_path)

            for image_id in self._extract_image_ids(metadata):
                group["images"].add(image_id)

        collections: list[dict[str, Any]] = []
        total_documents = 0
        total_images = 0
        for group_name in sorted(grouped):
            group = grouped[group_name]
            document_count = len(group["sources"])
            image_count = len(group["images"])
            total_documents += document_count
            total_images += image_count
            collections.append(
                {
                    "name": group_name,
                    "chunk_count": group["chunk_count"],
                    "document_count": document_count,
                    "image_count": image_count,
                }
            )

        return {
            "collection_name": self.collection_name,
            "chunk_count": total_chunks,
            "document_count": total_documents,
            "image_count": total_images,
            "collections": collections,
        }

    @staticmethod
    def _validate_non_empty_filters(filters: dict[str, Any]) -> dict[str, Any]:
        """校验删除操作必须提供非空过滤条件，避免误删整库。"""
        if not isinstance(filters, dict):
            raise ValueError("[chroma] ValidationError: filters must be dict")
        normalized = {str(key): value for key, value in filters.items() if str(key).strip()}
        if not normalized:
            raise ValueError("[chroma] ValidationError: filters must be non-empty dict")
        return normalized

    @staticmethod
    def _safe_int(value: Any) -> int:
        """把可能来自 metadata 的 chunk_index 安全转换为 int，用于稳定排序。"""
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 10**9

    @staticmethod
    def _normalize_where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
        """把通用过滤字典转换为 Chroma 接受的 where 结构。

        Chroma 的约束是：
        - 单字段过滤可以直接传 `{"field": value}`；
        - 多字段过滤必须包装成 `{"$and": [{"field1": value1}, {"field2": value2}]}`。

        上层调用方更自然的写法是普通 dict，所以这里统一做一次适配。
        """
        if filters is None:
            return None
        if not isinstance(filters, dict):
            raise ValueError("[chroma] ValidationError: filters must be dict or None")

        normalized = {str(key): value for key, value in filters.items() if str(key).strip()}
        if not normalized:
            return None
        if len(normalized) == 1:
            return normalized
        return {"$and": [{key: value} for key, value in normalized.items()]}

    @staticmethod
    def _extract_image_ids(metadata: dict[str, Any]) -> list[str]:
        """从兼容的 metadata 形态中提取唯一图片 ID 列表。"""
        image_ids: list[str] = []

        image_refs = metadata.get("image_refs")
        if isinstance(image_refs, list):
            for item in image_refs:
                if isinstance(item, str) and item.strip():
                    image_ids.append(item.strip())

        images = metadata.get("images")
        if isinstance(images, list):
            for item in images:
                if isinstance(item, str) and item.strip():
                    image_ids.append(item.strip())
                elif isinstance(item, dict):
                    image_id = str(item.get("image_id", "")).strip()
                    if image_id:
                        image_ids.append(image_id)

        return image_ids
