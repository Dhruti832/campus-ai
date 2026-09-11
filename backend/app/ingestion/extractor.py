"""Content extraction from raw HTML and PDF bytes.

Kept separate from crawler.py (which does network + link-graph traversal)
so extraction logic can be unit tested without mocking HTTP at all.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

EXCLUDE_TAGS = ("nav", "footer", "script", "style", "aside")
MIN_LINE_LENGTH = 40


@dataclass
class ExtractedPage:
    title: str
    headings: list[str] = field(default_factory=list)
    text: str = ""
    links: list[str] = field(default_factory=list)


def extract_html(html: str, exclude_tags: tuple[str, ...] = EXCLUDE_TAGS) -> ExtractedPage:
    """Parse a page's HTML into title/headings/body-text/links.

    Strips navigation/boilerplate elements before extracting text, same
    idea as the original's scraper.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(exclude_tags):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    links = [a["href"] for a in soup.find_all("a", href=True)]

    return ExtractedPage(title=title, headings=headings, text="\n\n".join(paragraphs), links=links)


def clean_text(text: str, min_line_length: int = MIN_LINE_LENGTH) -> str:
    """Drop short non-sentence lines (nav crumbs, labels) scraped pages
    tend to accumulate."""
    lines = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if len(line) < min_line_length and not line.endswith("."):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def extract_pdf_text(data: bytes) -> str:
    """Extract concatenated text from a PDF's bytes."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(t for t in pages_text if t.strip())
