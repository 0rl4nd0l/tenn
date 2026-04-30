from __future__ import annotations

import json
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


@respx.mock
def test_start_action_job_posts_wait_false_and_api_key() -> None:
    route = respx.post(f"{BASE}/api/cockpit/action/execute").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "job_id": "job-123", "queued": True, "status": "queued"},
        )
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.start_action_job(
        "daily_news_ingest",
        {"tickers": "BHP"},
        session_id="global-main",
    )

    assert result["job_id"] == "job-123"
    request = route.calls[0].request
    assert request.headers.get("x-api-key") == "secret"
    assert request.content
    assert json.loads(request.content.decode("utf-8")) == {
        "action_id": "daily_news_ingest",
        "args": {"tickers": "BHP"},
        "wait": False,
        "session_id": "global-main",
    }


@respx.mock
def test_get_action_job_sends_tail_query_param() -> None:
    route = respx.get(f"{BASE}/api/cockpit/action/jobs/job-123").mock(
        return_value=httpx.Response(200, json={"job_id": "job-123", "status": "running"})
    )
    client = BackendApiClient(BASE)

    result = client.get_action_job("job-123", tail=25)

    assert result == {"job_id": "job-123", "status": "running"}
    request = route.calls[0].request
    assert str(request.url.copy_with(query=None)) == f"{BASE}/api/cockpit/action/jobs/job-123"
    assert dict(request.url.params) == {"tail": "25"}


@respx.mock
def test_stop_action_job_posts_stop_endpoint() -> None:
    route = respx.post(f"{BASE}/api/cockpit/action/jobs/job-123/stop").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "job-123", "status": "cancelling"})
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.stop_action_job("job-123")

    assert result["status"] == "cancelling"
    request = route.calls[0].request
    assert request.headers.get("x-api-key") == "secret"
    assert str(request.url) == f"{BASE}/api/cockpit/action/jobs/job-123/stop"


@respx.mock
def test_queue_action_job_posts_wait_false_payload() -> None:
    route = respx.post(f"{BASE}/api/cockpit/action/execute").mock(
        return_value=httpx.Response(200, json={"queued": True, "job_id": "job-1"})
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.queue_action_job(
        "daily_news_ingest",
        {"tickers": "BHP"},
        session_id="session-1",
    )

    assert result == {"queued": True, "job_id": "job-1"}
    request = route.calls[0].request
    assert str(request.url) == f"{BASE}/api/cockpit/action/execute"
    assert request.headers.get("x-api-key") == "secret"
    assert json.loads(request.content.decode("utf-8")) == {
        "action_id": "daily_news_ingest",
        "args": {"tickers": "BHP"},
        "wait": False,
        "session_id": "session-1",
    }


@respx.mock
def test_get_action_job_uses_tail_param() -> None:
    route = respx.get(f"{BASE}/api/cockpit/action/jobs/job-123").mock(
        return_value=httpx.Response(200, json={"job_id": "job-123", "status": "running"})
    )
    client = BackendApiClient(BASE)

    result = client.get_action_job("job-123", tail=5)

    assert result == {"job_id": "job-123", "status": "running"}
    request = route.calls[0].request
    assert str(request.url.copy_with(query=None)) == f"{BASE}/api/cockpit/action/jobs/job-123"
    assert dict(request.url.params) == {"tail": "5"}


@respx.mock
def test_stop_action_job_posts_stop_route() -> None:
    route = respx.post(f"{BASE}/api/cockpit/action/jobs/job-123/stop").mock(
        return_value=httpx.Response(200, json={"status": "stopping"})
    )
    client = BackendApiClient(BASE)

    result = client.stop_action_job("job-123")

    assert result == {"status": "stopping"}
    request = route.calls[0].request
    assert str(request.url) == f"{BASE}/api/cockpit/action/jobs/job-123/stop"


@respx.mock
def test_list_cockpit_holdings_passes_ticker_and_include_archived() -> None:
    route = respx.get(f"{BASE}/api/cockpit/holdings").mock(
        return_value=httpx.Response(200, json={"items": [{"ticker": "BHP"}]})
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.list_cockpit_holdings(
        ticker=" bhp ",
        include_archived=True,
    )

    assert result == {"items": [{"ticker": "BHP"}]}
    request = route.calls[0].request
    assert str(request.url.copy_with(query=None)) == f"{BASE}/api/cockpit/holdings"
    assert dict(request.url.params) == {"ticker": "BHP", "include_archived": "true"}
    assert request.headers.get("x-api-key") == "secret"


@respx.mock
def test_list_cockpit_holdings_defaults_include_archived_false() -> None:
    route = respx.get(f"{BASE}/api/cockpit/holdings").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    client = BackendApiClient(BASE)

    result = client.list_cockpit_holdings()

    assert result == {"items": []}
    request = route.calls[0].request
    assert dict(request.url.params) == {"include_archived": "false"}
