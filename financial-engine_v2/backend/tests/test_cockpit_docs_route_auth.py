from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.routes import cockpit_api
from app.routes.cockpit_api import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    return TestClient(app, raise_server_exceptions=False)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        assert value == 200
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.closed = False
        self.queried = False

    def query(self, model):
        assert model is cockpit_api.Document
        self.queried = True
        return _FakeQuery(self.rows)

    def close(self):
        self.closed = True


def test_cockpit_docs_denies_missing_api_key_before_opening_db(monkeypatch):
    monkeypatch.setattr(
        api_routes.settings, "local_api_key", "local-secret", raising=False
    )

    def fail_if_opened():
        raise AssertionError("SessionLocal must not be opened before API-key auth")

    monkeypatch.setattr(cockpit_api, "SessionLocal", fail_if_opened)

    response = _client().get("/api/cockpit/docs")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_cockpit_docs_accepts_api_key_and_returns_documents(monkeypatch):
    monkeypatch.setattr(
        api_routes.settings, "local_api_key", "local-secret", raising=False
    )
    document_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    published_at = datetime(2026, 6, 26, 1, 2, 3, tzinfo=timezone.utc)
    fake_db = _FakeSession(
        [
            SimpleNamespace(
                document_id=document_id,
                ticker="BHP",
                doc_class="annual_report",
                doc_subtype="appendix_4e",
                published_at=published_at,
                title="BHP Annual Report",
                source_url="https://example.test/bhp.pdf",
                pdf_path="/tmp/bhp.pdf",
            )
        ]
    )
    monkeypatch.setattr(cockpit_api, "SessionLocal", lambda: fake_db)

    response = _client().get(
        "/api/cockpit/docs", headers={"X-API-Key": "local-secret"}
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "document_id": str(document_id),
            "ticker": "BHP",
            "doc_class": "annual_report",
            "doc_subtype": "appendix_4e",
            "published_at": "2026-06-26T01:02:03+00:00",
            "title": "BHP Annual Report",
            "source_url": "https://example.test/bhp.pdf",
            "pdf_path": "/tmp/bhp.pdf",
        }
    ]
    assert fake_db.queried is True
    assert fake_db.closed is True
