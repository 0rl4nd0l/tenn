from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

import pandas as pd

from app.utils.trading_calendar import get_xasx_calendar

ASX_TIMEZONE = "Australia/Melbourne"
MarketSessionState = Literal["PRE_MARKET", "OPEN", "POST_MARKET", "DEGRADED"]


@dataclass(frozen=True)
class MarketSessionSnapshot:
    exchange: str
    timezone: str
    session: MarketSessionState
    session_date: str
    next_event_label: str
    next_event_at: str
    as_of: str


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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp_to_iso(value: pd.Timestamp) -> str:
    timestamp = value.to_pydatetime()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat()
