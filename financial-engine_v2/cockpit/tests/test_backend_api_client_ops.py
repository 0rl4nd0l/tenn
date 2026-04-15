from __future__ import annotations

import httpx
import respx

from cockpit.integrations.backend_api import BackendApiClient


BASE = "http://127.0.0.1:8000"


@respx.mock
def test_list_ops_jobs_builds_query_and_sends_api_key() -> None:
    route = respx.get(f"{BASE}/api/ops/jobs").mock(
        return_value=httpx.Response(200, json={"items": [{"job_id": "job-1"}], "total": 1})
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.list_ops_jobs(
        status="running,pending",
        job_type="ingest",
        ticker="abc",
        limit=25,
        offset=10,
    )

    assert result == {"items": [{"job_id": "job-1"}], "total": 1}
    request = route.calls[0].request
    assert str(request.url.copy_with(query=None)) == f"{BASE}/api/ops/jobs"
    assert dict(request.url.params) == {
        "status": "running,pending",
        "job_type": "ingest",
        "ticker": "ABC",
        "limit": "25",
        "offset": "10",
    }
    assert request.headers.get("x-api-key") == "secret"


@respx.mock
def test_list_active_ops_jobs_uses_active_endpoint() -> None:
    route = respx.get(f"{BASE}/api/ops/jobs/active").mock(
        return_value=httpx.Response(200, json={"items": [], "total": 0})
    )
    client = BackendApiClient(BASE)

    result = client.list_active_ops_jobs()

    assert result == {"items": [], "total": 0}
    request = route.calls[0].request
    assert str(request.url) == f"{BASE}/api/ops/jobs/active"
    assert "x-api-key" not in request.headers


@respx.mock
def test_get_ops_job_uses_job_id_path() -> None:
    route = respx.get(f"{BASE}/api/ops/jobs/job-123").mock(
        return_value=httpx.Response(200, json={"job_id": "job-123", "status": "running"})
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.get_ops_job(" job-123 ")

    assert result == {"job_id": "job-123", "status": "running"}
    request = route.calls[0].request
    assert str(request.url) == f"{BASE}/api/ops/jobs/job-123"
    assert request.headers.get("x-api-key") == "secret"


@respx.mock
def test_get_ops_job_events_includes_limit_param() -> None:
    route = respx.get(f"{BASE}/api/ops/jobs/job-123/events").mock(
        return_value=httpx.Response(200, json={"items": [{"event_id": "evt-1"}]})
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.get_ops_job_events("job-123", limit=77)

    assert result == {"items": [{"event_id": "evt-1"}]}
    request = route.calls[0].request
    assert str(request.url.copy_with(query=None)) == f"{BASE}/api/ops/jobs/job-123/events"
    assert dict(request.url.params) == {"limit": "77"}
    assert request.headers.get("x-api-key") == "secret"


@respx.mock
def test_get_ops_job_artifacts_returns_empty_payload_for_empty_response() -> None:
    route = respx.get(f"{BASE}/api/ops/jobs/job-123/artifacts").mock(
        return_value=httpx.Response(200, content=b"")
    )
    client = BackendApiClient(BASE)

    result = client.get_ops_job_artifacts("job-123")

    assert result == {}
    request = route.calls[0].request
    assert str(request.url) == f"{BASE}/api/ops/jobs/job-123/artifacts"
