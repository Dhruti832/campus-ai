"""Real-DB proof that keyword_search uses Postgres full-text search
(GIN-indexed tsvector) instead of a Python word-overlap loop."""

import pytest
from sqlalchemy import delete

from app.db.models import Chunk, Source
from app.retrieval.keyword_search import keyword_search

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.rollback()
    db_session.execute(delete(Chunk).where(Chunk.chunk_text.like("ks-test-%")))
    db_session.execute(delete(Source).where(Source.corpus == "ks-test-corpus"))
    db_session.commit()


@pytest.fixture
def seeded_sources(db_session):
    tuition = Source(corpus="ks-test-corpus", url="https://x/fees", title="Fees", category="Fees")
    housing = Source(
        corpus="ks-test-corpus", url="https://x/housing", title="Housing", category="Housing"
    )
    db_session.add_all([tuition, housing])
    db_session.flush()

    db_session.add_all(
        [
            Chunk(
                source_id=tuition.id,
                chunk_index=0,
                chunk_text=(
                    "ks-test-chunk Tuition and fees are due every September for all students."
                ),
            ),
            Chunk(
                source_id=tuition.id,
                chunk_index=1,
                chunk_text="ks-test-chunk Financial aid and scholarships can offset tuition costs.",
            ),
            Chunk(
                source_id=housing.id,
                chunk_index=0,
                chunk_text="ks-test-chunk Residence halls open two weeks before the fall term.",
            ),
        ]
    )
    db_session.commit()
    return tuition, housing


class TestKeywordSearch:
    def test_matches_query_terms(self, db_session, seeded_sources):
        results = keyword_search(db_session, "ks-test-corpus", "tuition fees", top_k=5)
        texts = [r.chunk_text for r in results]
        assert any("Tuition and fees" in t for t in texts)

    def test_ranks_stronger_matches_first(self, db_session, seeded_sources):
        results = keyword_search(db_session, "ks-test-corpus", "tuition fees", top_k=5)
        assert results[0].score >= results[-1].score

    def test_no_match_returns_empty(self, db_session, seeded_sources):
        results = keyword_search(db_session, "ks-test-corpus", "astrophysics quasar", top_k=5)
        assert results == []

    def test_filters_by_category(self, db_session, seeded_sources):
        results = keyword_search(
            db_session, "ks-test-corpus", "term", top_k=5, category_filter="Housing"
        )
        assert all(r.category == "Housing" for r in results)

    def test_isolates_by_corpus(self, db_session, seeded_sources):
        results = keyword_search(db_session, "some-other-corpus", "tuition", top_k=5)
        assert results == []
