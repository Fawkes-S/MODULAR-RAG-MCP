"""QueryKnowledgeHubTool 单元测试（G6）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.reranker import RerankOutput  # noqa: E402
from core.types import RetrievalResult  # noqa: E402
from mcp_server.tools.query_knowledge_hub import QueryKnowledgeHubTool  # noqa: E402


class _FakeSearcher:
    """测试桩：返回固定 hybrid 结果，并记录传入 trace。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: Any | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append({"query": query, "top_k": top_k, "filters": filters, "trace": trace})
        if trace is not None:
            trace.record_stage(
                stage_name="fusion",
                details={"method": "rrf", "provider": "RRFFusion", "top_k": top_k},
                elapsed_ms=1.0,
            )
        return [
            RetrievalResult(
                chunk_id="chunk_001",
                score=0.9,
                text="Azure OpenAI guide",
                metadata={"source_path": "docs/azure.pdf", "collection": "manual"},
            )
        ]


class _FakeReranker:
    """测试桩：原样返回结果，并补一条 rerank 阶段。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int | None = None,
        trace: Any | None = None,
    ) -> RerankOutput:
        self.calls.append({"query": query, "top_k": top_k, "trace": trace})
        if trace is not None:
            trace.record_stage(
                stage_name="rerank",
                details={"method": "backend_rerank_with_fallback", "provider": "ordered_backend", "top_k": top_k},
                elapsed_ms=2.0,
            )
        return RerankOutput(
            results=list(candidates[:top_k]),
            fallback=False,
            fallback_reason=None,
            backend="ordered_backend",
        )


class _FakeTraceCollector:
    """测试桩：记录 collect 是否被调用。"""

    def __init__(self) -> None:
        self.traces: list[Any] = []

    def collect(self, trace: Any) -> None:
        self.traces.append(trace)


class _FakeResponseBuilder:
    """测试桩：返回最小结构，避免把断言焦点放到 response 格式层。"""

    def build(self, retrieval_results: list[RetrievalResult], query: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": query}],
            "structuredContent": {"result_count": len(retrieval_results), **(extra or {})},
        }


def test_query_knowledge_hub_tool_collects_query_trace_after_handle() -> None:
    """
    Given:
        一个注入 fake searcher/reranker/response_builder/trace_collector 的 QueryKnowledgeHubTool。
    When:
        调用 `handle()` 执行一次查询。
    Then:
        - tool 应正常返回结果；
        - trace_collector 应在收口阶段被调用一次；
        - 被收集的 trace 应是 `trace_type == "query"`，且包含至少 `fusion/rerank` 阶段。
    """
    fake_searcher = _FakeSearcher()
    fake_reranker = _FakeReranker()
    fake_collector = _FakeTraceCollector()
    tool = QueryKnowledgeHubTool(
        searcher=fake_searcher,
        reranker=fake_reranker,
        response_builder=_FakeResponseBuilder(),  # type: ignore[arg-type]
        trace_collector=fake_collector,  # type: ignore[arg-type]
    )

    result = tool.handle({"query": "如何配置 Azure OpenAI", "top_k": 1, "collection": "manual"})

    assert result["structuredContent"]["trace_id"]
    assert len(fake_collector.traces) == 1
    trace = fake_collector.traces[0]
    assert trace.trace_type == "query"
    stage_names = [stage["stage_name"] for stage in trace.stages]
    assert "fusion" in stage_names
    assert "rerank" in stage_names
