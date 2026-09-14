"""LLM provider tests — HTTP is fully mocked."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.llm.base import Provider
from app.llm.echo_provider import EchoProvider
from app.llm.factory import get_llm_provider
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider


class TestOllamaProvider:
    def test_requires_host(self):
        with pytest.raises(ValueError, match="host"):
            OllamaProvider(host="", model="phi3")

    def test_generate_posts_to_api_generate_and_returns_response_field(self):
        provider = OllamaProvider(host="http://localhost:11434", model="phi3")
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {"response": "hello"}
        with patch("app.llm.ollama_provider.requests.post", return_value=fake_response) as post:
            result = provider.generate("hi")

        assert result == "hello"
        called_url = post.call_args.args[0]
        assert called_url == "http://localhost:11434/api/generate"
        assert post.call_args.kwargs["json"]["model"] == "phi3"
        assert post.call_args.kwargs["json"]["prompt"] == "hi"

    def test_strips_trailing_slash_from_host(self):
        provider = OllamaProvider(host="http://localhost:11434/", model="phi3")
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {"response": ""}
        with patch("app.llm.ollama_provider.requests.post", return_value=fake_response) as post:
            provider.generate("hi")
        assert post.call_args.args[0] == "http://localhost:11434/api/generate"

    def test_raises_on_http_error(self):
        import requests

        provider = OllamaProvider(host="http://localhost:11434", model="phi3")
        with patch(
            "app.llm.ollama_provider.requests.post",
            side_effect=requests.RequestException("down"),
        ):
            with pytest.raises(requests.RequestException):
                provider.generate("hi")

    def test_satisfies_provider_protocol(self):
        provider = OllamaProvider(host="http://x", model="phi3")
        assert isinstance(provider, Provider)

    def test_stream_yields_response_chunks_until_done(self):
        provider = OllamaProvider(host="http://localhost:11434", model="phi3")
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.iter_lines.return_value = [
            b"",
            b'{"response": "Hel", "done": false}',
            b'{"response": "lo", "done": false}',
            b'{"response": "", "done": true}',
        ]
        with patch(
            "app.llm.ollama_provider.requests.post", return_value=fake_response
        ) as post:
            chunks = list(provider.stream("hi"))

        assert chunks == ["Hel", "lo"]
        assert post.call_args.kwargs["json"]["stream"] is True
        assert post.call_args.kwargs["stream"] is True

    def test_stream_raises_on_http_error(self):
        import requests

        provider = OllamaProvider(host="http://localhost:11434", model="phi3")
        with patch(
            "app.llm.ollama_provider.requests.post",
            side_effect=requests.RequestException("down"),
        ):
            with pytest.raises(requests.RequestException):
                list(provider.stream("hi"))


class TestGroqProvider:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="api_key"):
            GroqProvider(api_key="", model="llama-3.1-8b-instant")

    def test_generate_returns_message_content(self):
        provider = GroqProvider(api_key="sk-test", model="llama-3.1-8b-instant")
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {"choices": [{"message": {"content": "hi there"}}]}
        with patch("app.llm.groq_provider.requests.post", return_value=fake_response) as post:
            result = provider.generate("hello")

        assert result == "hi there"
        assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test"
        assert post.call_args.kwargs["json"]["messages"] == [{"role": "user", "content": "hello"}]

    def test_satisfies_provider_protocol(self):
        provider = GroqProvider(api_key="sk-test", model="m")
        assert isinstance(provider, Provider)

    def test_stream_yields_delta_content_until_done_marker(self):
        provider = GroqProvider(api_key="sk-test", model="m")
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.iter_lines.return_value = [
            b"",
            b': keep-alive',
            b'data: {"choices": [{"delta": {"content": "Hi"}}]}',
            b'data: {"choices": [{"delta": {"content": " there"}}]}',
            b"data: [DONE]",
        ]
        with patch(
            "app.llm.groq_provider.requests.post", return_value=fake_response
        ) as post:
            chunks = list(provider.stream("hello"))

        assert chunks == ["Hi", " there"]
        assert post.call_args.kwargs["json"]["stream"] is True
        assert post.call_args.kwargs["stream"] is True

    def test_stream_raises_on_http_error(self):
        import requests

        provider = GroqProvider(api_key="sk-test", model="m")
        with patch(
            "app.llm.groq_provider.requests.post",
            side_effect=requests.RequestException("down"),
        ):
            with pytest.raises(requests.RequestException):
                list(provider.stream("hello"))


class TestEchoProvider:
    def test_satisfies_provider_protocol(self):
        assert isinstance(EchoProvider(), Provider)

    def test_generate_echoes_the_context_section(self):
        prompt = (
            "Persona\n\nRules:\n- x\n\nContext:\nCampusAI is free."
            "\n\nQuestion:\nWhat is it?\n\nAnswer:"
        )
        result = EchoProvider().generate(prompt)
        assert "CampusAI is free." in result

    def test_generate_handles_a_missing_context_section(self):
        result = EchoProvider().generate("no context markers here")
        assert result.strip() == "I don't have any context to answer that."

    def test_stream_yields_the_same_text_as_generate_in_pieces(self):
        prompt = "Context:\nHello world.\n\nQuestion:\nq"
        chunks = list(EchoProvider().stream(prompt))
        assert len(chunks) > 1
        assert "".join(chunks) == EchoProvider().generate(prompt)

    def test_is_deterministic_for_the_same_prompt(self):
        prompt = "Context:\nSame content.\n\nQuestion:\nq"
        assert EchoProvider().generate(prompt) == EchoProvider().generate(prompt)


class TestGetLlmProvider:
    def test_returns_groq_provider_when_configured(self):
        settings = Settings(_env_file=None, llm_provider="groq", groq_api_key="sk-test")
        provider = get_llm_provider(settings)
        assert isinstance(provider, GroqProvider)

    def test_returns_echo_provider_when_configured(self):
        settings = Settings(_env_file=None, llm_provider="echo")
        provider = get_llm_provider(settings)
        assert isinstance(provider, EchoProvider)

    def test_returns_ollama_provider_by_default(self):
        settings = Settings(_env_file=None, llm_provider="ollama")
        provider = get_llm_provider(settings)
        assert isinstance(provider, OllamaProvider)

    def test_uses_get_settings_when_none_passed(self):
        with patch("app.llm.factory.get_settings") as mock_get_settings:
            mock_get_settings.return_value = Settings(_env_file=None, llm_provider="ollama")
            provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
