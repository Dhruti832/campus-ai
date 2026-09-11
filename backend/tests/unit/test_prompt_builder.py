from app.config import CorpusConfig
from app.llm.prompt_builder import build_prompt


class TestBuildPrompt:
    def test_includes_corpus_persona_verbatim(self):
        config = CorpusConfig(name="c", persona="You are a helpful docs assistant.")
        prompt = build_prompt("What is X?", ["some context"], config)
        assert "You are a helpful docs assistant." in prompt

    def test_includes_corpus_specific_rules(self):
        config = CorpusConfig(name="c", persona="p", rules=["Only use bullet points."])
        prompt = build_prompt("q", ["ctx"], config)
        assert "- Only use bullet points." in prompt

    def test_uses_fallback_rule_when_corpus_has_none(self):
        config = CorpusConfig(name="c", persona="p", rules=[])
        prompt = build_prompt("q", ["ctx"], config)
        assert "not found in the context" in prompt

    def test_includes_context_and_question(self):
        config = CorpusConfig(name="c", persona="p")
        prompt = build_prompt("What are the fees?", ["Fees are due in September."], config)
        assert "Fees are due in September." in prompt
        assert "What are the fees?" in prompt
        assert prompt.endswith("Answer:")

    def test_joins_multiple_context_chunks(self):
        config = CorpusConfig(name="c", persona="p")
        prompt = build_prompt("q", ["chunk one", "chunk two"], config)
        assert "chunk one" in prompt
        assert "chunk two" in prompt

    def test_no_two_corpora_produce_the_same_prompt(self):
        """Proves genericness: different corpus configs yield visibly
        different prompts with zero code changes."""
        university = CorpusConfig(name="u", persona="You are a university assistant.")
        docs = CorpusConfig(name="d", persona="You are a FastAPI docs assistant.")
        p1 = build_prompt("q", ["ctx"], university)
        p2 = build_prompt("q", ["ctx"], docs)
        assert p1 != p2
