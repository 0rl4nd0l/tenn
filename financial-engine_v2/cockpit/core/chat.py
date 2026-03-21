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
    _CHART_KEYWORDS = re.compile(
        r"\b(?:candlestick|candle|chart|price\s+history|plot)\b"
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
            chart_args, chart_err = prepare_chart_action_args(
                message if not ticker else chart_ticker,
                parse_kv_args=self.action_registry.parse_kv_args,
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
            assert chart_args is not None
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
