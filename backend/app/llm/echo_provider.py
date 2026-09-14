"""Deterministic, no-network provider — echoes back the retrieved context
instead of calling a real model. Used for CI/E2E, where a real Ollama or
Groq call would be slow, flaky, or need a paid API key; letting tests
assert retrieval actually surfaced the right chunk without depending on
real LLM output."""

from __future__ import annotations

import re
from collections.abc import Iterator

_CONTEXT_PATTERN = re.compile(r"Context:\n(.*?)\n\nQuestion:", re.DOTALL)


class EchoProvider:
    def generate(self, prompt: str) -> str:
        return "".join(self.stream(prompt))

    def stream(self, prompt: str) -> Iterator[str]:
        match = _CONTEXT_PATTERN.search(prompt)
        context = match.group(1).strip() if match else ""
        reply = (
            f"Based on the context: {context}"
            if context
            else "I don't have any context to answer that."
        )
        for word in reply.split(" "):
            yield word + " "
