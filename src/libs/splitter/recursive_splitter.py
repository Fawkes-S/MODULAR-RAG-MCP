"""Recursive splitter implementation.

优先使用 LangChain 的 `RecursiveCharacterTextSplitter`；当运行环境未安装对应依赖时，
回退到本地实现（尽量保留 Markdown 标题与代码块边界）。
"""

from __future__ import annotations

import re
from typing import Any

from libs.splitter.base_splitter import BaseSplitter

try:  # pragma: no cover - 依赖存在时走真实实现
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # pragma: no cover - 无依赖时走回退
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]


class RecursiveSplitter(BaseSplitter):
    """默认递归切分器实现。

    用途：
    - 将较长文本切成适合后续向量化与检索的块；
    - 优先保证 Markdown 结构（标题/代码块）不被随意打断。

    方法：
    - 若可用，调用 LangChain `RecursiveCharacterTextSplitter`；
    - 否则使用本地回退算法：先按代码块/标题切成语义单元，再按 chunk_size 组包。

    关键约束：
    - `chunk_size` 必须为正整数；
    - `chunk_overlap` 必须满足 `0 <= overlap < chunk_size`。
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
        use_langchain: bool = True,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must satisfy 0 <= chunk_overlap < chunk_size")

        self.chunk_size = int(chunk_size)
        self.chunk_overlap = int(chunk_overlap)
        self.separators = separators or ["\n\n", "\n", " ", ""]
        self.use_langchain = use_langchain

        self._langchain_splitter = None
        if self.use_langchain and RecursiveCharacterTextSplitter is not None:
            self._langchain_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
                length_function=len,
            )

    def split_text(self, text: str, trace: Any | None = None) -> list[str]:
        """切分文本并返回 chunk 列表。

        Args:
            text: 原始文本。
            trace: 预留链路追踪上下文（当前未使用）。

        Returns:
            list[str]: chunk 列表（已去除空白项）。
        """
        if not isinstance(text, str):
            raise ValueError("text must be str")
        if not text.strip():
            return []

        if self._langchain_splitter is not None:
            chunks = self._langchain_splitter.split_text(text)
            return [chunk for chunk in chunks if chunk and chunk.strip()]

        # 回退路径：尽量保留 Markdown 结构边界。
        units = self._split_markdown_units(text)
        return self._pack_units(units)

    def _split_markdown_units(self, text: str) -> list[str]:
        """先将文本拆为较稳定的 Markdown 单元。

        策略：
        - fenced code block(````...````) 作为独立单元保留；
        - 普通文本再按 heading（`^#{1,6} `）切段。
        """
        units: list[str] = []

        # 先把代码块切出来，避免后续 heading 正则误伤代码内容。
        parts = re.split(r"(```[\s\S]*?```)", text)
        for part in parts:
            if not part or not part.strip():
                continue
            if part.strip().startswith("```"):
                units.append(part.strip())
                continue

            # 非代码区按标题边界切分（保留标题与其内容在同一单元）。
            sections = re.split(r"(?m)(?=^#{1,6}\s+)", part)
            for section in sections:
                if section and section.strip():
                    units.append(section.strip())

        return units

    def _pack_units(self, units: list[str]) -> list[str]:
        """将语义单元打包成不超过 chunk_size 的块。"""
        chunks: list[str] = []
        current = ""

        for unit in units:
            # fenced code block 即使超长也保持为原子单元，避免把 ``` 围栏打断。
            is_fenced_code = unit.strip().startswith("```") and unit.strip().endswith("```")
            if len(unit) > self.chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                if is_fenced_code:
                    chunks.append(unit)
                else:
                    chunks.extend(self._split_long_text(unit))
                continue

            candidate = unit if not current else f"{current}\n\n{unit}"
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = unit

        if current:
            chunks.append(current)

        return [chunk for chunk in chunks if chunk.strip()]

    def _split_long_text(self, text: str) -> list[str]:
        """按字符窗口切分超长单元。"""
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size

        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            pieces.append(text[start:end])
            if end >= len(text):
                break
            start += step
        return pieces

