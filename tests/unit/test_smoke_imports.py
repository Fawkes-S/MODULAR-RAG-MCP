"""Smoke tests for top-level package imports."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_top_level_packages_are_importable() -> None:
    """Ensure core top-level packages can be imported."""
    src_path = Path(__file__).resolve().parents[2] / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    modules = ("mcp_server", "core", "ingestion", "libs", "observability")
    for module in modules:
        imported = importlib.import_module(module)
        assert imported is not None
