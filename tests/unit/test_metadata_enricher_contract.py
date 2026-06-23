"""MetadataEnricher 合约测试（C6）。"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path
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
    MetadataEnricherSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
    load_settings,
)
from core.trace.trace_context import TraceContext
from core.types import Chunk
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.llm.base_llm import BaseLLM


class _FakeLLM(BaseLLM):
    """可控 FakeLLM：支持固定返回或抛异常。"""

    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[list[dict[str, Any]]] = []

    def chat(self, messages: list[dict[str, Any]]) -> str:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.response


def _make_settings(use_llm: bool, *, llm_provider: str = "openai") -> Settings:
    return Settings(
        llm=LLMSettings(provider=llm_provider, model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=5, sparse_top_k=10),
        rerank=RerankSettings(provider="none", enabled=False, top_m=10),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(
            metadata_enricher=MetadataEnricherSettings(use_llm=use_llm),
        ),
    )


def _make_chunk(chunk_id: str, text: str, source_path: str = "memory://policy.md") -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        metadata={"source_path": source_path, "doc_type": "pdf"},
        start_offset=0,
        end_offset=max(len(text), 0),
        source_ref="doc_unit",
    )


def test_rule_mode_always_outputs_required_metadata() -> None:
    """
    Given:
        `use_llm=false` 且输入为普通正文 chunk。
    When:
        执行 `MetadataEnricher.transform()`。
    Then:
        输出 metadata 必须包含非空 `title/summary/tags`，并标记规则模式降级原因。
    """
    enricher = MetadataEnricher(settings=_make_settings(use_llm=False))

    out = enricher.transform([
        _make_chunk(
            "c1",
            "# Contract Overview\n\nThis section explains ingestion stages and fallback behaviors.",
        )
    ])[0]

    assert out.metadata["title"]
    assert out.metadata["summary"]
    assert isinstance(out.metadata["tags"], list)
    assert out.metadata["tags"]
    assert out.metadata["enriched_by"] == "rule"
    assert out.metadata["enrich_fallback_reason"] == "llm_disabled_by_settings"


def test_rule_mode_uses_source_filename_when_text_is_empty_noise() -> None:
    """
    Given:
        几乎无有效正文的 chunk（仅图片占位符和空白）。
    When:
        执行规则增强。
    Then:
        仍应从 `source_path` 推导标题并生成兜底摘要/标签，满足最小契约。
    """
    enricher = MetadataEnricher(settings=_make_settings(use_llm=False))

    out = enricher.transform([
        _make_chunk("c2", "\n\n[IMAGE: img_001]\n\n", source_path="docs/meeting_notes.pdf")
    ])[0]

    assert out.metadata["title"] == "meeting_notes.pdf"
    assert out.metadata["summary"]
    assert out.metadata["tags"]


def test_llm_mode_uses_llm_output_when_json_is_valid() -> None:
    """
    Given:
        `use_llm=true` 且 LLM 返回合法 JSON（含 title/summary/tags）。
    When:
        执行 metadata 增强。
    Then:
        应采用 LLM 输出并标记 `enriched_by=llm`，且不写入降级原因。
    """
    fake_llm = _FakeLLM(
        response='{"title":"采购流程说明","summary":"描述采购审批与入库流程。","tags":["采购","流程","审批"]}'
    )
    enricher = MetadataEnricher(settings=_make_settings(use_llm=True), llm=fake_llm)

    out = enricher.transform([_make_chunk("c3", "raw text")])[0]

    assert out.metadata["enriched_by"] == "llm"
    assert out.metadata["title"] == "采购流程说明"
    assert out.metadata["summary"] == "描述采购审批与入库流程。"
    assert out.metadata["tags"] == ["采购", "流程", "审批"]
    assert "enrich_fallback_reason" not in out.metadata
    assert fake_llm.calls


def test_llm_mode_parses_json_when_think_tags_wrap_response() -> None:
    """
    Given:
        `use_llm=true` 且 LLM 在最终 JSON 前输出 `<think>...</think>` 推理内容。

    When:
        执行 metadata 增强。

    Then:
        组件应先清洗推理痕迹，再正确解析 JSON，而不是误判为 parse error。
    """
    fake_llm = _FakeLLM(
        response=(
            "<think>internal reasoning</think>\n"
            '{"title":"架构概览","summary":"说明模块边界。","tags":["架构","模块"]}'
        )
    )
    enricher = MetadataEnricher(settings=_make_settings(use_llm=True), llm=fake_llm)

    out = enricher.transform([_make_chunk("c3", "raw text")])[0]

    assert out.metadata["enriched_by"] == "llm"
    assert out.metadata["title"] == "架构概览"
    assert out.metadata["summary"] == "说明模块边界。"
    assert out.metadata["tags"] == ["架构", "模块"]


def test_llm_mode_falls_back_when_response_is_not_json() -> None:
    """
    Given:
        `use_llm=true` 但 LLM 返回不可解析文本（非 JSON）。
    When:
        执行 metadata 增强。
    Then:
        应回退规则增强，且写入 `llm_response_parse_error` 方便排障。
    """
    fake_llm = _FakeLLM(response="I can help but here is plain text, not JSON")
    enricher = MetadataEnricher(settings=_make_settings(use_llm=True), llm=fake_llm)

    out = enricher.transform([_make_chunk("c4", "# A\n\nBody")])[0]

    assert out.metadata["enriched_by"] == "rule"
    assert out.metadata["enrich_fallback_reason"] == "llm_response_parse_error"
    assert out.metadata["title"]
    assert out.metadata["summary"]
    assert out.metadata["tags"]


def test_llm_mode_falls_back_on_runtime_exception() -> None:
    """
    Given:
        `use_llm=true` 且 LLM 调用时抛出运行时异常。
    When:
        执行 metadata 增强。
    Then:
        应回退规则增强并记录异常类型，保证 ingestion 不被阻塞。
    """
    fake_llm = _FakeLLM(error=RuntimeError("network timeout"))
    enricher = MetadataEnricher(settings=_make_settings(use_llm=True), llm=fake_llm)

    out = enricher.transform([_make_chunk("c5", "# Fault\n\nBody")])[0]

    assert out.metadata["enriched_by"] == "rule"
    assert out.metadata["enrich_fallback_reason"].startswith("llm_error:RuntimeError")


def test_transform_preserves_chunk_identity_fields() -> None:
    """
    Given:
        一个带固定 `id/start_offset/end_offset/source_ref` 的 chunk。
    When:
        执行 `transform()`。
    Then:
        身份字段必须保持不变，仅允许 metadata 被增强。
    """
    chunk = Chunk(
        id="chunk_identity",
        text="# T\n\nBody",
        metadata={"source_path": "memory://x.md", "doc_type": "md"},
        start_offset=12,
        end_offset=66,
        source_ref="doc_abc",
    )
    enricher = MetadataEnricher(settings=_make_settings(use_llm=False))

    out = None
    for _ in range(2):
        out = enricher.transform([chunk])[0]
        if out.metadata.get("enriched_by") == "llm":
            break

    assert out is not None

    assert out.id == "chunk_identity"
    assert out.start_offset == 12
    assert out.end_offset == 66
    assert out.source_ref == "doc_abc"


def test_transform_records_trace_stage_details() -> None:
    """
    Given:
        一条可处理 chunk 和一个 TraceContext。
    When:
        调用 `transform(chunks, trace=...)`。
    Then:
        trace 末尾应写入 `transform.metadata_enricher` 阶段，并包含统计字段。
    """
    enricher = MetadataEnricher(settings=_make_settings(use_llm=False))
    trace = TraceContext(trace_type="ingestion")

    enricher.transform([_make_chunk("c6", "# A\n\nB")], trace=trace)

    assert trace.stages
    stage = trace.stages[-1]
    assert stage["stage_name"] == "transform.metadata_enricher"
    assert stage["details"]["total"] == 1
    assert "elapsed_ms" in stage


def test_transform_rejects_non_list_input() -> None:
    """
    Given:
        非 `list[Chunk]` 的非法输入。
    When:
        调用 `transform()`。
    Then:
        应抛出 ValueError，阻止错误 shape 进入流水线。
    """
    enricher = MetadataEnricher(settings=_make_settings(use_llm=False))

    with pytest.raises(ValueError, match="chunks must be list"):
        enricher.transform("not-a-list")  # type: ignore[arg-type]


pytestmark = [pytest.mark.unit]


def _load_project_settings() -> Settings:
    return load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))


def _required_key_name(provider: str) -> str | None:
    mapping = {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "azure": "AZURE_API_KEY",
    }
    return mapping.get(provider)


def _has_real_key(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False

    placeholders = ["your_", "<", ">", "***", "dummy", "example"]
    lowered = text.lower()
    return not any(token in lowered for token in placeholders)


def _ensure_llm_runtime_ready(settings: Settings) -> None:
    provider = settings.llm.provider.strip().lower()
    if not provider:
        pytest.skip("settings.llm.provider 为空，跳过真实 LLM 集成测试")

    if not _has_real_key(settings.llm.api_key):
        required_key = _required_key_name(provider)
        env_key = os.getenv(required_key or "") if required_key else ""
        if not _has_real_key(env_key):
            if required_key:
                pytest.skip(
                    "llm.api_key 为空或占位符，且缺少可用环境变量 "
                    f"{required_key}，跳过真实 LLM 集成测试"
                )
            pytest.skip("llm.api_key 为空或占位符，跳过真实 LLM 集成测试")

    if provider == "azure":
        endpoint = settings.llm.endpoint.strip()
        deployment = (settings.llm.deployment_name or settings.llm.model).strip()
        if not endpoint or not deployment:
            pytest.skip("Azure 配置缺少 endpoint/deployment_name，跳过真实 LLM 集成测试")

@pytest.mark.integration
@pytest.mark.llm
def test_metadata_enricher_real_llm_connectivity_and_quality() -> None:
    """
    Given:
        可用的真实 LLM 配置，且 `metadata_enricher.use_llm=true`。
    When:
        执行 `MetadataEnricher.transform()` 对真实文本做增强。
    Then:
        应完成真实 LLM 调用并输出语义化 metadata（title/summary/tags 非空且有信息量）。
        若出现 `llm_error`，应直接判定失败，不再以 skip 掩盖连通性问题。
    """
    settings = _load_project_settings()
    settings = replace(
        settings,
        llm=replace(settings.llm, timeout=60.0),
        ingestion=replace(
            settings.ingestion,
            metadata_enricher=replace(settings.ingestion.metadata_enricher, use_llm=True),
        ),
    )
    _ensure_llm_runtime_ready(settings)

    enricher = MetadataEnricher(settings=settings)
    chunk = _make_chunk(
        "c_real",
        """
# 多模态检索管线设计

本文档说明了摄取阶段的关键步骤：
1) 先用规则和 LLM 对 chunk 进行清洗与摘要；
2) 再提取 tags 以支持过滤与聚类；
3) 最后进入 embedding 与 upsert。
""".strip(),
    )

    # 真实 LLM 用例只调用一次：重试策略已下沉到 LLM provider 内部。
    out = enricher.transform([chunk])[0]

    if out.metadata.get("enriched_by") != "llm":
        reason = str(out.metadata.get("enrich_fallback_reason", "unknown"))
        if reason.startswith("llm_error:"):
            pytest.fail(f"真实 LLM 调用失败（{reason}），本用例应视为失败而不是跳过")
        pytest.fail(f"真实 LLM 未产生 llm 增强结果（fallback_reason={reason}）")

    assert out.metadata.get("enriched_by") == "llm"
    assert isinstance(out.metadata.get("title"), str) and len(out.metadata["title"].strip()) >= 4
    assert isinstance(out.metadata.get("summary"), str) and len(out.metadata["summary"].strip()) >= 12
    assert isinstance(out.metadata.get("tags"), list) and len(out.metadata["tags"]) >= 2
