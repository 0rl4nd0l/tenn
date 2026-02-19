import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

DEFAULT_DB_PATH = Path("data/model_strategy/youtube_transcripts_index.json")
DEFAULT_TRANSCRIPTS_DIR = Path("data/model_strategy/youtube_transcripts")
WATCH_URL_PREFIX = "https://www.youtube.com/watch?v="


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download YouTube transcripts and persist them into a local model-strategy "
            "database index."
        )
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="YouTube URL to ingest (can be passed multiple times).",
    )
    parser.add_argument(
        "--video-id",
        action="append",
        default=[],
        help="YouTube video ID to ingest directly (can be passed multiple times).",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Optional text file containing one YouTube URL or video ID per line.",
    )
    parser.add_argument(
        "--languages",
        default="en,en-US",
        help="Comma-separated transcript language preference order.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to JSON strategy database index (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=DEFAULT_TRANSCRIPTS_DIR,
        help=(
            f"Directory where transcript artifacts are saved "
            f"(default: {DEFAULT_TRANSCRIPTS_DIR})."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download and overwrite transcript artifacts for videos already in the index.",
    )
    return parser.parse_args()


def extract_video_id(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None

    id_pattern = re.compile(r"^[A-Za-z0-9_-]{11}$")
    if id_pattern.match(candidate):
        return candidate

    parsed = urlparse(candidate)
    if not parsed.netloc:
        return None

    hostname = parsed.netloc.lower()
    if hostname.endswith("youtu.be"):
        short_id = parsed.path.strip("/").split("/")[0]
        return short_id if id_pattern.match(short_id) else None

    if "youtube.com" in hostname:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            return video_id if video_id and id_pattern.match(video_id) else None
        if parsed.path.startswith("/shorts/"):
            short_id = parsed.path.split("/")[2]
            return short_id if id_pattern.match(short_id) else None
        if parsed.path.startswith("/embed/"):
            embed_id = parsed.path.split("/")[2]
            return embed_id if id_pattern.match(embed_id) else None

    return None


def read_inputs(file_path: Path) -> list[str]:
    values: list[str] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        values.append(line)
    return values


def normalize_video_ids(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []

    for value in values:
        video_id = extract_video_id(value)
        if not video_id:
            print(f"[warn] skipping unrecognized input: {value}")
            continue
        if video_id in seen:
            continue
        seen.add(video_id)
        normalized.append(video_id)

    return normalized


def load_index(db_path: Path) -> dict[str, dict]:
    if not db_path.exists():
        return {}

    content = json.loads(db_path.read_text(encoding="utf-8"))
    videos = content.get("videos", [])
    by_id: dict[str, dict] = {}
    for record in videos:
        video_id = record.get("video_id")
        if video_id:
            by_id[video_id] = record
    return by_id


def save_index(db_path: Path, records_by_id: dict[str, dict]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "videos": sorted(records_by_id.values(), key=lambda row: row["video_id"]),
    }
    db_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_markdown(record: dict) -> str:
    lines = [
        f"# {record['title']}",
        "",
        f"- video_id: `{record['video_id']}`",
        f"- url: {record['url']}",
        f"- language: {record['language']}",
        f"- fetched_at_utc: {record['fetched_at_utc']}",
        "",
        "## Transcript",
        "",
    ]

    for item in record["segments"]:
        start_seconds = item.get("start", 0)
        text = item.get("text", "").strip()
        if not text:
            continue
        lines.append(f"[{start_seconds:>7.2f}s] {text}")

    return "\n".join(lines).strip() + "\n"


def fetch_transcript(video_id: str, languages: list[str]) -> tuple[list[dict], str]:
    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    resolved_language = transcript_data[0].get("language", languages[0]) if transcript_data else languages[0]
    return transcript_data, resolved_language


def infer_title(segments: list[dict], video_id: str) -> str:
    for segment in segments:
        text = (segment.get("text") or "").strip()
        if text and not text.startswith("["):
            clipped = re.sub(r"\s+", " ", text)
            return clipped[:100]
    return f"YouTube Transcript {video_id}"


def main() -> int:
    args = parse_args()
    languages = [part.strip() for part in args.languages.split(",") if part.strip()]

    collected_inputs = list(args.url) + list(args.video_id)
    if args.input_file:
        if not args.input_file.exists():
            print(f"[error] --input-file not found: {args.input_file}")
            return 1
        collected_inputs.extend(read_inputs(args.input_file))

    video_ids = normalize_video_ids(collected_inputs)
    if not video_ids:
        print("[error] no valid YouTube video IDs were provided.")
        return 1

    records_by_id = load_index(args.db_path)
    args.transcripts_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    skipped_count = 0

    for video_id in video_ids:
        if video_id in records_by_id and not args.overwrite:
            print(f"[skip] {video_id} already indexed (use --overwrite to refresh).")
            skipped_count += 1
            continue

        try:
            segments, resolved_language = fetch_transcript(video_id, languages)
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
            print(f"[error] {video_id}: {exc}")
            continue
        except Exception as exc:
            print(f"[error] {video_id}: unexpected failure: {exc}")
            continue

        now_utc = datetime.now(timezone.utc).isoformat()
        title = infer_title(segments, video_id)
        record = {
            "video_id": video_id,
            "url": f"{WATCH_URL_PREFIX}{video_id}",
            "title": title,
            "language": resolved_language,
            "fetched_at_utc": now_utc,
            "segment_count": len(segments),
            "segments": segments,
            "artifact_json": str((args.transcripts_dir / f"{video_id}.json").as_posix()),
            "artifact_md": str((args.transcripts_dir / f"{video_id}.md").as_posix()),
        }

        json_path = args.transcripts_dir / f"{video_id}.json"
        md_path = args.transcripts_dir / f"{video_id}.md"
        json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(build_markdown(record), encoding="utf-8")

        records_by_id[video_id] = {k: v for k, v in record.items() if k != "segments"}
        print(f"[ok] saved transcript for {video_id} -> {json_path}")
        success_count += 1

    save_index(args.db_path, records_by_id)

    print(
        f"[done] successes={success_count}, skipped={skipped_count}, "
        f"total_indexed={len(records_by_id)}"
    )
    return 0 if success_count > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
