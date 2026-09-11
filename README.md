# DocuChat

> A generic, config-driven RAG (Retrieval-Augmented Generation) chatbot: point it at a sitemap or a set of seed URLs, and chat with that content. Built with a free, self-hostable stack end to end.

[![Backend CI](https://github.com/REPLACE_ME/docuchat/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/REPLACE_ME/docuchat/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/REPLACE_ME/docuchat/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/REPLACE_ME/docuchat/actions/workflows/frontend-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Status:** 🚧 Under active development (Phase 1 MVP in progress). Live demo link and screenshots will be added here once deployed.

---

## What this is

DocuChat crawls a website (or a fixed list of pages), chunks and embeds the content, stores it in Postgres with `pgvector`, and answers natural-language questions about it using retrieval-augmented generation. The active "corpus" (what site/domain it knows about, its persona, its category rules) is entirely config-driven — swapping to a new knowledge base means pointing at a different YAML file, never editing code.

## Why this exists

This started as a rebuild of a university group project (a Dalhousie-specific chatbot) that had real, fixable issues: vector similarity search implemented as a brute-force Python loop over every row in a MySQL table (no index, no LIMIT), and domain-specific logic hardcoded into the orchestration layer instead of config. This version fixes both, generalizes the product, and uses a fully free tech stack. See [`docs/architecture.md`](docs/architecture.md) and [`docs/adr/`](docs/adr/) for the reasoning behind each decision.

## Tech stack

| Layer | Choice |
|---|---|
| Vector DB | Postgres 16 + `pgvector` (HNSW index) — Docker locally, [Neon](https://neon.tech) free tier for the demo |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`), local, free |
| LLM | [Ollama](https://ollama.com) locally, [Groq](https://groq.com) free API for the live demo |
| Backend | FastAPI |
| Frontend | Next.js + Tailwind CSS + shadcn/ui |
| Hosting | [Render](https://render.com) (backend) + [Vercel](https://vercel.com) (frontend), both free tiers |
| CI | GitHub Actions |

RAG orchestration (chunking, retrieval, prompting) is hand-rolled rather than built on LangChain/LlamaIndex — see [`docs/adr/0002-hand-rolled-vs-framework.md`](docs/adr/0002-hand-rolled-vs-framework.md) for why.

## Quickstart (local, $0)

```bash
docker compose -f infra/docker-compose.yml up --build
```

*(Full instructions land here once the ingestion/backend/frontend pieces are built — see project status above.)*

## Project structure

```
docuchat/
├── backend/     # FastAPI app: ingestion, embeddings, retrieval, LLM providers, chat agent
├── frontend/    # Next.js chat UI
├── infra/       # docker-compose + DB init scripts
├── docs/        # architecture notes and ADRs
└── scripts/     # ingestion CLI
```

## License

[MIT](LICENSE)
