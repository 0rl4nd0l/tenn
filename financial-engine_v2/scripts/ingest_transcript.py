#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.commentary_ingest import ingest_transcript  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a transcript into commentary memory.")
    parser.add_argument("transcript_path", help="Path to the transcript text file.")
    parser.add_argument("--source-name", default="", help="Display name for the transcript source.")
    parser.add_argument(
        "--source-type",
        default="youtube_transcript",
        choices=["youtube_transcript", "podcast_transcript", "market_commentary"],
        help="Commentary source type.",
    )
    parser.add_argument("--speaker", required=True, help="Primary speaker or host.")
    parser.add_argument("--published-at", required=True, help="Published timestamp in ISO-8601 form.")
    parser.add_argument(
        "--topic-tags",
        default="",
        help="Comma-separated topic tags to attach to each commentary chunk.",
    )
    parser.add_argument("--credibility-weight", type=float, default=None, help="Optional credibility override.")
    parser.add_argument("--decay-half-life-days", type=float, default=None, help="Optional decay half-life override.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    transcript_path = Path(args.transcript_path).expanduser().resolve()
    if not transcript_path.exists():
        raise FileNotFoundError(f"transcript file not found: {transcript_path}")

    topic_tags = [
        value.strip()
        for value in str(args.topic_tags or "").split(",")
        if value.strip()
    ]
    payload = ingest_transcript(
        transcript_text=transcript_path.read_text(encoding="utf-8"),
        source_name=args.source_name or transcript_path.stem,
        source_type=args.source_type,
        speaker=args.speaker,
        published_at=args.published_at,
        topic_tags=topic_tags,
        credibility_weight=args.credibility_weight,
        decay_half_life_days=args.decay_half_life_days,
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
