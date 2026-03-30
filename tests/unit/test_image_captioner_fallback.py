"""ImageCaptioner 回退与契约测试（C7）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import (  # noqa: E402
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
    VisionLLMSettings,
)
from core.trace.trace_context import TraceContext  # noqa: E402
from core.types import Chunk  # noqa: E402
from ingestion.transform.image_captioner import ImageCaptioner  # noqa: E402
from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse  # noqa: E402

FIXTURE_IMAGE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents" / "test_vision_llm.jpg"


class _FakeVisionLLM(BaseVisionLLM):
    """可控 VisionLLM 假实现：支持固定返回或抛异常。"""

    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def chat_with_image(
        self,
        text: str,
        image_path: str | bytes,
        trace: Any | None = None,
    ) -> ChatResponse:
        self.calls.append({"text": text, "image_path": image_path, "trace": trace})
        if self.error is not None:
            raise self.error
        return ChatResponse(content=self.response, metadata={"provider": "fake"})


def _make_settings(vision_enabled: bool, *, provider: str = "dashscope") -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=5, sparse_top_k=10),
        rerank=RerankSettings(provider="none", enabled=False, top_m=10),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        vision_llm=VisionLLMSettings(enabled=vision_enabled, provider=provider, model="qwen-vl"),
        ingestion=IngestionSettings(),
    )


def _make_chunk(chunk_id: str, text: str, *, image_refs: list[str]) -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        metadata={
            "source_path": "memory://with_image.md",
            "doc_type": "md",
            "image_refs": list(image_refs),
            "images": [
                {
                    "id": "img_a",
                    "path": str(FIXTURE_IMAGE_PATH),
                    "page": 1,
                }
            ],
        },
        start_offset=0,
        end_offset=max(len(text), 0),
        source_ref="doc_with_image",
    )


def test_enabled_mode_generates_caption_and_writes_metadata() -> None:
    """
    Given:
        Vision LLM 开启，且 chunk 存在 `image_refs` 与可用图片路径。
    When:
        调用 `ImageCaptioner.transform()`。
    Then:
        应调用 Vision LLM 生成 caption，写入 `metadata.image_captions`，并把描述注入正文。
    """
    fake_vision = _FakeVisionLLM(response="图中展示系统三层结构与数据流向。")
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=True), vision_llm=fake_vision)

    out = captioner.transform([
        _make_chunk("c1", "系统架构如下 [IMAGE: img_a]，请重点阅读。", image_refs=["img_a"])
    ])[0]

    assert len(fake_vision.calls) == 1
    assert out.metadata["image_refs"] == ["img_a"]
    assert out.metadata["captioned_by"] == "vision_llm"
    assert out.metadata["image_captions"]["img_a"] == "图中展示系统三层结构与数据流向。"
    assert "has_unprocessed_images" not in out.metadata
    assert "[图片描述: 图中展示系统三层结构与数据流向。]" in out.text


def test_fallback_mode_when_vision_disabled_marks_unprocessed_images() -> None:
    """
    Given:
        配置中 `vision_llm.enabled=false`，且 chunk 中有图片引用。
    When:
        调用 `transform()`。
    Then:
        不应调用 Vision LLM，chunk 保留 `image_refs`，并标记 `has_unprocessed_images=true`。
    """
    fake_vision = _FakeVisionLLM(response="不会被使用")
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=False), vision_llm=fake_vision)

    out = captioner.transform([
        _make_chunk("c2", "这里有图 [IMAGE: img_a]。", image_refs=["img_a"])
    ])[0]

    assert fake_vision.calls == []
    assert out.metadata["image_refs"] == ["img_a"]
    assert out.metadata["has_unprocessed_images"] is True
    assert out.metadata["captioned_by"] == "rule"
    assert out.metadata["caption_fallback_reason"] == "vision_llm_disabled_by_settings"
    assert "image_captions" not in out.metadata


def test_fallback_mode_when_vision_raises_error_does_not_block_ingestion() -> None:
    """
    Given:
        Vision LLM 开启，但调用时抛出运行时异常。
    When:
        调用 `transform()`。
    Then:
        应走降级路径，不抛致命异常，并记录 `caption_fallback_reason`。
    """
    fake_vision = _FakeVisionLLM(error=RuntimeError("gateway timeout"))
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=True), vision_llm=fake_vision)

    out = captioner.transform([
        _make_chunk("c3", "流程图见 [IMAGE: img_a]。", image_refs=["img_a"])
    ])[0]

    assert len(fake_vision.calls) == 1
    assert out.metadata["has_unprocessed_images"] is True
    assert out.metadata["captioned_by"] == "rule"
    assert out.metadata["caption_fallback_reason"].startswith("vision_llm_error:RuntimeError")
    assert "image_captions" not in out.metadata


def test_transform_preserves_chunk_identity_fields() -> None:
    """
    Given:
        一个带固定 `id/start_offset/end_offset/source_ref` 的 chunk。
    When:
        执行 `transform()`。
    Then:
        身份字段必须保持不变，仅允许 text/metadata 发生增强变化。
    """
    fake_vision = _FakeVisionLLM(response="架构图包含入口、服务层和存储层。")
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=True), vision_llm=fake_vision)

    chunk = Chunk(
        id="chunk_identity",
        text="见图 [IMAGE: img_a]",
        metadata={
            "source_path": "memory://id.md",
            "doc_type": "md",
            "image_refs": ["img_a"],
            "images": [{"id": "img_a", "path": str(FIXTURE_IMAGE_PATH)}],
        },
        start_offset=12,
        end_offset=66,
        source_ref="doc_identity",
    )

    out = captioner.transform([chunk])[0]

    assert out.id == "chunk_identity"
    assert out.start_offset == 12
    assert out.end_offset == 66
    assert out.source_ref == "doc_identity"


def test_transform_records_trace_stage_details() -> None:
    """
    Given:
        一条包含图片引用的 chunk 和 TraceContext。
    When:
        调用 `transform(chunks, trace=...)`。
    Then:
        trace 末尾应写入 `transform.image_captioner` 阶段，包含统计字段。
    """
    fake_vision = _FakeVisionLLM(response="图表展示季度增长趋势。")
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=True), vision_llm=fake_vision)
    trace = TraceContext(trace_type="ingestion")

    captioner.transform([_make_chunk("c4", "趋势如图 [IMAGE: img_a]", image_refs=["img_a"])], trace=trace)

    assert trace.stages
    stage = trace.stages[-1]
    assert stage["stage_name"] == "transform.image_captioner"
    assert stage["details"]["total"] == 1
    assert stage["details"]["chunks_with_images"] == 1
    assert "elapsed_ms" in stage


def test_transform_is_idempotent_when_caption_already_exists() -> None:
    """
    Given:
        同一 chunk 连续执行两次 captioning，第二次输入已包含 image_captions。
    When:
        重复调用 `transform()`。
    Then:
        第二次不应重复调用 Vision LLM，正文中的图片描述块也不应重复追加。
    """
    fake_vision = _FakeVisionLLM(response="图中展示系统三层结构与数据流向。")
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=True), vision_llm=fake_vision)

    first = captioner.transform([
        _make_chunk("c5", "系统架构如下 [IMAGE: img_a]。", image_refs=["img_a"])
    ])[0]
    second = captioner.transform([first])[0]

    assert len(fake_vision.calls) == 1
    assert second.text.count("[图片描述:") == 1
    assert second.metadata["image_captions"]["img_a"] == "图中展示系统三层结构与数据流向。"


def test_transform_rejects_non_list_input() -> None:
    """
    Given:
        非 `list[Chunk]` 的非法输入。
    When:
        调用 `transform()`。
    Then:
        应抛出 ValueError，阻止错误 shape 进入流水线。
    """
    captioner = ImageCaptioner(settings=_make_settings(vision_enabled=False))

    with pytest.raises(ValueError, match="chunks must be list"):
        captioner.transform("not-a-list")  # type: ignore[arg-type]
