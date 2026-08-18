from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.core.config as config
from app.api import extraction_review


@pytest.fixture()
def client(monkeypatch, tmp_path) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(extraction_review.router, prefix="/api/extraction-review")
    app.dependency_overrides[extraction_review.get_db] = lambda: object()

    monkeypatch.setattr(
        extraction_review,
        "list_review_runs",
        lambda _db, *, ticker=None, limit=50: {
            "items": [{"run_id": "run-1", "ticker": ticker or "BHP"}],
            "count": 1,
            "limit": limit,
        },
    )
    monkeypatch.setattr(
        extraction_review,
        "list_review_sessions",
        lambda *, ticker=None, limit=50: {
            "items": [{"session_id": "session-1", "ticker": ticker or "BHP"}],
            "count": 1,
            "limit": limit,
        },
    )
    monkeypatch.setattr(
        extraction_review,
        "load_review_session",
        lambda session_id: {
            "session_id": session_id,
            "items": [{"item_id": "item-1", "metric_name": "revenue"}],
        },
    )
    monkeypatch.setattr(
        extraction_review,
        "get_error_queue",
        lambda *, limit=200: {"items": [{"item_id": "wrong-1"}], "limit": limit},
    )
    monkeypatch.setattr(
        extraction_review,
        "get_run_status",
        lambda run_id, *, limit=120: {"run_id": run_id, "events": [], "limit": limit},
    )

    snippets_root = tmp_path / "snippets"
    snippets_root.mkdir()
    (snippets_root / "evidence.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(extraction_review, "SNIPPETS_ROOT", snippets_root)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "path",
    [
        "/api/extraction-review/runs",
        "/api/extraction-review/sessions",
        "/api/extraction-review/session/session-1",
        "/api/extraction-review/errors",
        "/api/extraction-review/run/run-1",
        "/api/extraction-review/snippets/evidence.png",
    ],
)
def test_extraction_review_read_routes_reject_missing_key_when_configured(
    client, monkeypatch, path: str
) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


@pytest.mark.parametrize(
    "path",
    [
        "/api/extraction-review/runs?ticker=bhp&limit=10",
        "/api/extraction-review/sessions?ticker=bhp&limit=10",
        "/api/extraction-review/session/session-1",
        "/api/extraction-review/errors?limit=5",
        "/api/extraction-review/run/run-1?limit=5",
    ],
)
def test_extraction_review_read_routes_accept_matching_key(
    client, monkeypatch, path: str
) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    response = client.get(path, headers={"X-API-Key": "local-secret"})

    assert response.status_code == 200


def test_extraction_review_snippet_accepts_matching_key(client, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    response = client.get(
        "/api/extraction-review/snippets/evidence.png",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_extraction_review_read_routes_allow_unconfigured_local_dev(
    client, monkeypatch
) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "", raising=False)

    response = client.get("/api/extraction-review/runs?ticker=bhp&limit=10")

    assert response.status_code == 200
    assert response.json()["items"][0]["ticker"] == "BHP"


def test_extraction_review_snippet_keeps_path_traversal_guard(
    client, monkeypatch
) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    response = client.get(
        "/api/extraction-review/snippets/bad%5Cname.png",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid snippet image name"
