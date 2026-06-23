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
    load_settings,
)
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory
from libs.llm.openai_llm import OpenAILLM


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
    built_snapshot = LLMFactory._builtin_loaded
    LLMFactory._registry.clear()
    LLMFactory._builtin_loaded = False
    try:
        yield snapshot
    finally:
        LLMFactory._registry.clear()
        LLMFactory._registry.update(snapshot)
        LLMFactory._builtin_loaded = built_snapshot


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
    LLMFactory.register("fake", lambda model="", **_: _FakeLLM(model=model))
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


def test_factory_can_create_openai_llm_from_loaded_settings_object() -> None:
    """
    Given:
        通过 `load_settings(config/settings.yaml)` 得到的强类型 Settings 对象。

    When:
        调用 `LLMFactory.create(settings)`。

    Then:
        工厂能从 Settings.llm 读取 provider/model/base_url/api_key，
        并按当前配置创建对应的 OpenAI-compatible 客户端。
    """
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    client = LLMFactory.create(settings)

    assert isinstance(client, OpenAILLM)
    # 这里验证“工厂遵守配置文件”，而不是把 provider 写死成某个值。
    assert client.provider_name == settings.llm.provider
    assert client.model == settings.llm.model
    assert client.base_url == settings.llm.base_url
    assert client.api_key == settings.llm.api_key


def test_factory_passes_proxy_to_openai_compatible_llm(isolated_registry: dict[str, object]) -> None:
    """当 `llm.proxy` 存在时，工厂应把代理地址透传到客户端实例。"""
    settings = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "k",
            "proxy": "http://127.0.0.1:10809",
        }
    }

    client = LLMFactory.create(settings)

    assert isinstance(client, OpenAILLM)
    assert client.proxy == "http://127.0.0.1:10809"
