"""VectorUpserter：向量写入与幂等 ID 生成（C12）。"""

from __future__ import annotations

import hashlib
import re
from time import perf_counter

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import ChunkRecord
from libs.vector_store.base_vector_store import BaseVectorStore
from libs.vector_store.vector_store_factory import VectorStoreFactory

_CHUNK_INDEX_PATTERN = re.compile(r"_(\d{4})_")


class VectorUpserter:
    """将 DenseEncoder 输出写入向量存储，并提供幂等写入语义。

    做什么：
    - 接收 `ChunkRecord` 列表（要求包含 `dense_vector`），转换成 `BaseVectorStore.upsert` 所需 shape。
    - 为每条记录生成稳定 `chunk_id`（存储主键），保证同内容重复写入不会产生重复记录。
    - 调用底层 `vector_store.upsert()` 批量写入，并可选记录 trace 统计。

    为什么：
    - C12 的目标是把 C8/C10 产出的 dense 编码结果真正落地到向量数据库。
    - 上游 `Chunk.id` 解决“切分阶段定位”，这里重新生成“存储主键”是为了幂等策略与存储层解耦。

    关键权衡：
    - 采用“上游 ID 保留 + 存储 ID 独立”策略：
      - `source_chunk_id`：保留上游切分 ID，便于问题追溯；
      - `id`：使用稳定哈希生成，面向存储幂等。
    - 若缺失 `metadata.chunk_index`，先尝试从上游 `record.id` 解析；仍失败则显式报错，避免静默冲突。

    失败路径：
    - 输入不是 `list[ChunkRecord]`：抛 `ValueError`。
    - 记录缺失 `dense_vector` 或 `metadata.source_path`：抛 `ValueError`。
    - 无法确定 `chunk_index`：抛 `ValueError`，阻止生成不可靠主键。

    Args:
        settings: 全局配置对象，用于构建默认 vector_store。
        vector_store: 可注入向量存储实现（测试或定制场景）。
    """

    def __init__(self, settings: Settings, vector_store: BaseVectorStore | None = None) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("VectorUpserter requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.vector_store = vector_store or VectorStoreFactory.create(settings)

    def upsert(self, records: list[ChunkRecord], trace: TraceContext | None = None) -> list[str]:
        """批量写入向量记录并返回按输入顺序生成的存储 ID 列表。"""
        normalized_records = self._validate_records(records)
        started = perf_counter()

        if not normalized_records:
            if trace is not None:
                trace.record_stage(
                    stage_name="storage.vector_upserter",
                    details={
                        "total": 0,
                        "upserted": 0,
                        "provider": self.settings.vector_store.provider,
                    },
                    elapsed_ms=0.0,
                )
            return []

        payload_records: list[dict[str, object]] = []
        generated_ids: list[str] = []

        for record in normalized_records:
            storage_id = self._generate_chunk_id(record)
            generated_ids.append(storage_id)

            if record.dense_vector is None or len(record.dense_vector) == 0:
                raise ValueError(f"ChunkRecord {record.id} missing dense_vector for vector upsert")

            metadata = dict(record.metadata)
            # 保留上游 ID，便于“存储记录 -> 原始切分片段”回溯。
            metadata["source_chunk_id"] = record.id
            metadata["chunk_id"] = storage_id

            payload_records.append(
                {
                    "id": storage_id,
                    "vector": [float(value) for value in record.dense_vector],
                    "metadata": metadata,
                    "text": record.text,
                }
            )

        self.vector_store.upsert(payload_records, trace=trace)

        if trace is not None:
            trace.record_stage(
                stage_name="storage.vector_upserter",
                details={
                    "total": len(normalized_records),
                    "upserted": len(payload_records),
                    "provider": self.settings.vector_store.provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return generated_ids

    @staticmethod
    def _validate_records(records: list[ChunkRecord]) -> list[ChunkRecord]:
        """校验 upsert 输入契约。"""
        if not isinstance(records, list):
            raise ValueError("records must be list[ChunkRecord]")

        for idx, record in enumerate(records):
            if not isinstance(record, ChunkRecord):
                raise ValueError(f"records[{idx}] must be ChunkRecord")

        return records

    @staticmethod
    def _generate_chunk_id(record: ChunkRecord) -> str:
        """生成存储层幂等主键。

        公式（按 C12 规格）:
            hash(source_path + chunk_index + content_hash[:8])

        说明：
        - `source_path`：同一文档来源保持稳定；
        - `chunk_index`：区分同文档内不同片段；
        - `content_hash[:8]`：内容变化时触发主键变化。
        """
        source_path = VectorUpserter._extract_source_path(record)
        chunk_index = VectorUpserter._resolve_chunk_index(record)
        content_hash = hashlib.sha256(record.text.encode("utf-8")).hexdigest()

        seed = f"{source_path}|{chunk_index}|{content_hash[:8]}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return f"chunk_{digest}"

    @staticmethod
    def _extract_source_path(record: ChunkRecord) -> str:
        """提取并校验 source_path。"""
        source_path = record.metadata.get("source_path")
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError(f"ChunkRecord {record.id} missing metadata.source_path")
        return source_path.strip()

    @staticmethod
    def _resolve_chunk_index(record: ChunkRecord) -> int:
        """解析 chunk_index（优先 metadata，其次从上游 ID 兜底解析）。"""
        raw = record.metadata.get("chunk_index")
        if isinstance(raw, int) and raw >= 0:
            return raw

        if isinstance(raw, str) and raw.strip().isdigit():
            value = int(raw.strip())
            if value >= 0:
                return value

        # 兜底：兼容 DocumentChunker 风格 ID（如 doc_0001_ab12cd34）。
        match = _CHUNK_INDEX_PATTERN.search(record.id)
        if match:
            return int(match.group(1))

        raise ValueError(
            f"ChunkRecord {record.id} missing metadata.chunk_index and cannot infer from id"
        )
