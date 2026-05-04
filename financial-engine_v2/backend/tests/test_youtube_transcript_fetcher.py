from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from app.services.youtube_transcript_fetcher import (
    YoutubeVideo,
    fetch_video_metadata,
    list_recent_channel_videos,
)


def _make_ydl_info(
    video_id="abc123",
    title="My Video",
    channel="My Channel",
    upload_date="20260412",
    webpage_url="https://www.youtube.com/watch?v=abc123",
):
    return {
        "id": video_id,
        "title": title,
        "channel": channel,
        "upload_date": upload_date,
        "webpage_url": webpage_url,
        "release_timestamp": None,
        "timestamp": None,
    }


class TestFetchVideoMetadata:
    def test_returns_youtube_video_from_watch_url(self, monkeypatch):
        info = _make_ydl_info()

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        video = fetch_video_metadata("https://www.youtube.com/watch?v=abc123")

        assert isinstance(video, YoutubeVideo)
        assert video.video_id == "abc123"
        assert video.title == "My Video"
        assert video.channel_name == "My Channel"
        assert video.published_at == "2026-04-12T00:00:00Z"
        assert "abc123" in video.webpage_url

    def test_returns_youtube_video_from_short_url(self, monkeypatch):
        info = _make_ydl_info(video_id="UNJwgi0aW6s", title="Short URL Title")

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        video = fetch_video_metadata("https://youtu.be/UNJwgi0aW6s")
        assert video.video_id == "UNJwgi0aW6s"
        assert video.title == "Short URL Title"

    def test_falls_back_to_yt_dlp_cli_when_python_module_missing(self, monkeypatch):
        info = _make_ydl_info(video_id="UNJwgi0aW6s", title="CLI Fallback Title")
        commands = []

        monkeypatch.setitem(__import__("sys").modules, "yt_dlp", None)
        monkeypatch.setattr(
            "app.services.youtube_transcript_fetcher.subprocess.run",
            lambda cmd, **kwargs: commands.append((cmd, kwargs))
            or SimpleNamespace(
                returncode=0,
                stdout=json.dumps(info),
                stderr="",
            ),
        )

        video = fetch_video_metadata("https://youtu.be/UNJwgi0aW6s")

        assert video.video_id == "UNJwgi0aW6s"
        assert video.title == "CLI Fallback Title"
        assert commands
        assert commands[0][0][:3] == ["yt-dlp", "--dump-single-json", "--skip-download"]

    def test_yt_dlp_unavailable_raises_runtime_error(self, monkeypatch):
        monkeypatch.setitem(__import__("sys").modules, "yt_dlp", None)

        def _raise_file_not_found(*args, **kwargs):
            raise FileNotFoundError("yt-dlp")

        monkeypatch.setattr(
            "app.services.youtube_transcript_fetcher.subprocess.run",
            _raise_file_not_found,
        )

        with pytest.raises(RuntimeError, match="yt-dlp is required"):
            fetch_video_metadata("https://youtu.be/abc123")

    def test_yt_dlp_returns_none_raises_runtime_error(self, monkeypatch):
        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return None

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        with pytest.raises(RuntimeError, match="no metadata"):
            fetch_video_metadata("https://youtu.be/abc123")

    def test_yt_dlp_extract_error_raises_runtime_error(self, monkeypatch):
        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False):
                raise Exception("video unavailable")

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        with pytest.raises(RuntimeError, match="metadata fetch failed"):
            fetch_video_metadata("https://youtu.be/abc123")

    def test_missing_video_id_raises_runtime_error(self, monkeypatch):
        info = _make_ydl_info(video_id="")

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        with pytest.raises(RuntimeError, match="could not resolve video_id"):
            fetch_video_metadata("https://youtu.be/abc123")

    def test_channel_falls_back_to_uploader(self, monkeypatch):
        info = {
            "id": "abc123",
            "title": "Test",
            "channel": None,
            "uploader": "Fallback Uploader",
            "upload_date": "20260412",
            "webpage_url": "https://www.youtube.com/watch?v=abc123",
            "release_timestamp": None,
            "timestamp": None,
        }

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        video = fetch_video_metadata("https://www.youtube.com/watch?v=abc123")
        assert video.channel_name == "Fallback Uploader"

    def test_webpage_url_falls_back_to_input_url(self, monkeypatch):
        info = {
            "id": "abc123",
            "title": "Test",
            "channel": "Test Channel",
            "upload_date": "20260412",
            "webpage_url": None,
            "release_timestamp": None,
            "timestamp": None,
        }

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        input_url = "https://youtu.be/abc123"
        video = fetch_video_metadata(input_url)
        assert video.webpage_url == input_url

    def test_missing_publish_date_remains_unknown(self, monkeypatch):
        info = {
            "id": "abc123",
            "title": "Test",
            "channel": "Test Channel",
            "upload_date": None,
            "webpage_url": "https://www.youtube.com/watch?v=abc123",
            "release_timestamp": None,
            "timestamp": None,
        }

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        video = fetch_video_metadata("https://www.youtube.com/watch?v=abc123")

        assert video.published_at is None


from unittest.mock import patch, MagicMock
from app.services.youtube_transcript_fetcher import resolve_channel_id, _slugify_as_handle


class TestResolveChannelId:
    def _mock_ydl(self, channel_id: str, uploader: str):
        return {
            "channel_id": channel_id,
            "uploader": uploader,
            "channel": uploader,
            "uploader_id": f"@{uploader.replace(' ', '')}",
        }

    def test_resolves_at_handle(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id("@KneppyInvests")
        assert channel_id == "UCabc123"
        assert name == "Kneppy Invests"

    def test_resolves_plain_name_via_at_handle(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id("Kneppy Invests")
        assert channel_id == "UCabc123"
        # Verify correct @handle URL was constructed from the plain name
        call_args = instance.extract_info.call_args
        assert "KneppyInvests" in call_args[0][0]

    def test_plain_name_falls_back_to_youtube_search(self):
        search_info = {
            "entries": [
                {
                    "channel_id": "UCjQJPzeCJhA4KrETh3FVVHA",
                    "channel": "Kneppy Invests",
                    "uploader": "Kneppy Invests",
                    "uploader_id": "@kneppyinvests7584",
                }
            ]
        }
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.side_effect = [
                Exception("HTTP Error 404: Not Found"),
                search_info,
            ]
            channel_id, name = resolve_channel_id("Kneppy Invests")

        assert channel_id == "UCjQJPzeCJhA4KrETh3FVVHA"
        assert name == "Kneppy Invests"
        assert instance.extract_info.call_args_list[0].args[0].endswith(
            "/@KneppyInvests/videos"
        )
        assert instance.extract_info.call_args_list[1].args[0] == (
            "ytsearch5:Kneppy Invests"
        )

    def test_search_fallback_prefers_matching_channel_name(self):
        search_info = {
            "entries": [
                {
                    "channel_id": "UCwrong",
                    "channel": "Other Channel",
                    "uploader": "Other Channel",
                },
                {
                    "channel_id": "UCabc123",
                    "channel": "Kneppy Invests",
                    "uploader": "Kneppy Invests",
                },
            ]
        }
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.side_effect = [
                Exception("HTTP Error 404: Not Found"),
                search_info,
            ]
            channel_id, name = resolve_channel_id("Kneppy Invests")

        assert channel_id == "UCabc123"
        assert name == "Kneppy Invests"

    def test_passthrough_raw_channel_id(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id("UCabc123")
        assert channel_id == "UCabc123"

    def test_resolves_channel_url(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id(
                "https://www.youtube.com/@KneppyInvests"
            )
        assert channel_id == "UCabc123"

    def test_raises_on_missing_channel_id(self):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = {"uploader": "Someone"}
            with pytest.raises(RuntimeError, match="could not resolve channel_id"):
                resolve_channel_id("some channel")

    def test_raises_runtime_error_on_yt_dlp_failure(self):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.side_effect = Exception("network error")
            with pytest.raises(RuntimeError, match="channel lookup failed"):
                resolve_channel_id("Kneppy Invests")


class TestSlugifyAsHandle:
    def test_plain_two_word_name(self):
        assert _slugify_as_handle("Kneppy Invests") == "KneppyInvests"

    def test_name_with_hyphen(self):
        # hyphens stripped
        assert _slugify_as_handle("Investment-Guru") == "InvestmentGuru"

    def test_name_with_underscore(self):
        # underscores preserved
        assert _slugify_as_handle("test_channel") == "Test_Channel"

    def test_single_word(self):
        assert _slugify_as_handle("Kneppy") == "Kneppy"

    def test_empty_string(self):
        assert _slugify_as_handle("") == ""


class TestListRecentChannelVideos:
    def test_resolves_channel_and_returns_scored_recent_videos(self):
        videos = [
            YoutubeVideo(
                video_id="old123",
                title="Older ASX video",
                channel_name="Kneppy Invests",
                published_at="2026-01-01T00:00:00Z",
                webpage_url="https://www.youtube.com/watch?v=old123",
                duration_seconds=3600,
            ),
            YoutubeVideo(
                video_id="new123",
                title="BHP quarterly results breakdown",
                channel_name="Kneppy Invests",
                published_at="2026-04-28T00:00:00Z",
                webpage_url="https://www.youtube.com/watch?v=new123",
                duration_seconds=1200,
            ),
        ]

        def _list_videos(channel, limit):
            assert channel.channel_id == "UCabc123"
            assert limit == 2
            return videos

        with (
            patch(
                "app.services.youtube_transcript_fetcher.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.services.youtube_transcript_fetcher.ChannelRegistry") as MockRegistry,
        ):
            MockRegistry.return_value.channels.return_value = []
            result = list_recent_channel_videos(
                "Kneppy Invests",
                limit=2,
                list_videos_fn=_list_videos,
            )

        assert result["ok"] is True
        assert result["channel_id"] == "UCabc123"
        assert result["videos"][0]["video_id"] == "new123"
        assert result["videos"][0]["position"] == 1
        assert result["videos"][0]["scores"]["overall"] > result["videos"][1]["scores"]["overall"]

    def test_limit_is_clamped_to_twenty(self):
        captured = {}

        def _list_videos(_channel, limit):
            captured["limit"] = limit
            return []

        with (
            patch(
                "app.services.youtube_transcript_fetcher.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.services.youtube_transcript_fetcher.ChannelRegistry") as MockRegistry,
        ):
            MockRegistry.return_value.channels.return_value = []
            result = list_recent_channel_videos(
                "Kneppy Invests",
                limit=99,
                list_videos_fn=_list_videos,
            )

        assert result["limit"] == 20
        assert captured["limit"] == 20

    def test_preserves_upstream_order_when_any_publish_date_is_unknown(self):
        videos = [
            YoutubeVideo(
                video_id="unknown-a",
                title="Unknown date A",
                channel_name="Kneppy Invests",
                published_at=None,
                webpage_url="https://www.youtube.com/watch?v=unknown-a",
            ),
            YoutubeVideo(
                video_id="dated-new",
                title="Known recent date",
                channel_name="Kneppy Invests",
                published_at="2026-04-28T00:00:00Z",
                webpage_url="https://www.youtube.com/watch?v=dated-new",
            ),
            YoutubeVideo(
                video_id="unknown-b",
                title="Unknown date B",
                channel_name="Kneppy Invests",
                published_at=None,
                webpage_url="https://www.youtube.com/watch?v=unknown-b",
            ),
        ]

        with (
            patch(
                "app.services.youtube_transcript_fetcher.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.services.youtube_transcript_fetcher.ChannelRegistry") as MockRegistry,
        ):
            MockRegistry.return_value.channels.return_value = []
            result = list_recent_channel_videos(
                "Kneppy Invests",
                limit=3,
                list_videos_fn=lambda _channel, _limit: videos,
            )

        assert [video["video_id"] for video in result["videos"]] == [
            "unknown-a",
            "dated-new",
            "unknown-b",
        ]
        assert result["videos"][0]["published_at"] is None
