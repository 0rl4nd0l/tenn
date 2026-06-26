from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.routes import cockpit_api
from app.routes.cockpit_api import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    return TestClient(app, raise_server_exceptions=False)


class _FakeIntelPulseService:
    def __init__(self) -> None:
        self.pulse_ticker: str | None = None
        self.matrix_args: tuple[str, str | None] | None = None

    def get_intel_pulse_stats(self, ticker: str | None):
        self.pulse_ticker = ticker
        return cockpit_api.IntelPulseResponse(
            stats=cockpit_api.IntelPulseStats(document_count=2, extraction_count=1),
            pipeline=[
                cockpit_api.IntelPulseStageHealth(
                    id="extraction",
                    label="Extraction",
                    health=0.9,
                    status="healthy",
                )
            ],
            failures=[],
        )

    def get_diagnostic_matrix(self, stage: str, ticker: str | None):
        self.matrix_args = (stage, ticker)
        return cockpit_api.IntelPulseMatrixResponse(
            stage=stage,
            entities=[
                cockpit_api.IntelPulseEntityMetric(
                    entity=ticker or "ALL",
                    metrics={"revenue": "populated"},
                )
            ],
        )


def test_intel_pulse_denies_missing_api_key_before_service_call(monkeypatch):
    monkeypatch.setattr(api_routes.settings, "local_api_key", "local-secret", raising=False)

    def fail_if_called():
        raise AssertionError("CockpitService must not be opened before API-key auth")

    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", fail_if_called)

    response = _client().get("/api/cockpit/pulse?ticker=BHP")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_intel_matrix_denies_missing_api_key_before_service_call(monkeypatch):
    monkeypatch.setattr(api_routes.settings, "local_api_key", "local-secret", raising=False)

    def fail_if_called():
        raise AssertionError("CockpitService must not be opened before API-key auth")

    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", fail_if_called)

    response = _client().get("/api/cockpit/matrix?stage=extraction&ticker=BHP")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_intel_pulse_accepts_api_key_and_returns_payload(monkeypatch):
    monkeypatch.setattr(api_routes.settings, "local_api_key", "local-secret", raising=False)
    service = _FakeIntelPulseService()
    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", lambda: service)

    response = _client().get("/api/cockpit/pulse?ticker=BHP", headers={"X-API-Key": "local-secret"})

    assert response.status_code == 200
    assert service.pulse_ticker == "BHP"
    assert response.json() == {
        "stats": {
            "document_count": 2,
            "extraction_count": 1,
            "signal_count": 0,
            "memory_count": 0,
            "population_index": 0.0,
            "trust_score_avg": 0.0,
            "quarantine_rate": 0.0,
        },
        "pipeline": [
            {
                "id": "extraction",
                "label": "Extraction",
                "health": 0.9,
                "status": "healthy",
            }
        ],
        "failures": [],
    }


def test_intel_matrix_accepts_api_key_and_returns_payload(monkeypatch):
    monkeypatch.setattr(api_routes.settings, "local_api_key", "local-secret", raising=False)
    service = _FakeIntelPulseService()
    monkeypatch.setattr(cockpit_api.CockpitService, "get_instance", lambda: service)

    response = _client().get(
        "/api/cockpit/matrix?stage=extraction&ticker=BHP",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert service.matrix_args == ("extraction", "BHP")
    assert response.json() == {
        "stage": "extraction",
        "entities": [
            {
                "entity": "BHP",
                "metrics": {"revenue": "populated"},
            }
        ],
    }
