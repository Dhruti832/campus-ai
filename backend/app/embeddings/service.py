"""Embedding client. Near-copy of the original's lazy-load pattern for
sentence-transformers, generalized to read the model name from Settings
instead of a hardcoded constant.
"""

from __future__ import annotations

import logging

from app.config import get_settings

MAX_EMBEDDING_TEXT_CHARS = 8000

_local_model = None
_local_model_name: str | None = None
logger = logging.getLogger(__name__)


def _get_local_model():
    """Lazy-load the sentence-transformers model named in Settings."""
    global _local_model, _local_model_name
    model_name = get_settings().embedding_model
    if _local_model is None or _local_model_name != model_name:
        from sentence_transformers import SentenceTransformer

        _local_model = SentenceTransformer(model_name)
        _local_model_name = model_name
    return _local_model


def get_local_model():
    """Public accessor for the local model (used in tests)."""
    return _get_local_model()


def get_embedding(text: str) -> list[float] | None:
    """Return an embedding vector for text using local sentence-transformers."""
    if not text or not text.strip():
        return None
    text_clean = text.replace("\n", " ").strip()[:MAX_EMBEDDING_TEXT_CHARS]
    try:
        model = _get_local_model()
        vec = model.encode(text_clean)
        return vec.tolist()
    except Exception as exc:
        logger.debug("Embedding generation failed: %s", exc)
        return None


def embeddings_available() -> bool:
    """True if sentence-transformers can be used."""
    try:
        from sentence_transformers import SentenceTransformer as _SentenceTransformer

        _ = _SentenceTransformer
        return True
    except ImportError as exc:
        logger.debug("sentence-transformers unavailable: %s", exc)
        return False
