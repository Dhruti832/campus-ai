#!/usr/bin/env python
"""CLI entry point: crawl, chunk, embed, and store one corpus.

Usage:
    python scripts/ingest.py --corpus example-docs

The actual pipeline logic lives in backend/app/ingestion/ingest_service.py
(covered by the backend's test suite) — this script is just an argparse
wrapper that puts backend/ on sys.path and wires up a DB session.
"""

import argparse
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import get_session_factory  # noqa: E402
from app.ingestion.ingest_service import ingest_corpus  # noqa: E402

logger = logging.getLogger("ingest")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Ingest a corpus into Postgres")
    parser.add_argument(
        "--corpus",
        required=True,
        help="Corpus config name (backend/config/corpora/<name>.yaml, no extension)",
    )
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        logger.info("Ingesting corpus '%s'...", args.corpus)
        result = ingest_corpus(args.corpus, session)
        logger.info(
            "Done: %d sources, %d chunks ingested for corpus '%s'",
            result.sources_ingested,
            result.chunks_ingested,
            args.corpus,
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
