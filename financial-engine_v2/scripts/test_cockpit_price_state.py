#!/usr/bin/env python3
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.tools import ToolRouter  # noqa: E402


def _build_price_payload(
    count: int,
    market_time: datetime,
    *,
    duplicate_last: bool = False,
) -> dict:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history = []
    for i in range(count):
        # Upward drift with mild alternation keeps volatility non-zero.
        close = 100.0 + (i * 0.85) + (0.12 if i % 2 else -0.08)
        history.append(
            {
                "timestamp": (start + timedelta(days=i)).isoformat(),
                "close": close,
            }
        )
    if duplicate_last and history:
        history.append(
            {
                "timestamp": history[-1]["timestamp"],
                "close": history[-1]["close"] + 0.4,
            }
        )

    current_price = history[-1]["close"] if history else None
    prev_close = history[-2]["close"] if len(history) >= 2 else None
    return {
        "provider": "yahoo_finance",
        "ticker": "BHP",
        "symbol": "BHP.AX",
        "currency": "AUD",
        "current": {
            "price": current_price,
            "previous_close": prev_close,
            "market_time": market_time.isoformat(),
        },
        "history": history,
    }


class CockpitPriceStateTests(unittest.TestCase):
    def test_full_history_computes_metrics_and_bull_trend(self):
        payload = _build_price_payload(
            70,
            market_time=datetime.now(timezone.utc),
            duplicate_last=True,
        )
        state = ToolRouter._compute_price_state(payload)

        self.assertTrue(state["ok"])
        # Duplicate trailing timestamp should be deduped.
        self.assertEqual(state["history_points"], 70)
        self.assertFalse(state["insufficient_history"])
        self.assertEqual(state["trend_regime"], "bull")
        self.assertIsNotNone(state["ret_1d"])
        self.assertIsNotNone(state["ret_20d"])
        self.assertIsNotNone(state["ret_63d"])
        self.assertIsNotNone(state["sma20"])
        self.assertIsNotNone(state["sma50"])
        self.assertIsNotNone(state["vol_20d_ann"])
        self.assertFalse(state["stale_data"])
        self.assertIsNone(state["error"])

    def test_sparse_history_returns_none_for_long_windows(self):
        payload = _build_price_payload(
            5,
            market_time=datetime.now(timezone.utc),
        )
        state = ToolRouter._compute_price_state(payload)

        self.assertTrue(state["ok"])
        self.assertEqual(state["history_points"], 5)
        self.assertTrue(state["insufficient_history"])
        self.assertIsNone(state["ret_5d"])
        self.assertIsNone(state["ret_20d"])
        self.assertIsNone(state["ret_63d"])
        self.assertIsNone(state["sma20"])
        self.assertIsNone(state["sma50"])
        self.assertIsNone(state["vol_20d_ann"])

    def test_error_payload_produces_safe_defaults(self):
        payload = {
            "ok": False,
            "ticker": "BHP",
            "symbol": "BHP.AX",
            "currency": "AUD",
            "error": "backend unavailable",
        }
        state = ToolRouter._compute_price_state(payload)

        self.assertFalse(state["ok"])
        self.assertEqual(state["ticker"], "BHP")
        self.assertEqual(state["symbol"], "BHP.AX")
        self.assertEqual(state["error"], "backend unavailable")
        self.assertTrue(state["stale_data"])
        self.assertEqual(state["history_points"], 0)
        self.assertTrue(state["insufficient_history"])

    def test_stale_flag_trips_for_old_market_time(self):
        payload = _build_price_payload(
            30,
            market_time=datetime.now(timezone.utc) - timedelta(hours=120),
        )
        state = ToolRouter._compute_price_state(payload)

        self.assertTrue(state["ok"])
        self.assertTrue(state["stale_data"])
        self.assertIsNotNone(state["data_age_hours"])
        self.assertGreater(state["data_age_hours"], 96.0)


if __name__ == "__main__":
    unittest.main()
