import pytest

from app.config import ChunkingConfig
from app.ingestion.chunker import chunk_text, chunk_text_for_corpus, token_count


class TestChunkText:
    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("") == []
        assert chunk_text("   \n  ") == []

    def test_text_shorter_than_chunk_size_is_one_chunk(self):
        text = "one two three"
        assert chunk_text(text, chunk_size=10) == ["one two three"]

    def test_no_overlap_matches_original_fixed_window_behavior(self):
        words = [f"w{i}" for i in range(12)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=5, chunk_overlap=0)
        assert chunks == [
            "w0 w1 w2 w3 w4",
            "w5 w6 w7 w8 w9",
            "w10 w11",
        ]

    def test_overlap_repeats_trailing_words_across_chunks(self):
        words = [f"w{i}" for i in range(12)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=5, chunk_overlap=2)
        assert chunks == [
            "w0 w1 w2 w3 w4",
            "w3 w4 w5 w6 w7",
            "w6 w7 w8 w9 w10",
            "w9 w10 w11",
        ]

    def test_all_words_covered_with_overlap(self):
        words = [f"w{i}" for i in range(37)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=8, chunk_overlap=3)
        recovered = set(" ".join(chunks).split())
        assert recovered == set(words)

    def test_exact_multiple_of_chunk_size_has_no_trailing_empty_chunk(self):
        words = [f"w{i}" for i in range(10)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=5, chunk_overlap=0)
        assert len(chunks) == 2

    @pytest.mark.parametrize("chunk_size", [0, -1])
    def test_non_positive_chunk_size_raises(self, chunk_size):
        with pytest.raises(ValueError, match="chunk_size"):
            chunk_text("some text", chunk_size=chunk_size)

    def test_negative_overlap_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("some text", chunk_size=5, chunk_overlap=-1)

    def test_overlap_equal_to_chunk_size_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("some text", chunk_size=5, chunk_overlap=5)

    def test_overlap_greater_than_chunk_size_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("some text", chunk_size=5, chunk_overlap=6)


class TestChunkTextForCorpus:
    def test_reads_sizes_from_config(self):
        config = ChunkingConfig(chunk_size=4, chunk_overlap=1)
        words = [f"w{i}" for i in range(9)]
        text = " ".join(words)
        chunks = chunk_text_for_corpus(text, config)
        assert chunks == chunk_text(text, chunk_size=4, chunk_overlap=1)


class TestTokenCount:
    def test_counts_words(self):
        assert token_count("one two three") == 3

    def test_empty_string_is_zero(self):
        assert token_count("") == 0
