from __future__ import annotations

from aicicd.domain.enums import ProviderName

from .base import LLMProvider
from .groq_provider import GroqProvider


def get_provider(name: str) -> LLMProvider:
    try:
        provider = ProviderName(name)
    except ValueError:
        raise ValueError(f"Unsupported provider: {name}")

    if provider == ProviderName.GROQ:
        return GroqProvider()

    # Placeholder cho tương lai
    elif provider == ProviderName.OPENAI:
        raise NotImplementedError("OpenAI provider not implemented yet")

    elif provider == ProviderName.OLLAMA:
        raise NotImplementedError("Ollama provider not implemented yet")

    elif provider == ProviderName.MOCK:
        return MockProvider()

    else:
        raise ValueError(f"Unsupported provider: {name}")


# =========================
# Mock provider (test)
# =========================
class MockProvider(LLMProvider):
    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        return '{"summary": "mock response", "decision": "APPROVE"}'