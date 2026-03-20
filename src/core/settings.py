"""Settings loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str = ""


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    model: str = ""


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


@dataclass(frozen=True)
class EvaluationSettings:
    provider: str
    enabled: bool = False


@dataclass(frozen=True)
class ObservabilitySettings:
    log_level: str
    trace_file: str = "logs/traces.jsonl"


@dataclass(frozen=True)
class Settings:
    llm: LLMSettings
    embedding: EmbeddingSettings
    vector_store: VectorStoreSettings
    retrieval: RetrievalSettings
    rerank: RerankSettings
    evaluation: EvaluationSettings
    observability: ObservabilitySettings


def _read_nested(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"Missing required setting: {path}")
        current = current[key]
    return current


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


def load_settings(path: str) -> Settings:
    """Load YAML settings and validate required fields."""
    settings_path = Path(path)
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")

    raw = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid settings format: root must be a mapping")

    settings = Settings(
        llm=LLMSettings(
            provider=str(_read_nested(raw, "llm.provider")),
            model=str(raw.get("llm", {}).get("model", "")),
        ),
        embedding=EmbeddingSettings(
            provider=str(_read_nested(raw, "embedding.provider")),
            model=str(raw.get("embedding", {}).get("model", "")),
        ),
        vector_store=VectorStoreSettings(
            provider=str(_read_nested(raw, "vector_store.provider")),
            persist_dir=str(raw.get("vector_store", {}).get("persist_dir", "data/db/chroma")),
        ),
        retrieval=RetrievalSettings(
            top_k=int(_read_nested(raw, "retrieval.top_k")),
            sparse_top_k=int(raw.get("retrieval", {}).get("sparse_top_k", 20)),
        ),
        rerank=RerankSettings(
            provider=str(_read_nested(raw, "rerank.provider")),
            enabled=bool(raw.get("rerank", {}).get("enabled", False)),
            top_m=int(raw.get("rerank", {}).get("top_m", 30)),
        ),
        evaluation=EvaluationSettings(
            provider=str(_read_nested(raw, "evaluation.provider")),
            enabled=bool(raw.get("evaluation", {}).get("enabled", False)),
        ),
        observability=ObservabilitySettings(
            log_level=str(_read_nested(raw, "observability.log_level")),
            trace_file=str(raw.get("observability", {}).get("trace_file", "logs/traces.jsonl")),
        ),
    )
    validate_settings(settings)
    return settings
