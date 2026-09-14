"""Orchestration tests — vector_search/keyword_search are mocked so this
verifies only the vector-first/fallback wiring, not query correctness
(that's covered by the real-DB integration tests)."""

from unittest.mock import patch

from app.config import CorpusConfig
from app.retrieval.result import SearchResult
from app.retrieval.search_service import search

CONFIG = CorpusConfig(name="test-corpus", persona="p")

SOME_RESULT = [
    SearchResult(
        chunk_text="text",
        url="https://x",
        title="T",
        category="General",
        source_type="page",
        score=0.9,
    )
]


class TestSearch:
    def test_returns_vector_results_when_available(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=[0.1, 0.2]),
            patch("app.retrieval.search_service.vector_search", return_value=SOME_RESULT) as vs,
            patch("app.retrieval.search_service.keyword_search") as ks,
        ):
            results = search(session=object(), corpus_config=CONFIG, query="hi")

        assert results == SOME_RESULT
        vs.assert_called_once()
        ks.assert_not_called()

    def test_falls_back_to_keyword_when_embeddings_unavailable(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=False),
            patch("app.retrieval.search_service.vector_search") as vs,
            patch("app.retrieval.search_service.keyword_search", return_value=SOME_RESULT) as ks,
        ):
            results = search(session=object(), corpus_config=CONFIG, query="hi")

        assert results == SOME_RESULT
        vs.assert_not_called()
        ks.assert_called_once()

    def test_falls_back_to_keyword_when_query_embedding_is_none(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=None),
            patch("app.retrieval.search_service.vector_search") as vs,
            patch("app.retrieval.search_service.keyword_search", return_value=SOME_RESULT) as ks,
        ):
            results = search(session=object(), corpus_config=CONFIG, query="hi")

        assert results == SOME_RESULT
        vs.assert_not_called()
        ks.assert_called_once()

    def test_falls_back_to_keyword_when_vector_search_returns_empty(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=[0.1]),
            patch("app.retrieval.search_service.vector_search", return_value=[]),
            patch("app.retrieval.search_service.keyword_search", return_value=SOME_RESULT) as ks,
        ):
            results = search(session=object(), corpus_config=CONFIG, query="hi")

        assert results == SOME_RESULT
        ks.assert_called_once()

    def test_falls_back_to_keyword_when_vector_search_raises(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=[0.1]),
            patch("app.retrieval.search_service.vector_search", side_effect=RuntimeError("boom")),
            patch("app.retrieval.search_service.keyword_search", return_value=SOME_RESULT) as ks,
        ):
            results = search(session=object(), corpus_config=CONFIG, query="hi")

        assert results == SOME_RESULT
        ks.assert_called_once()

    def test_uses_corpus_default_top_k_when_not_specified(self):
        config = CorpusConfig(name="c", persona="p")
        config.retrieval.top_k = 7
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=[0.1]),
            patch("app.retrieval.search_service.vector_search", return_value=SOME_RESULT) as vs,
        ):
            search(session=object(), corpus_config=config, query="hi")

        assert vs.call_args.args[3] == 7

    def test_explicit_top_k_overrides_corpus_default(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=[0.1]),
            patch("app.retrieval.search_service.vector_search", return_value=SOME_RESULT) as vs,
        ):
            search(session=object(), corpus_config=CONFIG, query="hi", top_k=2)

        assert vs.call_args.args[3] == 2

    def test_passes_category_filter_through(self):
        with (
            patch("app.retrieval.search_service.embeddings_available", return_value=True),
            patch("app.retrieval.search_service.get_embedding", return_value=[0.1]),
            patch("app.retrieval.search_service.vector_search", return_value=SOME_RESULT) as vs,
        ):
            search(session=object(), corpus_config=CONFIG, query="hi", category_filter="Admissions")

        assert vs.call_args.args[4] == "Admissions"
