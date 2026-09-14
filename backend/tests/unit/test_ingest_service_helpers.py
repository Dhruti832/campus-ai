"""Pure-logic pieces of ingest_service that don't need a real DB."""

from unittest.mock import MagicMock, patch

import requests

from app.ingestion.extractor import extract_docx_text, extract_pdf_text
from app.ingestion.ingest_service import _extractor_for, _fetch_file_text


class TestExtractorFor:
    def test_matches_pdf_by_extension(self):
        assert _extractor_for("https://x/report.pdf") is extract_pdf_text

    def test_matches_docx_by_extension(self):
        assert _extractor_for("https://x/handbook.docx") is extract_docx_text

    def test_is_case_insensitive(self):
        assert _extractor_for("https://x/REPORT.PDF") is extract_pdf_text

    def test_returns_none_for_unsupported_extension(self):
        assert _extractor_for("https://x/notes.txt") is None


class TestFetchFileText:
    def test_returns_extracted_text_on_success(self):
        fake_response = MagicMock(content=b"fake-bytes")
        fake_response.raise_for_status = MagicMock()
        extractor = MagicMock(return_value="extracted text")
        with patch("app.ingestion.ingest_service.requests.get", return_value=fake_response):
            result = _fetch_file_text("https://x/a.pdf", extractor)

        assert result == "extracted text"
        extractor.assert_called_once_with(b"fake-bytes")

    def test_returns_none_on_request_failure(self):
        with patch(
            "app.ingestion.ingest_service.requests.get",
            side_effect=requests.RequestException("down"),
        ):
            assert _fetch_file_text("https://x/a.pdf", MagicMock()) is None

    def test_returns_none_when_extraction_raises(self):
        """Regression test: a single malformed/truncated file (a real
        crawl hit a PDF that raised pypdf.errors.PdfStreamError) must not
        crash the whole ingestion request — skip it and keep going."""
        fake_response = MagicMock(content=b"not-actually-a-pdf")
        fake_response.raise_for_status = MagicMock()
        extractor = MagicMock(side_effect=ValueError("Stream has ended unexpectedly"))
        with patch("app.ingestion.ingest_service.requests.get", return_value=fake_response):
            assert _fetch_file_text("https://x/a.pdf", extractor) is None
