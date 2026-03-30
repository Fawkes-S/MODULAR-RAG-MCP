"""ChunkRefiner 单元测试（C5）。"""

from __future__ import annotations

import json
import shutil
import sys
import uuid
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
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
    ChunkRefinerSettings,
)
from core.trace.trace_context import TraceContext
from core.types import Chunk
from ingestion.transform.chunk_refiner import ChunkRefiner
from libs.llm.base_llm import BaseLLM


class _FakeLLM(BaseLLM):
    """可控 FakeLLM：支持返回固定文本或抛出异常。"""

    def __init__(self, response: str = "LLM refined", error: Exception | None = None) -> None:
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
        ingestion=IngestionSettings(chunk_refiner=ChunkRefinerSettings(use_llm=use_llm)),
    )


def _make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        metadata={"source_path": "memory://chunk.md", "doc_type": "md"},
        start_offset=0,
        end_offset=max(len(text), 0),
        source_ref="doc_x",
    )


_NOISY_CASES = json.loads((PROJECT_ROOT / "tests" / "fixtures" / "noisy_chunks.json").read_text(encoding="utf-8-sig"))["cases"]


@pytest.mark.parametrize("case", _NOISY_CASES, ids=[case["name"] for case in _NOISY_CASES])
def test_rule_refine_fixtures_remove_expected_noise(case: dict[str, Any]) -> None:
    """
    Given:
        噪声样例 fixture（覆盖 8 种典型场景）。

    When:
        调用 `_rule_based_refine()` 执行规则清洗。

    Then:
        应保留必要内容，并移除该场景定义的噪声片段。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))
    refined = refiner._rule_based_refine(case["input"])

    for expected in case["expected_contains"]:
        assert expected in refined

    for banned in case["expected_not_contains"]:
        assert banned not in refined


def test_rule_refine_preserves_code_block_body() -> None:
    """
    Given:
        含 fenced code block 与页脚噪声的文本。

    When:
        执行规则清洗。

    Then:
        代码块内容与缩进应保留，页脚噪声应被移除。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))
    raw = "```python\nfor i in range(2):\n    print(i)\n```\n\nPage 1 of 1"

    refined = refiner._rule_based_refine(raw)

    assert "for i in range(2):" in refined
    assert "    print(i)" in refined
    assert "Page 1 of 1" not in refined


def test_rule_refine_keeps_clean_text_semantics() -> None:
    """
    Given:
        基本干净、只含轻微空白不规则的文本。

    When:
        执行规则清洗。

    Then:
        核心语义句子应完整保留，不发生过度清理。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))
    raw = "# Title\n\nThis   is   already   meaningful."

    refined = refiner._rule_based_refine(raw)

    assert "# Title" in refined
    assert "This is already meaningful." in refined


def test_rule_refine_collapses_excessive_blank_lines() -> None:
    """
    Given:
        含连续多空行的文本。

    When:
        执行规则清洗。

    Then:
        连续空行应被压缩，避免 chunk 内部出现冗余空白。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))
    raw = "A\n\n\n\nB"

    refined = refiner._rule_based_refine(raw)

    assert "\n\n\n" not in refined


def test_rule_refine_removes_html_comments() -> None:
    """
    Given:
        含 HTML 注释与正文的文本。

    When:
        执行规则清洗。

    Then:
        注释应被移除，正文应保留。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    refined = refiner._rule_based_refine("<!-- hidden -->\nBody text")

    assert "hidden" not in refined
    assert "Body text" in refined


def test_rule_refine_removes_page_footer() -> None:
    """
    Given:
        含页码页脚的文本。

    When:
        执行规则清洗。

    Then:
        页脚噪声应被清理。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    refined = refiner._rule_based_refine("Page 10 of 20\n\n正文")

    assert "Page 10 of 20" not in refined
    assert "正文" in refined


def test_rule_refine_removes_separator_lines() -> None:
    """
    Given:
        含分隔线噪声的文本。

    When:
        执行规则清洗。

    Then:
        分隔线应被移除，内容行保留。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    refined = refiner._rule_based_refine("----\n内容A\n====")

    assert "----" not in refined
    assert "====" not in refined
    assert "内容A" in refined


def test_transform_uses_rule_when_use_llm_disabled() -> None:
    """
    Given:
        配置 `use_llm=false`，并提供一个普通 chunk。

    When:
        执行 `transform()`。

    Then:
        输出应标记 `refined_by=rule`，且写入禁用原因。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False), llm=_FakeLLM())
    out = refiner.transform([_make_chunk("c1", "Line A")])

    assert out[0].metadata["refined_by"] == "rule"
    assert out[0].metadata["refine_fallback_reason"] == "llm_disabled_by_settings"


def test_transform_uses_llm_when_enabled_and_available() -> None:
    """
    Given:
        配置 `use_llm=true`，并注入可用 FakeLLM。

    When:
        执行 `transform()`。

    Then:
        输出应采用 LLM 文本，并标记 `refined_by=llm`。
    """
    llm = _FakeLLM(response="LLM cleaned result")
    refiner = ChunkRefiner(settings=_make_settings(use_llm=True), llm=llm)

    out = refiner.transform([_make_chunk("c1", "raw text")])

    assert out[0].text == "LLM cleaned result"
    assert out[0].metadata["refined_by"] == "llm"
    assert llm.calls


def test_transform_falls_back_when_llm_returns_empty() -> None:
    """
    Given:
        开启 LLM，但 FakeLLM 返回空字符串。

    When:
        执行 `transform()`。

    Then:
        应回退规则结果并标记 `llm_empty_response`。
    """
    llm = _FakeLLM(response="   ")
    refiner = ChunkRefiner(settings=_make_settings(use_llm=True), llm=llm)

    out = refiner.transform([_make_chunk("c1", "Page 1 of 1\n\nHello")])

    assert out[0].metadata["refined_by"] == "rule"
    assert out[0].metadata["refine_fallback_reason"] == "llm_empty_response"
    assert "Page 1 of 1" not in out[0].text


def test_transform_falls_back_on_llm_exception() -> None:
    """
    Given:
        开启 LLM，FakeLLM 抛出运行时异常。

    When:
        执行 `transform()`。

    Then:
        应降级到规则结果并携带异常类型原因。
    """
    llm = _FakeLLM(error=RuntimeError("network down"))
    refiner = ChunkRefiner(settings=_make_settings(use_llm=True), llm=llm)

    out = refiner.transform([_make_chunk("c1", "input text")])

    assert out[0].metadata["refined_by"] == "rule"
    assert out[0].metadata["refine_fallback_reason"].startswith("llm_error:RuntimeError")


def test_transform_records_fallback_reason_from_init_error() -> None:
    """
    Given:
        开启 LLM 但不提供可用 `llm.provider` 配置，导致初始化失败。

    When:
        执行 `transform()`。

    Then:
        应回退规则模式，并记录 `llm_client_init_error`。
    """
    bad_settings = _make_settings(use_llm=True, llm_provider="")
    refiner = ChunkRefiner(settings=bad_settings)

    out = refiner.transform([_make_chunk("c1", "input")])

    assert out[0].metadata["refined_by"] == "rule"
    assert out[0].metadata["refine_fallback_reason"].startswith("llm_client_init_error")


def test_transform_isolates_chunk_level_exceptions(monkeypatch) -> None:
    """
    Given:
        两个 chunk，其中第一个在规则清洗阶段抛异常。

    When:
        执行 `transform()`。

    Then:
        第一个 chunk 回退原文，第二个 chunk 仍正常处理。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    original = refiner._rule_based_refine

    def _broken(text: str) -> str:
        if "boom" in text:
            raise RuntimeError("boom")
        return original(text)

    monkeypatch.setattr(refiner, "_rule_based_refine", _broken)

    chunks = [_make_chunk("c1", "boom text"), _make_chunk("c2", "Page 1 of 1\nOK")]
    out = refiner.transform(chunks)

    assert out[0].text == "boom text"
    assert out[0].metadata["refined_by"] == "rule"
    assert out[1].text == "OK"


def test_transform_preserves_chunk_identity_fields() -> None:
    """
    Given:
        一个带固定 id/offset/source_ref 的 chunk。

    When:
        执行 `transform()`。

    Then:
        id、offset、source_ref 应保持不变，满足契约稳定性。
    """
    chunk = Chunk(
        id="chunk_x",
        text="Page 1 of 1\nHello",
        metadata={"source_path": "memory://x", "doc_type": "md"},
        start_offset=12,
        end_offset=99,
        source_ref="doc_abc",
    )
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    out = refiner.transform([chunk])[0]

    assert out.id == "chunk_x"
    assert out.start_offset == 12
    assert out.end_offset == 99
    assert out.source_ref == "doc_abc"


def test_transform_accepts_empty_chunks() -> None:
    """
    Given:
        空 chunk 列表。

    When:
        执行 `transform()`。

    Then:
        应返回空列表，不抛异常。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    out = refiner.transform([])

    assert out == []


def test_transform_rejects_non_list_input() -> None:
    """
    Given:
        非 list 的输入对象。

    When:
        执行 `transform()`。

    Then:
        应抛 ValueError，阻止非法输入进入处理链路。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    with pytest.raises(ValueError, match="chunks must be list"):
        refiner.transform("not-a-list")  # type: ignore[arg-type]


def test_transform_rejects_non_chunk_items() -> None:
    """
    Given:
        list 中混入非 Chunk 元素。

    When:
        执行 `transform()`。

    Then:
        应抛 ValueError 并指出非法元素位置。
    """
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    with pytest.raises(ValueError, match="chunks\\[0\\] must be Chunk"):
        refiner.transform([{"id": "x"}])  # type: ignore[list-item]


def test_load_prompt_reads_custom_file_and_injects_placeholder() -> None:
    """
    Given:
        自定义 prompt 文件且缺少 `{text}` 占位符。

    When:
        初始化 `ChunkRefiner(prompt_path=...)`。

    Then:
        应自动补齐 `{text}`，保证后续格式化不会失败。
    """
    workdir = PROJECT_ROOT / f"pytest-cache-files-prompt-{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    prompt_file = workdir / "custom_prompt.txt"

    try:
        prompt_file.write_text("请清理输入文本", encoding="utf-8")
        refiner = ChunkRefiner(settings=_make_settings(use_llm=False), prompt_path=prompt_file)

        assert "请清理输入文本" in refiner.prompt_template
        assert "{text}" in refiner.prompt_template
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_load_prompt_uses_default_when_file_missing() -> None:
    """
    Given:
        指向不存在的 prompt 文件路径。

    When:
        初始化 `ChunkRefiner`。

    Then:
        应回退内置默认模板，且模板包含 `{text}`。
    """
    workdir = PROJECT_ROOT / f"pytest-cache-files-prompt-{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    missing = workdir / "missing_prompt.txt"

    try:
        refiner = ChunkRefiner(settings=_make_settings(use_llm=False), prompt_path=missing)
        assert "{text}" in refiner.prompt_template
        assert "原文" in refiner.prompt_template
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_transform_records_trace_stage() -> None:
    """
    Given:
        一个 TraceContext 与一个待处理 chunk。

    When:
        执行 `transform(chunks, trace=...)`。

    Then:
        trace 中应新增 `transform.chunk_refiner` 阶段记录，并包含统计字段。
    """
    trace = TraceContext(trace_type="ingestion")
    refiner = ChunkRefiner(settings=_make_settings(use_llm=False))

    refiner.transform([_make_chunk("c1", "Page 1 of 1\n\nBody")], trace=trace)

    assert trace.stages
    stage = trace.stages[-1]
    assert stage["stage_name"] == "transform.chunk_refiner"
    assert "details" in stage
    assert stage["details"]["total"] == 1





