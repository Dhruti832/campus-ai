"""Real-DB tests for the crawl -> chunk -> embed -> store pipeline.
Network (crawl, PDF fetch) and the embedding model are mocked; only the
database interactions are real."""

from unittest.mock import patch

import pytest
from sqlalchemy import delete, select

from app.config import CorpusConfig
from app.db.models import Chunk, Source
from app.ingestion.crawler import CrawledPage, CrawlResult
from app.ingestion.ingest_service import ingest_corpus, store_chunks, upsert_source

pytestmark = pytest.mark.integration

TEST_CORPUS = "ingest-test-corpus"


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.rollback()
    source_ids = select(Source.id).where(Source.corpus == TEST_CORPUS)
    db_session.execute(delete(Chunk).where(Chunk.source_id.in_(source_ids)))
    db_session.execute(delete(Source).where(Source.corpus == TEST_CORPUS))
    db_session.commit()


@pytest.fixture
def test_config():
    return CorpusConfig(name=TEST_CORPUS, persona="p")


class TestUpsertSource:
    def test_creates_new_source(self, db_session):
        source = upsert_source(db_session, TEST_CORPUS, "https://x/a", "A", "General", "page")
        db_session.commit()
        assert source.id is not None
        assert source.url == "https://x/a"

    def test_updates_existing_source_and_clears_old_chunks(self, db_session):
        source = upsert_source(
            db_session, TEST_CORPUS, "https://x/a", "Old Title", "General", "page"
        )
        db_session.add(Chunk(source_id=source.id, chunk_index=0, chunk_text="stale chunk"))
        db_session.commit()

        updated = upsert_source(db_session, TEST_CORPUS, "https://x/a", "New Title", "Fees", "page")
        db_session.commit()

        assert updated.id == source.id
        assert updated.title == "New Title"
        assert updated.category == "Fees"
        remaining = db_session.query(Chunk).filter(Chunk.source_id == source.id).all()
        assert remaining == []


class TestStoreChunks:
    def test_creates_chunk_rows_without_embeddings_when_unavailable(self, db_session, test_config):
        source = upsert_source(db_session, TEST_CORPUS, "https://x/a", "A", "General", "page")
        db_session.commit()
        test_config.chunking.chunk_size = 3
        test_config.chunking.chunk_overlap = 0

        with patch("app.ingestion.ingest_service.embeddings_available", return_value=False):
            count = store_chunks(db_session, source, "one two three four five six", test_config)
        db_session.commit()

        assert count == 2
        chunks = db_session.query(Chunk).filter(Chunk.source_id == source.id).all()
        assert len(chunks) == 2
        assert all(c.embedding is None for c in chunks)

    def test_creates_chunk_rows_with_embeddings_when_available(self, db_session, test_config):
        source = upsert_source(db_session, TEST_CORPUS, "https://x/a", "A", "General", "page")
        db_session.commit()

        with (
            patch("app.ingestion.ingest_service.embeddings_available", return_value=True),
            patch("app.ingestion.ingest_service.get_embedding", return_value=[0.1] * 384),
        ):
            store_chunks(db_session, source, "some short text", test_config)
        db_session.commit()

        chunk = db_session.query(Chunk).filter(Chunk.source_id == source.id).one()
        assert len(chunk.embedding) == 384


class TestIngestCorpus:
    def test_ingests_crawled_pages_into_sources_and_chunks(self, db_session, test_config):
        fake_result = CrawlResult(
            pages=[
                CrawledPage(
                    url="https://x/tutorial",
                    title="Tutorial",
                    text="FastAPI is a modern web framework for building APIs with Python.",
                    links=[],
                )
            ],
            file_links=[],
        )

        with (
            patch("app.ingestion.ingest_service.load_corpus_config", return_value=test_config),
            patch("app.ingestion.ingest_service.crawl", return_value=fake_result),
            patch("app.ingestion.ingest_service.embeddings_available", return_value=False),
        ):
            result = ingest_corpus(TEST_CORPUS, db_session)

        assert result.sources_ingested == 1
        assert result.chunks_ingested >= 1

        stored = (
            db_session.query(Source)
            .filter(Source.corpus == TEST_CORPUS, Source.url == "https://x/tutorial")
            .one()
        )
        assert stored.title == "Tutorial"

    def test_fetches_and_ingests_pdf_file_links(self, db_session, test_config):
        fake_result = CrawlResult(
            pages=[],
            file_links=[
                {
                    "file_url": "https://x/handbook.pdf",
                    "source_page": "https://x/tutorial",
                    "file_type": "pdf",
                }
            ],
        )

        with (
            patch("app.ingestion.ingest_service.load_corpus_config", return_value=test_config),
            patch("app.ingestion.ingest_service.crawl", return_value=fake_result),
            patch("app.ingestion.ingest_service.embeddings_available", return_value=False),
            patch(
                "app.ingestion.ingest_service._fetch_pdf_text", return_value="PDF body text here."
            ),
        ):
            result = ingest_corpus(TEST_CORPUS, db_session)

        assert result.sources_ingested == 1
        stored = (
            db_session.query(Source)
            .filter(Source.corpus == TEST_CORPUS, Source.url == "https://x/handbook.pdf")
            .one()
        )
        assert stored.source_type == "file"

    def test_skips_pages_with_no_extractable_text(self, db_session, test_config):
        fake_result = CrawlResult(
            pages=[CrawledPage(url="https://x/empty", title="Empty", text="", links=[])],
            file_links=[],
        )
        with (
            patch("app.ingestion.ingest_service.load_corpus_config", return_value=test_config),
            patch("app.ingestion.ingest_service.crawl", return_value=fake_result),
        ):
            result = ingest_corpus(TEST_CORPUS, db_session)
        assert result.sources_ingested == 0

    def test_skips_non_pdf_file_links(self, db_session, test_config):
        fake_result = CrawlResult(
            pages=[],
            file_links=[
                {
                    "file_url": "https://x/notes.docx",
                    "source_page": "https://x/a",
                    "file_type": "docx",
                }
            ],
        )
        with (
            patch("app.ingestion.ingest_service.load_corpus_config", return_value=test_config),
            patch("app.ingestion.ingest_service.crawl", return_value=fake_result),
        ):
            result = ingest_corpus(TEST_CORPUS, db_session)
        assert result.sources_ingested == 0
