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
_INDEX_RE = re.compile(r"(?:ticker_index=|index=|items=)?(\d+)/(\d+)")
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")

_KNOWN_STAGES = frozenset({"progress", "backfill", "resume", "post", "sync", "extract", "audit"})


@dataclass(frozen=True)
class ProgressInfo:
    """Structured progress extracted from one output line."""

    stage: str
    current: int | None = None
    total: int | None = None
    percent_override: float | None = None
    detail: str = ""

    @property
    def pct(self) -> float | None:
        if self.percent_override is not None:
            return self.percent_override
        if self.current is None or self.total is None or self.total == 0:
            return None
        return (self.current / self.total) * 100.0


def parse_progress_line(line: str) -> ProgressInfo | None:
    """Parse a single output line into a ``ProgressInfo``, or ``None``.

    Supports:
    - [stage] message index=5/10
    - [stage] message 50%
    - [5/10] message
    """
    cleaned = line.strip()
    if not cleaned:
        return None

    stage = "working"
    detail = cleaned

    # Try standard [tag] format
    tag_match = _TAG_RE.match(cleaned)
    if tag_match:
        tag = tag_match.group(1).lower()
        # Check if tag is actually a progress fraction [5/10]
        if "/" in tag:
            idx_match = _INDEX_RE.search(tag)
            if idx_match:
                current = int(idx_match.group(1))
                total = int(idx_match.group(2))
                return ProgressInfo(stage="progress", current=current, total=total, detail=tag_match.group(2))
        
        if tag in _KNOWN_STAGES or any(c.isalpha() for c in tag):
            stage = tag
            detail = tag_match.group(2)
    
    current: int | None = None
    total: int | None = None
    percent_override: float | None = None

    # Look for 5/10 pattern
    idx_match = _INDEX_RE.search(detail)
    if idx_match:
        current = int(idx_match.group(1))
        total = int(idx_match.group(2))
    
    # Look for 50% pattern
    pct_match = _PCT_RE.search(detail)
    if pct_match:
        percent_override = float(pct_match.group(1))

    if current is not None or percent_override is not None or tag_match:
        return ProgressInfo(
            stage=stage,
            current=current,
            total=total,
            percent_override=percent_override,
            detail=detail
        )

    return None
