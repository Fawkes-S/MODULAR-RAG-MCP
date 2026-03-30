"""Settings loading and validation.

该模块负责将 `config/settings.yaml` 解析为强类型配置对象，并做基础校验。
设计目标：
- 对关键字段 fail-fast（provider/top_k 等）；
- 保留 provider 扩展字段（api_key/base_url/timeout 等），让工厂可直接读取；
- 支持环境变量占位符 `${VAR}` / `${VAR:-default}`，避免把密钥硬编码进仓库。
- 强制把 `settings.yaml` 的结构映射到 `Settings` dataclass，避免“配置有了但代码读不到”。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str = ""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    endpoint: str = ""
    deployment_name: str = ""
    api_version: str = ""
    timeout: float = 30.0


@dataclass(frozen=True)
class VisionLLMSettings:
    enabled: bool = False
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    endpoint: str = ""
    azure_endpoint: str = ""
    deployment_name: str = ""
    api_version: str = ""
    timeout: float = 30.0
    max_image_size: int = 2048


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    model: str = ""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    endpoint: str = ""
    deployment_name: str = ""
    api_version: str = ""
    timeout: float = 30.0


@dataclass(frozen=True)
class VectorStoreSettings:
    provider: str
    persist_dir: str = "data/db/chroma"


@dataclass(frozen=True)
class RetrievalSettings:
    top_k: int
    sparse_top_k: int = 20


@dataclass(frozen=True)
class RerankSettings:
    provider: str
    enabled: bool = False
    top_m: int = 30
    backend: str = ""
    prompt_path: str = "config/prompts/rerank.txt"
    timeout: float = 10.0


@dataclass(frozen=True)
class EvaluationSettings:
    provider: str
    enabled: bool = False


@dataclass(frozen=True)
class ObservabilitySettings:
    log_level: str
    trace_file: str = "logs/traces.jsonl"


@dataclass(frozen=True)
class ChunkRefinerSettings:
    use_llm: bool = False
    prompt_path: str = "config/prompts/chunk_refinement.txt"


@dataclass(frozen=True)
class MetadataEnricherSettings:
    use_llm: bool = False


@dataclass(frozen=True)
class IngestionSettings:
    splitter: str = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: list[str] = field(default_factory=list)
    splitter_kwargs: dict[str, Any] = field(default_factory=dict)
    batch_size: int = 100
    chunk_refiner: ChunkRefinerSettings = field(default_factory=ChunkRefinerSettings)
    metadata_enricher: MetadataEnricherSettings = field(default_factory=MetadataEnricherSettings)


@dataclass(frozen=True)
class Settings:
    llm: LLMSettings
    embedding: EmbeddingSettings
    vector_store: VectorStoreSettings
    retrieval: RetrievalSettings
    rerank: RerankSettings
    evaluation: EvaluationSettings
    observability: ObservabilitySettings
    # 为保持向后兼容放在最后，并给默认值：旧测试不传 vision_llm/ingestion 也能构造 Settings。
    vision_llm: VisionLLMSettings = field(default_factory=VisionLLMSettings)
    ingestion: IngestionSettings = field(default_factory=IngestionSettings)


def _read_nested(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"Missing required setting: {path}")
        current = current[key]
    return current


def _as_dict(raw: Any) -> dict[str, Any]:
    """把 section 标准化成 dict；缺失/非法时返回空 dict。"""
    return dict(raw) if isinstance(raw, dict) else {}


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _parse_dotenv_file(dotenv_path: Path) -> dict[str, str]:
    """解析 .env 文件（最小实现），忽略空行与注释。"""
    values: dict[str, str] = {}
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return values

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        values[key] = value

    return values


def _load_nearest_dotenv(settings_path: Path) -> None:
    """从 settings 文件向上查找最近的 `.env`，并注入到环境变量（不覆盖已有值）。"""
    for parent in [settings_path.parent, *settings_path.parents]:
        dotenv_path = parent / ".env"
        if not dotenv_path.exists():
            continue

        for key, value in _parse_dotenv_file(dotenv_path).items():
            os.environ.setdefault(key, value)
        return


def _resolve_env_in_string(text: str) -> str:
    """解析 `${VAR}` 与 `${VAR:-default}` 占位符。"""

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(3)

        if var_name in os.environ:
            return os.environ[var_name]
        if default is not None:
            return default
        raise ValueError(f"Missing required environment variable: {var_name}")

    return _ENV_PATTERN.sub(_replace, text)


def _resolve_env_placeholders(data: Any) -> Any:
    """递归解析配置中的环境变量占位符。"""
    if isinstance(data, dict):
        return {key: _resolve_env_placeholders(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_resolve_env_placeholders(item) for item in data]
    if isinstance(data, str):
        return _resolve_env_in_string(data)
    return data


def validate_settings(settings: Settings) -> None:
    """Validate required settings fields."""
    if not settings.llm.provider:
        raise ValueError("Missing required setting: llm.provider")
    if not settings.embedding.provider:
        raise ValueError("Missing required setting: embedding.provider")
    if not settings.vector_store.provider:
        raise ValueError("Missing required setting: vector_store.provider")
    if settings.retrieval.top_k <= 0:
        raise ValueError("Invalid setting: retrieval.top_k must be > 0")
    if not settings.rerank.provider:
        raise ValueError("Missing required setting: rerank.provider")
    if not settings.evaluation.provider:
        raise ValueError("Missing required setting: evaluation.provider")
    if not settings.observability.log_level:
        raise ValueError("Missing required setting: observability.log_level")

    # Vision 配置是可选的，但启用时必须有 provider。
    if settings.vision_llm.enabled and not settings.vision_llm.provider:
        raise ValueError("Missing required setting: vision_llm.provider (when vision_llm.enabled=true)")

    if not settings.ingestion.splitter.strip():
        raise ValueError("Missing required setting: ingestion.splitter")
    if settings.ingestion.chunk_size <= 0:
        raise ValueError("Invalid setting: ingestion.chunk_size must be > 0")
    if settings.ingestion.chunk_overlap < 0 or settings.ingestion.chunk_overlap >= settings.ingestion.chunk_size:
        raise ValueError("Invalid setting: ingestion.chunk_overlap must satisfy 0 <= chunk_overlap < chunk_size")
    if settings.ingestion.batch_size <= 0:
        raise ValueError("Invalid setting: ingestion.batch_size must be > 0")


def load_settings(path: str) -> Settings:
    """Load YAML settings and validate required fields."""
    settings_path = Path(path)
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")

    _load_nearest_dotenv(settings_path)

    raw = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid settings format: root must be a mapping")

    raw = _resolve_env_placeholders(raw)

    llm_cfg = _as_dict(raw.get("llm"))
    embedding_cfg = _as_dict(raw.get("embedding"))
    vector_cfg = _as_dict(raw.get("vector_store"))
    retrieval_cfg = _as_dict(raw.get("retrieval"))
    rerank_cfg = _as_dict(raw.get("rerank"))
    evaluation_cfg = _as_dict(raw.get("evaluation"))
    observability_cfg = _as_dict(raw.get("observability"))
    vision_cfg = _as_dict(raw.get("vision_llm"))
    ingestion_cfg = _as_dict(raw.get("ingestion"))
    chunk_refiner_cfg = _as_dict(ingestion_cfg.get("chunk_refiner"))
    metadata_enricher_cfg = _as_dict(ingestion_cfg.get("metadata_enricher"))

    separators_raw = ingestion_cfg.get("separators", [])
    separators = (
        [str(item) for item in separators_raw if isinstance(item, str)]
        if isinstance(separators_raw, list)
        else []
    )

    splitter_kwargs_raw = ingestion_cfg.get("splitter_kwargs", {})
    splitter_kwargs = dict(splitter_kwargs_raw) if isinstance(splitter_kwargs_raw, dict) else {}

    settings = Settings(
        llm=LLMSettings(
            provider=str(_read_nested(raw, "llm.provider")),
            model=str(llm_cfg.get("model", "")),
            api_key=str(llm_cfg.get("api_key", "")),
            base_url=str(llm_cfg.get("base_url", "https://api.openai.com/v1")),
            endpoint=str(llm_cfg.get("endpoint", "")),
            deployment_name=str(llm_cfg.get("deployment_name", "")),
            api_version=str(llm_cfg.get("api_version", "")),
            timeout=_to_float(llm_cfg.get("timeout", 30.0), 30.0),
        ),
        embedding=EmbeddingSettings(
            provider=str(_read_nested(raw, "embedding.provider")),
            model=str(embedding_cfg.get("model", "")),
            api_key=str(embedding_cfg.get("api_key", "")),
            base_url=str(embedding_cfg.get("base_url", "https://api.openai.com/v1")),
            endpoint=str(embedding_cfg.get("endpoint", "")),
            deployment_name=str(embedding_cfg.get("deployment_name", "")),
            api_version=str(embedding_cfg.get("api_version", "")),
            timeout=_to_float(embedding_cfg.get("timeout", 30.0), 30.0),
        ),
        vector_store=VectorStoreSettings(
            provider=str(_read_nested(raw, "vector_store.provider")),
            persist_dir=str(vector_cfg.get("persist_dir", "data/db/chroma")),
        ),
        retrieval=RetrievalSettings(
            top_k=int(_read_nested(raw, "retrieval.top_k")),
            sparse_top_k=int(retrieval_cfg.get("sparse_top_k", 20)),
        ),
        rerank=RerankSettings(
            provider=str(_read_nested(raw, "rerank.provider")),
            enabled=bool(rerank_cfg.get("enabled", False)),
            top_m=int(rerank_cfg.get("top_m", 30)),
            backend=str(rerank_cfg.get("backend", "")),
            prompt_path=str(rerank_cfg.get("prompt_path", "config/prompts/rerank.txt")),
            timeout=_to_float(rerank_cfg.get("timeout", 10.0), 10.0),
        ),
        evaluation=EvaluationSettings(
            provider=str(_read_nested(raw, "evaluation.provider")),
            enabled=bool(evaluation_cfg.get("enabled", False)),
        ),
        observability=ObservabilitySettings(
            log_level=str(_read_nested(raw, "observability.log_level")),
            trace_file=str(observability_cfg.get("trace_file", "logs/traces.jsonl")),
        ),
        vision_llm=VisionLLMSettings(
            enabled=bool(vision_cfg.get("enabled", False)),
            provider=str(vision_cfg.get("provider", "")),
            model=str(vision_cfg.get("model", "")),
            api_key=str(vision_cfg.get("api_key", "")),
            base_url=str(vision_cfg.get("base_url", "")),
            endpoint=str(vision_cfg.get("endpoint", "")),
            azure_endpoint=str(vision_cfg.get("azure_endpoint", "")),
            deployment_name=str(vision_cfg.get("deployment_name", "")),
            api_version=str(vision_cfg.get("api_version", "")),
            timeout=_to_float(vision_cfg.get("timeout", 30.0), 30.0),
            max_image_size=_to_int(vision_cfg.get("max_image_size", 2048), 2048),
        ),
        ingestion=IngestionSettings(
            splitter=str(ingestion_cfg.get("splitter", "recursive")),
            chunk_size=_to_int(ingestion_cfg.get("chunk_size", 1000), 1000),
            chunk_overlap=_to_int(ingestion_cfg.get("chunk_overlap", 200), 200),
            separators=separators,
            splitter_kwargs=splitter_kwargs,
            batch_size=_to_int(ingestion_cfg.get("batch_size", 100), 100),
            chunk_refiner=ChunkRefinerSettings(
                use_llm=bool(chunk_refiner_cfg.get("use_llm", False)),
                prompt_path=str(
                    chunk_refiner_cfg.get("prompt_path", "config/prompts/chunk_refinement.txt")
                ),
            ),
            metadata_enricher=MetadataEnricherSettings(
                use_llm=bool(metadata_enricher_cfg.get("use_llm", False)),
            ),
        ),
    )
    validate_settings(settings)
    return settings