from __future__ import annotations

import json
import re
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
    def __init__(self, ollama_client, tool_router, action_registry, llm_timeout_seconds: float = 300.0) -> None:
        self.ollama_client = ollama_client
        self.tool_router = tool_router
        self.action_registry = action_registry
        self.llm_timeout_seconds = float(llm_timeout_seconds)
        self.last_ticker: str | None = None

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
    }

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

    def build_chat_response(
        self,
        message: str,
        enable_web: bool = False,
        prior_ticker: str | None = None,
        on_chunk=None,
    ) -> ChatResponse:
        ticker = self._detect_ticker(message, prior_ticker=prior_ticker or self.last_ticker)
        self.last_ticker = ticker or self.last_ticker

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

        local_payload = dict(local_context.payload) if isinstance(local_context.payload, dict) else {}
        if mode == ResponseMode.WEB:
            local_payload["web_requested"] = True
        local_payload["response_mode"] = mode.value

        system_instruction = (
            "You are the Financial Engine cockpit analyst.\n"
            "Use the local evidence below first. If confidence is weak, say so.\n"
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

        prompt = (
            system_instruction
            + f"User question: {message}\n\n"
            + "Local evidence JSON:\n"
            + f"{json.dumps(local_payload)[:7000]}\n"
        )

        if on_chunk is not None:
            try:
                answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds, on_chunk=on_chunk)
            except TypeError as exc:
                if "on_chunk" not in str(exc):
                    raise
                answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds)
        else:
            answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds)

        return ChatResponse(text=answer.strip(), evidence=evidence, mode=mode, prompt=prompt)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
