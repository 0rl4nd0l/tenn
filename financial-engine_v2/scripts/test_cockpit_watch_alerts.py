#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.alerts import evaluate_price_state_alerts  # noqa: E402
from cockpit.storage.state import StateStore  # noqa: E402


class CockpitWatchAndAlertsTests(unittest.TestCase):
    def test_watchlist_persistence_ops(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.db"
            store = StateStore(str(db_path))
            now = datetime.now(timezone.utc).isoformat()

            self.assertTrue(store.add_watch_ticker("bhp", now))
            self.assertTrue(store.add_watch_ticker("csl", now))
            # duplicate insert ignored
            self.assertFalse(store.add_watch_ticker("BHP", now))

            rows = store.list_watch_tickers()
            tickers = [row["ticker"] for row in rows]
            self.assertEqual(tickers, ["BHP", "CSL"])

            self.assertTrue(store.remove_watch_ticker("CSL"))
            self.assertFalse(store.remove_watch_ticker("CSL"))
            self.assertEqual([row["ticker"] for row in store.list_watch_tickers()], ["BHP"])

            removed = store.clear_watch_tickers()
            self.assertEqual(removed, 1)
            self.assertEqual(store.list_watch_tickers(), [])

    def test_update_events_persistence_ops(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.db"
            store = StateStore(str(db_path))
            now = datetime.now(timezone.utc).isoformat()

            store.add_update_event(
                thread_id="global-main",
                ticker="BHP",
                action_id="update_ticker_financials",
                status="completed",
                summary={"delta": {"doc_counts": {"new": 2}}},
                created_at=now,
            )
            store.add_update_event(
                thread_id="global-main",
                ticker="CSL",
                action_id="update_ticker_financials",
                status="failed",
                summary={"error": "network"},
                created_at=now,
            )

            bhp = store.list_update_events("global-main", ticker="BHP", limit=5)
            self.assertEqual(len(bhp), 1)
            self.assertEqual(bhp[0]["ticker"], "BHP")
            self.assertEqual(bhp[0]["status"], "completed")
            self.assertEqual(bhp[0]["summary"]["delta"]["doc_counts"]["new"], 2)

            completed = store.list_update_events("global-main", limit=10, status="completed")
            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0]["ticker"], "BHP")

    def test_alerts_trigger_for_large_move_and_stale(self):
        state = {
            "ok": True,
            "ticker": "BHP",
            "symbol": "BHP.AX",
            "ret_1d": 4.2,
            "ret_20d": -11.5,
            "vol_20d_ann": 48.0,
            "drawdown_from_63d_high": -14.2,
            "stale_data": True,
            "data_age_hours": 120.0,
        }
        evaluated = evaluate_price_state_alerts(state)
        kinds = {item.get("kind") for item in evaluated["alerts"]}
        self.assertIn("ret_1d_move", kinds)
        self.assertIn("ret_20d_momentum", kinds)
        self.assertIn("high_volatility", kinds)
        self.assertIn("drawdown_63d", kinds)
        self.assertIn("stale_data", kinds)
        self.assertGreater(evaluated["score"], 3.0)

    def test_alerts_error_path(self):
        state = {
            "ok": False,
            "ticker": "BHP",
            "error": "market price provider returned HTTP 404",
        }
        evaluated = evaluate_price_state_alerts(state)
        self.assertFalse(evaluated["ok"])
        self.assertEqual(len(evaluated["alerts"]), 1)
        self.assertEqual(evaluated["alerts"][0]["kind"], "price_error")
        self.assertEqual(evaluated["alerts"][0]["severity"], "critical")


if __name__ == "__main__":
    unittest.main()
