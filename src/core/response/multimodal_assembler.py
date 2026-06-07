"""多模态响应组装：把命中的图片转换为 MCP ImageContent。"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

from core.types import RetrievalResult
from ingestion.storage.image_storage import ImageStorage


class MultimodalAssembler:
    """把检索结果中的 `image_refs` 组装为 MCP 图片内容。

    做什么：
    - 扫描 `RetrievalResult.metadata.image_refs`；
    - 通过 `ImageStorage` 查询图片文件路径；
    - 读取图片并编码为 base64，产出 MCP `ImageContent`；
    - 同时返回轻量结构化图片信息，便于客户端继续渲染或调试。

    为什么：
    - E6 的目标不是改变检索逻辑，而是把“检索已命中的图片引用”真正带回 MCP 响应；
    - 将图片处理从 `ResponseBuilder` 拆到独立组件后，文本拼装和图片拼装职责更清晰，
      后续如果要增加图片数量限制、缩略图、去重策略，也只需要改这里。

    关键权衡：
    - 当前阶段优先保证“查询不断流”，因此图片读取失败采用静默降级：
      单张图失败不会中断整个文本响应；
    - 全局按命中顺序去重 `image_id`，避免同一图片被多个 chunk 命中时重复塞进 MCP content。

    失败路径：
    - `retrieval_results` shape 非法：抛 `ValueError`，阻止坏数据继续传播；
    - `ImageStorage` 中不存在对应 `image_id`、文件路径不存在、metadata 形态异常：
      该图片被跳过，调用方仍得到 text-only 响应；
    - 文件读失败或 base64 编码前异常：同样仅跳过该图片，不影响其他图片与正文。

    Args:
        image_storage: 可注入的图片索引/文件访问层，默认使用本地 `ImageStorage`。
    """

    def __init__(self, image_storage: ImageStorage | None = None) -> None:
        self.image_storage = image_storage or ImageStorage()

    def assemble(self, retrieval_results: list[RetrievalResult]) -> dict[str, Any]:
        """从检索结果中提取图片并构造 MCP 多模态输出。

        Returns:
            dict[str, Any]:
                - `content`: MCP `image` 内容列表
                - `images`: 结构化图片元信息列表
        """
        normalized_results = self._normalize_results(retrieval_results)
        content: list[dict[str, Any]] = []
        images: list[dict[str, Any]] = []
        seen_image_ids: set[str] = set()

        for result in normalized_results:
            refs = self._normalize_image_refs(result.metadata.get("image_refs"))
            fallback_images = self._normalize_images_metadata(result.metadata.get("images"))

            for image_id in refs:
                if image_id in seen_image_ids:
                    continue
                seen_image_ids.add(image_id)

                image_payload = self._build_image_payload(
                    image_id=image_id,
                    fallback_images=fallback_images,
                    chunk_id=result.chunk_id,
                )
                if image_payload is None:
                    # 单张图失败不应影响文本主链路；这里选择“跳过该图，保留正文结果”。
                    continue

                content.append(image_payload["content"])
                images.append(image_payload["image"])

        return {"content": content, "images": images}

    @staticmethod
    def _normalize_results(retrieval_results: list[RetrievalResult]) -> list[RetrievalResult]:
        """校验输入必须是稳定的 `RetrievalResult` 列表。"""
        if not isinstance(retrieval_results, list):
            raise ValueError("retrieval_results must be list[RetrievalResult]")

        normalized: list[RetrievalResult] = []
        for index, item in enumerate(retrieval_results):
            if not isinstance(item, RetrievalResult):
                raise ValueError(f"retrieval_results[{index}] must be RetrievalResult")
            normalized.append(item)
        return normalized

    @staticmethod
    def _normalize_image_refs(value: Any) -> list[str]:
        """兼容 list / JSON 字符串 / 逗号分隔字符串三种常见 `image_refs` 形态。"""
        if isinstance(value, list):
            candidates = value
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                candidates = []
            else:
                try:
                    decoded = json.loads(text)
                except Exception:
                    decoded = None

                if isinstance(decoded, list):
                    candidates = decoded
                else:
                    candidates = [part.strip() for part in text.split(",")]
        else:
            candidates = []

        refs: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            image_id = str(item).strip()
            if not image_id or image_id in seen:
                continue
            seen.add(image_id)
            refs.append(image_id)
        return refs

    @staticmethod
    def _normalize_images_metadata(value: Any) -> list[dict[str, Any]]:
        """把 metadata.images 归一化为字典列表，兼容 JSON 字符串形式。"""
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                items = []
            else:
                try:
                    decoded = json.loads(text)
                except Exception:
                    decoded = []
                items = decoded if isinstance(decoded, list) else []
        else:
            items = []

        normalized: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                normalized.append(dict(item))
        return normalized

    def _build_image_payload(
        self,
        *,
        image_id: str,
        fallback_images: list[dict[str, Any]],
        chunk_id: str,
    ) -> dict[str, Any] | None:
        """构造单张图片的 MCP payload；失败返回 `None`。

        这里先查 `ImageStorage`，因为它代表 ingestion 后的最终可查询路径。
        若索引里暂时没有，再回退到检索结果 metadata 中携带的 `images` 子集，兼容过渡态数据。
        """
        record = self.image_storage.get_record(image_id)
        file_path = self._resolve_file_path(image_id=image_id, record=record, fallback_images=fallback_images)
        if file_path is None:
            return None

        file_obj = Path(file_path)
        if not file_obj.exists() or not file_obj.is_file():
            return None

        image_bytes = file_obj.read_bytes()
        if not image_bytes:
            return None

        mime_type = self._detect_mime_type(file_obj)
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        return {
            "content": {
                "type": "image",
                "data": encoded,
                "mimeType": mime_type,
            },
            "image": {
                "image_id": image_id,
                "chunk_id": chunk_id,
                "mimeType": mime_type,
                "file_path": file_obj.as_posix(),
            },
        }

    @staticmethod
    def _resolve_file_path(
        *,
        image_id: str,
        record: dict[str, Any] | None,
        fallback_images: list[dict[str, Any]],
    ) -> str | None:
        """优先从索引解析路径，缺失时回退到 metadata.images。"""
        if isinstance(record, dict):
            file_path = record.get("file_path")
            if isinstance(file_path, str) and file_path.strip():
                return file_path.strip()

        for item in fallback_images:
            candidate_id = str(item.get("id", "")).strip()
            if candidate_id != image_id:
                continue
            candidate_path = item.get("path")
            if isinstance(candidate_path, str) and candidate_path.strip():
                return candidate_path.strip()
        return None

    @staticmethod
    def _detect_mime_type(file_path: Path) -> str:
        """根据文件后缀推断 MIME，失败时回退为 `application/octet-stream`。"""
        guessed, _ = mimetypes.guess_type(file_path.name)
        return guessed or "application/octet-stream"
