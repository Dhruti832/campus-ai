# ADR 0003: Monorepo layout

## Status
Accepted

## Context
This is a solo project with a tightly coupled frontend (Next.js chat UI) and backend (FastAPI RAG service) that will always be versioned and deployed together for a given demo.

## Decision
Keep `backend/`, `frontend/`, `infra/`, `docs/`, and `scripts/` in a single repository with independent CI workflows per side (`backend-ci.yml`, `frontend-ci.yml`).

## Consequences
- One clone, one `docker compose up` gets the whole stack running locally.
- One README, one issue tracker, one place to link from a resume/portfolio.
- CI workflows use `working-directory` scoping so backend and frontend are linted/tested independently despite living in one repo.
