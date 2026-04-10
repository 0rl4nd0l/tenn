"""Parse structured progress lines emitted by cockpit action scripts.

Action scripts (e.g., full_history_ticker_sync.py) print lines with
prefixes like ``[progress]``, ``[backfill]``, ``[resume]``, ``[post]``.
This module extracts structured stage information from those lines so
the jobs API can report real-time progress.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TAG_RE = re.compile(r"^\s*\[(\w+)\]\s*(.*?)\s*$")
_INDEX_RE = re.compile(r"ticker_index=(\d+)/(\d+)")

_KNOWN_STAGES = frozenset({"progress", "backfill", "resume", "post"})


@dataclass(frozen=True)
class ProgressInfo:
    """Structured progress extracted from one output line."""

    stage: str
    current: int | None = None
    total: int | None = None
    detail: str = ""

    @property
    def pct(self) -> float | None:
        if self.current is None or self.total is None or self.total == 0:
            return None
        return (self.current / self.total) * 100.0


def parse_progress_line(line: str) -> ProgressInfo | None:
    """Parse a single output line into a ``ProgressInfo``, or ``None``."""
    m = _TAG_RE.match(line)
    if m is None:
        return None

    stage = m.group(1).lower()
    if stage not in _KNOWN_STAGES:
        return None

    detail = m.group(2)

    current: int | None = None
    total: int | None = None
    idx = _INDEX_RE.search(detail)
    if idx:
        current = int(idx.group(1))
        total = int(idx.group(2))

    return ProgressInfo(stage=stage, current=current, total=total, detail=detail)
