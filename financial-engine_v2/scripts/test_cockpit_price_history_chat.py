#!/usr/bin/env python3
import os
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


@dataclass
class _Preview:
    command: list[str]
    estimated_impact: str
    timeout_seconds: int


class _ActionRegistryStub:
    def preview(self, action_id: str, args: dict) -> _Preview:  # noqa: ARG002
        return _Preview(
            command=["python3", "noop.py"],
            estimated_impact="none",
            timeout_seconds=30,
        )


def _build_price_payload() -> dict:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history = []
    close = 40.0
    for day in range(40):
        close += 0.25
        history.append(
            {
                "timestamp": (start + timedelta(days=day)).isoformat(),
                "close": round(close, 4),
            }
        )
    return {
        "ok": True,
        "ticker": "BHP",
        "symbol": "BHP.AX",
        "currency": "AUD",
        "current": {
            "price": history[-1]["close"],
            "previous_close": history[-2]["close"],
            "market_time": history[-1]["timestamp"],
        },
        "history": history,
    }


class _ToolRouterStub:
    def __init__(self) -> None:
        self.price_payload = _build_price_payload()
        self.price_state = {
            "ok": True,
            "ticker": "BHP",
            "symbol": "BHP.AX",
            "currency": "AUD",
        }

    def get_price_context_for_window(
        self,
        ticker: str,
        *,
        range_: str = "10y",
        interval: str = "1d",
        max_history_rows: int = 3000,
    ) -> dict:  # noqa: ARG002
        return {
            "price": self.price_payload,
            "price_state": self.price_state,
        }

    def gather_local_context(self, ticker: str | None, query: str, deep_mode: bool = False):  # noqa: ARG002
        class _Result:
            def __init__(self, payload):
                self.payload = payload

        return _Result(
            {
                "query": query,
                "ticker": ticker,
                "price": self.price_payload,
                "price_state": self.price_state,
                "docs": [],
                "reports": [],
                "matches": [],
            }
        )


class CockpitPriceHistoryChatTests(unittest.TestCase):
    def _controller(self) -> ChatController:
        return ChatController(
            ollama_client=None,
            tool_router=_ToolRouterStub(),
            action_registry=_ActionRegistryStub(),
        )

    def test_price_on_date_query_returns_historical_close(self):
        c = self._controller()
        response = c.build_chat_response("what was bhp price on 2025-01-10", enable_web=False)
        self.assertIn("Historical close for BHP.AX on 2025-01-10", response.text)
        self.assertIn("Matched candle date: 2025-01-10 (exact)", response.text)
        self.assertEqual(response.evidence[0]["details"]["price_history_query"]["kind"], "on_date")

    def test_price_range_query_returns_period_summary(self):
        c = self._controller()
        response = c.build_chat_response("bhp between 2025-01-05 and 2025-01-15", enable_web=False)
        self.assertIn("Historical range for BHP.AX: 2025-01-05 to 2025-01-15", response.text)
        self.assertIn("Period return (close-to-close):", response.text)
        self.assertEqual(response.evidence[0]["details"]["price_history_query"]["kind"], "range")

    def test_price_on_date_before_coverage_is_safe(self):
        c = self._controller()
        response = c.build_chat_response("what was bhp on 2024-12-01", enable_web=False)
        self.assertIn("No price history exists on or before 2024-12-01", response.text)

    def test_full_history_query_returns_coverage_summary(self):
        c = self._controller()
        response = c.build_chat_response("price history bhp", enable_web=False)
        self.assertIn("Full historical summary for BHP.AX", response.text)
        self.assertIn("Coverage: 2025-01-01 to 2025-02-09 (40 points)", response.text)
        self.assertEqual(response.evidence[0]["details"]["price_history_query"]["kind"], "full_summary")


if __name__ == "__main__":
    unittest.main()
