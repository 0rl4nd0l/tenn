"""Tool executor for the agentic chat loop.

Dispatches tool calls to ToolRouter (read-only) or ActionRegistry (mutating).
Read-only tools execute immediately. Mutating tools return an action proposal
for user confirmation — they never execute autonomously.
"""

from __future__ import annotations

import json
import logging
import math
import re
import warnings
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from cockpit.core.actions import ActionRegistry
from cockpit.core.news_freshness import NewsFreshnessTracker
from cockpit.core.tool_definitions import MUTATING_TOOL_NAMES
from cockpit.core.tools import ToolRouter
from shared.ticker_inference import COMMON_TICKER_STOPWORDS, detect_primary_ticker

logger = logging.getLogger(__name__)

# Default max chars for tool result payloads (context window management).
DEFAULT_MAX_RESULT_CHARS = 2000
_NEWS_TICKER_STOPWORDS = {
    *COMMON_TICKER_STOPWORDS,
    "LATEST",
    "RECENT",
    "THIS",
    "TODAY",
    "CLOUD",
    "LOCAL",
    "ADVISOR",
    "OPS",
}
_CURRENT_NEWS_QUERY_RE = re.compile(
    r"\b(today|latest|current|now|breaking|market\s+update|market\s+wrap|"
    r"market\s+movers?|movers?\s+today|news\s+today|today'?s?\s+news)\b",
    re.IGNORECASE,
)


class ToolExecutor:
    """Thin dispatch layer between tool names and ToolRouter/ActionRegistry methods."""

    def __init__(
        self,
        tool_router: ToolRouter,
        action_registry: ActionRegistry,
        *,
        max_result_chars: int = DEFAULT_MAX_RESULT_CHARS,
        extraction_controller=None,
        dossier_service=None,
        deep_research_runner=None,
        alert_reader=None,
        strategy_service=None,
        watchlist_trigger=None,
        ticker_scorer=None,
        screen_runner=None,
        thesis_service=None,
        risk_gate=None,
        reflection_service=None,
    ) -> None:
        self._router = tool_router
        self._actions = action_registry
        self._max_result_chars = max_result_chars
        self._extraction_ctrl = extraction_controller
        self._dossier_service = dossier_service
        self._deep_research_runner = deep_research_runner
        self._alert_reader = alert_reader
        self._strategy_service = strategy_service
        self._watchlist_trigger = watchlist_trigger
        self._ticker_scorer = ticker_scorer
        self._screen_runner = screen_runner
        self._thesis_service = thesis_service
        self._risk_gate = risk_gate
        self._reflection_service = reflection_service
        self._current_intent: str | None = None
        self._freshness_tracker = NewsFreshnessTracker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def _get_tradingview_indicators_cls():
        """Import TradingView Indicators while suppressing upstream pkg_resources noise."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"pkg_resources is deprecated as an API.*",
                category=UserWarning,
                module=r"tradingview_scraper\.symbols\..*",
            )
            from tradingview_scraper.symbols.technicals import Indicators  # type: ignore[import-untyped]
        return Indicators

    @staticmethod
    def _get_tradingview_screener_cls():
        """Import TradingView Screener while suppressing upstream pkg_resources noise."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"pkg_resources is deprecated as an API.*",
                category=UserWarning,
                module=r"tradingview_scraper\.symbols\..*",
            )
            from tradingview_scraper.symbols.screener import Screener  # type: ignore[import-untyped]
        return Screener

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return the result dict.

        - Read-only tools: executes immediately, returns result.
        - Mutating tools: returns an action_proposal with preview, does NOT execute.
        - Unknown tools: returns an error dict.
        - Exceptions are caught and returned as error dicts (never raised).
        """
        try:
            if tool_name in MUTATING_TOOL_NAMES:
                return self._propose_action(tool_name, arguments)
            return self._execute_read_only(tool_name, arguments)
        except Exception as exc:
            logger.exception("tool_executor: %s failed", tool_name)
            return {
                "tool": tool_name,
                "ok": False,
                "error": f"Tool execution failed: {str(exc)[:500]}",
            }

    __call__ = execute

    # ------------------------------------------------------------------
    # Read-only dispatch
    # ------------------------------------------------------------------

    def _execute_read_only(
        self, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch a read-only tool and return truncated result."""
        handler = self._READ_ONLY_DISPATCH.get(tool_name)
        if handler is None:
            return {
                "tool": tool_name,
                "ok": False,
                "error": f"Unknown tool: {tool_name}",
            }
        result = handler(self, args)
        return self._truncate({"tool": tool_name, **result})

    def _exec_query_ticker_data(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        deep = bool(args.get("deep", False))
        limit = int(args.get("limit", 10))
        result = self._router.gather_local_context(
            ticker=ticker,
            query=ticker,
            deep_mode=deep,
        )
        # gather_local_context returns a ToolResult; extract its payload.
        payload = result.payload if hasattr(result, "payload") else {}
        # Trim to requested doc limit.
        docs = payload.get("docs", [])
        if isinstance(docs, list) and len(docs) > limit:
            payload["docs"] = docs[:limit]
        return {"ok": result.ok if hasattr(result, "ok") else True, **payload}

    def _exec_get_company_dump(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        client = self._router.backend_api_client
        if client is None:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "backend API client not configured",
            }
        try:
            payload = client.get_company_dump(ticker=ticker)
        except Exception as exc:
            return {
                "ok": False,
                "ticker": ticker,
                "error": f"company dump request failed: {exc}",
            }
        if not isinstance(payload, dict):
            return {
                "ok": False,
                "ticker": ticker,
                "error": "backend returned a non-object company dump payload",
            }
        return {"ok": True, **payload}

    def _exec_get_price(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        range_ = str(args.get("range", "1y")).strip() or "1y"
        interval = str(args.get("interval", "1d")).strip() or "1d"
        result = self._router.get_price_context_for_window(
            ticker=ticker,
            range_=range_,
            interval=interval,
            max_history_rows=260,
        )
        price = result.get("price") if isinstance(result, dict) else {}
        if isinstance(price, dict):
            price.setdefault("range", range_)
            price.setdefault("interval", interval)
        price_state = result.get("price_state") if isinstance(result, dict) else {}
        error = ""
        if isinstance(price, dict) and price.get("ok") is False:
            error = str(price.get("error") or "").strip()
        if not error and isinstance(price_state, dict) and price_state.get("ok") is False:
            error = str(price_state.get("error") or "").strip()
        if not error and isinstance(result, dict) and result.get("error"):
            error = str(result.get("error") or "").strip()
        ok = not bool(error)
        return {
            "ok": ok,
            **result,
            "ticker": ticker,
            **({"error": error or "price lookup failed"} if not ok else {}),
        }

    def _exec_get_price_on_date(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        date = str(args.get("date", "")).strip()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        if not date:
            return {"ok": False, "error": "date is required"}
        # Fetch a wide window and find the closest date.
        result = self._router.get_price_context_for_window(
            ticker=ticker,
            range_="10y",
            interval="1d",
            max_history_rows=3000,
        )
        price = result.get("price", {})
        history = price.get("recent_history", []) if isinstance(price, dict) else []
        # Find exact or nearest date match.
        for row in history:
            ts = str(row.get("timestamp", ""))[:10]
            if ts == date:
                return {
                    "ok": True,
                    "ticker": ticker,
                    "date": date,
                    "close": row.get("close"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "volume": row.get("volume"),
                }
        return {
            "ok": False,
            "ticker": ticker,
            "date": date,
            "error": f"No price data found for {ticker} on {date}",
        }

    def _exec_get_price_range(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        start = str(args.get("start_date", "")).strip()
        end = str(args.get("end_date", "")).strip()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        if not start or not end:
            return {"ok": False, "error": "start_date and end_date are required"}
        result = self._router.get_price_context_for_window(
            ticker=ticker,
            range_="10y",
            interval="1d",
            max_history_rows=3000,
        )
        price = result.get("price", {})
        history = price.get("recent_history", []) if isinstance(price, dict) else []
        filtered = [
            row
            for row in history
            if isinstance(row, dict)
            and start <= str(row.get("timestamp", ""))[:10] <= end
        ]
        return {
            "ok": bool(filtered),
            "ticker": ticker,
            "start_date": start,
            "end_date": end,
            "data_points": len(filtered),
            "history": filtered,
        }

    def _exec_get_financials(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        limit = int(args.get("limit", 6))
        financials = self._get_financials_via_backend(ticker, limit)
        if financials is None:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "backend API client not configured or request failed",
            }
        if not financials:
            return {
                "ok": True,
                "ticker": ticker,
                "financials": [],
                "narrative": "",
                "data_insufficient": True,
                "suggestion": (
                    "No canonical financial rows were returned. Check data quality "
                    "or source documents before proposing metric extraction or backfill."
                ),
                "recommended_next_tools": [
                    {
                        "tool": "get_data_quality",
                        "arguments": {"ticker": ticker},
                    },
                    {
                        "tool": "query_ticker_data",
                        "arguments": {"ticker": ticker, "limit": 5, "deep": True},
                    },
                ],
            }
        narrative = (
            self._router._build_financials_narrative(financials) if financials else ""
        )
        return {
            "ok": True,
            "ticker": ticker,
            "financials": financials,
            "narrative": narrative,
        }

    def _get_financials_via_backend(
        self, ticker: str, limit: int
    ) -> list[dict[str, Any]] | None:
        """Returns list when backend request succeeds, None when unavailable."""
        client = self._router.backend_api_client
        if not client:
            return None
        try:
            resp = client.get_ticker_context(ticker, financials_limit=limit)
            return resp.get("financials", [])
        except Exception as exc:
            logger.warning("Backend financials failed for %s: %s", ticker, exc)
            return None

    def _exec_search_news(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        explicit_ticker = str(args.get("ticker", "")).strip().upper()
        # Suppress ticker inference for market-wide queries to avoid narrowing
        # a "news today?" search to an irrelevant active ticker.
        _is_market_wide = str(self._current_intent or "").lower() == "market_wide"
        ticker = explicit_ticker or (
            None if _is_market_wide else self._infer_news_ticker(query)
        )
        limit = int(args.get("limit", 5))

        # Check news freshness before querying — surface a staleness warning
        # so the model can caveat its answer or offer an ingest if data is old.
        freshness = self._freshness_tracker.staleness_summary(ticker)
        staleness_preflight: dict[str, Any] | None = (
            freshness if freshness.get("recommend_ingest") or freshness.get("never_ingested") else None
        )

        result = self._router.get_news_context(
            query=query,
            top_k=limit,
            ticker=ticker,
        )

        if not isinstance(result, dict):
            return {"ok": False, "error": "unexpected news context response"}

        hits = result.get("hits")
        hit_count = len(hits) if isinstance(hits, list) else 0
        error_text = str(result.get("error") or "").strip()

        if hit_count == 0:
            lowered_error = error_text.lower()
            likely_unpopulated_news_db = any(
                marker in lowered_error
                for marker in (
                    "/rag/query",
                    "502",
                    "no news source configured",
                    "collection",
                    "unexpected backend response shape",
                )
            )

            if likely_unpopulated_news_db:
                suggestion_args: dict[str, Any] = {"since_hours": 24}
                if ticker:
                    suggestion_args["tickers"] = ticker
                suggestion_json = (
                    '{"tool": "run_news_ingest", "since_hours": 24'
                    + (f', "tickers": "{ticker}"' if ticker else "")
                    + "}"
                )
                enriched = {
                    **result,
                    "ok": False,
                    "data_insufficient": True,
                    "suggestion": (
                        "No indexed news corpus is available yet. Offer to populate it by "
                        "calling the run_news_ingest tool (requires confirmation): "
                        f"{suggestion_json}"
                    ),
                    "recommended_tool_call": {
                        "tool": "run_news_ingest",
                        "arguments": suggestion_args,
                        "requires_confirmation": True,
                    },
                }
                if ticker:
                    enriched["ticker"] = ticker
                return enriched

            # For a named ticker with zero hits, zero results almost certainly
            # means stale or missing data — not confirmed absence of news.
            if ticker and not likely_unpopulated_news_db:
                suggestion_json = (
                    f'{{"tool": "run_news_ingest", "since_hours": 24, '
                    f'"tickers": "{ticker}"}}'
                )
                enriched = {
                    **result,
                    "ok": False,
                    "data_insufficient": True,
                    "hit_count": 0,
                    "ticker": ticker,
                    "suggestion": (
                        f"No news articles found for {ticker}. This likely means the news "
                        f"corpus is stale or {ticker} has not been ingested yet. "
                        f"Offer to run news ingest (requires confirmation): {suggestion_json}"
                    ),
                    "recommended_tool_call": {
                        "tool": "run_news_ingest",
                        "arguments": {"since_hours": 24, "tickers": ticker},
                        "requires_confirmation": True,
                    },
                }
                return enriched

        compact_hits: list[dict[str, Any]] = []
        for hit in hits if isinstance(hits, list) else []:
            if not isinstance(hit, dict):
                continue
            raw_snippet = str(hit.get("text") or hit.get("snippet") or "").strip()
            compact_hits.append(
                {
                    "title": str(hit.get("title") or "").strip(),
                    "published_at": str(hit.get("published_at") or "").strip(),
                    "url": str(hit.get("url") or "").strip(),
                    "provider": str(hit.get("provider") or "").strip(),
                    "ticker": str(hit.get("ticker") or "").strip(),
                    "primary_ticker": str(
                        hit.get("primary_ticker") or hit.get("ticker") or ""
                    ).strip(),
                    "tickers": [
                        str(value).strip()
                        for value in (hit.get("tickers") or [])
                        if str(value).strip()
                    ],
                    "score": float(hit.get("score") or hit.get("final_score") or 0.0),
                    "snippet": re.sub(r"\s+", " ", raw_snippet)[:280],
                }
            )

        # Annotate staleness so the model can caveat responses about "today".
        freshness_warning: str | None = None
        if compact_hits:
            most_recent_str = max(
                (h.get("published_at") or "" for h in compact_hits),
                default="",
            )
            if most_recent_str:
                try:
                    most_recent_dt = datetime.fromisoformat(
                        most_recent_str.replace("Z", "+00:00")
                    )
                    now = datetime.now(timezone.utc)
                    age_days = (now - most_recent_dt).days
                    today_str = now.strftime("%Y-%m-%d")
                    article_date_str = most_recent_dt.strftime("%Y-%m-%d")
                    if age_days >= 2:
                        freshness_warning = (
                            f"Most recent article is {age_days} day(s) old "
                            f"(published {article_date_str}). "
                            f"Today is {today_str}. "
                            "Treat these results as historical context, not current news. "
                            "Do not present them as today's events."
                        )
                except (ValueError, TypeError):
                    pass
        else:
            # 0-hit path: inject today's date so the LLM cannot conflate corpus
            # absence with confirmed factual absence of news.
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            freshness_warning = (
                f"No articles were returned. Today is {today_str}. "
                "The absence of results may reflect a stale or limited corpus — "
                "do not present this as confirmation that no news exists on this topic."
            )

        current_news_query = bool(_CURRENT_NEWS_QUERY_RE.search(query))

        # Successful fresh hits act as a freshness proxy. Historical hits must
        # not make the local freshness tracker think the corpus was just ingested.
        if compact_hits and not freshness_warning:
            self._freshness_tracker.record_ingest(ticker)

        out: dict[str, Any] = {
            "ok": bool(result.get("ok", hit_count > 0)),
            "query": query,
            "ticker": ticker,
            "hit_count": len(compact_hits),
            "hits": compact_hits,
            "_source": result.get("_source"),
            "error": error_text or None,
        }
        if freshness_warning:
            out["freshness_warning"] = freshness_warning
            if compact_hits and current_news_query:
                insufficiency_error = (
                    "only historical news was returned for a current-news query"
                )
                out["ok"] = False
                out["error"] = error_text or insufficiency_error
                out["data_insufficient"] = True
                out["historical_hits"] = list(compact_hits)
                out["suggestion"] = (
                    "Only historical news was returned for a current-news query. "
                    "Do not answer as if this is today's news; offer to run news ingest."
                )
        if staleness_preflight:
            out["staleness_preflight"] = staleness_preflight
        return out

    @staticmethod
    def _infer_news_ticker(query: str) -> str | None:
        return detect_primary_ticker(query, stopwords=_NEWS_TICKER_STOPWORDS)

    def _exec_search_announcements(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        limit = int(args.get("limit", 10))
        if not ticker:
            return {"ok": False, "error": "ticker is required for announcement search"}
        backend_ctx = self._get_announcements_via_backend(ticker, limit)
        if backend_ctx is None:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "backend API client not configured or request failed",
            }
        docs, context = backend_ctx
        return {
            "ok": bool(docs or context),
            "ticker": ticker,
            "documents": docs,
            "context": context,
        }

    def _get_announcements_via_backend(
        self, ticker: str, limit: int
    ) -> tuple[list, list] | None:
        """Returns tuple when backend configured, None when no backend."""
        client = self._router.backend_api_client
        if not client:
            return None
        try:
            resp = client.get_ticker_context(
                ticker, docs_limit=limit, announcements_limit=limit
            )
            return resp.get("docs", []), resp.get("announcement_context", [])
        except Exception as exc:
            logger.warning("Backend announcements failed for %s: %s", ticker, exc)
            return [], []

    def _get_data_quality_via_backend(self, ticker: str) -> tuple[list, list] | None:
        """Returns tuple when backend configured, None when no backend."""
        client = self._router.backend_api_client
        if not client:
            return None
        try:
            resp = client.get_verification_context(
                ticker=ticker,
                failures_limit=8,
                low_confidence_threshold=0.4,
                low_confidence_limit=8,
            )
            return resp.get("extraction_failures", []), resp.get(
                "low_confidence_financials", []
            )
        except Exception as exc:
            logger.warning("Backend data quality failed for %s: %s", ticker, exc)
            return [], []

    def _exec_search_files(self, args: dict[str, Any]) -> dict[str, Any]:
        pattern = str(args.get("pattern", "")).strip()
        if not pattern:
            return {"ok": False, "error": "pattern is required"}
        limit = int(args.get("limit", 20))
        matches = self._router.file_indexer.search_text(pattern=pattern, limit=limit)
        return {"ok": True, "matches": matches}

    def _exec_list_recent_reports(self, args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 10))
        reports = self._router.file_indexer.list_recent_reports(limit=limit)
        return {"ok": True, "reports": reports}

    def _exec_get_data_quality(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        backend_dq = self._get_data_quality_via_backend(ticker)
        if backend_dq is None:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "backend API client not configured or request failed",
            }
        extraction_failures, low_conf = backend_dq
        quality = self._router._build_data_quality_payload(
            extraction_failures=extraction_failures
            if isinstance(extraction_failures, list)
            else [],
            low_conf_rows=low_conf if isinstance(low_conf, list) else [],
            confidence_threshold=0.4,
            deep_mode=False,
        )
        return {"ok": True, "ticker": ticker, **quality}

    def _exec_fetch_url(self, args: dict[str, Any]) -> dict[str, Any]:
        url = str(args.get("url", "")).strip()
        if not url:
            return {"ok": False, "error": "url is required"}
        max_chars = int(args.get("max_chars", 8000))
        result = self._router.fetch_web(
            url=url,
            enabled=self._router.web_default_enabled,
            max_chars=max_chars,
        )
        return {"ok": result.ok, **result.payload}

    # ------------------------------------------------------------------
    # Research tools (search_web, search_social, recall_dossier, deep_research, alerts)
    # ------------------------------------------------------------------

    def _exec_get_strategy(self, args: dict[str, Any]) -> dict[str, Any]:
        if self._strategy_service is None:
            return {"ok": False, "error": "strategy service not available"}
        ticker = str(args.get("ticker", "")).strip().upper() or None
        global_criteria = self._strategy_service.get_global(limit=10)
        ticker_criteria = self._strategy_service.get_ticker(ticker) if ticker else []
        decision = self._strategy_service.get_decision(ticker) if ticker else None
        context_block = self._strategy_service.build_context_block(ticker)
        return {
            "ok": True,
            "global_criteria": global_criteria,
            "ticker_criteria": ticker_criteria,
            "decision": decision,
            "context_block": context_block,
        }

    def _exec_search_web(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        if not bool(getattr(self._router, "web_default_enabled", False)):
            return {
                "ok": False,
                "error": "Web search is disabled. Request access first.",
            }
        count = int(args.get("count", 5))
        if self._router.brave_search_client is not None:
            return self._router.brave_search_client.search(query, count=count)
        # Fallback to WebFetcher if no Brave client wired.
        result = self._router.web_fetcher.search_and_fetch(query, max_results=count)
        return {"ok": result.get("ok", True), "results": result.get("pages", [])}

    def _exec_search_social(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        limit = int(args.get("limit", 10))
        if self._router.hn_search_client is not None:
            return self._router.hn_search_client.search(query, limit=limit)
        return {"ok": False, "stories": [], "error": "HN search client not available"}

    def _exec_recall_dossier(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        query = str(args.get("query", "")).strip() or None
        limit = int(args.get("limit", 5))
        if self._dossier_service is None:
            return {"ok": False, "error": "dossier service not available"}
        return self._dossier_service.recall(ticker, query=query, limit=limit)

    def _exec_deep_research(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        focus = str(args.get("focus", "")).strip() or None
        if self._deep_research_runner is None:
            return {"ok": False, "error": "deep research runner not available"}
        return self._deep_research_runner.run(ticker, focus=focus)

    def _exec_get_watchlist_alerts(self, args: dict[str, Any]) -> dict[str, Any]:
        since_hours = int(args.get("since_hours", 24))
        ticker = str(args.get("ticker", "")).strip().upper() or None
        if self._alert_reader is None:
            return {"ok": False, "error": "alert reader not available"}
        return self._alert_reader.get(since_hours=since_hours, ticker=ticker)

    def _exec_scan_watchlist(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run the full watchlist trigger: analyse → scan → alerts."""
        if self._watchlist_trigger is None:
            return {"ok": False, "error": "watchlist trigger not configured"}
        tickers_raw = str(args.get("tickers", "")).strip()
        ticker_list: list[str] | None = None
        if tickers_raw:
            ticker_list = [
                t.strip().upper() for t in tickers_raw.split(",") if t.strip()
            ]
        summary = self._watchlist_trigger.run(tickers=ticker_list)
        return {
            "ok": True,
            "tickers_scanned": summary.tickers_scanned,
            "total_alerts": summary.total_alerts,
            "total_errors": summary.total_errors,
            "started_at": summary.started_at,
            "finished_at": summary.finished_at,
            "results": [
                {
                    "ticker": r.ticker,
                    "analysis_ok": r.analysis_ok,
                    "modules_run": r.modules_run,
                    "alerts_generated": r.alerts_generated,
                    "errors": list(r.errors),
                }
                for r in summary.results
            ],
        }

    # ------------------------------------------------------------------
    # Analysis pipeline tool
    # ------------------------------------------------------------------

    def _exec_run_analysis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run the Phase 3 analysis pipeline via the backend API."""
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}

        modules_str = str(args.get("modules", "")).strip() or None

        # Call the backend API endpoint POST /api/analysis/{ticker}
        backend = self._router.backend_api_client
        if backend is None:
            return {
                "ok": False,
                "error": "backend API client not configured — cannot run analysis",
            }

        import httpx

        url = f"{backend.base_url}/api/analysis/{ticker}"
        params: dict[str, str] = {}
        if modules_str:
            params["modules"] = modules_str
        headers: dict[str, str] = {}
        if backend.api_key:
            headers["X-API-Key"] = backend.api_key

        try:
            with httpx.Client(timeout=180.0, follow_redirects=True) as client:
                response = client.post(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json() if response.content else {}
        except httpx.HTTPStatusError as exc:
            detail = None
            try:
                err_body = exc.response.json() if exc.response is not None else {}
                detail = err_body.get("detail")
            except Exception:
                pass
            code = exc.response.status_code if exc.response is not None else "unknown"
            return {
                "ok": False,
                "ticker": ticker,
                "error": f"Analysis API returned HTTP {code}: {detail or exc}",
            }
        except httpx.TimeoutException:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "Analysis request timed out (180s)",
            }
        except Exception as exc:
            return {
                "ok": False,
                "ticker": ticker,
                "error": f"Analysis request failed: {exc}",
            }

        # Format the results into a readable summary
        return self._format_analysis_results(ticker, data)

    @staticmethod
    def _format_analysis_results(ticker: str, data: dict[str, Any]) -> dict[str, Any]:
        """Format raw API analysis response into a structured summary for the LLM."""
        results = data.get("results", [])
        if not results:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "Analysis returned no module results",
                "data_insufficient": True,
                "suggestion": (
                    f"No data exists for {ticker}. Use the run_backfill tool "
                    f"to populate financial data first: "
                    f'{{"tool": "run_backfill", "ticker": "{ticker}", "years": 2}}'
                ),
            }

        # Key metric extraction per module
        _METRIC_EXTRACTORS: dict[str, list[tuple[str, str]]] = {
            "balance_sheet": [
                ("net_debt", "Net Debt"),
                ("cash_end", "Cash"),
                ("debt_to_equity", "D/E Ratio"),
            ],
            "roic": [
                ("roic", "ROIC"),
                ("roce", "ROCE"),
                ("roe", "ROE"),
            ],
            "risk": [
                ("risk_score", "Risk Score"),
                ("risk_grade", "Risk Grade"),
            ],
            "valuation": [
                ("pe_ratio", "P/E"),
                ("ev_ebit", "EV/EBIT"),
                ("price_to_book", "P/B"),
                ("fcf_yield", "FCF Yield"),
            ],
            "catalysts": [
                ("catalyst_count", "Catalysts"),
                ("top_catalyst", "Top Catalyst"),
            ],
            "sentiment": [
                ("sentiment_score", "Sentiment"),
                ("sentiment_label", "Label"),
            ],
            "moat": [
                ("moat_classification", "Moat"),
                ("moat_score", "Moat Score"),
            ],
        }

        summary_lines: list[str] = [f"Analysis Summary for {ticker}", "=" * 40]
        module_summaries: list[dict[str, Any]] = []

        for result in results:
            module_name = result.get("module", "unknown")
            completeness = result.get("completeness", "unknown")
            structured = result.get("structured", {})
            warnings = result.get("warnings", [])

            # Extract headline metrics
            extractors = _METRIC_EXTRACTORS.get(module_name, [])
            headline_metrics: dict[str, Any] = {}
            for key, label in extractors:
                val = structured.get(key)
                if val is not None:
                    headline_metrics[label] = val

            # Format the metric string
            if headline_metrics:
                metrics_str = ", ".join(
                    f"{k}: {v}" for k, v in headline_metrics.items()
                )
            else:
                metrics_str = "(no key metrics)"

            status_icon = {
                "complete": "OK",
                "partial": "PARTIAL",
                "failed": "FAILED",
            }.get(completeness, completeness.upper())

            summary_lines.append(
                f"  {module_name:<15} | {status_icon:<8} | {metrics_str}"
            )

            module_entry: dict[str, Any] = {
                "module": module_name,
                "status": completeness,
                "metrics": headline_metrics,
            }

            # Include narrative summary if present
            narrative = structured.get("narrative", {})
            if isinstance(narrative, dict) and narrative.get("summary"):
                module_entry["narrative"] = narrative["summary"]
            elif result.get("narrative") and isinstance(result["narrative"], dict):
                module_entry["narrative"] = result["narrative"].get("summary", "")

            if warnings:
                module_entry["warnings"] = warnings

            module_summaries.append(module_entry)

        summary_text = "\n".join(summary_lines)

        # Detect insufficient data — if most modules FAILED, suggest backfill
        failed_count = sum(1 for m in module_summaries if m.get("status") == "failed")
        total = len(module_summaries)
        suggestion = None
        if failed_count > total // 2:
            suggestion = (
                f"Most analysis modules failed for {ticker} due to "
                f"insufficient data ({failed_count}/{total} failed). "
                f"To populate financial data, use the run_backfill tool: "
                f'{{"tool": "run_backfill", "ticker": "{ticker}", "years": 2}}. '
                f"After backfill completes, re-run the analysis."
            )

        result: dict[str, Any] = {
            "ok": True,
            "ticker": ticker,
            "modules_run": data.get("modules_run", total),
            "summary_text": summary_text,
            "modules": module_summaries,
        }
        if suggestion:
            result["data_insufficient"] = True
            result["suggestion"] = suggestion
        return result

    # ------------------------------------------------------------------
    # Strategy tools (score, screen, valuation, thesis, reflection)
    # ------------------------------------------------------------------

    def _exec_score_ticker(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        if self._ticker_scorer is None:
            return {"ok": False, "error": "ticker scorer not available"}
        return self._ticker_scorer.score(ticker)

    def _exec_screen_tickers(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_tickers = args.get("tickers") or []
        tickers = [str(t).strip().upper() for t in raw_tickers if t]
        filters: dict[str, Any] = {}
        for key in ("min_health_score", "trend_regime", "min_fcf_yield", "max_pe"):
            val = args.get(key)
            if val is not None:
                filters[key] = val
        if self._screen_runner is None:
            return {"ok": False, "error": "screen runner not available"}
        return self._screen_runner.run(tickers or None, filters=filters)

    def _exec_get_valuation(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        try:
            from backend.app.services.analysis.financial_metrics import (  # type: ignore[import-untyped]
                compute_valuation_multiples,
            )
            from cockpit.core.research.signal_engine import _row_to_dict

            rows = []
            if self._router.backend_api_client:
                ctx = self._router.backend_api_client.get_ticker_context(
                    ticker, financials_limit=1
                )
                rows = ctx.get("financials", [])
            if not rows:
                return {"ok": False, "error": f"No financials found for {ticker}"}
            price_ctx = self._router.get_price_context_for_window(
                ticker=ticker,
                range_="1mo",
                interval="1d",
                max_history_rows=5,
            )
            last_close = (price_ctx or {}).get("price_state", {}).get("last_close")
            if not last_close:
                return {"ok": False, "error": f"No price data for {ticker}"}
            multiples = compute_valuation_multiples(
                float(last_close), _row_to_dict(rows[0])
            )
            return {"ok": True, "ticker": ticker, "price": last_close, **multiples}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:300]}

    def _exec_get_thesis(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        backend = self._router.backend_api_client
        if backend is None:
            return {"ok": False, "error": "backend API client not configured"}
        try:
            payload = backend.get_user_thesis_memory(ticker=ticker)
        except Exception as exc:
            return {
                "ok": False,
                "ticker": ticker,
                "error": f"user thesis request failed: {exc}",
            }
        memory_payload = (
            payload.get("user_thesis_memory", {})
            if isinstance(payload, dict)
            else {}
        )
        return {
            "ok": True,
            "ticker": ticker,
            "theses": memory_payload.get("entries", []),
            "proposals": memory_payload.get("proposals", []),
        }

    def _exec_check_decision_outcome(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        if self._reflection_service is None:
            return {"ok": False, "error": "reflection service not available"}
        return self._reflection_service.check_outcome(ticker)

    def _exec_review_open_decisions(self, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        if self._reflection_service is None:
            return {"ok": False, "error": "reflection service not available"}
        return {
            "ok": True,
            "decisions": self._reflection_service.review_open_decisions(),
        }

    def _exec_get_tv_indicators(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        raw_indicators = args.get("indicators") or ["RSI", "MACD", "EMA20", "SMA50"]
        requested_indicators = [
            str(ind).strip()
            for ind in (raw_indicators if isinstance(raw_indicators, list) else [raw_indicators])
            if str(ind).strip()
        ] or ["RSI", "MACD", "EMA20", "SMA50"]
        indicator_aliases = {
            "MACD": "MACD.macd",
            "MACD_SIGNAL": "MACD.signal",
        }
        provider_indicators = [
            indicator_aliases.get(ind.upper(), ind) for ind in requested_indicators
        ]
        exchange = str(args.get("exchange", "ASX")).strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}
        try:
            Indicators = self._get_tradingview_indicators_cls()
            handler = Indicators()
            payload = handler.scrape(
                exchange=exchange,
                symbol=ticker,
                indicators=provider_indicators,
            )
            if not isinstance(payload, dict):
                return {
                    "ok": False,
                    "ticker": ticker,
                    "exchange": exchange,
                    "indicators": {
                        ind: {"error": "unexpected provider response type"}
                        for ind in requested_indicators
                    },
                    "error": f"unexpected TradingView response type: {type(payload).__name__}",
                }

            status = str(payload.get("status") or "").strip().lower()
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            if status != "success":
                return {
                    "ok": False,
                    "ticker": ticker,
                    "exchange": exchange,
                    "indicators": {
                        ind: {"error": "provider returned failed status"}
                        for ind in requested_indicators
                    },
                    "error": "TradingView indicator request failed",
                }

            results: dict[str, Any] = {}
            successful_values = 0
            for original_ind, provider_ind in zip(
                requested_indicators, provider_indicators
            ):
                if provider_ind in data and data[provider_ind] is not None:
                    results[original_ind] = data[provider_ind]
                    successful_values += 1
                else:
                    results[original_ind] = {
                        "error": "indicator not returned by provider"
                    }
            return {
                "ok": successful_values > 0,
                "ticker": ticker,
                "exchange": exchange,
                "indicators": results,
                "error": None if successful_values > 0 else "No indicator values returned",
            }
        except ImportError:
            return {
                "ok": False,
                "error": "tradingview-scraper package not installed. Run: pip install tradingview-scraper",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:300]}

    def _exec_tv_screener(self, args: dict[str, Any]) -> dict[str, Any]:
        market = str(args.get("market", "australia")).strip().lower()
        filters = args.get("filters") or {}
        limit = int(args.get("limit", 20))
        mode = str(args.get("mode") or "").strip().lower()
        sort_by = str(args.get("sort_by") or args.get("sort") or "").strip()
        sort_order = str(args.get("sort_order") or "desc").strip().lower()
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"
        columns = args.get("columns")
        provider_filters = args.get("provider_filters")
        try:
            Screener = self._get_tradingview_screener_cls()
            handler = Screener()

            def _apply_local_filters(rows: list[Any]) -> list[Any]:
                # Apply simple filter: min_rs_rating if provided.
                min_rs = filters.get("min_rs_rating") if isinstance(filters, dict) else None
                if min_rs is None:
                    return rows

                def _row_rs_value(row: dict[str, Any]) -> float:
                    for key in (
                        "Relative Strength Index (14)",
                        "RSI",
                    ):
                        try:
                            value = float(row.get(key, 0) or 0)
                            return value
                        except (TypeError, ValueError):
                            continue
                    return 0.0

                return [
                    r
                    for r in rows
                    if isinstance(r, dict) and _row_rs_value(r) >= float(min_rs)
                ]

            def _annotate(rows: list[Any], side: str) -> list[dict[str, Any]]:
                annotated: list[dict[str, Any]] = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    copied = dict(row)
                    copied.setdefault("mover_side", side)
                    annotated.append(copied)
                return annotated

            def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
                seen: set[str] = set()
                deduped: list[dict[str, Any]] = []
                for row in rows:
                    key = str(
                        row.get("symbol")
                        or row.get("ticker")
                        or row.get("name")
                        or id(row)
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(row)
                return deduped

            # tradingview-scraper API migrated from .scrape(...) -> .screen(...).
            if hasattr(handler, "screen"):
                def _screen(
                    *,
                    limit_override: int | None = None,
                    sort_by_override: str | None = None,
                    sort_order_override: str | None = None,
                ) -> list[Any] | dict[str, str]:
                    screen_kwargs: dict[str, Any] = {
                        "market": market,
                        "limit": limit_override or limit,
                    }
                    if isinstance(columns, list) and columns:
                        screen_kwargs["columns"] = [str(item) for item in columns]
                    if isinstance(provider_filters, list):
                        screen_kwargs["filters"] = provider_filters
                    elif isinstance(filters, list):
                        screen_kwargs["filters"] = filters
                    effective_sort_by = sort_by_override or sort_by
                    if effective_sort_by:
                        screen_kwargs["sort_by"] = effective_sort_by
                    effective_sort_order = sort_order_override or sort_order
                    if effective_sort_order:
                        screen_kwargs["sort_order"] = effective_sort_order

                    payload = handler.screen(**screen_kwargs)
                    if not isinstance(payload, dict):
                        return {
                            "error": (
                                "unexpected screener response type: "
                                f"{type(payload).__name__}"
                            )
                        }
                    status = str(payload.get("status") or "").strip().lower()
                    if status != "success":
                        return {
                            "error": str(
                                payload.get("error")
                                or "TradingView screener request failed"
                            )[:300]
                        }
                    results = payload.get("data")
                    if not isinstance(results, list):
                        return {
                            "error": (
                                "unexpected screener result list type: "
                                f"{type(results).__name__}"
                            )
                        }
                    return results

                if mode == "market_movers":
                    per_side = max(1, limit // 2)
                    gainers_raw = _screen(
                        limit_override=per_side,
                        sort_by_override=sort_by or "change",
                        sort_order_override="desc",
                    )
                    if isinstance(gainers_raw, dict):
                        return {"ok": False, "error": gainers_raw["error"]}
                    decliners_raw = _screen(
                        limit_override=per_side,
                        sort_by_override=sort_by or "change",
                        sort_order_override="asc",
                    )
                    if isinstance(decliners_raw, dict):
                        return {"ok": False, "error": decliners_raw["error"]}
                    gainers = _annotate(_apply_local_filters(gainers_raw), "gainer")
                    decliners = _annotate(
                        _apply_local_filters(decliners_raw), "decliner"
                    )
                    combined = _dedupe([*gainers, *decliners])[:limit]
                    return {
                        "ok": True,
                        "market": market,
                        "mode": "market_movers",
                        "count": len(combined),
                        "results": combined,
                        "gainers": gainers,
                        "decliners": decliners,
                        "sort_by": sort_by or "change",
                    }

                results = _screen()
                if isinstance(results, dict):
                    return {"ok": False, "error": results["error"]}
            elif hasattr(handler, "scrape"):
                results = handler.scrape(market=market)
            else:
                return {
                    "ok": False,
                    "error": "tradingview-scraper Screener has no supported screen/scrape method",
                }
            if not isinstance(results, list):
                return {
                    "ok": False,
                    "error": f"unexpected screener result list type: {type(results).__name__}",
                }
            results = _apply_local_filters(results)
            return {
                "ok": True,
                "market": market,
                "count": len(results[:limit]),
                "results": results[:limit],
            }
        except ImportError:
            return {
                "ok": False,
                "error": "tradingview-scraper package not installed. Run: pip install tradingview-scraper",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:300]}

    def _exec_watch_youtube_channel(self, args: dict[str, Any]) -> dict[str, Any]:
        channel_name = str(args.get("channel_name", "")).strip()
        if not channel_name:
            return {"ok": False, "error": "channel_name is required"}
        client = self._router.backend_api_client
        if client is None:
            return {"ok": False, "error": "backend API client not configured"}
        try:
            credibility_weight = float(args.get("credibility_weight", 0.55))
        except (TypeError, ValueError):
            return {"ok": False, "error": "credibility_weight must be a number"}
        if not math.isfinite(credibility_weight) or not 0.0 <= credibility_weight <= 1.0:
            return {"ok": False, "error": "credibility_weight must be between 0.0 and 1.0"}
        try:
            result = client.add_watched_channel(
                channel_name, credibility_weight=credibility_weight
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, **result}

    def _exec_check_youtube_channel_recent_videos(self, args: dict[str, Any]) -> dict[str, Any]:
        channel_name = str(args.get("channel_name", "")).strip()
        if not channel_name:
            return {"ok": False, "error": "channel_name is required"}
        client = self._router.backend_api_client
        if client is None:
            return {"ok": False, "error": "backend API client not configured"}
        try:
            limit = int(args.get("limit", 8))
        except (TypeError, ValueError):
            return {"ok": False, "error": "limit must be an integer"}
        if limit < 1 or limit > 20:
            return {"ok": False, "error": "limit must be between 1 and 20"}
        try:
            result = client.get_youtube_channel_recent_videos(
                channel_name,
                limit=limit,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        videos = result.get("videos")
        count = len(videos) if isinstance(videos, list) else 0
        return {"ok": True, "count": count, **result}

    def _exec_ingest_youtube_videos(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_urls = args.get("urls")
        if isinstance(raw_urls, str):
            urls = [raw_urls]
        elif isinstance(raw_urls, list):
            urls = [str(item or "").strip() for item in raw_urls]
        else:
            urls = []
        urls = [url for url in urls if url]
        if not urls:
            return {"ok": False, "error": "urls is required"}
        if len(urls) > 5:
            return {"ok": False, "error": "at most 5 YouTube URLs can be ingested at once"}

        client = self._router.backend_api_client
        if client is None:
            return {"ok": False, "error": "backend API client not configured"}

        try:
            takeaway_limit = int(args.get("takeaway_limit", 5))
        except (TypeError, ValueError):
            return {"ok": False, "error": "takeaway_limit must be an integer"}
        if takeaway_limit < 1 or takeaway_limit > 12:
            return {"ok": False, "error": "takeaway_limit must be between 1 and 12"}

        credibility_weight = args.get("credibility_weight")
        if credibility_weight in ("", None):
            parsed_weight = None
        else:
            try:
                parsed_weight = float(credibility_weight)
            except (TypeError, ValueError):
                return {"ok": False, "error": "credibility_weight must be a number"}
            if not math.isfinite(parsed_weight) or not 0.0 <= parsed_weight <= 1.0:
                return {"ok": False, "error": "credibility_weight must be between 0.0 and 1.0"}

        try:
            result = client.ingest_youtube_urls(
                urls,
                credibility_weight=parsed_weight,
                takeaway_limit=takeaway_limit,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        results = result.get("results") if isinstance(result, dict) else []
        selected_videos = args.get("selected_videos")
        if isinstance(results, list) and isinstance(selected_videos, list):
            selected_by_url: dict[str, dict[str, Any]] = {}
            for position, row in enumerate(selected_videos, start=1):
                if not isinstance(row, dict):
                    continue
                url = str(row.get("webpage_url") or row.get("url") or "").strip()
                if not url:
                    continue
                selected_by_url[url] = {"position": position, **row}

            for item in results:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("webpage_url") or item.get("url") or "").strip()
                selected = selected_by_url.get(url)
                if selected is None and len(results) == 1 and len(selected_videos) == 1:
                    first = selected_videos[0]
                    selected = {"position": 1, **first} if isinstance(first, dict) else None
                if not isinstance(selected, dict):
                    continue
                item["selection_metadata"] = {
                    "position": selected.get("position"),
                    "title": selected.get("title"),
                    "published_at": selected.get("published_at"),
                    "duration_seconds": selected.get("duration_seconds"),
                    "scores": selected.get("scores"),
                }
        errors = result.get("errors") if isinstance(result, dict) else []
        success_count = len(results) if isinstance(results, list) else 0
        error_count = len(errors) if isinstance(errors, list) else 0
        return {
            **(result if isinstance(result, dict) else {}),
            "ok": success_count > 0 and error_count == 0,
            "partial_ok": success_count > 0 and error_count > 0,
        }

    # Dispatch table: tool_name -> handler method
    _READ_ONLY_DISPATCH: dict[str, Any] = {
        "query_ticker_data": _exec_query_ticker_data,
        "get_company_dump": _exec_get_company_dump,
        "get_price": _exec_get_price,
        "get_price_on_date": _exec_get_price_on_date,
        "get_price_range": _exec_get_price_range,
        "get_financials": _exec_get_financials,
        "search_news": _exec_search_news,
        "search_announcements": _exec_search_announcements,
        "search_files": _exec_search_files,
        "list_recent_reports": _exec_list_recent_reports,
        "get_data_quality": _exec_get_data_quality,
        "fetch_url": _exec_fetch_url,
        "get_strategy": _exec_get_strategy,
        "search_web": _exec_search_web,
        "search_social": _exec_search_social,
        "recall_dossier": _exec_recall_dossier,
        "deep_research": _exec_deep_research,
        "get_watchlist_alerts": _exec_get_watchlist_alerts,
        "scan_watchlist": _exec_scan_watchlist,
        "run_analysis": _exec_run_analysis,
        "score_ticker": _exec_score_ticker,
        "screen_tickers": _exec_screen_tickers,
        "get_valuation": _exec_get_valuation,
        "get_thesis": _exec_get_thesis,
        "check_decision_outcome": _exec_check_decision_outcome,
        "review_open_decisions": _exec_review_open_decisions,
        "get_tv_indicators": _exec_get_tv_indicators,
        "tv_screener": _exec_tv_screener,
        "watch_youtube_channel": _exec_watch_youtube_channel,
        "check_youtube_channel_recent_videos": _exec_check_youtube_channel_recent_videos,
        "ingest_youtube_videos": _exec_ingest_youtube_videos,
    }

    # ------------------------------------------------------------------
    # Mutating tool proposals
    # ------------------------------------------------------------------

    # Maps agentic tool names to ActionRegistry action IDs.
    _ACTION_ID_MAP: dict[str, str] = {
        "run_backfill": "single_ticker_announcement_backfill",
        "run_metric_extraction": "metric_extraction",
        "run_news_ingest": "daily_news_ingest",
        "run_announcement_ingest": "daily_announcement_ingest",
        "update_financials": "update_ticker_financials",
        "rebuild_financials": "rebuild_ticker_financials",
        "audit_financials": "audit_ticker_financials",
        "generate_chart": "show_candlestick",
        "save_research_finding": "_dossier_direct",  # handled directly, not via ActionRegistry
        "create_thesis": "_strategy_direct",
        "add_thesis_evidence": "_strategy_direct",
        "reflect_on_decision": "_strategy_direct",
        "adjust_signal_weights": "_strategy_direct",
    }

    # Maps agentic tool argument names to ActionRegistry argument names.
    _ARG_REMAP: dict[str, dict[str, str]] = {
        "run_backfill": {"ticker": "ticker", "years": "years"},
        "run_metric_extraction": {"ticker": "ticker"},
        "run_news_ingest": {"since_hours": "since_hours", "tickers": "tickers"},
        "run_announcement_ingest": {"date": "date"},
        "update_financials": {"ticker": "ticker", "years": "years"},
        "rebuild_financials": {"ticker": "ticker"},
        "audit_financials": {"ticker": "ticker"},
        "generate_chart": {"ticker": "ticker", "range": "timeframe"},
        "save_research_finding": {
            "ticker": "ticker",
            "finding": "finding",
            "source": "source",
        },
    }

    def _propose_action(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Build an action proposal for a mutating tool (does NOT execute)."""
        # save_research_finding bypasses ActionRegistry — it's a direct dossier write.
        if tool_name == "save_research_finding":
            return self._propose_dossier_save(args)
        if tool_name in ("create_thesis", "add_thesis_evidence", "reflect_on_decision"):
            return self._propose_strategy_action(tool_name, args)
        if tool_name == "adjust_signal_weights":
            return self._propose_adjust_signal_weights(args)

        # Validate extraction inputs before building the proposal.  This runs
        # at proposal time (pre-confirmation) so the user sees the error early
        # rather than at execution time.
        if tool_name == "run_metric_extraction" and self._extraction_ctrl is not None:
            ticker = str(args.get("ticker", "")).strip().upper()
            doc_id = str(args.get("document_id", ticker)).strip()
            try:
                self._extraction_ctrl.validate(doc_id, ticker)
            except ValueError as exc:
                return {
                    "tool": tool_name,
                    "ok": False,
                    "error": f"Validation failed: {exc}",
                }

        action_id = self._ACTION_ID_MAP.get(tool_name)
        if action_id is None:
            return {
                "tool": tool_name,
                "ok": False,
                "error": f"Unknown mutating tool: {tool_name}",
            }

        try:
            spec = self._actions.get(action_id)
        except KeyError:
            return {
                "tool": tool_name,
                "ok": False,
                "error": f"Action not found in registry: {action_id}",
            }

        # Remap arguments from agentic tool schema to action schema.
        remap = self._ARG_REMAP.get(tool_name, {})
        action_args: dict[str, Any] = {}
        for agent_key, action_key in remap.items():
            if agent_key in args:
                value = args[agent_key]
                if action_key == "date" and str(value).strip().lower() == "today":
                    value = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                action_args[action_key] = value

        proposal: dict[str, Any] = {
            "tool": tool_name,
            "ok": True,
            "type": "action_proposal",
            "action_id": action_id,
            "action_label": spec.label,
            "arguments": action_args,
            "requires_confirmation": spec.requires_confirmation,
            "is_mutating": spec.is_mutating,
            "timeout_seconds": spec.timeout_seconds,
        }
        if tool_name == "generate_chart":
            proposal["synthesis_instruction"] = (
                "After the chart renders, provide a 2-3 sentence commentary: "
                "describe the current trend (up/down/sideways), the recent price range, "
                "and whether the move is consistent with broader market conditions. "
                "Use the price data embedded in the chart result."
            )
        return proposal

    def _propose_dossier_save(self, args: dict[str, Any]) -> dict[str, Any]:
        """Build a dossier-save proposal (requires confirmation, then executes directly)."""
        ticker = str(args.get("ticker", "")).strip().upper()
        finding = str(args.get("finding", "")).strip()
        source = str(args.get("source", "")).strip()
        if not ticker or not finding:
            return {
                "tool": "save_research_finding",
                "ok": False,
                "error": "ticker and finding are required",
            }
        if self._dossier_service is None:
            return {
                "tool": "save_research_finding",
                "ok": False,
                "error": "dossier service not available",
            }

        return {
            "tool": "save_research_finding",
            "ok": True,
            "type": "action_proposal",
            "action_id": "save_research_finding",
            "action_label": f"Save research finding for {ticker}",
            "arguments": {
                "ticker": ticker,
                "finding": finding,
                "source": source,
                "confidence": float(args.get("confidence", 0.5)),
                "category": str(args.get("category", "general")).strip(),
            },
            "requires_confirmation": True,
            "is_mutating": True,
            "timeout_seconds": 5,
        }

    def _propose_strategy_action(
        self, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Build an action proposal for strategy mutating tools."""
        ticker = str(args.get("ticker", "")).strip().upper()

        if tool_name == "create_thesis":
            thesis_text = str(args.get("thesis", "")).strip()
            signal = str(args.get("signal", "HOLD")).strip().upper()
            if not ticker or not thesis_text:
                return {
                    "tool": tool_name,
                    "ok": False,
                    "error": "ticker and thesis are required",
                }
            if self._router.backend_api_client is None:
                return {
                    "tool": tool_name,
                    "ok": False,
                    "error": "backend API client not configured",
                }
            return {
                "tool": tool_name,
                "ok": True,
                "type": "action_proposal",
                "action_id": "create_thesis",
                "action_label": f"Create {signal} thesis for {ticker}",
                "arguments": {
                    "ticker": ticker,
                    "thesis": thesis_text,
                    "signal": signal,
                    "run_risk_gate": bool(args.get("run_risk_gate", True)),
                },
                "requires_confirmation": True,
                "is_mutating": True,
                "timeout_seconds": 60,
            }

        if tool_name == "add_thesis_evidence":
            finding = str(args.get("finding", "")).strip()
            if not ticker or not finding:
                return {
                    "tool": tool_name,
                    "ok": False,
                    "error": "ticker and finding are required",
                }
            if self._router.backend_api_client is None:
                return {
                    "tool": tool_name,
                    "ok": False,
                    "error": "backend API client not configured",
                }
            is_supporting = bool(args.get("is_supporting", True))
            label = "supporting" if is_supporting else "disconfirming"
            return {
                "tool": tool_name,
                "ok": True,
                "type": "action_proposal",
                "action_id": "add_thesis_evidence",
                "action_label": f"Add {label} evidence for {ticker} thesis",
                "arguments": {
                    "ticker": ticker,
                    "finding": finding,
                    "is_supporting": is_supporting,
                },
                "requires_confirmation": True,
                "is_mutating": True,
                "timeout_seconds": 5,
            }

        if tool_name == "reflect_on_decision":
            if not ticker:
                return {"tool": tool_name, "ok": False, "error": "ticker is required"}
            if self._reflection_service is None:
                return {
                    "tool": tool_name,
                    "ok": False,
                    "error": "reflection service not available",
                }
            return {
                "tool": tool_name,
                "ok": True,
                "type": "action_proposal",
                "action_id": "reflect_on_decision",
                "action_label": f"Reflect on {ticker} decision and record lesson",
                "arguments": {"ticker": ticker},
                "requires_confirmation": True,
                "is_mutating": True,
                "timeout_seconds": 30,
            }

        return {
            "tool": tool_name,
            "ok": False,
            "error": f"Unknown strategy tool: {tool_name}",
        }

    def _propose_adjust_signal_weights(self, args: dict[str, Any]) -> dict[str, Any]:
        """Build a proposal to adjust composite signal weights."""
        if self._strategy_service is None:
            return {
                "tool": "adjust_signal_weights",
                "ok": False,
                "error": "strategy service not available",
            }

        weights = {
            "health": args.get("health"),
            "momentum": args.get("momentum"),
            "valuation": args.get("valuation"),
            "technical": args.get("technical"),
        }
        # Early validation so the user sees errors before confirmation.
        try:
            from cockpit.core.strategy import StrategyService

            # Validate without storing — just check the values.
            required_keys = set(StrategyService._DEFAULT_SIGNAL_WEIGHTS)
            for k in required_keys:
                v = weights.get(k)
                if v is None or not isinstance(v, (int, float)) or v < 0:
                    return {
                        "tool": "adjust_signal_weights",
                        "ok": False,
                        "error": f"Weight '{k}' must be a non-negative number, got {v!r}",
                    }
            total = sum(float(weights[k]) for k in required_keys)
            if abs(total - 1.0) > 0.05:
                return {
                    "tool": "adjust_signal_weights",
                    "ok": False,
                    "error": f"Weights must sum to ~1.0 (tolerance 0.05). Got {total:.4f}",
                }
        except Exception as exc:
            return {"tool": "adjust_signal_weights", "ok": False, "error": str(exc)}

        label_parts = [f"{k}={v:.2f}" for k, v in weights.items() if v is not None]
        return {
            "tool": "adjust_signal_weights",
            "ok": True,
            "type": "action_proposal",
            "action_id": "adjust_signal_weights",
            "action_label": f"Set signal weights: {', '.join(label_parts)}",
            "arguments": weights,
            "requires_confirmation": True,
            "is_mutating": True,
            "timeout_seconds": 5,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compact_text(value: Any, *, max_chars: int = 220) -> str | None:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if not text:
            return None
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _compact_result_list(
        self,
        rows: Any,
        *,
        max_rows: int = 3,
        max_result_chars: int = 180,
    ) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        compact_rows: list[dict[str, Any]] = []
        for row in rows[:max_rows]:
            if not isinstance(row, dict):
                continue
            compact: dict[str, Any] = {}
            for key in (
                "title",
                "video_title",
                "source_name",
                "url",
                "source_url",
                "published_at",
                "provider",
                "ticker",
                "primary_ticker",
                "source_id",
                "video_id",
                "webpage_url",
                "document_id",
                "source_document_id",
                "symbol",
                "name",
                "doc_type",
                "period_type",
                "period_end",
                "path",
                "pdf_path",
                "channel_name",
                "duration_seconds",
                "view_count",
                "change",
                "change_abs",
                "close",
                "volume",
                "score",
                "final_score",
            ):
                if key in row and row.get(key) not in (None, ""):
                    value = row.get(key)
                    if isinstance(value, str):
                        compact[key] = self._compact_text(value, max_chars=220) or value
                    else:
                        compact[key] = value
            scores = row.get("scores")
            if isinstance(scores, dict):
                compact_scores = {
                    key: value
                    for key, value in scores.items()
                    if key in {"overall", "recency", "importance", "relevance", "duration"}
                    and value not in (None, "")
                }
                if compact_scores:
                    compact["scores"] = compact_scores

            snippet = self._compact_text(
                row.get("snippet")
                or row.get("text")
                or row.get("excerpt")
                or row.get("statement"),
                max_chars=max_result_chars,
            )
            if snippet:
                compact["snippet"] = snippet

            takeaways = row.get("takeaways")
            if isinstance(takeaways, list):
                compact_takeaways: list[dict[str, Any]] = []
                for takeaway in takeaways[:3]:
                    if not isinstance(takeaway, dict):
                        continue
                    text = self._compact_text(takeaway.get("text"), max_chars=220)
                    if text:
                        compact_takeaways.append({"text": text})
                if compact_takeaways:
                    compact["takeaways"] = compact_takeaways

            if not compact:
                compact = {
                    "summary": self._compact_text(
                        json.dumps(row, default=str, ensure_ascii=False),
                        max_chars=max_result_chars,
                    )
                }
            compact_rows.append(compact)
        return compact_rows

    def _structured_truncated_payload(
        self, result: dict[str, Any], original_chars: int
    ) -> dict[str, Any]:
        """Build a compact, structured payload that preserves source/freshness fields."""
        compact: dict[str, Any] = {
            "tool": result.get("tool", "unknown"),
            "ok": bool(result.get("ok", True)),
            "_truncated": True,
            "_original_chars": original_chars,
        }

        for key in (
            "error",
            "query",
            "ticker",
            "market",
            "name",
            "channel_id",
            "hit_count",
            "count",
            "limit",
            "freshness_warning",
            "transcript_quality_warning",
            "_source",
        ):
            if key in result and result.get(key) not in (None, ""):
                value = result.get(key)
                if isinstance(value, str):
                    compact[key] = self._compact_text(value, max_chars=320) or value
                else:
                    compact[key] = value

        if isinstance(result.get("staleness_preflight"), dict):
            compact["staleness_preflight"] = result.get("staleness_preflight")

        for list_key in (
            "hits",
            "results",
            "documents",
            "context",
            "alerts",
            "videos",
            "docs",
            "doc_snippets",
            "announcement_context",
            "financials",
        ):
            compact_rows = self._compact_result_list(result.get(list_key))
            if compact_rows:
                compact[list_key] = compact_rows

        snapshot = result.get("latest_financial_snapshot")
        if isinstance(snapshot, dict):
            compact_snapshot = self._compact_result_list([snapshot], max_rows=1)
            if compact_snapshot:
                compact["latest_financial_snapshot"] = compact_snapshot[0]

        # Keep scalar indicators if available (useful for get_tv_indicators).
        indicators = result.get("indicators")
        if isinstance(indicators, dict):
            compact_indicators: dict[str, Any] = {}
            for key, value in list(indicators.items())[:8]:
                if isinstance(value, dict):
                    err = self._compact_text(value.get("error"), max_chars=120)
                    compact_indicators[key] = {"error": err or "error"}
                else:
                    compact_indicators[key] = value
            compact["indicators"] = compact_indicators

        # Preserve price attribution metadata for source panel (strips history).
        price = result.get("price")
        if isinstance(price, dict):
            price_current = price.get("current")
            compact["price"] = {
                "provider": price.get("provider"),
                "symbol": price.get("symbol"),
                "range": price.get("range"),
                "interval": price.get("interval"),
                "current": price_current if isinstance(price_current, dict) else None,
            }

        return compact

    def _truncate(self, result: dict[str, Any]) -> dict[str, Any]:
        """Truncate serialized result to max_result_chars for context management."""
        serialized = json.dumps(result, default=str, ensure_ascii=False)
        if len(serialized) <= self._max_result_chars:
            return result

        compact = self._structured_truncated_payload(result, len(serialized))
        compact_serialized = json.dumps(compact, default=str, ensure_ascii=False)
        if len(compact_serialized) <= self._max_result_chars:
            return compact

        # Ultra-minimal structured fallback: keep just enough to preserve
        # source extraction (title/url/published_at) and freshness anchoring.
        minimal: dict[str, Any] = {
            "tool": result.get("tool", "unknown"),
            "ok": result.get("ok", True),
            "_truncated": True,
            "_original_chars": len(serialized),
        }
        if result.get("hit_count") is not None:
            minimal["hit_count"] = result.get("hit_count")
        if result.get("count") is not None:
            minimal["count"] = result.get("count")
        for key in ("name", "channel_id", "limit"):
            if result.get(key) not in (None, ""):
                minimal[key] = result.get(key)
        freshness_warning = self._compact_text(
            result.get("freshness_warning"), max_chars=120
        )
        if freshness_warning:
            minimal["freshness_warning"] = freshness_warning
        transcript_quality_warning = self._compact_text(
            result.get("transcript_quality_warning"), max_chars=220
        )
        if transcript_quality_warning:
            minimal["transcript_quality_warning"] = transcript_quality_warning

        for list_key in (
            "hits",
            "results",
            "videos",
            "docs",
            "doc_snippets",
            "announcement_context",
            "financials",
        ):
            rows = result.get(list_key)
            if not isinstance(rows, list) or not rows:
                continue
            first = rows[0] if isinstance(rows[0], dict) else {}
            if not isinstance(first, dict):
                continue
            minimal_row = {}
            for key in (
                "title",
                "video_title",
                "source_name",
                "url",
                "published_at",
                "video_id",
                "webpage_url",
                "source_id",
                "source_url",
                "symbol",
                "name",
                "document_id",
                "source_document_id",
                "period_type",
                "period_end",
                "duration_seconds",
            ):
                if first.get(key) not in (None, ""):
                    minimal_row[key] = first.get(key)
            scores = first.get("scores")
            if isinstance(scores, dict):
                minimal_scores = {
                    key: value
                    for key, value in scores.items()
                    if key in {"overall", "recency", "importance", "relevance", "duration"}
                    and value not in (None, "")
                }
                if minimal_scores:
                    minimal_row["scores"] = minimal_scores
            takeaways = first.get("takeaways")
            if isinstance(takeaways, list):
                compact_takeaways: list[dict[str, Any]] = []
                for takeaway in takeaways[:3]:
                    if not isinstance(takeaway, dict):
                        continue
                    text = self._compact_text(takeaway.get("text"), max_chars=180)
                    if text:
                        compact_takeaways.append({"text": text})
                if compact_takeaways:
                    minimal_row["takeaways"] = compact_takeaways
            if minimal_row:
                minimal[list_key] = [minimal_row]

        minimal_serialized = json.dumps(minimal, default=str, ensure_ascii=False)
        if len(minimal_serialized) <= self._max_result_chars:
            return minimal

        # Final fallback keeps shape minimal while still preserving key context.
        if "hits" in compact:
            compact["hits"] = compact["hits"][:1]
        if "results" in compact:
            compact["results"] = compact["results"][:1]
        if "documents" in compact:
            compact["documents"] = compact["documents"][:1]
        if "context" in compact:
            compact["context"] = compact["context"][:1]
        if "videos" in compact:
            compact["videos"] = compact["videos"][:1]
        if "docs" in compact:
            compact["docs"] = compact["docs"][:1]
        if "doc_snippets" in compact:
            compact["doc_snippets"] = compact["doc_snippets"][:1]
        if "announcement_context" in compact:
            compact["announcement_context"] = compact["announcement_context"][:1]
        if "financials" in compact:
            compact["financials"] = compact["financials"][:1]

        compact_serialized = json.dumps(compact, default=str, ensure_ascii=False)
        if len(compact_serialized) <= self._max_result_chars:
            return compact

        fallback: dict[str, Any] = {
            "tool": result.get("tool", "unknown"),
            "ok": result.get("ok", True),
            "_truncated": True,
            "_original_chars": len(serialized),
            "error": self._compact_text(result.get("error"), max_chars=180),
            "freshness_warning": self._compact_text(
                result.get("freshness_warning"), max_chars=220
            ),
            "data": self._compact_text(serialized, max_chars=self._max_result_chars),
        }
        for key in ("name", "channel_id", "count", "hit_count", "limit"):
            if result.get(key) not in (None, ""):
                fallback[key] = result.get(key)
        video_rows = self._compact_result_list(
            result.get("videos"),
            max_rows=1,
            max_result_chars=180,
        )
        if video_rows:
            fallback["videos"] = video_rows
        result_rows = self._compact_result_list(
            result.get("results"),
            max_rows=1,
            max_result_chars=140,
        )
        if result_rows:
            fallback["results"] = result_rows
        return fallback
