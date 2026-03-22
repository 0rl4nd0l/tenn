from __future__ import annotations

from typing import Any

# Alert thresholds
_RET_1D_THRESHOLD = 3.0        # % single-day move (absolute)
_RET_20D_THRESHOLD = -8.0      # % 20-day momentum
_VOL_20D_ANN_THRESHOLD = 40.0  # % annualised 20-day volatility
_DRAWDOWN_63D_THRESHOLD = -12.0  # % drawdown from 63-day high
_STALE_HOURS_THRESHOLD = 48.0  # hours before data is flagged stale


def evaluate_price_state_alerts(state: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate alert conditions from a price-state payload.

    Returns a dict with:
      - ok: bool
      - alerts: list of {kind, severity, message, value}
      - score: float (sum of per-alert weights)
    """
    if not state.get("ok"):
        return {
            "ok": False,
            "alerts": [
                {
                    "kind": "price_error",
                    "severity": "critical",
                    "message": str(state.get("error", "price state unavailable")),
                }
            ],
            "score": 0.0,
        }

    alerts: list[dict[str, Any]] = []
    score = 0.0

    ret_1d = state.get("ret_1d")
    if ret_1d is not None and abs(float(ret_1d)) >= _RET_1D_THRESHOLD:
        alerts.append({"kind": "ret_1d_move", "severity": "warning", "value": ret_1d,
                        "message": f"Single-day return {ret_1d:+.1f}% exceeds ±{_RET_1D_THRESHOLD}%"})
        score += 1.0

    ret_20d = state.get("ret_20d")
    if ret_20d is not None and float(ret_20d) <= _RET_20D_THRESHOLD:
        alerts.append({"kind": "ret_20d_momentum", "severity": "warning", "value": ret_20d,
                        "message": f"20-day momentum {ret_20d:+.1f}% below {_RET_20D_THRESHOLD}%"})
        score += 1.0

    vol = state.get("vol_20d_ann")
    if vol is not None and float(vol) >= _VOL_20D_ANN_THRESHOLD:
        alerts.append({"kind": "high_volatility", "severity": "info", "value": vol,
                        "message": f"Annualised 20-day volatility {vol:.1f}% ≥ {_VOL_20D_ANN_THRESHOLD}%"})
        score += 0.5

    drawdown = state.get("drawdown_from_63d_high")
    if drawdown is not None and float(drawdown) <= _DRAWDOWN_63D_THRESHOLD:
        alerts.append({"kind": "drawdown_63d", "severity": "warning", "value": drawdown,
                        "message": f"Drawdown from 63d high {drawdown:+.1f}% ≤ {_DRAWDOWN_63D_THRESHOLD}%"})
        score += 1.0

    if state.get("stale_data"):
        age = float(state.get("data_age_hours", 0))
        sev = "critical" if age >= _STALE_HOURS_THRESHOLD * 2 else "warning"
        alerts.append({"kind": "stale_data", "severity": sev, "value": age,
                        "message": f"Price data is stale ({age:.0f}h old)"})
        score += 1.0

    return {"ok": True, "alerts": alerts, "score": score}
