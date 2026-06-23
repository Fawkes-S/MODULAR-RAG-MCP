"""MCP tools 导出层。

做什么：
- 为 `mcp_server.server` 和测试代码提供统一的 tool 构造入口；
- 避免在包导入阶段就级联加载检索/LLM/Embedding 等重依赖；
- 通过按需导入把冷启动成本推迟到真正创建或调用对应 tool 的那一刻。

为什么：
- `initialize` / `tools/list` 的职责只是握手和公布 schema，不应该被真正的检索链启动成本拖慢；
- Windows 下 `subprocess.run(..., capture_output=True, timeout=10)` 对冷启动很敏感，
  如果在注册 tool 时就把重依赖全部 import 进来，MCP 冒烟测试会直接超时。

关键权衡：
- 这里牺牲了一点“所有东西都在模块顶层一次性导入”的直观性，
  换来更稳定的 stdio 冷启动；
- 真正执行业务 tool 时仍会加载目标模块，但这时已经处在明确的调用路径里，
  不再污染最小握手阶段。
"""

from __future__ import annotations

from typing import Any

from mcp_server.protocol_handler import ToolSpec

__all__ = [
    "create_get_document_summary_tool",
    "create_list_collections_tool",
    "create_query_knowledge_hub_tool",
]


def create_query_knowledge_hub_tool(**kwargs: Any) -> ToolSpec:
    """惰性构造 `query_knowledge_hub` tool。

    做什么：
    - 立即返回稳定的 `ToolSpec(name/description/inputSchema)`，让握手与 `tools/list` 不受重依赖影响；
    - 只有在 handler 第一次真正被调用时，才导入 `query_knowledge_hub` 模块并创建真实业务对象；
    - 首次创建完成后复用同一个底层 handler，避免每次请求都重复初始化。

    为什么：
    - 这个 tool 会间接拉起检索链、设置读取、响应构造等模块，是 MCP tools 中最重的一支；
    - `initialize` 阶段并不需要这些能力，只需要“告诉客户端这个 tool 存在且 schema 是什么”。

    关键权衡：
    - 为了冷启动性能，这里把静态 schema 和动态业务实现拆开；
    - schema 需要在这里保持一份轻量镜像，因此后续若修改底层 tool 契约，需要同步更新这份壳层定义。
    """
    tool_name = "query_knowledge_hub"
    description = "在知识库中执行混合检索并返回带引用的相关片段。"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "用户问题或检索表达式。"},
            "top_k": {"type": "integer", "minimum": 1, "description": "返回结果数量上限。"},
            "collection": {"type": "string", "description": "可选集合过滤条件。"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    cached_handler: dict[str, Any] = {}

    def _lazy_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        if "handler" not in cached_handler:
            # 只有真正收到 `tools/call(query_knowledge_hub)` 时，才支付检索链路的导入与实例化成本。
            from mcp_server.tools.query_knowledge_hub import create_query_knowledge_hub_tool as _impl

            cached_handler["handler"] = _impl(**kwargs).handler
        return cached_handler["handler"](arguments)

    return ToolSpec(
        name=tool_name,
        description=description,
        input_schema=input_schema,
        handler=_lazy_handler,
    )


def create_list_collections_tool(**kwargs: Any) -> ToolSpec:
    """惰性构造 `list_collections` tool。"""
    from mcp_server.tools.list_collections import create_list_collections_tool as _impl

    return _impl(**kwargs)


def create_get_document_summary_tool(**kwargs: Any) -> ToolSpec:
    """惰性构造 `get_document_summary` tool。"""
    from mcp_server.tools.get_document_summary import create_get_document_summary_tool as _impl

    return _impl(**kwargs)
