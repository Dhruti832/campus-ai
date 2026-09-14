from app.config import CorpusConfig
from app.llm.prompt_builder import MAX_HISTORY_TURNS, HistoryTurn, build_prompt


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

    def test_omits_conversation_section_when_no_history(self):
        config = CorpusConfig(name="c", persona="p")
        prompt = build_prompt("q", ["ctx"], config, history=None)
        assert "Conversation so far" not in prompt

    def test_omits_conversation_section_for_empty_history(self):
        config = CorpusConfig(name="c", persona="p")
        prompt = build_prompt("q", ["ctx"], config, history=[])
        assert "Conversation so far" not in prompt

    def test_includes_prior_turns_when_history_given(self):
        config = CorpusConfig(name="c", persona="p")
        history = [
            HistoryTurn(role="user", text="What is FastAPI?"),
            HistoryTurn(role="assistant", text="A Python web framework."),
        ]
        prompt = build_prompt("What about performance?", ["ctx"], config, history=history)
        assert "Conversation so far:" in prompt
        assert "User: What is FastAPI?" in prompt
        assert "Assistant: A Python web framework." in prompt
        # History section must come before the current question.
        assert prompt.index("Conversation so far") < prompt.index("What about performance?")

    def test_trims_history_to_the_most_recent_turns(self):
        config = CorpusConfig(name="c", persona="p")
        history = [HistoryTurn(role="user", text=f"turn {i}") for i in range(MAX_HISTORY_TURNS + 4)]
        prompt = build_prompt("q", ["ctx"], config, history=history)
        assert "turn 0" not in prompt
        assert f"turn {MAX_HISTORY_TURNS + 3}" in prompt
