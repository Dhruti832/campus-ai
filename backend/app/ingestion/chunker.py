"""Fixed-size, word-based text chunker with configurable overlap.

Generalizes the original's ``chunk_text`` (which had no overlap at all,
so retrieved chunks could cut a relevant sentence exactly at a chunk
boundary and lose it). Sizes come from a corpus's ``ChunkingConfig``,
never a hardcoded constant.
"""

from __future__ import annotations

from app.config import ChunkingConfig

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 0


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split ``text`` into word-count-bounded chunks with optional overlap.

    Args:
        text: the source text.
        chunk_size: max words per chunk. Must be positive.
        chunk_overlap: words repeated at the start of each chunk from the
            end of the previous one. Must be non-negative and < chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    stride = chunk_size - chunk_overlap
    chunks = []
    for start in range(0, len(words), stride):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def chunk_text_for_corpus(text: str, chunking_config: ChunkingConfig) -> list[str]:
    """Convenience wrapper reading sizes from a corpus's chunking config."""
    return chunk_text(
        text,
        chunk_size=chunking_config.chunk_size,
        chunk_overlap=chunking_config.chunk_overlap,
    )


def token_count(text: str) -> int:
    return len(text.split())
