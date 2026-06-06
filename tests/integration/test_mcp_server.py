"""MCP Server 集成测试（E1）。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_SCRIPT = PROJECT_ROOT / "src" / "mcp_server" / "server.py"
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def test_mcp_server_initialize_over_stdio_without_stdout_pollution() -> None:
    """
    Given:
        一个以子进程启动的 MCP stdio server。
    When:
        向其 stdin 发送一条 `initialize` JSON-RPC 请求。
    Then:
        stdout 应仅返回合法 JSON-RPC 响应；
        stderr 可以包含日志，但不应污染 stdout。
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

    # stdout 只允许出现协议消息；若混入日志，这里的 JSON 解析会直接失败。
    response = json.loads(completed.stdout.strip())
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert response["result"]["serverInfo"]["name"] == "modular-rag-mcp"
    assert "tools" in response["result"]["capabilities"]

    # stderr 允许有日志输出，但这些日志不能进入 stdout。
    assert "MCP stdio server started" in completed.stderr
