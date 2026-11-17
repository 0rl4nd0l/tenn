"""Evaluation harness for news pipeline regressions.

Covers the 4 failure classes identified in the P1 audit:
  A. Primary ticker selection (relevance-ordered, not alphabetical)
  B. /chat ticker-aware retrieval (news_chunks filter enabled)
  C. _build_prompt() temporal/uncertainty language
  D. Retrieval failure logging (no silent swallow)

Each class is independent and can be run in isolation.
"""
from __future__ import annotations

import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure scripts/ directory is on path for load_news_to_qdrant imports
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# A. Primary ticker selection
# ---------------------------------------------------------------------------

class TestPrimaryTickerSelection(unittest.TestCase):
    """_build_chunk_payload must use relevance-ordered primary_ticker, not alphabetical."""

    def setUp(self):
        from load_news_to_qdrant import _build_chunk_payload
        self._build = _build_chunk_payload

    def test_primary_ticker_from_article_relevance_field(self):
        """When primary_ticker is pre-resolved, it takes precedence."""
        art = {
            "article_id": "art-001",
            "url": "https://example.com/bhp",
            "title": "BHP lifts guidance",
            "provider": "eodhd",
            "language": "en",
            "published_at": "2026-03-01T00:00:00Z",
            "tickers": ["ABC", "BHP", "RIO"],  # alphabetical: ABC first
            "primary_ticker": "BHP",           # relevance says BHP is primary
        }
        payload = self._build(art, idx=0)
        self.assertEqual(payload["ticker"], "BHP")

    def test_single_ticker_fallback(self):
        """With one linked ticker and no primary_ticker, that ticker is used."""
        art = {
            "article_id": "art-002",
            "url": "https://example.com/rio",
            "title": "RIO update",
            "provider": "eodhd",
            "language": "en",
            "published_at": "2026-03-01T00:00:00Z",
            "tickers": ["RIO"],
            "primary_ticker": "",
        }
        payload = self._build(art, idx=0)
        self.assertEqual(payload["ticker"], "RIO")

    def test_empty_when_no_primary_and_multi_ticker(self):
        """With multiple tickers and no primary_ticker, ticker is empty (ambiguous)."""
        art = {
            "article_id": "art-003",
            "url": "https://example.com/multi",
            "title": "Sector overview",
            "provider": "eodhd",
            "language": "en",
            "published_at": "2026-03-01T00:00:00Z",
            "tickers": ["ABC", "BHP"],
            "primary_ticker": "",
        }
        payload = self._build(art, idx=0)
        self.assertEqual(payload["ticker"], "")

    def test_no_tickers_gives_empty(self):
        """With no linked tickers, ticker is empty string."""
        art = {
            "article_id": "art-004",
            "url": "",
            "title": "Market overview",
            "provider": "rss",
            "language": "en",
            "published_at": "2026-03-01T00:00:00Z",
            "tickers": [],
            "primary_ticker": "",
        }
        payload = self._build(art, idx=0)
        self.assertEqual(payload["ticker"], "")

    def test_primary_ticker_beats_alphabetical_first(self):
        """Regression: ensure we no longer take sorted()[0] when primary is known."""
        art = {
            "article_id": "art-005",
            "url": "https://example.com/wbc",
            "title": "WBC earnings",
            "provider": "eodhd",
            "language": "en",
            "published_at": "2026-03-01T00:00:00Z",
            "tickers": ["ANZ", "CBA", "WBC"],  # alphabetical: ANZ first
            "primary_ticker": "WBC",
        }
        payload = self._build(art, idx=0)
        self.assertNotEqual(payload["ticker"], "ANZ", "Must not be alphabetical-first")
        self.assertEqual(payload["ticker"], "WBC")


# ---------------------------------------------------------------------------
# B. /chat ticker-aware retrieval
# ---------------------------------------------------------------------------

class TestNewsTickerFilter(unittest.TestCase):
    """_build_ticker_filter must apply to news_chunks collection."""

    def setUp(self):
        from app.services.hybrid_retriever import (
            _build_ticker_filter,
            NEWS_CHUNKS_COLLECTION_NAME,
            ASX_DOCS_COLLECTION_NAME,
        )
        self._build_filter = _build_ticker_filter
        self.news_col = NEWS_CHUNKS_COLLECTION_NAME
        self.asx_col = ASX_DOCS_COLLECTION_NAME

    def test_ticker_filter_applied_for_news_chunks(self):
        f = self._build_filter(self.news_col, "BHP")
        self.assertIsNotNone(f, "Should produce a filter for news_chunks")
        self.assertFalse(f.must or [])
        should = f.should or []
        self.assertEqual(
            [condition.key for condition in should],
            ["ticker", "primary_ticker", "tickers"],
        )
        self.assertTrue(
            all(condition.match.value == "BHP" for condition in should)
        )

    def test_ticker_filter_applied_for_asx_docs(self):
        f = self._build_filter(self.asx_col, "BHP")
        self.assertIsNotNone(f)

    def test_ticker_filter_none_for_unknown_collection(self):
        f = self._build_filter("commentary_chunks", "BHP")
        self.assertIsNone(f, "Unrelated collections must not be filtered by ticker")

    def test_ticker_filter_none_when_no_ticker(self):
        f = self._build_filter(self.news_col, None)
        self.assertIsNone(f)

    def test_ticker_filter_none_for_empty_string(self):
        f = self._build_filter(self.news_col, "")
        self.assertIsNone(f)

    def test_ticker_normalized_to_uppercase(self):
        f = self._build_filter(self.news_col, "bhp")
        self.assertIsNotNone(f)
        should = f.should or []
        self.assertTrue(should)
        self.assertTrue(
            all(condition.match.value == "BHP" for condition in should)
        )


class TestChatWithTennTickerPropagation(unittest.TestCase):
    """chat_with_tenn must pass ticker through to the news retriever."""

    def _make_retriever_mock(self):
        mock = MagicMock()
        mock.retrieve.return_value = {"chunks": []}
        return mock

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_ticker_passed_to_news_retriever(self, mock_retriever_cls, mock_rag):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = self._make_retriever_mock()
        news_mock = self._make_retriever_mock()
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]

        from app.services.tenn_chat import chat_with_tenn
        # Will degrade (no LLM) but we only care about the retriever call
        try:
            chat_with_tenn("What is BHP doing?", ticker="BHP")
        except Exception:
            pass

        call_kwargs = news_mock.retrieve.call_args
        self.assertIsNotNone(call_kwargs, "news retriever.retrieve() must be called")
        _, kwargs = call_kwargs
        self.assertEqual(kwargs.get("ticker"), "BHP")

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_no_ticker_propagates_none(self, mock_retriever_cls, mock_rag):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = self._make_retriever_mock()
        news_mock = self._make_retriever_mock()
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]

        from app.services.tenn_chat import chat_with_tenn
        try:
            chat_with_tenn("Broad market outlook")
        except Exception:
            pass

        call_kwargs = news_mock.retrieve.call_args
        self.assertIsNotNone(call_kwargs)
        _, kwargs = call_kwargs
        self.assertIsNone(kwargs.get("ticker"))

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_query_ticker_is_inferred_for_rag_and_news_retriever(
        self,
        mock_retriever_cls,
        mock_rag,
    ):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = self._make_retriever_mock()
        news_mock = self._make_retriever_mock()
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]

        from app.services.tenn_chat import chat_with_tenn

        chat_with_tenn("what changed for A2M recently?")

        self.assertEqual(mock_rag.call_args.kwargs.get("ticker"), "A2M")
        self.assertEqual(news_mock.retrieve.call_args.kwargs.get("ticker"), "A2M")

    @patch("app.services.tenn_chat.generate_json")
    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_ticker_filtered_recall_news_is_kept_in_prompt_and_sources(
        self,
        mock_retriever_cls,
        mock_rag,
        mock_generate_json,
    ):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = MagicMock()
        commentary_mock.retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": f"commentary-{index}",
                    "source_name": "General dairy commentary",
                    "source_type": "commentary",
                    "text": "General dairy market commentary without local recall evidence.",
                    "relevance_score": 0.99,
                    "final_score": 0.99,
                }
                for index in range(12)
            ]
        }
        news_mock = MagicMock()
        news_mock.retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": "news:art_aa13edd261034dba97055d8a:0",
                    "article_id": "art_aa13edd261034dba97055d8a",
                    "ticker": "A2M",
                    "title": "A2 Milk shares plunge after finding toxins in infant formula",
                    "text": (
                        "A2 Milk recall evidence says infant formula was recalled "
                        "after toxins were detected."
                    ),
                    "url": "https://example.com/a2m-recall",
                    "provider": "Capital Brief",
                    "published_at": "2026-05-03T22:52:00Z",
                    "relevance_score": 0.2,
                    "final_score": 0.2,
                }
            ]
        }
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]
        captured: dict[str, str] = {}

        def _fake_generate_json(prompt, metadata=None, timeout=None):
            captured["prompt"] = prompt
            return {
                "answer": "A2M recall evidence is available in local news.",
                "insights": ["A2M recall evidence is available."],
                "supporting_evidence": [
                    {
                        "source_name": (
                            "A2 Milk shares plunge after finding toxins in infant formula"
                        ),
                        "published_at": "2026-05-03T22:52:00Z",
                    }
                ],
                "confidence": 0.7,
            }

        mock_generate_json.side_effect = _fake_generate_json

        from app.services.tenn_chat import chat_with_tenn

        result = chat_with_tenn("tell me about A2M with ticker A2M")

        self.assertIn("art_aa13edd261034dba97055d8a", captured["prompt"])
        self.assertIn("infant formula was recalled", captured["prompt"])
        self.assertTrue(
            any(
                source.get("article_id") == "art_aa13edd261034dba97055d8a"
                and source.get("ticker") == "A2M"
                for source in result["sources"]
            )
        )
        recall_source = next(
            source
            for source in result["sources"]
            if source.get("article_id") == "art_aa13edd261034dba97055d8a"
        )
        self.assertIn("local_news_context", recall_source["evidence_labels"])
        self.assertIn("claim_verified", recall_source["evidence_labels"])
        self.assertTrue(recall_source["claim_verified"])
        self.assertEqual(result["source_coverage_status"], "claim_verified")

    @patch("app.services.tenn_chat.generate_json")
    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_linked_ticker_news_with_different_primary_is_kept_as_context_only(
        self,
        mock_retriever_cls,
        mock_rag,
        mock_generate_json,
    ):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = MagicMock()
        commentary_mock.retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": "commentary-a2m-background",
                    "source_name": "General company background",
                    "source_type": "commentary",
                    "text": "General company background without local news evidence.",
                    "relevance_score": 0.5,
                    "final_score": 0.5,
                }
            ]
        }
        news_mock = MagicMock()
        news_mock.retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": "news:art_62631b4f81acd6fd70efd61c:1",
                    "article_id": "art_62631b4f81acd6fd70efd61c",
                    "ticker": "AEG",
                    "primary_ticker": "AEG",
                    "tickers": ["A2M", "AEG", "BCA", "VMM"],
                    "title": "ASX Small Caps Weekly Form Guide",
                    "text": "The weekly form guide mentioned A2 Milk recall context.",
                    "url": "https://example.com/weekly-form-guide",
                    "provider": "Stockhead",
                    "published_at": "2026-05-08T06:47:16Z",
                    "source_type": "news_article",
                    "relevance_score": 0.6,
                    "final_score": 0.6,
                }
            ]
        }
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]
        captured: dict[str, str] = {}

        def _fake_generate_json(prompt, metadata=None, timeout=None):
            captured["prompt"] = prompt
            return {
                "answer": "A2M local news context was retrieved.",
                "insights": [],
                "supporting_evidence": [{"source_name": "Different source"}],
                "confidence": 0.4,
            }

        mock_generate_json.side_effect = _fake_generate_json

        from app.services.tenn_chat import chat_with_tenn

        result = chat_with_tenn("what changed for A2M recently?", ticker="A2M")

        self.assertIn("art_62631b4f81acd6fd70efd61c", captured["prompt"])
        source = next(
            source
            for source in result["sources"]
            if source.get("article_id") == "art_62631b4f81acd6fd70efd61c"
        )
        self.assertEqual(source["ticker"], "AEG")
        self.assertIn("local_news_context", source["evidence_labels"])
        self.assertIn("context_only", source["evidence_labels"])
        self.assertNotIn("claim_verified", source["evidence_labels"])
        self.assertFalse(source["claim_verified"])
        self.assertIn("missing_required_evidence", result["evidence_labels"])
        self.assertIn("insufficient_for_recent_news", result["evidence_labels"])
        self.assertNotIn("no_hit", result["evidence_labels"])
        self.assertEqual(result["source_coverage_status"], "missing_required_evidence")
        self.assertEqual(
            result["evidence_status"]["missing_required_evidence"],
            ["local_news_context"],
        )

    @patch("app.services.tenn_chat.generate_json")
    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_local_news_is_context_only_without_direct_support_marker(
        self,
        mock_retriever_cls,
        mock_rag,
        mock_generate_json,
    ):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = self._make_retriever_mock()
        news_mock = MagicMock()
        news_mock.retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": "news:a2m:0",
                    "article_id": "art_a2m_context",
                    "ticker": "A2M",
                    "title": "A2M recall background",
                    "text": "A2M recall background was retrieved.",
                    "url": "https://example.com/a2m-context",
                    "provider": "local-news",
                    "published_at": "2026-05-03T00:00:00Z",
                    "source_type": "news_article",
                    "relevance_score": 0.7,
                    "final_score": 0.7,
                }
            ]
        }
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]
        mock_generate_json.return_value = {
            "answer": "A2M context was retrieved.",
            "insights": [],
            "supporting_evidence": [{"source_name": "Different source"}],
            "confidence": 0.4,
        }

        from app.services.tenn_chat import chat_with_tenn

        result = chat_with_tenn("tell me about A2M", ticker="A2M")

        source = result["sources"][0]
        self.assertIn("local_news_context", source["evidence_labels"])
        self.assertIn("context_only", source["evidence_labels"])
        self.assertNotIn("claim_verified", source["evidence_labels"])
        self.assertFalse(source["claim_verified"])
        self.assertEqual(result["source_coverage_status"], "context_only")

    @patch("app.services.tenn_chat.generate_json")
    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_expected_ticker_news_no_hit_surfaces_evidence_gap(
        self,
        mock_retriever_cls,
        mock_rag,
        mock_generate_json,
    ):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = MagicMock()
        commentary_mock.retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": "commentary-1",
                    "source_name": "Company context",
                    "source_type": "commentary",
                    "text": "Company context exists but no local news was returned.",
                    "relevance_score": 0.6,
                    "final_score": 0.6,
                }
            ]
        }
        news_mock = MagicMock()
        news_mock.retrieve.return_value = {"chunks": []}
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]
        mock_generate_json.return_value = {
            "answer": "A2M context is incomplete without local news.",
            "insights": [],
            "supporting_evidence": [{"source_name": "Company context"}],
            "confidence": 0.3,
        }

        from app.services.tenn_chat import chat_with_tenn

        result = chat_with_tenn("what changed for A2M recently?", ticker="A2M")

        self.assertIn("missing_required_evidence", result["evidence_labels"])
        self.assertIn("no_hit", result["evidence_labels"])
        self.assertEqual(result["source_coverage_status"], "missing_required_evidence")
        self.assertEqual(
            result["evidence_status"]["missing_required_evidence"],
            ["local_news_context"],
        )

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_no_resolved_ticker_keeps_broad_semantic_behavior(
        self,
        mock_retriever_cls,
        mock_rag,
    ):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}
        commentary_mock = self._make_retriever_mock()
        news_mock = self._make_retriever_mock()
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]

        from app.services.tenn_chat import chat_with_tenn

        chat_with_tenn("Broad market outlook")

        self.assertIsNone(mock_rag.call_args.kwargs.get("ticker"))
        self.assertIsNone(news_mock.retrieve.call_args.kwargs.get("ticker"))

    @patch("app.services.tenn_chat.generate_json")
    @patch("app.services.tenn_chat.get_session_context")
    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_chat_uses_shared_session_fallback_context(
        self,
        mock_retriever_cls,
        mock_rag,
        mock_get_session_context,
        mock_generate_json,
    ):
        mock_rag.return_value = {
            "hits": [
                {
                    "text": "BHP reiterated cost discipline.",
                    "title": "BHP update",
                    "document_id": "doc-1",
                    "score": 0.87,
                    "doc_class": "asx_announcement",
                    "published_at": "2026-03-31T00:00:00Z",
                }
            ],
            "research_context": {"evidence_chunks": []},
        }
        commentary_mock = self._make_retriever_mock()
        news_mock = self._make_retriever_mock()
        mock_retriever_cls.side_effect = [commentary_mock, news_mock]
        mock_get_session_context.return_value = [
            {
                "query": "What did management say last time?",
                "answer": "Management focused on cost discipline.",
            }
        ]
        captured: dict[str, str] = {}

        def _fake_generate_json(prompt, metadata=None, timeout=None):
            captured["prompt"] = prompt
            return {
                "answer": "BHP remains focused on cost discipline.",
                "insights": [],
                "confidence": 0.6,
            }

        mock_generate_json.side_effect = _fake_generate_json

        from app.services.tenn_chat import chat_with_tenn

        result = chat_with_tenn(
            "What is BHP doing now?",
            ticker="BHP",
            session_id="session-1",
        )

        self.assertIn("Relevant prior session context", captured["prompt"])
        self.assertIn("Management focused on cost discipline.", captured["prompt"])
        self.assertEqual(result["answer"], "BHP remains focused on cost discipline.")


# ---------------------------------------------------------------------------
# C. _build_prompt() temporal/uncertainty behavior
# ---------------------------------------------------------------------------

class TestBuildPromptTemporalGuidance(unittest.TestCase):
    """_build_prompt must include explicit temporal/uncertainty instructions."""

    def setUp(self):
        from app.services.tenn_chat import _build_prompt
        self._build_prompt = _build_prompt

    def _prompt(self, query="What happened?", rows=None):
        return self._build_prompt(query, rows or [])

    def test_prompt_instructs_use_published_at(self):
        p = self._prompt()
        self.assertIn("published_at", p, "Prompt must reference published_at for recency reasoning")

    def test_prompt_addresses_conflicting_sources(self):
        p = self._prompt()
        lower = p.lower()
        self.assertTrue(
            "conflict" in lower or "contradict" in lower,
            "Prompt must address conflicting source evidence",
        )

    def test_prompt_addresses_staleness(self):
        p = self._prompt()
        self.assertIn("stale", p.lower(), "Prompt must mention staleness / old articles")

    def test_prompt_forbids_overclaiming(self):
        p = self._prompt()
        lower = p.lower()
        self.assertTrue(
            "uncertain" in lower or "overclaim" in lower or "sparse" in lower,
            "Prompt must discourage overclaiming when evidence is weak",
        )

    def test_prompt_instructs_confidence_calibration(self):
        p = self._prompt()
        lower = p.lower()
        self.assertIn("confidence", lower)
        # Explicit example of low confidence being valid
        self.assertTrue(
            "0.2" in p or "0.3" in p or "honest" in lower,
            "Prompt must convey that low confidence is a valid answer",
        )

    def test_prompt_returns_only_json(self):
        p = self._prompt()
        self.assertIn("valid JSON", p, "Prompt must instruct model to return valid JSON only")

    def test_prompt_includes_query(self):
        p = self._prompt(query="BHP earnings trend")
        self.assertIn("BHP earnings trend", p)

    def test_prompt_includes_context_json(self):
        rows = [{"text": "BHP revenue rose 10%", "source_name": "Reuters", "published_at": "2026-03-01"}]
        p = self._build_prompt("revenue?", rows)
        self.assertIn("BHP revenue rose 10%", p)

    def test_prompt_includes_current_date_anchor(self):
        from datetime import datetime, timezone

        today_iso = datetime.now(timezone.utc).date().isoformat()
        p = self._prompt()
        self.assertIn(today_iso, p)
        self.assertIn("historical context", p.lower())

    def test_prompt_requires_verifiable_claims(self):
        p = self._prompt()
        lower = p.lower()
        self.assertIn("cannot be verified", lower)
        self.assertIn("backed by the provided context", lower)

    def test_prompt_requires_claims_to_map_to_supporting_evidence(self):
        p = self._prompt()
        lower = p.lower()
        self.assertIn("supporting evidence", lower)
        self.assertIn("do not include any claim", lower)


# ---------------------------------------------------------------------------
# D. Retrieval failure logging
# ---------------------------------------------------------------------------

class TestRetrievalFailureLogging(unittest.TestCase):
    """Retrieval failures must produce a WARNING log, not silently return []."""

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_news_retrieval_failure_is_logged(self, mock_retriever_cls, mock_rag):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}

        commentary_mock = MagicMock()
        commentary_mock.retrieve.return_value = {"chunks": []}

        news_mock = MagicMock()
        news_mock.retrieve.side_effect = RuntimeError("Qdrant unavailable")

        mock_retriever_cls.side_effect = [commentary_mock, news_mock]

        from app.services.tenn_chat import chat_with_tenn

        with self.assertLogs("app.services.tenn_chat", level="WARNING") as cm:
            try:
                chat_with_tenn("any query")
            except Exception:
                pass

        log_text = "\n".join(cm.output)
        self.assertIn("news_retrieval_failed", log_text)

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_commentary_retrieval_failure_is_logged(self, mock_retriever_cls, mock_rag):
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}

        commentary_mock = MagicMock()
        commentary_mock.retrieve.side_effect = ConnectionError("Cannot reach Qdrant")

        news_mock = MagicMock()
        news_mock.retrieve.return_value = {"chunks": []}

        mock_retriever_cls.side_effect = [commentary_mock, news_mock]

        from app.services.tenn_chat import chat_with_tenn

        with self.assertLogs("app.services.tenn_chat", level="WARNING") as cm:
            try:
                chat_with_tenn("any query")
            except Exception:
                pass

        log_text = "\n".join(cm.output)
        self.assertIn("commentary_retrieval_failed", log_text)

    @patch("app.services.tenn_chat.query_rag")
    @patch("app.services.tenn_chat.HybridRetriever")
    def test_user_path_degrades_safely_on_failure(self, mock_retriever_cls, mock_rag):
        """When retrieval fails, the user gets a degraded (not crash) response."""
        mock_rag.return_value = {"hits": [], "research_context": {"evidence_chunks": []}}

        for mock_r in [MagicMock(), MagicMock()]:
            mock_r.retrieve.side_effect = RuntimeError("all down")
        mock_retriever_cls.side_effect = [
            _make_failing_retriever(),
            _make_failing_retriever(),
        ]

        from app.services.tenn_chat import chat_with_tenn

        with self.assertLogs("app.services.tenn_chat", level="WARNING"):
            result = chat_with_tenn("any query")

        # Degraded response — must have system_status key or safe fallback answer
        self.assertIn("answer", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["system_status"], "degraded")
        self.assertIn("degraded_runtime", result["evidence_labels"])
        self.assertEqual(result["source_coverage_status"], "degraded_runtime")


def _make_failing_retriever():
    m = MagicMock()
    m.retrieve.side_effect = RuntimeError("retrieval down")
    return m


if __name__ == "__main__":
    unittest.main()
