"""Admin operations: list corpora, view ingestion stats, and switch the
runtime-active corpus. Kept separate from routes/admin.py so the logic
is testable without spinning up FastAPI.

"Switching corpus" writes to the app_state table rather than an
in-memory variable — Render's free tier restarts the process on every
cold start after idling, so an in-memory override would silently reset
itself. The env var (Settings.active_corpus) stays the fallback default
for a fresh database with no app_state row yet.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import CorpusConfig, Settings, get_settings
from app.corpus_store import (
    list_all_corpus_names,
    list_dynamic_corpus_names,
    load_any_corpus_config,
)
from app.db.models import AppState, Chunk, Feedback, Source


def list_available_corpora(session: Session) -> list[str]:
    return list_all_corpus_names(session)


def get_active_corpus_name(session: Session, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    state = session.get(AppState, 1)
    if state and state.active_corpus:
        return state.active_corpus
    return settings.active_corpus


def resolve_active_corpus_config(
    session: Session, settings: Settings | None = None
) -> CorpusConfig:
    return load_any_corpus_config(session, get_active_corpus_name(session, settings))


def set_active_corpus(session: Session, corpus_name: str) -> None:
    if corpus_name not in list_available_corpora(session):
        raise ValueError(f"Unknown corpus: {corpus_name!r}")

    state = session.get(AppState, 1)
    if state is None:
        session.add(AppState(id=1, active_corpus=corpus_name))
    else:
        state.active_corpus = corpus_name
    session.commit()


def get_corpus_stats(session: Session) -> list[dict]:
    """Per-corpus source/chunk counts for every known corpus config,
    including ones with zero ingested data yet."""
    rows = session.execute(
        select(Source.corpus, func.count(func.distinct(Source.id)), func.count(Chunk.id))
        .outerjoin(Chunk, Chunk.source_id == Source.id)
        .group_by(Source.corpus)
    ).all()
    counts = {corpus: (sources, chunks) for corpus, sources, chunks in rows}

    feedback_rows = session.execute(
        select(
            Feedback.corpus,
            func.count(Feedback.id).filter(Feedback.rating == 1),
            func.count(Feedback.id).filter(Feedback.rating == -1),
        ).group_by(Feedback.corpus)
    ).all()
    feedback_counts = {corpus: (up, down) for corpus, up, down in feedback_rows}

    active = get_active_corpus_name(session)
    editable_names = set(list_dynamic_corpus_names(session))
    stats = []
    for name in list_available_corpora(session):
        sources, chunks = counts.get(name, (0, 0))
        thumbs_up, thumbs_down = feedback_counts.get(name, (0, 0))
        stats.append(
            {
                "name": name,
                "sources": sources,
                "chunks": chunks,
                "active": name == active,
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "editable": name in editable_names,
            }
        )
    return stats
