from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from app.services.youtube_transcript_fetcher import YoutubeVideo, fetch_video_metadata


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
