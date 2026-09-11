"""Picks an LLM Provider based on Settings.llm_provider — the Strategy
pattern generalizing the original's single-function Ollama-only client."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import Provider
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider


def get_llm_provider(settings: Settings | None = None) -> Provider:
    settings = settings or get_settings()

    if settings.llm_provider == "groq":
        return GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)
    return OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
