#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


class CockpitChatTickerDetectionTests(unittest.TestCase):
    def _controller(self) -> ChatController:
        return ChatController(
            ollama_client=None,
            tool_router=None,
            action_registry=None,
        )

    def test_detect_ticker_price_forward_phrase(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("price bhp"), "BHP")

    def test_detect_ticker_price_reverse_phrase(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("bhp price"), "BHP")

    def test_detect_ticker_reverse_phrase_with_trailing_noise(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("bhp price xxx"), "BHP")

    def test_detect_ticker_ignores_month_token_in_on_date_phrase(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("what was bhp on Feb 3 2025"), "BHP")

    def test_detect_ticker_ignores_month_token_in_price_on_date_phrase(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("what was bhp price on Feb 3 2025"), "BHP")

    def test_detect_ticker_allows_month_like_symbol_without_date_context(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("analyse MAY"), "MAY")


if __name__ == "__main__":
    unittest.main()
