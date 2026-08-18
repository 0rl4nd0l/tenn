"""Tests for GET /api/commentary/recent."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import commentary as mod
from app.main import app
from app.services.source_registry import SourceRegistry


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("LOCAL_API_KEY", "test-key")}


def test_recent_returns_approved_commentary_sources_newest_first(monkeypatch) -> None:
    rows = [
        {
            "source_id": "youtube_transcript:video-a:111",
            "source_type": "youtube_transcript",
            "source_name": "Video A",
            "review_status": "approved",
            "approved_at": "2026-05-01T10:00:00Z",
            "ingested_at": "2026-05-01T09:00:00Z",
        },
        {
            "source_id": "youtube_transcript:video-pending:333",
            "source_type": "youtube_transcript",
            "source_name": "Pending Video",
            "review_status": "pending",
            "approved_at": "2026-05-03T10:00:00Z",
        },
        {
            "source_id": "book:framework:444",
            "source_type": "book",
            "source_name": "Framework PDF",
            "review_status": "approved",
            "approved_at": "2026-05-04T10:00:00Z",
        },
        {
            "source_id": "market_commentary:macro:222",
            "source_type": "market_commentary",
            "source_name": "Macro Note",
            "review_status": "approved",
            "approved_at": "2026-05-02T10:00:00Z",
        },
    ]

    class RegistryStub:
        def all(self) -> list[dict[str, object]]:
            return rows

    monkeypatch.setattr(mod, "SourceRegistry", RegistryStub)

    response = TestClient(app).get(
        "/api/commentary/recent?limit=10",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [item["source_id"] for item in body["items"]] == [
        "market_commentary:macro:222",
        "youtube_transcript:video-a:111",
    ]
    assert body["items"][0]["source_name"] == "Macro Note"
    assert body["items"][0]["source_type"] == "market_commentary"
    assert body["items"][0]["source_kind"] == "concat"
    assert body["items"][0]["approved_at"] == "2026-05-02T10:00:00Z"
    assert body["items"][1]["source_type"] == "youtube_transcript"
    assert body["items"][1]["source_kind"] == "ephemeral"


def test_recent_honors_limit(monkeypatch) -> None:
    rows = [
        {
            "source_id": f"youtube_transcript:video-{index}:abc",
            "source_type": "youtube_transcript",
            "source_name": f"Video {index}",
            "review_status": "approved",
            "approved_at": f"2026-05-0{index}T10:00:00Z",
        }
        for index in range(1, 4)
    ]

    class RegistryStub:
        def all(self) -> list[dict[str, object]]:
            return rows

    monkeypatch.setattr(mod, "SourceRegistry", RegistryStub)

    response = TestClient(app).get(
        "/api/commentary/recent?limit=1",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["source_id"] == "youtube_transcript:video-3:abc"


def test_recent_surfaces_registry_load_failure(monkeypatch) -> None:
    class RegistryStub:
        def all(self) -> list[dict[str, object]]:
            raise RuntimeError("bad json")

    monkeypatch.setattr(mod, "SourceRegistry", RegistryStub)

    response = TestClient(app).get(
        "/api/commentary/recent",
        headers=_auth_headers(),
    )

    assert response.status_code == 503
    assert "source registry unavailable" in response.json()["detail"]


def test_approval_update_preserves_approved_at_metadata(tmp_path: Path, monkeypatch) -> None:
    registry = SourceRegistry(tmp_path / "source_registry.jsonl")
    source_id = "youtube_transcript:video-a:111"
    registry.upsert(
        {
            "source_id": source_id,
            "source_type": "youtube_transcript",
            "source_name": "Video A",
            "review_status": "pending",
            "ingested_at": "2026-05-01T09:00:00Z",
        }
    )

    monkeypatch.setattr(mod, "SourceRegistry", lambda: registry)
    monkeypatch.setattr(mod, "_utc_now_iso", lambda: "2026-05-06T12:00:00+00:00")

    mod._update_source_registry(source_id, "approved")

    row = registry.get(source_id)
    assert row is not None
    assert row["review_status"] == "approved"
    assert row["approved_at"] == "2026-05-06T12:00:00+00:00"
