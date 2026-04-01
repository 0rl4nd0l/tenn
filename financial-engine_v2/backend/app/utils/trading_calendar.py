"""
ASX trading calendar utilities using exchange_calendars XASX.
All date arithmetic needing ASX trading days should use this module.
"""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Union

import exchange_calendars as xcals
import pandas as pd


@lru_cache(maxsize=1)
def get_xasx_calendar() -> xcals.ExchangeCalendar:
    return xcals.get_calendar("XASX")


def is_trading_day(dt: Union[date, datetime, str]) -> bool:
    return get_xasx_calendar().is_session(pd.Timestamp(dt))


def previous_trading_day(dt: Union[date, datetime, str]) -> date:
    cal = get_xasx_calendar()
    ts = pd.Timestamp(dt)
    return cal.date_to_session(ts, direction="previous").date()


def trading_days_between(
    start: Union[date, str], end: Union[date, str],
) -> int:
    sessions = get_xasx_calendar().sessions_in_range(
        pd.Timestamp(start), pd.Timestamp(end),
    )
    return len(sessions)
