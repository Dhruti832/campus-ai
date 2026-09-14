"""Glues crawl -> chunk -> embed -> store together for one corpus.

Kept in app/ (rather than only in scripts/ingest.py) so this logic is
covered by the same 90% coverage gate as the rest of the backend;
scripts/ingest.py is a thin CLI wrapper around ``ingest_corpus``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CorpusConfig
from app.corpus_store import load_any_corpus_config
from app.db.models import Chunk, Source
from app.embeddings.service import embeddings_available, get_embedding
from app.ingestion.chunker import chunk_text_for_corpus
from app.ingestion.crawler import CrawlResult, crawl
from app.ingestion.extractor import clean_text, extract_docx_text, extract_pdf_text

logger = logging.getLogger(__name__)

FILE_FETCH_TIMEOUT = 30

# Extension -> extractor, in the order they're checked. Adding a new file
# type (e.g. .pptx) is just one more entry here plus an extractor function.
FILE_EXTRACTORS = {
    ".pdf": extract_pdf_text,
    ".docx": extract_docx_text,
}


@dataclass
class IngestResult:
    sources_ingested: int
    chunks_ingested: int


def upsert_source(
    session: Session, corpus: str, url: str, title: str, category: str, source_type: str
) -> Source:
    """Insert or update a Source row, clearing any of its existing chunks
    so re-ingestion doesn't leave stale chunks behind."""
    existing = session.execute(
        select(Source).where(Source.corpus == corpus, Source.url == url)
    ).scalar_one_or_none()

    if existing is None:
        source = Source(
            corpus=corpus, url=url, title=title, category=category, source_type=source_type
        )
        session.add(source)
        session.flush()
        return source

    existing.title = title
    existing.category = category
    existing.source_type = source_type
    for chunk in list(existing.chunks):
        session.delete(chunk)
    session.flush()
    return existing


def store_chunks(session: Session, source: Source, text: str, corpus_config: CorpusConfig) -> int:
    pieces = chunk_text_for_corpus(text, corpus_config.chunking)
    for index, piece in enumerate(pieces):
        embedding = get_embedding(piece) if embeddings_available() else None
        session.add(
            Chunk(source_id=source.id, chunk_index=index, chunk_text=piece, embedding=embedding)
        )
    return len(pieces)


def _ingest_pages(
    session: Session, result: CrawlResult, corpus_config: CorpusConfig
) -> tuple[int, int]:
    sources_count = 0
    chunks_count = 0
    for page in result.pages:
        cleaned = clean_text(page.text)
        if not cleaned:
            continue
        category = corpus_config.infer_category(page.url)
        source = upsert_source(session, corpus_config.name, page.url, page.title, category, "page")
        chunks_count += store_chunks(session, source, cleaned, corpus_config)
        sources_count += 1
    return sources_count, chunks_count


def _extractor_for(file_url: str) -> Callable[[bytes], str] | None:
    lower = file_url.lower()
    for extension, extractor in FILE_EXTRACTORS.items():
        if lower.endswith(extension):
            return extractor
    return None


def _fetch_file_text(file_url: str, extractor: Callable[[bytes], str]) -> str | None:
    try:
        response = requests.get(file_url, timeout=FILE_FETCH_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", file_url, exc)
        return None

    try:
        return extractor(response.content)
    except Exception as exc:
        # A single malformed/truncated PDF or DOCX (real-world crawls hit
        # these — a linked file that 404s to an HTML error page saved with
        # a .pdf extension, a corrupted upload, etc.) must not take down
        # ingestion for the whole corpus. pypdf and python-docx don't share
        # a common exception base, so this is deliberately broad; skipping
        # one bad file and logging it beats crashing the request.
        logger.warning("Failed to extract text from %s: %s", file_url, exc)
        return None


def _ingest_files(
    session: Session, result: CrawlResult, corpus_config: CorpusConfig
) -> tuple[int, int]:
    sources_count = 0
    chunks_count = 0
    for file_link in result.file_links:
        file_url = file_link["file_url"]
        extractor = _extractor_for(file_url)
        if extractor is None:
            continue
        text = _fetch_file_text(file_url, extractor)
        if not text:
            continue
        category = corpus_config.infer_category(file_url)
        title = file_url.rsplit("/", 1)[-1]
        source = upsert_source(session, corpus_config.name, file_url, title, category, "file")
        chunks_count += store_chunks(session, source, text, corpus_config)
        sources_count += 1
    return sources_count, chunks_count


def ingest_corpus(corpus_name: str, session: Session) -> IngestResult:
    """Crawl, chunk, embed, and store one corpus's content. Commits on
    success; caller owns the session's lifecycle (open/close)."""
    corpus_config = load_any_corpus_config(session, corpus_name)
    result = crawl(corpus_config.crawl)

    page_sources, page_chunks = _ingest_pages(session, result, corpus_config)
    file_sources, file_chunks = _ingest_files(session, result, corpus_config)
    session.commit()

    return IngestResult(
        sources_ingested=page_sources + file_sources,
        chunks_ingested=page_chunks + file_chunks,
    )
