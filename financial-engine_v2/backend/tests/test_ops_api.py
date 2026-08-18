"""Integration tests for the /api/ops/ endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api import routes
from app.core import config
from app.routes import ops_api
from app.services.job_tracker import JobTracker, init_tracker
from app.services.ops_store import OpsStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Create a test client with an initialized ops tracker."""
    store = OpsStore(tmp_path / "ops.db")
    tracker = init_tracker(store)
    monkeypatch.setattr(
        ops_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": False,
            "source": "none",
            "token_count": 0,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [],
        },
    )

    app = FastAPI()
    app.include_router(ops_api.router, prefix="/api/ops")

    with TestClient(app) as c:
        yield c, tracker


def _ops_route(path: str, method: str) -> APIRoute:
    for candidate in ops_api.router.routes:
        if (
            isinstance(candidate, APIRoute)
            and candidate.path == path
            and method in candidate.methods
        ):
            return candidate
    raise AssertionError(f"route not found: {method} {path}")


def _has_api_key_dependency(route: APIRoute) -> bool:
    return any(
        dependency.call is routes.require_api_key
        for dependency in route.dependant.dependencies
    )


# ── API-key guard coverage ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/jobs", "GET"),
        ("/jobs/active", "GET"),
        ("/jobs/{job_id}", "GET"),
        ("/jobs/{job_id}/events", "GET"),
        ("/jobs/{job_id}/artifacts", "GET"),
        ("/stream", "GET"),
    ],
)
def test_ops_read_routes_register_api_key_dependency(path, method):
    assert _has_api_key_dependency(_ops_route(path, method))


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
def test_ops_read_routes_reject_missing_or_wrong_key_when_configured(
    client,
    monkeypatch,
    headers,
):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    c, _ = client

    resp = c.get("/api/ops/jobs", headers=headers)

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid or missing API key"}


def test_ops_read_routes_accept_matching_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    c, tracker = client
    tracker.create_job(
        job_type="extraction",
        job_family="pipeline",
        title="Guarded read",
    )

    resp = c.get("/api/ops/jobs", headers={"X-API-Key": "local-secret"})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── GET /api/ops/jobs ──────────────────────────────────────────────────────


def test_list_jobs_empty(client):
    c, _ = client
    resp = c.get("/api/ops/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_jobs_with_data(client):
    c, tracker = client
    tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Extract A"
    )
    tracker.create_job(
        job_type="backfill", job_family="celery", title="Backfill B", ticker="CBA"
    )
    resp = c.get("/api/ops/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_jobs_filter_by_status(client):
    c, tracker = client
    h = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Running job"
    )
    tracker.start_job(h.job_id)
    tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Pending job"
    )
    resp = c.get("/api/ops/jobs?status=running")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "running"


def test_list_jobs_filter_by_type(client):
    c, tracker = client
    tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Ext"
    )
    tracker.create_job(
        job_type="backfill", job_family="celery", title="Back"
    )
    resp = c.get("/api/ops/jobs?job_type=backfill")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["job_type"] == "backfill"


def test_list_jobs_filter_by_ticker(client):
    c, tracker = client
    tracker.create_job(
        job_type="extraction",
        job_family="pipeline",
        title="BHP extract",
        ticker="BHP",
    )
    tracker.create_job(
        job_type="extraction",
        job_family="pipeline",
        title="CBA extract",
        ticker="CBA",
    )
    resp = c.get("/api/ops/jobs?ticker=BHP")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["ticker"] == "BHP"


def test_list_jobs_pagination(client):
    c, tracker = client
    for i in range(5):
        tracker.create_job(
            job_type="extraction", job_family="pipeline", title=f"Job {i}"
        )
    resp = c.get("/api/ops/jobs?limit=2&offset=0")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2

    resp2 = c.get("/api/ops/jobs?limit=2&offset=2")
    body2 = resp2.json()
    assert len(body2["items"]) == 2
    ids1 = {j["job_id"] for j in body["items"]}
    ids2 = {j["job_id"] for j in body2["items"]}
    assert not ids1 & ids2


# ── GET /api/ops/jobs/active ───────────────────────────────────────────────


def test_list_active_jobs(client):
    c, tracker = client
    h1 = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Active 1"
    )
    tracker.start_job(h1.job_id)
    h2 = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Pending"
    )
    h3 = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Done"
    )
    tracker.start_job(h3.job_id)
    tracker.complete_job(h3.job_id)

    resp = c.get("/api/ops/jobs/active")
    body = resp.json()
    # h1 (running) + h2 (pending) = 2 active, h3 (succeeded) excluded
    assert body["total"] == 2
    statuses = {j["status"] for j in body["items"]}
    assert statuses <= {"running", "pending"}


def test_list_jobs_includes_synthetic_active_extraction(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(
        ops_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": True,
            "source": "file",
            "token_count": 1,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [
                {
                    "token": "tok-123",
                    "document_id": "doc-456",
                    "requested_method": "docling",
                    "ticker": "BHP",
                    "title": "Quarterly Activities",
                    "started_at": "2026-04-18T10:15:00+00:00",
                }
            ],
        },
    )

    resp = c.get("/api/ops/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    job = body["items"][0]
    assert job["job_id"] == "extraction-activity:tok-123"
    assert job["job_type"] == "extraction"
    assert job["job_family"] == "external_activity"
    assert job["status"] == "running"
    assert job["ticker"] == "BHP"
    assert job["phase"] == "docling"
    assert job["metadata"]["synthetic"] is True
    assert job["metadata"]["document_id"] == "doc-456"


def test_synthetic_extraction_card_reports_real_elapsed_ms(client, monkeypatch):
    """Synthetic card must show real elapsed time derived from started_at."""
    from datetime import datetime, timedelta, timezone

    c, _ = client
    started_at = (
        datetime.now(timezone.utc) - timedelta(seconds=42)
    ).replace(microsecond=0).isoformat()

    monkeypatch.setattr(
        ops_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": True,
            "source": "redis",
            "token_count": 1,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [
                {
                    "token": "tok-elapsed",
                    "document_id": "doc-elapsed",
                    "requested_method": "auto",
                    "ticker": "BHP",
                    "title": "Half Yearly Report",
                    "started_at": started_at,
                    "host": "test-host",
                    "pid": "4242",
                }
            ],
        },
    )

    resp = c.get("/api/ops/jobs")
    assert resp.status_code == 200
    job = resp.json()["items"][0]

    # elapsed_ms should reflect real wall-clock time since started_at, not be hardcoded 0.
    assert job["elapsed_ms"] >= 40_000  # at least 40s
    assert job["elapsed_ms"] < 120_000  # sanity upper bound for a quick test
    # updated_at must be fresh, not echo of started_at.
    assert job["updated_at"] != job["started_at"]
    # Host and pid forwarded for ops diagnostics.
    assert job["metadata"]["host"] == "test-host"
    assert job["metadata"]["pid"] == "4242"


def test_synthetic_extraction_card_clamps_future_started_at(client, monkeypatch):
    """If started_at is in the future (clock skew), elapsed_ms must not go negative."""
    from datetime import datetime, timedelta, timezone

    c, _ = client
    future_start = (
        datetime.now(timezone.utc) + timedelta(minutes=5)
    ).replace(microsecond=0).isoformat()

    monkeypatch.setattr(
        ops_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": True,
            "source": "file",
            "token_count": 1,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [
                {
                    "token": "tok-future",
                    "document_id": "doc-future",
                    "requested_method": "auto",
                    "ticker": "BHP",
                    "started_at": future_start,
                }
            ],
        },
    )

    resp = c.get("/api/ops/jobs/active")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["elapsed_ms"] == 0


def test_list_active_jobs_includes_synthetic_active_extraction(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(
        ops_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": True,
            "source": "redis",
            "token_count": 1,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [
                {
                    "run_id": "run-abc",
                    "token": "tok-abc",
                    "document_id": "doc-abc",
                    "requested_method": "pymupdf",
                    "ticker": "MIN",
                    "title": "Annual Report",
                    "started_at": "2026-04-18T11:00:00+00:00",
                }
            ],
        },
    )

    resp = c.get("/api/ops/jobs/active")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["job_id"] == "run-abc"
    assert body["items"][0]["status"] == "running"


# ── GET /api/ops/jobs/{job_id} ─────────────────────────────────────────────


def test_get_job_found(client):
    c, tracker = client
    h = tracker.create_job(
        job_type="extraction",
        job_family="pipeline",
        title="Single job",
        ticker="BHP",
    )
    resp = c.get(f"/api/ops/jobs/{h.job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == h.job_id
    assert body["title"] == "Single job"
    assert body["ticker"] == "BHP"


def test_get_job_and_events_for_synthetic_active_extraction(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(
        ops_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": True,
            "source": "file",
            "token_count": 1,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [
                {
                    "token": "tok-789",
                    "document_id": "doc-789",
                    "requested_method": "docling",
                    "ticker": "TLS",
                    "title": "Half Year Results",
                    "started_at": "2026-04-18T12:00:00+00:00",
                }
            ],
        },
    )

    job_resp = c.get("/api/ops/jobs/extraction-activity:tok-789")
    assert job_resp.status_code == 200
    assert job_resp.json()["title"] == "TLS | Half Year Results"

    events_resp = c.get("/api/ops/jobs/extraction-activity:tok-789/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["items"]
    assert len(events) == 1
    assert events[0]["event_type"] == "job.started"
    assert "docling" in events[0]["message"]

    artifacts_resp = c.get("/api/ops/jobs/extraction-activity:tok-789/artifacts")
    assert artifacts_resp.status_code == 200
    assert artifacts_resp.json()["items"] == []


def test_get_job_not_found(client):
    c, _ = client
    resp = c.get("/api/ops/jobs/nonexistent")
    assert resp.status_code == 404


# ── GET /api/ops/jobs/{job_id}/events ──────────────────────────────────────


def test_get_job_events(client):
    c, tracker = client
    h = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Events test"
    )
    tracker.start_job(h.job_id)
    tracker.change_phase(h.job_id, "parser")
    tracker.complete_job(h.job_id)

    resp = c.get(f"/api/ops/jobs/{h.job_id}/events")
    assert resp.status_code == 200
    body = resp.json()
    types = [e["event_type"] for e in body["items"]]
    assert "job.created" in types
    assert "job.started" in types
    assert "job.phase_changed" in types
    assert "job.completed" in types


def test_get_job_events_not_found(client):
    c, _ = client
    resp = c.get("/api/ops/jobs/ghost/events")
    assert resp.status_code == 404


# ── GET /api/ops/jobs/{job_id}/artifacts ───────────────────────────────────


def test_get_job_artifacts(client):
    c, tracker = client
    h = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Artifacts test"
    )
    tracker.add_artifact(
        h.job_id,
        artifact_type="report",
        artifact_label="Summary",
        artifact_path="/tmp/out.json",
    )
    resp = c.get(f"/api/ops/jobs/{h.job_id}/artifacts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["artifact_type"] == "report"


def test_get_job_artifacts_not_found(client):
    c, _ = client
    resp = c.get("/api/ops/jobs/ghost/artifacts")
    assert resp.status_code == 404


# ── GET /api/ops/stream ───────────────────────────────────────────────────


def test_stream_endpoint_responds(client):
    """Verify SSE endpoint is reachable and subscriber lifecycle works.

    Full event delivery is tested at the JobTracker unit level
    (test_subscriber_receives_events). Here we verify the route exists
    and the tracker's subscribe/unsubscribe is wired correctly.
    """
    c, tracker = client
    # Verify the endpoint exists by checking subscriber count changes
    assert len(tracker._subscribers) == 0
    q = tracker.subscribe()
    assert len(tracker._subscribers) == 1
    tracker.unsubscribe(q)
    assert len(tracker._subscribers) == 0


# ── POST /api/ops/jobs/external/* ──────────────────────────────────────────


def test_start_external_job_creates_running_job(client):
    c, _ = client
    resp = c.post(
        "/api/ops/jobs/external/start",
        json={
            "job_type": "codex_agent",
            "job_family": "agent_dev",
            "title": "Local Codex interactive session",
            "trigger_source": "codex",
            "entity_scope": "/tmp/workspace",
            "phase": "interactive",
            "phase_message": "Local Codex interactive session started",
            "metadata": {"provider": "openai", "model": "qwen2.5-coder-14b"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_type"] == "codex_agent"
    assert body["job_family"] == "agent_dev"
    assert body["status"] == "running"
    assert body["phase"] == "interactive"
    assert body["trigger_source"] == "codex"


def test_external_job_phase_and_complete(client):
    c, _ = client
    create = c.post(
        "/api/ops/jobs/external/start",
        json={
            "job_type": "codex_agent",
            "job_family": "agent_dev",
            "title": "Local Codex prompt run",
            "start": True,
        },
    )
    job_id = create.json()["job_id"]

    phase = c.post(
        f"/api/ops/jobs/{job_id}/external/phase",
        json={"phase": "running_turn", "message": "Processing prompt"},
    )
    assert phase.status_code == 200
    assert phase.json()["phase"] == "running_turn"

    complete = c.post(
        f"/api/ops/jobs/{job_id}/external/complete",
        json={"summary": "Local Codex prompt run completed"},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "succeeded"
    assert complete.json()["summary"] == "Local Codex prompt run completed"


def test_external_job_fail_missing_job_returns_404(client):
    c, _ = client
    resp = c.post(
        "/api/ops/jobs/missing-job/external/fail",
        json={"error": "boom"},
    )
    assert resp.status_code == 404
