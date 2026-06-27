from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import context as context_api


def _mock_db_session(query_results: dict[str, list[dict[str, Any]]]):
    db = MagicMock()

    def fake_execute(sql_text, params=None):
        sql_str = str(sql_text)
        result_mock = MagicMock()
        rows = []
        for table_key, table_rows in query_results.items():
            if table_key.lower() in sql_str.lower():
                rows = table_rows
                break

        row_mocks = []
        for row in rows:
            row_mock = MagicMock()
            row_mock._mapping = row
            row_mocks.append(row_mock)
        result_mock.__iter__ = lambda self: iter(row_mocks)
        return result_mock

    db.execute = fake_execute
    return db


def _diagnostic_db():
    return _mock_db_session(
        {
            "extraction_runs": [
                {
                    "run_id": "run-1",
                    "document_id": "doc-1",
                    "status": "failed",
                    "error": "parser leaked stack path",
                    "created_at": "2026-06-26T00:00:00Z",
                    "ticker": "BHP",
                    "title": "BHP result",
                }
            ],
            "documents": [
                {
                    "document_id": "doc-1",
                    "ticker": "BHP",
                    "doc_class": "results",
                    "doc_subtype": None,
                    "published_at": "2026-06-26",
                    "title": "BHP result",
                    "source_url": "https://example.test/bhp.pdf",
                    "pdf_path": "/private/source/bhp.pdf",
                    "pdf_sha256": "abc123",
                }
            ],
            "cockpit_announcement_context": [
                {
                    "document_id": "doc-1",
                    "ticker": "BHP",
                    "published_at": "2026-06-26",
                    "title": "BHP result",
                    "pdf_path": "/private/source/bhp.pdf",
                    "source_url": "https://example.test/bhp.pdf",
                    "excerpt": "local source excerpt",
                    "extracted_text": "local source text",
                    "updated_at": "2026-06-26T00:00:00Z",
                }
            ],
            "asx_periodic_financials": [
                {
                    "ticker": "BHP",
                    "period_end": "2025-12-31",
                    "period_type": "annual",
                    "revenue": "50000",
                    "ebit": "20000",
                    "np_attributable": "15000",
                    "operating_cf": "25000",
                    "investing_cf": "-10000",
                    "financing_cf": "-5000",
                    "capex": "-8000",
                    "cash_end": "12000",
                    "net_debt": "3000",
                    "shares_outstanding": "5000000",
                    "confidence_metrics": 0.25,
                    "source_document_id": "doc-1",
                }
            ],
        }
    )


def _client(db=None) -> TestClient:
    app = FastAPI()
    app.include_router(context_api.router, prefix="/api/context")
    if db is not None:
        app.dependency_overrides[context_api.get_db] = lambda: db
    return TestClient(app, raise_server_exceptions=False)


def test_ticker_context_redacts_diagnostics_without_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    response = _client(_diagnostic_db()).get("/api/context/ticker?ticker=BHP")

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnostics_redacted"] is True
    assert payload["docs"][0]["title"] == "BHP result"
    assert payload["docs"][0]["source_url"] is None
    assert payload["docs"][0]["pdf_path"] is None
    assert payload["docs"][0]["pdf_sha256"] is None
    assert payload["announcement_context"][0]["pdf_path"] is None
    assert payload["announcement_context"][0]["source_url"] is None
    assert payload["announcement_context"][0]["excerpt"] is None
    assert payload["announcement_context"][0]["extracted_text"] is None
    assert payload["financials"]
    assert payload["extraction_failures"] == []
    assert payload["low_confidence_financials"] == []
    assert payload["errors"] == []


def test_ticker_context_keeps_diagnostics_with_matching_api_key(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    response = _client(_diagnostic_db()).get(
        "/api/context/ticker?ticker=BHP",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnostics_redacted"] is False
    assert payload["docs"][0]["source_url"] == "https://example.test/bhp.pdf"
    assert payload["docs"][0]["pdf_path"] == "/private/source/bhp.pdf"
    assert payload["docs"][0]["pdf_sha256"] == "abc123"
    assert payload["announcement_context"][0]["pdf_path"] == "/private/source/bhp.pdf"
    assert payload["announcement_context"][0]["excerpt"] == "local source excerpt"
    assert payload["announcement_context"][0]["extracted_text"] == "local source text"
    assert payload["extraction_failures"][0]["error"] == "parser leaked stack path"
    assert payload["low_confidence_financials"]


def test_ticker_context_internal_helper_keeps_diagnostics_when_api_key_configured(
    monkeypatch,
):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    payload = context_api.get_ticker_context(ticker="BHP", db=_diagnostic_db())

    assert payload["diagnostics_redacted"] is False
    assert payload["docs"][0]["pdf_path"] == "/private/source/bhp.pdf"
    assert payload["announcement_context"][0]["excerpt"] == "local source excerpt"
    assert payload["extraction_failures"][0]["error"] == "parser leaked stack path"
    assert payload["low_confidence_financials"]


def test_ticker_context_keeps_diagnostics_when_local_api_key_unconfigured(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "", raising=False)

    response = _client(_diagnostic_db()).get("/api/context/ticker?ticker=BHP")

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnostics_redacted"] is False
    assert payload["docs"][0]["pdf_path"] == "/private/source/bhp.pdf"
    assert payload["extraction_failures"]
    assert payload["low_confidence_financials"]


def test_company_dump_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    response = _client(_diagnostic_db()).get("/api/context/company_dump?ticker=BHP")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_company_dump_preserves_diagnostics_with_matching_api_key(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    response = _client(_diagnostic_db()).get(
        "/api/context/company_dump?ticker=BHP",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["extraction_failure_count"] == 1
    assert payload["summary"]["low_confidence_financial_count"] == 1
    assert payload["docs"][0]["pdf_path"] == "/private/source/bhp.pdf"
    assert payload["extraction_failures"][0]["error"] == "parser leaked stack path"
    assert payload["low_confidence_financials"]


def test_verification_context_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    response = _client(_diagnostic_db()).get("/api/context/verification?ticker=BHP")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_verification_context_accepts_matching_api_key(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    response = _client(_diagnostic_db()).get(
        "/api/context/verification?ticker=BHP",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["extraction_failures"][0]["error"] == "parser leaked stack path"
    assert payload["low_confidence_financials"]


def test_verification_runs_requires_api_key_before_service_call(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    def fail_if_called():
        raise AssertionError("CockpitService must not be opened before API-key auth")

    from app.services import cockpit_service

    monkeypatch.setattr(cockpit_service.CockpitService, "get_instance", fail_if_called)

    response = _client().get("/api/context/verification/runs?limit=1")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_verification_runs_accepts_matching_api_key(monkeypatch):
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)

    class _Service:
        def get_verification_runs(self, limit: int):
            return [{"id": "run-1", "limit": limit}]

    from app.services import cockpit_service

    monkeypatch.setattr(cockpit_service.CockpitService, "get_instance", lambda: _Service())

    response = _client().get(
        "/api/context/verification/runs?limit=1",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runs": [{"id": "run-1", "limit": 1}],
        "count": 1,
    }
