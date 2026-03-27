"""Tests for BraveSearchClient with DDG fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cockpit.integrations.brave_search import BraveSearchClient


# ------------------------------------------------------------------
# Happy path: Brave API responds 200
# ------------------------------------------------------------------


def test_brave_search_happy_path():
    """Brave API returns structured results with title, url, snippet."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "BHP Group",
                    "url": "https://example.com/bhp",
                    "description": "Mining company",
                    "age": "2d",
                },
                {
                    "title": "BHP News",
                    "url": "https://example.com/bhp-news",
                    "description": "Latest news",
                    "age": "1d",
                },
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("cockpit.integrations.brave_search.httpx.get", return_value=mock_response):
        client = BraveSearchClient(api_key="test-key")
        result = client.search("BHP mining")

    assert result["ok"] is True
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "BHP Group"
    assert result["results"][0]["url"] == "https://example.com/bhp"
    assert result["results"][0]["snippet"] == "Mining company"


# ------------------------------------------------------------------
# Fallback: Brave API fails, DDG fallback fires
# ------------------------------------------------------------------


def test_brave_fails_ddg_fallback_fires():
    """When Brave raises httpx.HTTPError, DDG fallback returns results."""
    mock_fetcher = MagicMock()
    mock_fetcher.search_and_fetch.return_value = {
        "ok": True,
        "pages": [
            {"url": "https://ddg.example.com/bhp", "text": "DDG result text"},
        ],
    }

    with patch(
        "cockpit.integrations.brave_search.httpx.get",
        side_effect=httpx.HTTPError("503 Service Unavailable"),
    ):
        client = BraveSearchClient(api_key="test-key", web_fetcher=mock_fetcher)
        result = client.search("BHP mining")

    assert result["ok"] is True
    assert len(result["results"]) == 1
    assert result["results"][0]["url"] == "https://ddg.example.com/bhp"
    mock_fetcher.search_and_fetch.assert_called_once()


# ------------------------------------------------------------------
# Empty: both Brave and DDG return empty
# ------------------------------------------------------------------


def test_both_empty_returns_empty_list():
    """Both Brave and DDG return empty — returns empty list, no raise."""
    mock_fetcher = MagicMock()
    mock_fetcher.search_and_fetch.return_value = {"ok": True, "pages": []}

    with patch(
        "cockpit.integrations.brave_search.httpx.get",
        side_effect=httpx.HTTPError("timeout"),
    ):
        client = BraveSearchClient(api_key="test-key", web_fetcher=mock_fetcher)
        result = client.search("nonexistent query xyz")

    assert result["ok"] is True
    assert result["results"] == []


def test_no_api_key_no_fetcher_returns_error():
    """No Brave key and no WebFetcher — returns error dict, no raise."""
    client = BraveSearchClient(api_key="", web_fetcher=None)
    result = client.search("anything")

    assert result["ok"] is False
    assert result["results"] == []
    assert "error" in result


def test_empty_query_returns_error():
    """Empty query returns error immediately."""
    client = BraveSearchClient(api_key="test-key")
    result = client.search("   ")

    assert result["ok"] is False
    assert result["results"] == []
