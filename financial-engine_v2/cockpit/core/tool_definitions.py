"""Tool definitions for the agentic chat loop.

Defines all tools the LLM can invoke, split into read-only (immediate execution)
and mutating (requires user confirmation). Each tool has a JSON-schema-compatible
definition suitable for system prompt injection or native tool calling.

Exports:
    TOOL_DEFINITIONS: list[dict]          — all tool schemas
    TOOL_DEFINITIONS_PROMPT: str          — formatted for system prompt injection
    MUTATING_TOOL_NAMES: frozenset[str]   — safety gate for confirmation checks
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Read-only tools — safe to execute without confirmation
# ---------------------------------------------------------------------------

_READ_ONLY_TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_ticker_data",
        "description": (
            "Query the local database for documents, financial metrics, and "
            "announcements for an ASX ticker. Use this when the user asks about "
            "a company and you need data to answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol, e.g. 'CSL', 'BHP', '29M'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to return",
                    "default": 10,
                },
                "deep": {
                    "type": "boolean",
                    "description": "If true, return expanded context (more docs, financials, snippets)",
                    "default": False,
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "get_company_dump",
        "description": (
            "Get a deterministic full company data dump from the backend authority, "
            "including documents, financials, 1y daily price history, narrative "
            "risk notes, and memory sections."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol, e.g. 'BHP', 'CSL', '29M'",
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "get_price",
        "description": (
            "Get current and recent price data for an ASX ticker, including "
            "price history, technical indicators (SMA, RSI), and trend regime."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "range": {
                    "type": "string",
                    "description": "Price history range, e.g. '1mo', '3mo', '1y', '5y'",
                    "default": "1y",
                },
                "interval": {
                    "type": "string",
                    "description": "Data interval, e.g. '1d', '1wk'",
                    "default": "1d",
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "get_price_on_date",
        "description": (
            "Get the historical closing price for a ticker on a specific date. "
            "Use this for questions like 'What was BHP's price on 2024-01-15?'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format",
                },
            },
            "required": ["ticker", "date"],
        },
        "mutating": False,
    },
    {
        "name": "get_price_range",
        "description": (
            "Get price history between two dates. Use this for questions about "
            "price performance over a specific period."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
            },
            "required": ["ticker", "start_date", "end_date"],
        },
        "mutating": False,
    },
    {
        "name": "get_financials",
        "description": (
            "Get extracted financial metrics (revenue, EBIT, cash flow, net debt) "
            "for a ticker. Returns the most recent extraction runs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of financial periods to return",
                    "default": 6,
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "search_news",
        "description": (
            "Search news articles for a ticker or topic. Returns relevant articles "
            "from the news corpus with relevance scores."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (company name, topic, keywords)",
                },
                "ticker": {
                    "type": "string",
                    "description": "Optional ASX ticker to filter results",
                    "default": "",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        "mutating": False,
    },
    {
        "name": "search_announcements",
        "description": (
            "Search ASX announcements and documents in the local database. "
            "Returns document metadata and announcement context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol to filter announcements",
                    "default": "",
                },
                "query": {
                    "type": "string",
                    "description": "Optional search query to filter by content",
                    "default": "",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of announcements to return",
                    "default": 10,
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "search_files",
        "description": (
            "Search local report files and artifacts by text pattern. "
            "Use this to find generated reports, logs, or exported data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text pattern to search for in file names and content",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of matching files to return",
                    "default": 20,
                },
            },
            "required": ["pattern"],
        },
        "mutating": False,
    },
    {
        "name": "list_recent_reports",
        "description": (
            "List recently generated reports and output files, ordered by "
            "recency. Use this to find what reports are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of reports to list",
                    "default": 10,
                },
            },
            "required": [],
        },
        "mutating": False,
    },
    {
        "name": "get_data_quality",
        "description": (
            "Check extraction quality and data completeness for a ticker. "
            "Returns extraction failures, low-confidence metrics, and quality signals."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "run_analysis",
        "description": (
            "Run the Phase 3 analysis pipeline for a ticker. Executes up to 7 "
            "analysis modules (balance_sheet, roic, risk, valuation, catalysts, "
            "sentiment, moat) and returns a structured summary with key metrics, "
            "narratives, and warnings. Use when the user asks to analyse a ticker, "
            "run analysis, or wants a comprehensive fundamental assessment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol, e.g. 'CSL', 'BHP'",
                },
                "modules": {
                    "type": "string",
                    "description": (
                        "Comma-separated module names to run. "
                        "Valid: balance_sheet, roic, risk, valuation, catalysts, sentiment, moat. "
                        "Omit to run all modules."
                    ),
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "fetch_url",
        "description": (
            "Fetch and return the text content of a web URL. Use this when "
            "the user provides a link or you need to read a web page."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return from the page",
                    "default": 8000,
                },
            },
            "required": ["url"],
        },
        "mutating": False,
    },
    {
        "name": "get_strategy",
        "description": (
            "Get the user's investment strategy criteria and any recorded "
            "decisions. Returns global criteria (apply to all tickers) and "
            "optionally ticker-specific criteria with the current decision."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional ASX ticker to also get ticker-specific criteria and decision",
                },
            },
            "required": [],
        },
        "mutating": False,
    },
    {
        "name": "search_web",
        "description": (
            "Search the web for current information about a company, sector, "
            "or topic. Better than fetch_url for discovery — returns structured "
            "results with titles, URLs, and snippets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (company name, topic, keywords)",
                },
                "count": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        "mutating": False,
    },
    {
        "name": "search_social",
        "description": (
            "Search Hacker News for developer and tech community discussion "
            "about a topic or company. Returns stories with points, comments, "
            "and links. Useful for tech sentiment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of stories to return",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        "mutating": False,
    },
    {
        "name": "recall_dossier",
        "description": (
            "Recall accumulated research findings about a company from past "
            "research sessions. Returns findings stored in the company dossier."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "query": {
                    "type": "string",
                    "description": "Optional keyword filter for findings",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of findings to return",
                    "default": 5,
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "deep_research",
        "description": (
            "Conduct thorough multi-source research on a company. Queries "
            "financials, prices, web news, social sentiment, and prior dossier "
            "findings, then synthesizes a research brief. Use for in-depth "
            "analysis when the user wants a comprehensive view."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus area: earnings, risk, valuation, catalysts",
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "get_watchlist_alerts",
        "description": (
            "Check for material changes detected by the background research "
            "scanner on watchlist tickers. Returns alerts about price moves, "
            "new announcements, and significant news."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "since_hours": {
                    "type": "integer",
                    "description": "Look back N hours for alerts",
                    "default": 24,
                },
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker to filter alerts",
                },
            },
            "required": [],
        },
        "mutating": False,
    },
    {
        "name": "scan_watchlist",
        "description": (
            "Run the full watchlist trigger: analyse each watchlist ticker, "
            "scan artifacts against strategy criteria, and generate alerts. "
            "Returns a summary of tickers scanned, alerts generated, and errors."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "string",
                    "description": "Optional comma-separated tickers to scan (default: all watchlist tickers)",
                    "default": "",
                },
            },
            "required": [],
        },
        "mutating": False,
    },
    # --- Strategy tools (Phase 1-3) ---
    {
        "name": "score_ticker",
        "description": (
            "Compute a composite investment score (0-100) for an ASX ticker. "
            "Combines financial health, valuation multiples, momentum, and "
            "technical indicators into a single ranked score with breakdown."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker symbol"},
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "screen_tickers",
        "description": (
            "Screen and rank multiple tickers by composite score. If no tickers "
            "provided, screens the watchlist. Supports filters for minimum scores, "
            "trend regimes, and valuation thresholds."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ASX tickers to screen. Empty = use watchlist.",
                },
                "min_health_score": {
                    "type": "number",
                    "description": "Minimum financial health score (0-100)",
                },
                "trend_regime": {
                    "type": "string",
                    "description": "Filter by trend: bull, bear, neutral",
                },
                "min_fcf_yield": {
                    "type": "number",
                    "description": "Minimum FCF yield percentage",
                },
                "max_pe": {"type": "number", "description": "Maximum P/E ratio"},
            },
            "required": [],
        },
        "mutating": False,
    },
    {
        "name": "get_valuation",
        "description": (
            "Get valuation multiples for an ASX ticker: market cap, P/E ratio, "
            "FCF yield, EV/EBIT. Combines current price with latest financials."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker symbol"},
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "get_thesis",
        "description": (
            "Get active investment theses for a ticker, including evidence "
            "balance, risk assessment, and signal."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker symbol"},
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "check_decision_outcome",
        "description": (
            "Check what happened since a strategy decision was made. Returns "
            "price change, score change, and outcome quality assessment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker to check"},
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "review_open_decisions",
        "description": (
            "List all strategy decisions that haven't been reviewed yet. "
            "Shows which decisions need reflection based on time elapsed."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "mutating": False,
    },
    {
        "name": "get_tv_indicators",
        "description": (
            "Fetch TradingView technical indicators for a ticker (RSI, MACD, EMA, SMA, etc.). "
            "Uses TradingView's screener data. Available when tradingview-scraper is installed. "
            "Useful for confirming momentum, trend direction, and overbought/oversold conditions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker symbol"},
                "indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Indicator names e.g. ['RSI', 'MACD', 'EMA20', 'SMA50', 'BB_upper']. Defaults to RSI, MACD, EMA20, SMA50.",
                },
                "exchange": {
                    "type": "string",
                    "description": "Exchange prefix (default: ASX). E.g. ASX, NASDAQ, NYSE.",
                },
            },
            "required": ["ticker"],
        },
        "mutating": False,
    },
    {
        "name": "tv_screener",
        "description": (
            "Screen tickers on TradingView for a given market. Returns ranked list with technical "
            "indicator values. Useful for identifying momentum plays, breakouts, or oversold names "
            "across the ASX or other markets. Available when tradingview-scraper is installed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "market": {
                    "type": "string",
                    "description": "Market to screen: 'australia', 'us', 'uk', etc. Defaults to 'australia'.",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filter dict. Supported: min_rs_rating (number).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default: 20).",
                },
            },
            "required": [],
        },
        "mutating": False,
    },
]

# ---------------------------------------------------------------------------
# Mutating tools — require user confirmation before execution
# ---------------------------------------------------------------------------

_MUTATING_TOOLS: list[dict[str, Any]] = [
    {
        "name": "run_backfill",
        "description": (
            "Backfill ASX announcements for a ticker. Downloads historical "
            "announcements and processes documents. Use when no data exists "
            "for a ticker or data is stale."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol to backfill",
                },
                "years": {
                    "type": "integer",
                    "description": "Number of years of history to fetch",
                    "default": 3,
                },
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    {
        "name": "run_metric_extraction",
        "description": (
            "Extract financial metrics from existing documents for a ticker. "
            "Runs LLM-based extraction on downloaded PDFs to populate financials."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    {
        "name": "run_news_ingest",
        "description": (
            "Run daily news ingestion. Fetches recent news articles from "
            "configured providers and indexes them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "since_hours": {
                    "type": "integer",
                    "description": "Fetch articles from the last N hours",
                    "default": 24,
                },
            },
            "required": [],
        },
        "mutating": True,
    },
    {
        "name": "run_announcement_ingest",
        "description": (
            "Run daily ASX announcement ingestion. Fetches today's (or a "
            "specified date's) announcements from the ASX."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to ingest in YYYY-MM-DD format, or 'today'",
                    "default": "today",
                },
            },
            "required": [],
        },
        "mutating": True,
    },
    {
        "name": "update_financials",
        "description": (
            "Re-process financial data for a ticker. Downloads new announcements "
            "and re-extracts metrics. Use when financials may be outdated."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "years": {
                    "type": "integer",
                    "description": "Number of years to re-process",
                    "default": 1,
                },
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    {
        "name": "rebuild_financials",
        "description": (
            "Rebuild financials from existing documents for a ticker. "
            "Re-runs extraction on already-downloaded PDFs without fetching new ones."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    {
        "name": "audit_financials",
        "description": (
            "Run a quality audit on extracted financials for a ticker. "
            "Checks for extraction errors, low-confidence values, and inconsistencies."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    {
        "name": "save_research_finding",
        "description": (
            "Save a research finding to the company dossier for future "
            "reference. Findings persist across sessions and can be recalled "
            "later with recall_dossier."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "finding": {
                    "type": "string",
                    "description": "The research finding to save",
                },
                "source": {
                    "type": "string",
                    "description": "Where this finding came from (e.g. 'web_search', 'announcement', 'analysis')",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level 0.0-1.0",
                    "default": 0.5,
                },
                "category": {
                    "type": "string",
                    "description": "Finding category: news, financial, sentiment, announcement",
                    "default": "general",
                },
            },
            "required": ["ticker", "finding", "source"],
        },
        "mutating": True,
    },
    {
        "name": "generate_chart",
        "description": (
            "Generate a candlestick / price chart for a ticker. "
            "Creates an interactive HTML chart with OHLCV data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "ASX ticker symbol",
                },
                "range": {
                    "type": "string",
                    "description": "Price history range for the chart",
                    "default": "1y",
                },
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    # --- Strategy mutating tools ---
    {
        "name": "create_thesis",
        "description": (
            "Create a structured investment thesis for a ticker with a specific "
            "signal (BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL). Runs a bull/bear "
            "risk gate debate to validate the thesis."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker symbol"},
                "thesis": {
                    "type": "string",
                    "description": "The investment thesis statement",
                },
                "signal": {
                    "type": "string",
                    "description": "Signal: BUY, OVERWEIGHT, HOLD, UNDERWEIGHT, SELL",
                },
                "run_risk_gate": {
                    "type": "boolean",
                    "description": "Run bull/bear debate",
                    "default": True,
                },
            },
            "required": ["ticker", "thesis", "signal"],
        },
        "mutating": True,
    },
    {
        "name": "add_thesis_evidence",
        "description": (
            "Add supporting or disconfirming evidence to the active thesis for a ticker."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker symbol"},
                "finding": {
                    "type": "string",
                    "description": "The evidence finding text",
                },
                "is_supporting": {
                    "type": "boolean",
                    "description": "True=supporting, False=disconfirming",
                    "default": True,
                },
            },
            "required": ["ticker", "finding"],
        },
        "mutating": True,
    },
    {
        "name": "reflect_on_decision",
        "description": (
            "Review the outcome of a past strategy decision and record the "
            "lesson to situation memory for future learning."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ASX ticker to reflect on"},
            },
            "required": ["ticker"],
        },
        "mutating": True,
    },
    {
        "name": "adjust_signal_weights",
        "description": (
            "Adjust the composite scoring weights. Weights must sum to approximately 1.0. "
            "Default: health=0.40, momentum=0.25, valuation=0.20, technical=0.15"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "health": {
                    "type": "number",
                    "description": "Weight for financial health sub-score",
                },
                "momentum": {
                    "type": "number",
                    "description": "Weight for momentum sub-score",
                },
                "valuation": {
                    "type": "number",
                    "description": "Weight for valuation sub-score",
                },
                "technical": {
                    "type": "number",
                    "description": "Weight for technical sub-score",
                },
            },
            "required": ["health", "momentum", "valuation", "technical"],
        },
        "mutating": True,
    },
]

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = _READ_ONLY_TOOLS + _MUTATING_TOOLS

MUTATING_TOOL_NAMES: frozenset[str] = frozenset(
    t["name"] for t in TOOL_DEFINITIONS if t.get("mutating")
)


def _build_prompt() -> str:
    """Format tool definitions as a text block for system prompt injection."""
    lines = ["TOOLS:"]
    for tool in TOOL_DEFINITIONS:
        # Compact JSON without the mutating flag (LLM doesn't need it)
        schema = {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        }
        lines.append(json.dumps(schema, separators=(",", ":")))
    return "\n".join(lines)


TOOL_DEFINITIONS_PROMPT: str = _build_prompt()
