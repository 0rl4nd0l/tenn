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
    router.backend_api_client.get_youtube_channel_recent_videos.return_value = {
        "ok": True,
        "channel_id": "UCabc123",
        "name": "Kneppy Invests",
        "videos": [
            {
                "position": 1,
                "title": "BHP quarterly results breakdown",
                "published_at": "2026-04-28T00:00:00Z",
                "webpage_url": "https://www.youtube.com/watch?v=abc123",
                "scores": {"overall": 0.91},
            }
        ],
    }
    router.backend_api_client.ingest_youtube_urls.return_value = {
        "ok": True,
        "count": 1,
        "error_count": 0,
        "results": [
            {
                "source_id": "youtube_transcript:test:abc123",
                "video_title": "BHP quarterly results breakdown",
                "webpage_url": "https://www.youtube.com/watch?v=abc123",
                "staged": True,
                "chunks_staged": 3,
                "takeaways": [{"text": "BHP takeaway"}],
            }
        ],
        "errors": [],
    }
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

    def test_invalid_credibility_weight_returns_error(self):
        executor = _make_executor()
        result = executor.execute(
            "watch_youtube_channel",
            {"channel_name": "Kneppy Invests", "credibility_weight": 1.5},
        )
        assert result["ok"] is False
        assert "credibility_weight" in result["error"]
        executor._router.backend_api_client.add_watched_channel.assert_not_called()

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


class TestCheckYoutubeChannelRecentVideosTool:
    def test_successful_recent_video_preview(self):
        executor = _make_executor()

        result = executor.execute(
            "check_youtube_channel_recent_videos",
            {"channel_name": "Kneppy Invests", "limit": 3},
        )

        assert result["ok"] is True
        assert result["channel_id"] == "UCabc123"
        assert result["count"] == 1
        executor._router.backend_api_client.get_youtube_channel_recent_videos.assert_called_once_with(
            "Kneppy Invests",
            limit=3,
        )

    def test_recent_video_preview_requires_backend(self):
        router = MagicMock()
        router.backend_api_client = None
        executor = ToolExecutor(tool_router=router, action_registry=MagicMock())

        result = executor.execute(
            "check_youtube_channel_recent_videos",
            {"channel_name": "Kneppy Invests"},
        )

        assert result["ok"] is False
        assert "backend" in result["error"].lower()

    def test_recent_video_preview_validates_limit(self):
        executor = _make_executor()

        result = executor.execute(
            "check_youtube_channel_recent_videos",
            {"channel_name": "Kneppy Invests", "limit": 99},
        )

        assert result["ok"] is False
        assert "limit" in result["error"]


class TestIngestYoutubeVideosTool:
    def test_successful_selected_video_ingest(self):
        executor = _make_executor()

        result = executor.execute(
            "ingest_youtube_videos",
            {
                "urls": ["https://www.youtube.com/watch?v=abc123"],
                "credibility_weight": 0.7,
                "takeaway_limit": 3,
                "selected_videos": [
                    {
                        "title": "BHP quarterly results breakdown",
                        "webpage_url": "https://www.youtube.com/watch?v=abc123",
                        "duration_seconds": 420,
                        "scores": {"overall": 0.91, "recency": 0.9},
                    }
                ],
            },
        )

        assert result["ok"] is True
        assert result["count"] == 1
        metadata = result["results"][0]["selection_metadata"]
        assert metadata["duration_seconds"] == 420
        assert metadata["scores"]["overall"] == 0.91
        executor._router.backend_api_client.ingest_youtube_urls.assert_called_once_with(
            ["https://www.youtube.com/watch?v=abc123"],
            credibility_weight=0.7,
            takeaway_limit=3,
        )

    def test_selected_video_ingest_requires_urls(self):
        executor = _make_executor()

        result = executor.execute("ingest_youtube_videos", {})

        assert result["ok"] is False
        assert "urls" in result["error"]

    def test_selected_video_ingest_validates_weight(self):
        executor = _make_executor()

        result = executor.execute(
            "ingest_youtube_videos",
            {
                "urls": ["https://www.youtube.com/watch?v=abc123"],
                "credibility_weight": 2.0,
            },
        )

        assert result["ok"] is False
        assert "credibility_weight" in result["error"]
