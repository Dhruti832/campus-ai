"""SQLAlchemy ORM models mirroring infra/init-db/001_enable_pgvector.sql
and 002_admin_state.sql.

The ``chunks.text_search`` generated tsvector column is deliberately not
mapped here — it's written by Postgres, never by the ORM, and is only ever
read via raw SQL in ``retrieval/keyword_search.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("corpus", "url", name="uq_sources_corpus_url"),
        Index("sources_corpus_idx", "corpus"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    corpus: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(default=None)
    source_type: Mapped[str] = mapped_column(default="page")
    category: Mapped[str | None] = mapped_column(default=None)
    content_hash: Mapped[str | None] = mapped_column(default=None)
    crawled_at: Mapped[datetime] = mapped_column(server_default=func.now())

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (Index("chunks_source_id_idx", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    source: Mapped[Source] = relationship(back_populates="chunks")


class AppState(Base):
    """Single-row table (id is always 1) holding the runtime-switchable
    active corpus — see infra/init-db/002_admin_state.sql."""

    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    active_corpus: Mapped[str | None] = mapped_column(default=None)


class CorpusConfigRow(Base):
    """A corpus config created at runtime via the admin panel (see
    app/corpus_store.py) — the built-in example-* corpora stay as YAML
    files instead; see infra/init-db/003_corpus_configs.sql."""

    __tablename__ = "corpus_configs"

    name: Mapped[str] = mapped_column(primary_key=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Feedback(Base):
    """A thumbs up/down on one answer — see infra/init-db/004_feedback.sql.
    query/answer are stored alongside the rating (not just a message id)
    since the server never persists conversation state; the frontend is
    the only place that association exists."""

    __tablename__ = "feedback"
    __table_args__ = (Index("feedback_corpus_idx", "corpus"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    corpus: Mapped[str] = mapped_column(nullable=False)
    query: Mapped[str] = mapped_column(nullable=False)
    answer: Mapped[str] = mapped_column(nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
