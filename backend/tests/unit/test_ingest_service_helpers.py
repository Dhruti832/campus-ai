"""Pure-logic pieces of ingest_service that don't need a real DB."""

from unittest.mock import MagicMock, patch

import requests

from app.ingestion.ingest_service import _fetch_pdf_text


class TestFetchPdfText:
    def test_returns_extracted_text_on_success(self):
        fake_response = MagicMock(content=b"%PDF-fake-bytes")
        fake_response.raise_for_status = MagicMock()
        with (
            patch("app.ingestion.ingest_service.requests.get", return_value=fake_response),
            patch("app.ingestion.ingest_service.extract_pdf_text", return_value="extracted text"),
        ):
            assert _fetch_pdf_text("https://x/a.pdf") == "extracted text"

    def test_returns_none_on_request_failure(self):
        with patch(
            "app.ingestion.ingest_service.requests.get",
            side_effect=requests.RequestException("down"),
        ):
            assert _fetch_pdf_text("https://x/a.pdf") is None
