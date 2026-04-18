"""Regression tests for ToolExecutor — freshness anchoring and safe error shapes.

Covers:
  - search_news 0-hit path now emits freshness_warning (Bug 3 extension)
  - freshness_warning content for stale vs. fresh articles
  - HTTP/exception path returns a structured dict, never raises
  - Bug 2 regression: agent-loop evidence {tool:"search_news", result:{hits:[...]}}
    is correctly consumed by _build_ui_sources
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.routes.cockpit_api import _build_ui_sources
from cockpit.core.tool_executor import ToolExecutor


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_executor() -> ToolExecutor:
    """ToolExecutor with a mocked ToolRouter and a no-op ActionRegistry."""
    mock_router = MagicMock()
    mock_registry = MagicMock()
    mock_registry.get.return_value = None
    return ToolExecutor(tool_router=mock_router, action_registry=mock_registry)


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# search_news — freshness_warning on zero-hit path (Bug 3 extension)
# ---------------------------------------------------------------------------


class TestSearchNewsFreshnessWarning:
    def test_infer_news_ticker_handles_cued_lowercase_query(self) -> None:
        assert ToolExecutor._infer_news_ticker("tell me about csl news") == "CSL"

    def test_infer_news_ticker_rejects_plain_language_false_positive(self) -> None:
        assert ToolExecutor._infer_news_ticker("How are things going?") is None

    def test_exec_search_news_zero_hits_has_freshness_key(self) -> None:
        """0-hit result must carry a freshness_warning key so the LLM can
        anchor temporally and not present corpus absence as factual absence."""
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [],
            "_source": "mock",
        }
        result = executor.execute("search_news", {"query": "BHP earnings"})
        assert "freshness_warning" in result, (
            "freshness_warning must be present even when 0 hits are returned"
        )
        # The warning must reference today's date to provide a temporal anchor.
        assert _today_iso() in result["freshness_warning"]

    def test_exec_search_news_freshness_warning_stale_news(self) -> None:
        """Articles older than 2 days → freshness_warning is a non-empty string."""
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "Old article",
                    "published_at": _days_ago_iso(5),
                    "url": "http://example.com/old",
                }
            ],
        }
        result = executor.execute("search_news", {"query": "BHP"})
        warning = result.get("freshness_warning")
        assert warning and len(warning) > 0, (
            "freshness_warning must be non-empty when most recent article is ≥2 days old"
        )
        assert "5 day" in warning or "days old" in warning.lower()

    def test_exec_search_news_freshness_warning_fresh_news(self) -> None:
        """Article published today → freshness_warning absent or empty."""
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "Breaking news",
                    "published_at": _days_ago_iso(0),
                    "url": "http://example.com/fresh",
                }
            ],
        }
        result = executor.execute("search_news", {"query": "BHP"})
        # Fresh articles should produce no warning (age_days < 2).
        assert not result.get("freshness_warning"), (
            "freshness_warning should be absent or empty for same-day articles"
        )

    # -----------------------------------------------------------------------
    # HTTP / backend exception path
    # -----------------------------------------------------------------------

    def test_tool_http_error_returns_safe_dict(self) -> None:
        """Backend exception (e.g. HTTP 500) → execute() returns a structured
        dict with ok=False and an error key, never raises."""
        executor = _make_executor()
        executor._router.get_news_context.side_effect = RuntimeError(
            "upstream 500 Internal Server Error"
        )
        result = executor.execute("search_news", {"query": "BHP"})
        assert isinstance(result, dict), "execute() must return a dict on exception"
        assert result.get("ok") is False
        assert "error" in result, "error key must be present in the fallback dict"


# ---------------------------------------------------------------------------
# Bug 2 regression: agent-loop evidence format consumed by _build_ui_sources
# ---------------------------------------------------------------------------


class TestBuildUiSourcesSearchNewsRegression:
    def test_known_bug_regression_empty_sources(self) -> None:
        """Evidence in agent-loop format {tool:'search_news', result:{hits:[...]}}
        must produce a non-empty sources list from _build_ui_sources.

        This is a regression test for Bug 2: the orchestrator-format branch
        only handled ev.get('type') evidence, silently discarding agent-loop
        evidence that has 'tool' but no 'type' key.
        """
        evidence = [
            {
                "tool": "search_news",
                "arguments": {"query": "BHP earnings"},
                "result": {
                    "hits": [
                        {
                            "title": "BHP reports record profit",
                            "url": "http://example.com/bhp-profit",
                            "published_at": "2024-10-15",
                            "provider": "AFR",
                        }
                    ]
                },
            }
        ]
        sources = _build_ui_sources(evidence)
        assert len(sources) > 0, (
            "Agent-loop search_news evidence must produce at least one source item"
        )
        assert any(s.get("url") == "http://example.com/bhp-profit" for s in sources)
