"""LLMFactory 单元测试。"""

from __future__ import annotations

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
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory


class _FakeLLM(BaseLLM):
    """用于验证工厂分流行为的测试桩。"""

    def __init__(self, model: str = "") -> None:
        self.model = model

    def chat(self, messages: list[dict[str, object]]) -> str:
        return f"fake:{self.model}:{len(messages)}"


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离全局注册表，避免测试用例互相污染状态。"""
    snapshot = dict(LLMFactory._registry)
    LLMFactory._registry.clear()
    try:
        yield snapshot
    finally:
        LLMFactory._registry.clear()
        LLMFactory._registry.update(snapshot)


def _build_settings(provider: str, model: str = "") -> Settings:
    """构造最小可用 Settings，聚焦 llm provider/model 字段。"""
    return Settings(
        llm=LLMSettings(provider=provider, model=model),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=5, sparse_top_k=10),
        rerank=RerankSettings(provider="none", enabled=False, top_m=10),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
    )


def test_factory_routes_to_registered_provider(isolated_registry: dict[str, object]) -> None:
    """验证工厂会按 provider 路由到已注册实现，并正确透传 model 参数。"""
    LLMFactory.register("fake", lambda model="": _FakeLLM(model=model))
    settings = _build_settings(provider="fake", model="demo-model")

    client = LLMFactory.create(settings)

    assert isinstance(client, _FakeLLM)
    assert client.model == "demo-model"
    assert client.chat([{"role": "user", "content": "hello"}]) == "fake:demo-model:1"


def test_factory_missing_provider_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证缺少 `llm.provider` 时，错误信息包含明确字段路径便于定位配置问题。"""
    with pytest.raises(ValueError, match="llm.provider"):
        LLMFactory.create({"llm": {"model": "x"}})


def test_factory_unknown_provider_raises(isolated_registry: dict[str, object]) -> None:
    """验证未注册 provider 会被拒绝，防止系统静默降级到错误实现。"""
    settings = _build_settings(provider="unknown")

    with pytest.raises(ValueError, match="Unknown llm provider: unknown"):
        LLMFactory.create(settings)
