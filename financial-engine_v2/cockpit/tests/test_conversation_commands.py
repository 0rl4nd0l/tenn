from __future__ import annotations

from cockpit.core.conversation_commands import derive_conversational_command


def test_filestats_phrase_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhp filestats") == "/filestats BHP"


def test_filestat_singular_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhpt filestat") == "/filestats BHPT"


def test_non_command_phrase_returns_none() -> None:
    assert derive_conversational_command("tell me about bhp") is None


class TestYouTubeIngestRules:
    def test_bare_youtube_watch_url_maps_to_ingest(self):
        url = "https://www.youtube.com/watch?v=UNJwgi0aW6s"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_bare_youtu_be_url_maps_to_ingest(self):
        url = "https://youtu.be/UNJwgi0aW6s"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_youtu_be_with_si_param_maps_to_ingest(self):
        url = "https://youtu.be/UNJwgi0aW6s?si=jeB30d8VCY8xjnbR"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_ingest_this_video_phrase_maps_to_ingest(self):
        url = "https://youtu.be/abc123abcde"
        result = derive_conversational_command(f"ingest this video {url}")
        assert result == f"/ingest {url}"

    def test_non_youtube_url_does_not_match(self):
        result = derive_conversational_command("https://example.com/page")
        assert result is None

    def test_slash_command_passthrough_not_matched(self):
        result = derive_conversational_command("/ingest https://youtu.be/abc123abcde")
        assert result is None
