"""PDF Loader 实现（C3）。

设计目标（对齐开发文档）：
- 文本主链路：通过 MarkItDown 将 PDF 转换为 Markdown；
- 图片主链路：通过 PyMuPDF（fitz）提取图片；
- 图片落盘：`data/images/{doc_hash}/`；
- 图文关联：在 `Document.text` 中插入 `[IMAGE: {image_id}]` 占位符；
- 元数据补齐：`source_path/doc_type/page/title/heading_outline/sha256/images`；
- 降级策略：图片提取失败不阻塞文本解析，并记录 warning 日志。
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from core.types import Document, IMAGE_PLACEHOLDER_TEMPLATE
from libs.loader.base_loader import BaseLoader

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - 环境依赖可变
    fitz = None

try:
    from markitdown import MarkItDown
except ImportError:  # pragma: no cover - 环境依赖可变
    MarkItDown = None  # type: ignore

logger = logging.getLogger(__name__)


class PdfLoader(BaseLoader):
    """PDF 文档加载器。

    Args:
        image_root: 图片落盘根目录，默认 `data/images`。
    """

    def __init__(self, image_root: str = "data/images") -> None:
        self.image_root = Path(image_root)
        self.image_root.mkdir(parents=True, exist_ok=True)

    def load(self, path: str) -> Document:
        """加载 PDF 并输出统一 Document。

        Args:
            path: 待解析 PDF 文件路径。

        Returns:
            Document: `text` 为规范化 Markdown，metadata 至少包含 `source_path`。

        Raises:
            FileNotFoundError: 文件不存在或不是常规文件。
            PermissionError: 文件不可读。
            ValueError: 文件不是 PDF。
            RuntimeError: MarkItDown 或 PyMuPDF 关键依赖缺失时抛出明确错误。
        """
        pdf_path = self._validate_file(path)
        raw_pdf = pdf_path.read_bytes()
        if not raw_pdf.startswith(b"%PDF"):
            raise ValueError(f"Not a PDF file: {pdf_path}")

        sha256 = hashlib.sha256(raw_pdf).hexdigest()
        doc_hash = sha256[:16]
        doc_id = f"pdf_{doc_hash}"

        markdown_text = self._convert_pdf_to_markdown(pdf_path)

        images: list[dict[str, Any]] = []
        try:
            images = self._extract_images_with_pymupdf(pdf_path=pdf_path, doc_hash=doc_hash)
        except Exception:
            # 降级行为：图片提取失败不阻塞文本解析。
            logger.warning(
                "Image extraction failed for %s; continue with text-only result.",
                pdf_path,
                exc_info=True,
            )
            images = []

        markdown_with_placeholders = self._insert_image_placeholders(markdown_text, images)
        self._backfill_image_offsets(markdown_with_placeholders, images)

        title = self._extract_title(markdown_with_placeholders, fallback=pdf_path.stem)
        heading_outline = self._extract_heading_outline(markdown_with_placeholders)
        page_count = self._get_page_count(pdf_path)

        metadata: dict[str, Any] = {
            "source_path": str(pdf_path),
            "doc_type": "pdf",
            "page": page_count,
            "title": title,
            "heading_outline": heading_outline,
            "sha256": sha256,
            "parse_backend": "markitdown+pymupdf",
        }
        if images:
            metadata["images"] = images

        return Document(id=doc_id, text=markdown_with_placeholders, metadata=metadata)

    def _convert_pdf_to_markdown(self, pdf_path: Path) -> str:
        """使用 MarkItDown 将 PDF 转换为 Markdown。"""
        if MarkItDown is None:
            raise RuntimeError(
                "MarkItDown is not installed. Please install `markitdown[pdf]` in this environment."
            )

        converter = MarkItDown()
        result = converter.convert(str(pdf_path))
        raw_text = str(getattr(result, "text_content", "") or "")

        return self._normalize_markdown(raw_text, fallback_title=pdf_path.stem)

    @staticmethod
    def _normalize_markdown(raw_text: str, fallback_title: str) -> str:
        """将 MarkItDown 输出标准化为 canonical Markdown 子集。"""
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return f"# {fallback_title}"

        lines = text.split("\n")
        first_non_empty = -1
        for idx, line in enumerate(lines):
            if line.strip():
                first_non_empty = idx
                break

        if first_non_empty == -1:
            return f"# {fallback_title}"

        first_line = lines[first_non_empty].strip()
        if not re.match(r"^#{1,6}\s+", first_line):
            lines[first_non_empty] = f"# {first_line}"

        normalized = "\n".join(lines).strip()
        return normalized if normalized else f"# {fallback_title}"

    def _extract_images_with_pymupdf(self, pdf_path: Path, doc_hash: str) -> list[dict[str, Any]]:
        """使用 PyMuPDF 提取图片并保存到 `data/images/{doc_hash}/`。"""
        if fitz is None:
            raise RuntimeError(
                "PyMuPDF is not installed. Please install `pymupdf` in this environment."
            )

        out_dir = self.image_root / doc_hash
        out_dir.mkdir(parents=True, exist_ok=True)

        images: list[dict[str, Any]] = []

        with fitz.open(str(pdf_path)) as pymu_doc:
            for page_index in range(int(pymu_doc.page_count)):
                page = pymu_doc.load_page(page_index)
                page_number = page_index + 1

                seq = 0
                seen_xrefs: set[int] = set()

                for image_info in page.get_images(full=True):
                    if not image_info:
                        continue

                    xref = int(image_info[0])
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    # 优先根据图片几何位置提取“就近文本锚点”，避免占位符固定插在页首标题后。
                    anchor_text = self._extract_anchor_text_for_image(page, xref)

                    extracted = pymu_doc.extract_image(xref)
                    image_bytes = extracted.get("image") if isinstance(extracted, dict) else None
                    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
                        continue

                    seq += 1
                    image_id = f"{doc_hash}_{page_number}_{seq:04d}"

                    ext = str(extracted.get("ext", "png")).lower() if isinstance(extracted, dict) else "png"
                    if ext not in {"png", "jpg", "jpeg", "webp", "bmp", "tiff"}:
                        ext = "bin"

                    image_path = out_dir / f"{image_id}.{ext}"
                    image_path.write_bytes(bytes(image_bytes))

                    width = int(extracted.get("width") or 0) if isinstance(extracted, dict) else 0
                    height = int(extracted.get("height") or 0) if isinstance(extracted, dict) else 0
                    if width <= 0 and len(image_info) > 3:
                        width = int(image_info[2] or 0)
                        height = int(image_info[3] or 0)

                    images.append(
                        {
                            "id": image_id,
                            "path": image_path.as_posix(),
                            "page": page_number,
                            "text_offset": 0,
                            "text_length": 0,
                            "position": {"width": width, "height": height},
                            "_anchor_text": anchor_text,
                        }
                    )

        return images

    @staticmethod
    def _extract_page_anchor_text(page: Any) -> str:
        """提取页面首行文本作为占位符插入锚点。"""
        try:
            plain = str(page.get_text("text") or "")
        except Exception:
            return ""

        for line in plain.splitlines():
            candidate = line.strip()
            if candidate:
                return candidate[:120]
        return ""

    def _extract_anchor_text_for_image(self, page: Any, xref: int) -> str:
        """为图片提取更接近其实际位置的文本锚点。

        做什么：
        - 读取页面文本块与图片矩形；
        - 优先选择“位于图片上方且最近”的文本块末行作为锚点；
        - 若无法定位，则回退为页面首行锚点。

        为什么：
        - 仅用页首锚点会把占位符插得过早（常在标题后），导致图文顺序偏离原文。

        失败路径：
        - 页面不支持几何接口或无可用文本块时，回退到 `_extract_page_anchor_text()`。
        """
        blocks = self._extract_text_blocks(page)
        if not blocks:
            return self._extract_page_anchor_text(page)

        try:
            rects = list(page.get_image_rects(int(xref)) or [])
        except Exception:
            rects = []

        if rects:
            try:
                image_top = min(float(getattr(rect, "y0", 0.0)) for rect in rects)
            except Exception:
                image_top = 0.0

            # 先找“在图片上方”的最近文本块。
            above_blocks = [block for block in blocks if block["y1"] <= image_top]
            if above_blocks:
                nearest_above = max(above_blocks, key=lambda item: item["y1"])
                line = self._extract_last_non_empty_line(nearest_above["text"])
                if line:
                    return line

            # 若上方没有文本，退化到几何中心最近的文本块。
            nearest = min(
                blocks,
                key=lambda item: abs(((item["y0"] + item["y1"]) / 2.0) - image_top),
            )
            line = self._extract_last_non_empty_line(nearest["text"])
            if line:
                return line

        return self._extract_page_anchor_text(page)

    @staticmethod
    def _extract_text_blocks(page: Any) -> list[dict[str, Any]]:
        """提取页面文本块（仅保留有文本且坐标可解析的块）。"""
        try:
            raw_blocks = page.get_text("blocks") or []
        except Exception:
            return []

        blocks: list[dict[str, Any]] = []
        for block in raw_blocks:
            if not isinstance(block, (tuple, list)) or len(block) < 5:
                continue

            text = str(block[4] or "")
            if not text.strip():
                continue

            try:
                y0 = float(block[1])
                y1 = float(block[3])
            except Exception:
                continue

            blocks.append({"y0": y0, "y1": y1, "text": text})

        return blocks

    @staticmethod
    def _extract_last_non_empty_line(text: str, max_len: int = 120) -> str:
        """提取文本块末尾的非空行，作为更自然的插入锚点。"""
        for line in reversed(text.splitlines()):
            candidate = line.strip()
            if candidate:
                return candidate[:max_len]
        return ""

    def _insert_image_placeholders(self, markdown_text: str, images: list[dict[str, Any]]) -> str:
        """将图片占位符插入 Markdown 文本。

        策略：
        - 优先在图片所在页的锚点文本后插入；
        - 若找不到锚点，则追加到文末；
        - 保持图片顺序稳定（按 page/id 排序）。
        """
        if not images:
            return markdown_text

        text = markdown_text
        cursor = 0

        for image in sorted(images, key=lambda item: (int(item.get("page", 1)), str(item.get("id", "")))):
            image_id = str(image.get("id", "")).strip()
            if not image_id:
                continue

            placeholder = IMAGE_PLACEHOLDER_TEMPLATE.format(image_id=image_id)
            anchor = str(image.get("_anchor_text", "")).strip()
            inserted = False

            if anchor:
                anchor_pos = text.find(anchor, cursor)
                if anchor_pos >= 0:
                    insert_at = anchor_pos + len(anchor)
                    text = f"{text[:insert_at]}\n\n{placeholder}{text[insert_at:]}"
                    cursor = insert_at + len(placeholder) + 2
                    inserted = True

            if not inserted:
                tail_sep = "\n\n" if text and not text.endswith("\n\n") else ""
                text = f"{text}{tail_sep}{placeholder}"
                cursor = len(text)

            image.pop("_anchor_text", None)

        return text.strip()

    @staticmethod
    def _backfill_image_offsets(text: str, images: list[dict[str, Any]]) -> None:
        """回填占位符在文本中的 offset/length。"""
        for image in images:
            image_id = str(image.get("id", "")).strip()
            if not image_id:
                continue

            placeholder = IMAGE_PLACEHOLDER_TEMPLATE.format(image_id=image_id)
            offset = text.find(placeholder)
            if offset >= 0:
                image["text_offset"] = offset
                image["text_length"] = len(placeholder)
            else:
                image["text_offset"] = 0
                image["text_length"] = 0

    @staticmethod
    def _extract_title(markdown_text: str, fallback: str) -> str:
        """从 Markdown 标题或首行提取文档标题。"""
        for line in markdown_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            heading = re.match(r"^#{1,6}\s+(.*\S)\s*$", stripped)
            if heading:
                return heading.group(1).strip()
            return stripped

        return fallback

    @staticmethod
    def _extract_heading_outline(markdown_text: str) -> list[dict[str, Any]]:
        """提取 Markdown 标题大纲。"""
        outline: list[dict[str, Any]] = []

        for line in markdown_text.splitlines():
            stripped = line.strip()
            matched = re.match(r"^(#{1,6})\s+(.*\S)\s*$", stripped)
            if not matched:
                continue

            outline.append({
                "level": len(matched.group(1)),
                "title": matched.group(2).strip(),
            })

        return outline

    @staticmethod
    def _get_page_count(pdf_path: Path) -> int:
        """读取 PDF 页数，失败时回退为 1。"""
        if fitz is None:
            return 1

        try:
            with fitz.open(str(pdf_path)) as doc:
                count = int(doc.page_count)
                return count if count > 0 else 1
        except Exception:
            logger.warning("Failed to get page_count for %s; fallback to 1.", pdf_path, exc_info=True)
            return 1

