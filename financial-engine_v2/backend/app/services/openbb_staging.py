from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.openbb_snapshots import OpenBBFundamentalSnapshot, OpenBBPriceSnapshot


def _normalize_upper(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    return text or None


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _stable_hash(payload: dict[str, Any], params: dict[str, Any]) -> str:
    normalized = {
        "payload": payload,
        "params": params,
    }
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def persist_price_snapshot(
    db: Session,
    *,
    ticker: str,
    exchange: str,
    payload: dict[str, Any],
    params: dict[str, Any],
) -> bool:
    request_hash = _stable_hash(payload, params)
    row = OpenBBPriceSnapshot(
        ticker=_normalize_upper(ticker) or "",
        exchange=_normalize_upper(exchange),
        symbol=_normalize_upper(payload.get("symbol")),
        provider=_normalize_text(payload.get("provider_source") or payload.get("provider")),
        dataset_type="price_historical",
        request_hash=request_hash,
        payload=payload,
        captured_at=datetime.now(timezone.utc),
    )
    try:
        db.add(row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def persist_fundamental_snapshot(
    db: Session,
    *,
    ticker: str,
    exchange: str,
    dataset_type: str,
    payload: dict[str, Any],
    params: dict[str, Any],
    statement_type: str | None = None,
    period: str | None = None,
) -> bool:
    request_hash = _stable_hash(payload, params)
    row = OpenBBFundamentalSnapshot(
        ticker=_normalize_upper(ticker) or "",
        exchange=_normalize_upper(exchange),
        symbol=_normalize_upper(payload.get("symbol")),
        provider=_normalize_text(payload.get("provider_source") or payload.get("provider")),
        dataset_type=_normalize_text(dataset_type) or "unknown",
        statement_type=_normalize_text(statement_type),
        period=_normalize_text(period),
        request_hash=request_hash,
        payload=payload,
        captured_at=datetime.now(timezone.utc),
    )
    try:
        db.add(row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
