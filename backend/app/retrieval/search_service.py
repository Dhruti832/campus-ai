"""Retrieval orchestration: vector search first, keyword search as a
fallback on failure or empty results. Same resilience pattern as the
original's ``rag/search_service.py``, but both strategies now use a
real database index instead of a Python loop.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import CorpusConfig
from app.embeddings.service import embeddings_available, get_embedding
from app.retrieval.keyword_search import keyword_search
from app.retrieval.result import SearchResult
from app.retrieval.vector_store import vector_search

logger = logging.getLogger(__name__)


def search(
    session: Session,
    corpus_config: CorpusConfig,
    query: str,
    top_k: int | None = None,
    category_filter: str | None = None,
) -> list[SearchResult]:
    top_k = top_k or corpus_config.retrieval.top_k

    vector_results = _try_vector_search(session, corpus_config, query, top_k, category_filter)
    if vector_results:
        return vector_results

    return keyword_search(session, corpus_config.name, query, top_k, category_filter)


def _try_vector_search(
    session: Session,
    corpus_config: CorpusConfig,
    query: str,
    top_k: int,
    category_filter: str | None,
) -> list[SearchResult]:
    if not embeddings_available():
        return []

    query_embedding = get_embedding(query)
    if not query_embedding:
        return []

    try:
        return vector_search(session, corpus_config.name, query_embedding, top_k, category_filter)
    except Exception as exc:
        logger.warning("Vector search failed, falling back to keyword search: %s", exc)
        return []
