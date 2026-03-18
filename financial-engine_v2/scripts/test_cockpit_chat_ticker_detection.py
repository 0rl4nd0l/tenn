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

    def test_detect_ticker_news_about_phrase(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("give me some news about bhp"), "BHP")

    def test_detect_ticker_news_about_overrides_prior_ticker(self):
        c = self._controller()
        self.assertEqual(c._detect_ticker("give me some news about bhp", prior_ticker="BP"), "BHP")

    def test_detect_ticker_asx_news_market_scope(self):
        c = self._controller()
        self.assertIsNone(c._detect_ticker("asx news today"))
        self.assertFalse(c._is_global_announcement_request("asx news today"))
        self.assertTrue(c._is_global_news_request("asx news today"))

    def test_detect_ticker_run_news_ingestion_does_not_use_run(self):
        c = self._controller()
        self.assertIsNone(c._detect_ticker("run news ingestion"))


if __name__ == "__main__":
    unittest.main()
