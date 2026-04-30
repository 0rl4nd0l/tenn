"""Tests for POST/GET /api/commentary/channels endpoints."""
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient


def _make_client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=True)


def _auth_headers():
    import os
    key = os.environ.get("LOCAL_API_KEY", "test-key")
    return {"X-API-Key": key}


class TestAddChannelEndpoint:
    def test_add_new_channel(self):
        client = _make_client()
        with (
            patch(
                "app.api.commentary.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.api.commentary.ChannelRegistry") as MockReg,
        ):
            instance = MockReg.return_value
            instance.channels.return_value = []
            instance.save.return_value = None

            resp = client.post(
                "/api/commentary/channels",
                json={"name_or_id": "Kneppy Invests", "credibility_weight": 0.6},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["channel_id"] == "UCabc123"
        assert body["name"] == "Kneppy Invests"
        assert body["enabled"] is True
        assert body["already_existed"] is False

    def test_add_already_existing_channel(self):
        from app.services.channel_registry import ChannelConfig
        client = _make_client()
        existing = [
            ChannelConfig(
                name="Kneppy Invests",
                channel_id="UCabc123",
                enabled=False,
                credibility_weight=0.7,
            )
        ]

        with (
            patch(
                "app.api.commentary.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.api.commentary.ChannelRegistry") as MockReg,
        ):
            instance = MockReg.return_value
            instance.channels.return_value = existing
            instance.save.return_value = None

            resp = client.post(
                "/api/commentary/channels",
                json={"name_or_id": "UCabc123"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["already_existed"] is True
        assert body["enabled"] is False
        assert body["credibility_weight"] == 0.7
        instance.save.assert_not_called()

    def test_missing_name_returns_422(self):
        client = _make_client()
        resp = client.post(
            "/api/commentary/channels",
            json={},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_credibility_weight_must_be_in_range(self):
        client = _make_client()
        resp = client.post(
            "/api/commentary/channels",
            json={"name_or_id": "Kneppy Invests", "credibility_weight": 1.5},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_resolve_failure_returns_502(self):
        client = _make_client()
        with patch(
            "app.api.commentary.resolve_channel_id",
            side_effect=RuntimeError("channel lookup failed"),
        ):
            resp = client.post(
                "/api/commentary/channels",
                json={"name_or_id": "nonexistent xyz channel 99999"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 502
        assert resp.json()["detail"]["error"] == "youtube_channel_lookup_failed"
        assert "YouTube channel URL" in resp.json()["detail"]["suggestion"]

    def test_list_channels(self):
        from app.services.channel_registry import ChannelConfig
        client = _make_client()
        channels = [
            ChannelConfig(name="Kneppy Invests", channel_id="UCabc123", enabled=True),
            ChannelConfig(name="Other Channel", channel_id="UCdef456", enabled=False),
        ]
        with patch("app.api.commentary.ChannelRegistry") as MockReg:
            MockReg.return_value.channels.return_value = channels
            resp = client.get("/api/commentary/channels", headers=_auth_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["channels"]) == 2
        assert body["channels"][0]["channel_id"] == "UCabc123"

    def test_recent_videos_preview(self):
        client = _make_client()
        with patch(
            "app.api.commentary.list_recent_channel_videos",
            return_value={
                "ok": True,
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "limit": 2,
                "videos": [
                    {
                        "position": 1,
                        "video_id": "vid123",
                        "title": "BHP quarterly results breakdown",
                        "published_at": "2026-04-28T00:00:00Z",
                        "webpage_url": "https://www.youtube.com/watch?v=vid123",
                        "duration_seconds": 1200,
                        "scores": {"overall": 0.91},
                    }
                ],
            },
        ) as preview:
            resp = client.post(
                "/api/commentary/channels/recent-videos",
                json={"name_or_id": "Kneppy Invests", "limit": 2},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["channel_id"] == "UCabc123"
        assert body["videos"][0]["position"] == 1
        preview.assert_called_once_with("Kneppy Invests", limit=2)

    def test_recent_videos_resolve_failure_returns_502(self):
        client = _make_client()
        with patch(
            "app.api.commentary.list_recent_channel_videos",
            side_effect=RuntimeError("channel lookup failed"),
        ):
            resp = client.post(
                "/api/commentary/channels/recent-videos",
                json={"name_or_id": "missing channel"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 502
        assert resp.json()["detail"]["error"] == "youtube_channel_lookup_failed"

    def test_recent_videos_limit_must_be_in_range(self):
        client = _make_client()
        resp = client.post(
            "/api/commentary/channels/recent-videos",
            json={"name_or_id": "Kneppy Invests", "limit": 99},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422
