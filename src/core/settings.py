"""Settings loading and validation.

将 `config/settings.yaml` 解析为强类型 `Settings` 对象，
并在启动阶段执行 fail-fast 校验，避免配置问题延迟到运行时。
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
    max_retries: int = 2
    retry_backoff_seconds: float = 0.25
    retry_backoff_multiplier: float = 2.0
    retry_max_backoff_seconds: float = 2.0


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
    max_retries: int = 2
    retry_backoff_seconds: float = 0.25
    retry_backoff_multiplier: float = 2.0
    retry_max_backoff_seconds: float = 2.0


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
    max_chars: int = 0
    truncate_long_text: bool = False
    device: str = "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = False


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
    """将 section 标准化为 dict；缺失或类型错误时返回空 dict。"""
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
    """解析 .env（最小实现）：忽略空行与注释，支持 KEY=VALUE。"""
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
    """从 settings 目录向上查找最近的 `.env` 并注入环境变量（不覆盖已有值）。"""
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
    """递归解析配置对象中的环境变量占位符。"""
    if isinstance(data, dict):
        return {key: _resolve_env_placeholders(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_resolve_env_placeholders(item) for item in data]
    if isinstance(data, str):
        return _resolve_env_in_string(data)
    return data


def _resolve_existing_path_from_candidates(raw_value: str, candidates: list[Path]) -> str:
    """将相对路径解析为“已存在”的绝对路径；找不到则返回原值。

    设计意图：
    - 配置里常用相对路径（例如 `data/models/...`），但运行时 cwd 可能变化（IDE/测试目录）。
    - 对本地路径做“存在即绝对化”，可避免 cwd 差异导致找不到文件。
    """
    if not isinstance(raw_value, str):
        return str(raw_value)

    value = raw_value.strip()
    if not value:
        return value

    path_obj = Path(value)
    if path_obj.is_absolute():
        return str(path_obj)

    # 先试 cwd（兼容已有行为），再试 settings 目录与项目根目录。
    for base in candidates:
        candidate = (base / path_obj).resolve()
        if candidate.exists():
            return str(candidate)

    return raw_value

def validate_settings(settings: Settings) -> None:
    """校验关键配置字段并做边界检查。"""
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

    if settings.llm.max_retries < 0:
        raise ValueError("Invalid setting: llm.max_retries must be >= 0")
    if settings.llm.retry_backoff_seconds < 0:
        raise ValueError("Invalid setting: llm.retry_backoff_seconds must be >= 0")
    if settings.llm.retry_backoff_multiplier < 1.0:
        raise ValueError("Invalid setting: llm.retry_backoff_multiplier must be >= 1.0")
    if settings.llm.retry_max_backoff_seconds < 0:
        raise ValueError("Invalid setting: llm.retry_max_backoff_seconds must be >= 0")

    if settings.vision_llm.max_retries < 0:
        raise ValueError("Invalid setting: vision_llm.max_retries must be >= 0")
    if settings.vision_llm.retry_backoff_seconds < 0:
        raise ValueError("Invalid setting: vision_llm.retry_backoff_seconds must be >= 0")
    if settings.vision_llm.retry_backoff_multiplier < 1.0:
        raise ValueError("Invalid setting: vision_llm.retry_backoff_multiplier must be >= 1.0")
    if settings.vision_llm.retry_max_backoff_seconds < 0:
        raise ValueError("Invalid setting: vision_llm.retry_max_backoff_seconds must be >= 0")


def load_settings(path: str) -> Settings:
    """读取 YAML 配置并返回强类型 Settings。"""
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
    separators = [str(item) for item in separators_raw if isinstance(item, str)] if isinstance(separators_raw, list) else []

    splitter_kwargs_raw = ingestion_cfg.get("splitter_kwargs", {})
    splitter_kwargs = dict(splitter_kwargs_raw) if isinstance(splitter_kwargs_raw, dict) else {}

    project_root = settings_path.resolve().parent.parent
    settings_dir = settings_path.resolve().parent

    embedding_provider = str(_read_nested(raw, "embedding.provider"))
    embedding_model = str(embedding_cfg.get("model", ""))
    if embedding_provider.strip().lower() == "huggingface_local":
        embedding_model = _resolve_existing_path_from_candidates(
            embedding_model,
            candidates=[Path.cwd(), settings_dir, project_root],
        )
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
            max_retries=_to_int(llm_cfg.get("max_retries", 2), 2),
            retry_backoff_seconds=_to_float(llm_cfg.get("retry_backoff_seconds", 0.25), 0.25),
            retry_backoff_multiplier=_to_float(llm_cfg.get("retry_backoff_multiplier", 2.0), 2.0),
            retry_max_backoff_seconds=_to_float(llm_cfg.get("retry_max_backoff_seconds", 2.0), 2.0),
        ),
        embedding=EmbeddingSettings(
            provider=embedding_provider,
            model=embedding_model,
            api_key=str(embedding_cfg.get("api_key", "")),
            base_url=str(embedding_cfg.get("base_url", "https://api.openai.com/v1")),
            endpoint=str(embedding_cfg.get("endpoint", "")),
            deployment_name=str(embedding_cfg.get("deployment_name", "")),
            api_version=str(embedding_cfg.get("api_version", "")),
            timeout=_to_float(embedding_cfg.get("timeout", 30.0), 30.0),
            max_chars=_to_int(embedding_cfg.get("max_chars", 0), 0),
            truncate_long_text=bool(embedding_cfg.get("truncate_long_text", False)),
            device=str(embedding_cfg.get("device", "cpu")),
            batch_size=_to_int(embedding_cfg.get("batch_size", 32), 32),
            normalize_embeddings=bool(embedding_cfg.get("normalize_embeddings", False)),
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
            max_retries=_to_int(vision_cfg.get("max_retries", 2), 2),
            retry_backoff_seconds=_to_float(vision_cfg.get("retry_backoff_seconds", 0.25), 0.25),
            retry_backoff_multiplier=_to_float(vision_cfg.get("retry_backoff_multiplier", 2.0), 2.0),
            retry_max_backoff_seconds=_to_float(vision_cfg.get("retry_max_backoff_seconds", 2.0), 2.0),
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
                prompt_path=str(chunk_refiner_cfg.get("prompt_path", "config/prompts/chunk_refinement.txt")),
            ),
            metadata_enricher=MetadataEnricherSettings(
                use_llm=bool(metadata_enricher_cfg.get("use_llm", False)),
            ),
        ),
    )
    validate_settings(settings)
    return settings

