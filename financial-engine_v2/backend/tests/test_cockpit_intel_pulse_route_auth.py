from __future__ import annotations

from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.core.config as config
import app.main as main
from app.routes import cockpit_api


def _pulse_payload() -> dict[str, object]:
    return {
        "stats": {
            "document_count": 1,
            "extraction_count": 1,
            "signal_count": 0,
            "memory_count": 0,
            "population_index": 0.5,
            "trust_score_avg": 0.75,
            "quarantine_rate": 0.0,
        },
        "pipeline": [
            {
                "id": "documents",
                "label": "Documents",
                "health": 1.0,
                "status": "ok",
            }
        ],
        "failures": [],
    }


def _matrix_payload() -> dict[str, object]:
    return {
        "stage": "extraction",
        "entities": [
            {
                "entity": "BHP",
                "metrics": {"revenue": "populated"},
            }
        ],
    }


def test_pulse_rejects_missing_api_key_before_loading_service(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    get_instance = Mock(side_effect=AssertionError("service should not load"))
    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", get_instance)

    response = TestClient(main.app).get("/api/cockpit/pulse")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    get_instance.assert_not_called()


def test_matrix_rejects_missing_api_key_before_loading_service(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    get_instance = Mock(side_effect=AssertionError("service should not load"))
    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", get_instance)

    response = TestClient(main.app).get("/api/cockpit/matrix?stage=extraction")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    get_instance.assert_not_called()


def test_pulse_accepts_matching_api_key(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    service = Mock()
    service.get_intel_pulse_stats.return_value = _pulse_payload()
    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", Mock(return_value=service))

    response = TestClient(main.app).get(
        "/api/cockpit/pulse?ticker=bhp",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.json()["stats"]["document_count"] == 1
    service.get_intel_pulse_stats.assert_called_once_with("bhp")


def test_matrix_accepts_matching_api_key(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    service = Mock()
    service.get_diagnostic_matrix.return_value = _matrix_payload()
    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", Mock(return_value=service))

    response = TestClient(main.app).get(
        "/api/cockpit/matrix?stage=extraction&ticker=bhp",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.json()["entities"][0]["metrics"]["revenue"] == "populated"
    service.get_diagnostic_matrix.assert_called_once_with("extraction", "bhp")
