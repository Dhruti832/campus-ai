"""/chat route tests — the agent and DB session are mocked; behavior of
get_reply() itself is covered by test_chat_engine.py."""

import json
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


class TestActiveCorpusRoute:
    def test_returns_the_active_corpus_name_and_description(self, client):
        config = CorpusConfig(name="example-docs", description="FastAPI's own docs.", persona="p")
        with patch("app.routes.chat.resolve_active_corpus_config", return_value=config):
            response = client.get("/active-corpus")

        assert response.status_code == 200
        assert response.json() == {"name": "example-docs", "description": "FastAPI's own docs."}

    def test_requires_no_admin_key(self, client):
        with patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG):
            response = client.get("/active-corpus")
        assert response.status_code == 200


class TestChatRoute:
    def test_returns_answer_and_sources(self, client):
        fake_reply = {
            "text": "Fees are due in September.",
            "sources": [{"url": "https://x/fees", "title": "Fees", "category": "Fees"}],
        }
        with (
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
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
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
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

    def test_passes_history_through_as_history_turns(self, client):
        with (
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
            patch(
                "app.routes.chat.get_reply", return_value={"text": "ok", "sources": []}
            ) as mock_get_reply,
        ):
            client.post(
                "/chat",
                json={
                    "query": "q",
                    "history": [
                        {"role": "user", "text": "earlier question"},
                        {"role": "assistant", "text": "earlier answer"},
                    ],
                },
            )

        _, kwargs = mock_get_reply.call_args
        history = kwargs["history"]
        assert [(h.role, h.text) for h in history] == [
            ("user", "earlier question"),
            ("assistant", "earlier answer"),
        ]

    def test_defaults_to_empty_history_when_omitted(self, client):
        with (
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
            patch(
                "app.routes.chat.get_reply", return_value={"text": "ok", "sources": []}
            ) as mock_get_reply,
        ):
            client.post("/chat", json={"query": "q"})

        _, kwargs = mock_get_reply.call_args
        assert kwargs["history"] == []

    def test_rejects_an_invalid_history_role(self, client):
        response = client.post(
            "/chat",
            json={"query": "q", "history": [{"role": "system", "text": "x"}]},
        )
        assert response.status_code == 422


class TestChatStreamRoute:
    def test_streams_ndjson_tokens_then_sources(self, client):
        fake_events = [
            {"type": "token", "text": "Fees "},
            {"type": "token", "text": "are due."},
            {
                "type": "sources",
                "sources": [{"url": "https://x/fees", "title": "Fees", "category": "Fees"}],
            },
        ]
        with (
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
            patch("app.routes.chat.prepare_reply_context", return_value=(None, [])),
            patch("app.routes.chat.get_llm_provider"),
            patch("app.routes.chat.stream_reply_events", return_value=iter(fake_events)),
        ):
            response = client.post("/chat/stream", json={"query": "when are fees due"})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/x-ndjson")
        lines = [json.loads(line) for line in response.text.strip().split("\n")]
        assert lines == fake_events

    def test_passes_query_top_k_and_category_filter_through(self, client):
        with (
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
            patch(
                "app.routes.chat.prepare_reply_context", return_value=(None, [])
            ) as mock_prepare,
            patch("app.routes.chat.get_llm_provider"),
            patch("app.routes.chat.stream_reply_events", return_value=iter([])),
        ):
            client.post(
                "/chat/stream",
                json={"query": "q", "category_filter": "Housing", "top_k": 2},
            )

        args, kwargs = mock_prepare.call_args
        assert args[2] == "q"
        assert kwargs["top_k"] == 2
        assert kwargs["category_filter"] == "Housing"

    def test_empty_query_is_rejected(self, client):
        response = client.post("/chat/stream", json={"query": ""})
        assert response.status_code == 422

    def test_passes_history_through_as_history_turns(self, client):
        with (
            patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG),
            patch("app.routes.chat.prepare_reply_context", return_value=(None, [])),
            patch("app.routes.chat.get_llm_provider"),
            patch(
                "app.routes.chat.stream_reply_events", return_value=iter([])
            ) as mock_stream_events,
        ):
            client.post(
                "/chat/stream",
                json={
                    "query": "q",
                    "history": [{"role": "user", "text": "earlier question"}],
                },
            )

        _, kwargs = mock_stream_events.call_args
        history = kwargs["history"]
        assert [(h.role, h.text) for h in history] == [("user", "earlier question")]


class TestFeedbackRoute:
    def test_records_feedback_against_the_resolved_corpus(self, client):
        db = MagicMock()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.routes.chat.resolve_active_corpus_config", return_value=CONFIG):
            response = client.post(
                "/feedback",
                json={"query": "when are fees due", "answer": "In September.", "rating": 1},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        added = db.add.call_args[0][0]
        assert added.corpus == "test"
        assert added.query == "when are fees due"
        assert added.answer == "In September."
        assert added.rating == 1
        db.commit.assert_called_once()

    def test_rejects_an_invalid_rating(self, client):
        response = client.post(
            "/feedback", json={"query": "q", "answer": "a", "rating": 0}
        )
        assert response.status_code == 422

    def test_empty_query_is_rejected(self, client):
        response = client.post(
            "/feedback", json={"query": "", "answer": "a", "rating": 1}
        )
        assert response.status_code == 422
