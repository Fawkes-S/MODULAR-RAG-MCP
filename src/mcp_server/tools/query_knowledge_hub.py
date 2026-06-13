"""MCP tool：知识库查询入口。"""

from __future__ import annotations

from typing import Any, Callable

from core.query_engine.hybrid_search import HybridSearch
from core.query_engine.reranker import RerankOutput, Reranker
from core.response.response_builder import ResponseBuilder
from core.settings import Settings, load_settings
from core.trace import TraceCollector
from core.trace.trace_context import TraceContext
from mcp_server.protocol_handler import ProtocolHandlerError, ToolSpec

SettingsLoader = Callable[[str], Settings]


class QueryKnowledgeHubTool:
    """`query_knowledge_hub` 的业务实现。

    做什么：
    - 校验 MCP `tools/call.arguments`；
    - 懒加载 settings/searcher/reranker；
    - 执行 HybridSearch -> Reranker -> ResponseBuilder 整条查询链路。

    为什么：
    - 这是 E3 暴露给 MCP Client 的主检索入口。
    - 采用懒加载能避免 server 刚启动时就加载 embedding 模型，降低 `initialize` 成本。

    关键权衡：
    - 参数问题返回 `-32602`，明确告诉调用方是请求写错了；
    - 内部系统错误继续抛出，由协议层统一转成 `-32603`，避免暴露实现细节。

    失败路径：
    - query/top_k/collection 不合法：抛 `ProtocolHandlerError(-32602, "Invalid params")`；
    - 检索链路异常：不在这里吞掉，让上层转标准 internal error；
    - 无结果：返回友好的成功响应，而不是异常。
    """

    NAME = "query_knowledge_hub"
    DESCRIPTION = "在知识库中执行混合检索并返回带引用的相关片段。"
    INPUT_SCHEMA: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "用户问题或检索表达式。"},
            "top_k": {"type": "integer", "minimum": 1, "description": "返回结果数量上限。"},
            "collection": {"type": "string", "description": "可选集合过滤条件。"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        settings_path: str = "config/settings.yaml",
        settings_loader: SettingsLoader | None = None,
        searcher: Any | None = None,
        reranker: Any | None = None,
        response_builder: ResponseBuilder | None = None,
        trace_collector: TraceCollector | None = None,
    ) -> None:
        self.settings_path = settings_path
        self.settings_loader = settings_loader or load_settings
        self.response_builder = response_builder or ResponseBuilder()
        self._settings: Settings | None = None
        self._searcher = searcher
        self._reranker = reranker
        self._trace_collector = trace_collector

    def handle(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行一次知识库查询并返回 MCP tool 结果。"""
        if not isinstance(arguments, dict):
            raise self._invalid_params()

        query = self._normalize_query(arguments.get("query"))
        collection = self._normalize_collection(arguments.get("collection"))
        top_k = self._normalize_top_k(arguments.get("top_k"))
        trace = TraceContext(trace_type="query")

        try:
            filters = {"collection": collection} if collection is not None else None
            retrieval_results = self._get_searcher().search(
                query=query,
                top_k=top_k,
                filters=filters,
                trace=trace,
            )
            rerank_output = self._get_reranker().rerank(
                query=query,
                candidates=retrieval_results,
                top_k=top_k,
                trace=trace,
            )

            return self.response_builder.build(
                rerank_output.results,
                query,
                extra=self._build_extra_payload(
                    collection=collection,
                    top_k=top_k,
                    trace=trace,
                    rerank_output=rerank_output,
                ),
            )
        finally:
            # Query 追踪页依赖 `traces.jsonl` 中存在 query 记录；
            # 因此 MCP 查询入口也必须像 CLI 一样在请求结束时统一收口并持久化 trace。
            self._get_trace_collector().collect(trace)

    def _get_settings(self) -> Settings:
        """懒加载配置，避免 `initialize/tools/list` 触发重型依赖初始化。"""
        if self._settings is None:
            self._settings = self.settings_loader(self.settings_path)
        return self._settings

    def _get_searcher(self) -> Any:
        if self._searcher is None:
            self._searcher = HybridSearch(settings=self._get_settings())
        return self._searcher

    def _get_reranker(self) -> Any:
        if self._reranker is None:
            self._reranker = Reranker(settings=self._get_settings())
        return self._reranker

    def _get_trace_collector(self) -> TraceCollector:
        if self._trace_collector is None:
            self._trace_collector = TraceCollector(trace_file=self._get_settings().observability.trace_file)
        return self._trace_collector

    @staticmethod
    def _build_extra_payload(
        *,
        collection: str | None,
        top_k: int,
        trace: TraceContext,
        rerank_output: RerankOutput,
    ) -> dict[str, Any]:
        return {
            "collection": collection,
            "top_k": top_k,
            "trace_id": trace.trace_id,
            "backend": rerank_output.backend,
            "fallback": rerank_output.fallback,
            "fallback_reason": rerank_output.fallback_reason,
        }

    @staticmethod
    def _normalize_query(raw_query: Any) -> str:
        if not isinstance(raw_query, str):
            raise QueryKnowledgeHubTool._invalid_params()
        normalized = " ".join(raw_query.strip().split())
        if not normalized:
            raise QueryKnowledgeHubTool._invalid_params()
        return normalized

    @staticmethod
    def _normalize_collection(raw_collection: Any) -> str | None:
        if raw_collection is None:
            return None
        if not isinstance(raw_collection, str):
            raise QueryKnowledgeHubTool._invalid_params()
        normalized = raw_collection.strip()
        return normalized or None

    def _normalize_top_k(self, raw_top_k: Any) -> int:
        if raw_top_k is None:
            return int(self._get_settings().retrieval.top_k)
        if not isinstance(raw_top_k, int) or raw_top_k <= 0:
            raise self._invalid_params()
        return raw_top_k

    @staticmethod
    def _invalid_params() -> ProtocolHandlerError:
        return ProtocolHandlerError(code=-32602, message="Invalid params")


def create_query_knowledge_hub_tool(
    *,
    settings_path: str = "config/settings.yaml",
    settings_loader: SettingsLoader | None = None,
    searcher: Any | None = None,
    reranker: Any | None = None,
    response_builder: ResponseBuilder | None = None,
    trace_collector: TraceCollector | None = None,
) -> ToolSpec:
    """构造可注册到 `ProtocolHandler` 的 ToolSpec。"""
    tool = QueryKnowledgeHubTool(
        settings_path=settings_path,
        settings_loader=settings_loader,
        searcher=searcher,
        reranker=reranker,
        response_builder=response_builder,
        trace_collector=trace_collector,
    )
    return ToolSpec(
        name=QueryKnowledgeHubTool.NAME,
        description=QueryKnowledgeHubTool.DESCRIPTION,
        input_schema=dict(QueryKnowledgeHubTool.INPUT_SCHEMA),
        handler=tool.handle,
    )
