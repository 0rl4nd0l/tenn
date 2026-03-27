"""Tests for HNSearchClient (Hacker News Algolia API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cockpit.integrations.hn_search import HNSearchClient


# ------------------------------------------------------------------
# Happy path: returns stories sorted by points descending
# ------------------------------------------------------------------


def test_search_returns_stories_sorted_by_points():
    """Stories are returned sorted by points descending."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hits": [
            {
                "objectID": "100",
                "title": "Low score",
                "url": "https://a.com",
                "points": 10,
                "num_comments": 2,
                "author": "alice",
                "created_at": "2026-03-20T00:00:00Z",
            },
            {
                "objectID": "200",
                "title": "High score",
                "url": "https://b.com",
                "points": 500,
                "num_comments": 100,
                "author": "bob",
                "created_at": "2026-03-21T00:00:00Z",
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("cockpit.integrations.hn_search.httpx.get", return_value=mock_response):
        client = HNSearchClient()
        result = client.search("BHP mining")

    assert result["ok"] is True
    assert len(result["stories"]) == 2
    assert result["stories"][0]["title"] == "High score"
    assert result["stories"][0]["points"] == 500
    assert result["stories"][1]["points"] == 10


# ------------------------------------------------------------------
# Failure: Algolia API down — returns empty list, no raise
# ------------------------------------------------------------------


def test_search_api_down_returns_empty():
    """When Algolia API raises, returns empty list with error message."""
    with patch(
        "cockpit.integrations.hn_search.httpx.get",
        side_effect=httpx.HTTPError("Connection refused"),
    ):
        client = HNSearchClient()
        result = client.search("BHP")

    assert result["ok"] is False
    assert result["stories"] == []
    assert "error" in result


# ------------------------------------------------------------------
# Edge: stories with missing points field handled gracefully
# ------------------------------------------------------------------


def test_missing_points_treated_as_zero():
    """Stories with missing/None points are treated as 0."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hits": [
            {
                "objectID": "300",
                "title": "No points field",
                "url": "https://c.com",
                "num_comments": 5,
                "author": "charlie",
                "created_at": "2026-03-22T00:00:00Z",
                # points key missing entirely
            },
            {
                "objectID": "400",
                "title": "None points",
                "url": "https://d.com",
                "points": None,
                "num_comments": 3,
                "author": "dave",
                "created_at": "2026-03-22T00:00:00Z",
            },
            {
                "objectID": "500",
                "title": "Has points",
                "url": "https://e.com",
                "points": 42,
                "num_comments": 8,
                "author": "eve",
                "created_at": "2026-03-22T00:00:00Z",
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("cockpit.integrations.hn_search.httpx.get", return_value=mock_response):
        client = HNSearchClient()
        result = client.search("test")

    assert result["ok"] is True
    assert len(result["stories"]) == 3
    # Has points (42) should be first
    assert result["stories"][0]["points"] == 42
    # Missing/None points should be 0
    assert result["stories"][1]["points"] == 0
    assert result["stories"][2]["points"] == 0


def test_empty_query_returns_error():
    """Empty query returns error immediately."""
    client = HNSearchClient()
    result = client.search("   ")

    assert result["ok"] is False
    assert result["stories"] == []
