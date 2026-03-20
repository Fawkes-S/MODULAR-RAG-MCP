"""Tests for settings loading and validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings


def test_load_settings_success() -> None:
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    assert isinstance(settings, Settings)
    assert settings.embedding.provider == "openai"
    assert settings.retrieval.top_k > 0


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
