"""PDF Loader 端到端集成测试。"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from pprint import pprint

import pytest

pytest.importorskip("markitdown")
pytest.importorskip("fitz")
pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.loader.pdf_loader import PdfLoader


FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents"


def _new_image_root() -> Path:
    """为每次集成测试创建独立图片目录，避免并发污染。"""
    path = PROJECT_ROOT / "data" / "images" / f"test_loader_integration_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup_dir(path: Path) -> None:
    """清理测试产生的临时图片目录。"""
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def test_pdf_loader_end_to_end_simple_pdf() -> None:
    """
    Given:
        真实 `simple.pdf` 文件，且环境中存在 MarkItDown + PyMuPDF 依赖。

    When:
        调用 `PdfLoader.load()` 执行真实端到端流程（文本转换、元数据构建）。

    Then:
        - 返回结果为可用 Document；
        - `parse_backend` 为 `markitdown+pymupdf`；
        - 文本为 Markdown（标题开头）；
        - 元数据中的标题/哈希等关键字段可用。
    """
    pdf_path = FIXTURE_DIR / "simple.pdf"
    image_root = _new_image_root()
    loader = PdfLoader(image_root=str(image_root))

    try:
        doc = loader.load(str(pdf_path))

        assert doc.id.startswith("pdf_")
        assert doc.metadata["source_path"] == str(pdf_path.resolve())
        assert doc.metadata["doc_type"] == "pdf"
        assert doc.metadata["parse_backend"] == "markitdown+pymupdf"
        assert doc.metadata["title"]
        assert len(doc.metadata["sha256"]) == 64
        assert doc.text.lstrip().startswith("#")
    finally:
        _cleanup_dir(image_root)


def test_pdf_loader_end_to_end_with_images() -> None:
    """
    Given:
        真实 `with_images.pdf` 文件，且环境中存在 MarkItDown + PyMuPDF 依赖。

    When:
        调用 `PdfLoader.load()` 执行真实端到端流程（文本转换、图片提取、占位符插入）。

    Then:
        - 至少提取出 1 张图片并成功落盘；
        - `Document.text` 出现对应图片占位符；
        - 占位符 offset/length 与实际文本位置一致。
    """
    pdf_path = FIXTURE_DIR / "with_images.pdf"
    image_root = _new_image_root()
    loader = PdfLoader(image_root=str(image_root))

    try:
        doc = loader.load(str(pdf_path))
        pprint(doc)
        images = doc.metadata.get("images")

        assert isinstance(images, list)
        assert len(images) >= 1

        for image in images:
            image_id = image["id"]
            placeholder = f"[IMAGE: {image_id}]"
            image_path = Path(image["path"])

            assert image_path.exists()
            assert image_root.as_posix() in image_path.as_posix()
            assert placeholder in doc.text
            assert doc.text.find(placeholder) == image["text_offset"]
            assert image["text_length"] == len(placeholder)
    finally:
        _cleanup_dir(image_root)
