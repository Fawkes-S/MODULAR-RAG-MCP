"""MCP tool：列出知识库集合。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_server.protocol_handler import ProtocolHandlerError, ToolSpec


class ListCollectionsTool:
    """`list_collections` 的最小实现。

    做什么：
    - 扫描 `data/documents/` 下的一级子目录；
    - 把每个目录视为一个集合，并返回集合名与轻量统计；
    - 生成可读文本和结构化列表，供 MCP 客户端直接展示或继续处理。

    为什么：
    - E4 的验收点只要求“对 fixtures 的目录结构能返回集合名列表”；
    - 因此当前阶段不提前实现 G2 `DocumentManager`，避免把 E4 过度扩展成跨存储统计系统。

    关键权衡：
    - 统计只做目录级轻量计算，例如文件数和子目录数；
    - 更精确的文档数/chunk 数/图片数将在后续 `DocumentManager` 落地后接管。

    失败路径：
    - `arguments` 非空或类型错误：抛 `ProtocolHandlerError(-32602)`；
    - `documents_root` 不存在时，不抛异常，而是返回空集合列表，便于新环境首次启动。
    """

    NAME = "list_collections"
    DESCRIPTION = "列出知识库中可用的文档集合。"
    INPUT_SCHEMA: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }

    def __init__(self, documents_root: str = "data/documents") -> None:
        self.documents_root = Path(documents_root)

    def handle(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行集合枚举并返回 MCP tool 结果。"""
        if not isinstance(arguments, dict) or arguments:
            raise self._invalid_params()

        collections = self._collect_collections()
        markdown = self._build_markdown(collections)

        return {
            "content": [{"type": "text", "text": markdown}],
            "structuredContent": {
                "documents_root": str(self.documents_root),
                "count": len(collections),
                "collections": collections,
            },
        }

    def _collect_collections(self) -> list[dict[str, Any]]:
        """收集一级集合目录。

        关键逻辑：
        - 仅扫描一级目录，避免把集合内部的业务子目录误当成新集合；
        - 使用名字排序，保证不同平台/文件系统上的返回顺序稳定，便于测试与客户端缓存。
        """
        if not self.documents_root.exists() or not self.documents_root.is_dir():
            return []

        collections: list[dict[str, Any]] = []
        for entry in sorted(self.documents_root.iterdir(), key=lambda path: path.name.lower()):
            if not entry.is_dir():
                continue

            file_count = 0
            subdir_count = 0
            for child in entry.iterdir():
                if child.is_file():
                    file_count += 1
                elif child.is_dir():
                    subdir_count += 1

            collections.append(
                {
                    "name": entry.name,
                    "path": str(entry),
                    "file_count": file_count,
                    "subdir_count": subdir_count,
                }
            )
        return collections

    @staticmethod
    def _build_markdown(collections: list[dict[str, Any]]) -> str:
        """把集合列表渲染为人可读文本。"""
        if not collections:
            return "当前没有可用的知识库集合。"

        lines = ["当前可用的知识库集合：", ""]
        for index, item in enumerate(collections, start=1):
            lines.append(
                f"{index}. {item['name']} "
                f"(files={item['file_count']}, subdirs={item['subdir_count']})"
            )
        return "\n".join(lines)

    @staticmethod
    def _invalid_params() -> ProtocolHandlerError:
        return ProtocolHandlerError(code=-32602, message="Invalid params")


def create_list_collections_tool(documents_root: str = "data/documents") -> ToolSpec:
    """构造可注册到 `ProtocolHandler` 的 `list_collections` tool。"""
    tool = ListCollectionsTool(documents_root=documents_root)
    return ToolSpec(
        name=ListCollectionsTool.NAME,
        description=ListCollectionsTool.DESCRIPTION,
        input_schema=dict(ListCollectionsTool.INPUT_SCHEMA),
        handler=tool.handle,
    )
