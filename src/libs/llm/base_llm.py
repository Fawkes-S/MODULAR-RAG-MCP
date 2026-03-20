"""LLM abstraction contracts used by the project."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLM(ABC):
    """Abstract LLM client interface.

    Keep this contract intentionally small. Downstream modules should depend on
    one stable method (`chat`) so provider replacement stays low-cost.
    """

    @abstractmethod
    def chat(self, messages: list[dict[str, Any]]) -> str:
        """Generate a text response from chat-style messages."""
        raise NotImplementedError
