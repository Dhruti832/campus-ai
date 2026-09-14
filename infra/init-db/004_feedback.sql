CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    corpus TEXT NOT NULL,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS feedback_corpus_idx ON feedback (corpus);
