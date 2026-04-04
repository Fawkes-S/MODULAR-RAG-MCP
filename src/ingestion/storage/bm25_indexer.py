"""BM25Indexer：倒排索引构建、持久化与查询（C11）。"""

from __future__ import annotations

import math
import pickle
import re
from pathlib import Path
from typing import Any

from core.types import ChunkRecord

_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class BM25Indexer:
    """基于稀疏统计构建 BM25 倒排索引。

    做什么：
    - 接收 `SparseEncoder` 产出的 `ChunkRecord.sparse_vector`（term -> tf）作为输入。
    - 计算每个 term 的文档频率（df）和 IDF，并构建倒排索引 postings。
    - 将索引序列化到 `data/db/bm25/bm25_index.pkl`，支持重启后加载与继续增量更新。

    为什么：
    - C11 需要把“稀疏编码结果”落地为可查询结构，供后续 D3 SparseRetriever 直接检索。
    - 若不提前构建倒排索引，查询阶段就需要全量扫描所有 chunk，性能与可维护性都不可接受。

    关键权衡：
    - 当前持久化选型使用 `pickle`（与规格一致），优先快速落地和本地可用性。
    - 评分只实现 BM25 核心形式（k1/b 可配置），不叠加额外启发式，保证可解释与可测试。

    失败路径：
    - build 输入不合法或记录缺失 `sparse_vector`：抛 `ValueError`，拒绝写入坏索引。
    - 索引文件损坏/不可读：`load()` 抛 `ValueError`，避免静默使用不完整数据。

    Args:
        persist_dir: 索引目录，默认 `data/db/bm25`。
        k1: BM25 参数，控制词频饱和速度。
        b: BM25 参数，控制文档长度归一化强度。

    Example:
        输入（来自 SparseEncoder 的最小样例）:
            - c1.sparse_vector = {"azure": 2.0, "openai": 1.0}
            - c2.sparse_vector = {"azure": 1.0, "api": 1.0}

        build 后的核心中间结构（示意）:
            - _doc_term_freqs:
                {
                    "c1": {"azure": 2.0, "openai": 1.0},
                    "c2": {"azure": 1.0, "api": 1.0},
                }
            - _inverted_index:
                {
                    "azure": {
                        "idf": <按公式计算>,
                        "postings": [
                            {"chunk_id": "c1", "tf": 2.0, "doc_length": 3.0},
                            {"chunk_id": "c2", "tf": 1.0, "doc_length": 2.0},
                        ],
                    },
                    ...
                }

        query("azure", top_k=2) 输出（示意）:
            [("c1", 0.XX), ("c2", 0.XX)]
    """

    def __init__(self, persist_dir: str = "data/db/bm25", k1: float = 1.5, b: float = 0.75) -> None:
        self.persist_dir = Path(persist_dir)
        self.index_path = self.persist_dir / "bm25_index.pkl"
        self.k1 = float(k1)
        self.b = float(b)

        if self.k1 <= 0:
            raise ValueError("k1 must be > 0")
        if not (0.0 <= self.b <= 1.0):
            raise ValueError("b must satisfy 0 <= b <= 1")

        self._doc_term_freqs: dict[str, dict[str, float]] = {}
        self._doc_lengths: dict[str, float] = {}
        self._doc_sources: dict[str, str] = {}
        self._inverted_index: dict[str, dict[str, Any]] = {}
        self._avg_doc_length: float = 0.0

    def build(self, records: list[ChunkRecord], rebuild: bool = False) -> dict[str, Any]:
        """构建或增量更新 BM25 索引。

        Args:
            records: 由 SparseEncoder 生成的 `ChunkRecord` 列表。
            rebuild: 是否重建。`True` 时先清空已有索引，再写入当前 records。

        Returns:
            dict: 本次构建统计信息。

        说明：
        - `rebuild=True`：
            清空历史索引，仅保留本次 `records` 构建结果。
        - `rebuild=False`：
            采用增量语义。若磁盘已有索引且内存为空，会先 load，再 upsert 本次 records。

        输入输出关系（简化）：
        - 输入：`list[ChunkRecord]`（每条至少有 `id`、`metadata.source_path`、`sparse_vector`）
        - 输出：构建统计 dict，例如
            {
                "documents": 123,
                "terms": 4567,
                "avg_doc_length": 18.2,
                "persist_path": ".../bm25_index.pkl",
                "rebuild": False,
            }
        """
        normalized_records = self._validate_records(records)

        if rebuild:
            self._clear()
        elif not self._doc_term_freqs and self.index_path.exists():
            # 增量更新场景下，如果内存为空且磁盘有历史索引，先加载再合并。
            self.load()

        for record in normalized_records:
            self._upsert_record(record)

        self._rebuild_inverted_index()
        self.save()

        return {
            "documents": len(self._doc_term_freqs),
            "terms": len(self._inverted_index),
            "avg_doc_length": self._avg_doc_length,
            "persist_path": str(self.index_path),
            "rebuild": bool(rebuild),
        }

    def save(self) -> None:
        """将当前索引状态持久化到磁盘。

        持久化 payload 主要包含三层：
        1. 文档级统计：`doc_term_freqs/doc_lengths/doc_sources`
        2. 可查询倒排：`inverted_index`
        3. 评分参数：`k1/b/avg_doc_length`

        这样重启后 `load()` 可以直接恢复查询能力，不需要重新 build。
        """
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "k1": self.k1,
            "b": self.b,
            "doc_term_freqs": self._doc_term_freqs,
            "doc_lengths": self._doc_lengths,
            "doc_sources": self._doc_sources,
            "inverted_index": self._inverted_index,
            "avg_doc_length": self._avg_doc_length,
        }
        self.index_path.write_bytes(pickle.dumps(payload))

    def load(self) -> None:
        """从磁盘加载索引状态到内存。

        行为约定：
        - 索引文件不存在：视为“空索引”，不会抛错；
        - 索引文件损坏/格式错误：抛 `ValueError`，避免使用不可靠数据。
        """
        if not self.index_path.exists():
            self._clear()
            return

        try:
            payload = pickle.loads(self.index_path.read_bytes())
        except Exception as exc:  # pragma: no cover - 防御性分支
            raise ValueError(f"Failed to load BM25 index from {self.index_path}: {exc}") from exc

        if not isinstance(payload, dict):
            raise ValueError(f"Invalid BM25 index payload type: {type(payload).__name__}")

        # 这里虽然通过 `self.` 调用，但这几个 `_ensure_*` 是 `@staticmethod`：
        # - 仅作为“类内工具函数”归档，不依赖实例状态；
        # - 用 `self.` 调用只是语法允许，和 `BM25Indexer._ensure_*` 效果等价。
        self._doc_term_freqs = self._ensure_nested_float_dict(payload.get("doc_term_freqs"))
        self._doc_lengths = self._ensure_float_dict(payload.get("doc_lengths"))
        self._doc_sources = self._ensure_string_dict(payload.get("doc_sources"))

        raw_index = payload.get("inverted_index", {})
        self._inverted_index = self._ensure_inverted_index(raw_index)
        self._avg_doc_length = float(payload.get("avg_doc_length", 0.0))

    def query(self, query: str | list[str], top_k: int = 10) -> list[tuple[str, float]]:
        """执行 BM25 查询，返回 `(chunk_id, score)` 排序结果。

        做什么：
        - 解析 query 为 term 列表；
        - 基于倒排索引找到候选 chunk；
        - 按 BM25 公式累积分数并排序，返回 top_k。

        BM25 核心打分（单 term）：
            score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * |D| / avgdl))

        Example:
            输入：
                query = "azure openai"
                top_k = 2
            输出（示意）：
                [("c1", 0.72), ("c2", 0.41)]

        Note:
        - 结果按“分数降序、chunk_id 升序”排序，确保同分时顺序稳定。
        """
        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        if not self._inverted_index:
            return []

        terms = self._normalize_query_terms(query)
        if not terms:
            return []

        scores: dict[str, float] = {}
        avgdl = self._avg_doc_length if self._avg_doc_length > 0 else 1.0

        for term in terms:
            term_entry = self._inverted_index.get(term)
            if not term_entry:
                continue

            idf = float(term_entry["idf"])
            for posting in term_entry["postings"]:
                chunk_id = posting["chunk_id"]
                tf = float(posting["tf"])
                doc_length = max(float(posting["doc_length"]), 1.0)

                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_length / avgdl))
                if denominator <= 0:
                    continue
                score = idf * (tf * (self.k1 + 1.0) / denominator)
                scores[chunk_id] = scores.get(chunk_id, 0.0) + score

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return ranked[:top_k]

    def get_idf(self, term: str) -> float | None:
        """返回 term 的 IDF；不存在时返回 `None`。

        用途：
        - 单元测试中可直接验证 IDF 公式是否正确；
        - 调试检索效果时，可快速查看“某词是否过于常见/稀有”。
        """
        normalized = term.strip().lower()
        if not normalized:
            return None
        entry = self._inverted_index.get(normalized)
        if entry is None:
            return None
        return float(entry["idf"])

    def remove_document(self, source: str) -> int:
        """按 `metadata.source_path` 删除文档对应索引记录。

        Returns:
            int: 删除的 chunk 数量。

        Example:
            若 source="memory://doc-a.md" 对应 c1/c2 两条记录：
            - 删除前：query("azure") -> [("c1", ...), ("c2", ...), ...]
            - 删除后：query("azure") 不再返回 c1/c2
        """
        normalized_source = str(source).strip()
        if not normalized_source:
            raise ValueError("source must be non-empty string")

        target_ids = [chunk_id for chunk_id, path in self._doc_sources.items() if path == normalized_source]
        if not target_ids:
            return 0

        for chunk_id in target_ids:
            self._doc_sources.pop(chunk_id, None)
            self._doc_lengths.pop(chunk_id, None)
            self._doc_term_freqs.pop(chunk_id, None)

        self._rebuild_inverted_index()
        self.save()
        return len(target_ids)

    def _upsert_record(self, record: ChunkRecord) -> None:
        """将单条 ChunkRecord 写入文档统计，并覆盖同 ID 的旧记录。

        输入要求：
        - `record.sparse_vector` 必须存在，且为 `term -> tf` 映射。

        归一化动作：
        - term: 去空白 + 小写；
        - tf: 转 float，过滤 `<= 0` 的噪声值。

        输出到内部结构：
        - `_doc_term_freqs[record.id] = term_freqs`
        - `_doc_lengths[record.id] = sum(tf)`
        - `_doc_sources[record.id] = metadata.source_path`
        """
        sparse_vector = record.sparse_vector
        if sparse_vector is None:
            raise ValueError(f"ChunkRecord {record.id} missing sparse_vector for BM25 build")

        term_freqs: dict[str, float] = {}
        for raw_term, raw_tf in sparse_vector.items():
            term = str(raw_term).strip().lower()
            if not term:
                continue
            tf = float(raw_tf)
            if tf <= 0:
                continue
            term_freqs[term] = term_freqs.get(term, 0.0) + tf

        doc_length = float(sum(term_freqs.values()))
        self._doc_term_freqs[record.id] = term_freqs
        self._doc_lengths[record.id] = doc_length
        self._doc_sources[record.id] = str(record.metadata.get("source_path", ""))

    def _rebuild_inverted_index(self) -> None:
        """从文档统计重建倒排索引与 IDF。

        说明：
        - C11 验收要求的索引结构为 `{term: {idf, postings: [{chunk_id, tf, doc_length}]}}`。
        - 此方法统一在 build/remove 后重算，保证索引与文档统计一致。

        过程拆解：
        1. 遍历每个文档的 term_freqs，把每个 term 的 posting 追加到倒排列表；
        2. 计算全库平均文档长度 `avg_doc_length`；
        3. 对每个 term 计算 df，并按规格公式计算 IDF。

        公式说明：
        - N: 文档总数（chunk 数）
        - df: 含该 term 的文档数
        - idf = log((N - df + 0.5) / (df + 0.5))

        注意：
        - postings 按 `chunk_id` 排序，保证序列化与测试断言稳定。
        """
        self._inverted_index = {}

        total_docs = len(self._doc_term_freqs)
        if total_docs == 0:
            self._avg_doc_length = 0.0
            return

        total_length = 0.0
        for chunk_id, term_freqs in self._doc_term_freqs.items():
            doc_length = float(self._doc_lengths.get(chunk_id, 0.0))
            total_length += doc_length

            for term, tf in term_freqs.items():
                term_entry = self._inverted_index.setdefault(term, {"idf": 0.0, "postings": []})
                term_entry["postings"].append(
                    {
                        "chunk_id": chunk_id,
                        "tf": float(tf),
                        "doc_length": doc_length,
                    }
                )

        self._avg_doc_length = total_length / float(total_docs)

        for term, term_entry in self._inverted_index.items():
            postings = term_entry["postings"]
            postings.sort(key=lambda row: row["chunk_id"])
            df = len(postings)
            # 按规格实现：IDF(term) = log((N - df + 0.5) / (df + 0.5))
            # idf衡量“一个词的区分度”。 越稀有，区分度越高；
            idf = math.log((float(total_docs) - float(df) + 0.5) / (float(df) + 0.5))
            term_entry["idf"] = float(idf)

    @staticmethod
    def _validate_records(records: list[ChunkRecord]) -> list[ChunkRecord]:
        """校验 build 输入是否为 `list[ChunkRecord]`。

        作用：
        - 把“输入契约错误”尽早拦截在入口层，避免后续构建逻辑出现隐式异常。
        - 返回值仍是原列表，目的是让调用方继续使用同一对象引用。

        Example:
            输入：
                [ChunkRecord(...), ChunkRecord(...)]
            输出：
                原样返回该列表（仅在类型合法时）
        """
        if not isinstance(records, list):
            raise ValueError("records must be list[ChunkRecord]")

        for idx, record in enumerate(records):
            if not isinstance(record, ChunkRecord):
                raise ValueError(f"records[{idx}] must be ChunkRecord")
        return records

    @staticmethod
    def _normalize_query_terms(query: str | list[str]) -> list[str]:
        """将查询输入归一化为 term 列表。

        支持两种输入：
        - str: 例如 `"Azure retry_backoff"` -> `["azure", "retry_backoff"]`
        - list[str]: 例如 `["Azure", "retry_backoff"]` -> `["azure", "retry_backoff"]`

        该方法只负责轻量规范化（小写/去空白），不做同义词扩展。
        """
        if isinstance(query, str):
            return [token for token in _TOKEN_PATTERN.findall(query.lower()) if token.strip("_")]

        if isinstance(query, list):
            terms: list[str] = []
            for item in query:
                if not isinstance(item, str):
                    continue
                normalized = item.strip().lower()
                if normalized:
                    terms.append(normalized)
            return terms

        raise ValueError("query must be str or list[str]")

    def _clear(self) -> None:
        """清空所有内存索引状态。

        使用场景：
        - `build(..., rebuild=True)` 前重置；
        - `load()` 且索引文件不存在时重置为空索引。
        """
        self._doc_term_freqs = {}
        self._doc_lengths = {}
        self._doc_sources = {}
        self._inverted_index = {}
        self._avg_doc_length = 0.0

    @staticmethod
    def _ensure_float_dict(raw: Any) -> dict[str, float]:
        """将任意对象安全归一化为 `dict[str, float]`。

        主要用于 `load()`：
        - 读取 pickle 后，保证字段类型稳定（key 为非空字符串，value 可转 float）。
        - 非 dict 输入直接降级为空字典，避免加载过程崩溃。
        """
        if not isinstance(raw, dict):
            return {}
        normalized: dict[str, float] = {}
        for key, value in raw.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            normalized[key_text] = float(value)
        return normalized

    @staticmethod
    def _ensure_string_dict(raw: Any) -> dict[str, str]:
        """将任意对象安全归一化为 `dict[str, str]`。

        主要用于恢复 `doc_sources`（`chunk_id -> source_path`）：
        - key/value 统一转字符串；
        - 空 key 丢弃，防止产生无效映射。
        """
        if not isinstance(raw, dict):
            return {}
        normalized: dict[str, str] = {}
        for key, value in raw.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            normalized[key_text] = str(value)
        return normalized

    @staticmethod
    def _ensure_nested_float_dict(raw: Any) -> dict[str, dict[str, float]]:
        """将对象归一化为嵌套字典 `dict[str, dict[str, float]]`。

        目标字段：`doc_term_freqs`，结构是：
            {
                "chunk_id": {"term_a": 2.0, "term_b": 1.0},
                ...
            }

        用途：
        - 保证 load 后 `_doc_term_freqs` 的 shape 稳定，后续可直接参与倒排重建。
        """
        if not isinstance(raw, dict):
            return {}
        normalized: dict[str, dict[str, float]] = {}
        for chunk_id, term_map in raw.items():
            chunk_key = str(chunk_id).strip()
            if not chunk_key or not isinstance(term_map, dict):
                continue
            clean_term_map: dict[str, float] = {}
            for term, tf in term_map.items():
                term_key = str(term).strip()
                if not term_key:
                    continue
                clean_term_map[term_key] = float(tf)
            normalized[chunk_key] = clean_term_map
        return normalized

    @staticmethod
    def _ensure_inverted_index(raw: Any) -> dict[str, dict[str, Any]]:
        """将对象归一化为倒排索引结构。

        目标结构：
            {
                "term": {
                    "idf": float,
                    "postings": [{"chunk_id": str, "tf": float, "doc_length": float}, ...]
                },
                ...
            }

        作用：
        - 用于 `load()` 后恢复 `_inverted_index`。
        - 对脏数据做容错过滤，避免坏 posting 污染查询阶段。
        """
        if not isinstance(raw, dict):
            return {}

        normalized: dict[str, dict[str, Any]] = {}
        for term, term_entry in raw.items():
            term_key = str(term).strip()
            if not term_key or not isinstance(term_entry, dict):
                continue

            postings_raw = term_entry.get("postings", [])
            postings: list[dict[str, Any]] = []
            if isinstance(postings_raw, list):
                for posting in postings_raw:
                    if not isinstance(posting, dict):
                        continue
                    chunk_id = str(posting.get("chunk_id", "")).strip()
                    if not chunk_id:
                        continue
                    postings.append(
                        {
                            "chunk_id": chunk_id,
                            "tf": float(posting.get("tf", 0.0)),
                            "doc_length": float(posting.get("doc_length", 0.0)),
                        }
                    )

            normalized[term_key] = {
                "idf": float(term_entry.get("idf", 0.0)),
                "postings": postings,
            }

        return normalized

