"""get_document_summary tool 单元测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from mcp_server.protocol_handler import ProtocolHandlerError  # noqa: E402
from mcp_server.tools.get_document_summary import (  # noqa: E402
    GetDocumentSummaryTool,
)


def test_get_document_summary_returns_structured_summary_from_injected_resolver() -> None:
    """
    Given:
        一个可控的 resolver，能够按 `doc_id` 返回完整的 `title/summary/tags` 元数据。
    When:
        调用 `GetDocumentSummaryTool.handle({"doc_id": ...})`。
    Then:
        应返回包含 `content` 与 `structuredContent` 的成功结果，
        且结构化字段中的标题、摘要、标签与 resolver 输出一致。
    """

    def _resolver(doc_id: str) -> dict[str, object] | None:
        if doc_id != "pdf_abc123":
            return None
        return {
            "title": "Azure OpenAI 配置说明",
            "summary": "介绍 endpoint、deployment 和 API Key 的基本配置方式。",
            "tags": ["Azure", "OpenAI", "配置"],
            "collection": "manual",
        }

    payload = GetDocumentSummaryTool(resolver=_resolver).handle({"doc_id": "pdf_abc123"})

    assert "文档摘要" in payload["content"][0]["text"]
    assert payload["structuredContent"]["doc_id"] == "pdf_abc123"
    assert payload["structuredContent"]["title"] == "Azure OpenAI 配置说明"
    assert payload["structuredContent"]["summary"] == "介绍 endpoint、deployment 和 API Key 的基本配置方式。"
    assert payload["structuredContent"]["tags"] == ["Azure", "OpenAI", "配置"]
    assert payload["structuredContent"]["collection"] == "manual"


def test_get_document_summary_reads_summary_from_json_cache_file(tmp_path: Path) -> None:
    """
    Given:
        一个临时 JSON 缓存文件，内部按 `{doc_id: {...}}` 形式保存文档摘要。
    When:
        不注入 resolver，直接让 tool 使用默认文件解析器读取该缓存文件。
    Then:
        应成功命中缓存并返回结构化摘要，证明 E5 的“从 metadata/缓存取”最小路径可工作。
    """
    cache_path = tmp_path / "document_summaries.json"
    cache_path.write_text(
        json.dumps(
            {
                "pdf_cache_doc": {
                    "title": "缓存中的文档",
                    "summary": "这是从本地缓存文件读取到的摘要。",
                    "tags": ["cache", "summary"],
                    "source_path": "docs/cache.pdf",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = GetDocumentSummaryTool(cache_path=str(cache_path)).handle({"doc_id": "pdf_cache_doc"})

    assert payload["structuredContent"]["title"] == "缓存中的文档"
    assert payload["structuredContent"]["summary"] == "这是从本地缓存文件读取到的摘要。"
    assert payload["structuredContent"]["tags"] == ["cache", "summary"]
    assert payload["structuredContent"]["source_path"] == "docs/cache.pdf"


def test_get_document_summary_rejects_invalid_doc_id_arguments() -> None:
    """
    Given:
        `get_document_summary` 按契约要求必须接收非空字符串 `doc_id`。
    When:
        传入缺失、空白或错误类型的 `doc_id`。
    Then:
        应抛出协议级 `Invalid params` 错误，而不是静默纠正或返回内部错误。
    """
    tool = GetDocumentSummaryTool(resolver=lambda _doc_id: None)

    with pytest.raises(ProtocolHandlerError, match="Invalid params"):
        tool.handle({})

    with pytest.raises(ProtocolHandlerError, match="Invalid params"):
        tool.handle({"doc_id": "   "})

    with pytest.raises(ProtocolHandlerError, match="Invalid params"):
        tool.handle({"doc_id": 123})


def test_get_document_summary_raises_protocol_error_when_doc_id_missing_in_backend() -> None:
    """
    Given:
        一个 resolver，它对任何 `doc_id` 都返回 `None`，表示后端中不存在该文档。
    When:
        调用 `get_document_summary` 查询一个具体 `doc_id`。
    Then:
        应抛出协议级 “Document not found” 错误，
        以满足 E5 对“不存在 doc_id 返回规范错误”的验收要求。
    """
    tool = GetDocumentSummaryTool(resolver=lambda _doc_id: None)

    with pytest.raises(ProtocolHandlerError, match="Document not found"):
        tool.handle({"doc_id": "pdf_missing"})
