"""Shared result shape returned by every retrieval strategy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    chunk_text: str
    url: str
    title: str
    category: str
    source_type: str
    score: float
