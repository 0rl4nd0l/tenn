from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from app.services.channel_registry import ChannelConfig, ChannelRegistry
from app.services.transcript_watcher import TranscriptMetadata, TranscriptProcessor


DEFAULT_YOUTUBE_POLL_INTERVAL_SECONDS = 600.0
DEFAULT_CHANNEL_VIDEO_LIMIT = 8


class TranscriptUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class YoutubeVideo:
    video_id: str
    title: str
    channel_name: str
    published_at: str
    webpage_url: str


def _slugify_as_handle(name: str) -> str:
    """Convert 'Kneppy Invests' → 'KneppyInvests' for @handle attempt."""
    return re.sub(r"[^A-Za-z0-9_]", "", name.title().replace(" ", ""))


def resolve_channel_id(name_or_url: str) -> tuple[str, str]:
    """Resolve a channel name, @handle, URL, or raw ID to (channel_id, canonical_name).

    Tries in order:
    1. If input starts with 'UC' (raw channel ID) → validate via yt-dlp
    2. If input is a URL or @handle → pass directly to yt-dlp
    3. Plain name → try https://www.youtube.com/@{slugified} via yt-dlp

    Raises RuntimeError if channel_id cannot be resolved.
    """
    raw = str(name_or_url or "").strip()
    if not raw:
        raise ValueError("channel name or URL is required")

    # Build the lookup URL
    if raw.startswith("http://") or raw.startswith("https://"):
        lookup_url = raw
    elif raw.startswith("@"):
        lookup_url = f"https://www.youtube.com/{raw}/videos"
    elif re.match(r"^UC[A-Za-z0-9_-]{10,}$", raw):
        lookup_url = f"https://www.youtube.com/channel/{raw}/videos"
    else:
        handle = _slugify_as_handle(raw)
        lookup_url = f"https://www.youtube.com/@{handle}/videos"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlist_items": "1",
    }
    try:
        import yt_dlp  # type: ignore

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(lookup_url, download=False)
    except Exception as exc:
        raise RuntimeError(f"channel lookup failed for {raw!r}: {exc}") from exc

    channel_id = str((info or {}).get("channel_id") or "").strip()
    if not channel_id:
        raise RuntimeError(
            f"could not resolve channel_id from {raw!r} — "
            "try providing a YouTube channel URL or @handle instead"
        )
    canonical_name = str(
        (info or {}).get("channel")
        or (info or {}).get("uploader")
        or raw
    ).strip()
    return channel_id, canonical_name


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "transcript"


def _iso_from_timestamp(value: Any) -> str:
    if isinstance(value, (int, float)) and float(value) > 0:
        return (
            datetime.fromtimestamp(float(value), tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    text = str(value or "").strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}T00:00:00Z"
    if text:
        return text
    return "1970-01-01T00:00:00Z"


def fetch_video_metadata(url: str) -> YoutubeVideo:
    """Resolve a single YouTube URL to a YoutubeVideo using yt-dlp.

    Raises RuntimeError if yt-dlp is unavailable, returns no info,
    or the video_id cannot be resolved.
    """
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        cmd = [
            "yt-dlp",
            "--dump-single-json",
            "--skip-download",
            str(url or "").strip(),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("yt-dlp is required for single-URL ingestion") from exc
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "yt-dlp failed"
            raise RuntimeError(message)
        try:
            info = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"yt-dlp returned invalid metadata for URL: {url}") from exc
    else:
        options = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(str(url or "").strip(), download=False)

    if not info:
        raise RuntimeError(f"yt-dlp returned no metadata for URL: {url}")

    video_id = str(info.get("id") or "").strip()
    if not video_id:
        raise RuntimeError(f"yt-dlp could not resolve video_id from URL: {url}")

    title = str(info.get("title") or video_id).strip() or video_id
    channel = str(info.get("channel") or info.get("uploader") or "").strip()
    webpage_url = str(info.get("webpage_url") or url).strip()
    published_at = _iso_from_timestamp(
        info.get("release_timestamp") or info.get("timestamp") or info.get("upload_date")
    )

    return YoutubeVideo(
        video_id=video_id,
        title=title,
        channel_name=channel,
        published_at=published_at,
        webpage_url=webpage_url,
    )


def _youtube_videos_url(channel_id: str) -> str:
    return f"https://www.youtube.com/channel/{channel_id}/videos"


def _default_list_videos(channel: ChannelConfig, limit: int) -> list[YoutubeVideo]:
    url = _youtube_videos_url(channel.channel_id)
    playlist_limit = max(1, int(limit))
    payload: dict[str, Any]
    try:
        import yt_dlp  # type: ignore
    except Exception:
        cmd = [
            "yt-dlp",
            "--dump-single-json",
            "--flat-playlist",
            "--playlist-end",
            str(playlist_limit),
            url,
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("yt-dlp is required for monitored channel ingestion") from exc
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "yt-dlp failed"
            raise RuntimeError(message)
        payload = json.loads(completed.stdout)
    else:
        options = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "playlistend": playlist_limit,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            payload = ydl.extract_info(url, download=False) or {}

    entries = payload.get("entries") or []
    videos: list[YoutubeVideo] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video_id = str(entry.get("id") or "").strip()
        if not video_id:
            continue
        title = str(entry.get("title") or video_id).strip() or video_id
        channel_name = str(entry.get("channel") or channel.name).strip() or channel.name
        published_at = _iso_from_timestamp(
            entry.get("release_timestamp") or entry.get("timestamp") or entry.get("upload_date")
        )
        webpage_url = str(entry.get("url") or entry.get("webpage_url") or "").strip()
        if webpage_url and not webpage_url.startswith("http"):
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        if not webpage_url:
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append(
            YoutubeVideo(
                video_id=video_id,
                title=title,
                channel_name=channel_name,
                published_at=published_at,
                webpage_url=webpage_url,
            )
        )
    return videos


def _is_transcript_unavailable(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    return any(
        token in name or token in message
        for token in (
            "notranscriptfound",
            "transcriptsdisabled",
            "transcriptunavailable",
            "videounavailable",
            "couldnotretrievetranscript",
            "transcript unavailable",
            "no transcript",
            "transcripts disabled",
        )
    )


def _transcript_segments_to_text(segments: list[Any]) -> str:
    lines: list[str] = []
    for segment in segments:
        if isinstance(segment, dict):
            text = str(segment.get("text") or "").strip()
            start = segment.get("start")
        else:
            text = str(getattr(segment, "text", "") or "").strip()
            start = getattr(segment, "start", None)
        if not text:
            continue
        prefix = ""
        if isinstance(start, (int, float)):
            total_seconds = max(0, int(float(start)))
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            prefix = f"{hours:02d}:{minutes:02d}:{seconds:02d} "
        lines.append(f"{prefix}{text}".strip())
    return "\n".join(lines).strip()


def _coerce_transcript_segments(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if hasattr(raw, "to_raw_data"):
        data = raw.to_raw_data()
        if isinstance(data, list):
            return data
    if isinstance(raw, list):
        return raw
    try:
        return list(raw)
    except TypeError:
        return []


def _default_fetch_transcript(video: YoutubeVideo) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "youtube-transcript-api is required for monitored channel ingestion"
        ) from exc

    languages = ["en", "en-US", "en-GB"]
    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            segments = YouTubeTranscriptApi.get_transcript(video.video_id, languages=languages)
        else:
            api = YouTubeTranscriptApi()
            if hasattr(api, "fetch"):
                try:
                    segments = _coerce_transcript_segments(api.fetch(video.video_id, languages=languages))
                except TypeError:
                    segments = _coerce_transcript_segments(api.fetch(video.video_id))
            elif hasattr(api, "list_transcripts"):
                transcript_list = api.list_transcripts(video.video_id)
                if hasattr(transcript_list, "find_transcript"):
                    transcript = transcript_list.find_transcript(languages)
                else:
                    transcript = next(iter(transcript_list))
                segments = _coerce_transcript_segments(transcript.fetch())
            else:
                raise RuntimeError("unsupported youtube-transcript-api interface")
    except Exception as exc:
        if _is_transcript_unavailable(exc):
            raise TranscriptUnavailableError(str(exc)) from exc
        raise

    text = _transcript_segments_to_text(segments)
    if not text:
        raise TranscriptUnavailableError("transcript unavailable")
    return text


class YoutubeTranscriptFetcher:
    def __init__(
        self,
        *,
        processor: TranscriptProcessor | None = None,
        channel_registry_path: str | None = None,
        list_videos_fn: Callable[[ChannelConfig, int], list[YoutubeVideo]] | None = None,
        fetch_transcript_fn: Callable[[YoutubeVideo], str] | None = None,
        poll_interval_seconds: float = DEFAULT_YOUTUBE_POLL_INTERVAL_SECONDS,
        video_limit: int = DEFAULT_CHANNEL_VIDEO_LIMIT,
    ) -> None:
        self.processor = processor or TranscriptProcessor()
        self.channel_registry = ChannelRegistry(channel_registry_path)
        self.list_videos_fn = list_videos_fn or _default_list_videos
        self.fetch_transcript_fn = fetch_transcript_fn or _default_fetch_transcript
        self.poll_interval_seconds = max(1.0, float(poll_interval_seconds))
        self.video_limit = max(1, int(video_limit))
        self._last_poll_started_at = 0.0

    def poll_once(self) -> list:
        self.processor.ensure_directories()
        self.channel_registry.ensure_exists()
        results = []
        for channel in self.channel_registry.enabled_channels():
            videos = sorted(
                self.list_videos_fn(channel, self.video_limit),
                key=lambda video: (video.published_at, video.video_id),
            )
            for video in videos:
                try:
                    transcript_text = self.fetch_transcript_fn(video)
                except TranscriptUnavailableError:
                    continue

                metadata = TranscriptMetadata(
                    source_name=video.title,
                    source_type="youtube_transcript",
                    speaker=video.channel_name or channel.name,
                    published_at=video.published_at,
                    credibility_weight=channel.credibility_weight,
                    decay_half_life_days=14.0,
                )
                if (
                    self.processor.duplicate_source_id_for_text(
                        transcript_text=transcript_text,
                        metadata=metadata,
                    )
                    is not None
                ):
                    continue
                file_name = f"{_slugify(video.title)}_{_slugify(video.video_id)}.txt"
                path = self.processor.write_drop_file(
                    file_name=file_name,
                    transcript_text=transcript_text,
                    metadata=metadata,
                )
                results.append(self.processor.process_file(path))
        return results

    def maybe_poll(self) -> list:
        now = time.monotonic()
        if self._last_poll_started_at and now - self._last_poll_started_at < self.poll_interval_seconds:
            return []
        self._last_poll_started_at = now
        return self.poll_once()
