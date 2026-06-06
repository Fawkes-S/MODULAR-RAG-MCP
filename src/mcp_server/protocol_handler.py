"""ProtocolHandler：MCP/JSON-RPC 协议解析与能力协商（E2）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

SUPPORTED_PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "modular-rag-mcp"
SERVER_TITLE = "Modular RAG MCP Server"
SERVER_VERSION = "0.1.0"

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    """已注册 MCP tool 的最小描述。"""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def to_dict(self) -> dict[str, Any]:
        """转换为 `tools/list` 响应里的标准结构。"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
        }


class ProtocolHandler:
    """纯协议层处理器。

    做什么：
    - 处理 `initialize`、`tools/list`、`tools/call` 三类 MCP 核心方法；
    - 屏蔽底层 server 的 JSON-RPC 细节，让 server 只负责 stdio 收发；
    - 提供统一错误码与不泄露堆栈的错误输出。

    为什么：
    - E2 需要把“协议逻辑”和“传输逻辑”分层，便于单元测试和后续扩展 tools。

    关键权衡：
    - 当前阶段只做最小工具注册表，不引入复杂 schema 校验库；
      参数检查以 shape 校验为主，优先保证行为清晰和测试稳定。
    """

    def __init__(self, tools: list[ToolSpec] | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for tool in tools or []:
            self.register_tool(tool)

    def register_tool(self, tool: ToolSpec) -> None:
        """注册单个 tool。"""
        if not isinstance(tool, ToolSpec):
            raise TypeError("tool must be ToolSpec")
        key = tool.name.strip()
        if not key:
            raise ValueError("tool.name must be non-empty")
        self._tools[key] = tool

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """处理完整 JSON-RPC 请求消息。"""
        if not isinstance(message, dict):
            return self._error_response(None, -32600, "Invalid Request")
        if message.get("jsonrpc") != "2.0":
            return self._error_response(message.get("id"), -32600, "Invalid Request")

        method = message.get("method")
        if not isinstance(method, str) or not method.strip():
            return self._error_response(message.get("id"), -32600, "Invalid Request")

        request_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            try:
                return self._success_response(request_id, self.handle_initialize(params))
            except _ProtocolHandlerJSONRPCError as exc:
                return self._error_response(request_id, exc.code, exc.message)
        if method == "tools/list":
            try:
                return self._success_response(request_id, self.handle_tools_list())
            except _ProtocolHandlerJSONRPCError as exc:
                return self._error_response(request_id, exc.code, exc.message)
        if method == "tools/call":
            try:
                return self._success_response(request_id, self.handle_tools_call(params))
            except _ProtocolHandlerJSONRPCError as exc:
                return self._error_response(request_id, exc.code, exc.message)
        if method == "notifications/initialized":
            return None
        if request_id is None:
            return None
        return self._error_response(request_id, -32601, "Method not found")

    def handle_initialize(self, params: Any) -> dict[str, Any]:
        """返回 initialize 结果体。"""
        if not isinstance(params, dict):
            raise self._jsonrpc_error(-32602, "Invalid params")

        client_protocol_version = params.get("protocolVersion")
        if not isinstance(client_protocol_version, str) or not client_protocol_version.strip():
            raise self._jsonrpc_error(-32602, "Invalid params")

        return {
            "protocolVersion": (
                client_protocol_version.strip()
                if client_protocol_version.strip() == SUPPORTED_PROTOCOL_VERSION
                else SUPPORTED_PROTOCOL_VERSION
            ),
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "title": SERVER_TITLE,
                "version": SERVER_VERSION,
            },
            "instructions": (
                "This server currently supports initialize/tools/list/tools/call. "
                "Business tools will be added in subsequent phases."
            ),
        }

    def handle_tools_list(self) -> dict[str, Any]:
        """返回已注册 tool schema 列表。"""
        return {
            "tools": [tool.to_dict() for tool in self._tools.values()],
        }

    def handle_tools_call(self, params: Any) -> dict[str, Any]:
        """根据 name 路由到具体 tool。"""
        if not isinstance(params, dict):
            raise self._jsonrpc_error(-32602, "Invalid params")

        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not name.strip():
            raise self._jsonrpc_error(-32602, "Invalid params")
        if not isinstance(arguments, dict):
            raise self._jsonrpc_error(-32602, "Invalid params")

        tool = self._tools.get(name.strip())
        if tool is None:
            raise self._jsonrpc_error(-32601, "Method not found")

        try:
            result = tool.handler(dict(arguments))
        except _ProtocolHandlerJSONRPCError:
            raise
        except Exception:
            # 不泄露堆栈或内部实现细节，只返回标准 internal error。
            raise self._jsonrpc_error(-32603, "Internal error")

        if not isinstance(result, dict):
            raise self._jsonrpc_error(-32603, "Internal error")
        return result

    def _success_response(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": int(code),
                "message": str(message),
            },
        }

    @staticmethod
    def _jsonrpc_error(code: int, message: str) -> "_ProtocolHandlerJSONRPCError":
        return _ProtocolHandlerJSONRPCError(code=code, message=message)


class _ProtocolHandlerJSONRPCError(RuntimeError):
    """ProtocolHandler 内部使用的标准 JSON-RPC 错误。"""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = int(code)
        self.message = str(message)
