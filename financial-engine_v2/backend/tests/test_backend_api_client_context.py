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


class TestGetCompanyDump:
    def test_success(self, client):
        response_data = {
            "ticker": "BHP",
            "summary": {"doc_count": 1},
            "docs": [],
            "financials": [],
            "announcement_context": [],
            "risk_notes": [],
            "price": {},
            "price_history_1y": [],
            "price_summary_1y": {},
            "extraction_failures": [],
            "low_confidence_financials": [],
            "company_memory": {},
            "market_memory": {},
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

            result = client.get_company_dump("BHP")

        assert result["ticker"] == "BHP"
        called_params = mock_http.get.call_args.kwargs["params"]
        assert called_params["ticker"] == "BHP"

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
                client.get_company_dump("BHP")


class TestMemoryMethods:
    def test_get_memory_dump(self, client):
        response_data = {
            "ticker": "BHP",
            "company_memory": {"entries": [], "change_log": []},
            "market_memory": {"items": []},
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

            result = client.get_memory_dump("BHP")

        assert result["ticker"] == "BHP"
        called = mock_http.get.call_args
        assert called.kwargs["params"]["ticker"] == "BHP"
        assert called.kwargs["headers"] == {}

    def test_add_company_memory_note_posts_payload(self, client):
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = {"ok": True, "entry": {"entry_id": 7}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            result = client.add_company_memory_note(
                "bhp",
                "Temporary rail outage is constraining exports.",
            )

        assert result["entry"]["entry_id"] == 7
        called = mock_http.post.call_args
        assert called.args[0].endswith("/api/context/memory/company/add")
        assert called.kwargs["json"]["ticker"] == "BHP"
        assert called.kwargs["json"]["type"] == "observed_fact"

    def test_expire_company_memory_entry_posts_payload(self, client):
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            client.expire_company_memory_entry("BHP", 11)

        called = mock_http.post.call_args
        assert called.args[0].endswith("/api/context/memory/company/expire")
        assert called.kwargs["json"] == {"ticker": "BHP", "entry_id": 11}

    def test_add_market_memory_note_defaults_to_sector_trend(self, client):
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = {"ok": True, "entry": {"entry_id": 9}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            client.add_market_memory_note(
                "BHP",
                "Iron ore sentiment is improving.",
            )

        called = mock_http.post.call_args
        assert called.args[0].endswith("/api/context/memory/market/add")
        assert called.kwargs["json"]["ticker"] == "BHP"
        assert called.kwargs["json"]["scope"] == "sector"
        assert called.kwargs["json"]["type"] == "sector_trend"

    def test_expire_market_memory_entry_posts_payload(self, client):
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            client.expire_market_memory_entry(5, scope="macro")

        called = mock_http.post.call_args
        assert called.args[0].endswith("/api/context/memory/market/expire")
        assert called.kwargs["json"] == {"entry_id": 5, "scope": "macro"}


# ---------------------------------------------------------------------------
# approve_transcript
# ---------------------------------------------------------------------------


class TestApproveTranscript:
    def test_success(self, client):
        response_data = {
            "ok": True,
            "source_id": "src-001",
            "points_upserted": 5,
            "collection": "commentary_chunks",
        }
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


class TestExtractionReviewMethods:
    def test_process_document(self, client):
        response_data = {
            "mode": "sync",
            "document_id": "doc-1",
            "extraction_status": "ok",
        }
        mock_response = MagicMock()
        mock_response.content = b'{"mode":"sync"}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            result = client.process_document("doc-1")

        assert result["document_id"] == "doc-1"
        mock_http.post.assert_called_once()

    def test_create_review_session(self, client):
        response_data = {
            "session_id": "manual-review-1",
            "items": [{"item_id": "run-1:revenue"}],
        }
        mock_response = MagicMock()
        mock_response.content = b'{"session_id":"manual-review-1"}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            result = client.create_extraction_review_session(["doc-1", "doc-2"])

        assert result["session_id"] == "manual-review-1"
        called_json = mock_http.post.call_args.kwargs["json"]
        assert called_json == {"document_ids": ["doc-1", "doc-2"], "run_ids": []}

    def test_create_review_session_for_explicit_run_ids(self, client):
        response_data = {
            "session_id": "manual-review-2",
            "run_ids": ["run-1"],
        }
        mock_response = MagicMock()
        mock_response.content = b'{"session_id":"manual-review-2"}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_response

            result = client.create_extraction_review_session(run_ids=["run-1"])

        assert result["session_id"] == "manual-review-2"
        called_json = mock_http.post.call_args.kwargs["json"]
        assert called_json == {"document_ids": [], "run_ids": ["run-1"]}

    def test_list_review_runs(self, client):
        response_data = {
            "count": 1,
            "items": [{"run_id": "run-1", "ticker": "BHP"}],
        }
        mock_response = MagicMock()
        mock_response.content = b'{"count":1}'
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = mock_response

            result = client.list_extraction_review_runs(ticker="bhp", limit=20)

        assert result["count"] == 1
        called_params = mock_http.get.call_args.kwargs["params"]
        assert called_params == {"ticker": "BHP", "limit": 20}

    def test_submit_review_decision_and_error_queue(self, client):
        decision_response = MagicMock()
        decision_response.content = b'{"session_id":"manual-review-1"}'
        decision_response.json.return_value = {
            "session_id": "manual-review-1",
            "item": {"item_id": "run-1:revenue"},
        }
        decision_response.raise_for_status = MagicMock()

        queue_response = MagicMock()
        queue_response.content = b'{"count":1}'
        queue_response.json.return_value = {
            "count": 1,
            "items": [{"item_id": "run-1:revenue"}],
        }
        queue_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_http)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = decision_response
            mock_http.get.return_value = queue_response

            result = client.submit_extraction_review_decision(
                "manual-review-1",
                item_id="run-1:revenue",
                status="wrong",
                expected_value="125.0",
                reviewer_note="Column shifted",
            )
            queue = client.get_extraction_review_errors(limit=25)

        assert result["session_id"] == "manual-review-1"
        posted_json = mock_http.post.call_args.kwargs["json"]
        assert posted_json["status"] == "wrong"
        assert posted_json["expected_value"] == "125.0"
        assert queue["count"] == 1
