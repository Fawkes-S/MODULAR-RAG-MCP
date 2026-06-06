"""ProtocolHandler 单元测试（E2）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from mcp_server.protocol_handler import ProtocolHandler, ToolSpec  # noqa: E402


def _make_handler() -> ProtocolHandler:
    def _echo_tool(arguments: dict[str, object]) -> dict[str, object]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"echo:{arguments.get('text', '')}",
                }
            ]
        }

    return ProtocolHandler(
        tools=[
            ToolSpec(
                name="echo_tool",
                description="Echo back the provided text.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
                handler=_echo_tool,
            )
        ]
    )


def test_protocol_handler_initialize_returns_capabilities_and_server_info() -> None:
    """
    Given:
        一个最小 ProtocolHandler。
    When:
        发送 `initialize` 请求消息。
    Then:
        应返回 serverInfo、protocolVersion 和 capabilities.tools。
    """
    handler = _make_handler()

    response = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0.1"},
            },
        }
    )

    assert response is not None
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert response["result"]["serverInfo"]["name"] == "modular-rag-mcp"
    assert "tools" in response["result"]["capabilities"]


def test_protocol_handler_tools_list_returns_registered_tool_schema() -> None:
    """
    Given:
        一个已注册 `echo_tool` 的 ProtocolHandler。
    When:
        发送 `tools/list` 请求。
    Then:
        应返回该 tool 的 name、description 和 inputSchema。
    """
    handler = _make_handler()

    response = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
    )

    assert response is not None
    tools = response["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo_tool"
    assert "inputSchema" in tools[0]


def test_protocol_handler_tools_call_routes_to_tool_handler() -> None:
    """
    Given:
        一个注册了 `echo_tool` 的 ProtocolHandler。
    When:
        发送 `tools/call` 请求。
    Then:
        应正确路由到 tool handler，并返回其产出的结构化结果。
    """
    handler = _make_handler()

    response = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo_tool",
                "arguments": {"text": "hello"},
            },
        }
    )

    assert response is not None
    assert response["result"]["content"][0]["text"] == "echo:hello"


def test_protocol_handler_returns_standard_errors_for_invalid_method_params_and_internal_error() -> None:
    """
    Given:
        非法 method、非法 params，以及一个会抛异常的 tool handler。
    When:
        分别发送对应请求。
    Then:
        应返回 JSON-RPC 标准错误码：
        -32601 / -32602 / -32603，且不泄露内部堆栈。
    """
    def _broken_tool(_arguments: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("secret stack detail")

    handler = ProtocolHandler(
        tools=[
            ToolSpec(
                name="broken_tool",
                description="broken",
                input_schema={"type": "object"},
                handler=_broken_tool,
            )
        ]
    )

    method_not_found = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "unknown/method",
            "params": {},
        }
    )
    invalid_params = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "broken_tool", "arguments": "bad"},
        }
    )
    internal_error = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "broken_tool", "arguments": {}},
        }
    )

    assert method_not_found is not None
    assert method_not_found["error"]["code"] == -32601

    assert invalid_params is not None
    assert invalid_params["error"]["code"] == -32602

    assert internal_error is not None
    assert internal_error["error"]["code"] == -32603
    assert "secret stack detail" not in internal_error["error"]["message"]


def test_protocol_handler_initialized_notification_returns_no_response() -> None:
    """
    Given:
        一条 `notifications/initialized` 通知消息。
    When:
        交给 ProtocolHandler 处理。
    Then:
        应返回 `None`，因为通知不需要响应。
    """
    handler = _make_handler()

    response = handler.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
    )

    assert response is None
