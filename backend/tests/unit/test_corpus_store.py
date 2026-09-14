"""Pure-logic pieces of corpus_store — turning a name+URL into a full
CorpusConfig. DB-touching CRUD (save/load/delete/list) is covered by
tests/integration/test_corpus_store_db.py, since it needs a real session."""

import re

import pytest

from app.corpus_store import InvalidCorpusNameError, build_corpus_config_from_url


class TestBuildCorpusConfigFromUrl:
    def test_derives_a_same_domain_allow_pattern(self):
        config = build_corpus_config_from_url("acme-docs", "https://docs.acme.com/start")
        assert config.crawl.allow_patterns == [r"^https?://docs\.acme\.com(/|$)"]

    def test_bare_domain_root_url_matches_its_own_allow_pattern(self):
        """Regression test: a bare root URL (no path) normalizes to no
        trailing slash, so a pattern that unconditionally required one
        made the crawler reject its own seed URL before fetching it."""
        config = build_corpus_config_from_url("example-site", "https://example.com")
        pattern = config.crawl.allow_patterns[0]
        assert re.search(pattern, "https://example.com")
        assert re.search(pattern, "https://example.com/about")

    def test_seeds_from_the_given_url(self):
        config = build_corpus_config_from_url("acme-docs", "https://docs.acme.com/start")
        assert config.crawl.mode == "seed_list"
        assert config.crawl.seed_urls == ["https://docs.acme.com/start"]

    def test_generates_a_default_persona_mentioning_the_domain(self):
        config = build_corpus_config_from_url("acme-docs", "https://docs.acme.com")
        assert "docs.acme.com" in config.persona

    def test_uses_the_given_persona_when_provided(self):
        config = build_corpus_config_from_url(
            "acme-docs", "https://docs.acme.com", persona="You are Acme's support bot."
        )
        assert config.persona == "You are Acme's support bot."

    def test_uses_the_given_max_pages(self):
        config = build_corpus_config_from_url("acme-docs", "https://docs.acme.com", max_pages=25)
        assert config.crawl.max_pages == 25

    def test_defaults_max_pages_when_not_given(self):
        config = build_corpus_config_from_url("acme-docs", "https://docs.acme.com")
        assert config.crawl.max_pages == 100

    def test_sets_the_corpus_name(self):
        config = build_corpus_config_from_url("acme-docs", "https://docs.acme.com")
        assert config.name == "acme-docs"

    @pytest.mark.parametrize(
        "bad_name", ["", "a", "Has-Caps", "has_underscore", "-leading-hyphen", "sp ace"]
    )
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(InvalidCorpusNameError):
            build_corpus_config_from_url(bad_name, "https://docs.acme.com")

    @pytest.mark.parametrize(
        "bad_url", ["not-a-url", "ftp://docs.acme.com", "javascript:alert(1)", ""]
    )
    def test_rejects_invalid_urls(self, bad_url):
        with pytest.raises(ValueError, match="Not a valid website URL"):
            build_corpus_config_from_url("acme-docs", bad_url)
