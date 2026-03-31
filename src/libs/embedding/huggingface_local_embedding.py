"""HuggingFace local embedding provider implementation.

该实现使用 `sentence-transformers` 在本地进行文本向量化：
- 首次运行会自动下载模型到本地缓存；
- 后续运行复用缓存，不需要 API Key / Base URL；
- 适合离线、低成本场景。
"""

from __future__ import annotations

from typing import Any

from libs.embedding.base_embedding import BaseEmbedding

try:  # pragma: no cover - 依赖是否安装受运行环境影响
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment]


class HuggingFaceLocalEmbedding(BaseEmbedding):
    """本地 HuggingFace 向量化客户端实现。"""

    provider_name = "huggingface_local"

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 32,
        normalize_embeddings: bool = False,
        max_chars: int = 0,
        truncate_long_text: bool = False,
        **_: Any,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("[huggingface_local] ValidationError: model must be non-empty string")
        if not isinstance(device, str) or not device.strip():
            raise ValueError("[huggingface_local] ValidationError: device must be non-empty string")
        if not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError("[huggingface_local] ValidationError: batch_size must be positive int")

        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers is required for huggingface_local embedding. "
                "Install with: pip install sentence-transformers"
            )

        self.model = model
        self.device = device
        self.batch_size = batch_size
        self.normalize_embeddings = bool(normalize_embeddings)
        self.max_chars = int(max_chars)
        self.truncate_long_text = bool(truncate_long_text)

        try:
            self._encoder = SentenceTransformer(model_name_or_path=self.model, device=self.device)
        except Exception as exc:  # pragma: no cover - 依赖库下载/初始化错误
            raise RuntimeError(
                f"[huggingface_local] InitError: failed to load model '{self.model}' on device '{self.device}': {exc}"
            ) from exc

    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        """批量向量化文本。"""
        normalized = self._normalize_texts(texts)

        try:
            vectors = self._encoder.encode(
                normalized,
                batch_size=self.batch_size,
                show_progress_bar=False,
                normalize_embeddings=self.normalize_embeddings,
                convert_to_numpy=True,
            )
        except Exception as exc:  # pragma: no cover - 依赖库推理异常
            raise RuntimeError(
                f"[huggingface_local] InferenceError: {type(exc).__name__}: {exc}"
            ) from exc

        if hasattr(vectors, "tolist"):
            rows = vectors.tolist()
        else:
            rows = list(vectors)

        result: list[list[float]] = []
        for idx, row in enumerate(rows):
            if not isinstance(row, (list, tuple)):
                raise ValueError(
                    f"[huggingface_local] ResponseShapeError: embedding[{idx}] must be list-like"
                )
            result.append([float(v) for v in row])

        return result

    def _normalize_texts(self, texts: list[str]) -> list[str]:
        """输入校验与超长文本策略处理。"""
        if not isinstance(texts, list):
            raise ValueError("[huggingface_local] ValidationError: texts must be list")
        if len(texts) == 0:
            raise ValueError("[huggingface_local] ValidationError: texts must not be empty")

        normalized: list[str] = []
        for idx, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"[huggingface_local] ValidationError: texts[{idx}] must be non-empty string"
                )

            value = text
            if self.max_chars > 0 and len(value) > self.max_chars:
                if self.truncate_long_text:
                    value = value[: self.max_chars]
                else:
                    raise ValueError(
                        f"[huggingface_local] ValidationError: texts[{idx}] exceeds max_chars={self.max_chars}"
                    )

            normalized.append(value)

        return normalized
