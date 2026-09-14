#!/usr/bin/env python
"""Retrieval quality eval: runs a labeled query set through the real
search() pipeline (the exact code /chat uses, not a reimplementation) and
reports precision@k, recall@k, hit rate, and MRR.

Usage:
    python scripts/eval_retrieval.py --corpus example-docs
    python scripts/eval_retrieval.py --corpus example-docs --top-k 3
    python scripts/eval_retrieval.py --corpus example-docs --output docs/eval_results.md

The dataset lives at backend/eval/<corpus>.yaml — a hand-labeled list of
{query, relevant_urls} pairs checked against what's actually ingested (see
that file's header for how to regenerate it if the crawl scope changes).

Deliberately hand-rolled rather than pulling in a package like ranx or
ir_measures: precision/recall/MRR over a handful of queries is a few lines
of Python, matching this project's hand-rolled-over-framework stance (see
docs/adr/0002-hand-rolled-vs-framework.md). It also doubles as a regression
check before/after retrieval changes — e.g. run it before and after
swapping the embeddings backend to prove retrieval quality didn't regress.
"""

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import load_corpus_config  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.retrieval.search_service import search  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent.parent / "backend" / "eval"


@dataclass
class QueryResult:
    query: str
    relevant_urls: set[str]
    retrieved_urls: list[str]  # deduped by URL, ranked
    top_k: int

    @property
    def hits(self) -> int:
        return sum(1 for url in self.retrieved_urls if url in self.relevant_urls)

    @property
    def precision(self) -> float:
        """Precision@k — against the requested k, not just what came back,
        so a query that returns fewer than k results doesn't get an
        artificially inflated score."""
        return self.hits / self.top_k

    @property
    def recall(self) -> float:
        if not self.relevant_urls:
            return 0.0
        return self.hits / len(self.relevant_urls)

    @property
    def reciprocal_rank(self) -> float:
        for rank, url in enumerate(self.retrieved_urls, start=1):
            if url in self.relevant_urls:
                return 1 / rank
        return 0.0

    @property
    def hit(self) -> bool:
        return self.hits > 0


def load_dataset(corpus: str) -> list[dict]:
    path = EVAL_DIR / f"{corpus}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No eval dataset at {path}. Create one — see backend/eval/example-docs.yaml "
            "for the format."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    queries = raw.get("queries")
    if not queries:
        raise ValueError(f"{path} has no 'queries' list")
    return queries


def run_eval(corpus: str, top_k: int) -> list[QueryResult]:
    corpus_config = load_corpus_config(corpus)
    dataset = load_dataset(corpus)
    session = get_session_factory()()

    results = []
    try:
        for item in dataset:
            search_results = search(session, corpus_config, item["query"], top_k=top_k)
            # De-dupe by URL, preserving rank order — chat_engine's own
            # format_sources() does the same before showing sources to a
            # user, and evaluating at the chunk level would let one
            # relevant page's chunks pad out the retrieved list.
            retrieved_urls = list(dict.fromkeys(r.url for r in search_results))
            results.append(
                QueryResult(
                    query=item["query"],
                    relevant_urls=set(item["relevant_urls"]),
                    retrieved_urls=retrieved_urls,
                    top_k=top_k,
                )
            )
    finally:
        session.close()
    return results


def format_report(corpus: str, top_k: int, results: list[QueryResult]) -> str:
    lines = [
        f"# Retrieval eval: {corpus} (top_k={top_k})",
        "",
        "| Query | Precision@k | Recall@k | Hit | RR |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.query} | {r.precision:.2f} | {r.recall:.2f} | "
            f"{'yes' if r.hit else 'no'} | {r.reciprocal_rank:.2f} |"
        )

    mean_precision = statistics.mean(r.precision for r in results)
    mean_recall = statistics.mean(r.recall for r in results)
    hit_rate = sum(r.hit for r in results) / len(results)
    mrr = statistics.mean(r.reciprocal_rank for r in results)

    lines += [
        "",
        f"**Mean precision@{top_k}:** {mean_precision:.3f}  ",
        f"**Mean recall@{top_k}:** {mean_recall:.3f}  ",
        f"**Hit rate@{top_k}:** {hit_rate:.3f}  ",
        f"**MRR:** {mrr:.3f}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval quality against a labeled query set"
    )
    parser.add_argument("--corpus", required=True, help="Corpus config name")
    parser.add_argument(
        "--top-k", type=int, default=5, help="k for precision@k/recall@k (default: 5)"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Also write the report to this file"
    )
    args = parser.parse_args()

    results = run_eval(args.corpus, args.top_k)
    report = format_report(args.corpus, args.top_k, results)
    print(report)

    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()
