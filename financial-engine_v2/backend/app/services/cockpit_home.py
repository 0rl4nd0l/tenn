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
PortfolioDataState = Literal["READY", "PARTIAL", "DEGRADED", "DATA_MISSING"]


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


@dataclass(frozen=True)
class PortfolioMissingSignal:
    section: str
    code: str
    message: str
    source_id: str | None = None
    evidence_id: str | None = None
    source_label: str | None = "local_personal_data"


@dataclass(frozen=True)
class PortfolioSnapshot:
    data_state: PortfolioDataState
    degraded: bool
    data_missing: list[PortfolioMissingSignal]
    as_of: str | None
    source_label: str
    total_value: float | None
    currency: str | None
    day_change: float | None
    day_change_percent: float | None
    coverage_percent: float | None
    holdings_count: int
    priced_holdings_count: int
    day_change_priced_holdings_count: int


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


def build_portfolio_snapshot(
    holdings: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> PortfolioSnapshot:
    """Aggregate cockpit-local holdings without FX conversion or inferred prices."""

    rows = [dict(row) for row in holdings]
    holdings_count = len(rows)
    as_of = _latest_text_timestamp([_row_text(row, "price_as_of") for row in rows])
    if as_of is None:
        as_of = _as_utc(now or datetime.now(timezone.utc)).isoformat()

    if holdings_count == 0:
        return PortfolioSnapshot(
            data_state="READY",
            degraded=False,
            data_missing=[],
            as_of=as_of,
            source_label="local_personal_data",
            total_value=0.0,
            currency=None,
            day_change=0.0,
            day_change_percent=0.0,
            coverage_percent=100.0,
            holdings_count=0,
            priced_holdings_count=0,
            day_change_priced_holdings_count=0,
        )

    missing: list[PortfolioMissingSignal] = []
    priced_rows = [
        row
        for row in rows
        if _row_float(row, "market_value") is not None
    ]
    priced_count = len(priced_rows)
    coverage_percent = round((priced_count / holdings_count) * 100, 1)
    if priced_count == 0:
        missing.append(
            PortfolioMissingSignal(
                section="portfolio",
                code="PORTFOLIO_TOTAL_PRICING_UNAVAILABLE",
                message=(
                    "No local holdings have deterministic current price and quantity fields, "
                    "so Cockpit Home did not aggregate a portfolio total."
                ),
            )
        )
    elif priced_count < holdings_count:
        missing.append(
            PortfolioMissingSignal(
                section="portfolio",
                code="PORTFOLIO_PRICING_PARTIAL",
                message=(
                    f"Only {priced_count}/{holdings_count} local holdings have deterministic "
                    "current price and quantity fields."
                ),
            )
        )

    total_value, currency, total_missing = _portfolio_total(priced_rows)
    if total_missing is not None:
        missing.append(total_missing)

    day_change, day_change_percent, day_change_count, day_missing = _portfolio_day_change(
        rows=rows,
        total_currency=currency,
    )
    missing.extend(day_missing)

    data_state: PortfolioDataState = "PARTIAL" if missing else "READY"
    return PortfolioSnapshot(
        data_state=data_state,
        degraded=False,
        data_missing=missing,
        as_of=as_of,
        source_label="local_personal_data",
        total_value=total_value,
        currency=currency,
        day_change=day_change,
        day_change_percent=day_change_percent,
        coverage_percent=coverage_percent,
        holdings_count=holdings_count,
        priced_holdings_count=priced_count,
        day_change_priced_holdings_count=day_change_count,
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


def _portfolio_total(
    priced_rows: list[dict[str, Any]],
) -> tuple[float | None, str | None, PortfolioMissingSignal | None]:
    if not priced_rows:
        return None, None, None

    currencies: list[str] = []
    for row in priced_rows:
        currency = _row_text(row, "price_currency").upper()
        if not currency:
            return (
                None,
                None,
                PortfolioMissingSignal(
                    section="portfolio",
                    code="PORTFOLIO_TOTAL_CURRENCY_MISSING",
                    message=(
                        "Priced local holdings did not all include a currency, "
                        "so Cockpit Home did not aggregate a currency-less total value."
                    ),
                ),
            )
        currencies.append(currency)

    unique_currencies = set(currencies)
    if len(unique_currencies) > 1:
        return (
            None,
            None,
            PortfolioMissingSignal(
                section="portfolio",
                code="PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS",
                message=(
                    "Priced local holdings use multiple currencies, so Cockpit Home "
                    "did not aggregate a mixed-currency total value."
                ),
            ),
        )

    total = sum(_row_float(row, "market_value") or 0.0 for row in priced_rows)
    return _round_money(total), currencies[0], None


def _portfolio_day_change(
    *,
    rows: list[dict[str, Any]],
    total_currency: str | None,
) -> tuple[float | None, float | None, int, list[PortfolioMissingSignal]]:
    if not rows:
        return 0.0, 0.0, 0, []

    eligible: list[tuple[float, float, str]] = []
    for row in rows:
        quantity = _row_float(row, "quantity")
        current_price = _row_float(row, "current_price")
        previous_close = _row_float(row, "previous_close")
        currency = _row_text(row, "price_currency").upper()
        if (
            quantity is None
            or current_price is None
            or previous_close is None
            or previous_close <= 0
            or not currency
        ):
            continue
        eligible.append(
            (
                quantity * (current_price - previous_close),
                quantity * previous_close,
                currency,
            )
        )

    if not eligible:
        return (
            None,
            None,
            0,
            [
                PortfolioMissingSignal(
                    section="portfolio",
                    code="PORTFOLIO_DAY_CHANGE_UNAVAILABLE",
                    message=(
                        "Local holdings do not include deterministic current price, "
                        "previous close, quantity, and currency fields for portfolio day-change."
                    ),
                )
            ],
        )

    currencies = {currency for _, _, currency in eligible}
    if len(currencies) > 1 or total_currency is None or total_currency not in currencies:
        return (
            None,
            None,
            len(eligible),
            [
                PortfolioMissingSignal(
                    section="portfolio",
                    code="PORTFOLIO_DAY_CHANGE_CURRENCY_AMBIGUOUS",
                    message=(
                        "Day-change-capable local holdings do not share the same single "
                        "currency as the portfolio total."
                    ),
                )
            ],
        )

    missing: list[PortfolioMissingSignal] = []
    if len(eligible) < len(rows):
        missing.append(
            PortfolioMissingSignal(
                section="portfolio",
                code="PORTFOLIO_DAY_CHANGE_PARTIAL",
                message=(
                    f"Only {len(eligible)}/{len(rows)} local holdings include deterministic "
                    "previous-close inputs for portfolio day-change."
                ),
            )
        )

    day_change = sum(value for value, _, _ in eligible)
    previous_total = sum(value for _, value, _ in eligible)
    day_change_percent = (
        round((day_change / previous_total) * 100, 2)
        if previous_total > 0
        else None
    )
    return _round_money(day_change), day_change_percent, len(eligible), missing


def _round_money(value: float) -> float:
    return float(f"{value:.2f}")


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
        target_route=_attention_target_route(action_type),
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


def _attention_target_route(action_type: str) -> str | None:
    """Map queued operational follow-ups to read-only Cockpit destinations."""

    normalized = action_type.strip().lower()
    if normalized == "watchlist_add_proposal" or normalized.startswith("watchlist_"):
        return "/watchlist"
    if normalized in {"review", "research_queue"}:
        return "/news"
    return None


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
