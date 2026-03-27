"""PDF Loader 契约测试（C3）。"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.types import Document, IMAGE_PLACEHOLDER_TEMPLATE
from libs.loader.base_loader import BaseLoader
from libs.loader.pdf_loader import PdfLoader


FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents"


def _new_image_root() -> Path:
    """为每次测试创建独立图片目录，避免并发污染。"""
    path = PROJECT_ROOT / "data" / "images" / f"test_loader_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup_dir(path: Path) -> None:
    """清理测试生成的临时目录。"""
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def test_base_loader_validate_file_rejects_missing_path() -> None:
    """
    Given:
        一个不存在的文件路径。

    When:
        调用 `BaseLoader._validate_file()`。

    Then:
        应抛出 `FileNotFoundError`，阻止无效路径进入 Loader 主流程。
    """
    missing_path = FIXTURE_DIR / "__not_exists__.pdf"

    with pytest.raises(FileNotFoundError, match="file not found"):
        BaseLoader._validate_file(missing_path)


def test_base_loader_validate_file_rejects_directory() -> None:
    """
    Given:
        一个目录路径（非文件）。

    When:
        调用 `BaseLoader._validate_file()`。

    Then:
        应抛出 `FileNotFoundError`（not a regular file），避免把目录当文件解析。
    """
    with pytest.raises(FileNotFoundError, match="not a regular file"):
        BaseLoader._validate_file(FIXTURE_DIR)


def test_pdf_loader_contract_builds_id_and_metadata_with_stubbed_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        一个真实 PDF 输入，但将 `MarkItDown` 转换和图片提取都替换为可控桩函数。

    When:
        调用 `PdfLoader.load()` 构建 Document。

    Then:
        - `Document.id` 使用 sha256 前 16 位；
        - metadata 满足契约关键字段（source_path/doc_type/title/heading_outline/sha256）；
        - 无图片时 `metadata.images` 不强制出现。
    """
    pdf_path = FIXTURE_DIR / "simple.pdf"
    image_root = _new_image_root()

    def _fake_markdown(self: PdfLoader, path: Path) -> str:
        return "# 合同标题\n\n合同正文段落"

    def _fake_images(self: PdfLoader, pdf_path: Path, doc_hash: str) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(PdfLoader, "_convert_pdf_to_markdown", _fake_markdown)
    monkeypatch.setattr(PdfLoader, "_extract_images_with_pymupdf", _fake_images)

    loader = PdfLoader(image_root=str(image_root))

    try:
        doc = loader.load(str(pdf_path))

        assert isinstance(doc, Document)
        assert doc.id.startswith("pdf_")
        assert doc.metadata["source_path"] == str(pdf_path.resolve())
        assert doc.metadata["doc_type"] == "pdf"
        assert doc.metadata["title"] == "合同标题"
        assert doc.metadata["heading_outline"] == [{"level": 1, "title": "合同标题"}]

        sha256 = doc.metadata["sha256"]
        assert isinstance(sha256, str) and len(sha256) == 64
        assert doc.id == f"pdf_{sha256[:16]}"
        assert "images" not in doc.metadata
    finally:
        _cleanup_dir(image_root)


def test_pdf_loader_contract_backfills_image_offsets_with_stubbed_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        通过桩函数返回固定 Markdown 和固定 images 元数据（模拟提图结果）。

    When:
        调用 `PdfLoader.load()`，让 Loader 负责占位符插入与 offset 回填。

    Then:
        - 文本中能看到 `[IMAGE: {image_id}]`；
        - 每张图的 `text_offset/text_length` 与实际文本位置一致；
        - `metadata.images` 字段形状符合 C1 合约关键要求。
    """
    pdf_path = FIXTURE_DIR / "with_images.pdf"
    image_root = _new_image_root()

    fake_img_dir = image_root / "fake"
    fake_img_dir.mkdir(parents=True, exist_ok=True)
    fake1 = fake_img_dir / "img_1.png"
    fake2 = fake_img_dir / "img_2.png"
    fake1.write_bytes(b"x")
    fake2.write_bytes(b"y")

    def _fake_markdown(self: PdfLoader, path: Path) -> str:
        return "# 图片合同\n\n第一页锚点\n\n第二页锚点"

    def _fake_images(self: PdfLoader, pdf_path: Path, doc_hash: str) -> list[dict[str, object]]:
        return [
            {
                "id": "img_a",
                "path": fake1.as_posix(),
                "page": 1,
                "text_offset": 0,
                "text_length": 0,
                "position": {"width": 10, "height": 10},
                "_anchor_text": "第一页锚点",
            },
            {
                "id": "img_b",
                "path": fake2.as_posix(),
                "page": 2,
                "text_offset": 0,
                "text_length": 0,
                "position": {"width": 20, "height": 20},
                "_anchor_text": "第二页锚点",
            },
        ]

    monkeypatch.setattr(PdfLoader, "_convert_pdf_to_markdown", _fake_markdown)
    monkeypatch.setattr(PdfLoader, "_extract_images_with_pymupdf", _fake_images)

    loader = PdfLoader(image_root=str(image_root))

    try:
        doc = loader.load(str(pdf_path))
        images = doc.metadata.get("images")
        assert isinstance(images, list)
        assert len(images) == 2

        for image in images:
            image_id = image["id"]
            placeholder = IMAGE_PLACEHOLDER_TEMPLATE.format(image_id=image_id)
            expected_offset = doc.text.find(placeholder)

            assert expected_offset >= 0
            assert image["text_offset"] == expected_offset
            assert image["text_length"] == len(placeholder)
            assert isinstance(image["page"], int)
            assert isinstance(image["position"], dict)
            assert "path" in image
    finally:
        _cleanup_dir(image_root)


def test_pdf_loader_contract_degrades_gracefully_when_image_extraction_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Given:
        将图片提取函数替换为固定抛错，模拟 PyMuPDF 提图异常。

    When:
        调用 `PdfLoader.load()`。

    Then:
        - 不应抛错（文本解析照常完成）；
        - `metadata.images` 可缺失；
        - warning 日志记录降级行为。
    """
    pdf_path = FIXTURE_DIR / "with_images.pdf"
    image_root = _new_image_root()

    def _fake_markdown(self: PdfLoader, path: Path) -> str:
        return "# 降级标题\n\n降级正文"

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated image extraction failure")

    monkeypatch.setattr(PdfLoader, "_convert_pdf_to_markdown", _fake_markdown)
    monkeypatch.setattr(PdfLoader, "_extract_images_with_pymupdf", _boom)

    loader = PdfLoader(image_root=str(image_root))

    try:
        with caplog.at_level("WARNING"):
            doc = loader.load(str(pdf_path))

        assert doc.text.strip() != ""
        assert doc.text.lstrip().startswith("#")
        assert "images" not in doc.metadata
        assert any("Image extraction failed" in message for message in caplog.messages)
    finally:
        _cleanup_dir(image_root)


def test_pdf_loader_contract_rejects_non_pdf_file() -> None:
    """
    Given:
        一个可读但非 PDF 的文本文件。

    When:
        调用 `PdfLoader.load()`。

    Then:
        应抛出 `ValueError`，避免非 PDF 输入进入后续解析路径。
    """
    temp_dir = PROJECT_ROOT / "data" / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    bad_file = temp_dir / f"not_pdf_{uuid.uuid4().hex}.txt"
    bad_file.write_text("not-a-pdf", encoding="utf-8")

    loader = PdfLoader()

    try:
        with pytest.raises(ValueError, match="Not a PDF file"):
            loader.load(str(bad_file))
    finally:
        if bad_file.exists():
            bad_file.unlink()


def test_pdf_loader_anchor_prefers_text_nearest_above_image_rect() -> None:
    """
    Given:
        页面中存在多段文本与一张图片，且图片下方还有文本。

    When:
        调用 `_extract_anchor_text_for_image()` 选择占位符插入锚点。

    Then:
        应优先返回“图片上方最近文本块”的末行，而不是页首标题，
        以减少图文顺序偏差（占位符过早插入）的问题。
    """

    class _FakeRect:
        def __init__(self, y0: float, y1: float) -> None:
            self.y0 = y0
            self.y1 = y1

    class _FakePage:
        def __init__(self, blocks: list[tuple[float, float, float, float, str, int, int]]) -> None:
            self._blocks = blocks
            self._rects: dict[int, list[_FakeRect]] = {}

        def set_rects(self, xref: int, rects: list[_FakeRect]) -> None:
            self._rects[xref] = rects

        def get_image_rects(self, xref: int) -> list[_FakeRect]:
            return self._rects.get(xref, [])

        def get_text(self, mode: str) -> object:
            if mode == "blocks":
                return self._blocks
            if mode == "text":
                merged = "\n".join(str(block[4]).strip() for block in self._blocks if str(block[4]).strip())
                return merged
            return ""

    blocks = [
        (0.0, 10.0, 500.0, 30.0, "Document with Images\n", 0, 0),
        (0.0, 120.0, 500.0, 160.0, "This document contains an embedded image below:\n", 1, 0),
        (0.0, 230.0, 500.0, 260.0, "Text continues after the image.\n", 2, 0),
    ]

    page = _FakePage(blocks)
    page.set_rects(7, [_FakeRect(170.0, 220.0)])

    loader = PdfLoader()
    anchor = loader._extract_anchor_text_for_image(page, 7)

    assert anchor == "This document contains an embedded image below:"
