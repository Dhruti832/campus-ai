"""Application settings and corpus configuration loading.

Two distinct things live here:

- ``Settings``: process-level config from environment variables (DB URL,
  which LLM provider to use, API keys). Never institution-specific.
- ``CorpusConfig``: the *entire* institution-specific personality of the
  bot (crawl scope, persona, category rules) loaded from a YAML file under
  ``backend/config/corpora/``. Swapping institutions means pointing
  ``ACTIVE_CORPUS`` at a different file — never editing code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CORPORA_DIR = Path(__file__).resolve().parent.parent / "config" / "corpora"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://unichat:unichat@localhost:5432/unichat"
    active_corpus: str = "example-docs"

    # "echo" is a deterministic, no-network provider used by the Playwright
    # E2E suite in CI — see app/llm/echo_provider.py.
    llm_provider: Literal["ollama", "groq", "echo"] = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "phi3"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    cors_origins: str = "http://localhost:3000"

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Empty by default so admin routes 403 unless explicitly configured.
    admin_api_key: str = ""

    # Off by default — only useful on an always-running instance (Docker
    # Compose, a paid host). On Render's free tier the process sleeps
    # after ~15 min idle, so this alone won't guarantee periodic runs;
    # see app/scheduler.py.
    scheduled_ingest_enabled: bool = False
    scheduled_ingest_interval_hours: int = 24

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


class CategoryRule(BaseModel):
    name: str
    url_terms: list[str] = Field(default_factory=list)


class CrawlConfig(BaseModel):
    mode: Literal["sitemap", "seed_list"] = "seed_list"
    sitemap_url: str | None = None
    seed_urls: list[str] = Field(default_factory=list)
    allow_patterns: list[str] = Field(default_factory=list)
    deny_patterns: list[str] = Field(default_factory=list)
    max_pages: int = 100
    max_depth: int = 3
    include_files: bool = False
    file_extensions: list[str] = Field(default_factory=list)


class ChunkingConfig(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50


class RetrievalConfig(BaseModel):
    top_k: int = 5


class NavigationShortcut(BaseModel):
    """A fixed, step-by-step answer for a specific known task (e.g. "how do
    I register for a course") that bypasses retrieval and the LLM entirely
    — generalizes the original's hardcoded DalOnline navigation lookup
    into per-corpus config."""

    title: str
    keywords: list[str]
    steps: list[str]
    url: str | None = None


class CorpusConfig(BaseModel):
    name: str
    description: str = ""
    persona: str
    rules: list[str] = Field(default_factory=list)
    categories: list[CategoryRule] = Field(default_factory=list)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    navigation_shortcuts: list[NavigationShortcut] = Field(default_factory=list)

    def infer_category(self, url: str) -> str:
        """Infer a category label from a URL using this corpus's rules."""
        url_lower = url.lower()
        for rule in self.categories:
            if any(term.lower() in url_lower for term in rule.url_terms):
                return rule.name
        return "General"


class CorpusNotFoundError(FileNotFoundError):
    """Raised when the requested corpus YAML file doesn't exist."""


def load_corpus_config(name: str, corpora_dir: Path = CORPORA_DIR) -> CorpusConfig:
    """Load and validate a corpus config YAML file by name (no extension)."""
    path = corpora_dir / f"{name}.yaml"
    if not path.exists():
        raise CorpusNotFoundError(f"No corpus config found at {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return CorpusConfig.model_validate(raw)


@lru_cache
def get_settings() -> Settings:
    return Settings()
