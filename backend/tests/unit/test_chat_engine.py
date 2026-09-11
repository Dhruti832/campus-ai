"""Agent orchestration tests — search() and the LLM provider are mocked;
query correctness is covered by the retrieval integration tests, and
provider HTTP behavior by test_llm_providers.py."""

from unittest.mock import MagicMock, patch

from app.agent.chat_engine import (
    NO_RESULTS_MESSAGE,
    build_context,
    extract_answer_from_top_chunk,
    format_sources,
    get_reply,
)
from app.config import CorpusConfig
from app.retrieval.result import SearchResult

CONFIG = CorpusConfig(name="test", persona="You are a test assistant.")


def _result(text="chunk text", url="https://x/a", title="A", category="General", score=0.9):
    return SearchResult(
        chunk_text=text, url=url, title=title, category=category, source_type="page", score=score
    )


class TestBuildContext:
    def test_joins_chunk_texts_with_separator(self):
        results = [_result("first"), _result("second")]
        assert build_context(results) == "first\n\n---\n\nsecond"

    def test_stops_before_exceeding_max_chars(self):
        results = [_result("a" * 10), _result("b" * 10)]
        context = build_context(results, max_chars=15)
        assert context == "a" * 10

    def test_empty_results_gives_empty_string(self):
        assert build_context([]) == ""


class TestExtractAnswerFromTopChunk:
    def test_returns_cleaned_top_chunk_when_short(self):
        results = [_result("This is a short answer that fits easily within limits.")]
        answer = extract_answer_from_top_chunk(results, max_chars=200)
        assert answer == "This is a short answer that fits easily within limits."

    def test_truncates_long_chunk_at_sentence_boundary(self):
        long_text = ("Sentence one is here. " * 40).strip()
        results = [_result(long_text)]
        answer = extract_answer_from_top_chunk(results, max_chars=100)
        assert answer.endswith(".")
        assert len(answer) <= 100

    def test_no_results_returns_no_results_message(self):
        assert extract_answer_from_top_chunk([]) == NO_RESULTS_MESSAGE


class TestFormatSources:
    def test_dedupes_by_url(self):
        results = [_result(url="https://x/a"), _result(url="https://x/a"), _result(url="https://x/b")]
        sources = format_sources(results)
        assert [s["url"] for s in sources] == ["https://x/a", "https://x/b"]

    def test_includes_title_and_category(self):
        results = [_result(url="https://x/a", title="Fees Page", category="Fees")]
        sources = format_sources(results)
        assert sources[0] == {"url": "https://x/a", "title": "Fees Page", "category": "Fees"}


class TestGetReply:
    def test_no_results_short_circuits_with_no_results_message(self):
        with patch("app.agent.chat_engine.search", return_value=[]):
            reply = get_reply(session=object(), corpus_config=CONFIG, query="anything")
        assert reply == {"text": NO_RESULTS_MESSAGE, "sources": []}

    def test_uses_llm_answer_and_sources_on_success(self):
        results = [_result(text="Fees are due in September.", url="https://x/fees", title="Fees")]
        fake_provider = MagicMock()
        fake_provider.generate.return_value = "Fees are due in September, per the context."

        with patch("app.agent.chat_engine.search", return_value=results):
            reply = get_reply(
                session=object(), corpus_config=CONFIG, query="when are fees due",
                llm_provider=fake_provider,
            )

        assert reply["text"] == "Fees are due in September, per the context."
        assert reply["sources"] == [
            {"url": "https://x/fees", "title": "Fees", "category": "General"}
        ]
        fake_provider.generate.assert_called_once()

    def test_falls_back_to_top_chunk_when_llm_raises(self):
        results = [_result(text="Fees are due in September for all students.")]
        fake_provider = MagicMock()
        fake_provider.generate.side_effect = RuntimeError("LLM down")

        with patch("app.agent.chat_engine.search", return_value=results):
            reply = get_reply(
                session=object(), corpus_config=CONFIG, query="q", llm_provider=fake_provider
            )

        assert "Fees are due in September" in reply["text"]
        assert reply["sources"]

    def test_passes_top_k_and_category_filter_through_to_search(self):
        with patch("app.agent.chat_engine.search", return_value=[]) as mock_search:
            get_reply(
                session=object(),
                corpus_config=CONFIG,
                query="q",
                top_k=3,
                category_filter="Housing",
            )
        _, kwargs = mock_search.call_args
        assert kwargs["top_k"] == 3
        assert kwargs["category_filter"] == "Housing"

    def test_uses_default_provider_when_none_passed(self):
        with (
            patch("app.agent.chat_engine.search", return_value=[]),
            patch("app.agent.chat_engine.get_llm_provider") as mock_factory,
        ):
            get_reply(session=object(), corpus_config=CONFIG, query="q")
        mock_factory.assert_called_once()
