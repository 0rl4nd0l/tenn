from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


def test_process_document_api_passes_method_and_strict_flag(monkeypatch):
    captured: dict[str, object] = {}

    def fake_process_document(document_id: str, **kwargs):
        captured["document_id"] = document_id
        captured.update(kwargs)
        return {
            "ok": True,
            "run_id": "run-123",
            "extraction_status": "ok",
            "method_provenance": {
                "requested_method": kwargs.get("requested_method"),
                "strict_method": kwargs.get("strict_method"),
            },
        }

    monkeypatch.setattr("app.services.pipeline.process_document", fake_process_document)
    client = TestClient(app)

    response = client.post(
        "/api/process/document/doc-123",
        json={"method": "docling", "strict_method": True},
    )

    assert response.status_code == 200
    assert captured == {
        "document_id": "doc-123",
        "requested_method": "docling",
        "strict_method": True,
    }
    assert response.json()["method_provenance"]["requested_method"] == "docling"
