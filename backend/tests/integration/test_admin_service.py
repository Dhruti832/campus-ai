"""Real-DB tests for admin_service — the corpus-switching state lives in
Postgres (app_state table), not an in-memory variable, specifically so
it survives Render's free-tier restarts."""

import pytest
from sqlalchemy import delete

from app.admin_service import (
    get_active_corpus_name,
    get_corpus_stats,
    list_available_corpora,
    resolve_active_corpus_config,
    set_active_corpus,
)
from app.config import CorpusConfig, Settings
from app.corpus_store import delete_corpus_config, save_corpus_config
from app.db.models import AppState, Chunk, Feedback, Source

pytestmark = pytest.mark.integration

TEST_CORPUS = "admin-test-corpus"


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    db_session.execute(delete(AppState))
    db_session.commit()
    yield
    db_session.rollback()
    db_session.execute(delete(AppState))
    db_session.execute(delete(Chunk).where(Chunk.chunk_text.like("admin-test-%")))
    db_session.execute(
        delete(Source).where(
            (Source.corpus == TEST_CORPUS) | (Source.url.like("https://x/admin-test-%"))
        )
    )
    db_session.execute(delete(Feedback).where(Feedback.query.like("admin-test-%")))
    db_session.commit()


class TestListAvailableCorpora:
    def test_includes_the_real_example_corpora(self, db_session):
        corpora = list_available_corpora(db_session)
        assert "example-docs" in corpora
        assert "example-university" in corpora

    def test_returns_sorted_names(self, db_session):
        corpora = list_available_corpora(db_session)
        assert corpora == sorted(corpora)


class TestGetActiveCorpusName:
    def test_falls_back_to_settings_when_no_row_exists(self, db_session):
        settings = Settings(_env_file=None, active_corpus="example-docs")
        assert get_active_corpus_name(db_session, settings) == "example-docs"

    def test_returns_db_value_when_row_exists(self, db_session):
        db_session.add(AppState(id=1, active_corpus="example-university"))
        db_session.commit()
        settings = Settings(_env_file=None, active_corpus="example-docs")
        assert get_active_corpus_name(db_session, settings) == "example-university"


class TestSetActiveCorpus:
    def test_creates_row_when_none_exists(self, db_session):
        set_active_corpus(db_session, "example-university")
        state = db_session.get(AppState, 1)
        assert state.active_corpus == "example-university"

    def test_updates_existing_row(self, db_session):
        set_active_corpus(db_session, "example-docs")
        set_active_corpus(db_session, "example-university")
        state = db_session.get(AppState, 1)
        assert state.active_corpus == "example-university"

    def test_rejects_unknown_corpus(self, db_session):
        with pytest.raises(ValueError, match="Unknown corpus"):
            set_active_corpus(db_session, "does-not-exist")


class TestResolveActiveCorpusConfig:
    def test_returns_the_switched_corpus_config(self, db_session):
        set_active_corpus(db_session, "example-university")
        config = resolve_active_corpus_config(db_session)
        assert config.name == "example-university"


class TestGetCorpusStats:
    def test_includes_corpora_with_zero_data(self, db_session):
        stats = get_corpus_stats(db_session)
        names = {s["name"] for s in stats}
        assert "example-docs" in names
        assert "example-university" in names
        for entry in stats:
            assert isinstance(entry["sources"], int)
            assert isinstance(entry["chunks"], int)

    def test_counts_sources_and_chunks_for_a_corpus(self, db_session):
        # "example-university" is a real corpus config but never ingested
        # in tests, so use a before/after delta rather than assuming it
        # starts at zero (robust even if that ever changes).
        real_corpus = "example-university"
        before = next(s for s in get_corpus_stats(db_session) if s["name"] == real_corpus)

        source = Source(corpus=real_corpus, url="https://x/admin-test-a", title="A")
        db_session.add(source)
        db_session.flush()
        db_session.add_all(
            [
                Chunk(source_id=source.id, chunk_index=0, chunk_text="admin-test-chunk-1"),
                Chunk(source_id=source.id, chunk_index=1, chunk_text="admin-test-chunk-2"),
            ]
        )
        db_session.commit()

        after = next(s for s in get_corpus_stats(db_session) if s["name"] == real_corpus)
        assert after["sources"] - before["sources"] == 1
        assert after["chunks"] - before["chunks"] == 2

    def test_marks_the_active_corpus(self, db_session):
        set_active_corpus(db_session, "example-university")
        stats = get_corpus_stats(db_session)
        active_entries = [s for s in stats if s["active"]]
        assert len(active_entries) == 1
        assert active_entries[0]["name"] == "example-university"

    def test_includes_zero_feedback_counts_by_default(self, db_session):
        stats = get_corpus_stats(db_session)
        for entry in stats:
            assert entry["thumbs_up"] == 0
            assert entry["thumbs_down"] == 0

    def test_marks_built_in_yaml_corpora_as_not_editable(self, db_session):
        stats = get_corpus_stats(db_session)
        entry = next(s for s in stats if s["name"] == "example-docs")
        assert entry["editable"] is False

    def test_marks_a_dynamic_corpus_as_editable(self, db_session):
        save_corpus_config(db_session, CorpusConfig(name=TEST_CORPUS, persona="p"))
        try:
            stats = get_corpus_stats(db_session)
            entry = next(s for s in stats if s["name"] == TEST_CORPUS)
            assert entry["editable"] is True
        finally:
            delete_corpus_config(db_session, TEST_CORPUS)

    def test_counts_feedback_for_a_corpus(self, db_session):
        real_corpus = "example-university"
        db_session.add_all(
            [
                Feedback(
                    corpus=real_corpus, query="admin-test-q1", answer="a", rating=1
                ),
                Feedback(
                    corpus=real_corpus, query="admin-test-q2", answer="a", rating=1
                ),
                Feedback(
                    corpus=real_corpus, query="admin-test-q3", answer="a", rating=-1
                ),
            ]
        )
        db_session.commit()

        stats = get_corpus_stats(db_session)
        entry = next(s for s in stats if s["name"] == real_corpus)
        assert entry["thumbs_up"] == 2
        assert entry["thumbs_down"] == 1
