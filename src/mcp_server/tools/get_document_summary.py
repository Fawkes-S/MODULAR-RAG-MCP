"""MCP tool：按 doc_id 获取文档摘要。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from mcp_server.protocol_handler import ProtocolHandlerError, ToolSpec

SummaryResolver = Callable[[str], dict[str, Any] | None]


class FileDocumentSummaryResolver:
    """基于本地 JSON 缓存读取文档摘要。

    做什么：
    - 从约定的缓存文件读取摘要元数据；
    - 支持两种常见缓存形态：
      1. `{doc_id: {...}}`
      2. `{"documents": [{"doc_id": "...", ...}]}`
    - 只负责“找原始记录”，不负责协议层错误映射。

    为什么：
    - E5 明确允许“先从 metadata/缓存取”；
    - 当前项目还没有 G2 的 `DocumentManager`，也没有真正的文档级索引，
      因此这里采用轻量缓存解析器，避免把 E5 过度扩展成未到期的跨存储查询系统。

    关键权衡：
    - 默认每次调用都重新读文件，而不是常驻内存缓存。
      这样牺牲少量 IO，换来更直观的“文件一改立即生效”，也避免测试里出现缓存污染。
    - 若缓存文件不存在，返回 `None` 而不是抛错。
      这样 tool 可以把“没找到文档”统一映射成协议级错误，而不是把首次空环境误判为系统故障。

    失败路径：
    - 缓存文件不存在：返回 `None`；
    - JSON 结构损坏：抛 `ValueError`，让上层按内部错误处理；
    - 找不到指定 `doc_id`：返回 `None`。

    Args:
        cache_path: 文档摘要缓存文件路径。
    """

    def __init__(self, cache_path: str = "data/cache/document_summaries.json") -> None:
        self.cache_path = Path(cache_path)

    def resolve(self, doc_id: str) -> dict[str, Any] | None:
        """读取缓存并返回指定文档的原始摘要记录。"""
        payload = self._load_payload()
        if payload is None:
            return None

        direct_hit = self._resolve_direct_mapping(payload, doc_id)
        if direct_hit is not None:
            return direct_hit

        return self._resolve_documents_list(payload, doc_id)

    def _load_payload(self) -> dict[str, Any] | None:
        """加载缓存文件。

        这里把“文件不存在”视为正常空状态，因为 E5 当前阶段允许先不持久化摘要缓存。
        但如果文件存在且内容损坏，则说明缓存写入过程或手工编辑出了问题，应显式暴露为内部错误。
        """
        if not self.cache_path.exists():
            return None

        raw_text = self.cache_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        if not isinstance(payload, dict):
            raise ValueError("document summary cache must be JSON object")
        return payload

    @staticmethod
    def _resolve_direct_mapping(payload: dict[str, Any], doc_id: str) -> dict[str, Any] | None:
        """兼容 `{doc_id: {...}}` 这种最直接的缓存结构。"""
        raw_item = payload.get(doc_id)
        if isinstance(raw_item, dict):
            return dict(raw_item)
        return None

    @staticmethod
    def _resolve_documents_list(payload: dict[str, Any], doc_id: str) -> dict[str, Any] | None:
        """兼容 `{"documents": [...]}` 结构，便于未来平滑切换到批量导出缓存。"""
        documents = payload.get("documents")
        if not isinstance(documents, list):
            return None

        for item in documents:
            if not isinstance(item, dict):
                continue

            candidate_id = item.get("doc_id", item.get("id"))
            if isinstance(candidate_id, str) and candidate_id.strip() == doc_id:
                return dict(item)
        return None


class GetDocumentSummaryTool:
    """`get_document_summary` 的业务实现。

    做什么：
    - 校验 MCP `tools/call.arguments` 中的 `doc_id`；
    - 通过可注入的 resolver 查询摘要元数据；
    - 返回 `title/summary/tags` 的结构化结果与人类可读文本。

    为什么：
    - 这是 E5 要暴露给 MCP Client 的文档级信息读取入口；
    - 当前阶段没有完整的文档管理后端，因此把“摘要来源”抽象成 resolver，
      后续接入 `DocumentManager` 或真实存储时，只需要替换 resolver 而不必改协议层。

    关键权衡：
    - `doc_id` 存在但部分字段缺失时，尽量补齐默认值而不是直接失败，
      这样能兼容“只有部分 metadata 已落盘”的过渡阶段数据。
    - “文档不存在”走协议级错误而不是成功空结果，
      因为这个 tool 的语义是“按精确 ID 读取单条资源”，空结果更像调用错误而不是模糊检索未命中。

    失败路径：
    - `doc_id` 缺失、为空、类型错误：抛 `ProtocolHandlerError(-32602, "Invalid params")`；
    - resolver 未找到文档：抛 `ProtocolHandlerError(-32602, "Document not found")`；
    - resolver 内部读缓存/解析异常：不在这里吞掉，交给协议层转成 `-32603 Internal error`。

    Args:
        resolver: 可注入的摘要查询函数，便于单元测试和后续接入真实后端。
        cache_path: 默认文件解析器使用的缓存文件路径。

    Example:
        >>> tool = GetDocumentSummaryTool(
        ...     resolver=lambda doc_id: {"title": "入门指南", "summary": "介绍基础配置。", "tags": ["guide"]}
        ... )
        >>> tool.handle({"doc_id": "pdf_abc123"})["structuredContent"]["title"]
        '入门指南'
    """

    NAME = "get_document_summary"
    DESCRIPTION = "按文档 ID 返回标题、摘要和标签。"
    INPUT_SCHEMA: dict[str, Any] = {
        "type": "object",
        "properties": {
            "doc_id": {"type": "string", "description": "目标文档的稳定 ID。"},
        },
        "required": ["doc_id"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        resolver: SummaryResolver | None = None,
        cache_path: str = "data/cache/document_summaries.json",
    ) -> None:
        file_resolver = FileDocumentSummaryResolver(cache_path=cache_path)
        self._resolver = resolver or file_resolver.resolve

    def handle(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行单文档摘要读取并返回 MCP tool 结果。"""
        if not isinstance(arguments, dict):
            raise self._invalid_params()

        doc_id = self._normalize_doc_id(arguments.get("doc_id"))
        raw_summary = self._resolver(doc_id)
        if raw_summary is None:
            # 这里显式返回协议级“请求目标不存在”，避免客户端把空结果误解成成功命中。
            raise self._document_not_found()

        summary = self._normalize_summary(doc_id=doc_id, raw_summary=raw_summary)
        return {
            "content": [{"type": "text", "text": self._build_markdown(summary)}],
            "structuredContent": summary,
        }

    @staticmethod
    def _normalize_doc_id(raw_doc_id: Any) -> str:
        """把输入归一化为非空 doc_id。"""
        if not isinstance(raw_doc_id, str):
            raise GetDocumentSummaryTool._invalid_params()
        normalized = raw_doc_id.strip()
        if not normalized:
            raise GetDocumentSummaryTool._invalid_params()
        return normalized

    @staticmethod
    def _normalize_summary(doc_id: str, raw_summary: dict[str, Any]) -> dict[str, Any]:
        """补齐摘要结构中的关键字段。

        这里优先保证 tool 契约稳定：
        - `title` 始终返回字符串；
        - `summary` 始终返回字符串；
        - `tags` 始终返回字符串列表。
        """
        title = str(raw_summary.get("title", "")).strip() or doc_id
        summary = str(raw_summary.get("summary", "")).strip() or "No summary available."
        tags = GetDocumentSummaryTool._normalize_tags(raw_summary.get("tags"))

        normalized = {
            "doc_id": doc_id,
            "title": title,
            "summary": summary,
            "tags": tags,
        }

        # 可选透传少量已知元信息，方便客户端直接展示，但不把整个原始 payload 原封不动暴露出去。
        for optional_key in ("source_path", "collection"):
            optional_value = raw_summary.get(optional_key)
            if isinstance(optional_value, str) and optional_value.strip():
                normalized[optional_key] = optional_value.strip()

        return normalized

    @staticmethod
    def _normalize_tags(raw_tags: Any) -> list[str]:
        """把 tags 归一化为去空、去重、保序的字符串列表。"""
        if isinstance(raw_tags, str):
            candidates = [part.strip() for part in raw_tags.split(",")]
        elif isinstance(raw_tags, list):
            candidates = [str(item).strip() for item in raw_tags]
        else:
            candidates = []

        tags: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            lowered = item.lower()
            if not item or lowered in seen:
                continue
            seen.add(lowered)
            tags.append(item)
        return tags

    @staticmethod
    def _build_markdown(summary: dict[str, Any]) -> str:
        """渲染为便于 MCP 客户端直接展示的文本。"""
        tags = summary["tags"]
        tags_text = "、".join(tags) if tags else "无"
        lines = [
            "文档摘要",
            "",
            f"- doc_id: {summary['doc_id']}",
            f"- title: {summary['title']}",
            f"- tags: {tags_text}",
            "",
            summary["summary"],
        ]
        if "source_path" in summary:
            lines.insert(5, f"- source_path: {summary['source_path']}")
        if "collection" in summary:
            insert_at = 6 if "source_path" in summary else 5
            lines.insert(insert_at, f"- collection: {summary['collection']}")
        return "\n".join(lines)

    @staticmethod
    def _invalid_params() -> ProtocolHandlerError:
        return ProtocolHandlerError(code=-32602, message="Invalid params")

    @staticmethod
    def _document_not_found() -> ProtocolHandlerError:
        return ProtocolHandlerError(code=-32602, message="Document not found")


def create_get_document_summary_tool(
    *,
    resolver: SummaryResolver | None = None,
    cache_path: str = "data/cache/document_summaries.json",
) -> ToolSpec:
    """构造可注册到 `ProtocolHandler` 的 `get_document_summary` tool。"""
    tool = GetDocumentSummaryTool(resolver=resolver, cache_path=cache_path)
    return ToolSpec(
        name=GetDocumentSummaryTool.NAME,
        description=GetDocumentSummaryTool.DESCRIPTION,
        input_schema=dict(GetDocumentSummaryTool.INPUT_SCHEMA),
        handler=tool.handle,
    )
