"""Tests for ToolExecutor integration with ExtractionController.

Covers the validation gate introduced in _propose_action() for
run_metric_extraction: valid inputs pass through, invalid inputs return an
error dict before the action proposal is built.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cockpit.core.agent.extraction_controller import ExtractionController
from cockpit.core.tool_executor import ToolExecutor
from cockpit.core.types import ActionSpec


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_action_spec(action_id: str = "metric_extraction") -> ActionSpec:
    return ActionSpec(
        id=action_id,
        label="Run metric extraction",
        command_template=["python", "extract.py"],
        arg_schema={"ticker": str},
        is_mutating=True,
        requires_confirmation=True,
        expected_outputs=[],
        timeout_seconds=3600,
    )


def _make_executor(extraction_controller=None) -> ToolExecutor:
    """Build a ToolExecutor with lightweight mocks for router and action registry."""
    mock_router = MagicMock()

    mock_registry = MagicMock()
    mock_registry.get.return_value = _make_action_spec()

    return ToolExecutor(
        tool_router=mock_router,
        action_registry=mock_registry,
        extraction_controller=extraction_controller,
    )


def _make_controller() -> ExtractionController:
    """Return a controller whose pipeline_fn is a no-op (never called in validate())."""
    return ExtractionController(pipeline_fn=lambda doc_id, ticker: "job-test")


# ---------------------------------------------------------------------------
# No controller wired — baseline behaviour unchanged
# ---------------------------------------------------------------------------


class TestNoExtractionController:
    def test_valid_args_produce_proposal_without_controller(self):
        executor = _make_executor(extraction_controller=None)
        result = executor.execute("run_metric_extraction", {"ticker": "BHP"})
        assert result["ok"] is True
        assert result["type"] == "action_proposal"
        assert result["action_id"] == "metric_extraction"

    def test_invalid_ticker_still_produces_proposal_without_controller(self):
        """Without a controller, ToolExecutor cannot validate — proposal is built."""
        executor = _make_executor(extraction_controller=None)
        result = executor.execute("run_metric_extraction", {"ticker": ""})
        # No validation: proposal is built regardless of ticker value.
        assert result["ok"] is True
        assert result["type"] == "action_proposal"

    def test_announcement_ingest_preview_normalizes_today_alias(self):
        executor = _make_executor(extraction_controller=None)
        executor._actions.get.return_value = ActionSpec(
            id="daily_announcement_ingest",
            label="Daily announcement ingest",
            command_template=["python", "daily.py"],
            arg_schema={"date": str},
            is_mutating=True,
            requires_confirmation=True,
            expected_outputs=[],
            timeout_seconds=7200,
        )

        result = executor.execute("run_announcement_ingest", {"date": "today"})

        assert result["ok"] is True
        assert result["arguments"]["date"] == datetime.now(timezone.utc).strftime(
            "%Y-%m-%d"
        )


# ---------------------------------------------------------------------------
# Controller wired — validation gate active
# ---------------------------------------------------------------------------


class TestWithExtractionController:
    def test_valid_ticker_and_doc_id_produce_proposal(self):
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute(
            "run_metric_extraction",
            {"ticker": "BHP", "document_id": "doc-abc123"},
        )
        assert result["ok"] is True
        assert result["type"] == "action_proposal"
        assert result["action_id"] == "metric_extraction"

    def test_ticker_only_uses_ticker_as_doc_id_fallback(self):
        """When document_id is absent, ticker is used as doc_id placeholder."""
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute("run_metric_extraction", {"ticker": "CSL"})
        assert result["ok"] is True
        assert result["type"] == "action_proposal"

    def test_empty_ticker_is_rejected(self):
        # When ticker is empty, doc_id fallback is also empty, so the first
        # format check that fires is document_id (empty string fails the regex).
        # Either way the proposal must be rejected.
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute("run_metric_extraction", {"ticker": ""})
        assert result["ok"] is False
        assert "Validation failed" in result["error"]

    def test_lowercase_ticker_is_normalised_to_uppercase_before_validation(self):
        # _propose_action calls .strip().upper() on the ticker before validating,
        # so a lowercase ticker from the LLM is accepted (not rejected).
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute("run_metric_extraction", {"ticker": "bhp"})
        assert result["ok"] is True
        assert result["type"] == "action_proposal"

    def test_ticker_with_spaces_is_rejected(self):
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute("run_metric_extraction", {"ticker": "BH P"})
        assert result["ok"] is False
        assert "Validation failed" in result["error"]

    def test_free_text_document_id_is_rejected(self):
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute(
            "run_metric_extraction",
            {"ticker": "BHP", "document_id": "Please extract revenue from BHP..."},
        )
        assert result["ok"] is False
        assert "Validation failed" in result["error"]
        assert "document_id" in result["error"]

    def test_valid_ticker_is_uppercased_before_validation(self):
        """Args arrive as lowercase from LLM; executor uppercases before validating."""
        executor = _make_executor(extraction_controller=_make_controller())
        # Lowercase ticker should be uppercased internally and pass.
        # The _propose_action code does .strip().upper() on ticker.
        result = executor.execute(
            "run_metric_extraction",
            {"ticker": "bhp", "document_id": "doc-abc"},
        )
        # After uppercasing "bhp" -> "BHP", validation passes.
        assert result["ok"] is True
        assert result["type"] == "action_proposal"

    def test_validation_error_does_not_reach_action_registry(self):
        """Registry.get() must NOT be called when validation fails."""
        mock_registry = MagicMock()
        mock_registry.get.return_value = _make_action_spec()
        mock_router = MagicMock()

        executor = ToolExecutor(
            tool_router=mock_router,
            action_registry=mock_registry,
            extraction_controller=_make_controller(),
        )
        executor.execute("run_metric_extraction", {"ticker": ""})
        mock_registry.get.assert_not_called()

    def test_other_mutating_tools_bypass_validation(self):
        """The extraction gate must not interfere with other mutating tools."""
        executor = _make_executor(extraction_controller=_make_controller())
        result = executor.execute("run_backfill", {"ticker": "BHP", "years": 3})
        assert result["ok"] is True
        assert result["action_id"] == "single_ticker_announcement_backfill"


class TestSearchNewsTickerInference:
    def test_search_news_infers_ticker_from_query_when_missing(self):
        executor = _make_executor()
        executor._router.get_news_context.return_value = {"ok": True, "hits": []}

        result = executor.execute("search_news", {"query": "bhp news", "limit": 5})

        assert result["ok"] is False
        assert result["data_insufficient"] is True
        assert result["recommended_tool_call"]["tool"] == "run_news_ingest"
        executor._router.get_news_context.assert_called_once_with(
            query="bhp news",
            top_k=5,
            ticker="BHP",
        )

    def test_search_news_does_not_treat_market_news_as_ticker(self):
        executor = _make_executor()
        executor._router.get_news_context.return_value = {"ok": True, "hits": []}

        executor.execute("search_news", {"query": "market news", "limit": 5})

        executor._router.get_news_context.assert_called_once_with(
            query="market news",
            top_k=5,
            ticker=None,
        )

    def test_search_news_suggests_population_when_news_db_unavailable(self):
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": False,
            "hits": [],
            "error": "Server error '502 Bad Gateway' for url 'http://localhost:8000/rag/query'",
            "_source": "sqlite_fallback",
        }

        result = executor.execute("search_news", {"query": "bhp news", "limit": 5})

        assert result["ok"] is False
        assert result["data_insufficient"] is True
        assert "run_news_ingest" in result["suggestion"]
        assert result["recommended_tool_call"]["tool"] == "run_news_ingest"
        assert result["recommended_tool_call"]["arguments"]["since_hours"] == 24
        assert result["recommended_tool_call"]["requires_confirmation"] is True

    def test_search_news_does_not_suggest_population_when_hits_exist(self):
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [{"title": "BHP updates"}],
            "error": None,
            "_source": "qdrant",
        }

        result = executor.execute("search_news", {"query": "bhp news", "limit": 5})

        assert result["ok"] is True
        assert "recommended_tool_call" not in result

    def test_search_news_compacts_hit_payload_for_model_context(self):
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "BHP copper update",
                    "url": "https://example.com/bhp",
                    "provider": "newswire",
                    "ticker": "SFR",
                    "tickers": ["SFR", "BHP"],
                    "published_at": "2026-04-08T03:00:00Z",
                    "score": 0.61,
                    "text": "BHP expanded its copper footprint. " * 40,
                }
            ],
            "error": None,
            "_source": "qdrant",
        }

        result = executor.execute("search_news", {"query": "bhp news", "limit": 5})

        assert result["ok"] is True
        assert result["hit_count"] == 1
        assert result["hits"][0]["title"] == "BHP copper update"
        assert result["hits"][0]["primary_ticker"] == "SFR"
        assert result["hits"][0]["tickers"] == ["SFR", "BHP"]
        assert len(result["hits"][0]["snippet"]) <= 280
        assert "text" not in result["hits"][0]

    def test_search_news_adds_freshness_warning_for_stale_articles(self):
        """Articles older than 2 days should include a freshness_warning."""
        executor = _make_executor()
        # Simulate articles published 7 days ago
        old_date = datetime(2026, 4, 7, 7, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "ASX rallied last week",
                    "url": "https://example.com/asx",
                    "published_at": old_date,
                    "score": 0.7,
                    "text": "Markets moved.",
                }
            ],
            "error": None,
            "_source": "qdrant",
        }

        result = executor.execute("search_news", {"query": "ASX news today", "limit": 5})

        assert result["ok"] is True
        assert "freshness_warning" in result
        assert "historical context" in result["freshness_warning"]
        assert "2026-04-07" in result["freshness_warning"]

    def test_search_news_no_freshness_warning_for_recent_articles(self):
        """Articles published today or yesterday should not get a staleness warning."""
        executor = _make_executor()
        # Simulate articles published today
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "Breaking: ASX up today",
                    "url": "https://example.com/today",
                    "published_at": today_iso,
                    "score": 0.8,
                    "text": "Markets are up today.",
                }
            ],
            "error": None,
            "_source": "qdrant",
        }

        result = executor.execute("search_news", {"query": "ASX news", "limit": 5})

        assert result["ok"] is True
        assert "freshness_warning" not in result


# ---------------------------------------------------------------------------
# ExtractionController.validate() unit tests
# ---------------------------------------------------------------------------


class TestExtractionControllerValidate:
    def test_valid_inputs_do_not_raise(self):
        ctrl = _make_controller()
        ctrl.validate("doc-abc", "BHP")  # must not raise

    def test_invalid_document_id_raises_value_error(self):
        ctrl = _make_controller()
        with pytest.raises(ValueError, match="document_id"):
            ctrl.validate("Please extract...", "BHP")

    def test_invalid_ticker_raises_value_error(self):
        ctrl = _make_controller()
        with pytest.raises(ValueError, match="ticker"):
            ctrl.validate("doc-abc", "")

    def test_validate_does_not_call_pipeline(self):
        called = []
        ctrl = ExtractionController(pipeline_fn=lambda *a: called.append(a) or "job")
        ctrl.validate("doc-abc", "BHP")
        assert called == [], "pipeline_fn must not be invoked by validate()"

    def test_validate_does_not_check_concurrency_limit(self):
        """validate() should NOT raise RuntimeError when at capacity."""
        ctrl = ExtractionController(pipeline_fn=lambda *a: "job", max_concurrent=1)
        ctrl._active_jobs.add("existing-job")  # already at limit
        # validate() should NOT check the concurrency limit
        ctrl.validate("doc-abc", "BHP")  # must not raise

    def test_validate_does_not_deduplicate(self):
        """Repeated validate() calls on the same pair must not raise."""
        ctrl = _make_controller()
        ctrl.validate("doc-abc", "BHP")
        ctrl.validate("doc-abc", "BHP")  # must not raise
