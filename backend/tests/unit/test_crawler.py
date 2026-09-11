"""Crawler tests — network is fully mocked; nothing here hits real URLs."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.config import CrawlConfig
from app.ingestion.crawler import (
    crawl,
    fetch_page,
    fetch_sitemap_urls,
    is_file_link,
    normalize_url,
    url_allowed,
)


class TestNormalizeUrl:
    def test_resolves_relative_link_against_base(self):
        assert normalize_url("https://example.com/a/", "/b") == "https://example.com/b"

    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com", "/b/") == "https://example.com/b"

    def test_resolves_absolute_link_unchanged(self):
        assert normalize_url("https://example.com/a", "https://other.com/c") == "https://other.com/c"


class TestUrlAllowed:
    def test_allows_everything_when_no_patterns_set(self):
        assert url_allowed("https://example.com/x", [], []) is True

    def test_deny_pattern_blocks_even_without_allow_patterns(self):
        assert url_allowed("https://example.com/x.png", [], [r"\.png$"]) is False

    def test_allow_pattern_restricts_scope(self):
        allow = [r"^https://example\.com/docs/"]
        assert url_allowed("https://example.com/docs/a", allow, []) is True
        assert url_allowed("https://example.com/other/a", allow, []) is False

    def test_deny_wins_over_allow(self):
        allow = [r"^https://example\.com/"]
        deny = [r"\.pdf$"]
        assert url_allowed("https://example.com/file.pdf", allow, deny) is False


class TestIsFileLink:
    def test_matches_configured_extension(self):
        assert is_file_link("https://example.com/a.pdf", [".pdf"]) is True

    def test_ignores_query_string(self):
        assert is_file_link("https://example.com/a.pdf?x=1", [".pdf"]) is True

    def test_no_match_for_unlisted_extension(self):
        assert is_file_link("https://example.com/a.docx", [".pdf"]) is False


class TestFetchSitemapUrls:
    def test_parses_loc_entries(self):
        sitemap_xml = b"""<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/a</loc></url>
          <url><loc>https://example.com/b</loc></url>
        </urlset>"""
        fake_response = MagicMock(content=sitemap_xml)
        fake_response.raise_for_status = MagicMock()
        with patch("app.ingestion.crawler.requests.get", return_value=fake_response):
            urls = fetch_sitemap_urls("https://example.com/sitemap.xml")
        assert urls == ["https://example.com/a", "https://example.com/b"]

    def test_returns_empty_list_on_request_failure(self):
        with patch(
            "app.ingestion.crawler.requests.get",
            side_effect=requests.RequestException("network down"),
        ):
            assert fetch_sitemap_urls("https://example.com/sitemap.xml") == []

    def test_returns_empty_list_on_malformed_xml(self):
        fake_response = MagicMock(content=b"<not valid xml")
        fake_response.raise_for_status = MagicMock()
        with patch("app.ingestion.crawler.requests.get", return_value=fake_response):
            assert fetch_sitemap_urls("https://example.com/sitemap.xml") == []


class TestFetchPage:
    def test_returns_extracted_page_on_success(self):
        fake_response = MagicMock(text="<html><body><p>Hi there.</p></body></html>")
        fake_response.raise_for_status = MagicMock()
        with patch("app.ingestion.crawler.requests.get", return_value=fake_response):
            page = fetch_page("https://example.com/a")
        assert page is not None
        assert "Hi there." in page.text

    def test_returns_none_on_request_failure(self):
        with patch(
            "app.ingestion.crawler.requests.get",
            side_effect=requests.RequestException("timeout"),
        ):
            assert fetch_page("https://example.com/a") is None


@pytest.fixture
def html_page():
    def _make(links: list[str], text: str = "Body text.") -> str:
        anchors = "".join(f'<a href="{link}">link</a>' for link in links)
        return f"<html><body><p>{text}</p>{anchors}</body></html>"

    return _make


class TestCrawlSeedListMode:
    def test_visits_seed_and_follows_allowed_links(self, html_page):
        pages = {
            "https://example.com/a": html_page(["/b", "https://other.com/x"]),
            "https://example.com/b": html_page([]),
        }

        def fake_get(url, headers=None, timeout=None):
            resp = MagicMock(text=pages[url])
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/a"],
            allow_patterns=[r"^https://example\.com/"],
            max_pages=10,
            max_depth=2,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        visited_urls = {p.url for p in result.pages}
        assert visited_urls == {"https://example.com/a", "https://example.com/b"}

    def test_respects_max_pages_budget(self, html_page):
        pages = {f"https://example.com/{i}": html_page([f"/{i + 1}"]) for i in range(10)}

        def fake_get(url, headers=None, timeout=None):
            resp = MagicMock(text=pages.get(url, html_page([])))
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/0"],
            allow_patterns=[r"^https://example\.com/"],
            max_pages=3,
            max_depth=10,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        assert len(result.pages) == 3

    def test_respects_max_depth(self, html_page):
        pages = {
            "https://example.com/0": html_page(["/1"]),
            "https://example.com/1": html_page(["/2"]),
            "https://example.com/2": html_page(["/3"]),
        }

        def fake_get(url, headers=None, timeout=None):
            resp = MagicMock(text=pages.get(url, html_page([])))
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/0"],
            allow_patterns=[r"^https://example\.com/"],
            max_pages=10,
            max_depth=1,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        visited_urls = {p.url for p in result.pages}
        assert visited_urls == {"https://example.com/0", "https://example.com/1"}

    def test_does_not_revisit_same_url_twice(self, html_page):
        loop_page = html_page(["/a"])  # links back to itself

        def fake_get(url, headers=None, timeout=None):
            resp = MagicMock(text=loop_page)
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/a"],
            allow_patterns=[r"^https://example\.com/"],
            max_pages=10,
            max_depth=5,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        assert len(result.pages) == 1

    def test_denied_links_are_never_fetched(self, html_page):
        fetch_log = []

        def fake_get(url, headers=None, timeout=None):
            fetch_log.append(url)
            resp = MagicMock(text=html_page(["https://external.com/x"]))
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/a"],
            allow_patterns=[r"^https://example\.com/"],
            max_pages=10,
            max_depth=3,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            crawl(config, request_delay=0)

        assert "https://external.com/x" not in fetch_log

    def test_collects_file_links_when_include_files_true(self, html_page):
        def fake_get(url, headers=None, timeout=None):
            resp = MagicMock(text=html_page(["/report.pdf"]))
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/a"],
            allow_patterns=[r"^https://example\.com/"],
            include_files=True,
            file_extensions=[".pdf"],
            max_pages=10,
            max_depth=2,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        assert len(result.file_links) == 1
        assert result.file_links[0]["file_url"] == "https://example.com/report.pdf"

    def test_file_links_ignored_when_include_files_false(self, html_page):
        def fake_get(url, headers=None, timeout=None):
            resp = MagicMock(text=html_page(["/report.pdf"]))
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="seed_list",
            seed_urls=["https://example.com/a"],
            allow_patterns=[r"^https://example\.com/"],
            include_files=False,
            file_extensions=[".pdf"],
            max_pages=10,
            max_depth=2,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        assert result.file_links == []


class TestCrawlSitemapMode:
    def test_uses_sitemap_urls_filtered_by_allow_patterns(self, html_page):
        sitemap_xml = b"""<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/docs/a</loc></url>
          <url><loc>https://example.com/other/b</loc></url>
        </urlset>"""

        def fake_get(url, headers=None, timeout=None, **kwargs):
            if url == "https://example.com/sitemap.xml":
                resp = MagicMock(content=sitemap_xml)
            else:
                resp = MagicMock(text=html_page([]))
            resp.raise_for_status = MagicMock()
            return resp

        config = CrawlConfig(
            mode="sitemap",
            sitemap_url="https://example.com/sitemap.xml",
            allow_patterns=[r"^https://example\.com/docs/"],
            max_pages=10,
            max_depth=1,
        )
        with patch("app.ingestion.crawler.requests.get", side_effect=fake_get):
            result = crawl(config, request_delay=0)

        visited_urls = {p.url for p in result.pages}
        assert visited_urls == {"https://example.com/docs/a"}

    def test_sitemap_mode_without_sitemap_url_raises(self):
        config = CrawlConfig(mode="sitemap", sitemap_url=None)
        with pytest.raises(ValueError, match="sitemap_url"):
            crawl(config, request_delay=0)
