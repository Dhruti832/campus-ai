"""Chat orchestration: navigation shortcut check -> retrieve -> build
context -> build prompt -> generate, with a graceful fallback to the top
retrieved chunk if the LLM call fails.

Deliberately smaller than the original's chat_engine.py: the broad-query
clarification flow was institution-specific product behavior, not
RAG-engine logic, so it's cut from the MVP engine rather than
generalized. The original's hardcoded DalOnline navigation lookup *is*
generalized, though — see NavigationShortcut in app/config.py and
match_navigation_shortcut() below.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.config import CorpusConfig, NavigationShortcut
from app.ingestion.extractor import clean_text
from app.llm.base import Provider
from app.llm.factory import get_llm_provider
from app.llm.prompt_builder import HistoryTurn, build_prompt
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


def match_navigation_shortcut(
    query: str, corpus_config: CorpusConfig
) -> NavigationShortcut | None:
    """First shortcut whose keywords appear in the query, checked in the
    order the corpus config lists them."""
    query_lower = query.lower()
    for shortcut in corpus_config.navigation_shortcuts:
        if any(keyword.lower() in query_lower for keyword in shortcut.keywords):
            return shortcut
    return None


def _format_shortcut_reply(shortcut: NavigationShortcut) -> dict:
    steps_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(shortcut.steps))
    sources = (
        [{"url": shortcut.url, "title": shortcut.title, "category": "Navigation"}]
        if shortcut.url
        else []
    )
    return {"text": f"{shortcut.title}\n\n{steps_text}", "sources": sources}


def _generate_answer_with_fallback(
    results: list[SearchResult],
    query: str,
    corpus_config: CorpusConfig,
    llm_provider: Provider,
    history: list[HistoryTurn] | None = None,
) -> str:
    context = build_context(results)
    try:
        prompt = build_prompt(query, [context], corpus_config, history=history)
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
    history: list[HistoryTurn] | None = None,
) -> dict:
    shortcut = match_navigation_shortcut(query, corpus_config)
    if shortcut is not None:
        return _format_shortcut_reply(shortcut)

    llm_provider = llm_provider or get_llm_provider()

    results = search(session, corpus_config, query, top_k=top_k, category_filter=category_filter)
    if not results:
        return {"text": NO_RESULTS_MESSAGE, "sources": []}

    answer = _generate_answer_with_fallback(results, query, corpus_config, llm_provider, history)
    return {"text": answer, "sources": format_sources(results)}


def prepare_reply_context(
    session: Session,
    corpus_config: CorpusConfig,
    query: str,
    top_k: int | None = None,
    category_filter: str | None = None,
) -> tuple[NavigationShortcut | None, list[SearchResult]]:
    """The DB-touching half of a reply: shortcut match + retrieval, with no
    LLM call. Split out from get_reply so the streaming route can run this
    *before* returning a StreamingResponse — FastAPI closes yield-based
    dependencies (like the DB session from get_db) once the route function
    returns, which happens before a StreamingResponse body is ever
    consumed, so nothing after this point may touch `session`."""
    shortcut = match_navigation_shortcut(query, corpus_config)
    if shortcut is not None:
        return shortcut, []
    results = search(session, corpus_config, query, top_k=top_k, category_filter=category_filter)
    return None, results


def stream_reply_events(
    query: str,
    corpus_config: CorpusConfig,
    shortcut: NavigationShortcut | None,
    results: list[SearchResult],
    llm_provider: Provider,
    history: list[HistoryTurn] | None = None,
) -> Iterator[dict]:
    """DB-free counterpart to get_reply for the streaming route: yields
    ``{"type": "token", "text": ...}`` chunks as they're generated, then a
    final ``{"type": "sources", "sources": [...]}`` event. Takes the
    shortcut/results already resolved by prepare_reply_context rather than
    a DB session, since this runs after the request's session has closed."""
    if shortcut is not None:
        reply = _format_shortcut_reply(shortcut)
        yield {"type": "token", "text": reply["text"]}
        yield {"type": "sources", "sources": reply["sources"]}
        return

    if not results:
        yield {"type": "token", "text": NO_RESULTS_MESSAGE}
        yield {"type": "sources", "sources": []}
        return

    context = build_context(results)
    prompt = build_prompt(query, [context], corpus_config, history=history)
    try:
        for chunk in llm_provider.stream(prompt):
            yield {"type": "token", "text": chunk}
    except Exception as exc:
        logger.warning("LLM streaming failed, falling back to top chunk: %s", exc)
        yield {"type": "token", "text": extract_answer_from_top_chunk(results)}

    yield {"type": "sources", "sources": format_sources(results)}
