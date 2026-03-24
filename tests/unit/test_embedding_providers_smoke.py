"""OpenAI/Azure Embedding providers 冒烟测试（全 mock HTTP）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.embedding.azure_embedding import AzureEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory
from libs.embedding.openai_embedding import OpenAIEmbedding


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，保证测试可重复执行且不依赖外部状态。"""
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


def _ok_transport(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    # OpenAI embedding response: {"data": [{"embedding": [...]} ...]}
    inputs = payload.get("input") or []
    return {"data": [{"embedding": [float(i), 0.0, 1.0]} for i, _ in enumerate(inputs)]}


def test_factory_routes_openai_and_azure(isolated_registry: dict[str, object]) -> None:
    """验证工厂可按 provider 正确创建 OpenAIEmbedding/AzureEmbedding。"""
    openai_client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "k",
                "transport": _ok_transport,
            }
        }
    )
    azure_client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "azure",
                "model": "text-embedding-ada-002",
                "endpoint": "https://example.openai.azure.com",
                "deployment_name": "emb-1",
                "api_key": "k",
                "transport": _ok_transport,
            }
        }
    )

    assert isinstance(openai_client, OpenAIEmbedding)
    assert isinstance(azure_client, AzureEmbedding)


def test_openai_embedding_batch_shape(isolated_registry: dict[str, object]) -> None:
    """验证 OpenAIEmbedding 支持批量 embed(texts)，输出 shape 为 N x D。"""
    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "transport": _ok_transport,
            }
        }
    )

    vectors = client.embed(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(v) == 3 for v in vectors)


def test_azure_embedding_uses_deployment_url_and_api_key_header(isolated_registry: dict[str, object]) -> None:
    """验证 AzureEmbedding 的 URL/headers 处理符合 Azure 特有要求。"""
    captured: dict[str, Any] = {}

    def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["url"] = url
        captured["headers"] = headers
        return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "azure",
                "model": "text-embedding-ada-002",
                "endpoint": "https://example.openai.azure.com",
                "deployment_name": "emb-1",
                "api_key": "k",
                "api_version": "2024-02-01",
                "transport": transport,
            }
        }
    )

    vectors = client.embed(["hello"])

    assert vectors == [[0.1, 0.2, 0.3]]
    assert "/openai/deployments/emb-1/embeddings" in captured["url"]
    assert "api-version=2024-02-01" in captured["url"]
    assert captured["headers"]["api-key"] == "k"


def test_embedding_empty_input_has_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证空输入会显式报错，避免向后端发出无意义请求。"""
    client = EmbeddingFactory.create(
        {"embedding": {"provider": "openai", "transport": _ok_transport}}
    )

    with pytest.raises(ValueError, match=r"\[openai\].*texts must not be empty"):
        client.embed([])


def test_embedding_too_long_input_can_raise(isolated_registry: dict[str, object]) -> None:
    """验证超长输入在未开启截断时会报错（行为由配置控制）。"""
    client = EmbeddingFactory.create(
        {
            "embedding": {
                "provider": "openai",
                "transport": _ok_transport,
                "max_chars": 3,
                "truncate_long_text": False,
            }
        }
    )

    with pytest.raises(ValueError, match=r"max_chars=3"):
        client.embed(["abcd"])
