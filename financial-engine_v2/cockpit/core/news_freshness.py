"""News freshness tracking for the cockpit agent loop.

Maintains a lightweight per-ticker (and market-wide) ingest timestamp so
the agent can check staleness before answering news queries. When data is
> 4 hours old, a status warning is surfaced. When > 24 hours, an automatic
ingest is suggested before search_news runs.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["NewsFreshnessTracker"]

_STALE_WARN_SECONDS = 4 * 3600   # 4 hours → surface warning
_STALE_AUTO_INGEST_SECONDS = 24 * 3600  # 24 hours → suggest auto-ingest
_MARKET_KEY = "__market__"


class NewsFreshnessTracker:
    """Track last news ingest timestamps to detect stale data.

    Uses a simple JSON file for persistence across cockpit restarts.
    Thread safety is best-effort (file writes are atomic on POSIX via
    rename). This is a lightweight heuristic, not a transactional store.

    Parameters
    ----------
    state_path:
        Optional path to the JSON persistence file. If None, state is
        in-memory only (resets on restart).
    """

    def __init__(self, state_path: Path | str | None = None) -> None:
        self._state_path = Path(state_path) if state_path else None
        self._timestamps: dict[str, float] = {}
        self._load()

    def record_ingest(self, ticker: str | None = None) -> None:
        """Record that a news ingest just completed for *ticker* (or market-wide if None)."""
        key = (ticker or "").upper().strip() or _MARKET_KEY
        self._timestamps[key] = time.time()
        self._save()

    def staleness_seconds(self, ticker: str | None = None) -> float | None:
        """Return seconds since last ingest for *ticker*, or None if never ingested."""
        key = (ticker or "").upper().strip() or _MARKET_KEY
        ts = self._timestamps.get(key)
        if ts is None:
            return None
        return time.time() - ts

    def is_stale(self, ticker: str | None = None, threshold: float = _STALE_WARN_SECONDS) -> bool:
        age = self.staleness_seconds(ticker)
        return age is None or age > threshold

    def staleness_summary(self, ticker: str | None = None) -> dict[str, Any]:
        """Return a dict suitable for embedding in a status event or tool result."""
        age = self.staleness_seconds(ticker)
        key = (ticker or "").upper().strip() or _MARKET_KEY
        if age is None:
            return {
                "ticker": key,
                "never_ingested": True,
                "recommend_ingest": True,
                "message": f"No news has ever been ingested for {key}. Offer to run news ingest.",
            }
        hours = age / 3600
        warn = age > _STALE_WARN_SECONDS
        auto = age > _STALE_AUTO_INGEST_SECONDS
        return {
            "ticker": key,
            "age_hours": round(hours, 1),
            "stale_warn": warn,
            "recommend_ingest": auto,
            "message": (
                f"News data for {key} is {hours:.1f}h old. "
                + ("Consider refreshing." if warn and not auto else "")
                + ("Recommend auto-ingest before querying." if auto else "")
            ),
        }

    def _load(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            return
        try:
            data = json.loads(self._state_path.read_text())
            if isinstance(data, dict):
                self._timestamps = {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}
        except Exception as exc:
            logger.warning("NewsFreshnessTracker: failed to load state: %s", exc)

    def _save(self) -> None:
        if self._state_path is None:
            return
        try:
            tmp = self._state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._timestamps))
            tmp.replace(self._state_path)
        except Exception as exc:
            logger.warning("NewsFreshnessTracker: failed to save state: %s", exc)
