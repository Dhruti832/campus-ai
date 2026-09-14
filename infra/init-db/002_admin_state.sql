-- Single-row table holding the runtime-switchable active corpus.
-- Separate from the ACTIVE_CORPUS env var (which stays the fallback
-- default): the admin panel can flip this without a redeploy, and it
-- survives Render's free-tier restarts (unlike an in-memory override).

CREATE TABLE IF NOT EXISTS app_state (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    active_corpus TEXT,
    CONSTRAINT app_state_singleton CHECK (id = 1)
);
