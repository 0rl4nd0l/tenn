from __future__ import annotations

import json

import pytest
import httpx
import respx

from cockpit.integrations.backend_api import BackendApiClient


BASE = "http://127.0.0.1:8000"


@respx.mock
def test_ingest_url_success():
    respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "source_id": "youtube_transcript:my-video:abc123",
                "staged": True,
                "chunks_staged": 18,
                "chunks_indexed": 0,
                "video_title": "My Video",
                "channel": "My Channel",
            },
        )
    )
    client = BackendApiClient(BASE, api_key="test-key")
    result = client.ingest_url("https://youtu.be/abc123")
    assert result["ok"] is True
    assert result["chunks_staged"] == 18
    assert result["video_title"] == "My Video"
    assert json.loads(respx.calls.last.request.read()) == {
        "url": "https://youtu.be/abc123"
    }


@respx.mock
def test_ingest_url_422_raises():
    respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(422, json={"detail": "transcript unavailable"})
    )
    client = BackendApiClient(BASE, api_key="test-key")
    with pytest.raises(httpx.HTTPStatusError):
        client.ingest_url("https://youtu.be/abc123")


@respx.mock
def test_ingest_url_sends_api_key():
    route = respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = BackendApiClient(BASE, api_key="secret")
    client.ingest_url("https://youtu.be/abc123")
    assert route.calls[0].request.headers.get("x-api-key") == "secret"


@respx.mock
def test_ingest_url_sends_credibility_weight():
    route = respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = BackendApiClient(BASE, api_key="secret")
    client.ingest_url("https://youtu.be/abc123", credibility_weight=0.7)
    assert json.loads(route.calls[0].request.read()) == {
        "url": "https://youtu.be/abc123",
        "credibility_weight": 0.7,
    }


@respx.mock
def test_ingest_youtube_urls_success():
    route = respx.post(f"{BASE}/api/commentary/ingest-urls").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "count": 1,
                "results": [{"source_id": "youtube_transcript:test:abc123"}],
                "errors": [],
            },
        )
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.ingest_youtube_urls(
        ["https://youtu.be/abc123"],
        credibility_weight=0.65,
        takeaway_limit=3,
    )

    assert result["count"] == 1
    assert route.calls[0].request.headers.get("x-api-key") == "secret"
    assert json.loads(route.calls[0].request.read()) == {
        "urls": ["https://youtu.be/abc123"],
        "takeaway_limit": 3,
        "credibility_weight": 0.65,
    }


@respx.mock
def test_update_transcript_review_success():
    route = respx.patch(
        f"{BASE}/api/commentary/transcripts/youtube_transcript:test:abc123/review"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "source_id": "youtube_transcript:test:abc123",
                "credibility_weight": 0.7,
                "takeaways": [{"text": "Edited takeaway"}],
            },
        )
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.update_transcript_review(
        "youtube_transcript:test:abc123",
        credibility_weight=0.7,
        takeaways=["Edited takeaway"],
    )

    assert result["ok"] is True
    assert route.calls[0].request.headers.get("x-api-key") == "secret"
    assert json.loads(route.calls[0].request.read()) == {
        "credibility_weight": 0.7,
        "takeaways": ["Edited takeaway"],
    }


@respx.mock
def test_ingest_url_no_api_key_omits_header():
    route = respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = BackendApiClient(BASE)  # no api_key
    client.ingest_url("https://youtu.be/abc123")
    assert "x-api-key" not in route.calls[0].request.headers


@respx.mock
def test_add_watched_channel_success():
    route = respx.post(f"{BASE}/api/commentary/channels").mock(
        return_value=httpx.Response(
            200,
            json={
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "enabled": True,
                "credibility_weight": 0.55,
                "already_existed": False,
            },
        )
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.add_watched_channel("Kneppy Invests")

    assert result["channel_id"] == "UCabc123"
    request = route.calls[0].request
    assert request.headers.get("x-api-key") == "secret"
    assert json.loads(request.read()) == {
        "name_or_id": "Kneppy Invests",
        "credibility_weight": 0.55,
        "enabled": True,
    }


@respx.mock
def test_add_watched_channel_raises_backend_detail():
    respx.post(f"{BASE}/api/commentary/channels").mock(
        return_value=httpx.Response(
            502,
            json={"detail": "channel lookup failed for 'Kneppy Invests'"},
        )
    )
    client = BackendApiClient(BASE)

    with pytest.raises(RuntimeError, match="channel lookup failed"):
        client.add_watched_channel("Kneppy Invests")


@respx.mock
def test_get_youtube_channel_recent_videos_success():
    route = respx.post(f"{BASE}/api/commentary/channels/recent-videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "videos": [{"position": 1, "title": "Latest video"}],
            },
        )
    )
    client = BackendApiClient(BASE, api_key="secret")

    result = client.get_youtube_channel_recent_videos("Kneppy Invests", limit=3)

    assert result["channel_id"] == "UCabc123"
    request = route.calls[0].request
    assert request.headers.get("x-api-key") == "secret"
    assert json.loads(request.read()) == {
        "name_or_id": "Kneppy Invests",
        "limit": 3,
    }


@respx.mock
def test_get_youtube_channel_recent_videos_raises_backend_detail():
    respx.post(f"{BASE}/api/commentary/channels/recent-videos").mock(
        return_value=httpx.Response(
            502,
            json={"detail": "channel lookup failed"},
        )
    )
    client = BackendApiClient(BASE)

    with pytest.raises(RuntimeError, match="channel lookup failed"):
        client.get_youtube_channel_recent_videos("missing")
