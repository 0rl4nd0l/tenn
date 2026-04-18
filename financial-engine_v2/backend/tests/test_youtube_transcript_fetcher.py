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
