#!/usr/bin/env python3
from __future__ import annotations

import argparse
import signal
import sys
from threading import Event
from typing import Iterable

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.transcript_watcher import (  # noqa: E402
    DEFAULT_POLL_INTERVAL_SECONDS,
    TranscriptProcessor,
    TranscriptWatcher,
)
from app.services.youtube_transcript_fetcher import (  # noqa: E402
    DEFAULT_YOUTUBE_POLL_INTERVAL_SECONDS,
    YoutubeTranscriptFetcher,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the transcript inbox watcher daemon.")
    parser.add_argument("--once", action="store_true", help="Run one watcher pass and exit.")
    parser.add_argument(
        "--poll-seconds",
        "--transcript-poll-seconds",
        dest="poll_seconds",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Polling interval for inbox/transcripts scans.",
    )
    parser.add_argument(
        "--youtube-poll-seconds",
        type=float,
        default=DEFAULT_YOUTUBE_POLL_INTERVAL_SECONDS,
        help="Minimum interval for polling watched YouTube channels.",
    )
    return parser.parse_args()


def _print_results(label: str, results: Iterable[object]) -> None:
    rows = list(results)
    if not rows:
        return
    counts: dict[str, int] = {}
    for row in rows:
        status = str(getattr(row, "status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    summary = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    print(f"[{label}] {summary}", flush=True)


def main() -> int:
    args = parse_args()
    stop_event = Event()

    def _stop(*_args: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    processor = TranscriptProcessor()
    processor.ensure_directories()

    watcher = TranscriptWatcher(
        processor=processor,
        poll_interval_seconds=args.poll_seconds,
    )
    youtube_fetcher = YoutubeTranscriptFetcher(
        processor=processor,
        poll_interval_seconds=args.youtube_poll_seconds,
    )

    if args.once:
        _print_results("watcher", watcher.poll_once())
        _print_results("youtube", youtube_fetcher.maybe_poll())
        return 0

    while not stop_event.is_set():
        _print_results("watcher", watcher.poll_once())
        _print_results("youtube", youtube_fetcher.maybe_poll())
        stop_event.wait(max(1.0, float(args.poll_seconds)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
