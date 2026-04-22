from __future__ import annotations

import requests
import logging
from .base import LLMProvider

logger = logging.getLogger(__name__)

class FPTProvider(LLMProvider):
    """
    Self-hosted LLM Provider running on FPT GPU VM.
    Uses vLLM with OpenAI-compatible API.
    """

    def __init__(self, endpoint: str = "http://124.197.18.41:8000/v1/chat/completions"):
        self.endpoint = endpoint
        self.model = "deepseek-ai/deepseek-coder-6.7b-instruct"

    def complete(self, prompt: str, max_tokens: int = 1500) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        try:
            response = requests.post(self.endpoint, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"FPT LLM Provider error: {e}")
            raise RuntimeError(f"FPT LLM Provider error: {str(e)}")
