"""MCP Server 最小 stdio 入口（E1）。

当前阶段目标：
- 仅实现 MCP 生命周期里最基础的 `initialize` 请求；
- 遵守 stdio 约束：`stdout` 只输出合法 JSON-RPC 消息，日志统一写入 `stderr`；
- 为 E2 的 `ProtocolHandler` 留出清晰替换点，不在这里过度实现协议细节。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, TextIO

from observability.logger import get_logger

LOGGER = get_logger("mcp_server.server")

SUPPORTED_PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "modular-rag-mcp"
SERVER_VERSION = "0.1.0"
SERVER_TITLE = "Modular RAG MCP Server"


@dataclass(frozen=True)
class InitializeResponse:
    """`initialize` 成功响应的数据结构。"""

    protocol_version: str = SUPPORTED_PROTOCOL_VERSION
    capabilities: dict[str, Any] | None = None
    instructions: str = (
        "This server currently supports initialization only. "
        "Tools/resources/prompts will be added in subsequent phases."
    )

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON-RPC result 可直接复用的字典。"""
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities or {},
            "serverInfo": {
                "name": SERVER_NAME,
                "title": SERVER_TITLE,
                "version": SERVER_VERSION,
            },
            "instructions": self.instructions,
        }


class MCPServer:
    """最小 MCP stdio 服务端。

    做什么：
    - 从 `stdin` 逐行读取 JSON-RPC 消息；
    - 处理 `initialize` 请求与 `notifications/initialized` 通知；
    - 将合法 JSON-RPC 响应逐行写到 `stdout`。

    为什么：
    - E1 只需要先证明“子进程 stdio 通道可用 + initialize 可完成 + stdout 不被日志污染”。

    关键权衡：
    - 当前只支持换行分隔 JSON 消息，不引入官方 SDK；
      这是根据 MCP 官方 stdio transport 文档做的最小实现。

    失败路径：
    - 非法 JSON 或非法请求不会向 `stdout` 打日志，而是返回 JSON-RPC error；
    - 通知消息不回包，避免破坏协议语义。
    """

    def __init__(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._initialized = False

    def serve_forever(self) -> int:
        """启动主循环，直到 `stdin` 关闭。"""
        LOGGER.info("MCP stdio server started")
        for raw_line in self.stdin:
            line = raw_line.strip()
            if not line:
                continue
            response = self._process_line(line)
            if response is None:
                continue
            self._write_message(response)

        LOGGER.info("MCP stdio server stopped")
        return 0

    def _process_line(self, line: str) -> dict[str, Any] | None:
        """解析并处理单条 JSON-RPC 消息。"""
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return self._error_response(
                request_id=None,
                code=-32700,
                message="Parse error",
            )

        if not isinstance(message, dict):
            return self._error_response(
                request_id=None,
                code=-32600,
                message="Invalid Request",
            )

        return self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """按 JSON-RPC method 分发消息。"""
        if message.get("jsonrpc") != "2.0":
            return self._error_response(
                request_id=message.get("id"),
                code=-32600,
                message="Invalid Request",
            )

        method = message.get("method")
        if not isinstance(method, str) or not method.strip():
            return self._error_response(
                request_id=message.get("id"),
                code=-32600,
                message="Invalid Request",
            )

        request_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            return self._handle_initialize(request_id=request_id, params=params)

        if method == "notifications/initialized":
            self._initialized = True
            LOGGER.info("Client initialized notification received")
            return None

        # E1 阶段只承诺 initialize；其余方法留待 E2 扩展。
        if request_id is None:
            return None
        return self._error_response(
            request_id=request_id,
            code=-32601,
            message="Method not found",
        )

    def _handle_initialize(self, request_id: Any, params: Any) -> dict[str, Any]:
        """处理 MCP 初始化请求。"""
        if request_id is None:
            return self._error_response(
                request_id=None,
                code=-32600,
                message="Invalid Request",
            )
        if not isinstance(params, dict):
            return self._error_response(
                request_id=request_id,
                code=-32602,
                message="Invalid params",
            )

        client_version = params.get("protocolVersion")
        if not isinstance(client_version, str) or not client_version.strip():
            return self._error_response(
                request_id=request_id,
                code=-32602,
                message="Invalid params",
            )

        result = InitializeResponse(
            protocol_version=(
                client_version.strip()
                if client_version.strip() == SUPPORTED_PROTOCOL_VERSION
                else SUPPORTED_PROTOCOL_VERSION
            ),
            capabilities={
                "tools": {},
            },
        ).to_dict()

        LOGGER.info("Handled initialize request (client_protocol=%s)", client_version)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    @staticmethod
    def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
        """生成 JSON-RPC 错误响应。"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": int(code),
                "message": str(message),
            },
        }

    def _write_message(self, payload: dict[str, Any]) -> None:
        """将 JSON-RPC 响应写入 stdout。

        根据 MCP 官方 stdio transport 文档，消息按“单行 JSON”分隔，
        因此这里强制使用紧凑 JSON 并追加单个换行。
        """
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.stdout.write(text)
        self.stdout.write("\n")
        self.stdout.flush()


def main() -> int:
    """CLI 入口。"""
    return MCPServer().serve_forever()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("MCP server crashed: %s", exc)
        raise SystemExit(1) from exc
