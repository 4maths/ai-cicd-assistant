from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate completion from prompt."""
        pass