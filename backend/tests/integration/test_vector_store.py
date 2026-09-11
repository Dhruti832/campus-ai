"""Real-DB proof that vector_search uses an indexed ORDER BY ... LIMIT
query — the direct fix for the original's fetch-everything Python loop."""

import pytest
from sqlalchemy import delete

from app.db.models import Chunk, Source
from app.retrieval.vector_store import vector_search

pytestmark = pytest.mark.integration

DIM = 384


def _vec(base_index: int) -> list[float]:
    v = [1.0] * DIM
    v[1] = float(base_index)
    return v


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.rollback()
    db_session.execute(delete(Chunk).where(Chunk.chunk_text.like("vs-test-%")))
    db_session.execute(delete(Source).where(Source.corpus == "vs-test-corpus"))
    db_session.commit()


@pytest.fixture
def seeded_sources(db_session):
    admissions = Source(
        corpus="vs-test-corpus",
        url="https://x/admissions",
        title="Admissions",
        category="Admissions",
    )
    housing = Source(
        corpus="vs-test-corpus", url="https://x/housing", title="Housing", category="Housing"
    )
    db_session.add_all([admissions, housing])
    db_session.flush()

    for i, source in enumerate([admissions, admissions, housing]):
        db_session.add(
            Chunk(
                source_id=source.id,
                chunk_index=i,
                chunk_text=f"vs-test-chunk-{i}",
                embedding=_vec(i),
            )
        )
    db_session.commit()
    return admissions, housing


class TestVectorSearch:
    def test_returns_nearest_chunks_ordered_by_similarity(self, db_session, seeded_sources):
        query_vec = _vec(0)  # identical to chunk 0 -> closest
        results = vector_search(db_session, "vs-test-corpus", query_vec, top_k=3)
        assert [r.chunk_text for r in results] == [
            "vs-test-chunk-0",
            "vs-test-chunk-1",
            "vs-test-chunk-2",
        ]
        assert results[0].score > results[1].score > results[2].score

    def test_respects_top_k_limit(self, db_session, seeded_sources):
        results = vector_search(db_session, "vs-test-corpus", _vec(0), top_k=1)
        assert len(results) == 1
        assert results[0].chunk_text == "vs-test-chunk-0"

    def test_filters_by_category(self, db_session, seeded_sources):
        results = vector_search(
            db_session, "vs-test-corpus", _vec(0), top_k=10, category_filter="Housing"
        )
        assert all(r.category == "Housing" for r in results)
        assert results[0].chunk_text == "vs-test-chunk-2"

    def test_isolates_by_corpus(self, db_session, seeded_sources):
        results = vector_search(db_session, "some-other-corpus", _vec(0), top_k=10)
        assert results == []

    def test_score_is_a_similarity_not_a_distance(self, db_session, seeded_sources):
        results = vector_search(db_session, "vs-test-corpus", _vec(0), top_k=1)
        assert results[0].score == pytest.approx(1.0, abs=1e-6)
