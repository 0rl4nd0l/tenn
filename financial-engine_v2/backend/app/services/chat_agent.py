"""Minimal LLM-driven agent loop with tool calling for the Financial Engine.

Provides a /chat endpoint that:
- Connects to Ollama for LLM inference
- Exposes tools for price, docs, financials, chart data
- Runs a loop: LLM -> optional tool call -> feed result -> LLM
- Grounds all responses in real data (no fabrication)
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.documents import Document
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.providers.market_price_provider import MarketPriceProvider, MarketPriceProviderError

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5
OLLAMA_CHAT_TIMEOUT = 180.0

SYSTEM_PROMPT = """\
You are a financial analysis assistant for ASX (Australian Securities Exchange) stocks.
You have access to real-time tools. ALWAYS use them when the user asks about prices, \
documents, financials, or charts. Never fabricate financial data.

Available tools (call by responding with a TOOL_CALL line):

1. get_ticker_price(ticker)
   Returns current price, change, and recent history for an ASX ticker.

2. get_ticker_docs(ticker)
   Returns recent announcements/documents filed by the company on ASX.

3. get_chart_data(ticker, range)
   Returns OHLCV history. range can be: 5d, 1mo, 3mo, 6mo, 1y, 5y.

4. get_financials(ticker)
   Returns extracted periodic financial metrics (revenue, EBIT, cash flow, etc.).

5. search_docs(query)
   Searches document titles across all tickers.

TOOL CALLING FORMAT — to call a tool, output EXACTLY one line:
TOOL_CALL: {"name": "<function>", "args": {"<param>": "<value>"}}

Example:
TOOL_CALL: {"name": "get_ticker_price", "args": {"ticker": "BHP"}}

RULES:
- Call ONE tool at a time. After receiving the result, you may call another.
- When asked about a price, ALWAYS call get_ticker_price first.
- When asked about news/documents/announcements, call get_ticker_docs.
- When asked for a chart, call get_chart_data.
- When asked to compare tickers, call tools for each ticker.
- For transcript analysis: read the provided text, identify companies/tickers, \
call tools if needed, then provide structured analysis.
- If a tool returns an error, report it honestly — do not invent data.
- Always distinguish between retrieved facts and your inferences.
- If data is insufficient, say so explicitly.
"""

TRANSCRIPT_ANALYSIS_ADDENDUM = """\

The user has provided a transcript or long text for analysis. Your task:
1. Identify key companies, tickers, and financial topics mentioned.
2. Use tools to retrieve current data for mentioned tickers.
3. Provide structured analysis with sections:
   - Summary of Key Points
   - Companies/Tickers Identified
   - Market Data (from tools)
   - Strategic Assessment
   - Risks and Considerations
   - Recommended Actions (with confidence level)
Ground every claim in data from the transcript or from tool results.
"""


def _normalize_ollama_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        value = "http://localhost:11434"
    if "://" not in value:
        value = f"http://{value}"
    if value.lower().endswith("/api"):
        value = value[:-4]
    return value


def _parse_tool_call(text: str) -> dict[str, Any] | None:
    """Extract a TOOL_CALL JSON from the LLM response."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("TOOL_CALL:"):
            json_part = stripped[len("TOOL_CALL:"):].strip()
            json_part = re.sub(r"^```(?:json)?\s*", "", json_part)
            json_part = re.sub(r"\s*```$", "", json_part)
            try:
                parsed = json.loads(json_part)
                if isinstance(parsed, dict) and "name" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass
    match = re.search(
        r'\{\s*"name"\s*:\s*"(get_ticker_price|get_ticker_docs|get_chart_data|get_financials|search_docs)"',
        text,
    )
    if match:
        start = text.index(match.group(0))
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


class ChatAgent:
    """Minimal agent loop: LLM decides whether to respond or call a tool."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.ollama_url = _normalize_ollama_url(settings.ollama_url)
        self.model = getattr(settings, "extract_model", "llama3.1:8b")
        self._price_provider = MarketPriceProvider(
            base_url=getattr(settings, "market_data_base_url", "https://query1.finance.yahoo.com"),
            timeout=getattr(settings, "market_data_timeout_seconds", 20.0),
        )
        self.tool_log: list[dict[str, Any]] = []

    def _call_ollama_chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.ollama_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "top_p": 0.9},
        }
        logger.info("Ollama request: model=%s messages=%d", self.model, len(messages))
        t0 = time.monotonic()
        with httpx.Client(timeout=OLLAMA_CHAT_TIMEOUT) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        elapsed = time.monotonic() - t0
        data = resp.json()
        content = (data.get("message") or {}).get("content") or ""
        logger.info("Ollama response: %.1fs, %d chars", elapsed, len(content))
        return content

    # ------------------------------------------------------------------
    # Tool implementations — all use real data sources
    # ------------------------------------------------------------------

    def tool_get_ticker_price(self, ticker: str) -> dict[str, Any]:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return {"error": "ticker is required"}
        try:
            raw = self._price_provider.fetch(
                ticker=ticker, exchange="ASX", range_="1mo", interval="1d",
            )
        except (ValueError, MarketPriceProviderError) as exc:
            return {"error": str(exc), "ticker": ticker}
        current = raw.get("current", {})
        history = raw.get("history", [])
        prev_close = current.get("previous_close")
        price = current.get("price")
        change = None
        change_pct = None
        if price is not None and prev_close not in (None, 0):
            try:
                change = round(float(price) - float(prev_close), 4)
                change_pct = round((change / float(prev_close)) * 100, 2)
            except Exception:
                pass
        return {
            "ticker": ticker,
            "currency": raw.get("currency"),
            "price": price,
            "previous_close": prev_close,
            "change": change,
            "change_percent": change_pct,
            "open": current.get("open"),
            "day_high": current.get("day_high"),
            "day_low": current.get("day_low"),
            "volume": current.get("volume"),
            "market_time": current.get("market_time"),
            "recent_closes": [
                {"date": h.get("timestamp"), "close": h.get("close")}
                for h in (history or [])[-10:]
                if h.get("close") is not None
            ],
        }

    def tool_get_ticker_docs(self, ticker: str) -> dict[str, Any]:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return {"error": "ticker is required"}
        rows = (
            self.db.query(Document)
            .filter(Document.ticker == ticker)
            .order_by(Document.published_at.desc().nullslast())
            .limit(15)
            .all()
        )
        return {
            "ticker": ticker,
            "count": len(rows),
            "documents": [
                {
                    "title": r.title,
                    "doc_class": r.doc_class,
                    "doc_subtype": r.doc_subtype,
                    "published_at": str(r.published_at) if r.published_at else None,
                    "source_url": r.source_url,
                }
                for r in rows
            ],
        }

    def tool_get_chart_data(self, ticker: str, range_: str = "3mo") -> dict[str, Any]:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return {"error": "ticker is required"}
        range_ = (range_ or "3mo").strip()
        try:
            raw = self._price_provider.fetch(
                ticker=ticker, exchange="ASX", range_=range_, interval="1d",
            )
        except (ValueError, MarketPriceProviderError) as exc:
            return {"error": str(exc), "ticker": ticker}
        history = raw.get("history", [])
        return {
            "ticker": ticker,
            "range": range_,
            "currency": raw.get("currency"),
            "points": len(history),
            "chart": [
                {
                    "date": h.get("timestamp"),
                    "open": h.get("open"),
                    "high": h.get("high"),
                    "low": h.get("low"),
                    "close": h.get("close"),
                    "volume": h.get("volume"),
                }
                for h in history
            ],
        }

    def tool_get_financials(self, ticker: str) -> dict[str, Any]:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return {"error": "ticker is required"}
        rows = (
            self.db.query(ASXPeriodicFinancial)
            .filter(ASXPeriodicFinancial.ticker == ticker)
            .order_by(ASXPeriodicFinancial.period_end.desc())
            .limit(10)
            .all()
        )
        def n(x: Any) -> str | None:
            return str(x) if x is not None else None
        return {
            "ticker": ticker,
            "count": len(rows),
            "periods": [
                {
                    "period_end": str(r.period_end) if r.period_end else None,
                    "period_type": r.period_type,
                    "revenue": n(r.revenue),
                    "ebit": n(r.ebit),
                    "np_attributable": n(r.np_attributable),
                    "operating_cf": n(r.operating_cf),
                    "capex": n(r.capex),
                    "cash_end": n(r.cash_end),
                    "net_debt": n(r.net_debt),
                    "confidence": r.confidence_metrics,
                }
                for r in rows
            ],
        }

    def tool_search_docs(self, query: str) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {"error": "query is required"}
        pattern = f"%{query}%"
        rows = (
            self.db.query(Document)
            .filter(Document.title.ilike(pattern))
            .order_by(Document.published_at.desc().nullslast())
            .limit(15)
            .all()
        )
        return {
            "query": query,
            "count": len(rows),
            "documents": [
                {
                    "ticker": r.ticker,
                    "title": r.title,
                    "doc_class": r.doc_class,
                    "published_at": str(r.published_at) if r.published_at else None,
                }
                for r in rows
            ],
        }

    def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        t0 = time.monotonic()
        if name == "get_ticker_price":
            result = self.tool_get_ticker_price(args.get("ticker", ""))
        elif name == "get_ticker_docs":
            result = self.tool_get_ticker_docs(args.get("ticker", ""))
        elif name == "get_chart_data":
            result = self.tool_get_chart_data(
                args.get("ticker", ""), args.get("range", "3mo"),
            )
        elif name == "get_financials":
            result = self.tool_get_financials(args.get("ticker", ""))
        elif name == "search_docs":
            result = self.tool_search_docs(args.get("query", ""))
        else:
            result = {"error": f"Unknown tool: {name}"}
        elapsed = time.monotonic() - t0
        log_entry = {
            "tool": name,
            "args": args,
            "elapsed_seconds": round(elapsed, 3),
            "has_error": "error" in result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.tool_log.append(log_entry)
        logger.info("Tool executed: %s(%s) in %.3fs", name, args, elapsed)
        return result

    def run(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Run the agent loop for a user message.

        Returns a dict with: response, tool_calls, model, iterations.
        """
        is_transcript = len(message) > 2000

        system_content = SYSTEM_PROMPT
        if is_transcript:
            system_content += TRANSCRIPT_ANALYSIS_ADDENDUM

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

        if history:
            for entry in history[-20:]:
                role = entry.get("role", "user")
                content = entry.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        tool_calls_made: list[dict[str, Any]] = []

        for iteration in range(MAX_TOOL_ITERATIONS):
            try:
                llm_response = self._call_ollama_chat(messages)
            except httpx.ConnectError as exc:
                logger.error("Ollama connection failed: %s", exc)
                return {
                    "response": (
                        f"LLM connection failed: cannot reach Ollama at {self.ollama_url}. "
                        "Ensure Ollama is running and OLLAMA_URL is correct."
                    ),
                    "tool_calls": tool_calls_made,
                    "tool_log": self.tool_log,
                    "model": self.model,
                    "iterations": iteration + 1,
                    "error": str(exc),
                }
            except httpx.HTTPStatusError as exc:
                logger.error("Ollama HTTP error: %s", exc)
                return {
                    "response": f"LLM request failed: HTTP {exc.response.status_code}",
                    "tool_calls": tool_calls_made,
                    "tool_log": self.tool_log,
                    "model": self.model,
                    "iterations": iteration + 1,
                    "error": str(exc),
                }
            except Exception as exc:
                logger.error("Ollama error: %s", exc)
                return {
                    "response": f"LLM error: {exc}",
                    "tool_calls": tool_calls_made,
                    "tool_log": self.tool_log,
                    "model": self.model,
                    "iterations": iteration + 1,
                    "error": str(exc),
                }

            tool_call = _parse_tool_call(llm_response)

            if tool_call is None:
                return {
                    "response": llm_response,
                    "tool_calls": tool_calls_made,
                    "tool_log": self.tool_log,
                    "model": self.model,
                    "iterations": iteration + 1,
                }

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            if not isinstance(tool_args, dict):
                tool_args = {}

            logger.info("Agent iteration %d: calling tool %s", iteration, tool_name)
            tool_result = self._execute_tool(tool_name, tool_args)
            tool_calls_made.append({
                "name": tool_name,
                "args": tool_args,
                "result_summary": {
                    k: v for k, v in tool_result.items()
                    if k not in ("chart", "documents", "periods", "recent_closes")
                },
            })

            result_json = json.dumps(tool_result, default=str, indent=2)
            if len(result_json) > 12000:
                result_json = result_json[:12000] + "\n... (truncated)"

            messages.append({"role": "assistant", "content": llm_response})
            messages.append({
                "role": "user",
                "content": f"TOOL_RESULT for {tool_name}:\n{result_json}",
            })

        final_response = self._call_ollama_chat(messages)
        return {
            "response": final_response,
            "tool_calls": tool_calls_made,
            "tool_log": self.tool_log,
            "model": self.model,
            "iterations": MAX_TOOL_ITERATIONS,
            "note": "max iterations reached",
        }
