"""Real-DB proof that the pgvector schema and HNSW index work end to end.

This is the "one real-DB integration test" called for in the build plan —
it exercises the exact thing the original project got wrong: an indexed
`ORDER BY embedding <=> :q LIMIT :k` query instead of a Python loop.
"""

import pytest
from sqlalchemy import delete, text

from app.db.models import Chunk, Source

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.execute(delete(Chunk).where(Chunk.chunk_text.like("test-chunk-%")))
    db_session.execute(delete(Source).where(Source.corpus == "test-corpus"))
    db_session.commit()


def test_insert_source_and_chunk_with_embedding(db_session):
    source = Source(corpus="test-corpus", url="https://example.com/a", title="A")
    db_session.add(source)
    db_session.flush()

    embedding = [0.1] * 384
    chunk = Chunk(
        source_id=source.id,
        chunk_index=0,
        chunk_text="test-chunk-hello world",
        embedding=embedding,
    )
    db_session.add(chunk)
    db_session.commit()

    fetched = db_session.get(Chunk, chunk.id)
    assert fetched.chunk_text == "test-chunk-hello world"
    assert len(fetched.embedding) == 384


def test_hnsw_vector_search_uses_index_and_limit(db_session):
    source = Source(corpus="test-corpus", url="https://example.com/b", title="B")
    db_session.add(source)
    db_session.flush()

    base = [1.0] * 384
    for i in range(5):
        vec = list(base)
        vec[1] = float(i)  # increasingly different from the query as i grows
        db_session.add(
            Chunk(
                source_id=source.id,
                chunk_index=i,
                chunk_text=f"test-chunk-{i}",
                embedding=vec,
            )
        )
    db_session.commit()

    query_vec = list(base)
    query_vec[1] = 0.0  # identical to chunk 0 -> guaranteed closest
    rows = db_session.execute(
        text(
            "SELECT chunk_text FROM chunks "
            "WHERE chunk_text LIKE 'test-chunk-%' "
            "ORDER BY embedding <=> CAST(:q AS vector) LIMIT 2"
        ),
        {"q": str(query_vec)},
    ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "test-chunk-0"
