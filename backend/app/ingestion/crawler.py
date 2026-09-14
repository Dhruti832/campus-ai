"""Generic, config-driven web crawler.

Generalizes the original's ``site_crawler.py``: that version hardcoded a
Dalhousie sitemap URL and a Python dict of Dalhousie URL-prefix "scopes"
(``SCOPE_PREFIXES``) directly in code. Here, the sitemap/seed URLs and the
allow/deny scope patterns both come from a corpus's ``CrawlConfig`` — the
crawler itself has no idea what site it's pointed at.

Also fixes a latent bug in the original: it declared a ``max_depth``
constant but never actually used it to bound the crawl (only an
implicit two-level "seeds, then seeds' links" structure). This version
does a real depth-bounded BFS.
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests

from app.config import CrawlConfig
from app.ingestion.extractor import ExtractedPage, extract_html

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
REQUEST_DELAY_SECONDS = 0.5
USER_AGENT = "CampusAI-Crawler/1.0"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@dataclass
class CrawledPage:
    url: str
    title: str
    text: str
    links: list[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    pages: list[CrawledPage] = field(default_factory=list)
    file_links: list[dict] = field(default_factory=list)


def normalize_url(base_url: str, link: str) -> str:
    absolute = urljoin(base_url, link)
    parsed = urlparse(absolute)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def url_allowed(url: str, allow_patterns: list[str], deny_patterns: list[str]) -> bool:
    if any(re.search(pattern, url) for pattern in deny_patterns):
        return False
    if not allow_patterns:
        return True
    return any(re.search(pattern, url) for pattern in allow_patterns)


def is_file_link(url: str, file_extensions: list[str]) -> bool:
    return any(url.lower().split("?")[0].endswith(ext.lower()) for ext in file_extensions)


def fetch_sitemap_urls(sitemap_url: str) -> list[str]:
    """Fetch and parse a sitemap.xml, returning every <loc> URL."""
    try:
        response = requests.get(sitemap_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        return [loc.text.strip() for loc in root.iter(f"{SITEMAP_NS}loc") if loc.text]
    except (requests.RequestException, ET.ParseError) as exc:
        logger.warning("Failed to fetch/parse sitemap %s: %s", sitemap_url, exc)
        return []


def fetch_page(url: str) -> ExtractedPage | None:
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return extract_html(response.text)
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _get_seed_urls(config: CrawlConfig) -> list[str]:
    if config.mode == "sitemap":
        if not config.sitemap_url:
            raise ValueError("crawl.mode is 'sitemap' but no sitemap_url is configured")
        all_urls = fetch_sitemap_urls(config.sitemap_url)
        return [u for u in all_urls if url_allowed(u, config.allow_patterns, config.deny_patterns)]
    return list(config.seed_urls)


def crawl(config: CrawlConfig, request_delay: float = REQUEST_DELAY_SECONDS) -> CrawlResult:
    """Depth- and page-count-bounded BFS crawl driven entirely by ``config``."""
    seeds = _get_seed_urls(config)
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque((normalize_url(u, u), 0) for u in seeds)

    pages: list[CrawledPage] = []
    file_links: dict[str, dict] = {}

    while queue and len(pages) < config.max_pages:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        if not url_allowed(url, config.allow_patterns, config.deny_patterns):
            continue

        extracted = fetch_page(url)
        if request_delay:
            time.sleep(request_delay)
        if extracted is None:
            continue

        pages.append(
            CrawledPage(
                url=url, title=extracted.title, text=extracted.text, links=extracted.links
            )
        )

        for link in extracted.links:
            if config.include_files and is_file_link(link, config.file_extensions):
                file_url = urljoin(url, link)
                file_links.setdefault(
                    file_url,
                    {
                        "file_url": file_url,
                        "source_page": url,
                        "file_type": file_url.split(".")[-1],
                    },
                )
                continue
            if depth < config.max_depth:
                normalized = normalize_url(url, link)
                if normalized not in visited:
                    queue.append((normalized, depth + 1))

    return CrawlResult(pages=pages, file_links=list(file_links.values()))
