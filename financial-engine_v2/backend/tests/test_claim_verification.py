from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app.core.config as config
from app.routes.cockpit_claims import router
from app.services.claim_verification import verify_claims_against_evidence


def test_claim_verification_marks_supported_from_visible_source() -> None:
    result = verify_claims_against_evidence(
        answer_text="BHP revenue was $10m.",
        visible_sources=[
            {
                "source_id": "doc-1:0",
                "title": "BHP results",
                "snippet": "BHP revenue was $10m.",
            }
        ],
    )

    assert result["evidence_count"] == 1
    verdict = result["verdicts"][0]
    assert verdict["verdict"] == "supported"
    assert verdict["supporting_source_ids"] == ["doc-1:0"]


def test_claim_verification_prefers_insufficient_when_evidence_missing() -> None:
    result = verify_claims_against_evidence(
        answer_text="BHP revenue was $10m.",
        visible_sources=[],
    )

    verdict = result["verdicts"][0]
    assert verdict["verdict"] == "insufficient_evidence"
    assert verdict["supporting_source_ids"] == []


def test_claim_verification_detects_bounded_numeric_contradiction() -> None:
    result = verify_claims_against_evidence(
        answer_text="BHP revenue was $10m.",
        visible_sources=[
            {
                "source_id": "doc-2:0",
                "title": "BHP results",
                "snippet": "BHP revenue was $12m.",
            }
        ],
    )

    verdict = result["verdicts"][0]
    assert verdict["verdict"] == "contradicted"
    assert verdict["contradicting_source_ids"] == ["doc-2:0"]


def test_claim_verification_detects_contradiction_when_year_matches() -> None:
    result = verify_claims_against_evidence(
        answer_text="BHP FY2024 revenue was $10m.",
        visible_sources=[
            {
                "source_id": "doc-2:0",
                "title": "BHP FY2024 results",
                "snippet": "BHP FY2024 revenue was $12m.",
            }
        ],
    )

    verdict = result["verdicts"][0]
    assert verdict["verdict"] == "contradicted"
    assert verdict["contradicting_source_ids"] == ["doc-2:0"]


def test_claim_verification_marks_forward_looking_claim_not_checkable() -> None:
    result = verify_claims_against_evidence(
        answer_text="BHP will outperform the ASX next quarter.",
        visible_sources=[
            {
                "source_id": "doc-3:0",
                "title": "BHP price data",
                "snippet": "BHP last close was $42.00.",
            }
        ],
    )

    verdict = result["verdicts"][0]
    assert verdict["verdict"] == "not_checkable"
    assert verdict["uncheckable_reason"] == "subjective_or_forward_looking"


def test_claim_verification_does_not_treat_month_may_as_modal() -> None:
    result = verify_claims_against_evidence(
        answer_text="BHP reported revenue in May 2024.",
        visible_sources=[
            {
                "source_id": "doc-4:0",
                "title": "BHP May 2024 update",
                "snippet": "BHP reported revenue in May 2024.",
            }
        ],
    )

    verdict = result["verdicts"][0]
    assert verdict["verdict"] == "supported"


def test_claim_verification_endpoint_rejects_missing_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/claims/verify",
        json={
            "assistant_text": "BHP revenue was $10m.",
            "visible_sources": [
                {
                    "source_id": "doc-1:0",
                    "title": "BHP results",
                    "snippet": "BHP revenue was $10m.",
                }
            ],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_claim_verification_endpoint_rejects_wrong_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/claims/verify",
        headers={"X-API-Key": "wrong-secret"},
        json={
            "assistant_text": "BHP revenue was $10m.",
            "visible_sources": [
                {
                    "source_id": "doc-1:0",
                    "title": "BHP results",
                    "snippet": "BHP revenue was $10m.",
                }
            ],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_claim_verification_endpoint_returns_structured_verdicts(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/claims/verify",
        headers={"X-API-Key": "local-secret"},
        json={
            "session_id": "session-a",
            "message_id": "msg-a",
            "assistant_text": "BHP revenue was $10m.",
            "visible_sources": [
                {
                    "source_id": "doc-1:0",
                    "title": "BHP results",
                    "snippet": "BHP revenue was $10m.",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-a"
    assert payload["message_id"] == "msg-a"
    assert payload["evidence_scope"] == "visible_sources"
    assert payload["verdicts"][0]["verdict"] == "supported"


def test_claim_verification_endpoint_rejects_empty_assistant_text(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/claims/verify",
        headers={"X-API-Key": "local-secret"},
        json={"assistant_text": "   "},
    )

    assert response.status_code == 400
