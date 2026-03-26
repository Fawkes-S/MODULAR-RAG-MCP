"""核心数据类型（C1）单元测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.types import Chunk, ChunkRecord, Document, IMAGE_PLACEHOLDER_TEMPLATE


def test_document_roundtrip_serialization_is_stable() -> None:
    """
    Given:
        一个包含 `source_path` 与 `images` 元数据的 Document 实例。

    When:
        先 `to_dict()` 再 `json.dumps/json.loads`，最后 `from_dict()` 反序列化。

    Then:
        - 文档关键字段（id/text/metadata）保持一致；
        - 序列化结构稳定，可用于后续跨模块传递与日志落盘。
    """
    doc = Document(
        id="doc-1",
        text="hello [IMAGE: x]",
        metadata={
            "source_path": "docs/a.pdf",
            "images": [
                {
                    "id": "img_1_0",
                    "path": "data/images/default/img_1_0.png",
                    "page": 1,
                    "text_offset": 6,
                    "text_length": 11,
                    "position": {"x": 10, "y": 20},
                }
            ],
        },
    )

    payload = doc.to_dict()
    decoded = json.loads(json.dumps(payload, ensure_ascii=False))
    restored = Document.from_dict(decoded)

    assert restored.id == doc.id
    assert restored.text == doc.text
    assert restored.metadata == doc.metadata


def test_chunk_roundtrip_serialization_is_stable() -> None:
    """
    Given:
        一个带 offset 和 source_ref 的 Chunk。

    When:
        执行 `to_dict()` 与 `from_dict()` roundtrip。

    Then:
        - offset 字段保持一致；
        - `source_ref` 字段不丢失；
        - 可作为 Splitter 与后续 Transform 的稳定契约。
    """
    chunk = Chunk(
        id="chunk-1",
        text="section text",
        metadata={"source_path": "docs/a.pdf"},
        start_offset=0,
        end_offset=12,
        source_ref="docs/a.pdf#p1",
    )

    restored = Chunk.from_dict(chunk.to_dict())

    assert restored.id == "chunk-1"
    assert restored.start_offset == 0
    assert restored.end_offset == 12
    assert restored.source_ref == "docs/a.pdf#p1"


def test_chunk_record_roundtrip_serialization_is_stable() -> None:
    """
    Given:
        一个包含 dense/sparse 向量的 ChunkRecord。

    When:
        执行 `to_dict()` 与 `from_dict()` roundtrip。

    Then:
        - dense_vector 和 sparse_vector 能保持语义一致；
        - 为后续 C8~C12 的编码与存储步骤提供统一载体。
    """
    record = ChunkRecord(
        id="rec-1",
        text="text",
        metadata={"source_path": "docs/a.pdf"},
        dense_vector=[0.1, 0.2, 0.3],
        sparse_vector={"token_a": 1.0, "token_b": 0.5},
    )

    restored = ChunkRecord.from_dict(record.to_dict())

    assert restored.dense_vector == [0.1, 0.2, 0.3]
    assert restored.sparse_vector == {"token_a": 1.0, "token_b": 0.5}


def test_metadata_requires_source_path() -> None:
    """
    Given:
        缺失 `metadata.source_path` 的非法输入。

    When:
        构造 Document/Chunk/ChunkRecord。

    Then:
        均应抛出可读错误，确保全链路最小 metadata 契约被严格执行。
    """
    bad_metadata = {"title": "x"}

    with pytest.raises(ValueError, match="metadata.source_path"):
        Document(id="d", text="x", metadata=bad_metadata)

    with pytest.raises(ValueError, match="metadata.source_path"):
        Chunk(id="c", text="x", metadata=bad_metadata, start_offset=0, end_offset=1)

    with pytest.raises(ValueError, match="metadata.source_path"):
        ChunkRecord(id="r", text="x", metadata=bad_metadata)


def test_metadata_images_schema_validation() -> None:
    """
    Given:
        一个 `metadata.images` 结构错误的输入（text_offset 为负数）。

    When:
        构造 Document。

    Then:
        抛出字段级校验错误，防止不合法图片定位信息进入下游流程。
    """
    with pytest.raises(ValueError, match="text_offset"):
        Document(
            id="doc",
            text="x",
            metadata={
                "source_path": "docs/a.pdf",
                "images": [
                    {
                        "id": "img",
                        "path": "data/images/default/img.png",
                        "text_offset": -1,
                        "text_length": 12,
                    }
                ],
            },
        )


def test_image_placeholder_template_format() -> None:
    """
    Given:
        统一图片占位符模板常量 `IMAGE_PLACEHOLDER_TEMPLATE`。

    When:
        用 image_id 格式化模板。

    Then:
        输出符合规范 `[IMAGE: {image_id}]`，可用于 Loader/Transform 的位置标记。
    """
    placeholder = IMAGE_PLACEHOLDER_TEMPLATE.format(image_id="abc_1_0")

    assert placeholder == "[IMAGE: abc_1_0]"
