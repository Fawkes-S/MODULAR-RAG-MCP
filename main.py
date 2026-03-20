"""Project entrypoint for local development."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import load_settings
from observability.logger import get_logger


LOGGER = get_logger("main")


def main() -> None:
    """Load settings on startup and fail fast on invalid config."""
    settings = load_settings("config/settings.yaml")
    LOGGER.info(
        "Settings loaded successfully (llm=%s, embedding=%s)",
        settings.llm.provider,
        settings.embedding.provider,
    )
    print("Modular RAG MCP project skeleton is ready.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail-fast behavior required by A3
        LOGGER.error("Startup failed: %s", exc)
        raise SystemExit(1) from exc
