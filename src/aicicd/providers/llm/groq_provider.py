from __future__ import annotations

import os
import requests
import time
import logging

logger = logging.getLogger(__name__)

from .base import LLMProvider


class GroqProvider(LLMProvider):
    """Groq LLM Provider"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")

        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"

    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert AI assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            response = requests.post(self.endpoint, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    logger.warning(f"Groq Rate Limit hit. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
            
            # If we reach here, it failed and we can't retry or it's not a 429
            raise RuntimeError(
                f"Groq API error {response.status_code}: {response.text}"
            )
        
        return "" # Should not reach here