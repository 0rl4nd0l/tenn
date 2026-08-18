from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser


def _coerce_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = date_parser.isoparse(str(value))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_days(*, published_at: Any, now: Any = None) -> float:
    published_dt = _coerce_datetime(published_at)
    if published_dt is None:
        return 0.0
    now_dt = (
        _coerce_datetime(now) if now not in (None, "") else datetime.now(timezone.utc)
    )
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    delta = now_dt - published_dt
    return max(0.0, float(delta.total_seconds()) / 86400.0)


def compute_recency_decay(
    *,
    published_at: Any,
    half_life_days: float | int | None,
    now: Any = None,
) -> float:
    if half_life_days in (None, "", 0):
        return 1.0
    half_life = float(half_life_days)
    if half_life <= 0.0:
        return 1.0
    return math.exp(
        -math.log(2.0) * age_days(published_at=published_at, now=now) / half_life
    )


def compute_effective_weight(
    *,
    base_weight: float,
    published_at: Any,
    half_life_days: float | int | None,
    now: Any = None,
) -> float:
    return float(base_weight) * compute_recency_decay(
        published_at=published_at,
        half_life_days=half_life_days,
        now=now,
    )
