"""Groq provider — used for the live demo instead of local Ollama.
Talks to Groq's OpenAI-compatible chat completions endpoint directly via
requests, matching the project's "hand-rolled, no framework" philosophy
(see docs/adr/0002-hand-rolled-vs-framework.md)."""

from __future__ import annotations

import json
from collections.abc import Iterator

import requests

DEFAULT_TIMEOUT = 60
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    def __init__(self, api_key: str, model: str, timeout: int = DEFAULT_TIMEOUT):
        if not api_key:
            raise ValueError("GroqProvider requires an api_key")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def stream(self, prompt: str) -> Iterator[str]:
        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
            timeout=self.timeout,
            stream=True,
        )
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            payload = line[len("data: ") :]
            if payload.strip() == "[DONE]":
                break
            chunk = json.loads(payload)
            delta = chunk["choices"][0]["delta"].get("content")
            if delta:
                yield delta
