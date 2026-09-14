"""Real-DB tests for corpus_store — corpora created at runtime via the
admin panel, stored as a JSONB row rather than a YAML file."""

import pytest
from sqlalchemy import delete

from app.config import CorpusConfig
from app.corpus_store import (
    build_corpus_config_from_url,
    delete_corpus_config,
    list_all_corpus_names,
    list_dynamic_corpus_names,
    load_any_corpus_config,
    load_dynamic_corpus_config,
    save_corpus_config,
    update_corpus_config,
)
from app.db.models import Chunk, CorpusConfigRow, Source

pytestmark = pytest.mark.integration

TEST_CORPUS = "corpus-store-test"


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.rollback()
    db_session.execute(delete(CorpusConfigRow).where(CorpusConfigRow.name == TEST_CORPUS))
    db_session.execute(delete(Chunk).where(Chunk.chunk_text.like("corpus-store-test-%")))
    db_session.execute(delete(Source).where(Source.corpus == TEST_CORPUS))
    db_session.commit()


def _config(name=TEST_CORPUS, persona="A test persona."):
    return CorpusConfig(name=name, persona=persona)


class TestSaveAndLoadDynamicCorpusConfig:
    def test_load_returns_none_for_an_unknown_corpus(self, db_session):
        assert load_dynamic_corpus_config(db_session, "does-not-exist-anywhere") is None

    def test_save_then_load_round_trips(self, db_session):
        save_corpus_config(db_session, _config())
        loaded = load_dynamic_corpus_config(db_session, TEST_CORPUS)
        assert loaded is not None
        assert loaded.name == TEST_CORPUS
        assert loaded.persona == "A test persona."

    def test_save_again_updates_the_existing_row(self, db_session):
        save_corpus_config(db_session, _config(persona="First persona."))
        save_corpus_config(db_session, _config(persona="Second persona."))

        loaded = load_dynamic_corpus_config(db_session, TEST_CORPUS)
        assert loaded.persona == "Second persona."
        assert db_session.query(CorpusConfigRow).filter_by(name=TEST_CORPUS).count() == 1


class TestListDynamicCorpusNames:
    def test_includes_a_saved_corpus(self, db_session):
        save_corpus_config(db_session, _config())
        assert TEST_CORPUS in list_dynamic_corpus_names(db_session)

    def test_does_not_include_the_built_in_yaml_corpora(self, db_session):
        names = list_dynamic_corpus_names(db_session)
        assert "example-docs" not in names


class TestListAllCorpusNames:
    def test_merges_yaml_and_dynamic_corpora(self, db_session):
        save_corpus_config(db_session, _config())
        names = list_all_corpus_names(db_session)
        assert TEST_CORPUS in names
        assert "example-docs" in names
        assert names == sorted(names)


class TestLoadAnyCorpusConfig:
    def test_resolves_a_dynamic_corpus(self, db_session):
        save_corpus_config(db_session, _config(persona="Dynamic persona."))
        config = load_any_corpus_config(db_session, TEST_CORPUS)
        assert config.persona == "Dynamic persona."

    def test_falls_back_to_yaml_for_a_built_in_corpus(self, db_session):
        config = load_any_corpus_config(db_session, "example-docs")
        assert config.name == "example-docs"


class TestDeleteCorpusConfig:
    def test_returns_false_for_an_unknown_corpus(self, db_session):
        assert delete_corpus_config(db_session, "does-not-exist-anywhere") is False

    def test_removes_the_config_row(self, db_session):
        save_corpus_config(db_session, _config())
        assert delete_corpus_config(db_session, TEST_CORPUS) is True
        assert load_dynamic_corpus_config(db_session, TEST_CORPUS) is None

    def test_cascades_to_ingested_sources_and_chunks(self, db_session):
        save_corpus_config(db_session, _config())
        source = Source(corpus=TEST_CORPUS, url="https://x/a", title="A")
        db_session.add(source)
        db_session.flush()
        db_session.add(
            Chunk(source_id=source.id, chunk_index=0, chunk_text="corpus-store-test-chunk")
        )
        db_session.commit()

        delete_corpus_config(db_session, TEST_CORPUS)

        assert db_session.query(Source).filter_by(corpus=TEST_CORPUS).count() == 0
        assert (
            db_session.query(Chunk).filter(Chunk.chunk_text.like("corpus-store-test-%")).count()
            == 0
        )

    def test_never_touches_a_built_in_yaml_corpus(self, db_session):
        assert delete_corpus_config(db_session, "example-docs") is False


class TestUpdateCorpusConfig:
    def test_returns_none_for_an_unknown_corpus(self, db_session):
        assert update_corpus_config(db_session, "does-not-exist-anywhere", persona="x") is None

    def test_never_touches_a_built_in_yaml_corpus(self, db_session):
        assert update_corpus_config(db_session, "example-docs", persona="x") is None

    def test_updates_the_persona(self, db_session):
        save_corpus_config(db_session, _config(persona="Original persona."))
        updated = update_corpus_config(db_session, TEST_CORPUS, persona="New persona.")
        assert updated.persona == "New persona."
        assert load_dynamic_corpus_config(db_session, TEST_CORPUS).persona == "New persona."

    def test_updates_max_pages(self, db_session):
        save_corpus_config(db_session, _config())
        updated = update_corpus_config(db_session, TEST_CORPUS, max_pages=250)
        assert updated.crawl.max_pages == 250

    def test_updates_website_url_and_rederives_the_allow_pattern(self, db_session):
        save_corpus_config(db_session, _config())
        updated = update_corpus_config(
            db_session, TEST_CORPUS, website_url="https://newsite.example.com/docs"
        )
        assert updated.crawl.seed_urls == ["https://newsite.example.com/docs"]
        assert updated.crawl.allow_patterns == [r"^https?://newsite\.example\.com(/|$)"]

    def test_rejects_an_invalid_website_url(self, db_session):
        save_corpus_config(db_session, _config())
        with pytest.raises(ValueError, match="Not a valid website URL"):
            update_corpus_config(db_session, TEST_CORPUS, website_url="not-a-url")

    def test_leaves_unspecified_fields_unchanged(self, db_session):
        save_corpus_config(
            db_session, build_corpus_config_from_url(TEST_CORPUS, "https://acme.example.com")
        )
        updated = update_corpus_config(db_session, TEST_CORPUS, persona="Only persona changed.")
        assert updated.crawl.seed_urls == ["https://acme.example.com"]
        assert updated.crawl.max_pages == 100
