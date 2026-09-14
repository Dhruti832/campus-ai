# End-to-end tests

Playwright tests that drive the real frontend against a real backend and a
real Postgres database — the only thing faked is the LLM call itself
(`LLM_PROVIDER=echo`, see `backend/app/llm/echo_provider.py`), since a real
Ollama or Groq call would be slow, non-deterministic, or need a paid key.
Retrieval (embeddings + pgvector + keyword search) all run for real against
a couple of fixture chunks seeded by `scripts/seed_e2e_fixture.py`.

This is a separate package from `frontend/` (different test runner,
different dependencies) and from `backend/` (no Python here) — see
`.github/workflows/e2e-ci.yml` for how CI wires the two together.

## Running locally

1. Start Postgres and apply the schema (from the repo root):

   ```
   docker compose -f infra/docker-compose.yml up -d postgres
   for f in infra/init-db/*.sql; do
     PGPASSWORD=unichat psql -h localhost -U unichat -d unichat -f "$f"
   done
   ```

2. Seed the fixture corpus:

   ```
   cd backend && pip install -r requirements-dev.txt
   DATABASE_URL=postgresql+psycopg://unichat:unichat@localhost:5432/unichat \
     python ../scripts/seed_e2e_fixture.py
   ```

3. Start the backend with the deterministic echo provider and a known admin key:

   ```
   cd backend
   DATABASE_URL=postgresql+psycopg://unichat:unichat@localhost:5432/unichat \
   ACTIVE_CORPUS=example-docs \
   LLM_PROVIDER=echo \
   ADMIN_API_KEY=e2e-admin-key \
   CORS_ORIGINS=http://localhost:3000 \
   uvicorn app.main:app --port 8000
   ```

4. Build and start the frontend against it:

   ```
   cd frontend
   NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build
   NEXT_PUBLIC_API_URL=http://localhost:8000 npm run start
   ```

5. Run the tests:

   ```
   cd e2e
   npm install
   npx playwright install --with-deps chromium
   npm test
   ```

`E2E_BASE_URL` (default `http://localhost:3000`) and `E2E_ADMIN_KEY`
(default `e2e-admin-key`) can be overridden if you're pointing at different
ports or a different admin key.
