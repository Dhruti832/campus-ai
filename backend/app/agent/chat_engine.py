"""Chat orchestration: retrieve -> build context -> build prompt ->
generate, with a graceful fallback to the top retrieved chunk if the LLM
call fails.

Deliberately smaller than the original's chat_engine.py: the broad-query
clarification flow and the hardcoded DalOnline navigation lookup were
institution-specific product behavior, not RAG-engine logic, so they're
cut from the MVP engine rather than generalized (see the build plan's
Phase 2 stretch list for a config-driven version of the clarification
idea).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import CorpusConfig
from app.ingestion.extractor import clean_text
from app.llm.base import Provider
from app.llm.factory import get_llm_provider
from app.llm.prompt_builder import build_prompt
from app.retrieval.result import SearchResult
from app.retrieval.search_service import search

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 3000
MAX_EXCERPT_CHARS = 600
NO_RESULTS_MESSAGE = "I couldn't find anything relevant to that question. Try rephrasing it."


def build_context(results: list[SearchResult], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    parts = []
    total = 0
    for result in results:
        text = result.chunk_text.strip()
        if total + len(text) > max_chars:
            break
        parts.append(text)
        total += len(text)
    return "\n\n---\n\n".join(parts)


def extract_answer_from_top_chunk(
    results: list[SearchResult], max_chars: int = MAX_EXCERPT_CHARS
) -> str:
    if not results:
        return NO_RESULTS_MESSAGE

    top = clean_text(results[0].chunk_text)
    if len(top) <= max_chars:
        return top

    excerpt = top[:max_chars]
    last_period = excerpt.rfind(".")
    if last_period > max_chars // 2:
        return excerpt[: last_period + 1]
    return excerpt


def format_sources(results: list[SearchResult]) -> list[dict]:
    seen_urls = set()
    sources = []
    for result in results:
        if result.url in seen_urls:
            continue
        seen_urls.add(result.url)
        sources.append({"url": result.url, "title": result.title, "category": result.category})
    return sources


def _generate_answer_with_fallback(
    results: list[SearchResult],
    query: str,
    corpus_config: CorpusConfig,
    llm_provider: Provider,
) -> str:
    context = build_context(results)
    try:
        prompt = build_prompt(query, [context], corpus_config)
        return llm_provider.generate(prompt)
    except Exception as exc:
        logger.warning("LLM generation failed, falling back to top chunk: %s", exc)
        return extract_answer_from_top_chunk(results)


def get_reply(
    session: Session,
    corpus_config: CorpusConfig,
    query: str,
    llm_provider: Provider | None = None,
    top_k: int | None = None,
    category_filter: str | None = None,
) -> dict:
    llm_provider = llm_provider or get_llm_provider()

    results = search(session, corpus_config, query, top_k=top_k, category_filter=category_filter)
    if not results:
        return {"text": NO_RESULTS_MESSAGE, "sources": []}

    answer = _generate_answer_with_fallback(results, query, corpus_config, llm_provider)
    return {"text": answer, "sources": format_sources(results)}
