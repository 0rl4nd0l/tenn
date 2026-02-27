from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def doc_delta_key(row: dict[str, Any]) -> str:
    if not isinstance(row, dict):
        return ""
    doc_id = str(row.get("document_id") or "").strip()
    if doc_id:
        return f"id:{doc_id}"
    published = str(row.get("published_at") or "").strip()
    title = str(row.get("title") or "").strip()
    source = str(row.get("source_url") or "").strip()
    return f"fallback:{published}|{title}|{source}"


def compact_doc_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row.get("document_id"),
        "ticker": row.get("ticker"),
        "doc_class": row.get("doc_class"),
        "doc_subtype": row.get("doc_subtype"),
        "published_at": row.get("published_at"),
        "title": row.get("title"),
        "source_url": row.get("source_url"),
        "pdf_path": row.get("pdf_path"),
    }


def sync_human(sync: dict[str, Any]) -> str:
    if not isinstance(sync, dict):
        return "unknown"
    status = str(sync.get("status") or "unknown").strip().lower() or "unknown"
    try:
        age = float(sync.get("age_hours"))
        return f"{status} ({age:.1f}h old)"
    except Exception:
        return status


def build_announcement_update_delta_summary(
    ticker: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    before_docs = before.get("docs") if isinstance(before.get("docs"), list) else []
    after_docs = after.get("docs") if isinstance(after.get("docs"), list) else []
    before_keys = {doc_delta_key(row) for row in before_docs if isinstance(row, dict)}
    before_keys.discard("")
    new_rows = [
        row
        for row in after_docs
        if isinstance(row, dict) and doc_delta_key(row) and doc_delta_key(row) not in before_keys
    ]

    before_sync = before.get("sync") if isinstance(before.get("sync"), dict) else {}
    after_sync = after.get("sync") if isinstance(after.get("sync"), dict) else {}
    before_count = int(before.get("doc_count") or len(before_docs))
    after_count = int(after.get("doc_count") or len(after_docs))
    new_docs = [compact_doc_row(row) for row in new_rows]

    lines = [f"Update complete for {ticker}."]
    lines.append(f"Announcement freshness: before {sync_human(before_sync)} -> after {sync_human(after_sync)}.")
    lines.append(f"Indexed announcement count: before {before_count}, after {after_count}.")
    if new_docs:
        lines.append(f"New announcements indexed/downloaded: {len(new_docs)}")
        for row in new_docs[:8]:
            date = str(row.get("published_at") or "").split(" ")[0]
            doc_class = str(row.get("doc_class") or "").strip().lower()
            title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
            prefix = f"- {date}: " if date else "- "
            if doc_class:
                prefix += f"[{doc_class}] "
            lines.append(prefix + title)
        if len(new_docs) > 8:
            lines.append(f"- ... {len(new_docs) - 8} more")
    else:
        lines.append("No new announcements were indexed/downloaded in this run.")

    payload = {
        "ticker": ticker,
        "announcement_sync_before": before_sync,
        "announcement_sync_after": after_sync,
        "doc_counts": {
            "before": before_count,
            "after": after_count,
            "new": len(new_docs),
        },
        "new_announcements": new_docs[:50],
    }
    return "\n".join(lines), payload


def parse_timestamp_utc(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def build_close_series(price_payload: dict[str, Any]) -> list[tuple[datetime, float]]:
    history = price_payload.get("history") if isinstance(price_payload, dict) else []
    if not isinstance(history, list):
        return []
    deduped: dict[str, tuple[datetime, float]] = {}
    for row in history:
        if not isinstance(row, dict):
            continue
        ts = parse_timestamp_utc(row.get("timestamp"))
        close = _safe_float(row.get("close"))
        if ts is None or close is None:
            continue
        deduped[ts.isoformat()] = (ts, close)
    out = list(deduped.values())
    out.sort(key=lambda item: item[0].timestamp())
    return out


def compute_reaction_for_time(
    close_series: list[tuple[datetime, float]],
    published_at: datetime,
) -> dict[str, Any] | None:
    if not close_series:
        return None

    anchor_idx = -1
    for idx, (ts, _) in enumerate(close_series):
        if ts <= published_at:
            anchor_idx = idx
        else:
            break
    if anchor_idx < 0:
        return None

    anchor_time, anchor_close = close_series[anchor_idx]
    if anchor_close == 0:
        return None

    def _ret(days: int) -> float | None:
        target_idx = anchor_idx + days
        if target_idx >= len(close_series):
            return None
        target_close = close_series[target_idx][1]
        return ((target_close / anchor_close) - 1.0) * 100.0

    return {
        "anchor_time_utc": anchor_time.isoformat(),
        "anchor_close": anchor_close,
        "ret_1d": _ret(1),
        "ret_5d": _ret(5),
        "ret_20d": _ret(20),
    }
