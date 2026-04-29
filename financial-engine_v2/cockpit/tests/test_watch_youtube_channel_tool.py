"""Tests for watch_youtube_channel tool execution."""
from unittest.mock import MagicMock

from cockpit.core.tool_executor import ToolExecutor


def _make_executor(
    backend_response: dict | None = None, raises: Exception | None = None
):
    router = MagicMock()
    router.backend_api_client = MagicMock()
    if raises:
        router.backend_api_client.add_watched_channel.side_effect = raises
    else:
        router.backend_api_client.add_watched_channel.return_value = (
            backend_response
            or {
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "enabled": True,
                "credibility_weight": 0.55,
                "already_existed": False,
            }
        )
    action_registry = MagicMock()
    return ToolExecutor(tool_router=router, action_registry=action_registry)


class TestWatchYoutubeChannelTool:
    def test_successful_add(self):
        executor = _make_executor()
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        assert result["ok"] is True
        assert result["channel_id"] == "UCabc123"
        assert result["name"] == "Kneppy Invests"
        assert result["already_existed"] is False

    def test_with_credibility_weight(self):
        executor = _make_executor()
        executor.execute(
            "watch_youtube_channel",
            {"channel_name": "@KneppyInvests", "credibility_weight": 0.7},
        )
        executor._router.backend_api_client.add_watched_channel.assert_called_once_with(
            "@KneppyInvests", credibility_weight=0.7
        )

    def test_missing_channel_name_returns_error(self):
        executor = _make_executor()
        result = executor.execute("watch_youtube_channel", {})
        assert result["ok"] is False
        assert "channel_name" in result["error"]

    def test_backend_unavailable_returns_error(self):
        router = MagicMock()
        router.backend_api_client = None
        executor = ToolExecutor(tool_router=router, action_registry=MagicMock())
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        assert result["ok"] is False
        assert "backend" in result["error"].lower()

    def test_backend_api_error_returns_error(self):
        executor = _make_executor(raises=RuntimeError("channel lookup failed"))
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "nonexistent xyz 99999"}
        )
        assert result["ok"] is False
        assert "channel lookup failed" in result["error"]

    def test_already_existed_true(self):
        executor = _make_executor(
            backend_response={
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "enabled": True,
                "credibility_weight": 0.55,
                "already_existed": True,
            }
        )
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        assert result["ok"] is True
        assert result["already_existed"] is True
