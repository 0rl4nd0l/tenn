from __future__ import annotations

from typing import Any


DEFAULT_ALERT_THRESHOLDS: dict[str, float] = {
    "ret_1d_abs": 3.0,
    "ret_20d_abs": 10.0,
    "vol_20d_ann": 45.0,
    "drawdown_63d": -12.0,
}

_SEVERITY_WEIGHT = {
    "info": 1.0,
    "warning": 2.0,
    "critical": 3.0,
}


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def evaluate_price_state_alerts(
    price_state: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    cfg = dict(DEFAULT_ALERT_THRESHOLDS)
    if isinstance(thresholds, dict):
        for key, value in thresholds.items():
            parsed = _safe_float(value)
            if parsed is not None:
                cfg[key] = parsed

    ticker = str((price_state or {}).get("ticker") or "").strip().upper()
    symbol = str((price_state or {}).get("symbol") or "").strip().upper() or ticker
    alerts: list[dict[str, Any]] = []

    if not isinstance(price_state, dict) or not bool(price_state.get("ok")):
        error = str((price_state or {}).get("error") or "price lookup failed")
        alerts.append(
            {
                "kind": "price_error",
                "severity": "critical",
                "message": error,
                "value": None,
            }
        )
        return {
            "ticker": ticker,
            "symbol": symbol,
            "ok": False,
            "alerts": alerts,
            "score": _SEVERITY_WEIGHT["critical"],
        }

    ret_1d = _safe_float(price_state.get("ret_1d"))
    if ret_1d is not None and abs(ret_1d) >= cfg["ret_1d_abs"]:
        direction = "up" if ret_1d > 0 else "down"
        alerts.append(
            {
                "kind": "ret_1d_move",
                "severity": "warning",
                "message": f"1D move {direction} {ret_1d:+.2f}%",
                "value": ret_1d,
            }
        )

    ret_20d = _safe_float(price_state.get("ret_20d"))
    if ret_20d is not None and abs(ret_20d) >= cfg["ret_20d_abs"]:
        direction = "up" if ret_20d > 0 else "down"
        alerts.append(
            {
                "kind": "ret_20d_momentum",
                "severity": "warning",
                "message": f"20D momentum {direction} {ret_20d:+.2f}%",
                "value": ret_20d,
            }
        )

    vol_20d_ann = _safe_float(price_state.get("vol_20d_ann"))
    if vol_20d_ann is not None and vol_20d_ann >= cfg["vol_20d_ann"]:
        alerts.append(
            {
                "kind": "high_volatility",
                "severity": "warning",
                "message": f"20D annualized volatility {vol_20d_ann:.2f}%",
                "value": vol_20d_ann,
            }
        )

    drawdown = _safe_float(price_state.get("drawdown_from_63d_high"))
    if drawdown is not None and drawdown <= cfg["drawdown_63d"]:
        alerts.append(
            {
                "kind": "drawdown_63d",
                "severity": "warning",
                "message": f"Drawdown from 63D high {drawdown:+.2f}%",
                "value": drawdown,
            }
        )

    if price_state.get("stale_data") is True:
        age = _safe_float(price_state.get("data_age_hours"))
        age_txt = f"{age:.1f}h" if age is not None else "unknown"
        alerts.append(
            {
                "kind": "stale_data",
                "severity": "critical",
                "message": f"Price data stale ({age_txt})",
                "value": age,
            }
        )

    score = 0.0
    for item in alerts:
        sev = str(item.get("severity") or "info").lower()
        score = max(score, _SEVERITY_WEIGHT.get(sev, 1.0))
        value = _safe_float(item.get("value"))
        if value is not None:
            score += min(abs(value) / 100.0, 2.0)

    return {
        "ticker": ticker,
        "symbol": symbol,
        "ok": True,
        "alerts": alerts,
        "score": round(score, 3),
    }
