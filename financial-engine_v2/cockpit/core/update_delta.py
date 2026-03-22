from __future__ import annotations

import datetime
from typing import Any


def doc_delta_key(doc: dict[str, Any]) -> str:
    """Canonical deduplication key for an announcement doc."""
    if doc.get("document_id"):
        return f"id:{doc['document_id']}"
    if doc.get("sha256"):
        return f"sha256:{doc['sha256']}"
    return f"title:{doc.get('title', '')}"


def sync_human(sync: dict[str, Any]) -> str:
    """Human-readable sync status string."""
    status = sync.get("status", "unknown")
    age = sync.get("age_hours")
    if age is not None:
        return f"{status} ({age:.1f}h old)"
    return str(status)


def parse_timestamp_utc(ts: str | None) -> datetime.datetime | None:
    """Parse an ISO-8601 timestamp string to a UTC-aware datetime. Returns None on failure."""
    if not ts:
        return None
    try:
        # Python 3.10 doesn't support Z suffix in fromisoformat
        ts_clean = ts.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(ts_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def build_close_series(
    payload: dict[str, Any],
) -> list[tuple[datetime.datetime, float]]:
    """
    Extract a list of (timestamp, close_price) tuples from a price history payload.

    Expects `payload["history"]` as a list of dicts with "timestamp" and "close".
    Returns the series sorted by timestamp ascending.
    """
    history = payload.get("history", [])
    series: list[tuple[datetime.datetime, float]] = []
    for entry in history:
        dt = parse_timestamp_utc(str(entry.get("timestamp", "")))
        close = entry.get("close")
        if dt is not None and close is not None:
            series.append((dt, float(close)))
    series.sort(key=lambda x: x[0])
    return series


def compute_reaction_for_time(
    series: list[tuple[datetime.datetime, float]],
    *,
    published_at: datetime.datetime,
) -> dict[str, float] | None:
    """
    Compute post-announcement price reaction given a sorted (timestamp, close) series
    and the announcement publication timestamp.

    Finds the baseline close on or immediately after published_at date, then computes:
      - ret_1d: 1-day return (close[T+1] / close[T] - 1) * 100
      - ret_5d: 5-day return (close[T+5] / close[T] - 1) * 100

    Returns None if the series is too short or the anchor point is not found.
    """
    if not series:
        return None

    pub_date = published_at.date()

    # Find the anchor index: first entry whose date >= pub_date
    anchor_idx: int | None = None
    for i, (dt, _) in enumerate(series):
        if dt.date() >= pub_date:
            anchor_idx = i
            break

    if anchor_idx is None:
        return None

    base_price = series[anchor_idx][1]
    result: dict[str, float] = {}

    if anchor_idx + 1 < len(series):
        result["ret_1d"] = (series[anchor_idx + 1][1] / base_price - 1.0) * 100.0

    if anchor_idx + 5 < len(series):
        result["ret_5d"] = (series[anchor_idx + 5][1] / base_price - 1.0) * 100.0

    return result if result else None


def build_announcement_update_delta_summary(
    ticker: str,
    *,
    before: dict[str, Any],
    after: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Build a text summary and structured payload describing what changed in an
    announcement update run (before/after snapshots).

    Returns (text, payload).
    """
    before_docs = {doc_delta_key(d): d for d in before.get("docs", [])}
    after_docs = {doc_delta_key(d): d for d in after.get("docs", [])}

    new_keys = set(after_docs.keys()) - set(before_docs.keys())
    new_announcements = [after_docs[k] for k in sorted(new_keys)]

    before_count = before.get("doc_count", len(before.get("docs", [])))
    after_count = after.get("doc_count", len(after.get("docs", [])))

    before_sync = sync_human(before.get("sync", {}))
    after_sync = sync_human(after.get("sync", {}))

    lines = [
        f"Update complete for {ticker}.",
        f"Sync status: before {before_sync}, after {after_sync}.",
        f"New announcements indexed/downloaded: {len(new_announcements)}",
    ]
    for doc in new_announcements:
        title = doc.get("title", "(untitled)")
        published = doc.get("published_at", "")
        doc_class = doc.get("doc_class", "")
        tag = f" [{doc_class}]" if doc_class else ""
        lines.append(f"  • {title}{tag}" + (f" — {published}" if published else ""))

    text = "\n".join(lines)

    payload: dict[str, Any] = {
        "ticker": ticker,
        "doc_counts": {
            "before": before_count,
            "after": after_count,
            "new": len(new_announcements),
        },
        "sync_before": before.get("sync", {}),
        "sync_after": after.get("sync", {}),
        "new_announcements": new_announcements,
    }
    return text, payload
