"""Embeddings service tests — onnxruntime/tokenizers are mocked out so
these run fast and offline (no model download). Correctness of the actual
tokenize -> ONNX -> pool -> normalize pipeline against real model weights
is verified separately (cosine similarity 1.0 against sentence-
transformers for the same model, see the ONNX rewrite's commit message);
these tests cover the plumbing around it — lazy load, caching, the
concurrent-load lock, and get_embedding's text handling."""

import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import requests

import app.embeddings.service as service


def setup_function(_fn):
    service._session = None
    service._tokenizer = None
    service._loaded_model_name = None


def teardown_function(_fn):
    service._session = None
    service._tokenizer = None
    service._loaded_model_name = None


def _fake_pair(seq_len: int = 3, dim: int = 4):
    """A (session, tokenizer) pair whose encode -> pool -> normalize
    output is a unit vector (identical per-token embeddings mean-pool to
    themselves, then L2-normalize)."""
    tokenizer = MagicMock()
    tokenizer.encode.return_value = MagicMock(ids=[1] * seq_len, attention_mask=[1] * seq_len)
    session = MagicMock()
    token_embeddings = np.ones((1, seq_len, dim), dtype=np.float32)
    session.run.return_value = (token_embeddings,)
    return session, tokenizer


class TestGetEmbedding:
    def test_empty_text_returns_none(self):
        assert service.get_embedding("") is None
        assert service.get_embedding("   ") is None

    def test_returns_a_normalized_vector(self):
        session, tokenizer = _fake_pair(dim=4)
        with patch.object(service, "_get_local_model", return_value=(session, tokenizer)):
            vec = service.get_embedding("hello world")

        assert vec is not None
        assert len(vec) == 4
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-5

    def test_truncates_and_cleans_text_before_encoding(self):
        session, tokenizer = _fake_pair()
        long_text = "a\nb " * 5000
        with patch.object(service, "_get_local_model", return_value=(session, tokenizer)):
            service.get_embedding(long_text)

        encoded_arg = tokenizer.encode.call_args[0][0]
        assert "\n" not in encoded_arg
        assert len(encoded_arg) <= service.MAX_EMBEDDING_TEXT_CHARS

    def test_returns_none_when_model_raises(self):
        with patch.object(service, "_get_local_model", side_effect=RuntimeError("boom")):
            assert service.get_embedding("hello") is None

    def test_returns_none_when_session_run_raises(self):
        session, tokenizer = _fake_pair()
        session.run.side_effect = RuntimeError("inference failed")
        with patch.object(service, "_get_local_model", return_value=(session, tokenizer)):
            assert service.get_embedding("hello") is None


class TestGetLocalModel:
    def test_lazy_loads_and_caches(self):
        fake_ort = types.ModuleType("onnxruntime")
        fake_session_cls = MagicMock(return_value="session-instance")
        fake_ort.InferenceSession = fake_session_cls

        fake_tokenizers = types.ModuleType("tokenizers")
        fake_tokenizer_instance = MagicMock()
        fake_tokenizer_cls = MagicMock()
        fake_tokenizer_cls.from_file.return_value = fake_tokenizer_instance
        fake_tokenizers.Tokenizer = fake_tokenizer_cls

        with (
            patch.dict(sys.modules, {"onnxruntime": fake_ort, "tokenizers": fake_tokenizers}),
            patch.object(service, "_ensure_model_files", return_value=Path("/fake/dir")),
        ):
            first = service.get_local_model()
            second = service.get_local_model()

        assert first == second == ("session-instance", fake_tokenizer_instance)
        fake_session_cls.assert_called_once()
        fake_tokenizer_cls.from_file.assert_called_once()

    def test_reloads_when_configured_model_name_changes(self):
        fake_ort = types.ModuleType("onnxruntime")
        fake_session_cls = MagicMock(side_effect=lambda path, providers: f"session:{path}")
        fake_ort.InferenceSession = fake_session_cls

        fake_tokenizers = types.ModuleType("tokenizers")
        fake_tokenizer_cls = MagicMock()
        fake_tokenizer_cls.from_file.return_value = MagicMock()
        fake_tokenizers.Tokenizer = fake_tokenizer_cls

        with (
            patch.dict(sys.modules, {"onnxruntime": fake_ort, "tokenizers": fake_tokenizers}),
            patch.object(
                service, "_ensure_model_files", side_effect=[Path("/fake/a"), Path("/fake/b")]
            ),
        ):
            settings_a = MagicMock(embedding_model="model-a")
            settings_b = MagicMock(embedding_model="model-b")
            with patch.object(service, "get_settings", side_effect=[settings_a, settings_b]):
                first = service.get_local_model()
                second = service.get_local_model()

        assert first != second
        assert fake_session_cls.call_count == 2

    def test_concurrent_calls_construct_the_session_only_once(self):
        """Regression test: concurrent /chat requests arriving while the
        model is still loading must not each trigger their own
        InferenceSession() construction — that's what OOM-killed the
        service under load on a memory-constrained deployment."""

        def slow_constructor(path, providers):
            time.sleep(0.05)
            return "session-instance"

        fake_ort = types.ModuleType("onnxruntime")
        fake_session_cls = MagicMock(side_effect=slow_constructor)
        fake_ort.InferenceSession = fake_session_cls

        fake_tokenizer_instance = MagicMock()
        fake_tokenizers = types.ModuleType("tokenizers")
        fake_tokenizer_cls = MagicMock()
        fake_tokenizer_cls.from_file.return_value = fake_tokenizer_instance
        fake_tokenizers.Tokenizer = fake_tokenizer_cls

        results = []
        with (
            patch.dict(sys.modules, {"onnxruntime": fake_ort, "tokenizers": fake_tokenizers}),
            patch.object(service, "_ensure_model_files", return_value=Path("/fake/dir")),
        ):
            threads = [
                threading.Thread(target=lambda: results.append(service.get_local_model()))
                for _ in range(10)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert fake_session_cls.call_count == 1
        assert results == [("session-instance", fake_tokenizer_instance)] * 10


class TestEnsureModelFiles:
    def test_skips_download_when_files_already_exist(self, tmp_path):
        model_dir = tmp_path / "my-model"
        model_dir.mkdir(parents=True)
        (model_dir / "model.onnx").write_bytes(b"x")
        (model_dir / "tokenizer.json").write_text("{}")

        with (
            patch.object(service, "DEFAULT_MODEL_DIR", tmp_path),
            patch.object(service, "_download") as mock_download,
        ):
            result = service._ensure_model_files("my-model")

        assert result == model_dir
        mock_download.assert_not_called()

    def test_downloads_both_files_when_missing(self, tmp_path):
        with (
            patch.object(service, "DEFAULT_MODEL_DIR", tmp_path),
            patch.object(service, "_download") as mock_download,
        ):
            result = service._ensure_model_files("my-model")

        assert result == tmp_path / "my-model"
        assert mock_download.call_count == 2
        urls = [call.args[0] for call in mock_download.call_args_list]
        assert any(url.endswith("onnx/model.onnx") for url in urls)
        assert any(url.endswith("tokenizer.json") for url in urls)

    def test_downloads_again_if_only_one_file_is_present(self, tmp_path):
        model_dir = tmp_path / "my-model"
        model_dir.mkdir(parents=True)
        (model_dir / "model.onnx").write_bytes(b"x")
        # tokenizer.json missing

        with (
            patch.object(service, "DEFAULT_MODEL_DIR", tmp_path),
            patch.object(service, "_download") as mock_download,
        ):
            service._ensure_model_files("my-model")

        assert mock_download.call_count == 2


class TestDownload:
    def test_streams_response_to_dest_via_a_temp_file(self, tmp_path):
        dest = tmp_path / "model.onnx"
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.iter_content.return_value = [b"chunk-one-", b"chunk-two"]

        with patch.object(service.requests, "get", return_value=fake_response) as mock_get:
            service._download("https://example.com/model.onnx", dest)

        mock_get.assert_called_once_with(
            "https://example.com/model.onnx", timeout=120, stream=True
        )
        assert dest.read_bytes() == b"chunk-one-chunk-two"
        assert not dest.with_suffix(dest.suffix + ".part").exists()

    def test_raises_on_http_error(self, tmp_path):
        fake_response = MagicMock()
        fake_response.raise_for_status.side_effect = requests.HTTPError("404")

        with patch.object(service.requests, "get", return_value=fake_response):
            with pytest.raises(requests.HTTPError):
                service._download("https://example.com/model.onnx", tmp_path / "model.onnx")


class TestEmbeddingsAvailable:
    def test_true_when_importable(self):
        fake_ort = types.ModuleType("onnxruntime")
        with patch.dict(sys.modules, {"onnxruntime": fake_ort}):
            assert service.embeddings_available() is True

    def test_false_when_not_importable(self):
        with patch.dict(sys.modules, {"onnxruntime": None}):
            assert service.embeddings_available() is False
