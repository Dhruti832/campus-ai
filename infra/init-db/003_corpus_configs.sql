-- Corpus configs created at runtime via the admin panel's "Add website"
-- flow. The built-in example-* corpora stay as YAML files under
-- backend/config/corpora/ (versioned, reviewed in a PR); corpora added
-- through the admin UI live here instead, since Render's filesystem is
-- read-only after a deploy — a file can't be written at request time,
-- but a DB row can.
CREATE TABLE IF NOT EXISTS corpus_configs (
    name TEXT PRIMARY KEY,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
