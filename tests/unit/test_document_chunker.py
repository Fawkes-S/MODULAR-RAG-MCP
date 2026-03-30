"""DocumentChunker 单元测试（C4）。"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from pprint import pprint
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import (
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
    load_settings,
)
from core.types import Chunk, Document
from ingestion.chunking.document_chunker import DocumentChunker
from libs.loader.pdf_loader import PdfLoader
from libs.splitter.base_splitter import BaseSplitter
from libs.splitter.splitter_factory import SplitterFactory

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents"


class _StaticFakeSplitter(BaseSplitter):
    """返回预定义切分结果的 FakeSplitter。"""

    def __init__(self, chunks: list[str] | None = None, **_: Any) -> None:
        # 注意：这里刻意区分 None 与 []，以便测试可覆盖“返回空列表”场景。
        self._chunks = ["第一段", "第二段"] if chunks is None else list(chunks)

    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        return list(self._chunks)


class _EmptyFakeSplitter(BaseSplitter):
    """始终返回空列表，用于验证空切分结果分支。"""

    def __init__(self, **_: Any) -> None:
        pass

    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        return []


class _WindowFakeSplitter(BaseSplitter):
    """按固定窗口切分，便于验证 chunk_size 配置是否生效。"""

    def __init__(self, chunk_size: int = 10, chunk_overlap: int = 0, **_: Any) -> None:
        self.chunk_size = int(chunk_size)
        self.chunk_overlap = int(chunk_overlap)

    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += step
        return chunks


def _new_image_root() -> Path:
    """为真实 PDF 测试创建独立图片目录，避免与其他测试互相污染。"""
    path = PROJECT_ROOT / "data" / "images" / f"test_chunker_real_pdf_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup_dir(path: Path) -> None:
    """清理真实 PDF 测试产生的临时目录。"""
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def _build_settings(ingestion_overrides: dict[str, Any]) -> Settings:
    """构造测试用 Settings，仅覆写 ingestion 段。"""
    base = IngestionSettings()
    chunk_refiner_cfg = ingestion_overrides.get("chunk_refiner")
    metadata_enricher_cfg = ingestion_overrides.get("metadata_enricher")

    return Settings(
        llm=LLMSettings(provider="openai", model="qwen3.5-plus"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=8, sparse_top_k=20),
        rerank=RerankSettings(provider="none", enabled=False, top_m=30),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(
            splitter=str(ingestion_overrides.get("splitter", base.splitter)),
            chunk_size=int(ingestion_overrides.get("chunk_size", base.chunk_size)),
            chunk_overlap=int(ingestion_overrides.get("chunk_overlap", base.chunk_overlap)),
            separators=list(ingestion_overrides.get("separators", base.separators)),
            splitter_kwargs=dict(ingestion_overrides.get("splitter_kwargs", base.splitter_kwargs)),
            batch_size=int(ingestion_overrides.get("batch_size", base.batch_size)),
            chunk_refiner=base.chunk_refiner if not isinstance(chunk_refiner_cfg, dict) else base.chunk_refiner.__class__(
                use_llm=bool(chunk_refiner_cfg.get("use_llm", base.chunk_refiner.use_llm)),
                prompt_path=str(chunk_refiner_cfg.get("prompt_path", base.chunk_refiner.prompt_path)),
            ),
            metadata_enricher=base.metadata_enricher if not isinstance(metadata_enricher_cfg, dict) else base.metadata_enricher.__class__(
                use_llm=bool(metadata_enricher_cfg.get("use_llm", base.metadata_enricher.use_llm)),
            ),
        ),
    )

def _load_current_settings() -> Settings:
    """读取当前 settings.yaml，保持测试与项目实际配置一致。"""
    return load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

@pytest.fixture()
def isolated_registry() -> None:
    """隔离 SplitterFactory 全局注册表，避免测试互相污染。"""
    snapshot_registry = dict(SplitterFactory._registry)
    snapshot_builtin = SplitterFactory._builtin_loaded

    SplitterFactory._registry.clear()
    SplitterFactory._builtin_loaded = False
    try:
        yield
    finally:
        SplitterFactory._registry.clear()
        SplitterFactory._registry.update(snapshot_registry)
        SplitterFactory._builtin_loaded = snapshot_builtin


def test_split_document_generates_stable_unique_ids_and_source_refs(isolated_registry: None) -> None:
    """
    Given:
        注册一个静态 FakeSplitter，输入同一个 Document 进行两次切分。

    When:
        调用 `DocumentChunker.split_document()` 两次得到 Chunk 序列。

    Then:
        - 每个 Chunk 的 ID 在文档内唯一；
        - 同一文档重复切分时，ID 序列保持确定性；
        - 所有 Chunk.source_ref 均指向父 Document.id；
        - metadata 继承了文档字段并追加 chunk_index。
    """
    SplitterFactory.register("fake_static", _StaticFakeSplitter)
    settings = _build_settings({
        "splitter": "fake_static",
        "splitter_kwargs": {"chunks": ["第一段", "第二段"]},
    })

    document = Document(
        id="doc_alpha",
        text="第一段\n\n第二段",
        metadata={
            "source_path": "tests/fixtures/sample_documents/simple.pdf",
            "doc_type": "pdf",
            "title": "示例文档",
        },
    )

    chunker = DocumentChunker(settings)
    chunks_a = chunker.split_document(document)
    chunks_b = chunker.split_document(document)

    ids_a = [chunk.id for chunk in chunks_a]
    ids_b = [chunk.id for chunk in chunks_b]

    assert len(ids_a) == len(set(ids_a))
    assert ids_a == ids_b

    for idx, chunk in enumerate(chunks_a):
        assert isinstance(chunk, Chunk)
        assert chunk.source_ref == document.id
        assert chunk.metadata["source_path"] == document.metadata["source_path"]
        assert chunk.metadata["doc_type"] == "pdf"
        assert chunk.metadata["title"] == "示例文档"
        assert chunk.metadata["chunk_index"] == idx


def test_split_document_distributes_images_by_placeholder_subset(isolated_registry: None) -> None:
    """
    Given:
        文档级 metadata 含多张图片，FakeSplitter 返回 3 个 chunk，分别引用不同 `[IMAGE: id]`。

    When:
        调用 `split_document()` 执行图片引用按需分发。

    Then:
        - 含占位符的 chunk 仅保留本 chunk 实际引用的 `images` 子集；
        - 不含占位符的 chunk 不包含 `images` 字段；
        - `image_refs` 顺序与占位符出现顺序一致。
    """
    fake_chunks = [
        "第一段 [IMAGE: img_a]",
        "第二段无图",
        "第三段 [IMAGE: img_b] 与 [IMAGE: img_a]",
    ]
    SplitterFactory.register("fake_static", _StaticFakeSplitter)
    settings = _build_settings({
        "splitter": "fake_static",
        "splitter_kwargs": {"chunks": fake_chunks},
    })

    document = Document(
        id="doc_images",
        text="\n\n".join(fake_chunks),
        metadata={
            "source_path": "tests/fixtures/sample_documents/with_images.pdf",
            "doc_type": "pdf",
            "images": [
                {"id": "img_a", "path": "data/images/img_a.png", "page": 1, "text_offset": 0, "text_length": 0, "position": {}},
                {"id": "img_b", "path": "data/images/img_b.png", "page": 2, "text_offset": 0, "text_length": 0, "position": {}},
                {"id": "img_unused", "path": "data/images/img_unused.png", "page": 2, "text_offset": 0, "text_length": 0, "position": {}},
            ],
        },
    )

    chunks = DocumentChunker(settings).split_document(document)

    assert chunks[0].metadata["image_refs"] == ["img_a"]
    assert [img["id"] for img in chunks[0].metadata["images"]] == ["img_a"]

    assert chunks[1].metadata["image_refs"] == []
    assert "images" not in chunks[1].metadata

    assert chunks[2].metadata["image_refs"] == ["img_b", "img_a"]
    assert [img["id"] for img in chunks[2].metadata["images"]] == ["img_b", "img_a"]
    assert "img_unused" not in [img["id"] for img in chunks[2].metadata["images"]]


def test_split_document_uses_ingestion_config_to_change_chunk_shape(isolated_registry: None) -> None:
    """
    Given:
        同一份文档，分别使用不同 `ingestion.chunk_size` 的配置初始化 DocumentChunker。

    When:
        调用 `split_document()` 生成 Chunk 列表。

    Then:
        较小 chunk_size 产生更多 chunk，且每个 chunk 文本长度受对应配置约束，
        证明切分行为由 settings 配置驱动。
    """
    SplitterFactory.register("fake_window", _WindowFakeSplitter)

    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    document = Document(
        id="doc_cfg",
        text=text,
        metadata={"source_path": "memory://cfg.md", "doc_type": "md"},
    )

    small_settings = _build_settings({"splitter": "fake_window", "chunk_size": 6, "chunk_overlap": 0})
    large_settings = _build_settings({"splitter": "fake_window", "chunk_size": 18, "chunk_overlap": 0})

    small_chunks = DocumentChunker(small_settings).split_document(document)
    large_chunks = DocumentChunker(large_settings).split_document(document)

    assert len(small_chunks) > len(large_chunks)
    assert max(len(chunk.text) for chunk in small_chunks) <= 6
    assert max(len(chunk.text) for chunk in large_chunks) <= 18


def test_split_document_rejects_empty_document_text(isolated_registry: None) -> None:
    """
    Given:
        文档文本为空白字符串。

    When:
        调用 `split_document()`。

    Then:
        抛出 ValueError，避免无意义切分进入后续流程。
    """
    SplitterFactory.register("fake_static", _StaticFakeSplitter)
    chunker = DocumentChunker(_build_settings({"splitter": "fake_static"}))

    document = Document(
        id="doc_empty",
        text="   ",
        metadata={"source_path": "memory://empty.md", "doc_type": "md"},
    )

    with pytest.raises(ValueError, match="has no text content"):
        chunker.split_document(document)


def test_split_document_raises_when_splitter_returns_empty(isolated_registry: None) -> None:
    """
    Given:
        splitter 返回空 chunk 列表。

    When:
        调用 `split_document()`。

    Then:
        抛出 ValueError，明确提示切分结果为空。
    """
    SplitterFactory.register("fake_empty", _EmptyFakeSplitter)
    chunker = DocumentChunker(_build_settings({"splitter": "fake_empty"}))

    document = Document(
        id="doc_no_chunks",
        text="有内容但 splitter 返回空",
        metadata={"source_path": "memory://nochunks.md", "doc_type": "md"},
    )

    with pytest.raises(ValueError, match="returned no chunks"):
        chunker.split_document(document)


def test_split_document_real_pdf_with_current_ingestion_settings() -> None:
    """
    Given:
        真实 `with_images.pdf` 文件，以及 `config/settings.yaml` 中当前生效的 `ingestion.*` 配置。

    When:
        先用 `PdfLoader.load()` 读取真实 PDF 得到 Document，再交给 `DocumentChunker.split_document()` 切分。

    Then:
        - 能生成非空 Chunk 列表，且每个 Chunk 都满足核心契约字段；
        - Chunk 的 `source_ref` 正确指向父文档，`chunk_index` 连续递增；
        - 若文档含图片占位符，至少一个 Chunk 会携带对应 `image_refs`；
        - 可序列化为稳定字典结构，便于后续入库与检索链路使用。
    """
    pytest.importorskip("markitdown")
    pytest.importorskip("fitz")
    pytest.importorskip("langchain_text_splitters")

    pdf_path = FIXTURE_DIR / "blogger_intro.pdf"
    image_root = _new_image_root()
    loader = PdfLoader(image_root=str(image_root))
    settings = _load_current_settings()

    try:
        document = loader.load(str(pdf_path))
        pprint(document)
        print("=" * 100)
        chunks = DocumentChunker(settings).split_document(document)
        pprint(chunks)

        assert chunks
        for index, chunk in enumerate(chunks):
            assert isinstance(chunk, Chunk)
            assert chunk.id
            assert chunk.text.strip()
            assert chunk.source_ref == document.id
            assert chunk.metadata["chunk_index"] == index
            assert chunk.metadata["source_path"] == document.metadata["source_path"]
            assert chunk.start_offset >= 0
            assert chunk.end_offset >= chunk.start_offset

        if isinstance(document.metadata.get("images"), list) and document.metadata["images"]:
            image_ids = {
                str(img["id"])
                for img in document.metadata["images"]
                if isinstance(img, dict) and "id" in img
            }
            refs = {ref for chunk in chunks for ref in chunk.metadata.get("image_refs", [])}
            assert refs.intersection(image_ids)

        serialized = [chunk.to_dict() for chunk in chunks]
        required_keys = {"id", "text", "metadata", "start_offset", "end_offset", "source_ref"}
        assert all(required_keys <= set(item.keys()) for item in serialized)
    finally:
        _cleanup_dir(image_root)

def test_split_document_output_matches_chunk_contract(isolated_registry: None) -> None:
    """
    Given:
        FakeSplitter 返回确定的文本片段。

    When:
        调用 `split_document()` 并序列化每个 Chunk。

    Then:
        所有输出都满足 `core.types.Chunk` 契约：
        可序列化、字段完整、offset 有效且 `end_offset >= start_offset`。
    """
    SplitterFactory.register("fake_static", _StaticFakeSplitter)
    settings = _build_settings({"splitter": "fake_static", "splitter_kwargs": {"chunks": ["甲", "乙"]}})

    document = Document(
        id="doc_contract",
        text="甲\n乙",
        metadata={"source_path": "memory://contract.md", "doc_type": "md"},
    )

    chunks = DocumentChunker(settings).split_document(document)

    assert len(chunks) == 2
    for chunk in chunks:
        payload = chunk.to_dict()
        assert payload["id"]
        assert payload["metadata"]["source_path"] == "memory://contract.md"
        assert payload["start_offset"] >= 0
        assert payload["end_offset"] >= payload["start_offset"]
        restored = Chunk.from_dict(payload)
        assert restored.id == chunk.id
        assert restored.text == chunk.text

