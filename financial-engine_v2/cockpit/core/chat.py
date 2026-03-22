from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        pass
from pathlib import Path
from typing import Any


class ResponseMode(StrEnum):
    FAST = "fast"
    DEEP_ANALYSIS = "deep_analysis"
    ACTION = "action"
    VERIFICATION = "verification"
    WEB = "web"


@dataclass
class ChatResponse:
    text: str
    evidence: list[dict[str, Any]]
    action_preview: dict[str, Any] | None = None
    mode: str = ResponseMode.FAST
    prompt: str | None = None


@dataclass
class _ContextResult:
    """Lightweight result wrapper for gather_local_context calls."""
    payload: dict[str, Any]
    ok: bool = True


ACTION_KEYWORDS = {
    "full_history": ["backfill", "full history", "history sync"],
    "update_ticker_financials": ["refresh financials", "update financial data", "financial refresh"],
    "rebuild_ticker_financials": ["rebuild financials", "rebuild ticker financials", "reprocess docs financials"],
    "audit_ticker_financials": ["audit financials", "financial qa", "check financial quality"],
    "daily_news_ingest": [
        "daily news ingest",
        "ingest daily news",
        "run news ingestion",
        "news ingestion",
        "news ingewstion",
        "today news ingest",
    ],
    "historical_news_ingest": ["historical news ingest", "news backfill", "backfill news", "news history ingest"],
    "load_news_to_qdrant": [
        "load news to qdrant",
        "sync news chunks to qdrant",
        "news to qdrant",
        "push news to qdrant",
        "upload news chunks",
    ],
    "daily_announcement_ingest": [
        "daily announcement ingest",
        "daily announcements",
        "daily asx announcements",
        "asx announcements today",
    ],
    "single_ticker_announcement_backfill": [
        "single ticker backfill",
        "ticker announcement backfill",
        "backfill ticker announcements",
        "refresh announcements",
        "update announcements",
    ],
    "universe_announcement_enrichment_backfill": [
        "asx enrichment chunked",
        "chunked enrichment",
        "5 year asx enrichment",
        "universe announcement backfill",
        "announcement enrichment backfill",
    ],
    "metric_extraction": [
        "metric extraction",
        "extract metrics",
        "extract financial metrics",
        "financial metric extraction",
    ],
    "sort_asx_docs": ["sort asx docs", "classify announcements", "sort announcements", "organise asx docs"],
    "resume_pending": ["resume pending", "retry pending", "pending downloads"],
    "recover_headed": ["recover headed", "headed recovery"],
}


class ChatController:
    def __init__(
        self,
        ollama_client,
        tool_router,
        action_registry,
        llm_timeout_seconds: float = 300.0,
        state_store=None,
        thread_id: str = "global-main",
    ) -> None:
        self.ollama_client = ollama_client
        self.tool_router = tool_router
        self.action_registry = action_registry
        self.llm_timeout_seconds = float(llm_timeout_seconds)
        self.last_ticker: str | None = None
        self._state_store = state_store
        self._thread_id = thread_id
        # Prevents concurrent context-gather calls from stacking up.
        self._context_gather_lock = threading.Lock()

    TICKER_STOPWORDS = {
        "A",
        "AN",
        "AND",
        "AS",
        "ASK",
        "ANALYSE",
        "ANALYZE",
        "ABOUT",
        "CANDLE",
        "CHART",
        "CHECK",
        "FOR",
        "FROM",
        "GIVE",
        "HAVE",
        "HI",
        "HOW",
        "I",
        "IN",
        "IS",
        "IT",
        "LATEST",
        "MANY",
        "ME",
        "MOST",
        "NEWS",
        "OF",
        "ON",
        "ONE",
        "SHOW",
        "PLEASE",
        "PLOT",
        "PRICE",
        "RECENT",
        "SUMMARISE",
        "SUMMARIZE",
        "TELL",
        "THAT",
        "THE",
        "THIS",
        "TO",
        "TODAY",
        "UPDATE",
        "WE",
        "WHAT",
        "WHATS",
        "WITH",
        "YOU",
        "YOUR",
        "DO",
        "DOES",
        "DID",
        "ANY",
        "ALL",
        "COUNT",
        "NUMBER",
        "ANNOUNCEMENT",
        "ANNOUNCEMENTS",
        # Market/exchange scope words — not company tickers.
        "ASX",
        # Common English words that happen to be 2-5 chars.
        "RUN",
        "SOME",
    }

    # ------------------------------------------------------------------ #
    # Post-processing classifiers                                          #
    # ------------------------------------------------------------------ #

    _PROMPT_ECHO_MARKERS = (
        "cockpit context",
        "as of my last update",
        "my knowledge cutoff",
        "i don't have access to real-time",
        "i cannot access real-time",
        "as an ai",
    )

    @staticmethod
    def _looks_like_prompt_echo(text: str) -> bool:
        """Return True if the LLM appears to have echoed the system prompt back."""
        lower = text.lower()
        if lower.startswith("final context prompt"):
            return True
        count = sum(1 for m in ChatController._PROMPT_ECHO_MARKERS if m in lower)
        return count >= 2

    @staticmethod
    def _has_verification_disclaimer(text: str) -> bool:
        """Return True if the text contains a 'cannot be verified' disclaimer."""
        return "cannot be verified based on available data" in text.lower()

    @staticmethod
    def _extract_ticker_observations(ticker: str, assistant_text: str) -> list[dict]:
        """
        Extract financial observations from LLM response text using rule-based matching.
        Returns list of {'type': str, 'content': str}.
        """
        import re as _re

        # Financial signal vocabulary by type
        SIGNAL_WORDS = {
            "revenue": ["revenue", "sales", "turnover", "top-line", "top line"],
            "profitability": ["profit", "ebit", "ebitda", "npat", "margin", "earnings", "loss"],
            "cashflow": ["cash flow", "cashflow", "fcf", "operating cash", "free cash"],
            "debt": ["debt", "leverage", "net debt", "borrowings", "net cash", "gearing"],
            "guidance": ["guidance", "outlook", "forecast", "expects", "target", "projected"],
            "risk": ["risk", "headwind", "concern", "impairment", "write-down", "write-off"],
            "catalyst": ["catalyst", "upgrade", "acquisition", "merger", "buyback", "dividend"],
            "valuation": ["cheap", "expensive", "overvalued", "undervalued", "discount", "premium", "p/e", "ev/ebit"],
        }

        observations = []
        ticker_upper = ticker.upper()
        ticker_lower = ticker.lower()

        # Split into sentences
        sentences = _re.split(r"(?<=[.!?])\s+", assistant_text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 300:
                continue

            # Sentence must mention the ticker
            if ticker_upper not in sentence and ticker_lower not in sentence:
                continue

            # Check for signal words
            for obs_type, words in SIGNAL_WORDS.items():
                if any(w in sentence.lower() for w in words):
                    observations.append({
                        "type": obs_type,
                        "content": sentence,
                    })
                    break  # one type per sentence

        # Cap at 3 observations per turn to avoid noise
        return observations[:3]

    @staticmethod
    def _sanitize_prompt_local_payload(payload: Any, *, deep_mode: bool = False) -> dict[str, Any]:
        """
        Trim doc lists and snippet excerpts to safe sizes before building the prompt.

        - docs: 10 items (operational) or 20 items (deep)
        - doc_snippets: excerpt clipped to 1200 chars each
        - Non-dict payload: returns {}
        """
        if not isinstance(payload, dict):
            return {}
        out = dict(payload)
        max_docs = 20 if deep_mode else 10
        if isinstance(out.get("docs"), list):
            out["docs"] = out["docs"][:max_docs]
        if isinstance(out.get("doc_snippets"), list):
            snippets = []
            for s in out["doc_snippets"]:
                if isinstance(s, dict) and len(str(s.get("excerpt", ""))) > 1200:
                    s = dict(s)
                    s["excerpt"] = str(s["excerpt"])[:1200]
                snippets.append(s)
            out["doc_snippets"] = snippets
        return out

    # ------------------------------------------------------------------ #
    # Context gather with timeout                                          #
    # ------------------------------------------------------------------ #

    def _gather_local_context_with_timeout(
        self, ticker: str | None, query: str, deep_mode: bool
    ) -> _ContextResult:
        """
        Run tool_router.gather_local_context in a background thread with a timeout.

        - If already running: returns immediately with note="context_gather_busy".
        - If timeout exceeded: returns note="context_gather_timeout" (worker keeps running,
          lock stays held until the worker exits — so the next call sees "busy").
        - If exception: returns note="context_gather_error" with db_error field.
        - On success: returns the router result directly.
        """
        timeout = float(os.environ.get("COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS", "30"))

        # Non-blocking acquire: if already locked the worker is still running.
        if not self._context_gather_lock.acquire(blocking=False):
            return _ContextResult(ok=False, payload={"note": "context_gather_busy", "ticker": ticker})

        result_holder: list[Any] = [None]
        error_holder: list[BaseException | None] = [None]

        def _run() -> None:
            try:
                result_holder[0] = self.tool_router.gather_local_context(
                    ticker=ticker, query=query, deep_mode=deep_mode
                )
            except Exception as exc:
                error_holder[0] = exc
            finally:
                # Release unconditionally so the next call can proceed.
                self._context_gather_lock.release()

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=timeout)

        if worker.is_alive():
            # Worker timed out — lock still held by worker thread until it finishes.
            return _ContextResult(ok=False, payload={"note": "context_gather_timeout", "ticker": ticker})

        if error_holder[0] is not None:
            return _ContextResult(
                ok=False,
                payload={"note": "context_gather_error", "ticker": ticker, "db_error": str(error_holder[0])},
            )

        return result_holder[0]

    @staticmethod
    def _extract_alpha_tokens(message: str) -> list[tuple[str, str]]:
        # Match ASX-style tickers: letter-started, 2-5 alphanumeric chars (e.g. MP1, A200).
        return [(m.group(0), m.group(0).upper()) for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9]{1,4})\b", message)]

    def _detect_ticker(self, message: str, prior_ticker: str | None = None) -> str | None:
        # Prefer explicit ticker-like mentions first, e.g. "$BHP" or "ASX:BHP".
        explicit = re.search(r"(?:\bASX:|\$)([A-Za-z]{2,5})\b", message)
        if explicit:
            token = explicit.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        tokens = self._extract_alpha_tokens(message)
        if not tokens:
            return prior_ticker

        # Prefer explicit uppercase ticker-like tokens first.
        for original, upper in tokens:
            if original.isupper() and upper not in self.TICKER_STOPWORDS:
                return upper

        for _, upper in tokens:
            if upper not in self.TICKER_STOPWORDS:
                return upper
        return prior_ticker

    _GLOBAL_NEWS_RE = re.compile(r"\basx\s+news\b|\bmarket\s+news\b|\ball\s+news\b", re.IGNORECASE)
    _GLOBAL_ANNOUNCEMENT_RE = re.compile(
        r"\basx\s+announc|\ball\s+announc|\bmarket.?wide\s+announc", re.IGNORECASE
    )

    def _is_global_news_request(self, message: str) -> bool:
        """Return True when the message targets market-wide news rather than a specific company."""
        return bool(self._GLOBAL_NEWS_RE.search(message))

    def _is_global_announcement_request(self, message: str) -> bool:
        """Return True when the message targets market-wide ASX announcements."""
        return bool(self._GLOBAL_ANNOUNCEMENT_RE.search(message))

    # Chart intent keywords — checked before general action detection.
    # NOTE: "price history" is a price-query pattern, not a chart request.
    _CHART_KEYWORDS = re.compile(
        r"\b(?:candlestick|candle|chart|plot)\b"
        r"|show\s+\S+\s*chart",
        re.IGNORECASE,
    )

    def detect_chart_intent(self, message: str) -> bool:
        """Return True if *message* looks like a chart request."""
        return bool(self._CHART_KEYWORDS.search(message))

    def detect_action_intent(self, message: str) -> str | None:
        text = message.lower()
        for action_id, words in ACTION_KEYWORDS.items():
            if any(w in text for w in words):
                return action_id
        return None

    # --- Price history patterns ---
    _ON_DATE_RE = re.compile(
        r"(?:price|was|close|closing)\b.*?\b(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    )
    _RANGE_RE = re.compile(
        r"between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    )
    _FULL_HISTORY_RE = re.compile(
        r"\bprice\s+history\b",
        re.IGNORECASE,
    )

    def _try_price_history_shortcircuit(self, message: str, ticker: str | None) -> ChatResponse | None:
        """Detect price-on-date, range, or full-history queries and short-circuit."""
        if ticker is None:
            return None

        # Fetch price context (10y window gives us maximum coverage for queries).
        try:
            bundle = self.tool_router.get_price_context_for_window(
                ticker, range_="10y", interval="1d", max_history_rows=3000,
            )
        except Exception:
            return None

        price = bundle.get("price") if isinstance(bundle, dict) else {}
        price = price if isinstance(price, dict) else {}
        symbol = str(price.get("symbol") or f"{ticker}.AX")
        history = price.get("recent_history") if isinstance(price, dict) else None
        if history is None:
            history = price.get("history") if isinstance(price, dict) else []
        if not isinstance(history, list):
            history = []

        # Build sorted (date_str, close) pairs.
        dated_closes: list[tuple[str, float]] = []
        for row in history:
            if not isinstance(row, dict):
                continue
            ts = str(row.get("timestamp") or "")
            close = row.get("close")
            if not ts or close is None:
                continue
            date_str = ts[:10]
            try:
                dated_closes.append((date_str, float(close)))
            except (ValueError, TypeError):
                continue
        dated_closes.sort(key=lambda item: item[0])

        if not dated_closes:
            return None

        # --- Range query: "between DATE and DATE" ---
        range_match = self._RANGE_RE.search(message)
        if range_match:
            start_date = range_match.group(1)
            end_date = range_match.group(2)
            in_range = [(d, c) for d, c in dated_closes if start_date <= d <= end_date]
            if not in_range:
                text = f"No price history for {symbol} between {start_date} and {end_date}."
                return ChatResponse(
                    text=text,
                    evidence=[{"type": "local_context", "details": {"price_history_query": {"kind": "range", "ticker": ticker, "start": start_date, "end": end_date}}}],
                    mode=ResponseMode.FAST,
                )
            first_close = in_range[0][1]
            last_close = in_range[-1][1]
            period_return = ((last_close / first_close) - 1.0) * 100.0 if first_close != 0 else 0.0
            high = max(c for _, c in in_range)
            low = min(c for _, c in in_range)
            text = (
                f"Historical range for {symbol}: {start_date} to {end_date}\n"
                f"Period return (close-to-close): {period_return:+.2f}%\n"
                f"High: {high:.4f}  Low: {low:.4f}  Points: {len(in_range)}"
            )
            return ChatResponse(
                text=text,
                evidence=[{"type": "local_context", "details": {"price_history_query": {"kind": "range", "ticker": ticker, "start": start_date, "end": end_date}}}],
                mode=ResponseMode.FAST,
            )

        # --- On-date query: "price on DATE" ---
        on_date_match = self._ON_DATE_RE.search(message)
        if on_date_match:
            query_date = on_date_match.group(1)
            # Find exact or nearest preceding date.
            exact = [(d, c) for d, c in dated_closes if d == query_date]
            if exact:
                date_str, close_val = exact[0]
                text = (
                    f"Historical close for {symbol} on {query_date}: {close_val:.4f}\n"
                    f"Matched candle date: {date_str} (exact)"
                )
                return ChatResponse(
                    text=text,
                    evidence=[{"type": "local_context", "details": {"price_history_query": {"kind": "on_date", "ticker": ticker, "date": query_date}}}],
                    mode=ResponseMode.FAST,
                )
            # Try nearest preceding date.
            preceding = [(d, c) for d, c in dated_closes if d <= query_date]
            if preceding:
                date_str, close_val = preceding[-1]
                text = (
                    f"Historical close for {symbol} on {query_date}: {close_val:.4f}\n"
                    f"Matched candle date: {date_str} (nearest)"
                )
                return ChatResponse(
                    text=text,
                    evidence=[{"type": "local_context", "details": {"price_history_query": {"kind": "on_date", "ticker": ticker, "date": query_date}}}],
                    mode=ResponseMode.FAST,
                )
            text = f"No price history exists on or before {query_date} for {symbol}."
            return ChatResponse(
                text=text,
                evidence=[{"type": "local_context", "details": {"price_history_query": {"kind": "on_date", "ticker": ticker, "date": query_date}}}],
                mode=ResponseMode.FAST,
            )

        # --- Full history query: "price history TICKER" ---
        if self._FULL_HISTORY_RE.search(message):
            first_date = dated_closes[0][0]
            last_date = dated_closes[-1][0]
            n_points = len(dated_closes)
            first_close = dated_closes[0][1]
            last_close = dated_closes[-1][1]
            total_return = ((last_close / first_close) - 1.0) * 100.0 if first_close != 0 else 0.0
            high = max(c for _, c in dated_closes)
            low = min(c for _, c in dated_closes)
            text = (
                f"Full historical summary for {symbol}\n"
                f"Coverage: {first_date} to {last_date} ({n_points} points)\n"
                f"Total return: {total_return:+.2f}%\n"
                f"High: {high:.4f}  Low: {low:.4f}"
            )
            return ChatResponse(
                text=text,
                evidence=[{"type": "local_context", "details": {"price_history_query": {"kind": "full_summary", "ticker": ticker}}}],
                mode=ResponseMode.FAST,
            )

        return None

    @staticmethod
    def classify_request(message: str, *, enable_web: bool = False) -> ResponseMode:
        text = str(message or "").strip().lower()
        if not text:
            return ResponseMode.FAST

        if any(url_prefix in text for url_prefix in ("http://", "https://")) and enable_web:
            return ResponseMode.WEB

        verification_markers = (
            "verify",
            "verification",
            "did it work",
            "check status",
            "status",
            "what failed",
            "why did",
            "error",
            "failed",
            "failure",
        )
        if any(marker in text for marker in verification_markers):
            return ResponseMode.VERIFICATION

        deep_markers = (
            "deep analysis",
            "analyse",
            "analyze",
            "compare",
            "walk through",
            "walk me through",
            "explain",
            "what changed",
            "impact",
            "thesis",
            "full report",
        )
        if any(marker in text for marker in deep_markers):
            return ResponseMode.DEEP_ANALYSIS

        return ResponseMode.FAST

    def _compute_announcement_sync_status(self, ticker: str, docs: list[dict], message: str) -> dict:  # noqa: ARG002
        """Return {status, needs_update_offer} based on recency of docs."""
        if not docs:
            return {"status": "missing", "needs_update_offer": True}
        freshness_threshold_hours = 72
        now = datetime.now(timezone.utc)
        latest_doc = docs[0]
        published_at_str = str(latest_doc.get("published_at") or "")
        try:
            published_at = datetime.fromisoformat(published_at_str)
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            age_hours = (now - published_at).total_seconds() / 3600
        except (ValueError, TypeError):
            return {"status": "stale", "needs_update_offer": True}
        if age_hours < freshness_threshold_hours:
            return {"status": "fresh", "needs_update_offer": False}
        return {"status": "stale", "needs_update_offer": True}

    def _build_ticker_update_offer(self, ticker: str, sync: dict) -> dict:
        """Build an offer dict for updating ticker announcements."""
        if not sync.get("needs_update_offer"):
            return {
                "note": f"Announcement sync check for {ticker}: up to date",
                "action_preview": None,
            }
        args: dict[str, Any] = {"ticker": ticker, "years": 1, "process_documents": True}
        action_preview: dict[str, Any] = {"action_id": "update_ticker_financials", "args": args}
        if self.action_registry:
            try:
                preview = self.action_registry.preview("update_ticker_financials", args)
                action_preview["command"] = preview.command
                action_preview["impact"] = preview.estimated_impact
                action_preview["timeout_seconds"] = preview.timeout_seconds
            except Exception:
                pass
        status = sync.get("status", "unknown")
        note = (
            f"Announcement sync check for {ticker}: {status}. "
            f"Use /confirm to update or /cancel to skip."
        )
        return {"note": note, "action_preview": action_preview}

    def _build_system_instruction(self, mode: str, ticker: str | None, local_payload: dict) -> str:  # noqa: ARG002
        """Build the ASX-domain-specific system prompt for the LLM."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        instruction = (
            "You are Tenn, an advanced ASX equity research analyst and financial intelligence agent.\n"
            "\n"
            "Your primary function: deliver rigorous, evidence-grounded analysis of ASX-listed companies."
            " You have access to real-time price data, multi-period financial statements, regulatory"
            " announcements, and qualitative context from company filings.\n"
            "\n"
            "Domain context:\n"
            "- Exchange: Australian Securities Exchange (ASX), Sydney AEST/AEDT timezone\n"
            "- Reporting: Semi-annual (interim + full-year), calendar year-end typical for resources,"
            " June 30 FY for most corporates\n"
            "- Key metrics: Revenue, EBIT, NPAT, operating CF, FCF (OCF - capex), net debt, shares on issue\n"
            "- Valuation lenses: P/E, EV/EBIT, FCF yield, net debt/EBIT leverage. Use these when multiples"
            " data is available in the payload.\n"
            "- Price signals: trend regime (bull/bear/neutral via SMA), momentum (1d/20d/63d returns),"
            " annualised vol, drawdown from 63d high\n"
            "- Announcement types: results > guidance > capital raising > dividend > administrative."
            " Weight by type when synthesising.\n"
            "\n"
            "Analyst standards:\n"
            "- Lead with the most material facts. Flag data limitations explicitly.\n"
            "- Distinguish between confirmed financial data and qualitative inference.\n"
            "- When financials_narrative is provided, use it as your starting point for trend commentary.\n"
            "- When valuation_multiples are provided, anchor your valuation assessment to them.\n"
            "- When post-announcement price reactions are provided, include market interpretation.\n"
            "- Never fabricate metrics not present in the evidence payload.\n"
            "- If data is absent, state \"data not available\" rather than estimating.\n"
            "\n"
            f"Current mode: {mode}\n"
            f"Current date (AEST): {date_str}\n"
        )

        prefs: dict[str, str] = {}
        if self._state_store is not None:
            try:
                prefs = self._state_store.get_preferences()
            except Exception:
                pass

        if prefs:
            pref_lines = [f"  {k}: {v}" for k, v in prefs.items()]
            instruction += "\nUser preferences:\n" + "\n".join(pref_lines) + "\n"

        # Cross-session episodic memory
        if self._state_store:
            try:
                recent_sessions = self._state_store.get_recent_session_summaries(limit=2)
                if recent_sessions:
                    session_lines = []
                    for s in recent_sessions:
                        tickers_str = ", ".join(s.get("tickers", [])[:5])
                        session_lines.append(
                            f"  {s['date']}: {s['summary']}"
                            + (f" [tickers: {tickers_str}]" if tickers_str else "")
                        )
                    instruction += "\nPrior session context:\n" + "\n".join(session_lines) + "\n"
            except Exception:
                pass

        return instruction

    def build_chat_response(
        self,
        message: str,
        enable_web: bool = False,
        prior_ticker: str | None = None,
        on_chunk=None,
        analysis_mode: str | None = None,
        context_profile: str | None = None,
    ) -> ChatResponse:
        ticker = self._detect_ticker(message, prior_ticker=prior_ticker or self.last_ticker)
        self.last_ticker = ticker or self.last_ticker

        msg_lower = message.lower()
        effective_profile = context_profile or os.environ.get("COCKPIT_CONTEXT_PROFILE", "balanced")

        # --- Conversational update shortcut: "update <ticker> announcements" ---
        explicit_ticker_in_message = self._detect_ticker(message, prior_ticker=None)
        if "update" in msg_lower and "announcement" in msg_lower and explicit_ticker_in_message:
            args: dict[str, Any] = {"ticker": explicit_ticker_in_message, "years": 1, "process_documents": True}
            action_preview: dict[str, Any] = {"action_id": "update_ticker_financials", "args": args}
            if self.action_registry:
                try:
                    preview = self.action_registry.preview("update_ticker_financials", args)
                    action_preview["command"] = preview.command
                    action_preview["impact"] = preview.estimated_impact
                    action_preview["timeout_seconds"] = preview.timeout_seconds
                except Exception:
                    pass
            return ChatResponse(
                text=f"Preparing to update announcements for {explicit_ticker_in_message}. Use /confirm to execute.",
                evidence=[],
                action_preview=action_preview,
                mode=ResponseMode.ACTION,
            )

        # --- Access request: URL in message but web is disabled ---
        if any(p in message for p in ("http://", "https://")) and not enable_web:
            return ChatResponse(
                text="Web access is required to fetch that URL. Enable web and try again.",
                evidence=[],
                action_preview={"action_id": "__access_request__", "args": {"scope": "web"}},
                mode=ResponseMode.FAST,
            )

        # --- Access request: max-depth profile requires web enrichment ---
        if effective_profile == "max-depth" and not enable_web:
            return ChatResponse(
                text="Max-depth analysis requires web enrichment. Enable web and try again.",
                evidence=[],
                action_preview={"action_id": "__access_request__", "args": {"scope": "web"}},
                mode=ResponseMode.FAST,
            )

        # --- Chart intent short-circuit (before general action detection) ---
        if self.detect_chart_intent(message):
            from cockpit.core.chart_args import prepare_chart_action_args

            chart_ticker = ticker or "BHP"
            out_dir = Path("reports") / "candles"

            def _default_parse_kv(raw: str) -> dict:
                out: dict = {}
                for tok in str(raw or "").split():
                    if "=" not in tok:
                        continue
                    k, v = tok.split("=", 1)
                    out[k] = v
                return out

            _parse_kv = getattr(self.action_registry, "parse_kv_args", _default_parse_kv)
            chart_args, chart_err = prepare_chart_action_args(
                chart_ticker,
                parse_kv_args=_parse_kv,
                tool_router=self.tool_router,
                out_dir=out_dir,
            )
            if chart_err:
                return ChatResponse(
                    text=f"/chart failed: {chart_err}",
                    evidence=[{"type": "chart_error", "details": {"error": chart_err, "ticker": chart_ticker}}],
                    action_preview=None,
                    mode=ResponseMode.ACTION,
                )
            if chart_args is None:
                return ChatResponse(
                    text=f"/chart failed: no chart args returned for {chart_ticker}",
                    evidence=[{"type": "chart_error", "details": {"ticker": chart_ticker}}],
                    action_preview=None,
                    mode=ResponseMode.ACTION,
                )
            chart_args["ticker"] = chart_ticker
            preview = self.action_registry.preview("show_candlestick", chart_args)
            return ChatResponse(
                text=f"Running candlestick chart for {chart_ticker}...",
                evidence=[{"type": "chart_action", "details": {"ticker": chart_ticker, **chart_args}}],
                action_preview={
                    "action_id": "show_candlestick",
                    "args": chart_args,
                    "command": preview.command,
                    "impact": preview.estimated_impact,
                    "timeout_seconds": preview.timeout_seconds,
                },
                mode=ResponseMode.ACTION,
            )

        # --- Price history short-circuit ---
        price_history_result = self._try_price_history_shortcircuit(message, ticker)
        if price_history_result is not None:
            return price_history_result

        action_id = self.detect_action_intent(message)
        if action_id:
            mode = ResponseMode.ACTION
        else:
            mode = self.classify_request(message, enable_web=enable_web)

        # --- Access request: deep analysis requires RAG but it's disabled ---
        rag_available = bool(getattr(self.tool_router, "qual_context_reader", None))
        rag_enabled = bool(getattr(self.tool_router, "qual_context_enabled", False))
        if analysis_mode == "deep" and rag_available and not rag_enabled:
            return ChatResponse(
                text="Deep analysis requires RAG context. Enable RAG and try again.",
                evidence=[],
                action_preview={"action_id": "__access_request__", "args": {"scope": "rag"}},
                mode=ResponseMode.FAST,
            )

        deep_mode = mode in {ResponseMode.DEEP_ANALYSIS, ResponseMode.VERIFICATION}
        local_context = self.tool_router.gather_local_context(ticker=ticker, query=message, deep_mode=deep_mode)

        evidence = [
            {"type": "local_context", "details": local_context.payload},
        ]

        if action_id:
            args = {"ticker": ticker or "BHP"}
            preview = self.action_registry.preview(action_id, args)
            return ChatResponse(
                text=(
                    f"Action candidate detected: {action_id}. "
                    f"Use /confirm to execute or /cancel to skip.\n"
                    f"Command: {' '.join(preview.command)}"
                ),
                evidence=evidence,
                action_preview={
                    "action_id": action_id,
                    "args": args,
                    "command": preview.command,
                    "impact": preview.estimated_impact,
                    "timeout_seconds": preview.timeout_seconds,
                },
                mode=mode,
            )

        if mode == ResponseMode.WEB:
            maybe_url = re.search(r"https?://\S+", message)
            if maybe_url:
                web = self.tool_router.fetch_web(maybe_url.group(0), enabled=True)
                evidence.append({"type": "web", "details": web.payload})

        # --- Web enrichment for deep mode or max-depth profile ---
        if (analysis_mode == "deep" or effective_profile == "max-depth") and enable_web:
            if hasattr(self.tool_router, "web_enrich"):
                web_query = f"{ticker}: {message}" if ticker else message
                web_result = self.tool_router.web_enrich(web_query, enabled=True)
                evidence.append({"type": "web", "details": web_result.payload})

        # --- Announcement sync check ---
        if "announcement" in msg_lower and ticker:
            local_docs = (local_context.payload or {}).get("docs", []) if isinstance(local_context.payload, dict) else []
            sync = self._compute_announcement_sync_status(ticker, docs=local_docs, message=message)
            offer = self._build_ticker_update_offer(ticker, sync)
            return ChatResponse(
                text=offer.get("note", ""),
                evidence=evidence,
                action_preview=offer.get("action_preview"),
                mode=ResponseMode.FAST,
            )

        local_payload = dict(local_context.payload) if isinstance(local_context.payload, dict) else {}
        if mode == ResponseMode.WEB:
            local_payload["web_requested"] = True
        local_payload["response_mode"] = mode.value

        system_instruction = self._build_system_instruction(
            mode=mode.value, ticker=ticker, local_payload=local_payload
        )
        if mode == ResponseMode.DEEP_ANALYSIS:
            system_instruction += (
                "This is a deep analysis request. Synthesize the evidence, call out risks, "
                "and be explicit about uncertainty and missing support.\n"
            )
        elif mode == ResponseMode.VERIFICATION:
            system_instruction += (
                "This is a verification request. Focus on current state, failures, and what is "
                "confirmed versus inferred.\n"
            )
        elif mode == ResponseMode.WEB:
            system_instruction += "The user supplied a URL. Incorporate any fetched web evidence if it is available.\n"

        # Inject recent conversation history for context continuity
        history_block = ""
        if self._state_store is not None:
            try:
                history_msgs = self._state_store.get_chat_messages(self._thread_id, limit=12)
                # Exclude the most recent message (current turn, just stored)
                prior_turns = history_msgs[:-1] if history_msgs else []
                if prior_turns:
                    lines = []
                    for m in prior_turns[-6:]:  # last 6 turns max
                        role = m.get("role", "user")
                        content = str(m.get("content", ""))[:400]  # cap per message
                        lines.append(f"{role}: {content}")
                    history_block = "Recent conversation:\n" + "\n".join(lines)
            except Exception:
                pass  # history is best-effort, never fail the main response

        # Prepend pre-computed financial summaries for LLM clarity
        context_sections = []

        if local_payload.get("financials_narrative"):
            context_sections.append("Financial Trend Summary:\n" + local_payload["financials_narrative"])

        if local_payload.get("valuation_multiples"):
            vm = local_payload["valuation_multiples"]
            mv_lines = []
            for k, v in vm.items():
                if v is not None:
                    mv_lines.append(f"  {k}: {v}")
            if mv_lines:
                context_sections.append("Valuation Multiples:\n" + "\n".join(mv_lines))

        if local_payload.get("agent_memory"):
            mem_lines = []
            for obs in local_payload["agent_memory"]:
                mem_lines.append(f"  [{obs.get('type', 'note')}] {obs.get('content', '')}")
            if mem_lines:
                context_sections.append("Prior agent observations about this ticker:\n" + "\n".join(mem_lines[:6]))

        if local_payload.get("prior_export"):
            pe = local_payload["prior_export"]
            prior_ticker = ticker or str(local_payload.get("ticker") or "")
            context_sections.append(
                f"Most recent prior analysis for {prior_ticker}:\n"
                f"  Question: {pe.get('question', '')}\n"
                f"  (Run on {pe.get('date', 'unknown')})"
            )

        runtime_settings = {
            "context_profile": effective_profile,
            "response_mode": mode.value,
        }
        evidence_section = (
            "Local evidence JSON:\n"
            + f"{json.dumps(local_payload)[:7000]}\n"
            + "\nRuntime settings JSON:\n"
            + f"{json.dumps(runtime_settings)}\n"
            + "Change context depth: /context-profile balanced|max-depth\n"
        )

        if context_sections:
            evidence_section += "\n\n" + "\n\n".join(context_sections)

        if history_block:
            prompt = (
                system_instruction
                + "\n\n"
                + history_block
                + "\n\nUser question: "
                + message
                + "\n\n"
                + evidence_section
            )
        else:
            prompt = system_instruction + f"User question: {message}\n\n" + evidence_section

        if on_chunk is not None:
            try:
                answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds, on_chunk=on_chunk)
            except TypeError as exc:
                if "on_chunk" not in str(exc):
                    raise
                answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds)
        else:
            answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds)

        if analysis_mode == "deep" and (
            self._looks_like_framework_only_analysis(
                answer=answer, ticker=ticker or "", local_payload=local_payload
            )
            or self._violates_deep_output_contract(answer)
        ):
            answer = self._build_grounded_deep_analysis_brief(
                ticker=ticker or str(local_payload.get("ticker") or ""),
                message=message,
                local_payload=local_payload,
            )

        # Extract and store ticker observations from this response
        if self._state_store is not None and ticker:
            try:
                obs_list = ChatController._extract_ticker_observations(ticker, answer)
                for obs in obs_list:
                    self._state_store.add_entity_observation(
                        ticker=ticker,
                        observation_type=obs["type"],
                        content=obs["content"],
                        source="chat",
                    )
            except Exception:
                pass  # observations are best-effort, never block the response

        return ChatResponse(text=answer.strip(), evidence=evidence, mode=mode, prompt=prompt)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    _DEEP_REQUIRED_HEADERS = ("Verdict:", "Evidence:", "Risks:", "Counterpoints:", "Unknowns:")

    def _violates_deep_output_contract(self, text: str) -> bool:
        """Return True if text is missing required deep-analysis headers or source anchors."""
        for header in self._DEEP_REQUIRED_HEADERS:
            if header not in text:
                return True
        return "[source:" not in text.lower()

    def _looks_like_framework_only_analysis(
        self, *, answer: str, ticker: str, local_payload: dict[str, Any]  # noqa: ARG002
    ) -> bool:
        """Return True if the answer looks like an empty outline with no grounded evidence."""
        # Must have numbered markdown section headers (### N. ...) to be a framework answer.
        if not re.search(r"^###\s+\d+\.", answer, re.MULTILINE):
            return False
        # If the answer contains date anchors or score values, it has some grounding.
        if re.search(r"\d{4}-\d{2}-\d{2}", answer):
            return False
        if re.search(r"\bscore\b\s+\d+\.\d|\b0\.\d{3,}\b", answer, re.IGNORECASE):
            return False
        return True

    def _build_grounded_deep_analysis_brief(
        self, *, ticker: str, message: str, local_payload: dict[str, Any]  # noqa: ARG002
    ) -> str:
        """Build a structured evidence brief directly from local_payload, bypassing the LLM."""
        lines: list[str] = []
        evidence_lines: list[str] = []

        # --- Qual context hits (deduped by file, path-cleaned) ---
        qual = local_payload.get("qual_context") or {}
        hits = [h for h in (qual.get("hits") or []) if isinstance(h, dict)]
        seen_files: dict[str, float] = {}
        unique_hits: list[dict[str, Any]] = []
        for hit in sorted(hits, key=lambda h: float(h.get("score") or h.get("final_score") or 0.0), reverse=True):
            file_key = str(hit.get("file") or hit.get("title") or "")
            score = float(hit.get("score") or hit.get("final_score") or 0.0)
            if file_key and file_key in seen_files:
                continue
            if file_key:
                seen_files[file_key] = score
            unique_hits.append(hit)
        for hit in unique_hits:
            score = float(hit.get("score") or hit.get("final_score") or 0.0)
            date = str(hit.get("published_at") or "")[:10]
            raw_file = str(hit.get("file") or "")
            title = str(hit.get("title") or "")
            # Clean absolute paths — use basename only.
            src_label = Path(raw_file).name if raw_file else title
            evidence_lines.append(f"- score {score:.3f} | {date} | {title or src_label} [source: {src_label}]")

        # --- Doc snippets — signal extraction for liquidity/refinancing terms ---
        _SIGNAL_TERMS = re.compile(
            r"liquidity|refinanc|cash\s+runway|undrawn|debt\s+facilit|maturity|covenant", re.IGNORECASE
        )
        snippets = [s for s in (local_payload.get("doc_snippets") or []) if isinstance(s, dict)]
        signal_snippets: list[str] = []
        for snippet in snippets:
            excerpt = str(snippet.get("excerpt") or "")
            if _SIGNAL_TERMS.search(excerpt):
                src = str(snippet.get("title") or "document")
                excerpt_short = excerpt[:200]
                signal_snippets.append(f'- "{excerpt_short}" [source: {src}]')
        if signal_snippets:
            evidence_lines.append("Signal extraction identified concrete liquidity/refinancing snippets:")
            evidence_lines.extend(signal_snippets)

        # --- Data quality signals ---
        dq = local_payload.get("data_quality") or {}
        for failure in (dq.get("recent_failures") or []):
            if isinstance(failure, dict):
                evidence_lines.append(
                    f"- Extraction failed for {failure.get('title', 'unknown')} [source: extraction_runs/documents]"
                )
        for row in (dq.get("recent_low_conf_rows") or []):
            if isinstance(row, dict):
                conf = float(row.get("confidence_metrics") or 0.0)
                period = str(row.get("period_type") or "")
                period_end = str(row.get("period_end") or "")
                evidence_lines.append(
                    f"- Low-confidence financials: {period} {period_end} conf={conf:.2f} [source: asx_periodic_financials]"
                )

        # --- Price horizons ---
        for period, ph in (local_payload.get("price_horizons") or {}).items():
            if isinstance(ph, dict) and ph.get("ok"):
                tr = float(ph.get("total_return_pct") or 0.0)
                md = float(ph.get("max_drawdown_pct") or 0.0)
                vol = float(ph.get("volatility_ann_pct") or 0.0)
                evidence_lines.append(
                    f"- total_return={tr:.2f}% max_drawdown={md:.2f}% volatility={vol:.2f}% over {period} "
                    f"[source: price_horizon_{period}]"
                )

        # --- Web facts ---
        for fact in (local_payload.get("web_facts") or []):
            if isinstance(fact, dict):
                claim = str(fact.get("claim") or "")
                url = str(fact.get("url") or "")
                evidence_lines.append(f"- Web fact: {claim} [source: {url}]")

        # Assemble structured brief.
        n_sources = len(evidence_lines)
        lines.append("Verdict:")
        lines.append(
            f"{ticker}: Grounded analysis based on {n_sources} evidence item(s) from local context."
        )
        lines.append("")
        lines.append("Evidence:")
        lines.extend(evidence_lines if evidence_lines else ["- No local evidence available."])
        lines.append("")
        lines.append("Risks:")
        lines.append("- Dependent on availability and recency of evidence above.")
        lines.append("")
        lines.append("Counterpoints:")
        lines.append("- Data coverage may be partial; full picture requires additional sources.")
        lines.append("")
        lines.append("Unknowns:")
        lines.append("- Items not yet disclosed or unavailable in local evidence.")

        return "\n".join(lines)
