#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

try:
    from cockpit.integrations.web_fetcher import WebFetcher  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - dependency optional in local test env
    WebFetcher = None  # type: ignore[assignment]


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeClient:
    def __init__(self, routes: dict[str, str], search_html: str, *args, **kwargs) -> None:  # noqa: ANN002, ARG002
        self._routes = routes
        self._search_html = search_html

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001, D401
        return False

    def get(self, url: str, params=None, headers=None):  # noqa: ANN001, ARG002
        if "duckduckgo.com/html/" in url:
            return _FakeResponse(self._search_html)
        return _FakeResponse(self._routes.get(url, "<html><body>empty</body></html>"))


@unittest.skipIf(WebFetcher is None, "httpx is not installed in this environment")
class CockpitWebFetcherQualityTests(unittest.TestCase):
    def test_fetch_text_accepts_max_chars(self):
        routes = {
            "https://example.com/article": "<html><body>abcdefghijklmnopqrstuvwxyz</body></html>"
        }
        with mock.patch(
            "cockpit.integrations.web_fetcher.httpx.Client",
            side_effect=lambda *a, **k: _FakeClient(routes, "<html></html>", *a, **k),
        ):
            fetcher = WebFetcher()
            text = fetcher.fetch_text("https://example.com/article", max_chars=10)
        self.assertEqual(len(text), 10)

    def test_strict_official_first_prefers_official_url_when_available(self):
        search_html = """
        <a href="https://example.com/article">A</a>
        <a href="https://www.asx.com.au/markets/company/BHP">B</a>
        """
        routes = {
            "https://example.com/article": "<html><body>Revenue was 100.</body></html>",
            "https://www.asx.com.au/markets/company/BHP": "<html><body>Revenue was 120.</body></html>",
        }
        with mock.patch(
            "cockpit.integrations.web_fetcher.httpx.Client",
            side_effect=lambda *a, **k: _FakeClient(routes, search_html, *a, **k),
        ):
            fetcher = WebFetcher()
            result = fetcher.search_and_fetch(
                "BHP latest update",
                max_results=2,
                preferred_domains=["asx.com.au"],
                strict_official=True,
            )
        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("official_source_found"))
        self.assertEqual(result.get("urls")[0], "https://www.asx.com.au/markets/company/BHP")
        self.assertTrue(result.get("pages")[0].get("official_source"))

    def test_official_not_found_flag_when_missing(self):
        search_html = '<a href="https://example.com/article">A</a>'
        routes = {"https://example.com/article": "<html><body>Debt stood at $300m.</body></html>"}
        with mock.patch(
            "cockpit.integrations.web_fetcher.httpx.Client",
            side_effect=lambda *a, **k: _FakeClient(routes, search_html, *a, **k),
        ):
            fetcher = WebFetcher()
            result = fetcher.search_and_fetch(
                "BHP debt update",
                max_results=1,
                preferred_domains=["asx.com.au"],
                strict_official=True,
            )
        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("official_source_found"))
        self.assertTrue(result.get("official_source_required"))

    def test_fact_extraction_emits_structured_claim_rows(self):
        search_html = '<a href="https://example.com/article">A</a>'
        routes = {
            "https://example.com/article": (
                "<html><body>"
                "On 2026-02-20 the company reported revenue of $1.2 billion and net debt of $300m. "
                "Liquidity remained strong with undrawn facilities."
                "</body></html>"
            )
        }
        with mock.patch(
            "cockpit.integrations.web_fetcher.httpx.Client",
            side_effect=lambda *a, **k: _FakeClient(routes, search_html, *a, **k),
        ):
            fetcher = WebFetcher()
            result = fetcher.search_and_fetch("BHP revenue debt", max_results=1)
        self.assertTrue(result.get("ok"))
        self.assertGreaterEqual(int(result.get("facts_count") or 0), 1)
        facts = result.get("facts") or []
        self.assertTrue(isinstance(facts, list) and facts)
        self.assertIn("url", facts[0])
        self.assertIn("claim", facts[0])
        self.assertIn("numbers", facts[0])

    def test_search_and_fetch_respects_max_chars_per_page(self):
        search_html = '<a href="https://example.com/article">A</a>'
        routes = {
            "https://example.com/article": (
                "<html><body>" + ("x" * 5000) + "</body></html>"
            )
        }
        with mock.patch(
            "cockpit.integrations.web_fetcher.httpx.Client",
            side_effect=lambda *a, **k: _FakeClient(routes, search_html, *a, **k),
        ):
            fetcher = WebFetcher()
            result = fetcher.search_and_fetch(
                "BHP",
                max_results=1,
                max_chars_per_page=123,
            )
        self.assertTrue(result.get("ok"))
        pages = result.get("pages") or []
        self.assertEqual(len(pages), 1)
        self.assertLessEqual(len(str(pages[0].get("text") or "")), 123)


if __name__ == "__main__":
    unittest.main()
