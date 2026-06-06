"""响应构建器：把检索结果包装为 MCP tool 返回体。"""

from __future__ import annotations

from typing import Any

from core.response.citation_generator import CitationGenerator
from core.types import RetrievalResult


class ResponseBuilder:
    """构建 `query_knowledge_hub` 的最终响应。

    做什么：
    - 把命中结果渲染成一段可直接展示的 Markdown；
    - 生成 `structuredContent.citations` 与 `structuredContent.results`；
    - 在无结果或重排回退时补充友好提示。

    为什么：
    - MCP 客户端既可能直接展示文本，也可能读取结构化字段做二次渲染。
    - 把响应拼装集中在这里，可以避免 tool 层重复处理格式细节。

    关键权衡：
    - 当前阶段不做答案生成，只返回相关片段与引用，优先保证可追溯性。
    - 片段文本做轻量裁剪，避免一次响应塞入大段 chunk 导致可读性变差。

    失败路径：
    - 输入 shape 非法时抛 `ValueError`；
    - 无结果不是异常，而是返回业务友好的成功响应。
    """

    def __init__(
        self,
        citation_generator: CitationGenerator | None = None,
        max_snippet_chars: int = 220,
    ) -> None:
        if not isinstance(max_snippet_chars, int) or max_snippet_chars <= 0:
            raise ValueError("max_snippet_chars must be positive int")
        self.citation_generator = citation_generator or CitationGenerator()
        self.max_snippet_chars = max_snippet_chars

    def build(
        self,
        retrieval_results: list[RetrievalResult],
        query: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建 MCP tool 返回体。"""
        normalized_query = self._normalize_query(query)
        normalized_results = self._normalize_results(retrieval_results)
        citations = self.citation_generator.generate(normalized_results)

        structured_content = {
            "query": normalized_query,
            "result_count": len(normalized_results),
            "citations": citations,
            "results": [item.to_dict() for item in normalized_results],
        }
        if isinstance(extra, dict) and extra:
            structured_content.update(dict(extra))

        markdown = (
            self._build_empty_markdown(normalized_query)
            if not normalized_results
            else self._build_result_markdown(normalized_query, normalized_results, citations, extra=extra)
        )

        return {
            "content": [{"type": "text", "text": markdown}],
            "structuredContent": structured_content,
        }

    @staticmethod
    def _normalize_query(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("query must be non-empty string")
        normalized = " ".join(query.strip().split())
        if not normalized:
            raise ValueError("query must be non-empty string")
        return normalized

    @staticmethod
    def _normalize_results(retrieval_results: list[RetrievalResult]) -> list[RetrievalResult]:
        if not isinstance(retrieval_results, list):
            raise ValueError("retrieval_results must be list[RetrievalResult]")
        normalized: list[RetrievalResult] = []
        for index, item in enumerate(retrieval_results):
            if not isinstance(item, RetrievalResult):
                raise ValueError(f"retrieval_results[{index}] must be RetrievalResult")
            normalized.append(item)
        return normalized

    def _build_empty_markdown(self, query: str) -> str:
        """构建无命中提示。"""
        return (
            f"未在知识库中找到与“{query}”直接相关的内容。\n\n"
            "建议：\n"
            "1. 尝试换一个更具体的关键词。\n"
            "2. 如果你知道文档集合，可追加 collection 过滤。\n"
            "3. 先确认目标文档已经完成 ingest。"
        )

    def _build_result_markdown(
        self,
        query: str,
        retrieval_results: list[RetrievalResult],
        citations: list[dict[str, Any]],
        *,
        extra: dict[str, Any] | None,
    ) -> str:
        """构建命中结果 Markdown。"""
        lines = [f"以下是与“{query}”最相关的知识片段：", ""]

        rerank_note = self._build_rerank_note(extra)
        if rerank_note:
            lines.extend([rerank_note, ""])

        for item, citation in zip(retrieval_results, citations, strict=False):
            lines.append(f"{citation['index']}. {self._clip_text(item.text)} [{citation['index']}]")

        lines.extend(["", "引用："])
        for citation in citations:
            page_suffix = f" | page {citation['page']}" if citation["page"] is not None else ""
            lines.append(
                f"[{citation['index']}] {citation['source_label']}{page_suffix} | "
                f"chunk_id={citation['chunk_id']} | score={citation['score']:.4f}"
            )

        return "\n".join(lines)

    @staticmethod
    def _build_rerank_note(extra: dict[str, Any] | None) -> str:
        if not isinstance(extra, dict):
            return ""
        backend = str(extra.get("backend", "")).strip()
        fallback = bool(extra.get("fallback", False))
        if fallback:
            return f"> 重排后端 `{backend or 'unknown'}` 不可用，本次结果已回退为 fusion 原始顺序。"
        if backend and backend.lower() != "none":
            return f"> 结果已通过重排后端 `{backend}` 做进一步排序。"
        return ""

    def _clip_text(self, text: str) -> str:
        """裁剪片段文本，避免响应过长。"""
        normalized = " ".join(str(text).split())
        if len(normalized) <= self.max_snippet_chars:
            return normalized
        return normalized[: self.max_snippet_chars - 3].rstrip() + "..."
