"""HuggingFaceLocalEmbedding 单元测试（不触发真实模型下载）。"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
LOCAL_EMBEDDING_MODEL_DIR = PROJECT_ROOT / "data" / "models" / "all-MiniLM-L6-v2"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.embedding.embedding_factory import EmbeddingFactory
from libs.embedding.huggingface_local_embedding import HuggingFaceLocalEmbedding
import libs.embedding.huggingface_local_embedding as hf_module


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，避免测试互相污染。"""
    snapshot = dict(EmbeddingFactory._registry)
    snapshot_builtin = EmbeddingFactory._builtin_loaded
    EmbeddingFactory._registry.clear()
    EmbeddingFactory._builtin_loaded = False
    try:
        yield snapshot
    finally:
        EmbeddingFactory._registry.clear()
        EmbeddingFactory._registry.update(snapshot)
        EmbeddingFactory._builtin_loaded = snapshot_builtin


class _FakeSentenceTransformer:
    """最小可用 fake encoder，用于拦截 encode 参数并返回稳定向量。"""

    def __init__(self, model_name_or_path: str, device: str = "cpu") -> None:
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.last_encode: dict[str, Any] = {}

    def encode(
        self,
        texts: list[str],
        batch_size: int,
        show_progress_bar: bool,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> list[list[float]]:
        self.last_encode = {
            "texts": list(texts),
            "batch_size": batch_size,
            "show_progress_bar": show_progress_bar,
            "normalize_embeddings": normalize_embeddings,
            "convert_to_numpy": convert_to_numpy,
        }
        return [[float(i), 0.5, 1.0] for i, _ in enumerate(texts)]


def test_factory_can_create_huggingface_local_provider(
    isolated_registry: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        将 `SentenceTransformer` 替换为 fake encoder，避免真实下载模型。

    When:
        通过 `EmbeddingFactory.create` 创建 `provider=huggingface_local`。

    Then:
        返回 `HuggingFaceLocalEmbedding`，并透传 model/device 配置。
    """
    monkeypatch.setattr(hf_module, "SentenceTransformer", _FakeSentenceTransformer)

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "huggingface_local",
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "device": "cpu",
                "batch_size": 16,
            }
        }
    )

    assert isinstance(client, HuggingFaceLocalEmbedding)
    assert client.model == "sentence-transformers/all-MiniLM-L6-v2"
    assert client.device == "cpu"
    assert client.batch_size == 16


def test_embed_batch_returns_vectors_and_passes_encode_kwargs(
    isolated_registry: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        fake encoder 会记录 encode 调用参数并返回稳定向量。

    When:
        调用 `embed(["a", "b"])`。

    Then:
        - 返回二维浮点向量列表；
        - encode 参数（batch_size/normalize_embeddings）与配置一致。
    """
    monkeypatch.setattr(hf_module, "SentenceTransformer", _FakeSentenceTransformer)

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "huggingface_local",
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "device": "cpu",
                "batch_size": 8,
                "normalize_embeddings": True,
            }
        }
    )

    vectors = client.embed(["hello", "world"])

    assert len(vectors) == 2
    assert all(len(vec) == 3 for vec in vectors)
    assert vectors[0][0] == 0.0
    assert vectors[1][0] == 1.0

    fake_encoder = client._encoder
    assert fake_encoder.last_encode["batch_size"] == 8
    assert fake_encoder.last_encode["normalize_embeddings"] is True
    assert fake_encoder.last_encode["convert_to_numpy"] is True


def test_missing_dependency_raises_import_error(
    isolated_registry: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        运行环境缺少 `sentence-transformers`。

    When:
        创建 `huggingface_local` provider。

    Then:
        抛出可读 ImportError，明确提示安装依赖。
    """
    monkeypatch.setattr(hf_module, "SentenceTransformer", None)

    with pytest.raises(ImportError, match="sentence-transformers"):
        EmbeddingFactory.create(
            {
                "embedding": {
                    "provider": "huggingface_local",
                    "model": "sentence-transformers/all-MiniLM-L6-v2",
                }
            }
        )


def test_validation_error_for_empty_texts(
    isolated_registry: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        已创建好的 huggingface_local 客户端。

    When:
        调用 `embed([])`。

    Then:
        抛出 ValidationError，避免把空批次送入模型推理流程。
    """
    monkeypatch.setattr(hf_module, "SentenceTransformer", _FakeSentenceTransformer)

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "huggingface_local",
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            }
        }
    )

    with pytest.raises(ValueError, match=r"\[huggingface_local\].*texts must not be empty"):
        client.embed([])


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """计算两个向量的余弦相似度。"""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        raise ValueError("vector norm must be > 0 for cosine similarity")
    return dot / (norm_a * norm_b)


@pytest.mark.integration
@pytest.mark.slow
def test_real_local_model_semantic_similarity_smoke(
    isolated_registry: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        - 本地模型目录 `data/models/all-MiniLM-L6-v2` 已就绪；
        - 通过离线环境变量强制仅使用本地权重，不访问外网。

    When:
        对三条语义不同的英文句子执行真实 embedding：
        - text_a 与 text_b 语义相近（都在描述在家烤面包）；
        - text_c 与前两者语义无关（汽车机油更换）。

    Then:
        - 返回 3 条、且维度一致的向量；
        - `sim(text_a, text_b)` 明显高于 `sim(text_a, text_c)`，
          作为本地模型“语义区分能力”的基础冒烟验证。
    """
    if not LOCAL_EMBEDDING_MODEL_DIR.exists():
        pytest.skip(f"local embedding model directory not found: {LOCAL_EMBEDDING_MODEL_DIR}")

    # 强制离线模式（HF_HUB_OFFLINE=1 + TRANSFORMERS_OFFLINE=1）
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "huggingface_local",
                "model": str(LOCAL_EMBEDDING_MODEL_DIR),
                "device": "cpu",
                "batch_size": 4,
                "normalize_embeddings": True,
            }
        }
    )

    text_a = "How can I bake bread at home?"
    text_b = "What are the steps for homemade bread baking?"
    text_c = "How do I change car engine oil?"
    vectors = client.embed([text_a, text_b, text_c])

    assert len(vectors) == 3
    assert len(vectors[0]) > 100
    assert len(vectors[0]) == len(vectors[1]) == len(vectors[2])

    sim_related = _cosine_similarity(vectors[0], vectors[1])
    sim_unrelated = _cosine_similarity(vectors[0], vectors[2])
    assert sim_related > sim_unrelated + 0.08
