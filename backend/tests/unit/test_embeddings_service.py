"""Embeddings service tests — sentence-transformers itself is mocked out
so these run fast and offline (no model download)."""

import sys
import types
from unittest.mock import MagicMock, patch

import app.embeddings.service as service


def setup_function(_fn):
    service._local_model = None
    service._local_model_name = None


def teardown_function(_fn):
    service._local_model = None
    service._local_model_name = None


class TestGetEmbedding:
    def test_empty_text_returns_none(self):
        assert service.get_embedding("") is None
        assert service.get_embedding("   ") is None

    def test_returns_vector_from_model_encode(self):
        fake_model = MagicMock()
        fake_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        with patch.object(service, "_get_local_model", return_value=fake_model):
            vec = service.get_embedding("hello world")
        assert vec == [0.1, 0.2, 0.3]

    def test_truncates_and_cleans_text_before_encoding(self):
        fake_model = MagicMock()
        fake_model.encode.return_value = MagicMock(tolist=lambda: [0.0])
        long_text = "a\nb " * 5000
        with patch.object(service, "_get_local_model", return_value=fake_model):
            service.get_embedding(long_text)
        encoded_arg = fake_model.encode.call_args[0][0]
        assert "\n" not in encoded_arg
        assert len(encoded_arg) <= service.MAX_EMBEDDING_TEXT_CHARS

    def test_returns_none_when_model_raises(self):
        with patch.object(service, "_get_local_model", side_effect=RuntimeError("boom")):
            assert service.get_embedding("hello") is None


class TestGetLocalModel:
    def test_lazy_loads_and_caches(self):
        fake_st_module = types.ModuleType("sentence_transformers")
        fake_cls = MagicMock(return_value="model-instance")
        fake_st_module.SentenceTransformer = fake_cls

        with patch.dict(sys.modules, {"sentence_transformers": fake_st_module}):
            first = service.get_local_model()
            second = service.get_local_model()

        assert first == "model-instance"
        assert second == "model-instance"
        fake_cls.assert_called_once()

    def test_reloads_when_configured_model_name_changes(self):
        fake_st_module = types.ModuleType("sentence_transformers")
        fake_cls = MagicMock(side_effect=lambda name: f"model:{name}")
        fake_st_module.SentenceTransformer = fake_cls

        with patch.dict(sys.modules, {"sentence_transformers": fake_st_module}):
            settings_a = MagicMock(embedding_model="model-a")
            settings_b = MagicMock(embedding_model="model-b")
            with patch.object(service, "get_settings", side_effect=[settings_a, settings_b]):
                first = service.get_local_model()
                second = service.get_local_model()

        assert first == "model:model-a"
        assert second == "model:model-b"
        assert fake_cls.call_count == 2


class TestEmbeddingsAvailable:
    def test_true_when_importable(self):
        fake_st_module = types.ModuleType("sentence_transformers")
        fake_st_module.SentenceTransformer = MagicMock()
        with patch.dict(sys.modules, {"sentence_transformers": fake_st_module}):
            assert service.embeddings_available() is True

    def test_false_when_not_importable(self):
        broken_module = types.ModuleType("sentence_transformers")
        with patch.dict(sys.modules, {"sentence_transformers": broken_module}):
            assert service.embeddings_available() is False
