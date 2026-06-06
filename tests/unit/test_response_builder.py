"""ResponseBuilder / CitationGenerator 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.response import CitationGenerator, ResponseBuilder  # noqa: E402
from core.types import RetrievalResult  # noqa: E402


def _make_result(chunk_id: str, score: float, *, source_path: str, page: int | None, text: str) -> RetrievalResult:
    metadata = {"source_path": source_path}
    if page is not None:
        metadata["page"] = page
    return RetrievalResult(chunk_id=chunk_id, score=score, text=text, metadata=metadata)


def test_response_builder_builds_markdown_and_structured_citations() -> None:
    """
    Given:
        两条合法的 `RetrievalResult`，并且包含 source_path/page 等引用字段。
    When:
        调用 `ResponseBuilder.build()` 生成 MCP tool 返回体。
    Then:
        应返回可读 Markdown，且 `structuredContent.citations` 中包含 source/page/chunk_id/score。
    """
    builder = ResponseBuilder(citation_generator=CitationGenerator(), max_snippet_chars=80)
    results = [
        _make_result(
            "chunk_a",
            0.91,
            source_path="docs/azure_guide.pdf",
            page=3,
            text="Azure OpenAI 的配置步骤包括创建资源、获取 endpoint 与 API key，然后在 settings.yaml 中完成映射。",
        ),
        _make_result(
            "chunk_b",
            0.83,
            source_path="docs/openai_notes.pdf",
            page=8,
            text="如果需要多环境切换，建议把 API Key 和 endpoint 放入环境变量，并在配置文件中使用占位符解析。",
        ),
    ]

    payload = builder.build(
        results,
        "如何配置 Azure OpenAI？",
        extra={"backend": "cross_encoder", "fallback": False},
    )

    assert payload["content"][0]["type"] == "text"
    assert "[1]" in payload["content"][0]["text"]
    assert "azure_guide.pdf" in payload["content"][0]["text"]
    assert payload["structuredContent"]["query"] == "如何配置 Azure OpenAI？"
    assert payload["structuredContent"]["result_count"] == 2
    assert payload["structuredContent"]["citations"][0]["source"] == "docs/azure_guide.pdf"
    assert payload["structuredContent"]["citations"][0]["page"] == 3
    assert payload["structuredContent"]["citations"][0]["chunk_id"] == "chunk_a"
    assert payload["structuredContent"]["citations"][0]["score"] == pytest.approx(0.91)


def test_response_builder_returns_friendly_message_when_no_results() -> None:
    """
    Given:
        一个合法查询，但检索阶段没有返回任何结果。
    When:
        调用 `ResponseBuilder.build()` 构建响应。
    Then:
        应返回友好提示文本，而不是空字符串；同时 citations 应为空列表。
    """
    builder = ResponseBuilder()

    payload = builder.build([], "没有命中的问题")

    assert "未在知识库中找到" in payload["content"][0]["text"]
    assert payload["structuredContent"]["result_count"] == 0
    assert payload["structuredContent"]["citations"] == []
