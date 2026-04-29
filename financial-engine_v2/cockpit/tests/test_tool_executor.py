"""Regression tests for ToolExecutor — freshness anchoring and safe error shapes.

Covers:
  - search_news market-wide 0-hit path emits freshness_warning (Bug 3 extension)
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


def _make_executor(max_result_chars: int = 2000) -> ToolExecutor:
    """ToolExecutor with a mocked ToolRouter and a no-op ActionRegistry."""
    mock_router = MagicMock()
    mock_registry = MagicMock()
    mock_registry.get.return_value = None
    return ToolExecutor(
        tool_router=mock_router,
        action_registry=mock_registry,
        max_result_chars=max_result_chars,
    )


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class TestGetFinancials:
    def test_empty_backend_financial_rows_are_no_data_not_tool_failure(self) -> None:
        executor = _make_executor()
        backend = MagicMock()
        backend.get_ticker_context.return_value = {"financials": []}
        executor._router.backend_api_client = backend

        result = executor.execute("get_financials", {"ticker": "PLS"})

        assert result["ok"] is True
        assert result["financials"] == []
        backend.get_ticker_context.assert_called_once_with("PLS", financials_limit=6)

    def test_backend_financials_exception_remains_tool_failure(self) -> None:
        executor = _make_executor()
        backend = MagicMock()
        backend.get_ticker_context.side_effect = RuntimeError("backend down")
        executor._router.backend_api_client = backend

        result = executor.execute("get_financials", {"ticker": "PLS"})

        assert result["ok"] is False
        assert result["error"] == "backend API client not configured or request failed"
        backend.get_ticker_context.assert_called_once_with("PLS", financials_limit=6)


# ---------------------------------------------------------------------------
# search_news — freshness_warning on market-wide zero-hit path (Bug 3 extension)
# ---------------------------------------------------------------------------


class TestSearchNewsFreshnessWarning:
    def test_infer_news_ticker_handles_cued_lowercase_query(self) -> None:
        assert ToolExecutor._infer_news_ticker("tell me about csl news") == "CSL"

    def test_infer_news_ticker_rejects_plain_language_false_positive(self) -> None:
        assert ToolExecutor._infer_news_ticker("How are things going?") is None

    def test_exec_search_news_zero_hits_has_freshness_key(self) -> None:
        """Market-wide 0-hit result must carry a freshness_warning key so the
        LLM can anchor temporally and not present corpus absence as factual absence."""
        executor = _make_executor()
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [],
            "_source": "mock",
        }
        result = executor.execute("search_news", {"query": "market news"})
        assert "freshness_warning" in result, (
            "freshness_warning must be present for market-wide 0-hit responses"
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

    def test_exec_search_news_truncation_preserves_hits_and_freshness(self) -> None:
        """When truncated, result should still retain structured hits + freshness metadata."""
        executor = _make_executor(max_result_chars=420)
        executor._router.get_news_context.return_value = {
            "ok": True,
            "hits": [
                {
                    "title": "Very long stale market wrap",
                    "published_at": _days_ago_iso(6),
                    "url": "https://example.com/stale-market-wrap",
                    "provider": "ExampleWire",
                    "text": "A" * 2400,
                },
                {
                    "title": "Second stale article",
                    "published_at": _days_ago_iso(5),
                    "url": "https://example.com/stale-2",
                    "provider": "ExampleWire",
                    "text": "B" * 1800,
                },
            ],
        }

        result = executor.execute("search_news", {"query": "ASX market today"})

        assert result.get("_truncated") is True
        assert isinstance(result.get("hits"), list) and result.get("hits"), (
            "truncated payload should retain compact structured hits"
        )
        assert "freshness_warning" in result, (
            "truncated payload should retain freshness_warning for temporal anchoring"
        )
        assert _today_iso() in str(result.get("freshness_warning"))

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

    def test_truncated_search_news_payload_still_builds_sources(self) -> None:
        evidence = [
            {
                "tool": "search_news",
                "arguments": {"query": "ASX market today"},
                "result": {
                    "tool": "search_news",
                    "ok": True,
                    "_truncated": True,
                    "_original_chars": 6000,
                    "hit_count": 1,
                    "hits": [
                        {
                            "title": "ASX market wrap",
                            "url": "https://example.com/market-wrap",
                            "published_at": "2026-04-20T01:00:00+00:00",
                            "provider": "Example",
                            "snippet": "Market digest.",
                        }
                    ],
                    "freshness_warning": "Most recent article is 3 day(s) old.",
                },
            }
        ]

        sources = _build_ui_sources(evidence)
        assert len(sources) == 1
        assert sources[0]["url"] == "https://example.com/market-wrap"


class TestTradingViewIndicators:
    def test_exec_get_tv_indicators_uses_current_scraper_api(self, monkeypatch) -> None:
        executor = _make_executor()
        called: dict[str, object] = {}

        class FakeIndicators:
            def scrape(self, **kwargs):
                called.update(kwargs)
                return {"status": "success", "data": {"RSI": 58.2}}

        monkeypatch.setattr(
            executor,
            "_get_tradingview_indicators_cls",
            lambda: FakeIndicators,
        )

        result = executor.execute(
            "get_tv_indicators",
            {"ticker": "CBA", "exchange": "ASX", "indicators": ["RSI"]},
        )

        assert result["ok"] is True
        assert result["ticker"] == "CBA"
        assert result["exchange"] == "ASX"
        assert result["indicators"]["RSI"] == 58.2
        assert called == {
            "exchange": "ASX",
            "symbol": "CBA",
            "indicators": ["RSI"],
        }

    def test_exec_get_tv_indicators_marks_provider_failure_as_not_ok(
        self, monkeypatch
    ) -> None:
        executor = _make_executor()

        class FakeIndicators:
            def scrape(self, **kwargs):  # noqa: ARG002
                return {"status": "failed"}

        monkeypatch.setattr(
            executor,
            "_get_tradingview_indicators_cls",
            lambda: FakeIndicators,
        )

        result = executor.execute(
            "get_tv_indicators",
            {"ticker": "CBA", "exchange": "ASX", "indicators": ["RSI"]},
        )

        assert result["ok"] is False
        assert result["error"] == "TradingView indicator request failed"
        assert "error" in result["indicators"]["RSI"]

    def test_exec_get_tv_indicators_maps_macd_alias(self, monkeypatch) -> None:
        executor = _make_executor()
        called: dict[str, object] = {}

        class FakeIndicators:
            def scrape(self, **kwargs):
                called.update(kwargs)
                return {"status": "success", "data": {"MACD.macd": 1.23}}

        monkeypatch.setattr(
            executor,
            "_get_tradingview_indicators_cls",
            lambda: FakeIndicators,
        )

        result = executor.execute(
            "get_tv_indicators",
            {"ticker": "CBA", "exchange": "ASX", "indicators": ["MACD"]},
        )

        assert result["ok"] is True
        assert result["indicators"]["MACD"] == 1.23
        assert called["indicators"] == ["MACD.macd"]


class TestTradingViewScreener:
    def test_exec_tv_screener_uses_screen_api(self, monkeypatch) -> None:
        executor = _make_executor()

        class FakeScreener:
            def screen(self, **kwargs):
                assert kwargs["market"] == "australia"
                assert kwargs["limit"] == 3
                return {
                    "status": "success",
                    "data": [
                        {"symbol": "ASX:CBA", "RSI": 62.1},
                        {"symbol": "ASX:BHP", "RSI": 57.4},
                    ],
                }

        monkeypatch.setattr(
            executor,
            "_get_tradingview_screener_cls",
            lambda: FakeScreener,
        )

        result = executor.execute("tv_screener", {"market": "australia", "limit": 3})

        assert result["ok"] is True
        assert result["count"] == 2
        assert result["results"][0]["symbol"] == "ASX:CBA"

    def test_exec_tv_screener_handles_failed_screen_status(self, monkeypatch) -> None:
        executor = _make_executor()

        class FakeScreener:
            def screen(self, **kwargs):  # noqa: ARG002
                return {"status": "failed", "error": "upstream error"}

        monkeypatch.setattr(
            executor,
            "_get_tradingview_screener_cls",
            lambda: FakeScreener,
        )

        result = executor.execute("tv_screener", {"market": "australia", "limit": 3})

        assert result["ok"] is False
        assert "upstream error" in str(result["error"])
