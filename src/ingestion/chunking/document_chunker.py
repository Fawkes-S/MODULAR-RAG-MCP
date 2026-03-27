"""DocumentChunker：在 Ingestion 层集成 Splitter（C4）。

该模块是 `libs.splitter` 与 Ingestion Pipeline 之间的适配器层：
- `libs.splitter` 仅负责 `str -> list[str]` 的纯文本切分；
- `DocumentChunker` 负责 `Document -> list[Chunk]` 的业务对象转换。
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from core.types import Chunk, Document
from libs.splitter.base_splitter import BaseSplitter
from libs.splitter.splitter_factory import SplitterFactory

_IMAGE_REF_PATTERN = re.compile(r"\[IMAGE:\s*([^\]\s]+)\s*\]")


class DocumentChunker:
    """将 Document 切分并转换为 Chunk 对象列表。

    做什么：
    - 通过 `SplitterFactory` 根据 `ingestion.splitter` 创建切分器；
    - 调用切分器执行纯文本切分；
    - 将文本片段转换为 `Chunk` 并补齐 ID、metadata、source_ref、offset。

    为什么：
    - 让 libs 层保持“算法/工具”职责，业务语义聚合在 ingestion 层。

    关键权衡：
    - offset 采用“顺序查找优先 + 全局回退”的轻量策略，优先保证稳定可追踪；
      对重复文本不追求最优语义定位，但满足当前 C4 合约要求。

    失败路径：
    - 输入不是 `Document` 或文本为空：立即抛出 ValueError；
    - splitter 配置缺失/非法：由 `SplitterFactory` 抛出可读错误；
    - splitter 返回空列表：抛出 ValueError，避免静默丢数据。

    Args:
        settings: 应用配置对象（dict 或对象），配置路径使用 `ingestion.*`。

    Example:
        >>> chunker = DocumentChunker({"ingestion": {"splitter": "recursive"}})
        >>> chunks = chunker.split_document(doc)
    """

    def __init__(self, settings: Any) -> None:
        self._settings = settings
        self.splitter: BaseSplitter = SplitterFactory.create(settings)

    def split_document(self, document: Document) -> list[Chunk]:
        """执行 Document -> Chunk 的完整转换流程。"""
        if not isinstance(document, Document):
            raise ValueError("document must be Document")
        if not document.text or not document.text.strip():
            raise ValueError(f"Document {document.id} has no text content to split")

        # Step 1: 调用 libs.splitter 进行纯文本切分。
        # 这里是多态调用：实际执行的是工厂路由到的具体实现（例如 RecursiveSplitter）。
        raw_chunks = self.splitter.split_text(document.text)
        if not raw_chunks:
            raise ValueError(f"Splitter returned no chunks for document {document.id}")

        chunks: list[Chunk] = []
        search_cursor = 0

        # Step 2: 将文本片段升级为业务对象（Chunk），补齐 C4 合约字段。
        for chunk_index, chunk_text in enumerate(raw_chunks):
            start_offset, end_offset = self._locate_offsets(
                full_text=document.text,
                chunk_text=chunk_text,
                cursor=search_cursor,
            )
            search_cursor = end_offset

            chunk_id = self._generate_chunk_id(document.id, chunk_index, chunk_text)
            metadata = self._inherit_metadata(document, chunk_index, chunk_text)

            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata=metadata,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    source_ref=document.id,
                )
            )

        return chunks

    @staticmethod
    def _generate_chunk_id(doc_id: str, index: int, text: str) -> str:
        """生成稳定 Chunk ID：`{doc_id}_{index:04d}_{hash8}`。"""
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        return f"{doc_id}_{index:04d}_{digest}"

    @staticmethod
    def _inherit_metadata(document: Document, chunk_index: int, chunk_text: str) -> dict[str, Any]:
        """继承并裁剪 metadata（含图片按需分发）。

        核心规则：
        - 继承文档级 metadata；
        - 增加 `chunk_index`；
        - 扫描 chunk 内 `[IMAGE: id]` 并写入 `image_refs`；
        - `images` 仅保留该 chunk 实际引用的子集；
        - 无图片引用的 chunk，不保留 `images` 字段。
        """
        metadata = dict(document.metadata)
        metadata["chunk_index"] = int(chunk_index)

        refs = DocumentChunker._extract_image_refs(chunk_text)
        metadata["image_refs"] = refs

        images = document.metadata.get("images")
        if isinstance(images, list):
            selected_images = DocumentChunker._select_images_by_refs(images, refs)
            if selected_images:
                metadata["images"] = selected_images
            else:
                metadata.pop("images", None)

        return metadata

    @staticmethod
    def _extract_image_refs(chunk_text: str) -> list[str]:
        """提取 chunk 文本中的图片引用 ID，保持首次出现顺序并去重。"""
        seen: set[str] = set()
        refs: list[str] = []

        for match in _IMAGE_REF_PATTERN.finditer(chunk_text):
            image_id = match.group(1).strip()
            if not image_id or image_id in seen:
                continue
            seen.add(image_id)
            refs.append(image_id)

        return refs

    @staticmethod
    def _select_images_by_refs(images: list[Any], refs: list[str]) -> list[dict[str, Any]]:
        """按引用列表从文档级 images 中筛选子集。"""
        image_map: dict[str, dict[str, Any]] = {}
        for image in images:
            if not isinstance(image, dict):
                continue
            image_id = image.get("id")
            if isinstance(image_id, str) and image_id.strip():
                image_map[image_id] = dict(image)

        selected: list[dict[str, Any]] = []
        for ref in refs:
            image = image_map.get(ref)
            if image is not None:
                selected.append(image)

        return selected

    @staticmethod
    def _locate_offsets(full_text: str, chunk_text: str, cursor: int) -> tuple[int, int]:
        """定位 chunk 在原文中的起止 offset。

        策略：
        1. 优先从 `cursor` 之后查找，避免命中前文同名片段；
        2. 若失败，再全局查找一次；
        3. 仍失败则回退到 cursor，确保流程可继续。
        """
        if not chunk_text:
            return max(cursor, 0), max(cursor, 0)

        start = full_text.find(chunk_text, max(cursor, 0))
        if start < 0:
            start = full_text.find(chunk_text)
        if start < 0:
            start = max(cursor, 0)

        end = start + len(chunk_text)
        if end < start:
            end = start

        return start, end
