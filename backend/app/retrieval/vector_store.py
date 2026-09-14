"""pgvector-backed similarity search.

This is the direct fix for the original project's anti-pattern: that
version fetched *every* chunk's embedding out of MySQL (no LIMIT, no
index at all) and computed cosine similarity in a Python for-loop. Here,
the database does the nearest-neighbor search itself, using the HNSW
index on ``chunks.embedding`` (see infra/init-db/001_enable_pgvector.sql)
via a single indexed ``ORDER BY ... LIMIT`` query.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Source
from app.retrieval.result import SearchResult

SCORE_PRECISION = 4


def vector_search(
    session: Session,
    corpus: str,
    query_embedding: list[float],
    top_k: int = 5,
    category_filter: str | None = None,
) -> list[SearchResult]:
    """Return the top_k chunks nearest to query_embedding by cosine distance.

    Cosine *distance* (0 = identical, 2 = opposite) is converted to a
    similarity score (1 = identical) to match the rest of the app's
    "higher is better" scoring convention.
    """
    distance = Chunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(Chunk, Source, distance.label("distance"))
        .join(Source, Chunk.source_id == Source.id)
        .where(Source.corpus == corpus)
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )
    if category_filter:
        stmt = stmt.where(Source.category == category_filter)

    rows = session.execute(stmt).all()

    return [
        SearchResult(
            chunk_text=chunk.chunk_text,
            url=source.url,
            title=source.title or "Untitled",
            category=source.category or "General",
            source_type=source.source_type,
            score=round(1 - dist, SCORE_PRECISION),
        )
        for chunk, source, dist in rows
    ]
