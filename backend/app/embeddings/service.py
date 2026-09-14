"""Embedding client — bare onnxruntime + tokenizers, no torch/sentence-
transformers.

sentence-transformers unconditionally imports torch regardless of its own
"backend" setting, which costs ~370MB of RSS just to import, before a
model or a request is involved — right at the edge of (and sometimes over)
Render's 512MB free-tier limit. This hand-rolled tokenize -> ONNX forward
pass -> mean-pool -> L2-normalize pipeline produces embeddings that are
mathematically identical to sentence-transformers' for the same model
(verified directly: cosine similarity 1.0 against all-MiniLM-L6-v2 for
several test sentences) at roughly half the peak memory (measured: ~431MB
vs ~197MB for one encode call, same machine). See the free-tier memory
constraint note in README.md for the full before/after.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np
import requests

from app.config import get_settings

MAX_EMBEDDING_TEXT_CHARS = 8000
MAX_SEQUENCE_LENGTH = 256

# Baked into the Docker image at build time (see Dockerfile) so a cold
# start never needs a network round-trip to Hugging Face. This is also the
# local-dev cache location when running outside Docker — populated lazily
# on first use, then reused.
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
HF_MODEL_BASE_URL = "https://huggingface.co/sentence-transformers/{model}/resolve/main"

_session: Any = None
_tokenizer: Any = None
_loaded_model_name: str | None = None
_load_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _download(url: str, dest: Path) -> None:
    response = requests.get(url, timeout=120, stream=True)
    response.raise_for_status()
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    tmp.replace(dest)


def _ensure_model_files(model_name: str) -> Path:
    """Returns the directory containing model.onnx + tokenizer.json for
    model_name, downloading them from Hugging Face first if missing."""
    directory = DEFAULT_MODEL_DIR / model_name
    model_path = directory / "model.onnx"
    tokenizer_path = directory / "tokenizer.json"
    if model_path.exists() and tokenizer_path.exists():
        return directory

    directory.mkdir(parents=True, exist_ok=True)
    base_url = HF_MODEL_BASE_URL.format(model=model_name)
    logger.info("Downloading ONNX embedding model '%s' (first run only)...", model_name)
    _download(f"{base_url}/onnx/model.onnx", model_path)
    _download(f"{base_url}/tokenizer.json", tokenizer_path)
    return directory


def _get_local_model() -> tuple[Any, Any]:
    """Lazy-load the ONNX session + tokenizer named in Settings.

    FastAPI runs sync routes in a thread pool, so concurrent requests
    arriving while the model is still loading could each trigger their
    own redundant InferenceSession construction without this lock —
    doubling (or worse) peak memory right when it's already at its
    highest, which is exactly what OOM-killed this service on a 512MB
    Render instance under concurrent load.
    """
    global _session, _tokenizer, _loaded_model_name
    model_name = get_settings().embedding_model
    if _session is not None and _loaded_model_name == model_name:
        return _session, _tokenizer

    with _load_lock:
        if _session is None or _loaded_model_name != model_name:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            directory = _ensure_model_files(model_name)
            tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
            tokenizer.enable_truncation(max_length=MAX_SEQUENCE_LENGTH)
            session = ort.InferenceSession(
                str(directory / "model.onnx"), providers=["CPUExecutionProvider"]
            )
            _session, _tokenizer, _loaded_model_name = session, tokenizer, model_name
    return _session, _tokenizer


def get_local_model() -> tuple[Any, Any]:
    """Public accessor for the (session, tokenizer) pair (used in tests)."""
    return _get_local_model()


def _mean_pool_and_normalize(
    last_hidden_state: np.ndarray, attention_mask: np.ndarray
) -> np.ndarray:
    """Sentence-transformers' pooling for all-MiniLM-L6-v2: mean over
    non-padding token embeddings, then L2-normalize. The bare ONNX export
    only gives per-token embeddings (last_hidden_state) — this step isn't
    baked into the graph, so it has to happen here."""
    mask = attention_mask[..., None].astype(np.float32)
    summed = (last_hidden_state * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
    pooled = summed / counts
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    return pooled / np.clip(norms, a_min=1e-9, a_max=None)


def get_embedding(text: str) -> list[float] | None:
    """Return an embedding vector for text using the local ONNX model."""
    if not text or not text.strip():
        return None
    text_clean = text.replace("\n", " ").strip()[:MAX_EMBEDDING_TEXT_CHARS]
    try:
        session, tokenizer = _get_local_model()
        encoding = tokenizer.encode(text_clean)
        input_ids = np.array([encoding.ids], dtype=np.int64)
        attention_mask = np.array([encoding.attention_mask], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)
        (last_hidden_state,) = session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )
        vec = _mean_pool_and_normalize(last_hidden_state, attention_mask)
        return vec[0].tolist()
    except Exception as exc:
        logger.debug("Embedding generation failed: %s", exc)
        return None


def embeddings_available() -> bool:
    """True if onnxruntime can be used."""
    try:
        import onnxruntime as _onnxruntime

        _ = _onnxruntime
        return True
    except ImportError as exc:
        logger.debug("onnxruntime unavailable: %s", exc)
        return False
