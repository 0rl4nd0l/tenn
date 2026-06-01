from __future__ import annotations

import os
import unittest
from datetime import datetime as real_datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

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
        self.assertIsNone(
            self.controller._detect_ticker("can you help with this", prior_ticker=None)
        )

    def test_marketplace_ui_mode_bypasses_ticker_backfill_shortcuts(self) -> None:
        self.controller.ollama_client.chat.return_value = (
            '{"assistant_message":"What budget do you have?","draft":{},'
            '"missing_fields":["budget"],"ready_to_create":false,'
            '"suggested_action":"ask_followup"}'
        )

        response = self.controller.build_chat_response(
            "JSON",
            ui_mode="marketplace",
        )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIsNone(response.action_preview)
        self.assertIn("What budget do you have?", response.text)
        self.controller.ollama_client.chat.assert_called_once()

    def test_marketplace_ui_mode_uses_hybrid_router_when_available(self) -> None:
        hybrid_router = MagicMock()
        hybrid_router.chat.return_value = (
            '{"assistant_message":"Need budget.","draft":{},'
            '"missing_fields":["budget"],"ready_to_create":false,'
            '"suggested_action":"ask_followup"}'
        )
        hybrid_router.last_attempt_metadata.return_value = {
            "source": "api",
            "model": "claude-test",
            "latency_ms": 123,
            "cost_usd": 0.01,
            "routing_reason": "force:api",
        }
        hybrid_router.total_cost_usd.return_value = 0.01
        self.controller._hybrid_router = hybrid_router

        response = self.controller.build_chat_response(
            "/cloud find a used GPU in Victoria",
            ui_mode="marketplace",
        )

        self.assertEqual(response.text, '{"assistant_message":"Need budget.","draft":{},"missing_fields":["budget"],"ready_to_create":false,"suggested_action":"ask_followup"}')
        self.assertEqual(response.routing_metadata["source"], "api")
        hybrid_router.chat.assert_called_once()
        self.controller.ollama_client.chat.assert_not_called()

    def test_detect_ticker_accepts_cued_lowercase_ticker(self) -> None:
        self.assertEqual(
            self.controller._detect_ticker("tell me about csl", prior_ticker=None),
            "CSL",
        )

    def test_detect_ticker_accepts_recent_update_wording(self) -> None:
        self.assertEqual(
            self.controller._detect_ticker(
                "what happened with bhp this week", prior_ticker=None
            ),
            "BHP",
        )

    def test_resolve_ticker_context_reuses_prior_only_for_follow_up(self) -> None:
        ticker, explicit = self.controller._resolve_ticker_context(
            "what about it", prior_ticker="BHP"
        )
        self.assertEqual(ticker, "BHP")
        self.assertFalse(explicit)

    def test_source_gather_followup_reuses_prior_ticker(self) -> None:
        ticker, explicit = self.controller._resolve_ticker_context(
            "Okay gather the sources", prior_ticker="PPT"
        )

        self.assertEqual(ticker, "PPT")
        self.assertFalse(explicit)

    def test_resolve_ticker_context_does_not_force_prior_for_unrelated_chat(
        self,
    ) -> None:
        ticker, explicit = self.controller._resolve_ticker_context(
            "can you help me think this through",
            prior_ticker="BHP",
        )
        self.assertIsNone(ticker)
        self.assertFalse(explicit)

    def test_backend_prefix_does_not_become_ticker(self) -> None:
        ticker, explicit = self.controller._resolve_ticker_context(
            "/cloud news today?",
            prior_ticker=None,
        )
        self.assertIsNone(ticker)
        self.assertFalse(explicit)

    def test_audit_prompt_ui_acronym_does_not_become_ticker(self) -> None:
        ticker, explicit = self.controller._resolve_ticker_context(
            "UI_AUDIT_GEMINI 2026-05-26: From the current Cockpit UI, "
            "what should I review first today across holdings, watchlist, "
            "and recent news? Use only visible/source-backed Tenn context "
            "and say DATA_MISSING where needed.",
            prior_ticker=None,
        )
        self.assertIsNone(ticker)
        self.assertFalse(explicit)

    def test_audit_marker_variants_do_not_become_tickers_in_prose(self) -> None:
        prompts = (
            "UI AUDIT GEMINI what should I review across holdings and recent news",
            "UI-AUDIT-GEMINI what should I review across holdings and recent news",
            "UI/AUDIT/GEMINI what should I review across holdings and recent news",
            "from Cockpit UI what should I review across holdings and recent news",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                ticker, explicit = self.controller._resolve_ticker_context(
                    prompt,
                    prior_ticker=None,
                )
                self.assertIsNone(ticker)
                self.assertFalse(explicit)

    def test_explicit_ui_ticker_forms_still_route(self) -> None:
        for prompt in ("ASX:UI news", "$UI news", "UI.AX news"):
            with self.subTest(prompt=prompt):
                ticker, explicit = self.controller._resolve_ticker_context(
                    prompt,
                    prior_ticker=None,
                )
                self.assertEqual(ticker, "UI")
                self.assertTrue(explicit)

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

    def test_direct_ticker_news_shortcircuits_without_llm(self) -> None:
        self.controller.tool_router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "BHP copper update",
                    "published_at": "2026-04-08T03:00:00Z",
                    "url": "https://example.com/bhp",
                    "text": "BHP expanded its copper footprint.",
                }
            ],
        }

        response = self.controller.build_chat_response("bhp news", prior_ticker=None)

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("Recent BHP-linked news:", response.text)
        self.assertIn("BHP copper update", response.text)
        self.controller.tool_router.get_news_context.assert_called_once_with(
            query="BHP",
            top_k=5,
            ticker="BHP",
        )

    def test_strict_local_news_context_prompt_uses_news_shortcircuit(self) -> None:
        self.controller.tool_router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "BHP local news update",
                    "published_at": "2026-05-24T03:00:00Z",
                    "url": "https://example.com/bhp-local-news",
                    "text": "BHP was covered in local market news.",
                }
            ],
        }

        response = self.controller.build_chat_response(
            "Use only local_news_context for BHP", prior_ticker=None
        )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("Recent BHP-linked news:", response.text)
        self.assertIn("BHP local news update", response.text)
        self.controller.tool_router.get_news_context.assert_called_once_with(
            query="BHP",
            top_k=5,
            ticker="BHP",
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_natural_local_news_prompts_use_news_shortcircuit(self) -> None:
        prompts = [
            ("latest local news for A2M", "A2M"),
            ("latest local news for BHP", "BHP"),
            ("what is the latest news on CSL", "CSL"),
            ("recent local news for BHP", "BHP"),
            ("show me local news for A2M", "A2M"),
            ("any recent company news for CSL", "CSL"),
        ]
        self.controller.tool_router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "Local news update",
                    "published_at": "2026-05-24T03:00:00Z",
                    "url": "https://example.com/local-news",
                    "text": "The company was covered in local market news.",
                }
            ],
        }

        for prompt, ticker in prompts:
            with self.subTest(prompt=prompt):
                self.controller.tool_router.get_news_context.reset_mock()
                self.controller.ollama_client.chat.reset_mock()

                response = self.controller.build_chat_response(
                    prompt, prior_ticker=None
                )

                self.assertEqual(response.mode, ResponseMode.FAST)
                self.assertIn(f"Recent {ticker}-linked news:", response.text)
                self.assertIn("Local news update", response.text)
                self.controller.tool_router.get_news_context.assert_called_once_with(
                    query=ticker,
                    top_k=5,
                    ticker=ticker,
                )
                self.controller.ollama_client.chat.assert_not_called()

    def test_natural_news_shortcircuit_does_not_capture_non_news_controls(
        self,
    ) -> None:
        prompts = [
            "summarise BHP financial performance",
            "latest Appendix 4C for XRO",
            "BHP share price news",
            "latest on BHP",
        ]

        for prompt in prompts:
            with self.subTest(prompt=prompt):
                ticker, _ = self.controller._resolve_ticker_context(
                    prompt, prior_ticker=None
                )
                self.controller.tool_router.get_news_context.reset_mock()

                response = self.controller._try_news_shortcircuit(prompt, ticker)

                self.assertIsNone(response)
                self.controller.tool_router.get_news_context.assert_not_called()

    def test_ticker_leading_price_prompt_hits_price_fast_path(self) -> None:
        self.controller.tool_router.get_price_context_for_window.return_value = {
            "price": {
                "symbol": "JBH.AX",
                "recent_history": [
                    {"timestamp": "2026-04-17T00:00:00Z", "close": 92.15},
                    {"timestamp": "2026-04-18T00:00:00Z", "close": 93.40},
                ],
            }
        }

        response = self.controller.build_chat_response("JBH price?", prior_ticker=None)

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("**JBH.AX** last close: **93.4000** (2026-04-18)", response.text)
        self.assertNotIn("backfill", response.text.lower())
        self.controller.ollama_client.chat.assert_not_called()

    def test_ticker_leading_price_today_prompt_hits_price_fast_path(self) -> None:
        self.controller.tool_router.get_price_context_for_window.return_value = {
            "price": {
                "symbol": "EOS.AX",
                "recent_history": [
                    {"timestamp": "2026-04-29T00:00:00Z", "close": 8.88},
                    {"timestamp": "2026-04-30T00:00:00Z", "close": 9.06},
                ],
            }
        }

        response = self.controller.build_chat_response(
            "EOS price today", prior_ticker=None
        )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("**EOS.AX** last close: **9.0600** (2026-04-30)", response.text)
        self.assertNotIn("real-time market data sources", response.text.lower())
        self.controller.ollama_client.chat.assert_not_called()

    def test_fresh_web_context_detects_market_wrap_phrase(self) -> None:
        self.assertTrue(
            self.controller._query_signals_fresh_web_context("give me a market wrap")
        )

    def test_direct_ticker_news_reports_empty_corpus_cleanly(self) -> None:
        self.controller.tool_router.get_news_context.return_value = {
            "ok": True,
            "hits": [],
        }

        response = self.controller.build_chat_response(
            "news for bhp", prior_ticker=None
        )

        self.assertEqual(response.mode, ResponseMode.ACTION)
        self.assertIn("couldn't find recent indexed news for BHP", response.text)
        self.assertIn("not evidence there is no news", response.text)
        self.assertIsNotNone(response.action_preview)
        assert response.action_preview is not None
        self.assertEqual(response.action_preview["action_id"], "daily_news_ingest")
        self.assertEqual(response.action_preview["args"]["tickers"], "BHP")

    def test_recent_update_query_summarises_available_context_before_backfill_offer(
        self,
    ) -> None:
        self.controller.tool_router.gather_local_context.return_value = SimpleNamespace(
            payload={
                "ticker": "BHP",
                "docs": [],
                "doc_snippets": [],
                "financials": [],
                "price": {
                    "ok": True,
                    "symbol": "BHP.AX",
                    "current": {
                        "price": 44.0,
                        "previous_close": 43.5,
                        "change_percent": 1.15,
                    },
                    "recent_history": [
                        {"timestamp": "2026-04-14T00:00:00Z", "close": 41.0},
                        {"timestamp": "2026-04-15T00:00:00Z", "close": 41.5},
                        {"timestamp": "2026-04-16T00:00:00Z", "close": 42.0},
                        {"timestamp": "2026-04-17T00:00:00Z", "close": 43.0},
                        {"timestamp": "2026-04-18T00:00:00Z", "close": 44.0},
                    ],
                },
                "price_state": {"trend_regime": "bullish", "last_close": 44.0},
                "qual_context_news": {
                    "hits": [
                        {
                            "title": "BHP copper expansion gathers pace",
                            "published_at": "2026-04-18T01:00:00Z",
                            "text": "Recent coverage focused on BHP expanding its copper footprint.",
                            "source_corpus": "news",
                        }
                    ]
                },
                "qual_context": {"hits": []},
                "sources": {},
            }
        )
        self.controller.ollama_client.chat.return_value = (
            "BHP rose this week and recent coverage centred on copper expansion."
        )
        self.controller.action_registry.preview.return_value = SimpleNamespace(
            command=["python", "scripts/full_history_ticker_sync.py", "--ticker", "BHP"],
            estimated_impact="mutates local data and reports",
            timeout_seconds=14400,
        )

        response = self.controller.build_chat_response(
            "what happened with bhp this week", prior_ticker=None
        )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("BHP rose this week", response.text)
        self.assertIn("I can backfill ASX announcements for BHP next", response.text)
        self.assertIsNotNone(response.action_preview)
        assert response.action_preview is not None
        self.assertEqual(
            response.action_preview["action_id"], "single_ticker_announcement_backfill"
        )
        self.controller.ollama_client.chat.assert_called_once()

    def test_direct_filestats_shortcircuit_returns_company_dump(self) -> None:
        backend = MagicMock()
        backend.get_company_dump.return_value = {
            "ticker": "BHP",
            "summary": {
                "doc_count": 1,
                "financial_period_count": 0,
                "announcement_context_count": 0,
                "risk_note_count": 0,
                "extraction_failure_count": 0,
                "low_confidence_financial_count": 0,
                "company_memory_entry_count": 0,
                "market_memory_item_count": 0,
                "price_points_1y": 1,
                "last_close": 10.0,
                "one_year_return_pct": 0.0,
            },
            "docs": [
                {
                    "document_id": "doc-1",
                    "published_at": "2026-04-01",
                    "doc_class": "results",
                    "title": "BHP Result",
                    "pdf_path": "/tmp/doc.pdf",
                }
            ],
            "financials": [],
            "announcement_context": [],
            "risk_notes": [],
            "price_history_1y": [
                {
                    "timestamp": "2026-04-01T00:00:00Z",
                    "open": 10,
                    "high": 10,
                    "low": 10,
                    "close": 10,
                    "volume": 100,
                }
            ],
            "price": {},
            "price_summary_1y": {
                "points": 1,
                "coverage_start": "2026-04-01",
                "coverage_end": "2026-04-01",
                "last_close": 10,
                "high_close": 10,
                "low_close": 10,
                "one_year_return_pct": 0.0,
            },
            "extraction_failures": [],
            "low_confidence_financials": [],
            "company_memory": {"entries": [], "change_log": []},
            "market_memory": {"items": []},
            "errors": [],
        }
        self.controller.tool_router.backend_api_client = backend

        response = self.controller.build_chat_response(
            "bhp filestats", prior_ticker=None
        )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("Dashboard:", response.text)
        self.assertIn("Company Data Dump: BHP", response.text)
        backend.get_company_dump.assert_called_once_with(ticker="BHP")

    def test_ok_after_summary_offer_returns_summary(self) -> None:
        class _StateStore:
            def get_chat_messages(self, thread_id: str, limit: int = 10):
                return [
                    {
                        "role": "user",
                        "content": "print full bhp stockhead article",
                    },
                    {
                        "role": "assistant",
                        "content": "I’m sorry, but I can’t provide that. However, I can offer to give you a summary of the requested article.",
                    },
                ]

        self.controller._state_store = _StateStore()
        self.controller._thread_id = "session-1"
        self.controller.tool_router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "ASX copper players step into action as supply shortage looms",
                    "published_at": "2026-04-07T20:10:49Z",
                    "url": "https://stockhead.com.au/resources/asx-copper-players-step-into-action-as-supply-shortage-looms",
                    "text": "BHP expanded its global copper footprint with a series of deals. The article frames copper supply as the main strategic driver for current sector activity.",
                }
            ],
        }

        response = self.controller.build_chat_response("ok", prior_ticker="BHP")

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn(
            "Here’s the summary for ASX copper players step into action as supply shortage looms",
            response.text,
        )
        self.assertIn("BHP expanded its global copper footprint", response.text)
        self.controller.tool_router.get_news_context.assert_called_once_with(
            query="BHP stockhead article",
            top_k=5,
            ticker="BHP",
        )

    def test_no_after_summary_offer_declines_cleanly(self) -> None:
        class _StateStore:
            def get_chat_messages(self, thread_id: str, limit: int = 10):
                return [
                    {"role": "user", "content": "print full bhp stockhead article"},
                    {
                        "role": "assistant",
                        "content": "I can offer to give you a summary of the requested article.",
                    },
                ]

        self.controller._state_store = _StateStore()
        self.controller._thread_id = "session-1"

        response = self.controller.build_chat_response("no", prior_ticker="BHP")

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertEqual(response.text, "Okay, I won't do that.")

    def test_shorthand_greeting_does_not_reuse_prior_ticker(self) -> None:
        self.controller._query_orchestrator = MagicMock()

        response = self.controller.build_chat_response("how r u", prior_ticker="BHP")

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("Tenn", response.text)
        self.controller._query_orchestrator.orchestrate_query_with_context.assert_not_called()

    def test_runtime_clock_query_shortcircuits_before_orchestrator(self) -> None:
        self.controller._query_orchestrator = MagicMock()

        with unittest.mock.patch("cockpit.core.chat.datetime") as mock_datetime:
            mock_datetime.now.return_value = real_datetime(
                2026,
                4,
                18,
                11,
                36,
                tzinfo=ZoneInfo("Australia/Sydney"),
            )

            response = self.controller.build_chat_response(
                "what day is it",
                prior_ticker="BHP",
            )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertEqual(response.text, "Today is Saturday, April 18, 2026 (AEST).")
        self.assertEqual(response.evidence[0]["type"], "runtime_clock")
        self.controller._query_orchestrator.orchestrate_query_with_context.assert_not_called()

    def test_ok_rewrites_previous_binary_question_to_explicit_yes(self) -> None:
        class _StateStore:
            def get_chat_messages(self, thread_id: str, limit: int = 10):
                return [
                    {"role": "user", "content": "compare bhp and rio"},
                    {
                        "role": "assistant",
                        "content": "Would you like me to compare BHP and RIO on valuation and risk?",
                    },
                ]

        self.controller._state_store = _StateStore()
        self.controller._thread_id = "session-1"

        rewritten = self.controller._rewrite_confirmation_followup(
            "okay", prior_ticker="BHP"
        )

        assert rewritten is not None
        self.assertIn("Would you like me to compare BHP and RIO", rewritten)
        self.assertIn("My answer is yes, please proceed with that.", rewritten)

    def test_full_article_request_prints_recent_kalkine_article_from_local_corpus(
        self,
    ) -> None:
        class _StateStore:
            def get_chat_messages(self, thread_id: str, limit: int = 10):
                return [
                    {"role": "user", "content": "bhp news"},
                    {
                        "role": "assistant",
                        "content": (
                            "Recent BHP-linked news:\n"
                            "- Market News and Updates on NZX Stocks\n"
                            "  https://kalkinemedia.com/nz/news/market-updates"
                        ),
                    },
                ]

        self.controller._state_store = _StateStore()
        self.controller._thread_id = "session-1"
        self.controller.tool_router.get_local_news_article.return_value = {
            "ok": True,
            "title": "Market News and Updates on NZX Stocks",
            "published_at": "2026-04-08T03:30:00Z",
            "provider": "kalkine",
            "body": "Full locally stored article body.",
            "url": "https://kalkinemedia.com/nz/news/market-updates",
        }

        response = self.controller.build_chat_response(
            "print the full kalkine article", prior_ticker="BHP"
        )

        self.assertEqual(response.mode, ResponseMode.FAST)
        self.assertIn("Market News and Updates on NZX Stocks", response.text)
        self.assertIn("Full locally stored article body.", response.text)
        self.assertIn("https://kalkinemedia.com/nz/news/market-updates", response.text)
        self.controller.tool_router.get_local_news_article.assert_called_once_with(
            "https://kalkinemedia.com/nz/news/market-updates"
        )

    # ------------------------------------------------------------------
    # Stopword expansion — common English words must not be detected as tickers
    # ------------------------------------------------------------------

    def test_stopwords_block_common_english_words(self) -> None:
        """Words like WHY, ARE, FAIL must not be treated as tickers."""
        for word in (
            "why",
            "are",
            "fail",
            "was",
            "has",
            "got",
            "get",
            "try",
            "end",
            "who",
        ):
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
                ticker, explicit = self.controller._resolve_ticker_context(
                    msg, prior_ticker="BHP"
                )
                self.assertIsNone(
                    ticker,
                    f"'{msg}' should not reattach prior ticker BHP",
                )

    def test_follow_up_matches_financial_terms(self) -> None:
        """Financial/entity-referential terms SHOULD reattach prior ticker."""
        for msg in (
            "what about their financials",
            "tell me more",
            "earnings",
            "revenue",
            "outlook",
        ):
            with self.subTest(msg=msg):
                ticker, explicit = self.controller._resolve_ticker_context(
                    msg, prior_ticker="BHP"
                )
                self.assertEqual(
                    ticker,
                    "BHP",
                    f"'{msg}' should reattach prior ticker BHP",
                )
                self.assertFalse(explicit)

    # ------------------------------------------------------------------
    # Compound messages: conversational preamble + real ticker
    # ------------------------------------------------------------------

    def test_compound_message_extracts_real_ticker(self) -> None:
        """'sure, but what about BHP' must still detect BHP."""
        ticker = self.controller._detect_ticker(
            "sure, but what about BHP", prior_ticker=None
        )
        self.assertEqual(ticker, "BHP")

    def test_real_tickers_still_detected(self) -> None:
        """Core regression: single-word tickers must still be detected."""
        for msg, expected in (("BHP", "BHP"), ("CSL", "CSL"), ("bhp", "BHP")):
            with self.subTest(msg=msg):
                ticker = self.controller._detect_ticker(msg, prior_ticker=None)
                self.assertEqual(ticker, expected)

    def test_compact_uppercase_ticker_lists_still_detected(self) -> None:
        self.assertEqual(
            self.controller._detect_ticker("BHP CSL RIO", prior_ticker=None),
            "BHP",
        )

    def test_cued_ticker_in_sentence(self) -> None:
        """Tickers with a cue word (about, price, news) must still be detected."""
        for msg, expected in (
            ("arr price", "ARR"),
            ("csl news", "CSL"),
            ("tell me about bhp", "BHP"),
            ("what does eos do", "EOS"),
            ("what does csl do", "CSL"),
            ("what were BHP operating cash flows", "BHP"),
            ("what were BHP earnings", "BHP"),
            ("why did BHP fall today", "BHP"),
            ("BHP rallied today", "BHP"),
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
            "what are CI checks doing",
        ):
            with self.subTest(msg=msg):
                self.assertIsNone(
                    self.controller._detect_ticker(msg, prior_ticker=None),
                    f"'{msg}' should not produce a ticker",
                )

    def test_structured_mode_instantiation_smoke(self) -> None:
        """Verify ChatController can instantiate in structured mode (ToolExecutor init)."""
        with unittest.mock.patch.dict(os.environ, {"COCKPIT_AGENT_MODE": "structured"}):
            # Should not raise TypeError during ToolExecutor(...) call
            controller = ChatController(
                ollama_client=MagicMock(),
                tool_router=MagicMock(),
                action_registry=MagicMock(),
            )
            self.assertIsNotNone(controller)

    def test_structured_mode_agent_loop_can_build_system_prompt(self) -> None:
        with unittest.mock.patch.dict(os.environ, {"COCKPIT_AGENT_MODE": "structured"}):
            controller = ChatController(
                ollama_client=MagicMock(),
                tool_router=MagicMock(),
                action_registry=MagicMock(),
            )
            self.assertIsNotNone(controller._agent_loop)
            prompt = controller._agent_loop._build_system_prompt()
            self.assertTrue(prompt)

    def test_structured_mode_uses_configured_anthropic_key_when_env_missing(
        self,
    ) -> None:
        with unittest.mock.patch.dict(
            os.environ,
            {"COCKPIT_AGENT_MODE": "structured"},
            clear=False,
        ):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            import cockpit.core.agent.anthropic_client as anthropic_module

            captured: dict[str, str | None] = {"api_key": None, "model": None}

            class FakeAnthropicClient:
                def __init__(self, model=None, max_tokens=4096, api_key=None):
                    captured["api_key"] = api_key
                    captured["model"] = model

            with unittest.mock.patch.object(
                anthropic_module,
                "AnthropicClient",
                FakeAnthropicClient,
            ):
                controller = ChatController(
                    ollama_client=MagicMock(),
                    tool_router=MagicMock(),
                    action_registry=MagicMock(),
                    cockpit_llm={
                        "defaults": {
                            "anthropic_model": "claude-sonnet-4-20250514",
                            "anthropic_api_key": "sk-configured",
                        }
                    },
                )

            self.assertIsNotNone(controller._hybrid_router)
            self.assertEqual(captured["api_key"], "sk-configured")
            self.assertEqual(captured["model"], "claude-sonnet-4-20250514")


if __name__ == "__main__":
    unittest.main()
