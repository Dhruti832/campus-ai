"""DB-backed corpus configs — created at runtime through the admin
panel's "Add website" flow, unlike the built-in example-* corpora, which
are YAML files under config/corpora/ (versioned, reviewed in a PR).

Render's filesystem is read-only after a deploy: a file can't be written
at request time, but a database row can, so this is how a new corpus
gets created without needing a git commit + redeploy cycle.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import CORPORA_DIR, CorpusConfig, CrawlConfig, load_corpus_config
from app.db.models import CorpusConfigRow, Source

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}$")
DEFAULT_MAX_PAGES = 100
DEFAULT_RULES = [
    "If the information is not found in the context, say so plainly instead of guessing."
]


class InvalidCorpusNameError(ValueError):
    pass


def build_corpus_config_from_url(
    name: str,
    website_url: str,
    persona: str | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> CorpusConfig:
    """Turns "a name and a URL" into a full CorpusConfig with sensible
    defaults — seed-crawl from the homepage rather than requiring a
    sitemap (not every site has one, or keeps it complete), scoped to the
    same domain so it doesn't wander off onto external links."""
    if not NAME_PATTERN.match(name):
        raise InvalidCorpusNameError(
            "Corpus name must be lowercase letters, digits, and hyphens (2-49 characters)."
        )

    parsed = urlparse(website_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Not a valid website URL: {website_url!r}")

    # Matches either a path under the domain (https://x.com/foo) or the
    # bare domain root with nothing after it (https://x.com) — the crawler
    # normalizes a path-less seed URL's trailing slash away, so requiring
    # one unconditionally here would make a bare root URL reject its own
    # seed before ever fetching it.
    domain_pattern = f"^https?://{re.escape(parsed.netloc)}(/|$)"

    return CorpusConfig(
        name=name,
        description=f"Added via the admin panel from {parsed.netloc}.",
        persona=persona or (
            f"You are a helpful assistant answering questions about {parsed.netloc} "
            "using only the provided context."
        ),
        rules=list(DEFAULT_RULES),
        crawl=CrawlConfig(
            mode="seed_list",
            seed_urls=[website_url],
            allow_patterns=[domain_pattern],
            max_pages=max_pages,
            max_depth=3,
            include_files=True,
            file_extensions=[".pdf", ".docx"],
        ),
    )


def list_dynamic_corpus_names(session: Session) -> list[str]:
    return sorted(session.scalars(select(CorpusConfigRow.name)).all())


def load_dynamic_corpus_config(session: Session, name: str) -> CorpusConfig | None:
    row = session.get(CorpusConfigRow, name)
    if row is None:
        return None
    return CorpusConfig.model_validate(row.config)


def save_corpus_config(session: Session, config: CorpusConfig) -> None:
    row = session.get(CorpusConfigRow, config.name)
    if row is None:
        session.add(CorpusConfigRow(name=config.name, config=config.model_dump(mode="json")))
    else:
        row.config = config.model_dump(mode="json")
    session.commit()


def update_corpus_config(
    session: Session,
    name: str,
    *,
    website_url: str | None = None,
    persona: str | None = None,
    max_pages: int | None = None,
) -> CorpusConfig | None:
    """Partial update of an admin-created corpus's settings. Returns None
    if there's no such dynamic corpus (built-in YAML ones aren't editable
    this way, same restriction as delete_corpus_config)."""
    row = session.get(CorpusConfigRow, name)
    if row is None:
        return None

    config = CorpusConfig.model_validate(row.config)

    if website_url is not None:
        parsed = urlparse(website_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Not a valid website URL: {website_url!r}")
        config.crawl.seed_urls = [website_url]
        config.crawl.allow_patterns = [f"^https?://{re.escape(parsed.netloc)}(/|$)"]
    if persona is not None:
        config.persona = persona
    if max_pages is not None:
        config.crawl.max_pages = max_pages

    row.config = config.model_dump(mode="json")
    session.commit()
    return config


def delete_corpus_config(session: Session, name: str) -> bool:
    """Removes the config and any ingested sources/chunks for it (chunks
    cascade via Source's relationship). Returns False if there was no
    such dynamic corpus — this never touches the built-in YAML ones."""
    row = session.get(CorpusConfigRow, name)
    if row is None:
        return False
    session.execute(delete(Source).where(Source.corpus == name))
    session.delete(row)
    session.commit()
    return True


def list_all_corpus_names(session: Session) -> list[str]:
    yaml_names = {p.stem for p in CORPORA_DIR.glob("*.yaml")}
    dynamic_names = set(list_dynamic_corpus_names(session))
    return sorted(yaml_names | dynamic_names)


def load_any_corpus_config(session: Session, name: str) -> CorpusConfig:
    """Resolves a corpus config from either source — the DB first (so a
    dynamically-created corpus can reuse an example name), falling back
    to a YAML file for the built-in example-* corpora."""
    dynamic = load_dynamic_corpus_config(session, name)
    if dynamic is not None:
        return dynamic
    return load_corpus_config(name)
