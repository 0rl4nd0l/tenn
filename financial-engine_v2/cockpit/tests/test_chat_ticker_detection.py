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

    # ------------------------------------------------------------------
    # Stopword expansion — common English words must not be detected as tickers
    # ------------------------------------------------------------------

    def test_stopwords_block_common_english_words(self) -> None:
        """Words like WHY, ARE, FAIL must not be treated as tickers."""
        for word in ("why", "are", "fail", "was", "has", "got", "get", "try", "end", "who"):
            with self.subTest(word=word):
                self.assertIsNone(
                    self.controller._detect_ticker(word, prior_ticker=None),
                    f"'{word}' should not be detected as a ticker",
                )

    def test_stopwords_block_uppercase_common_words(self) -> None:
        """Even when typed in all-caps, common words must not be tickers."""
        for word in ("WHY", "ARE", "FAIL", "SURE", "OKAY"):
            with self.subTest(word=word):
                self.assertIsNone(
                    self.controller._detect_ticker(word, prior_ticker=None),
                    f"'{word}' (all-caps) should not be detected as a ticker",
                )

    # ------------------------------------------------------------------
    # _FOLLOW_UP_RE — narrowed to topic-referential terms only
    # ------------------------------------------------------------------

    def test_follow_up_does_not_match_discourse_markers(self) -> None:
        """Conversational fillers must NOT reattach prior ticker."""
        for msg in ("sure", "okay", "yes", "go ahead", "right", "also", "continue"):
            with self.subTest(msg=msg):
                ticker, explicit = self.controller._resolve_ticker_context(msg, prior_ticker="BHP")
                self.assertIsNone(
                    ticker,
                    f"'{msg}' should not reattach prior ticker BHP",
                )

    def test_follow_up_matches_financial_terms(self) -> None:
        """Financial/entity-referential terms SHOULD reattach prior ticker."""
        for msg in ("what about their financials", "tell me more", "earnings", "revenue", "outlook"):
            with self.subTest(msg=msg):
                ticker, explicit = self.controller._resolve_ticker_context(msg, prior_ticker="BHP")
                self.assertEqual(
                    ticker, "BHP",
                    f"'{msg}' should reattach prior ticker BHP",
                )
                self.assertFalse(explicit)

    # ------------------------------------------------------------------
    # Compound messages: conversational preamble + real ticker
    # ------------------------------------------------------------------

    def test_compound_message_extracts_real_ticker(self) -> None:
        """'sure, but what about BHP' must still detect BHP."""
        ticker = self.controller._detect_ticker("sure, but what about BHP", prior_ticker=None)
        self.assertEqual(ticker, "BHP")

    def test_real_tickers_still_detected(self) -> None:
        """Core regression: single-word tickers must still be detected."""
        for msg, expected in (("BHP", "BHP"), ("CSL", "CSL"), ("bhp", "BHP")):
            with self.subTest(msg=msg):
                ticker = self.controller._detect_ticker(msg, prior_ticker=None)
                self.assertEqual(ticker, expected)

    def test_cued_ticker_in_sentence(self) -> None:
        """Tickers with a cue word (about, price, news) must still be detected."""
        for msg, expected in (
            ("arr price", "ARR"),
            ("csl news", "CSL"),
            ("tell me about bhp", "BHP"),
        ):
            with self.subTest(msg=msg):
                ticker = self.controller._detect_ticker(msg, prior_ticker=None)
                self.assertEqual(ticker, expected, f"'{msg}' should detect {expected}")

    def test_conversational_sentence_no_ticker(self) -> None:
        """Full conversational sentences must not produce a ticker."""
        for msg in (
            "why did ingestion fail",
            "hi how are you",
            "can you help me debug this",
        ):
            with self.subTest(msg=msg):
                self.assertIsNone(
                    self.controller._detect_ticker(msg, prior_ticker=None),
                    f"'{msg}' should not produce a ticker",
                )


if __name__ == "__main__":
    unittest.main()
