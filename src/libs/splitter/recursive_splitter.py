"""Recursive splitter implementation based on LangChain.

实现策略：
- 固定使用 `langchain_text_splitters.RecursiveCharacterTextSplitter`；
- 若环境缺少该依赖，初始化时直接抛出 ImportError，避免静默降级。
"""

from __future__ import annotations

from typing import Any

from libs.splitter.base_splitter import BaseSplitter

try:  # pragma: no cover - 依赖安装与否受环境影响
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]


class RecursiveSplitter(BaseSplitter):
    """默认递归切分器实现（基于 LangChain）。

    做什么：
    - 将较长文本切成可用于下游 embedding/retrieval 的片段；
    - 优先按更强语义边界切分（段落/换行/标点/空格）。

    为什么：
    - 对齐 B3 技术选型，复用成熟实现，降低自研切分算法维护成本。

    关键权衡：
    - 依赖外部库换取更稳定切分质量；
    - 依赖缺失时选择 fail-fast，而非本地降级，保证环境问题可见。

    失败路径：
    - 构造阶段缺依赖：抛 ImportError；
    - split 阶段若底层异常：包装为 RuntimeError 并附带配置上下文。
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must satisfy 0 <= chunk_overlap < chunk_size")

        if RecursiveCharacterTextSplitter is None:
            raise ImportError(
                "langchain-text-splitters is required for RecursiveSplitter. "
                "Install with: pip install langchain-text-splitters"
            )

        self.chunk_size = int(chunk_size)
        self.chunk_overlap = int(chunk_overlap)
        self.separators = separators or list(self.DEFAULT_SEPARATORS)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        """切分文本并返回非空 chunk 列表。"""
        normalized_text = self.validate_text(text)
        if not normalized_text.strip():
            return []

        try:
            chunks = self._splitter.split_text(normalized_text)
            if not chunks:
                # 极端边界下底层可能返回空；保持最小可用语义，避免上层拿到空结果。
                chunks = [normalized_text]
            return self.validate_chunks(chunks)
        except Exception as exc:  # pragma: no cover - 依赖库异常路径
            raise RuntimeError(
                "RecursiveSplitter failed to split text. "
                f"text_len={len(normalized_text)}, chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap}"
            ) from exc
