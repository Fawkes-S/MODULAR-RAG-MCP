"""MCP Server stdio 入口（E1/E2 基础实现）。"""

from __future__ import annotations

import sys
from typing import Any, TextIO

from mcp_server.protocol_handler import ProtocolHandler
from observability.logger import get_logger

LOGGER = get_logger("mcp_server.server")


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

    def __init__(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        protocol_handler: ProtocolHandler | None = None,
    ) -> None:
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.protocol_handler = protocol_handler or ProtocolHandler()

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
        import json

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                },
            }

        response = self.protocol_handler.handle_message(message)
        method = message.get("method") if isinstance(message, dict) else None
        if method == "initialize" and isinstance(message, dict):
            params = message.get("params", {})
            client_protocol = params.get("protocolVersion") if isinstance(params, dict) else None
            LOGGER.info("Handled initialize request (client_protocol=%s)", client_protocol)
        elif method == "notifications/initialized":
            LOGGER.info("Client initialized notification received")
        return response

    def _write_message(self, payload: dict[str, Any]) -> None:
        """将 JSON-RPC 响应写入 stdout。

        根据 MCP 官方 stdio transport 文档，消息按“单行 JSON”分隔，
        因此这里强制使用紧凑 JSON 并追加单个换行。
        """
        import json

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
