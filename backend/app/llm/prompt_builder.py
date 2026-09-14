"""Prompt assembly — persona and rules come entirely from the active
corpus config. The original hardcoded "You are a Dalhousie University
assistant." and a fixed rules list directly in this file; here the
function has no idea what institution or domain it's serving."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import CorpusConfig

NO_CONTEXT_INSTRUCTION = (
    "If the information is not found in the context, say so plainly "
    "instead of guessing."
)

# Bounds prompt size (and LLM cost/latency) regardless of how much history a
# caller sends — enforced here, the one place every caller's prompt is built,
# rather than trusted to be pre-trimmed by the API request or the frontend.
MAX_HISTORY_TURNS = 6


@dataclass
class HistoryTurn:
    """One prior message in the conversation, for follow-up questions like
    "what about X" that only make sense with the preceding turns. Retrieval
    itself still runs on the raw current query only — history feeds the
    prompt, not the search."""

    role: str
    text: str


def build_prompt(
    query: str,
    context_chunks: list[str],
    corpus_config: CorpusConfig,
    history: list[HistoryTurn] | None = None,
) -> str:
    context_text = "\n\n".join(context_chunks)

    rules = list(corpus_config.rules) or [NO_CONTEXT_INSTRUCTION]
    rules_section = "Rules:\n" + "\n".join(f"- {rule}" for rule in rules)

    sections = [corpus_config.persona.strip(), rules_section, f"Context:\n{context_text}"]

    if history:
        trimmed = history[-MAX_HISTORY_TURNS:]
        history_text = "\n".join(f"{turn.role.capitalize()}: {turn.text}" for turn in trimmed)
        sections.append(f"Conversation so far:\n{history_text}")

    sections.append(f"Question:\n{query}")
    sections.append("Answer:")

    return "\n\n".join(sections)
