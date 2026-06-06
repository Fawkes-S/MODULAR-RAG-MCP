"""引用生成器：把检索结果转换为结构化引用。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.types import RetrievalResult


class CitationGenerator:
    """为检索结果生成稳定的 citations 列表。

    做什么：
    - 将 `RetrievalResult` 转换为 MCP 友好的结构化引用；
    - 统一抽取 `source/page/chunk_id/score` 等关键字段；
    - 额外补充 `source_label`，供 Markdown 直接展示。

    为什么：
    - E3 同时需要人可读的 Markdown 与程序可解析的 `structuredContent.citations`。
    - 如果每个 tool 自己拼引用，后续 E6 多模态扩展时会重复实现相同规则。

    关键权衡：
    - 当前只保留最稳定、最常用的引用字段，不做复杂文献格式化。
    - `source` 保留完整路径，`source_label` 提供简短文件名，两者分别服务机器和人。

    失败路径：
    - 输入不是 `list[RetrievalResult]` 时抛 `ValueError`，防止脏数据继续向上游传播。
    """

    def generate(self, retrieval_results: list[RetrievalResult]) -> list[dict[str, Any]]:
        """生成结构化引用列表。"""
        if not isinstance(retrieval_results, list):
            raise ValueError("retrieval_results must be list[RetrievalResult]")

        citations: list[dict[str, Any]] = []
        for index, item in enumerate(retrieval_results, start=1):
            if not isinstance(item, RetrievalResult):
                raise ValueError(f"retrieval_results[{index - 1}] must be RetrievalResult")

            source = str(item.metadata.get("source_path", "")).strip()
            page = item.metadata.get("page")
            citations.append(
                {
                    "index": index,
                    "source": source,
                    "source_label": Path(source).name if source else "unknown-source",
                    "page": int(page) if isinstance(page, int) else None,
                    "chunk_id": item.chunk_id,
                    "score": float(item.score),
                }
            )
        return citations
