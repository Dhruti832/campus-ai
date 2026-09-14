#!/usr/bin/env python
"""Seeds a tiny, deterministic set of sources/chunks for the Playwright
E2E suite — see e2e/README.md.

Real crawling (scripts/ingest.py) hits a live third-party site, which is
slow and flaky in CI. This inserts a couple of hand-written chunks
directly under the "example-docs" corpus with real embeddings (the actual
ONNX pipeline, so retrieval is genuinely exercised), skipping the crawl
step entirely. Paired with LLM_PROVIDER=echo (app/llm/echo_provider.py),
the whole chat pipeline runs for real except the model call itself, which
would otherwise be too slow/costly/flaky for CI.

Usage:
    python scripts/seed_e2e_fixture.py
"""

import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.models import Chunk, Source  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.embeddings.service import get_embedding  # noqa: E402

logger = logging.getLogger("seed_e2e_fixture")

CORPUS = "example-docs"

FIXTURE_PAGES = [
    (
        "https://fastapi.tiangolo.com/e2e-fixture/getting-started",
        "Getting Started",
        "Getting Started",
        "CampusAI lets you chat with any website's documentation. Pick a "
        "corpus from the admin panel, then ask a question in the chat window "
        "to get started.",
    ),
    (
        "https://fastapi.tiangolo.com/e2e-fixture/pricing",
        "Pricing",
        "General",
        "CampusAI is free and open source. There is no subscription fee "
        "to use the chatbot.",
    ),
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    session = get_session_factory()()
    try:
        for url, title, category, text in FIXTURE_PAGES:
            source = Source(corpus=CORPUS, url=url, title=title, category=category)
            session.add(source)
            session.flush()
            session.add(
                Chunk(
                    source_id=source.id,
                    chunk_index=0,
                    chunk_text=text,
                    embedding=get_embedding(text),
                )
            )
            logger.info("Seeded fixture chunk for %s", url)
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
