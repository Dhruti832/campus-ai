"""/chat route tests — the agent and DB session are mocked; behavior of
get_reply() itself is covered by test_chat_engine.py."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import CorpusConfig
from app.db.session import get_db
from app.main import app

CONFIG = CorpusConfig(name="test", persona="p")


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    app.state.limiter.reset()
    yield
    app.state.limiter.reset()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: iter([MagicMock()])
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


class TestChatRoute:
    def test_returns_answer_and_sources(self, client):
        fake_reply = {
            "text": "Fees are due in September.",
            "sources": [{"url": "https://x/fees", "title": "Fees", "category": "Fees"}],
        }
        with (
            patch("app.routes.chat.get_active_corpus_config", return_value=CONFIG),
            patch("app.routes.chat.get_reply", return_value=fake_reply),
        ):
            response = client.post("/chat", json={"query": "when are fees due"})

        assert response.status_code == 200
        assert response.json() == {
            "answer": "Fees are due in September.",
            "sources": [{"url": "https://x/fees", "title": "Fees", "category": "Fees"}],
        }

    def test_passes_category_filter_and_top_k_through(self, client):
        with (
            patch("app.routes.chat.get_active_corpus_config", return_value=CONFIG),
            patch(
                "app.routes.chat.get_reply", return_value={"text": "ok", "sources": []}
            ) as mock_get_reply,
        ):
            client.post(
                "/chat",
                json={"query": "q", "category_filter": "Housing", "top_k": 2},
            )

        _, kwargs = mock_get_reply.call_args
        assert kwargs["category_filter"] == "Housing"
        assert kwargs["top_k"] == 2

    def test_empty_query_is_rejected(self, client):
        response = client.post("/chat", json={"query": ""})
        assert response.status_code == 422

    def test_missing_query_is_rejected(self, client):
        response = client.post("/chat", json={})
        assert response.status_code == 422
