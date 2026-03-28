from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock

from cockpit.core.chat import ChatController, ResponseMode


class ChatTickerDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_agent_mode = os.environ.get("COCKPIT_AGENT_MODE")
        os.environ["COCKPIT_AGENT_MODE"] = "keyword"
        self.controller = ChatController(
            ollama_client=MagicMock(),
            tool_router=MagicMock(),
            action_registry=MagicMock(),
        )

    def tearDown(self) -> None:
        if self._old_agent_mode is None:
            os.environ.pop("COCKPIT_AGENT_MODE", None)
        else:
            os.environ["COCKPIT_AGENT_MODE"] = self._old_agent_mode

    def test_detect_ticker_ignores_generic_lowercase_words(self) -> None:
        self.assertIsNone(self.controller._detect_ticker("can you help with this", prior_ticker=None))

    def test_detect_ticker_accepts_cued_lowercase_ticker(self) -> None:
        self.assertEqual(self.controller._detect_ticker("tell me about csl", prior_ticker=None), "CSL")

    def test_resolve_ticker_context_reuses_prior_only_for_follow_up(self) -> None:
        ticker, explicit = self.controller._resolve_ticker_context("what about it", prior_ticker="BHP")
        self.assertEqual(ticker, "BHP")
        self.assertFalse(explicit)

    def test_resolve_ticker_context_does_not_force_prior_for_unrelated_chat(self) -> None:
        ticker, explicit = self.controller._resolve_ticker_context(
            "can you help me think this through",
            prior_ticker="BHP",
        )
        self.assertIsNone(ticker)
        self.assertFalse(explicit)

    def test_chart_request_with_prior_ticker_uses_follow_up_context(self) -> None:
        self.controller.action_registry.preview.return_value = MagicMock(
            command=["chart", "BHP"],
            estimated_impact="read-only",
            timeout_seconds=30,
        )
        self.controller.tool_router.build_candlestick_ohlc_lines.return_value = [
            {
                "timestamp": "2026-03-01T00:00:00Z",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.05,
                "volume": 1000,
            }
        ]

        response = self.controller.build_chat_response("show chart", prior_ticker="BHP")

        self.assertEqual(response.mode, ResponseMode.ACTION)
        self.assertIsNotNone(response.action_preview)
        assert response.action_preview is not None
        self.assertEqual(response.action_preview["action_id"], "show_candlestick")
        self.assertEqual(response.action_preview["args"]["ticker"], "BHP")

    def test_chart_request_without_ticker_asks_for_one(self) -> None:
        response = self.controller.build_chat_response("show chart", prior_ticker=None)

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("Which ticker do you want to chart?", response.text)


if __name__ == "__main__":
    unittest.main()
