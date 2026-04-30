"""Tests for /api/commentary/takeaways."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import commentary as mod


def _write_staged_points(tmp_path: Path, source_id: str, texts: list[str]) -> Path:
    staged_file = tmp_path / f"{source_id}.jsonl"
    rows = []
    for index, text in enumerate(texts):
        rows.append(
            {
                "id": f"pt-{index}",
                "vector": [0.1, 0.2],
                "payload": {
                    "source_id": source_id,
                    "chunk_id": f"{source_id}:{index}",
                    "chunk_index": index,
                    "text": text,
                    "source_name": "Test YouTube video",
                    "source_type": "youtube_transcript",
                    "published_at": "2026-04-28T00:00:00Z",
                },
            }
        )
    staged_file.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return staged_file


def test_takeaways_from_staged_chunks_without_memo(tmp_path, monkeypatch):
    source_id = "youtube_transcript:test-video:abc123"
    staged_file = _write_staged_points(
        tmp_path,
        source_id,
        [
            (
                "BHP reported stronger quarterly production and lower unit costs. "
                "Management said cash flow should improve if commodity prices remain firm."
            ),
            (
                "The speaker flagged debt reduction, valuation discipline, and project "
                "execution as important risks for investors to monitor."
            ),
        ],
    )
    monkeypatch.setattr(
        mod,
        "_load_index",
        lambda: {
            source_id: {
                "path": str(staged_file),
                "source_name": "Test YouTube video",
                "published_at": "2026-04-28T00:00:00Z",
            }
        },
    )
    monkeypatch.setattr(mod, "load_commentary_memos", lambda: [])

    result = mod.get_commentary_takeaways(
        mod.TakeawaysRequest(source_id=source_id, limit=3)
    )

    assert result["ok"] is True
    assert result["source_status"] == "staged"
    assert result["memo_status"] == "missing"
    assert result["takeaway_source"] == "chunks"
    assert len(result["takeaways"]) >= 2
    assert result["takeaways"][0]["citations"][0]["chunk_id"].startswith(source_id)
    assert result["watchlist_suggestions"] == []


def test_takeaways_http_route_returns_panel_contract(tmp_path, monkeypatch):
    from app.main import app

    source_id = "youtube_transcript:test-video:route123"
    staged_file = _write_staged_points(
        tmp_path,
        source_id,
        [
            (
                "The channel discussed revenue growth, margin pressure, and near-term "
                "valuation risk for investors watching the company."
            )
        ],
    )
    monkeypatch.setattr(
        mod,
        "_load_index",
        lambda: {source_id: {"path": str(staged_file), "source_name": "Route Video"}},
    )
    monkeypatch.setattr(mod, "load_commentary_memos", lambda: [])

    client = TestClient(app, raise_server_exceptions=True)
    response = client.post(
        "/api/commentary/takeaways",
        json={"source_id": source_id},
        headers={"X-API-Key": os.environ.get("LOCAL_API_KEY", "test-key")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == source_id
    assert body["takeaways"][0]["text"]
    assert body["takeaways"][0]["citations"][0]["chunk_id"] == f"{source_id}:0"
    assert body["watchlist_suggestions"] == []
    assert body["model"] == "deterministic:commentary-staged-chunks"
    assert body["prompt_version"] == "takeaways-v1-deterministic"


def test_takeaways_prefer_existing_memo_and_watchlist_suggestions(
    tmp_path,
    monkeypatch,
):
    source_id = "youtube_transcript:test-video:def456"
    staged_file = _write_staged_points(
        tmp_path,
        source_id,
        [
            (
                "BHP copper production improved in the quarter. Management expects "
                "stronger free cash flow, while lower iron ore prices remain a risk."
            )
        ],
    )
    memo = {
        "source_id": source_id,
        "claims": ["BHP copper production improved in the quarter"],
        "catalysts": ["Management expects stronger free cash flow"],
        "risks": ["Lower iron ore prices remain a risk"],
        "tickers": ["BHP", "ASX", "bad ticker"],
        "published_at": "2026-04-28T00:00:00Z",
    }
    monkeypatch.setattr(
        mod,
        "_load_index",
        lambda: {
            source_id: {
                "path": str(staged_file),
                "source_name": "Test YouTube video",
                "published_at": "2026-04-28T00:00:00Z",
            }
        },
    )
    monkeypatch.setattr(mod, "load_commentary_memos", lambda: [memo])

    result = mod.get_commentary_takeaways(
        mod.TakeawaysRequest(source_id=source_id, limit=3)
    )

    assert result["memo_status"] == "ready"
    assert result["takeaway_source"] == "memo"
    assert result["takeaways"][0]["text"].startswith("Claim:")
    assert result["takeaways"][0]["citations"][0]["chunk_id"] == f"{source_id}:0"
    assert result["watchlist_suggestions"] == [
        {
            "ticker": "BHP",
            "commentary": "Ticker mentioned in the extracted commentary memo.",
            "citations": [{"chunk_id": f"{source_id}:0", "segment_start_seconds": 0}],
        }
    ]


def test_takeaways_can_use_memo_without_staged_chunks(monkeypatch):
    source_id = "youtube_transcript:test-video:ghi789"
    monkeypatch.setattr(mod, "_load_index", lambda: {})
    monkeypatch.setattr(
        mod,
        "load_commentary_memos",
        lambda: [
            {
                "source_id": source_id,
                "claims": ["A memo-only claim remains available after staging cleanup"],
                "catalysts": [],
                "risks": [],
                "tickers": [],
            }
        ],
    )

    result = mod.get_commentary_takeaways(mod.TakeawaysRequest(source_id=source_id))

    assert result["source_status"] == "memo_only"
    assert result["takeaways"] == [
        {
            "text": "Claim: A memo-only claim remains available after staging cleanup",
            "citations": [],
            "source_field": "claims",
        }
    ]


def test_takeaways_unknown_source_raises_404(monkeypatch):
    monkeypatch.setattr(mod, "_load_index", lambda: {})
    monkeypatch.setattr(mod, "load_commentary_memos", lambda: [])

    with pytest.raises(HTTPException) as exc_info:
        mod.get_commentary_takeaways(mod.TakeawaysRequest(source_id="missing-src"))

    assert exc_info.value.status_code == 404


def test_takeaways_rejects_invalid_source_id():
    with pytest.raises(HTTPException) as exc_info:
        mod.get_commentary_takeaways(mod.TakeawaysRequest(source_id="../../bad"))

    assert exc_info.value.status_code == 400
