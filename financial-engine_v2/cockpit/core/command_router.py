"""Command pre-router for the cockpit agent loop.

Intercepts imperative user commands (ingest, chart, review, update)
BEFORE the agent loop runs, converting them directly to action proposals
or structured intents. This avoids the model misinterpreting commands as
questions and failing to produce the right action_proposal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = ["CommandRoute", "route_command"]


@dataclass
class CommandRoute:
    """A pre-parsed command that can skip or shortcut the agent loop."""
    matched: bool
    action_type: str | None = None   # "action_proposal", "direct_action", None
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    explanation: str | None = None


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_INGEST_RE = re.compile(
    r"^\s*(?:ingest|fetch\s+news)\s+(?:news\s+(?:for\s+)?)?([A-Z]{2,5})\b",
    re.IGNORECASE,
)
_INGEST_MARKET_RE = re.compile(
    r"^\s*(?:ingest|fetch)\s+(?:market\s+)?news\s*$",
    re.IGNORECASE,
)
_UPDATE_RE = re.compile(
    r"^\s*(?:update|refresh\s+financials?)\s+([A-Z]{2,5})\b",
    re.IGNORECASE,
)
_CHART_RE = re.compile(
    r"^\s*(?:chart|show\s+chart|candlestick)\s+([A-Z]{2,5})\b|"
    r"^\s*([A-Z]{2,5})\s+chart\s*$",
    re.IGNORECASE,
)
_BACKFILL_RE = re.compile(
    r"^\s*(?:backfill|run\s+backfill)\s+([A-Z]{2,5})\b",
    re.IGNORECASE,
)
_ANALYSIS_RE = re.compile(
    r"^\s*(?:run\s+analysis|analyse|analyze)\s+([A-Z]{2,5})\b",
    re.IGNORECASE,
)

_WATCH_CHANNEL_RE = re.compile(
    r"""
    ^\s*
    (?:
        watch\s+(?:youtube\s+)?(?:videos?\s+from\s+|channel\s+)?  # watch [youtube] [videos from | channel]
      | monitor\s+(?:youtube\s+)?(?:channel\s+)?                  # monitor [youtube] [channel]
      | add\s+(?:youtube\s+)?channel\s+                           # add [youtube] channel
      | subscribe\s+to\s+                                         # subscribe to
      | follow\s+(?:youtube\s+)?(?:channel\s+)?                   # follow [youtube] [channel]
    )
    (.+)$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TICKER_STOPWORDS = frozenset({
    "ASX", "ETF", "IPO", "CEO", "AGM", "EGM", "FY", "HY",
    "USA", "AUS", "GDP", "CPI", "RBA", "AUD", "USD",
})


def route_command(
    message: str,
    *,
    active_ticker: str | None = None,
) -> CommandRoute:
    """Attempt to match *message* as a direct command.

    Returns a ``CommandRoute`` with ``matched=True`` if the message
    is a recognized imperative command, along with the pre-built
    action proposal payload. Returns ``matched=False`` otherwise.
    """
    text = str(message or "").strip()

    # ingest [ticker] news
    m = _INGEST_RE.match(text)
    if m:
        ticker = m.group(1).upper()
        if ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="action_proposal",
                tool="run_news_ingest",
                arguments={"since_hours": 24, "ticker": ticker},
                explanation=f"Ingest latest news for {ticker} (last 24h).",
            )

    # ingest market news (no ticker)
    if _INGEST_MARKET_RE.match(text):
        return CommandRoute(
            matched=True,
            action_type="action_proposal",
            tool="run_news_ingest",
            arguments={"since_hours": 24},
            explanation="Ingest latest market-wide news (last 24h).",
        )

    # update / refresh financials [ticker]
    m = _UPDATE_RE.match(text)
    if m:
        ticker = m.group(1).upper()
        if ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="action_proposal",
                tool="update_financials",
                arguments={"ticker": ticker},
                explanation=f"Update financial data for {ticker}.",
            )

    # chart [ticker] / [ticker] chart
    m = _CHART_RE.match(text)
    if m:
        ticker = (m.group(1) or m.group(2) or "").upper()
        if not ticker and active_ticker:
            ticker = active_ticker
        if ticker and ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="action_proposal",
                tool="generate_chart",
                arguments={"ticker": ticker, "range": "6mo"},
                explanation=f"Show candlestick chart for {ticker} (6 months).",
            )

    # backfill [ticker]
    m = _BACKFILL_RE.match(text)
    if m:
        ticker = m.group(1).upper()
        if ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="action_proposal",
                tool="run_backfill",
                arguments={"ticker": ticker, "years": 2},
                explanation=f"Backfill financial data for {ticker} (2 years).",
            )

    # run analysis [ticker]
    m = _ANALYSIS_RE.match(text)
    if m:
        ticker = m.group(1).upper()
        if ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="action_proposal",
                tool="run_analysis",
                arguments={"ticker": ticker},
                explanation=f"Run full analysis pipeline for {ticker}.",
            )

    # watch/monitor/add/subscribe/follow youtube channel
    m = _WATCH_CHANNEL_RE.match(text)
    if m:
        channel_name = m.group(1).strip()
        if channel_name:
            return CommandRoute(
                matched=True,
                action_type=None,
                tool="watch_youtube_channel",
                arguments={"channel_name": channel_name},
                explanation=f"Add YouTube channel {channel_name!r} to the watch list.",
            )

    return CommandRoute(matched=False)
