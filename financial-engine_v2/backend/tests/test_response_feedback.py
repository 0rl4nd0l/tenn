from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import cockpit_feedback
from app.routes.cockpit_feedback import router
from app.services.response_feedback import (
    MAX_REVIEW_JSON_CHARS,
    MAX_REVIEW_LIST_ITEMS,
    MAX_REVIEW_TEXT_CHARS,
    ResponseFeedbackStore,
)


def _client_with_store(store: ResponseFeedbackStore, monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    monkeypatch.setattr(cockpit_feedback, "get_response_feedback_store", lambda: store)
    return TestClient(app)


def test_response_feedback_endpoint_writes_to_separate_sqlite_store(tmp_path, monkeypatch) -> None:
    store_path = tmp_path / "review_feedback.sqlite"
    store = ResponseFeedbackStore(store_path)
    client = _client_with_store(store, monkeypatch)

    response = client.post(
        "/api/cockpit/feedback",
        json={
            "session_id": "session-a",
            "message_id": "msg-a",
            "parent_message_id": "msg-user-a",
            "user_label": "evidence_check_issue",
            "reason_code": "wrong_number",
            "note": "Number does not match source.",
            "query_text": "What did BHP report?",
            "final_answer_text": "BHP revenue was $10m.",
            "ticker": "bhp",
            "route_type": "api",
            "model_label": "model-a",
            "sources_present": True,
            "source_ids": ["doc-1:0"],
            "source_summary": [{"source_id": "doc-1:0", "title": "BHP results"}],
            "response_latency_ms": 1234,
            "document_ids": ["doc-1"],
            "verifier_result": {"ok": True, "evidence_count": 1},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["storage_path"] == str(store_path)

    row = store.get(payload["feedback_id"])
    assert row is not None
    assert row["session_id"] == "session-a"
    assert row["message_id"] == "msg-a"
    assert row["parent_message_id"] == "msg-user-a"
    assert row["reason_code"] == "wrong_number"
    assert row["ticker"] == "BHP"
    assert row["sources_present"] == 1
    assert json.loads(row["source_ids_json"]) == ["doc-1:0"]
    assert json.loads(row["document_ids_json"]) == ["doc-1"]
    assert json.loads(row["verifier_result_json"])["evidence_count"] == 1


def test_response_feedback_endpoint_rejects_invalid_reason_code(tmp_path, monkeypatch) -> None:
    client = _client_with_store(ResponseFeedbackStore(tmp_path / "review.sqlite"), monkeypatch)

    response = client.post(
        "/api/cockpit/feedback",
        json={
            "reason_code": "truth_audit",
            "final_answer_text": "BHP revenue was $10m.",
        },
    )

    assert response.status_code == 422


def test_response_feedback_endpoint_rejects_blank_answer_text(tmp_path, monkeypatch) -> None:
    client = _client_with_store(ResponseFeedbackStore(tmp_path / "review.sqlite"), monkeypatch)

    response = client.post(
        "/api/cockpit/feedback",
        json={
            "reason_code": "unsupported_claim",
            "final_answer_text": "   ",
        },
    )

    assert response.status_code == 400


def test_response_feedback_endpoint_rejects_oversized_answer_text(tmp_path, monkeypatch) -> None:
    client = _client_with_store(ResponseFeedbackStore(tmp_path / "review.sqlite"), monkeypatch)

    response = client.post(
        "/api/cockpit/feedback",
        json={
            "reason_code": "unsupported_claim",
            "final_answer_text": "x" * (MAX_REVIEW_TEXT_CHARS + 1),
        },
    )

    assert response.status_code == 422


def test_response_feedback_endpoint_rejects_too_many_source_ids(tmp_path, monkeypatch) -> None:
    client = _client_with_store(ResponseFeedbackStore(tmp_path / "review.sqlite"), monkeypatch)

    response = client.post(
        "/api/cockpit/feedback",
        json={
            "reason_code": "unsupported_claim",
            "final_answer_text": "BHP revenue was $10m.",
            "source_ids": [f"source-{index}" for index in range(MAX_REVIEW_LIST_ITEMS + 1)],
        },
    )

    assert response.status_code == 422


def test_response_feedback_endpoint_rejects_oversized_snapshot_json(tmp_path, monkeypatch) -> None:
    client = _client_with_store(ResponseFeedbackStore(tmp_path / "review.sqlite"), monkeypatch)

    response = client.post(
        "/api/cockpit/feedback",
        json={
            "reason_code": "unsupported_claim",
            "final_answer_text": "BHP revenue was $10m.",
            "verifier_result": {"blob": "x" * (MAX_REVIEW_JSON_CHARS + 1)},
        },
    )

    assert response.status_code == 400
    assert "verifier_result" in response.json()["detail"]
