"""EmbeddingFactory 单元测试。"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import (
    EmbeddingSettings,
    EvaluationSettings,
    LLMSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
)
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory


class _FakeEmbedding(BaseEmbedding):
    """用于验证工厂分流的测试桩。"""

    def __init__(self, model: str = "") -> None:
        self.model = model

    def embed(self, texts: list[str], trace: object | None = None) -> list[list[float]]:
        """返回稳定向量，便于断言测试。

        设计说明：
        - 使用文本哈希前缀 + 长度构造三维向量。
        - 相同输入必须得到相同输出，才能验证“稳定向量”验收点。
        """
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            head = int(digest[:8], 16)
            vectors.append(
                [
                    len(text) / 100.0,
                    (head % 1000) / 1000.0,
                    (head // 1000 % 1000) / 1000.0,
                ]
            )
        return vectors


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂全局注册表，避免测试互相污染。"""
    snapshot = dict(EmbeddingFactory._registry)
    built_snapshot = EmbeddingFactory._builtin_loaded
    EmbeddingFactory._registry.clear()
    EmbeddingFactory._builtin_loaded = False
    try:
        yield snapshot
    finally:
        EmbeddingFactory._registry.clear()
        EmbeddingFactory._registry.update(snapshot)
        EmbeddingFactory._builtin_loaded = built_snapshot


def _build_settings(provider: str, model: str = "") -> Settings:
    """构造最小可用 Settings，聚焦 embedding 配置字段。"""
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider=provider, model=model),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=5, sparse_top_k=10),
        rerank=RerankSettings(provider="none", enabled=False, top_m=10),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
    )


def test_factory_routes_to_registered_provider(isolated_registry: dict[str, object]) -> None:
    """验证工厂会按 provider 路由到正确实现，并透传 model 给实例。"""
    EmbeddingFactory.register("fake", lambda model="", **_: _FakeEmbedding(model=model))
    settings = _build_settings(provider="fake", model="emb-model")

    client = EmbeddingFactory.create(settings)

    assert isinstance(client, _FakeEmbedding)
    assert client.model == "emb-model"


def test_fake_embedding_vectors_are_stable(isolated_registry: dict[str, object]) -> None:
    """验证同一输入生成稳定向量，且输出 shape 为二维列表（N x D）。"""
    EmbeddingFactory.register("fake", lambda model="", **_: _FakeEmbedding(model=model))
    client = EmbeddingFactory.create(_build_settings(provider="fake"))

    texts = ["hello", "world"]
    v1 = client.embed(texts)
    v2 = client.embed(texts)

    assert v1 == v2
    assert len(v1) == 2
    assert all(len(vec) == 3 for vec in v1)


def test_factory_missing_provider_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证缺少 `embedding.provider` 时会抛出可读错误，避免无提示失败。"""
    with pytest.raises(ValueError, match="embedding.provider"):
        EmbeddingFactory.create({"embedding": {"model": "x"}})


def test_factory_unknown_provider_raises(isolated_registry: dict[str, object]) -> None:
    """验证未知 provider 会显式报错，防止路由到错误后端。"""
    settings = _build_settings(provider="unknown")

    with pytest.raises(ValueError, match="Unknown embedding provider: unknown"):
        EmbeddingFactory.create(settings)
