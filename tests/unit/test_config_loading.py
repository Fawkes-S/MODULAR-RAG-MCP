"""Tests for settings loading and validation."""

from __future__ import annotations

from dataclasses import fields
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import (
    ChunkRefinerSettings,
    DashboardSettings,
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    MetadataEnricherSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
    VisionLLMSettings,
    load_settings,
)


def _write_minimal_settings(path: Path, *, llm_api_key: str, llm_base_url: str) -> None:
    """写入最小可加载配置，便于测试环境变量占位符解析。"""
    path.write_text(
        f"""
llm:
  provider: openai
  model: qwen3.5-plus
  api_key: {llm_api_key}
  base_url: {llm_base_url}
embedding:
  provider: openai
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: false
""".strip(),
        encoding="utf-8",
    )


def _assert_yaml_keys_are_covered(
    section_path: str,
    section: dict[str, object],
    dataclass_type: type,
) -> None:
    """断言 YAML section 的键都能在对应 dataclass 中找到。"""
    field_names = {item.name for item in fields(dataclass_type)}
    missing = set(section.keys()) - field_names
    assert not missing, f"{section_path} has unmapped keys in Settings dataclass: {sorted(missing)}"


def test_load_settings_success() -> None:
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    assert isinstance(settings, Settings)
    assert settings.embedding.provider == "huggingface_local"
    assert Path(settings.embedding.model).resolve() == (PROJECT_ROOT / "data" / "models" / "all-MiniLM-L6-v2").resolve()
    assert settings.retrieval.top_k > 0

    # 确保 llm 扩展字段可读取。
    assert settings.llm.profile == "minimax"
    assert settings.llm.provider == "openai"
    assert settings.llm.model
    assert settings.llm.base_url.startswith("https://")
    assert settings.llm.max_retries >= 0
    assert settings.llm.retry_backoff_seconds >= 0
    assert settings.llm.retry_backoff_multiplier >= 1.0
    assert settings.llm.retry_max_backoff_seconds >= 0

    # 确保 vision_llm 扩展字段可读取。
    assert settings.vision_llm.profile
    assert settings.vision_llm.provider in {"dashscope", "openai", "azure"}
    assert settings.vision_llm.model
    assert settings.vision_llm.base_url.startswith("https://")
    assert settings.vision_llm.max_retries >= 0
    assert settings.vision_llm.retry_backoff_seconds >= 0
    assert settings.vision_llm.retry_backoff_multiplier >= 1.0
    assert settings.vision_llm.retry_max_backoff_seconds >= 0

    # dashboard 段应被读取为强类型配置，供 G1 启动脚本与页面使用。
    assert settings.dashboard.enabled is True
    assert settings.dashboard.port == 8501
    assert settings.dashboard.traces_dir == "logs"
    assert settings.dashboard.auto_refresh is True
    assert settings.dashboard.refresh_interval == 5

    # ingestion 段也应进入强类型 Settings。
    assert settings.ingestion.splitter
    assert settings.ingestion.chunk_size > 0
    assert settings.ingestion.chunk_refiner.use_llm is True
    assert settings.ingestion.metadata_enricher.use_llm is True


def test_settings_yaml_keys_are_mapped_by_settings_dataclasses() -> None:
    """
    Given:
        当前项目的 `config/settings.yaml`。

    When:
        读取 YAML 并按 section 对照 `core.settings` 中对应 dataclass 字段。

    Then:
        YAML 中出现的键都必须能在 dataclass 中找到，
        防止“配置新增了但 Settings 未更新”导致运行时静默失效。
    """
    raw = yaml.safe_load((PROJECT_ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("config/settings.yaml root must be mapping")

    sections: list[tuple[str, type]] = [
        ("llm", LLMSettings),
        ("embedding", EmbeddingSettings),
        ("vector_store", VectorStoreSettings),
        ("retrieval", RetrievalSettings),
        ("rerank", RerankSettings),
        ("vision_llm", VisionLLMSettings),
        ("evaluation", EvaluationSettings),
        ("observability", ObservabilitySettings),
        ("dashboard", DashboardSettings),
        ("ingestion", IngestionSettings),
    ]

    for section_name, dataclass_type in sections:
        section = raw.get(section_name)
        assert isinstance(section, dict), f"settings.yaml missing mapping section: {section_name}"
        _assert_yaml_keys_are_covered(section_name, section, dataclass_type)

    ingestion = raw.get("ingestion")
    assert isinstance(ingestion, dict)

    chunk_refiner = ingestion.get("chunk_refiner")
    if isinstance(chunk_refiner, dict):
        _assert_yaml_keys_are_covered("ingestion.chunk_refiner", chunk_refiner, ChunkRefinerSettings)

    metadata_enricher = ingestion.get("metadata_enricher")
    if isinstance(metadata_enricher, dict):
        _assert_yaml_keys_are_covered(
            "ingestion.metadata_enricher",
            metadata_enricher,
            MetadataEnricherSettings,
        )


def test_load_settings_resolves_env_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    """`${VAR}` 应从环境变量读取并替换。"""
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_dir / "settings_env_placeholder.yaml"

    _write_minimal_settings(
        settings_path,
        llm_api_key="${TEST_LLM_API_KEY}",
        llm_base_url="${TEST_LLM_BASE_URL}",
    )

    monkeypatch.setenv("TEST_LLM_API_KEY", "key-123")
    monkeypatch.setenv("TEST_LLM_BASE_URL", "https://example.openai-compatible/v1")

    settings = load_settings(str(settings_path))

    assert settings.llm.api_key == "key-123"
    assert settings.llm.base_url == "https://example.openai-compatible/v1"


def test_load_settings_supports_env_default_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """`${VAR:-default}` 在变量缺失时应回退到 default。"""
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_dir / "settings_env_default.yaml"

    _write_minimal_settings(
        settings_path,
        llm_api_key="${MISSING_KEY:-fallback-key}",
        llm_base_url="${MISSING_URL:-https://fallback.example/v1}",
    )

    monkeypatch.delenv("MISSING_KEY", raising=False)
    monkeypatch.delenv("MISSING_URL", raising=False)

    settings = load_settings(str(settings_path))

    assert settings.llm.api_key == "fallback-key"
    assert settings.llm.base_url == "https://fallback.example/v1"


def test_load_settings_raises_when_env_missing_without_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """`${VAR}` 且环境变量缺失时应 fail-fast，避免静默空值。"""
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_dir / "settings_env_missing.yaml"

    _write_minimal_settings(
        settings_path,
        llm_api_key="${MISSING_MUST_SET_KEY}",
        llm_base_url="https://example/v1",
    )

    monkeypatch.delenv("MISSING_MUST_SET_KEY", raising=False)

    with pytest.raises(ValueError, match="MISSING_MUST_SET_KEY"):
        load_settings(str(settings_path))


def test_load_settings_reads_nearest_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """当环境变量未显式设置时，应能从 settings 上层目录的 `.env` 自动读取。"""
    tmp_root = PROJECT_ROOT / "tests" / ".tmp" / "dotenv_case"
    cfg_dir = tmp_root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    dotenv_path = tmp_root / ".env"
    dotenv_path.write_text(
        """
DOTENV_LLM_API_KEY=dotenv-key
DOTENV_LLM_BASE_URL=https://dotenv.example/v1
""".strip(),
        encoding="utf-8",
    )

    settings_path = cfg_dir / "settings.yaml"
    _write_minimal_settings(
        settings_path,
        llm_api_key="${DOTENV_LLM_API_KEY}",
        llm_base_url="${DOTENV_LLM_BASE_URL}",
    )

    monkeypatch.delenv("DOTENV_LLM_API_KEY", raising=False)
    monkeypatch.delenv("DOTENV_LLM_BASE_URL", raising=False)

    settings = load_settings(str(settings_path))

    assert settings.llm.api_key == "dotenv-key"
    assert settings.llm.base_url == "https://dotenv.example/v1"


def test_load_settings_merges_llm_and_vision_profiles() -> None:
    """
    Given:
        `llm.profile` / `vision_llm.profile` 都指向 `profiles` 中的具名配置，
        顶层 section 放公共 timeout/max_retries 字段。

    When:
        调用 `load_settings()`。

    Then:
        - provider/model/base_url/api_key 应取自所选 profile；
        - timeout/max_retries 等公共字段应继续从顶层 section 继承。
    """
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_dir / "settings_profiles.yaml"
    settings_path.write_text(
        """
llm:
  profile: qwen
  timeout: 41
  max_retries: 3
  profiles:
    minimax:
      provider: openai
      model: MiniMax-M2.7
      base_url: https://api.minimax.chat/v1
      api_key: mini-key
    qwen:
      provider: openai
      model: qwen3.5-plus
      base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
      api_key: qwen-key
embedding:
  provider: openai
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: true
  profile: gemini_flash
  max_image_size: 1536
  profiles:
    qwen:
      provider: dashscope
      model: qwen3.5-plus
      base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
      api_key: vision-qwen-key
    gemini_flash:
      provider: openai
      model: gemini-2.5-flash
      base_url: https://generativelanguage.googleapis.com/v1beta/openai
      api_key: gemini-key
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(str(settings_path))

    assert settings.llm.profile == "qwen"
    assert settings.llm.provider == "openai"
    assert settings.llm.model == "qwen3.5-plus"
    assert settings.llm.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings.llm.api_key == "qwen-key"
    assert settings.llm.proxy == ""
    assert settings.llm.timeout == 41.0
    assert settings.llm.max_retries == 3

    assert settings.vision_llm.profile == "gemini_flash"
    assert settings.vision_llm.provider == "openai"
    assert settings.vision_llm.model == "gemini-2.5-flash"
    assert settings.vision_llm.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert settings.vision_llm.api_key == "gemini-key"
    assert settings.vision_llm.proxy == ""
    assert settings.vision_llm.max_image_size == 1536


def test_load_settings_profile_can_override_proxy() -> None:
    """当选中的 profile 指定 proxy 时，应把代理配置并入最终 Settings。"""
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_dir / "settings_profile_proxy.yaml"
    settings_path.write_text(
        """
llm:
  profile: deepseek
  profiles:
    deepseek:
      provider: deepseek
      model: deepseek-chat
      base_url: https://api.deepseek.com/v1
      api_key: deepseek-key
      proxy: http://127.0.0.1:10809
embedding:
  provider: openai
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: true
  profile: gemini_flash
  profiles:
    gemini_flash:
      provider: openai
      model: gemini-2.5-flash
      base_url: https://generativelanguage.googleapis.com/v1beta/openai
      api_key: gemini-key
      proxy: http://127.0.0.1:10809
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(str(settings_path))

    assert settings.llm.proxy == "http://127.0.0.1:10809"
    assert settings.vision_llm.proxy == "http://127.0.0.1:10809"


def test_load_settings_unknown_profile_raises_readable_error() -> None:
    """当 profile 名称不存在于 profiles 中时，应给出可读错误。"""
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_dir / "settings_unknown_profile.yaml"
    settings_path.write_text(
        """
llm:
  profile: unknown
  profiles:
    qwen:
      provider: openai
      model: qwen3.5-plus
embedding:
  provider: openai
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown llm.profile='unknown'"):
        load_settings(str(settings_path))


def test_load_settings_missing_required_field_reports_path() -> None:
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    bad_settings = tmp_dir / "settings_missing_embedding_provider.yaml"
    bad_settings.write_text(
        """
llm:
  provider: openai
embedding:
  model: text-embedding-3-small
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="embedding.provider"):
        load_settings(str(bad_settings))


def test_load_settings_vision_enabled_requires_provider() -> None:
    """当 vision_llm.enabled=true 且 provider 缺失时，应给出可读错误。"""
    tmp_dir = PROJECT_ROOT / "tests" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    bad_settings = tmp_dir / "settings_vision_missing_provider.yaml"
    bad_settings.write_text(
        """
llm:
  provider: openai
embedding:
  provider: openai
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="vision_llm.provider"):
        load_settings(str(bad_settings))


def test_main_startup_loads_settings() -> None:
    proc = subprocess.run(
        [sys.executable, "main.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Modular RAG MCP project skeleton is ready." in proc.stdout



def test_load_settings_resolves_huggingface_local_model_path_against_project_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        一份 `embedding.provider=huggingface_local` 的配置，模型路径写成相对路径
        `data/models/all-MiniLM-L6-v2`，且当前工作目录切到其他子目录。

    When:
        调用 `load_settings(path)` 读取该配置。

    Then:
        `settings.embedding.model` 应被解析为可用绝对路径，
        指向该配置所属项目根目录下的模型目录，而不是当前 cwd 下的同名相对路径。
    """
    tmp_root = PROJECT_ROOT / "tests" / ".tmp" / "hf_model_path_resolution"
    model_dir = tmp_root / "data" / "models" / "all-MiniLM-L6-v2"
    model_dir.mkdir(parents=True, exist_ok=True)

    settings_path = tmp_root / "config" / "settings.yaml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        """
llm:
  provider: openai
embedding:
  provider: huggingface_local
  model: data/models/all-MiniLM-L6-v2
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: false
""".strip(),
        encoding="utf-8",
    )

    other_cwd = tmp_root / "tests" / "integration"
    other_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(other_cwd)

    settings = load_settings(str(settings_path))

    assert Path(settings.embedding.model).is_absolute()
    assert Path(settings.embedding.model).resolve() == model_dir.resolve()


def test_load_settings_keeps_remote_embedding_model_name_unchanged() -> None:
    """
    Given:
        `huggingface_local` 的模型名是远程仓库标识
        `sentence-transformers/all-MiniLM-L6-v2`（非本地目录）。

    When:
        调用 `load_settings(path)`。

    Then:
        配置值应保持原样，不应被误改为本地绝对路径。
    """
    tmp_root = PROJECT_ROOT / "tests" / ".tmp" / "hf_remote_model_name"
    tmp_root.mkdir(parents=True, exist_ok=True)
    settings_path = tmp_root / "config" / "settings.yaml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    remote_model_name = "sentence-transformers/all-MiniLM-L6-v2"
    settings_path.write_text(
        f"""
llm:
  provider: openai
embedding:
  provider: huggingface_local
  model: {remote_model_name}
vector_store:
  provider: chroma
retrieval:
  top_k: 8
rerank:
  provider: none
evaluation:
  provider: ragas
observability:
  log_level: INFO
vision_llm:
  enabled: false
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(str(settings_path))
    assert settings.embedding.model == remote_model_name

