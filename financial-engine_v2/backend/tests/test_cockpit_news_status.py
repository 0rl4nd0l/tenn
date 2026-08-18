from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.news_health_status import build_a2m_news_health_status


def _payload_text(payload: object) -> str:
    return repr(payload)


def test_a2m_news_health_status_preserves_split_truth_without_live_probes(tmp_path) -> None:
    payload = build_a2m_news_health_status(workspace_root=tmp_path)

    assert payload["live_probe_performed"] is False
    assert payload["a2m_news_health"] == {
        "qdrant_retrieval": "ok",
        "canonical_sqlite_projection": "missing",
        "legacy_sqlite_projection": "evidence_present_not_current_consumer",
        "cockpit_query_route": "ok_via_rag_query",
        "cockpit_status_routes": "implemented",
        "chat_synthesis": "DATA_MISSING",
        "projection_repair": "not_run",
    }
    assert payload["qdrant_retrieval"]["live_qdrant_probe_performed"] is False
    assert payload["legacy_sqlite_projection"]["live_legacy_db_read_performed"] is False
    assert payload["chat_synthesis"]["status"] == "DATA_MISSING"
    assert payload["projection_repair"] == {
        "status": "not_run",
        "forbidden_here": True,
    }
    assert "A2M missing" in payload["reporting_contract"]["do_not_report"]


def test_default_news_health_status_redacts_operator_diagnostics(tmp_path) -> None:
    payload = build_a2m_news_health_status(workspace_root=tmp_path)
    payload_text = _payload_text(payload)

    assert payload["news_artifact_root"] == {
        "status": "redacted",
        "source": "workspace_root_argument",
    }
    assert payload["canonical_sqlite_projection_paths"] == {
        "status": "redacted",
        "reason": "operator_diagnostics_only",
    }
    assert payload["evidence_reports"] == {
        "status": "redacted",
        "reason": "operator_diagnostics_only",
    }
    assert "collection" not in payload["qdrant_retrieval"]
    assert "absolute_path" not in payload_text
    assert "/mnt" not in payload_text
    assert str(tmp_path) not in payload_text
    assert "reports/agent_jobs" not in payload_text


def test_news_health_status_diagnostics_require_explicit_opt_in(tmp_path) -> None:
    payload = build_a2m_news_health_status(
        workspace_root=tmp_path,
        include_diagnostics=True,
    )

    assert payload["news_artifact_root"]["path"] == str(tmp_path / "reports" / "qual_context")
    assert payload["canonical_sqlite_projection_paths"][0]["absolute_path"]
    assert payload["qdrant_retrieval"]["collection"] == "news_chunks"
    assert payload["evidence_reports"]["a2m_readonly_smoke"]["path"].startswith(
        "reports/agent_jobs/"
    )


def test_cockpit_news_status_route_exposes_contract_and_keeps_news_status_absent() -> None:
    client = TestClient(app)

    response = client.get("/api/cockpit/news/status")
    payload = response.json()
    payload_text = _payload_text(payload)

    assert response.status_code == 200
    assert payload["a2m_news_health"]["qdrant_retrieval"] == "ok"
    assert payload["a2m_news_health"]["canonical_sqlite_projection"] in {
        "missing",
        "partial",
        "present",
    }
    assert (
        payload["a2m_news_health"]["legacy_sqlite_projection"]
        == "evidence_present_not_current_consumer"
    )
    assert payload["a2m_news_health"]["cockpit_query_route"] == "ok_via_rag_query"
    assert payload["a2m_news_health"]["cockpit_status_routes"] == "implemented"
    assert payload["a2m_news_health"]["chat_synthesis"] == "DATA_MISSING"
    assert payload["a2m_news_health"]["projection_repair"] == "not_run"
    assert payload["routes"]["backend_api_cockpit_news_status"]["status"] == "implemented"
    assert (
        payload["routes"]["backend_api_news_status"]["status"]
        == "intentionally_absent_in_current_profile"
    )
    assert payload["news_artifact_root"]["status"] == "redacted"
    assert payload["canonical_sqlite_projection_paths"]["status"] == "redacted"
    assert payload["evidence_reports"]["status"] == "redacted"
    assert "collection" not in payload["qdrant_retrieval"]
    assert "absolute_path" not in payload_text
    assert "/mnt" not in payload_text
    assert "reports/agent_jobs" not in payload_text

    assert client.get("/api/news/status").status_code == 404
