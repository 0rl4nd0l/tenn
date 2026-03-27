"""Tool executor for the agentic chat loop.

Dispatches tool calls to ToolRouter (read-only) or ActionRegistry (mutating).
Read-only tools execute immediately. Mutating tools return an action proposal
for user confirmation — they never execute autonomously.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from cockpit.core.actions import ActionRegistry
from cockpit.core.tool_definitions import MUTATING_TOOL_NAMES
from cockpit.core.tools import ToolRouter

logger = logging.getLogger(__name__)

# Default max chars for tool result payloads (context window management).
DEFAULT_MAX_RESULT_CHARS = 2000


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
    ) -> None:
        self._router = tool_router
        self._actions = action_registry
        self._max_result_chars = max_result_chars
        self._extraction_ctrl = extraction_controller
        self._dossier_service = dossier_service
        self._deep_research_runner = deep_research_runner
        self._alert_reader = alert_reader

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

    def _execute_read_only(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
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
        return {"ok": True, **result}

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
            row for row in history
            if isinstance(row, dict) and start <= str(row.get("timestamp", ""))[:10] <= end
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
        financials = self._router.db_reader.get_financials(ticker, limit=limit)
        narrative = self._router._build_financials_narrative(financials) if financials else ""
        return {
            "ok": bool(financials),
            "ticker": ticker,
            "financials": financials,
            "narrative": narrative,
        }

    def _exec_search_news(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        ticker = str(args.get("ticker", "")).strip().upper() or None
        limit = int(args.get("limit", 5))
        result = self._router.get_news_context(
            query=query,
            top_k=limit,
            ticker=ticker,
        )
        return result

    def _exec_search_announcements(self, args: dict[str, Any]) -> dict[str, Any]:
        ticker = str(args.get("ticker", "")).strip().upper()
        limit = int(args.get("limit", 10))
        if not ticker:
            return {"ok": False, "error": "ticker is required for announcement search"}
        docs = self._router.db_reader.get_docs(ticker, limit=limit)
        context = self._router.db_reader.get_announcement_context(ticker, limit=limit)
        return {
            "ok": bool(docs or context),
            "ticker": ticker,
            "documents": docs,
            "context": context,
        }

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
        extraction_failures = self._router.db_reader.get_extraction_failures(
            limit=8, ticker=ticker,
        )
        low_conf = self._router.db_reader.get_low_confidence_financials(
            threshold=0.4, limit=8, ticker=ticker,
        )
        quality = self._router._build_data_quality_payload(
            extraction_failures=extraction_failures if isinstance(extraction_failures, list) else [],
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

    def _exec_search_web(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"ok": False, "error": "query is required"}
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
            return {"ok": True, "alerts": [], "message": "alert reader not available"}
        return self._alert_reader.get(since_hours=since_hours, ticker=ticker)

    # Dispatch table: tool_name -> handler method
    _READ_ONLY_DISPATCH: dict[str, Any] = {
        "query_ticker_data": _exec_query_ticker_data,
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
        "search_web": _exec_search_web,
        "search_social": _exec_search_social,
        "recall_dossier": _exec_recall_dossier,
        "deep_research": _exec_deep_research,
        "get_watchlist_alerts": _exec_get_watchlist_alerts,
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
    }

    # Maps agentic tool argument names to ActionRegistry argument names.
    _ARG_REMAP: dict[str, dict[str, str]] = {
        "run_backfill": {"ticker": "ticker", "years": "years"},
        "run_metric_extraction": {"ticker": "ticker"},
        "run_news_ingest": {"since_hours": "since_hours"},
        "run_announcement_ingest": {"date": "date"},
        "update_financials": {"ticker": "ticker", "years": "years"},
        "rebuild_financials": {"ticker": "ticker"},
        "audit_financials": {"ticker": "ticker"},
        "generate_chart": {"ticker": "ticker", "range": "timeframe"},
        "save_research_finding": {"ticker": "ticker", "finding": "finding", "source": "source"},
    }

    def _propose_action(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Build an action proposal for a mutating tool (does NOT execute)."""
        # save_research_finding bypasses ActionRegistry — it's a direct dossier write.
        if tool_name == "save_research_finding":
            return self._propose_dossier_save(args)

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
                action_args[action_key] = args[agent_key]

        return {
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

    def _propose_dossier_save(self, args: dict[str, Any]) -> dict[str, Any]:
        """Build a dossier-save proposal (requires confirmation, then executes directly)."""
        ticker = str(args.get("ticker", "")).strip().upper()
        finding = str(args.get("finding", "")).strip()
        source = str(args.get("source", "")).strip()
        if not ticker or not finding:
            return {"tool": "save_research_finding", "ok": False, "error": "ticker and finding are required"}
        if self._dossier_service is None:
            return {"tool": "save_research_finding", "ok": False, "error": "dossier service not available"}

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _truncate(self, result: dict[str, Any]) -> dict[str, Any]:
        """Truncate serialized result to max_result_chars for context management."""
        serialized = json.dumps(result, default=str, ensure_ascii=False)
        if len(serialized) <= self._max_result_chars:
            return result

        # Truncate the JSON string and return a reduced version.
        truncated = serialized[: self._max_result_chars]
        return {
            "tool": result.get("tool", "unknown"),
            "ok": result.get("ok", True),
            "_truncated": True,
            "_original_chars": len(serialized),
            "data": truncated,
        }
