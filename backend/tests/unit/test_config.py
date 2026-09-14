"""Tests for Settings and CorpusConfig loading."""

import pytest
from pydantic import ValidationError

from app.config import (
    CorpusConfig,
    CorpusNotFoundError,
    Settings,
    get_settings,
    load_corpus_config,
)


class TestSettings:
    def test_defaults(self):
        settings = Settings(_env_file=None)
        assert settings.llm_provider == "ollama"
        assert settings.embedding_dim == 384

    def test_cors_origin_list_splits_and_strips(self):
        settings = Settings(_env_file=None, cors_origins="http://a.com, http://b.com ,,")
        assert settings.cors_origin_list() == ["http://a.com", "http://b.com"]

    def test_cors_origin_list_empty(self):
        settings = Settings(_env_file=None, cors_origins="")
        assert settings.cors_origin_list() == []

    def test_get_settings_is_cached(self):
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
        assert first is second
        get_settings.cache_clear()


class TestLoadCorpusConfig:
    def test_loads_example_university(self):
        config = load_corpus_config("example-university")
        assert config.name == "example-university"
        assert config.crawl.mode == "sitemap"
        assert config.chunking.chunk_size == 500

    def test_loads_example_docs(self):
        config = load_corpus_config("example-docs")
        assert config.crawl.mode == "seed_list"
        assert config.crawl.seed_urls

    def test_missing_corpus_raises(self, tmp_path):
        with pytest.raises(CorpusNotFoundError):
            load_corpus_config("does-not-exist", corpora_dir=tmp_path)

    def test_requires_persona(self, tmp_path):
        (tmp_path / "broken.yaml").write_text("name: broken\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            load_corpus_config("broken", corpora_dir=tmp_path)


class TestInferCategory:
    def test_matches_rule(self):
        config = CorpusConfig(
            name="t",
            persona="p",
            categories=[
                {"name": "Admissions", "url_terms": ["admission", "apply"]},
                {"name": "Fees", "url_terms": ["tuition"]},
            ],
        )
        assert config.infer_category("https://example.com/admissions/apply") == "Admissions"
        assert config.infer_category("https://example.com/fees/tuition") == "Fees"

    def test_falls_back_to_general(self):
        config = CorpusConfig(name="t", persona="p", categories=[])
        assert config.infer_category("https://example.com/anything") == "General"
