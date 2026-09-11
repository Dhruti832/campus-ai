"""Postgres full-text search fallback for when vector search is
unavailable or returns nothing.

Replaces the original's hand-rolled word-overlap scorer (a Python loop
over every chunk's text, `set` intersection per row) with Postgres's own
GIN-indexed ``tsvector``/``ts_rank`` — same fallback *role* in the
pipeline, but backed by a real index this time (see
``chunks_text_search_idx`` in infra/init-db/001_enable_pgvector.sql).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.retrieval.result import SearchResult

SCORE_PRECISION = 4

KEYWORD_SEARCH_SQL = """
    SELECT
        c.chunk_text,
        s.url,
        s.title,
        s.category,
        s.source_type,
        ts_rank(c.text_search, plainto_tsquery('english', :query)) AS rank
    FROM chunks c
    JOIN sources s ON c.source_id = s.id
    WHERE s.corpus = :corpus
      AND c.text_search @@ plainto_tsquery('english', :query)
      AND (CAST(:category AS TEXT) IS NULL OR s.category = CAST(:category AS TEXT))
    ORDER BY rank DESC
    LIMIT :top_k
"""


def keyword_search(
    session: Session,
    corpus: str,
    query: str,
    top_k: int = 5,
    category_filter: str | None = None,
) -> list[SearchResult]:
    rows = session.execute(
        text(KEYWORD_SEARCH_SQL),
        {"query": query, "corpus": corpus, "category": category_filter, "top_k": top_k},
    ).all()

    return [
        SearchResult(
            chunk_text=row.chunk_text,
            url=row.url,
            title=row.title or "Untitled",
            category=row.category or "General",
            source_type=row.source_type,
            score=round(row.rank, SCORE_PRECISION),
        )
        for row in rows
    ]
