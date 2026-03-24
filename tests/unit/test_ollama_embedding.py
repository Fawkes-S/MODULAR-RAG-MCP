"""OllamaEmbedding 单元测试（mock HTTP）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.embedding.embedding_factory import EmbeddingFactory
from libs.embedding.ollama_embedding import OllamaEmbedding


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，保证测试互不污染。"""
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


def test_factory_can_create_ollama_provider(isolated_registry: dict[str, object]) -> None:
    """Given provider=ollama, When 工厂创建实例, Then 返回 OllamaEmbedding。"""
    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "model": "nomic-embed-text",
                "transport": lambda *_: {"embedding": [0.1, 0.2]},
            }
        }
    )

    assert isinstance(client, OllamaEmbedding)


def test_embed_batch_returns_vectors_with_model_defined_dimension(isolated_registry: dict[str, object]) -> None:
    """Given 批量文本输入, When 调用 embed, Then 返回 N 条向量且维度由模型响应决定。"""

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        # 用固定 4 维向量模拟模型输出维度
        return {"embedding": [1.0, 2.0, 3.0, 4.0]}

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "model": "nomic-embed-text",
                "transport": transport,
            }
        }
    )

    vectors = client.embed(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(v) == 4 for v in vectors)


def test_embed_empty_input_has_readable_error(isolated_registry: dict[str, object]) -> None:
    """Given 空输入, When 调用 embed, Then 抛出可读 ValidationError。"""
    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "transport": lambda *_: {"embedding": [0.1, 0.2]},
            }
        }
    )

    with pytest.raises(ValueError, match=r"\[ollama\].*texts must not be empty"):
        client.embed([])


def test_embed_too_long_input_can_raise_or_truncate(isolated_registry: dict[str, object]) -> None:
    """Given 超长输入策略配置, When embed, Then 未开启截断时报错，开启截断时可继续处理。"""
    error_client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "max_chars": 3,
                "truncate_long_text": False,
                "transport": lambda *_: {"embedding": [0.1]},
            }
        }
    )
    with pytest.raises(ValueError, match=r"max_chars=3"):
        error_client.embed(["abcd"])

    ok_client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "max_chars": 3,
                "truncate_long_text": True,
                "transport": lambda *_: {"embedding": [0.1]},
            }
        }
    )
    assert ok_client.embed(["abcd"]) == [[0.1]]


def test_connection_and_timeout_error_are_readable(isolated_registry: dict[str, object]) -> None:
    """Given 网络故障, When embed, Then 抛出包含 provider + 错误类型的 RequestError。"""

    def broken_transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        raise TimeoutError("connect timeout")

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "transport": broken_transport,
            }
        }
    )

    with pytest.raises(RuntimeError, match=r"\[ollama\].*RequestError.*TimeoutError"):
        client.embed(["hello"])


def test_response_shape_error_is_readable(isolated_registry: dict[str, object]) -> None:
    """Given 非法响应结构, When embed, Then 抛出 ResponseShapeError 并标注问题索引。"""
    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "ollama",
                "transport": lambda *_: {"not_embedding": []},
            }
        }
    )

    with pytest.raises(ValueError, match=r"\[ollama\].*ResponseShapeError.*texts\[0\]"):
        client.embed(["hello"])
