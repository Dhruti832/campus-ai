# ADR 0002: Hand-rolled RAG orchestration instead of LangChain/LlamaIndex

## Status
Accepted

## Context
Frameworks like LangChain and LlamaIndex can assemble a RAG pipeline (chunking, retrieval, prompting) quickly, but they also abstract away the exact mechanics of how a query becomes an answer — which is the part worth demonstrating in a portfolio/interview context.

## Decision
Implement chunking, embedding, retrieval, prompt construction, and the retrieval-then-generate orchestration directly, with no RAG framework dependency. Each stage (`ingestion`, `embeddings`, `retrieval`, `llm`, `agent`) is a small, independently testable module with a narrow interface.

## Consequences
- The codebase is a legible, walkable demonstration of how RAG actually works: chunk sizing/overlap, embedding generation, vector + keyword fallback search, context assembly, prompt construction, and graceful degradation are all visible and testable in application code, not hidden in a framework.
- Some functionality a framework provides for free (e.g. document loaders for many file formats, agentic tool-calling) has to be built manually if needed later; this is an acceptable tradeoff for a project scoped around a single content type (crawled web pages + PDFs) rather than broad format support.
