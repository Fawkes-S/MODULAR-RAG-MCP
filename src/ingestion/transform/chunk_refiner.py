"""ChunkRefiner：规则去噪 + 可选 LLM 增强（C5）。"""

from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter

from core.prompt_loader import load_prompt_template
from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import Chunk
from ingestion.transform.base_transform import BaseTransform
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory


class ChunkRefiner(BaseTransform):
    """对 Chunk 文本做二次精炼。

    做什么：
    - 先执行规则去噪（空白规整、页眉页脚清理、HTML 标签/注释移除等）。
    - 在配置允许时调用 LLM 进一步润色文本可读性。
    - 无论 LLM 成功或失败，都返回可用结果并写入降级标记。

    为什么：
    - 规则层处理稳定、低成本，适合作为兜底。
    - LLM 层提升语义表达质量，但可能失败或超时，因此必须可降级。

    关键权衡：
    - 采用“规则优先 + LLM 可选增强”以平衡稳定性、成本与效果。
    - 为避免破坏结构，规则清理时对 fenced code block 采用分段保留策略。

    失败路径：
    - LLM 客户端初始化失败或调用失败：回退规则结果，不抛致命异常。
    - 单个 chunk 处理异常：仅该 chunk 回退原文，不影响其余 chunk。

    Args:
        settings: 强类型应用配置对象（`core.settings.Settings`）。
        llm: 可注入的 LLM 客户端（测试/定制场景）。
        prompt_path: 可选 prompt 文件路径；未提供则读取配置或默认路径。

    Example:
        >>> from core.settings import load_settings
        >>> settings = load_settings("config/settings.yaml")
        >>> refiner = ChunkRefiner(settings=settings)
        >>> refined = refiner.transform(chunks)
    """

    DEFAULT_PROMPT_PATH = Path("config/prompts/chunk_refinement.txt")
    DEFAULT_PROMPT_TEMPLATE = (
        "你是文档清洗助手。请在不改变事实的前提下，"
        "清理噪声并保持原有结构与术语。\n"
        "- 删除页眉页脚/无意义分隔符/重复空白\n"
        "- 保留代码块与列表结构\n"
        "- 不要编造不存在的信息\n\n"
        "原文：\n{text}"
    )

    _CODE_BLOCK_PATTERN = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)
    _HTML_COMMENT_PATTERN = re.compile(r"<!--([\s\S]*?)-->", re.MULTILINE)
    _HTML_TAG_PATTERN = re.compile(r"</?[A-Za-z][^>]*>")

    _PAGE_NOISE_PATTERNS = (
        # 经典页码：Page 1 / Page 1 of 3 / [ 2 / 9 ] / 第3页
        re.compile(r"^\s*page\s+\d+(\s*(?:of|/)\s*\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*\[\s*\d+\s*/\s*\d+\s*\]\s*$"),
        re.compile(r"^\s*第\s*\d+\s*页\s*$", re.IGNORECASE),
        # 扩展页眉：Page 42 | Technical Documentation / 第 3 页 | XXX
        re.compile(r"^\s*page\s+\d+(\s*(?:of|/)\s*\d+)?\s*(?:[|｜:：\-–—]\s*.+)\s*$", re.IGNORECASE),
        re.compile(r"^\s*第\s*\d+\s*页\s*(?:[|｜:：\-–—]\s*.+)\s*$", re.IGNORECASE),
    )

    _STRUCTURAL_NOISE_PATTERNS = (
        # 常见分隔线
        re.compile(r"^\s*[-_=~]{3,}\s*$"),
        # 盒绘制字符分隔线（OCR/PDF 常见）
        re.compile(r"^\s*[─━═│┃┄┅┈┉┊┋]{3,}\s*$"),
        # 纯符号标题线
        re.compile(r"^\s*[=*#]{6,}\s*$"),
    )

    _FOOTER_NOISE_PATTERNS = (
        re.compile(r"^\s*(?:footer|页脚)\s*[:：|].*$", re.IGNORECASE),
        re.compile(r"^\s*(?:copyright|©)\s*\d{2,4}.*$", re.IGNORECASE),
        re.compile(r"^\s*(?:all rights reserved|internal use only|confidential)\s*$", re.IGNORECASE),
        re.compile(r"^\s*.*\|\s*(?:confidential|internal use only)\s*$", re.IGNORECASE),
    )

    def __init__(
        self,
        settings: Settings,
        llm: BaseLLM | None = None,
        prompt_path: str | Path | None = None,
    ) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("ChunkRefiner requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.use_llm = bool(settings.ingestion.chunk_refiner.use_llm)

        configured_prompt_path = settings.ingestion.chunk_refiner.prompt_path.strip()
        effective_prompt_path: Path | str = (
            prompt_path
            if prompt_path is not None
            else configured_prompt_path or self.DEFAULT_PROMPT_PATH
        )

        self.prompt_template = load_prompt_template(
            prompt_path=effective_prompt_path,
            default_template=self.DEFAULT_PROMPT_TEMPLATE,
            required_placeholders=("text",),
            placeholder_append_blocks={"text": "\n\n原文：\n{text}"},
        )

        self.llm: BaseLLM | None = llm
        self._init_error_reason: str | None = None
        self._last_fallback_reason: str | None = None

        if self.use_llm and self.llm is None:
            try:
                self.llm = LLMFactory.create(settings)
            except Exception as exc:
                self.llm = None
                self._init_error_reason = f"llm_client_init_error:{type(exc).__name__}"

    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        """执行 Chunk 文本精炼并返回新 Chunk 列表。

        做什么：
        - 对每个 chunk 先做规则去噪。
        - 若开启 LLM，则尝试做二次润色；失败时回退规则结果。
        - 在 metadata 标注 `refined_by` 与可选降级原因，便于后续排障。

        为什么：
        - Ingestion 是批处理链路，单点失败不应阻塞整体吞吐。

        关键权衡：
        - 返回新的 `Chunk` 对象（而非原地修改），避免上游对象被隐式污染。

        失败路径：
        - 输入 shape 非法：直接抛 ValueError（调用方修复输入）。
        - 单条 chunk 处理异常：仅该条保留原文并写入 fallback 原因。

        Args:
            chunks: 待处理的 chunk 列表。
            trace: 可选追踪上下文，用于记录阶段统计。

        Returns:
            list[Chunk]: 精炼后的 chunk 列表，顺序与输入一致。
        """
        normalized_chunks = self.validate_chunks(chunks)
        stage_started = perf_counter()

        if not normalized_chunks:
            if trace is not None:
                trace.record_stage(
                    stage_name="transform.chunk_refiner",
                    details={"total": 0, "llm_success": 0, "rule_fallback": 0, "errors": 0},
                    elapsed_ms=0.0,
                )
            return []

        results: list[Chunk] = []
        stats = {"total": len(normalized_chunks), "llm_success": 0, "rule_fallback": 0, "errors": 0}

        for chunk in normalized_chunks:
            try:
                refined_text = self._rule_based_refine(chunk.text)
                output_text = refined_text
                metadata = dict(chunk.metadata)

                if self.use_llm:
                    llm_text = self._llm_refine(refined_text, trace=trace)
                    if llm_text is not None:
                        output_text = llm_text
                        metadata["refined_by"] = "llm"
                        metadata.pop("refine_fallback_reason", None)
                        stats["llm_success"] += 1
                    else:
                        metadata["refined_by"] = "rule"
                        metadata["refine_fallback_reason"] = (
                            self._last_fallback_reason or "llm_unavailable"
                        )
                        stats["rule_fallback"] += 1
                else:
                    metadata["refined_by"] = "rule"
                    metadata["refine_fallback_reason"] = "llm_disabled_by_settings"

                results.append(
                    Chunk(
                        id=chunk.id,
                        text=output_text,
                        metadata=metadata,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        source_ref=chunk.source_ref,
                    )
                )
            except Exception as exc:
                stats["errors"] += 1
                fallback_metadata = dict(chunk.metadata)
                fallback_metadata["refined_by"] = "rule"
                fallback_metadata["refine_fallback_reason"] = (
                    f"chunk_processing_error:{type(exc).__name__}"
                )

                results.append(
                    Chunk(
                        id=chunk.id,
                        text=chunk.text,
                        metadata=fallback_metadata,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        source_ref=chunk.source_ref,
                    )
                )

        if trace is not None:
            trace.record_stage(
                stage_name="transform.chunk_refiner",
                details=stats,
                elapsed_ms=(perf_counter() - stage_started) * 1000.0,
            )

        return results

    def _rule_based_refine(self, text: str) -> str:
        """执行规则去噪，并尽量保留 Markdown 与代码块结构。"""
        if not isinstance(text, str):
            raise ValueError("text must be string")
        if not text.strip():
            return ""

        segments = self._CODE_BLOCK_PATTERN.split(text)
        cleaned_segments: list[str] = []

        for idx, segment in enumerate(segments):
            # 奇数位是 fenced code block，原样保留，避免破坏缩进与语法。
            if idx % 2 == 1:
                cleaned_segments.append(segment)
                continue

            cleaned_segments.append(self._clean_non_code_segment(segment))

        merged = "".join(cleaned_segments)
        merged = merged.replace("\r\n", "\n").replace("\r", "\n")
        merged = re.sub(r"\n{3,}", "\n\n", merged)
        return merged.strip()

    def _llm_refine(self, text: str, trace: TraceContext | None = None) -> str | None:
        """调用 LLM 进行可选增强，失败时返回 None。"""
        _ = trace  # 预留参数，当前阶段仅保证签名兼容。

        if not self.use_llm:
            self._last_fallback_reason = "llm_disabled_by_settings"
            return None

        if self.llm is None:
            self._last_fallback_reason = self._init_error_reason or "llm_client_unavailable"
            return None

        try:
            prompt = self.prompt_template.format(text=text)
        except Exception:
            # 即使 prompt 模板格式不规范，也要保证可运行。
            prompt = f"{self.prompt_template}\n\n原文：\n{text}"

        messages = [
            {
                "role": "system",
                "content": "你是严谨的文档清洗助手，只输出清洗后的正文，不要解释。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.llm.chat(messages)
        except Exception as exc:
            summary = self._summarize_exception(exc)
            self._last_fallback_reason = f"llm_error:{type(exc).__name__}" + (f":{summary}" if summary else "")
            return None

        if not isinstance(response, str) or not response.strip():
            self._last_fallback_reason = "llm_empty_response"
            return None

        self._last_fallback_reason = None
        return response.strip()

    @staticmethod
    def _summarize_exception(exc: Exception, max_len: int = 80) -> str:
        """提取异常简短摘要，便于写入 fallback reason。"""
        text = str(exc).strip()
        if not text:
            return ""
        first_line = re.sub(r"\s+", " ", text.splitlines()[0]).strip()
        if len(first_line) <= max_len:
            return first_line
        return f"{first_line[: max_len - 1].rstrip()}…"

    def _clean_non_code_segment(self, segment: str) -> str:
        """清洗非代码段文本。

        做什么：
        - 统一换行与空白。
        - 去掉 HTML 注释与标签包装（保留标签内正文）。
        - 逐行过滤页眉/页脚/分隔线等格式噪声。
        """
        normalized = segment.replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        normalized = self._HTML_COMMENT_PATTERN.sub("", normalized)
        normalized = self._HTML_TAG_PATTERN.sub("", normalized)

        cleaned_lines: list[str] = []
        for raw_line in normalized.split("\n"):
            line = re.sub(r"[ \t]+", " ", raw_line).strip()

            if not line:
                cleaned_lines.append("")
                continue

            if self._is_noise_line(line):
                continue

            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    def _is_noise_line(self, line: str) -> bool:
        """判断单行是否属于可安全移除的格式噪声。"""
        if any(pattern.match(line) for pattern in self._PAGE_NOISE_PATTERNS):
            return True
        if any(pattern.match(line) for pattern in self._STRUCTURAL_NOISE_PATTERNS):
            return True
        if any(pattern.match(line) for pattern in self._FOOTER_NOISE_PATTERNS):
            return True

        # 兜底规则：明显页脚语义短句（保守匹配，降低误删正文风险）
        lowered = line.lower()
        if "confidential" in lowered and len(line) <= 120 and ("footer" in lowered or "|" in line):
            return True

        return False


