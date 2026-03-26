"""核心数据类型/契约定义（C1）。

该模块集中定义 ingestion -> retrieval -> mcp tools 共享的数据结构：
- Document
- Chunk
- ChunkRecord

设计原则：
- 结构稳定且可序列化（dict/json）；
- metadata 至少包含 `source_path`；
- 对 `metadata.images` 进行基础 shape 校验，保证后续多模态链路可依赖。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

IMAGE_PLACEHOLDER_TEMPLATE = "[IMAGE: {image_id}]"


def _ensure_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty string")
    return value


def _validate_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be dict")

    source_path = metadata.get("source_path")
    _ensure_non_empty_string(source_path, "metadata.source_path")

    images = metadata.get("images")
    if images is not None:
        _validate_images(images)

    return dict(metadata)


def _validate_images(images: Any) -> None:
    if not isinstance(images, list):
        raise ValueError("metadata.images must be list")

    for idx, image in enumerate(images):
        if not isinstance(image, dict):
            raise ValueError(f"metadata.images[{idx}] must be dict")

        _ensure_non_empty_string(image.get("id"), f"metadata.images[{idx}].id")
        _ensure_non_empty_string(image.get("path"), f"metadata.images[{idx}].path")

        if "page" in image and not isinstance(image["page"], int):
            raise ValueError(f"metadata.images[{idx}].page must be int")

        if "text_offset" in image:
            text_offset = image["text_offset"]
            if not isinstance(text_offset, int) or text_offset < 0:
                raise ValueError(f"metadata.images[{idx}].text_offset must be non-negative int")

        if "text_length" in image:
            text_length = image["text_length"]
            if not isinstance(text_length, int) or text_length < 0:
                raise ValueError(f"metadata.images[{idx}].text_length must be non-negative int")

        if "position" in image and not isinstance(image["position"], dict):
            raise ValueError(f"metadata.images[{idx}].position must be dict")


@dataclass
class Document:
    """文档层契约。

    Attributes:
        id: 文档唯一标识。
        text: 规范化后的正文（如 Markdown）。
        metadata: 至少包含 `source_path`，可扩展包含页码、标题、images 等字段。
    """

    id: str
    text: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        self.id = _ensure_non_empty_string(self.id, "id")
        if not isinstance(self.text, str):
            raise ValueError("text must be string")
        self.metadata = _validate_metadata(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """序列化为稳定字典结构。"""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """从字典反序列化。
           从字典创建对象”，它是构造入口。支持继承
        """
        return cls(
            id=str(data.get("id", "")),
            text=str(data.get("text", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class Chunk:
    """切片层契约。"""

    id: str
    text: str
    metadata: dict[str, Any]
    start_offset: int
    end_offset: int
    source_ref: str | None = None

    def __post_init__(self) -> None:
        self.id = _ensure_non_empty_string(self.id, "id")
        if not isinstance(self.text, str):
            raise ValueError("text must be string")
        self.metadata = _validate_metadata(self.metadata)

        if not isinstance(self.start_offset, int) or self.start_offset < 0:
            raise ValueError("start_offset must be non-negative int")
        if not isinstance(self.end_offset, int) or self.end_offset < 0:
            raise ValueError("end_offset must be non-negative int")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be >= start_offset")

        if self.source_ref is not None and not isinstance(self.source_ref, str):
            raise ValueError("source_ref must be string or None")

    def to_dict(self) -> dict[str, Any]:
        """序列化为稳定字典结构。"""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": dict(self.metadata),
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "source_ref": self.source_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        """从字典反序列化。"""
        return cls(
            id=str(data.get("id", "")),
            text=str(data.get("text", "")),
            metadata=dict(data.get("metadata", {})),
            start_offset=int(data.get("start_offset", 0)),
            end_offset=int(data.get("end_offset", 0)),
            source_ref=data.get("source_ref"),
        )


@dataclass
class ChunkRecord:
    """存储/检索载体契约。"""
    """代表已完全处理完毕、可随时存储和检索的数据块。

    This is the output of the embedding pipeline and the data structure
    stored in vector databases. It extends Chunk with vector representations.
    这是embedding pipeline的输出和存储在向量数据库中的数据结构。它用向量表示法扩展了 Chunk。

    Attributes:
        id: Unique chunk identifier (must be stable for idempotent upsert)
        text: Chunk content (same as Chunk.text)
        metadata: Extended metadata including:
            - source_path (required): Original file path
            - chunk_index: Sequential position
            - All metadata from Chunk
            - Any enrichment from Transform pipeline (title, summary, tags)
            - caption: Image caption if multimodal enrichment applied
        dense_vector: Dense embedding vector (e.g., from OpenAI, BGE)
        sparse_vector: Sparse vector for BM25/keyword matching (optional)

    Example:
        >>> record = ChunkRecord(
        ...     id="chunk_abc123_001",
        ...     text="## Section 1\\n\\nFirst paragraph...",
        ...     metadata={
        ...         "source_path": "data/documents/report.pdf",
        ...         "chunk_index": 0,
        ...         "title": "Introduction",
        ...         "summary": "Overview of project goals"
        ...     },
        ...     dense_vector=[0.1, 0.2, ..., 0.3],
        ...     sparse_vector={"word1": 0.5, "word2": 0.3}
        ... )
    """

    id: str
    text: str
    metadata: dict[str, Any]
    dense_vector: list[float] | None = None
    sparse_vector: dict[str, float] | None = None

    def __post_init__(self) -> None:
        self.id = _ensure_non_empty_string(self.id, "id")
        if not isinstance(self.text, str):
            raise ValueError("text must be string")
        self.metadata = _validate_metadata(self.metadata)

        if self.dense_vector is not None:
            if not isinstance(self.dense_vector, list):
                raise ValueError("dense_vector must be list[float] or None")
            self.dense_vector = [float(x) for x in self.dense_vector]

        if self.sparse_vector is not None:
            if not isinstance(self.sparse_vector, dict):
                raise ValueError("sparse_vector must be dict[str, float] or None")
            normalized_sparse: dict[str, float] = {}
            for key, value in self.sparse_vector.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError("sparse_vector keys must be non-empty strings")
                normalized_sparse[key] = float(value)
            self.sparse_vector = normalized_sparse

    def to_dict(self) -> dict[str, Any]:
        """序列化为稳定字典结构。"""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": dict(self.metadata),
            "dense_vector": list(self.dense_vector) if self.dense_vector is not None else None,
            "sparse_vector": dict(self.sparse_vector) if self.sparse_vector is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChunkRecord":
        """从字典反序列化。"""
        return cls(
            id=str(data.get("id", "")),
            text=str(data.get("text", "")),
            metadata=dict(data.get("metadata", {})),
            dense_vector=data.get("dense_vector"),
            sparse_vector=data.get("sparse_vector"),
        )
