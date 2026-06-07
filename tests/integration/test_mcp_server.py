"""MCP Server 集成测试。"""

from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.reranker import RerankOutput  # noqa: E402
from core.response.multimodal_assembler import MultimodalAssembler  # noqa: E402
from core.response.response_builder import ResponseBuilder  # noqa: E402
from core.types import RetrievalResult  # noqa: E402
from ingestion.storage.image_storage import ImageStorage  # noqa: E402
from mcp_server.protocol_handler import ProtocolHandler  # noqa: E402
from mcp_server.server import MCPServer  # noqa: E402
from mcp_server.tools import create_get_document_summary_tool, create_query_knowledge_hub_tool  # noqa: E402

SERVER_SCRIPT = PROJECT_ROOT / "src" / "mcp_server" / "server.py"
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def test_mcp_server_initialize_over_stdio_without_stdout_pollution() -> None:
    """
    Given:
        一个以子进程启动的 MCP stdio server。
    When:
        向其 stdin 发送一条 `initialize` JSON-RPC 请求。
    Then:
        stdout 应仅返回合法 JSON-RPC 响应，stderr 可以包含日志但不能污染 stdout。
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest-client", "version": "0.0.1"},
        },
    }

    completed = subprocess.run(
        [str(PYTHON_EXE), str(SERVER_SCRIPT)],
        input=json.dumps(payload, ensure_ascii=False) + "\n",
        text=True,
        capture_output=True,
        timeout=10,
        cwd=str(PROJECT_ROOT),
    )

    assert completed.returncode == 0
    assert completed.stdout.strip()

    response = json.loads(completed.stdout.strip())
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert response["result"]["serverInfo"]["name"] == "modular-rag-mcp"
    assert "tools" in response["result"]["capabilities"]
    assert "MCP stdio server started" in completed.stderr


class _FakeHybridSearch:
    """测试桩：模拟 `query -> hybrid search` 阶段。"""

    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "filters": dict(filters) if isinstance(filters, dict) else filters,
                "trace": trace,
            }
        )
        return list(self.results)[:top_k]


class _FakeReranker:
    """测试桩：模拟 rerank 阶段，并保留输入顺序。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int | None = None,
        trace: Any | None = None,
    ) -> RerankOutput:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "candidate_ids": [item.chunk_id for item in candidates],
                "trace": trace,
            }
        )
        results = list(candidates if top_k is None else candidates[:top_k])
        return RerankOutput(results=results, fallback=False, fallback_reason=None, backend="none")


@pytest.fixture()
def image_storage_workspace() -> Path:
    """在项目目录内创建图片测试工作区，避免依赖系统临时目录权限。"""
    root = PROJECT_ROOT / ".pytest_tmp" / f"mcp_server_images_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_mcp_server_query_knowledge_hub_returns_markdown_and_citations() -> None:
    """
    Given:
        一个注册了 `query_knowledge_hub` 的 MCP server，并注入可控的 fake 检索与重排依赖。
    When:
        客户端依次发送 `initialize` 与 `tools/call(query_knowledge_hub)` 请求。
    Then:
        server 应返回合法 JSON-RPC 响应，tool 结果中同时包含 Markdown 文本和 structured citations。
    """
    fake_search = _FakeHybridSearch(
        results=[
            RetrievalResult(
                chunk_id="chunk_001",
                score=0.88,
                text="Azure OpenAI 配置通常包括 endpoint、deployment_name 和 api_key 三个核心字段。",
                metadata={"source_path": "docs/azure.pdf", "page": 2, "collection": "manual"},
            ),
            RetrievalResult(
                chunk_id="chunk_002",
                score=0.77,
                text="建议把 API Key 放到环境变量中，再通过 settings.yaml 的占位符读取。",
                metadata={"source_path": "docs/setup.pdf", "page": 5, "collection": "manual"},
            ),
        ]
    )
    fake_reranker = _FakeReranker()
    protocol_handler = ProtocolHandler(
        tools=[
            create_query_knowledge_hub_tool(
                searcher=fake_search,
                reranker=fake_reranker,
            )
        ]
    )
    stdin = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "pytest-client", "version": "0.0.1"},
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "query_knowledge_hub",
                            "arguments": {
                                "query": "如何配置 Azure OpenAI？",
                                "top_k": 2,
                                "collection": "manual",
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n"
    )
    stdout = io.StringIO()

    exit_code = MCPServer(stdin=stdin, stdout=stdout, protocol_handler=protocol_handler).serve_forever()

    output_lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    initialize_response = json.loads(output_lines[0])
    tool_response = json.loads(output_lines[1])

    assert exit_code == 0
    assert initialize_response["result"]["serverInfo"]["name"] == "modular-rag-mcp"
    assert tool_response["jsonrpc"] == "2.0"
    assert tool_response["id"] == 2
    assert "Azure OpenAI" in tool_response["result"]["content"][0]["text"]
    assert tool_response["result"]["structuredContent"]["citations"][0]["source"] == "docs/azure.pdf"
    assert tool_response["result"]["structuredContent"]["citations"][0]["page"] == 2
    assert fake_search.calls[0]["filters"] == {"collection": "manual"}
    assert fake_reranker.calls[0]["candidate_ids"] == ["chunk_001", "chunk_002"]


def test_mcp_server_get_document_summary_returns_structured_summary() -> None:
    """
    Given:
        一个注册了 `get_document_summary` 的 MCP server，并注入可控的摘要 resolver。
    When:
        客户端发送 `tools/call(get_document_summary)` 请求。
    Then:
        server 应返回合法 JSON-RPC 响应，
        且 tool 结果中同时包含可展示文本和结构化的 `doc_id/title/summary/tags`。
    """

    def _resolver(doc_id: str) -> dict[str, object] | None:
        if doc_id != "pdf_summary_001":
            return None
        return {
            "title": "系统架构总览",
            "summary": "概述模块边界、数据流和扩展点。",
            "tags": ["architecture", "rag", "mcp"],
            "source_path": "docs/architecture.pdf",
        }

    protocol_handler = ProtocolHandler(
        tools=[
            create_get_document_summary_tool(resolver=_resolver),
        ]
    )
    stdin = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "pytest-client", "version": "0.0.1"},
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "get_document_summary",
                            "arguments": {"doc_id": "pdf_summary_001"},
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n"
    )
    stdout = io.StringIO()

    exit_code = MCPServer(stdin=stdin, stdout=stdout, protocol_handler=protocol_handler).serve_forever()

    output_lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    initialize_response = json.loads(output_lines[0])
    tool_response = json.loads(output_lines[1])

    assert exit_code == 0
    assert initialize_response["result"]["serverInfo"]["name"] == "modular-rag-mcp"
    assert tool_response["jsonrpc"] == "2.0"
    assert tool_response["id"] == 2
    assert "系统架构总览" in tool_response["result"]["content"][0]["text"]
    assert tool_response["result"]["structuredContent"]["doc_id"] == "pdf_summary_001"
    assert tool_response["result"]["structuredContent"]["summary"] == "概述模块边界、数据流和扩展点。"
    assert tool_response["result"]["structuredContent"]["tags"] == ["architecture", "rag", "mcp"]


def test_mcp_server_query_knowledge_hub_returns_text_and_image_content(
    image_storage_workspace: Path,
) -> None:
    """
    Given:
        一个命中结果携带 `image_refs` 的 `query_knowledge_hub`，并为对应 `image_id` 准备好本地 ImageStorage 索引与图片文件。
    When:
        客户端通过 MCP 调用 `query_knowledge_hub`。
    Then:
        返回的 `content` 中应同时包含 text 与 image 两种类型，
        且图片项的 `mimeType` 正确、`data` 是可解码的 base64 字符串。
    """
    image_storage = ImageStorage(
        image_root=str(image_storage_workspace / "images"),
        db_path=str(image_storage_workspace / "db" / "image_index.db"),
    )
    stored_path = image_storage.save_image(
        image_id="img_arch_001",
        image_bytes=(
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            b"\x90wS\xde"
            b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00"
            b"\xc9\xfe\x92\xef"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        collection="demo",
        doc_hash="img_arch",
        page_num=1,
        extension="png",
    )

    fake_search = _FakeHybridSearch(
        results=[
            RetrievalResult(
                chunk_id="chunk_img_001",
                score=0.93,
                text="系统架构如下 [IMAGE: img_arch_001]。",
                metadata={
                    "source_path": "docs/architecture.pdf",
                    "page": 1,
                    "collection": "manual",
                    "image_refs": ["img_arch_001"],
                    "images": [{"id": "img_arch_001", "path": stored_path, "page": 1}],
                },
            )
        ]
    )
    fake_reranker = _FakeReranker()
    response_builder = ResponseBuilder(
        multimodal_assembler=MultimodalAssembler(image_storage=image_storage),
    )
    protocol_handler = ProtocolHandler(
        tools=[
            create_query_knowledge_hub_tool(
                searcher=fake_search,
                reranker=fake_reranker,
                response_builder=response_builder,
            )
        ]
    )
    stdin = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "pytest-client", "version": "0.0.1"},
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "query_knowledge_hub",
                            "arguments": {
                                "query": "请展示系统架构图",
                                "top_k": 1,
                                "collection": "manual",
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n"
    )
    stdout = io.StringIO()

    exit_code = MCPServer(stdin=stdin, stdout=stdout, protocol_handler=protocol_handler).serve_forever()

    output_lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    tool_response = json.loads(output_lines[1])
    content = tool_response["result"]["content"]
    image_content = next(item for item in content if item["type"] == "image")

    assert exit_code == 0
    assert content[0]["type"] == "text"
    assert "系统架构" in content[0]["text"]
    assert image_content["mimeType"] == "image/png"
    assert base64.b64decode(image_content["data"])
    assert tool_response["result"]["structuredContent"]["images"][0]["image_id"] == "img_arch_001"
