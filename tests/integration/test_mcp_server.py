"""MCP Server 集成测试。"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.reranker import RerankOutput  # noqa: E402
from core.types import RetrievalResult  # noqa: E402
from mcp_server.protocol_handler import ProtocolHandler  # noqa: E402
from mcp_server.server import MCPServer  # noqa: E402
from mcp_server.tools import create_query_knowledge_hub_tool  # noqa: E402

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
