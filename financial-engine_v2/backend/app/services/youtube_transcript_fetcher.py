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


class _QuietYtDlpLogger:
    def debug(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


@dataclass(frozen=True)
class YoutubeVideo:
    video_id: str
    title: str
    channel_name: str
    published_at: str | None
    webpage_url: str
    duration_seconds: int | None = None
    view_count: int | None = None


class YoutubeChannelResolutionError(RuntimeError):
    def __init__(self, message: str, *, name_or_id: str) -> None:
        super().__init__(message)
        self.name_or_id = name_or_id
        self.error_code = "youtube_channel_resolution_failed"


def _slugify_as_handle(name: str) -> str:
    """Convert 'Kneppy Invests' → 'KneppyInvests' for @handle attempt."""
    return re.sub(r"[^A-Za-z0-9_]", "", name.title().replace(" ", ""))


def _normalize_channel_lookup_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _channel_identity_from_entry(entry: dict[str, Any], raw: str) -> tuple[str, str] | None:
    channel_id = str(entry.get("channel_id") or "").strip()
    if not channel_id:
        return None
    canonical_name = str(
        entry.get("channel")
        or entry.get("uploader")
        or raw
    ).strip()
    return channel_id, canonical_name or raw


def _search_result_matches_query(entry: dict[str, Any], raw: str) -> bool:
    query = _normalize_channel_lookup_value(raw.lstrip("@"))
    if not query:
        return False
    values = [
        entry.get("channel"),
        entry.get("uploader"),
        str(entry.get("uploader_id") or "").lstrip("@"),
    ]
    return any(_normalize_channel_lookup_value(str(value or "")) == query for value in values)


def _channel_identity_from_info(
    info: dict[str, Any],
    raw: str,
    *,
    prefer_query_match: bool = False,
) -> tuple[str, str] | None:
    direct = _channel_identity_from_entry(info, raw)
    if direct is not None:
        return direct

    entries = info.get("entries")
    if not isinstance(entries, list):
        return None

    first_identity: tuple[str, str] | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identity = _channel_identity_from_entry(entry, raw)
        if identity is None:
            continue
        if first_identity is None:
            first_identity = identity
        if prefer_query_match and _search_result_matches_query(entry, raw):
            return identity
    return first_identity


def resolve_channel_id(name_or_url: str) -> tuple[str, str]:
    """Resolve a channel name, @handle, URL, or raw ID to (channel_id, canonical_name).

    Tries in order:
    1. If input starts with 'UC' (raw channel ID) → validate via yt-dlp
    2. If input is a URL or @handle → pass directly to yt-dlp
    3. Plain name → try https://www.youtube.com/@{slugified} via yt-dlp
    4. Plain name or handle miss → fall back to ytsearch and use the matching channel

    Raises RuntimeError if channel_id cannot be resolved.
    """
    raw = str(name_or_url or "").strip()
    if not raw:
        raise ValueError("channel name or URL is required")

    def _resolution_error(message: str) -> YoutubeChannelResolutionError:
        return YoutubeChannelResolutionError(message, name_or_id=raw)

    # Build the lookup URL
    search_fallback_query = ""
    if raw.startswith("http://") or raw.startswith("https://"):
        lookup_url = raw
    elif raw.startswith("@"):
        lookup_url = f"https://www.youtube.com/{raw}/videos"
        search_fallback_query = raw.lstrip("@")
    elif re.match(r"^UC[A-Za-z0-9_-]{10,}$", raw):
        lookup_url = f"https://www.youtube.com/channel/{raw}/videos"
    else:
        handle = _slugify_as_handle(raw)
        lookup_url = f"https://www.youtube.com/@{handle}/videos"
        search_fallback_query = raw

    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise _resolution_error("yt-dlp is required for channel lookup") from exc

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "logger": _QuietYtDlpLogger(),
        "extract_flat": True,
        "playlist_items": "1",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            primary_error: Exception | None = None
            try:
                info = ydl.extract_info(lookup_url, download=False) or {}
            except Exception as exc:
                primary_error = exc
            else:
                identity = _channel_identity_from_info(info, raw)
                if identity is not None:
                    return identity

            if search_fallback_query:
                try:
                    search_info = ydl.extract_info(
                        f"ytsearch5:{search_fallback_query}",
                        download=False,
                    ) or {}
                except Exception as exc:
                    if primary_error is not None:
                        raise _resolution_error(
                            f"channel lookup failed for {raw!r}: {primary_error}; "
                            f"search fallback failed: {exc}"
                        ) from exc
                    raise _resolution_error(
                        f"channel lookup failed for {raw!r}: {exc}"
                    ) from exc

                identity = _channel_identity_from_info(
                    search_info,
                    raw,
                    prefer_query_match=True,
                )
                if identity is not None:
                    return identity

            if primary_error is not None:
                raise _resolution_error(
                    f"channel lookup failed for {raw!r}: {primary_error}"
                ) from primary_error
    except Exception as exc:
        if isinstance(exc, YoutubeChannelResolutionError):
            raise
        raise _resolution_error(f"channel lookup failed for {raw!r}: {exc}") from exc

    raise _resolution_error(
        f"could not resolve channel_id from {raw!r} — "
        "try providing a YouTube channel URL or @handle instead"
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "transcript"


def _iso_from_timestamp(value: Any) -> str | None:
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
    return None


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        coerced = int(float(value))
    except (TypeError, ValueError):
        return None
    return coerced if coerced >= 0 else None


def _parse_iso_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text or text == "1970-01-01T00:00:00Z":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ordered_recent_videos(videos: list[YoutubeVideo]) -> list[YoutubeVideo]:
    """Order dated videos by recency, but preserve upstream order if any date is unknown."""
    dated: list[tuple[datetime, str, YoutubeVideo]] = []
    for video in videos:
        parsed = _parse_iso_datetime(video.published_at or "")
        if parsed is None:
            return list(videos)
        dated.append((parsed, video.video_id, video))
    return [
        video
        for _published_at, _video_id, video in sorted(
            dated,
            key=lambda row: (row[0], row[1]),
            reverse=True,
        )
    ]


_IMPORTANT_TITLE_RE = re.compile(
    r"\b("
    r"results?|earnings?|quarterly|annual|guidance|upgrade|downgrade|"
    r"acquisition|takeover|merger|capital\s+rais(?:e|ing)|placement|"
    r"dividend|buyback|short\s+report|fraud|bankruptcy|administration"
    r")\b",
    re.IGNORECASE,
)
_ASX_TICKER_IN_TITLE_RE = re.compile(r"\b[A-Z]{2,5}\b")


def _score_video_for_review(video: YoutubeVideo, *, now: datetime | None = None) -> dict[str, Any]:
    """Return deterministic preview scores for operator triage.

    These scores are intentionally metadata-only. They help order a review list
    before any transcript is fetched, but they are not factual content claims
    about the video.
    """
    clock = now or datetime.now(timezone.utc)
    published_at = _parse_iso_datetime(video.published_at)
    if published_at is None:
        recency_score = 0.0
    else:
        age_days = max(0.0, (clock - published_at).total_seconds() / 86400.0)
        if age_days <= 7:
            recency_score = 1.0
        elif age_days <= 30:
            recency_score = 0.8
        elif age_days <= 90:
            recency_score = 0.5
        else:
            recency_score = 0.25

    duration = video.duration_seconds
    if duration is None:
        duration_score = 0.5
    elif duration < 5 * 60:
        duration_score = 0.4
    elif duration <= 45 * 60:
        duration_score = 1.0
    elif duration <= 90 * 60:
        duration_score = 0.7
    else:
        duration_score = 0.45

    importance_score = 0.8 if _IMPORTANT_TITLE_RE.search(video.title) else 0.45
    relevance_score = 0.7 if _ASX_TICKER_IN_TITLE_RE.search(video.title) else 0.5
    overall_score = (
        0.35 * recency_score
        + 0.25 * importance_score
        + 0.20 * relevance_score
        + 0.20 * duration_score
    )
    return {
        "overall": round(overall_score, 3),
        "recency": round(recency_score, 3),
        "importance": round(importance_score, 3),
        "relevance": round(relevance_score, 3),
        "duration": round(duration_score, 3),
    }


def youtube_video_to_dict(video: YoutubeVideo, *, position: int | None = None) -> dict[str, Any]:
    payload = {
        "video_id": video.video_id,
        "title": video.title,
        "channel_name": video.channel_name,
        "published_at": video.published_at,
        "webpage_url": video.webpage_url,
        "duration_seconds": video.duration_seconds,
        "view_count": video.view_count,
        "scores": _score_video_for_review(video),
    }
    if position is not None:
        payload["position"] = position
    return payload


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
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(str(url or "").strip(), download=False)
        except Exception as exc:
            raise RuntimeError(f"yt-dlp metadata fetch failed for URL: {url}: {exc}") from exc

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
        duration_seconds=_coerce_optional_int(info.get("duration")),
        view_count=_coerce_optional_int(info.get("view_count")),
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
                duration_seconds=_coerce_optional_int(entry.get("duration")),
                view_count=_coerce_optional_int(entry.get("view_count")),
            )
        )
    return videos


def list_recent_channel_videos(
    name_or_id: str,
    *,
    limit: int = DEFAULT_CHANNEL_VIDEO_LIMIT,
    list_videos_fn: Callable[[ChannelConfig, int], list[YoutubeVideo]] | None = None,
) -> dict[str, Any]:
    """Resolve a channel and return recent video metadata without ingesting transcripts."""
    requested = str(name_or_id or "").strip()
    if not requested:
        raise ValueError("channel name or URL is required")
    resolved_limit = max(1, min(20, int(limit)))
    channel_id, canonical_name = resolve_channel_id(requested)

    credibility_weight = 0.55
    try:
        registry = ChannelRegistry()
        existing = next(
            (
                channel
                for channel in registry.channels()
                if channel.channel_id == channel_id
            ),
            None,
        )
        if existing is not None:
            credibility_weight = existing.credibility_weight
    except Exception:
        credibility_weight = 0.55

    channel = ChannelConfig(
        name=canonical_name,
        channel_id=channel_id,
        credibility_weight=credibility_weight,
        enabled=True,
    )
    videos = _ordered_recent_videos(
        (list_videos_fn or _default_list_videos)(channel, resolved_limit)
    )[:resolved_limit]
    return {
        "ok": True,
        "channel_id": channel_id,
        "name": canonical_name,
        "limit": resolved_limit,
        "credibility_weight": credibility_weight,
        "videos": [
            youtube_video_to_dict(video, position=index)
            for index, video in enumerate(videos, start=1)
        ],
    }


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
            videos = _ordered_recent_videos(self.list_videos_fn(channel, self.video_limit))
            for video in videos:
                try:
                    transcript_text = self.fetch_transcript_fn(video)
                except TranscriptUnavailableError:
                    continue

                metadata = TranscriptMetadata(
                    source_name=video.title,
                    source_type="youtube_transcript",
                    speaker=video.channel_name or channel.name,
                    published_at=video.published_at or "",
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
