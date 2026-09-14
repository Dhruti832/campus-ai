-- Enables pgvector and creates the core schema for UniChat.
-- Applied automatically by the postgres container on first startup
-- (mounted into /docker-entrypoint-initdb.d/).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    corpus TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    source_type TEXT NOT NULL DEFAULT 'page',
    category TEXT,
    content_hash TEXT,
    crawled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (corpus, url)
);

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),
    text_search tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW ANN index for cosine similarity search. Replaces the
-- fetch-everything-and-loop-in-Python anti-pattern this project fixes:
-- see docs/adr/0001-vector-store.md.
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_text_search_idx
    ON chunks USING gin (text_search);

CREATE INDEX IF NOT EXISTS chunks_source_id_idx ON chunks (source_id);
CREATE INDEX IF NOT EXISTS sources_corpus_idx ON sources (corpus);
