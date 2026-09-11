"""Local Ollama provider. Near-copy of the original's llm/client.py,
generalized to read host/model from Settings instead of raw os.getenv
calls scattered through the function body."""

from __future__ import annotations

import requests

DEFAULT_TIMEOUT = 300


class OllamaProvider:
    def __init__(self, host: str, model: str, timeout: int = DEFAULT_TIMEOUT):
        if not host:
            raise ValueError("OllamaProvider requires a host")
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")
