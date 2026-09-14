"""Optional in-process scheduled re-crawl. Off by default.

Caveat this project's own deploy surfaced: Render's free tier spins the
process down after ~15 minutes with no HTTP traffic and only restarts it
on the next incoming request. A job scheduled here only fires while
something is keeping the instance awake, so it does NOT guarantee
periodic execution on a sleeping free-tier instance. For that, trigger
POST /admin/ingest from an external cron (e.g. a scheduled GitHub
Actions workflow) instead. This module is still the right tool for a
self-hosted or always-on deployment (Docker Compose, a paid instance).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.admin_service import list_available_corpora
from app.config import Settings, get_settings
from app.db.session import get_session_factory
from app.ingestion.ingest_service import ingest_corpus

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_scheduled_ingest(corpus_name: str) -> None:
    """Ingest one corpus with a fresh session. Logs but never raises —
    a scheduled job crashing shouldn't take the whole process down."""
    session = get_session_factory()()
    try:
        result = ingest_corpus(corpus_name, session)
        logger.info(
            "Scheduled ingest of %r: %d sources, %d chunks",
            corpus_name,
            result.sources_ingested,
            result.chunks_ingested,
        )
    except Exception:
        logger.exception("Scheduled ingest of %r failed", corpus_name)
    finally:
        session.close()


def start_scheduler(settings: Settings | None = None) -> BackgroundScheduler | None:
    """Start the scheduler if enabled, one interval job per known corpus.
    Returns None (and starts nothing) when disabled."""
    global _scheduler
    settings = settings or get_settings()
    if not settings.scheduled_ingest_enabled:
        return None

    scheduler = BackgroundScheduler()
    session = get_session_factory()()
    try:
        corpus_names = list_available_corpora(session)
    finally:
        session.close()

    for corpus_name in corpus_names:
        scheduler.add_job(
            run_scheduled_ingest,
            "interval",
            hours=settings.scheduled_ingest_interval_hours,
            args=[corpus_name],
            id=f"ingest-{corpus_name}",
            replace_existing=True,
        )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
