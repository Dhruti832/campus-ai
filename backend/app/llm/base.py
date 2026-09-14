"""Provider protocol — the Strategy interface every LLM backend implements.

Generalizes the original's single hardcoded Ollama-only function
(``llm/client.py``) into a swappable interface picked by ``factory.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    def generate(self, prompt: str) -> str:
        """Return the model's completion for prompt. Raises on failure."""
        ...

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield the model's completion for prompt incrementally, as text
        chunks. Raises on failure (including mid-stream)."""
        ...
