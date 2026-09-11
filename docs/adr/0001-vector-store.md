# ADR 0001: Postgres + pgvector for vector storage

## Status
Accepted

## Context
An earlier version of this project (a course assignment) stored embeddings as JSON-encoded text in a MySQL `TEXT` column, with no vector index. Every similarity search fetched *every* row with an embedding out of the database and computed cosine similarity in a Python loop — an O(n) linear scan with no LIMIT on the query. This works at a few thousand rows and falls over as the corpus grows.

## Decision
Use Postgres with the `pgvector` extension. Store embeddings as a native `vector(384)` column, build an HNSW index (`vector_cosine_ops`), and let Postgres do the nearest-neighbor search via `ORDER BY embedding <=> :query LIMIT :k`. Locally this runs in Docker; for the public demo, [Neon](https://neon.tech)'s free tier provides managed Postgres with pgvector support and auto-resumes on connection after idling (unlike some alternatives that require a manual restore after a period of inactivity).

## Consequences
- Similarity search is pushed into the database and uses a real index instead of application-code linear scan.
- One database serves both relational metadata (pages, chunks, sessions) and vector search — no second system to run.
- Corpus size on the free Neon tier is capped at 0.5GB, which bounds how large the demo corpus can be; this is acceptable for a portfolio demo and documented in the ingestion config.
