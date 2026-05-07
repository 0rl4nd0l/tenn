from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd

from app.utils.trading_calendar import get_xasx_calendar

ASX_TIMEZONE = "Australia/Melbourne"
MarketSessionState = Literal["PRE_MARKET", "OPEN", "POST_MARKET", "DEGRADED"]
AttentionQueueDataState = Literal["READY", "PARTIAL", "DEGRADED", "DATA_MISSING"]
AttentionQueuePriority = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class MarketSessionSnapshot:
    exchange: str
    timezone: str
    session: MarketSessionState
    session_date: str
    next_event_label: str
    next_event_at: str
    as_of: str


@dataclass(frozen=True)
class AttentionQueueMissingSignal:
    section: str
    code: str
    message: str
    source_id: str | None = None
    evidence_id: str | None = None
    source_label: str | None = "missing_required_evidence"


@dataclass(frozen=True)
class AttentionQueueItem:
    id: str
    title: str
    reason: str
    status: str
    priority: AttentionQueuePriority
    source_type: str
    created_at: str | None
    updated_at: str | None
    source_id: str | None = None
    target_route: str | None = None


@dataclass(frozen=True)
class AttentionQueueSnapshot:
    data_state: AttentionQueueDataState
    degraded: bool
    data_missing: list[AttentionQueueMissingSignal]
    as_of: str | None
    items: list[AttentionQueueItem]


def build_market_session_snapshot(now: datetime | None = None) -> MarketSessionSnapshot:
    """Return deterministic ASX session state from the backend-owned XASX calendar."""
    utc_now = _as_utc(now or datetime.now(timezone.utc))
    minute = pd.Timestamp(utc_now).floor("min")
    calendar = get_xasx_calendar()
    local_now = utc_now.astimezone(ZoneInfo(ASX_TIMEZONE))
    session_date = local_now.date().isoformat()

    if calendar.is_open_on_minute(minute):
        next_close = calendar.next_close(minute)
        return MarketSessionSnapshot(
            exchange="ASX",
            timezone=ASX_TIMEZONE,
            session="OPEN",
            session_date=session_date,
            next_event_label="ASX close",
            next_event_at=_timestamp_to_iso(next_close),
            as_of=utc_now.isoformat(),
        )

    next_open = calendar.next_open(minute)
    next_open_local_date = next_open.to_pydatetime().astimezone(ZoneInfo(ASX_TIMEZONE)).date()
    session = "PRE_MARKET" if next_open_local_date == local_now.date() else "POST_MARKET"
    return MarketSessionSnapshot(
        exchange="ASX",
        timezone=ASX_TIMEZONE,
        session=session,
        session_date=session_date,
        next_event_label="ASX open",
        next_event_at=_timestamp_to_iso(next_open),
        as_of=utc_now.isoformat(),
    )


def build_attention_queue_snapshot(
    state_store: Any,
    *,
    limit: int = 50,
    now: datetime | None = None,
) -> AttentionQueueSnapshot:
    """Return queued cockpit-local market-update follow-ups for Cockpit Home.

    The source rows are operational cockpit state, not canonical financial facts.
    This function performs no writes and does not synthesize items from prose.
    """

    max_items = max(1, min(int(limit or 50), 100))
    rows = state_store.list_market_update_followups(status="queued", limit=max_items)
    items: list[AttentionQueueItem] = []
    missing: list[AttentionQueueMissingSignal] = []

    for index, row in enumerate(rows):
        item = _market_update_followup_to_attention_item(row)
        if item is None:
            missing.append(
                AttentionQueueMissingSignal(
                    section="attention_queue",
                    code="ATTENTION_QUEUE_ROW_INVALID",
                    message=(
                        "A queued market-update follow-up row did not include "
                        "the deterministic fields required by Cockpit Home."
                    ),
                    evidence_id=str(index),
                    source_label="degraded_runtime",
                )
            )
            continue
        items.append(item)

    as_of = _latest_text_timestamp([item.updated_at or item.created_at for item in items])
    if as_of is None:
        as_of = _as_utc(now or datetime.now(timezone.utc)).isoformat()

    data_state: AttentionQueueDataState = "PARTIAL" if missing else "READY"
    return AttentionQueueSnapshot(
        data_state=data_state,
        degraded=False,
        data_missing=missing,
        as_of=as_of,
        items=items,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp_to_iso(value: pd.Timestamp) -> str:
    timestamp = value.to_pydatetime()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat()


def _market_update_followup_to_attention_item(row: Any) -> AttentionQueueItem | None:
    followup_id = _row_text(row, "followup_id")
    action_type = _row_text(row, "action_type")
    status = _row_text(row, "status") or "queued"
    if not followup_id or not action_type:
        return None

    ticker = _row_text(row, "ticker")
    reason_payload = _row_dict(row, "reason")
    priority_score = _row_float(row, "priority_score")
    created_at = _row_text(row, "created_at") or None

    return AttentionQueueItem(
        id=f"market_update_followup:{followup_id}",
        title=_attention_title(action_type=action_type, ticker=ticker),
        reason=_attention_reason(action_type=action_type, reason=reason_payload),
        status=status,
        priority=_priority_from_score(priority_score),
        source_type="market_update_followup",
        created_at=created_at,
        updated_at=created_at,
        source_id=None,
        target_route=None,
    )


def _attention_title(*, action_type: str, ticker: str) -> str:
    action_label = action_type.replace("_", " ").strip() or "review"
    if ticker:
        return f"{ticker}: {action_label}"
    return action_label


def _attention_reason(*, action_type: str, reason: dict[str, Any]) -> str:
    reasons = reason.get("reasons")
    if isinstance(reasons, list):
        text_reasons = [str(item).strip() for item in reasons if str(item).strip()]
        if text_reasons:
            return "; ".join(text_reasons[:2])

    note = str(reason.get("note") or "").strip()
    if note:
        return note

    score = reason.get("score")
    if score is not None:
        return f"Queued from market update with score {score}."

    return f"Queued market-update follow-up action: {action_type}."


def _priority_from_score(value: float | None) -> AttentionQueuePriority:
    if value is None:
        return "low"
    if value >= 0.75:
        return "high"
    if value >= 0.5:
        return "medium"
    return "low"


def _row_text(row: Any, key: str) -> str:
    value = _row_value(row, key)
    return str(value or "").strip()


def _row_float(row: Any, key: str) -> float | None:
    value = _row_value(row, key)
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not pd.notna(parsed):
        return None
    return parsed


def _row_dict(row: Any, key: str) -> dict[str, Any]:
    value = _row_value(row, key)
    return value if isinstance(value, dict) else {}


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)


def _latest_text_timestamp(values: list[str | None]) -> str | None:
    timestamps: list[tuple[float, str]] = []
    for value in values:
        raw = str(value or "").strip()
        if not raw:
            continue
        try:
            parsed = pd.Timestamp(raw)
        except ValueError:
            continue
        if pd.isna(parsed):
            continue
        timestamps.append((parsed.timestamp(), raw))
    if not timestamps:
        return None
    timestamps.sort(key=lambda item: item[0], reverse=True)
    return timestamps[0][1]
