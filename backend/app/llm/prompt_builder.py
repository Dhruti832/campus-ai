"""Prompt assembly — persona and rules come entirely from the active
corpus config. The original hardcoded "You are a Dalhousie University
assistant." and a fixed rules list directly in this file; here the
function has no idea what institution or domain it's serving."""

from __future__ import annotations

from app.config import CorpusConfig

NO_CONTEXT_INSTRUCTION = (
    "If the information is not found in the context, say so plainly "
    "instead of guessing."
)


def build_prompt(query: str, context_chunks: list[str], corpus_config: CorpusConfig) -> str:
    context_text = "\n\n".join(context_chunks)

    rules = list(corpus_config.rules) or [NO_CONTEXT_INSTRUCTION]
    rules_section = "Rules:\n" + "\n".join(f"- {rule}" for rule in rules)

    context_section = f"Context:\n{context_text}"
    question_section = f"Question:\n{query}"

    return "\n\n".join(
        [corpus_config.persona.strip(), rules_section, context_section, question_section, "Answer:"]
    )
