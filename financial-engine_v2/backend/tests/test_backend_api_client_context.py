"""Tests for BackendApiClient context + commentary methods."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Ensure the cockpit package is importable.
FE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FE_ROOT))

from cockpit.integrations.backend_api import BackendApiClient


@pytest.fixture
def client():
    return BackendApiClient("http://localhost:8000")


# ---------------------------------------------------------------------------
# get_ticker_context
# ---------------------------------------------------------------------------

class TestGetTickerContext:
    def test_success(self, client):
        response_data = {
            "ticker": "BHP",
            "docs": [],
            "financials": [],
            "latest_financial_snapshot": None,
            "announcement_context": [],
            "extraction_failures": [],
            "low_confidence_financials": [],
            "backend_version": "1.0",
            "errors": [],
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"ticker":"BHP"}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = mock_response

            result = client.get_ticker_context("BHP")

        assert result["ticker"] == "BHP"
        assert result["errors"] == []

    def test_http_error_raises(self, client):
        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=MagicMock(), response=MagicMock(status_code=400)
            )
            mock_http.get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.get_ticker_context("BHP")


# ---------------------------------------------------------------------------
# approve_transcript
# ---------------------------------------------------------------------------

class TestApproveTranscript:
    def test_success(self, client):
        response_data = {"ok": True, "source_id": "src-001", "points_upserted": 5, "collection": "commentary_chunks"}
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            result = client.approve_transcript("src-001")

        assert result["ok"] is True

    def test_non_200_raises(self, client):
        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
            )
            mock_http.post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.approve_transcript("unknown")


# ---------------------------------------------------------------------------
# get_pending_transcripts
# ---------------------------------------------------------------------------

class TestGetPendingTranscripts:
    def test_success(self, client):
        response_data = {"pending": [{"source_id": "src-001"}], "count": 1}
        mock_response = MagicMock()
        mock_response.content = b'{"pending": []}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = mock_response

            result = client.get_pending_transcripts()

        assert result["count"] == 1
