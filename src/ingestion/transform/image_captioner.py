"""ImageCaptioner：基于 Vision LLM 的图片描述增强（C7）。"""

from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

from core.prompt_loader import load_prompt_template
from core.settings import Settings
from core.trace.trace_context import TraceContext
from core.types import Chunk
from ingestion.transform.base_transform import BaseTransform
from libs.llm.base_vision_llm import BaseVisionLLM
from libs.llm.llm_factory import LLMFactory


class ImageCaptioner(BaseTransform):
    """为含图片引用的 Chunk 生成可检索描述文本。

    做什么：
    - 读取 chunk 中的 `image_refs` 与对应图片路径，按引用调用 Vision LLM 生成描述。
    - 将描述写回 `metadata.image_captions`，并注入正文占位符附近，提升后续检索命中率。
    - 当配置禁用、客户端不可用或调用失败时，保留 `image_refs` 并标记
      `has_unprocessed_images=true`，保证 ingestion 主链路不中断。

    为什么：
    - 项目在 C7 采用 Image-to-Text 路线，把视觉信息转成文本复用现有 RAG 链路。
    - 图片描述属于“增强能力”，不应成为摄取流程的单点故障。

    关键权衡：
    - 采用“可用即增强、失败即降级”的策略，优先保障稳定吞吐。
    - 描述注入采用“占位符旁追加描述”而非替换原占位符，便于后续继续定位图片引用。
    - 对已存在 caption 的图片直接复用，避免重复调用 Vision LLM，降低成本并增强幂等性。

    失败路径：
    - Vision LLM 初始化失败：记录 `caption_fallback_reason` 并整体降级。
    - 单张图片处理失败：仅该图片标记未处理，不影响同 chunk 的其他图片。
    - 单个 chunk 处理异常：该 chunk 回退原文并标记 `has_unprocessed_images=true`。

    Args:
        settings: 全局强类型配置。
        vision_llm: 可注入 Vision LLM（测试或定制场景）。
        prompt_path: 可选 prompt 文件路径；未指定则使用默认路径。
    """

    DEFAULT_PROMPT_PATH = Path("config/prompts/image_captioning.txt")
    DEFAULT_PROMPT_TEMPLATE = (
        "你是文档图片理解助手。请基于图片和上下文，输出一段可检索的中文描述。\n"
        "输出要求：\n"
        "1) 只输出描述正文，不要解释和前缀。\n"
        "2) 优先描述图中关键信息、结构关系、数字/指标（如可见）。\n"
        "3) 不要编造图片中不存在的信息。\n"
        "4) 控制在 40~180 字。\n\n"
        "图片ID：{image_id}\n"
        "前文：{context_before}\n"
        "后文：{context_after}\n"
        "当前Chunk：\n{chunk_text}"
    )

    _IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\[IMAGE:\s*([^\]\s]+)\s*\]")
    _CAPTION_BLOCK_PATTERN_TEMPLATE = (
        r"\[IMAGE:\s*{image_id}\s*\](?:\s*\n?\[图片描述:\s*[^\n\]]*\])?"
    )

    def __init__(
        self,
        settings: Settings,
        vision_llm: BaseVisionLLM | None = None,
        prompt_path: str | Path | None = None,
    ) -> None:
        if not isinstance(settings, Settings):
            raise TypeError(
                "ImageCaptioner requires Settings; call load_settings('config/settings.yaml') first"
            )

        self.settings = settings
        self.vision_enabled = bool(settings.vision_llm.enabled)

        effective_prompt_path: Path | str = (
            prompt_path if prompt_path is not None else self.DEFAULT_PROMPT_PATH
        )
        self.prompt_template = load_prompt_template(
            prompt_path=effective_prompt_path,
            default_template=self.DEFAULT_PROMPT_TEMPLATE,
            required_placeholders=("image_id", "context_before", "context_after", "chunk_text"),
            placeholder_append_blocks={
                "image_id": "\n\n图片ID：{image_id}",
                "context_before": "\n前文：{context_before}",
                "context_after": "\n后文：{context_after}",
                "chunk_text": "\n当前Chunk：\n{chunk_text}",
            },
        )

        self.vision_llm: BaseVisionLLM | None = vision_llm
        self._init_error_reason: str | None = None
        self._last_fallback_reason: str | None = None

        if self.vision_enabled and self.vision_llm is None:
            try:
                self.vision_llm = LLMFactory.create_vision_llm(settings)
            except Exception as exc:
                self.vision_llm = None
                self._init_error_reason = f"vision_llm_client_init_error:{type(exc).__name__}"

    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        """对 Chunk 列表执行图片描述增强。

        做什么：
        - 遍历 chunk，按 `image_refs` 生成/复用 caption，并注入 metadata 与正文。
        - 统计处理数量、降级数量和异常数量，便于 trace 观测。

        为什么：
        - C7 要求“可选 caption + 降级不阻塞”，因此方法必须保证始终返回可用结果。

        关键权衡：
        - 输入为 `list[Chunk]` 时，采用“新对象返回”而非原地修改，避免上游数据被污染。
        - 在降级场景下保留 `image_refs`，为后续补偿处理提供锚点。

        失败路径：
        - 输入 shape 非法时抛 ValueError；
        - chunk 内局部异常时仅回退该 chunk，不中断整个批次。

        Args:
            chunks: 待处理 chunk 列表。
            trace: 可选追踪上下文。

        Returns:
            list[Chunk]: 处理后的 chunk 列表，顺序与输入一致。
        """
        normalized_chunks = self.validate_chunks(chunks)
        started = perf_counter()

        if not normalized_chunks:
            if trace is not None:
                trace.record_stage(
                    stage_name="transform.image_captioner",
                    details={
                        "total": 0,
                        "chunks_with_images": 0,
                        "image_refs_total": 0,
                        "captioned_images": 0,
                        "fallback_images": 0,
                        "errors": 0,
                    },
                    elapsed_ms=0.0,
                )
            return []

        stats = {
            "total": len(normalized_chunks),
            "chunks_with_images": 0,
            "image_refs_total": 0,
            "captioned_images": 0,
            "fallback_images": 0,
            "errors": 0,
        }
        results: list[Chunk] = []

        for chunk in normalized_chunks:
            try:
                out_chunk, chunk_stats = self._process_chunk(chunk=chunk, trace=trace)
                results.append(out_chunk)
                for key, value in chunk_stats.items():
                    stats[key] += int(value)
            except Exception as exc:
                stats["errors"] += 1
                fallback_metadata = dict(chunk.metadata)
                refs = self._normalize_image_refs(fallback_metadata.get("image_refs"))
                fallback_metadata["image_refs"] = refs
                if refs:
                    fallback_metadata["has_unprocessed_images"] = True
                    fallback_metadata["captioned_by"] = "rule"
                    fallback_metadata["caption_fallback_reason"] = (
                        f"chunk_processing_error:{type(exc).__name__}"
                    )
                results.append(self._copy_chunk(chunk=chunk, text=chunk.text, metadata=fallback_metadata))

        if trace is not None:
            trace.record_stage(
                stage_name="transform.image_captioner",
                details={
                    **stats,
                    "vision_enabled": self.vision_enabled,
                    "vision_provider": self.settings.vision_llm.provider,
                },
                elapsed_ms=(perf_counter() - started) * 1000.0,
            )

        return results

    def _process_chunk(
        self,
        chunk: Chunk,
        trace: TraceContext | None = None,
    ) -> tuple[Chunk, dict[str, int]]:
        """处理单个 chunk，并返回处理统计。"""
        _ = trace
        metadata = dict(chunk.metadata)
        refs = self._normalize_image_refs(metadata.get("image_refs"))
        metadata["image_refs"] = refs

        chunk_stats = {
            "chunks_with_images": 0,
            "image_refs_total": 0,
            "captioned_images": 0,
            "fallback_images": 0,
        }
        if not refs:
            return self._copy_chunk(chunk=chunk, text=chunk.text, metadata=metadata), chunk_stats

        chunk_stats["chunks_with_images"] = 1
        chunk_stats["image_refs_total"] = len(refs)

        image_map = self._build_image_map(metadata.get("images"))
        captions = self._normalize_image_captions(metadata.get("image_captions"))
        unresolved_refs: list[str] = []
        output_text = chunk.text

        for image_id in refs:
            caption = captions.get(image_id, "")
            if not caption:
                generated = self._generate_caption(
                    image_id=image_id,
                    image_map=image_map,
                    chunk_text=chunk.text,
                    trace=trace,
                )
                if generated:
                    captions[image_id] = generated
                    caption = generated

            if caption:
                output_text = self._inject_caption(text=output_text, image_id=image_id, caption=caption)
                chunk_stats["captioned_images"] += 1
            else:
                unresolved_refs.append(image_id)
                chunk_stats["fallback_images"] += 1

        if captions:
            metadata["image_captions"] = captions
            metadata["captioned_by"] = "vision_llm" if not unresolved_refs else "vision_llm_partial"
        else:
            metadata.pop("image_captions", None)
            metadata["captioned_by"] = "rule"

        if unresolved_refs:
            metadata["has_unprocessed_images"] = True
            reason = self._last_fallback_reason or "vision_llm_unavailable"
            metadata["caption_fallback_reason"] = reason
        else:
            metadata.pop("has_unprocessed_images", None)
            metadata.pop("caption_fallback_reason", None)

        return self._copy_chunk(chunk=chunk, text=output_text, metadata=metadata), chunk_stats

    def _generate_caption(
        self,
        image_id: str,
        image_map: dict[str, dict[str, Any]],
        chunk_text: str,
        trace: TraceContext | None = None,
    ) -> str | None:
        """调用 Vision LLM 为指定图片生成 caption。"""
        if not self.vision_enabled:
            self._last_fallback_reason = "vision_llm_disabled_by_settings"
            return None

        if self.vision_llm is None:
            self._last_fallback_reason = self._init_error_reason or "vision_llm_client_unavailable"
            return None

        image = image_map.get(image_id)
        if image is None:
            self._last_fallback_reason = f"image_ref_not_found:{image_id}"
            return None

        image_path = image.get("path")
        if not isinstance(image_path, str) or not image_path.strip():
            self._last_fallback_reason = f"image_path_missing:{image_id}"
            return None

        prompt = self._build_prompt(image_id=image_id, chunk_text=chunk_text)
        try:
            response = self.vision_llm.chat_with_image(
                text=prompt,
                image_path=image_path,
                trace=trace,
            )
        except Exception as exc:
            summary = self._summarize_exception(exc)
            suffix = f":{summary}" if summary else ""
            self._last_fallback_reason = f"vision_llm_error:{type(exc).__name__}{suffix}"
            return None

        content = getattr(response, "content", None)
        if not isinstance(content, str) or not content.strip():
            self._last_fallback_reason = "vision_llm_empty_response"
            return None

        caption = self._normalize_caption(content)
        if not caption:
            self._last_fallback_reason = "vision_llm_empty_response"
            return None

        self._last_fallback_reason = None
        return caption

    def _build_prompt(self, image_id: str, chunk_text: str) -> str:
        """构造图像理解 prompt，包含占位符附近上下文。"""
        context_before, context_after = self._extract_context_around_image(
            text=chunk_text,
            image_id=image_id,
            max_chars=180,
        )

        try:
            return self.prompt_template.format(
                image_id=image_id,
                context_before=context_before,
                context_after=context_after,
                chunk_text=chunk_text,
            )
        except Exception:
            # Prompt 模板即便被误改，也应保障可运行并降级到最小可用提示。
            return (
                "请描述图片关键内容，不要编造。\n"
                f"图片ID：{image_id}\n"
                f"前文：{context_before}\n"
                f"后文：{context_after}\n"
                f"当前Chunk：\n{chunk_text}"
            )

    @classmethod
    def _extract_context_around_image(cls, text: str, image_id: str, max_chars: int) -> tuple[str, str]:
        """提取图片占位符前后文，用于增强 Vision LLM 的语境理解。"""
        placeholder_pattern = re.compile(rf"\[IMAGE:\s*{re.escape(image_id)}\s*\]")
        match = placeholder_pattern.search(text)
        if match is None:
            compact = cls._compact_whitespace(text)
            snippet = compact[-max_chars:] if len(compact) > max_chars else compact
            return snippet, ""

        before = cls._compact_whitespace(text[: match.start()])
        after = cls._compact_whitespace(text[match.end() :])
        if len(before) > max_chars:
            before = before[-max_chars:]
        if len(after) > max_chars:
            after = after[:max_chars]
        return before, after

    @classmethod
    def _inject_caption(cls, text: str, image_id: str, caption: str) -> str:
        """将图片描述稳定注入占位符附近，避免重复注入。"""
        caption_block = f"[IMAGE: {image_id}]\n[图片描述: {caption}]"
        block_pattern = re.compile(
            cls._CAPTION_BLOCK_PATTERN_TEMPLATE.format(image_id=re.escape(image_id))
        )
        replaced = block_pattern.sub(caption_block, text)

        if replaced != text:
            return replaced

        if caption_block in text:
            return text

        if not text.strip():
            return caption_block

        return f"{text.rstrip()}\n\n{caption_block}"

    @staticmethod
    def _copy_chunk(chunk: Chunk, text: str, metadata: dict[str, Any]) -> Chunk:
        """复制 chunk 并替换正文/metadata。"""
        return Chunk(
            id=chunk.id,
            text=text,
            metadata=metadata,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            source_ref=chunk.source_ref,
        )

    @classmethod
    def _build_image_map(cls, images: Any) -> dict[str, dict[str, Any]]:
        """将 `metadata.images` 规范化为 `image_id -> image_info` 映射。"""
        if not isinstance(images, list):
            return {}

        image_map: dict[str, dict[str, Any]] = {}
        for image in images:
            if not isinstance(image, dict):
                continue
            image_id = image.get("id")
            if isinstance(image_id, str) and image_id.strip():
                image_map[image_id.strip()] = dict(image)
        return image_map

    @classmethod
    def _normalize_image_refs(cls, value: Any) -> list[str]:
        """将 `image_refs` 归一化为去重且保序的字符串列表。"""
        if isinstance(value, list):
            refs = [item for item in value if isinstance(item, str)]
        else:
            refs = []

        normalized: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            ref_text = ref.strip()
            if not ref_text or ref_text in seen:
                continue
            seen.add(ref_text)
            normalized.append(ref_text)
        return normalized

    @classmethod
    def _normalize_image_captions(cls, value: Any) -> dict[str, str]:
        """将 `image_captions` 归一化为 `dict[image_id, caption]`。"""
        if not isinstance(value, dict):
            return {}

        normalized: dict[str, str] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                continue
            key = raw_key.strip()
            caption = cls._normalize_caption(raw_value)
            if key and caption:
                normalized[key] = caption
        return normalized

    @staticmethod
    def _normalize_caption(value: Any, max_len: int = 320) -> str:
        """规整 caption 文本，避免影响 markdown 结构。"""
        if not isinstance(value, str):
            return ""
        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return ""
        text = text.replace("[", "（").replace("]", "）")
        if len(text) <= max_len:
            return text
        return f"{text[: max_len - 1].rstrip()}…"

    @staticmethod
    def _compact_whitespace(text: str) -> str:
        """压缩空白字符，便于构建短上下文窗口。"""
        return re.sub(r"\s+", " ", str(text)).strip()

    @staticmethod
    def _summarize_exception(exc: Exception, max_len: int = 80) -> str:
        """提取异常摘要，供 fallback reason 使用。"""
        text = str(exc).strip()
        if not text:
            return ""
        first_line = re.sub(r"\s+", " ", text.splitlines()[0]).strip()
        if len(first_line) <= max_len:
            return first_line
        return f"{first_line[: max_len - 1].rstrip()}…"
