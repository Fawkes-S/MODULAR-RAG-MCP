"""MetadataEnricher：规则增强 + 可选 LLM 增强（C6）。"""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any

from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import Chunk
from ingestion.transform.base_transform import BaseTransform
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory


class MetadataEnricher(BaseTransform):
    """为每个 Chunk 生成语义元数据（title/summary/tags）。

    做什么：
    - 先执行规则增强，保证 `title/summary/tags` 三个字段始终可用（兜底契约）。
    - 当配置开启 `use_llm` 时，尝试调用 LLM 产出更语义化的元数据。
    - LLM 失败时自动降级到规则结果，不中断 ingestion 流程。

    为什么：
    - 元数据增强属于“提升质量”的步骤，不应成为主链路单点故障。
    - 通过“规则保底 + LLM 增强”可以同时兼顾稳定性与效果上限。

    关键权衡：
    - 规则增强可解释、低成本，但语义表达能力有限。
    - LLM 增强效果更好，但存在网络/限流/输出格式不稳定风险。
    - 当前实现优先保证稳定契约（字段必有），再逐步提升语义质量。

    失败路径：
    - LLM 客户端初始化失败：记录 fallback 原因并回退规则增强。
    - LLM 调用异常/返回格式非法：回退规则增强并记录具体原因。
    - 单个 Chunk 处理异常：仅该 Chunk 回退，不影响其他 Chunk。
    """

    _JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    _JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")
    _EN_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
    _ZH_WORD_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,8}")
    _STOPWORDS = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "are",
        "was",
        "were",
        "you",
        "your",
        "chunk",
        "document",
        "section",
        "metadata",
        "以及",
        "一个",
        "我们",
        "你们",
        "这些",
        "这个",
        "进行",
        "相关",
    }

    def __init__(self, settings: Settings, llm: BaseLLM | None = None) -> None:
        if not isinstance(settings, Settings):
            raise TypeError(
                "MetadataEnricher requires Settings; call load_settings('config/settings.yaml') first"
            )

        self.settings = settings
        self.use_llm = bool(settings.ingestion.metadata_enricher.use_llm)
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
        """执行元数据增强并返回新 Chunk 列表。

        做什么：
        - 对每个 Chunk 先产出规则增强结果。
        - 若 `use_llm=true`，再尝试 LLM 增强并覆盖规则结果。
        - 无论是否发生异常，都保证输出 metadata 含 `title/summary/tags`。

        为什么：
        - Transform 链路要求可插拔且具备降级能力，避免单步失败阻塞整体摄取。

        关键权衡：
        - 不直接修改输入 Chunk，而是返回新对象，减少上游对象被污染的风险。
        - trace 记录聚焦统计指标，避免引入高耦合日志协议。

        失败路径：
        - 输入 shape 非法：直接抛出 ValueError（调用方需修复）。
        - 单条处理异常：该条回退规则输出并记录 `enrich_fallback_reason`。

        Args:
            chunks: 待增强的 Chunk 列表。
            trace: 可选追踪上下文，用于记录阶段统计。

        Returns:
            list[Chunk]: 与输入顺序一致的增强结果。
        """
        normalized_chunks = self.validate_chunks(chunks)
        started = perf_counter()

        if not normalized_chunks:
            if trace is not None:
                trace.record_stage(
                    stage_name="transform.metadata_enricher",
                    details={"total": 0, "llm_success": 0, "rule_fallback": 0, "errors": 0},
                    elapsed_ms=0.0,
                )
            return []

        stats = {"total": len(normalized_chunks), "llm_success": 0, "rule_fallback": 0, "errors": 0}
        results: list[Chunk] = []

        for chunk in normalized_chunks:
            try:
                metadata = self._rule_enrich(chunk.text, chunk.metadata)

                if self.use_llm:
                    llm_metadata = self._llm_enrich(chunk.text, metadata, trace=trace)
                    if llm_metadata is not None:
                        metadata.update(llm_metadata)
                        metadata["enriched_by"] = "llm"
                        metadata.pop("enrich_fallback_reason", None)
                        stats["llm_success"] += 1
                    else:
                        metadata["enriched_by"] = "rule"
                        metadata["enrich_fallback_reason"] = (
                            self._last_fallback_reason or "llm_unavailable"
                        )
                        stats["rule_fallback"] += 1
                else:
                    metadata["enriched_by"] = "rule"
                    metadata["enrich_fallback_reason"] = "llm_disabled_by_settings"

                metadata = self._ensure_required_fields(metadata=metadata, text=chunk.text)
                results.append(self._copy_chunk_with_metadata(chunk, metadata))
            except Exception as exc:
                stats["errors"] += 1
                fallback_metadata = self._ensure_required_fields(
                    metadata=dict(chunk.metadata),
                    text=chunk.text,
                )
                fallback_metadata["enriched_by"] = "rule"
                fallback_metadata["enrich_fallback_reason"] = (
                    f"chunk_processing_error:{type(exc).__name__}"
                )
                results.append(self._copy_chunk_with_metadata(chunk, fallback_metadata))

        if trace is not None:
            trace.record_stage(
                stage_name="transform.metadata_enricher",
                details={
                    **stats,
                    "llm_enabled": self.use_llm,
                    "llm_provider": self.settings.llm.provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return results

    @staticmethod
    def _copy_chunk_with_metadata(chunk: Chunk, metadata: dict[str, Any]) -> Chunk:
        """复制 Chunk 并替换 metadata。"""
        return Chunk(
            id=chunk.id,
            text=chunk.text,
            metadata=metadata,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            source_ref=chunk.source_ref,
        )

    def _rule_enrich(self, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """规则增强：保证三个核心字段可用。"""
        enriched = dict(metadata)
        enriched["title"] = self._derive_title(text=text, metadata=enriched)
        enriched["summary"] = self._derive_summary(text=text, metadata=enriched)
        enriched["tags"] = self._derive_tags(text=text, metadata=enriched)
        return enriched

    def _llm_enrich(
        self,
        text: str,
        rule_metadata: dict[str, Any],
        trace: TraceContext | None = None,
    ) -> dict[str, Any] | None:
        """调用 LLM 生成更语义化的 title/summary/tags，失败返回 None。"""
        _ = trace
        if not self.use_llm:
            self._last_fallback_reason = "llm_disabled_by_settings"
            return None
        if self.llm is None:
            self._last_fallback_reason = self._init_error_reason or "llm_client_unavailable"
            return None

        prompt = self._build_llm_prompt(text=text, rule_metadata=rule_metadata)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是文档元数据增强助手。请仅返回 JSON 对象，字段必须包含 "
                    "title(字符串)、summary(字符串)、tags(字符串数组)。不要输出解释。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.llm.chat(messages)
        except Exception as exc:
            summary = self._summarize_exception(exc)
            self._last_fallback_reason = f"llm_error:{type(exc).__name__}" + (f":{summary}" if summary else "")
            return None

        payload = self._parse_json_response(response)
        if payload is None:
            self._last_fallback_reason = "llm_response_parse_error"
            return None

        title = str(payload.get("title", "")).strip()
        summary = str(payload.get("summary", "")).strip()
        tags = self._normalize_tags(payload.get("tags"))

        merged = {
            "title": title or str(rule_metadata.get("title", "")).strip(),
            "summary": summary or str(rule_metadata.get("summary", "")).strip(),
            "tags": tags or self._normalize_tags(rule_metadata.get("tags")),
        }
        merged = self._ensure_required_fields(metadata=merged, text=text)

        self._last_fallback_reason = None
        return {
            "title": merged["title"],
            "summary": merged["summary"],
            "tags": merged["tags"],
        }


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

    def _build_llm_prompt(self, text: str, rule_metadata: dict[str, Any]) -> str:
        """构造 LLM 增强 prompt。"""
        fallback_title = str(rule_metadata.get("title", "")).strip()
        fallback_summary = str(rule_metadata.get("summary", "")).strip()
        fallback_tags = ", ".join(self._normalize_tags(rule_metadata.get("tags")))
        return (
            "请基于以下文本生成更准确的元数据。\n"
            "输出要求：\n"
            "1) 仅输出 JSON 对象。\n"
            "2) 必须包含 title/summary/tags 三个字段。\n"
            "3) title 不超过 80 字；summary 控制在 1-2 句；tags 3-6 个。\n"
            "4) 不要编造文本中不存在的信息。\n\n"
            f"规则兜底 title: {fallback_title}\n"
            f"规则兜底 summary: {fallback_summary}\n"
            f"规则兜底 tags: {fallback_tags}\n\n"
            "原文：\n"
            f"{text}"
        )

    def _ensure_required_fields(self, metadata: dict[str, Any], text: str) -> dict[str, Any]:
        """确保 metadata 至少包含非空 title/summary/tags。"""
        normalized = dict(metadata)

        title = str(normalized.get("title", "")).strip()
        if not title:
            title = self._derive_title(text=text, metadata=normalized)
        normalized["title"] = title or "Untitled"

        summary = str(normalized.get("summary", "")).strip()
        if not summary:
            summary = self._derive_summary(text=text, metadata=normalized)
        normalized["summary"] = summary or "No summary available."

        tags = self._normalize_tags(normalized.get("tags"))
        if not tags:
            tags = self._derive_tags(text=text, metadata=normalized)
        normalized["tags"] = tags or ["general"]

        return normalized

    def _derive_title(self, text: str, metadata: dict[str, Any]) -> str:
        """规则提取标题：优先 metadata，其次首个有效标题行。"""
        existing = str(metadata.get("title", "")).strip()
        if existing:
            return self._truncate(existing, max_length=80)

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("[IMAGE:"):
                continue
            if line.startswith("#"):
                line = line.lstrip("#").strip()
            if line:
                return self._truncate(line, max_length=80)

        source_path = str(metadata.get("source_path", "")).strip()
        if source_path:
            filename = source_path.replace("\\", "/").split("/")[-1].strip()
            if filename:
                return self._truncate(filename, max_length=80)
        return "Untitled"

    def _derive_summary(self, text: str, metadata: dict[str, Any]) -> str:
        """规则提取摘要：优先 metadata，其次提取正文前两句。"""
        existing = str(metadata.get("summary", "")).strip()
        if existing:
            return self._truncate(existing, max_length=220)

        cleaned = self._normalize_plain_text(text)
        if not cleaned:
            return "No summary available."

        pieces = re.split(r"(?<=[。！？.!?])\s+|\n+", cleaned)
        selected: list[str] = []
        current_len = 0
        for piece in pieces:
            sentence = piece.strip()
            if not sentence:
                continue
            selected.append(sentence)
            current_len += len(sentence)
            if len(selected) >= 2 or current_len >= 180:
                break

        summary = " ".join(selected).strip()
        if not summary:
            summary = cleaned
        return self._truncate(summary, max_length=220)

    def _derive_tags(self, text: str, metadata: dict[str, Any]) -> list[str]:
        """规则提取标签：优先 metadata，再从文本中提取关键词。"""
        existing = self._normalize_tags(metadata.get("tags"))
        if existing:
            return existing

        candidates: list[str] = []
        doc_type = str(metadata.get("doc_type", "")).strip()
        if doc_type:
            candidates.append(doc_type.lower())

        for token in self._EN_WORD_PATTERN.findall(text):
            normalized = token.lower()
            if normalized in self._STOPWORDS:
                continue
            candidates.append(normalized)

        for token in self._ZH_WORD_PATTERN.findall(text):
            if token in self._STOPWORDS:
                continue
            candidates.append(token)

        return self._normalize_tags(candidates) or ["general"]

    @staticmethod
    def _normalize_plain_text(text: str) -> str:
        """清理换行与多余空白，得到用于规则摘要的纯文本。"""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines: list[str] = []
        for raw_line in normalized.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("[IMAGE:"):
                continue
            line = line.lstrip("#").strip()
            if line:
                lines.append(line)
        return re.sub(r"\s+", " ", " ".join(lines)).strip()

    def _normalize_tags(self, value: Any) -> list[str]:
        """将 tags 归一化为去重后的字符串列表。"""
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, list):
            raw_items = [item for item in value if isinstance(item, str)]
        else:
            raw_items = []

        result: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            tag = item.strip().lower()
            if not tag or tag in seen:
                continue
            seen.add(tag)
            result.append(self._truncate(tag, max_length=24))
            if len(result) >= 8:
                break
        return result

    def _parse_json_response(self, response: Any) -> dict[str, Any] | None:
        """从 LLM 响应中解析 JSON 对象。"""
        if not isinstance(response, str) or not response.strip():
            return None

        candidates: list[str] = [response.strip()]
        block_match = self._JSON_BLOCK_PATTERN.search(response)
        if block_match:
            candidates.insert(0, block_match.group(1).strip())

        object_match = self._JSON_OBJECT_PATTERN.search(response)
        if object_match:
            candidates.append(object_match.group(0).strip())

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except Exception:
                continue
            if isinstance(payload, dict):
                return dict(payload)

        return None

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """截断字符串长度，保证输出稳定。"""
        if len(text) <= max_length:
            return text
        return f"{text[: max_length - 1].rstrip()}…"


