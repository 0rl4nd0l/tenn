"""Query intent classifier for the cockpit agent loop.

Classifies each incoming user message into one of four intents so that
the agent loop can route context injection (ticker, news scope, commands)
appropriately rather than blindly prepending all ambient state to every
message.
"""

from __future__ import annotations

import re
from enum import Enum

from cockpit.core.turn_continuity import (
    ContinuityTurnKind,
    classify_continuity_turn,
)
from shared.ticker_inference import COMMON_TICKER_STOPWORDS

__all__ = ["QueryIntent", "classify_intent"]


class QueryIntent(str, Enum):
    MARKET_WIDE = "market_wide"    # "news today", "market movers" — no specific ticker
    TICKER_SPECIFIC = "ticker_specific"  # "what happened to BHP", "news about CSL"
    COMMAND = "command"            # "ingest VEA", "chart BHP", "review CBA"
    FOLLOWUP = "followup"          # short follow-up in an ongoing ticker thread
    PREVIOUS_TOOL_TRACE_QUESTION = "previous_tool_trace_question"
    CORRECTION_TURN = "correction_turn"
    THESIS_SAVE = "thesis_save"


# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_COMMAND_RE = re.compile(
    r"^\s*(?:"
    r"ingest\b|"
    r"fetch\s+news\b|"
    r"update\b|"
    r"refresh\s+financials?\b|"
    r"chart\b|"
    r"show\s+chart\b|"
    r"review\b|"
    r"run\s+analysis\b|"
    r"backfill\b"
    r")",
    re.IGNORECASE,
)

_MARKET_WIDE_RE = re.compile(
    r"\b(?:"
    r"market\s+(?:today|news|movers?|update|wrap|close|open)|"
    r"today'?s?\s+(?:news|headlines?|movers?|market)|"
    r"broker\s+(?:upgrades?|downgrades?|calls?)|"
    r"what(?:'s|\s+is)\s+(?:moving|happening|in\s+the\s+market)|"
    r"top\s+(?:movers?|performers?|gainers?|losers?)|"
    r"(?:latest|recent|breaking)\s+(?:news|headlines?)"
    r")\b",
    re.IGNORECASE,
)

# ASX ticker: 2-5 uppercase letters (or explicit mention)
_TICKER_IN_MESSAGE_RE = re.compile(
    r"\b(?:about|for|on|regarding|covering|re:?\s+)?([A-Z]{2,5})\b(?:\s+(?:news|stock|shares?|price|chart))?",
)

# Short follow-up messages (under 6 words, no ticker keyword)
_SHORT_FOLLOWUP_RE = re.compile(
    r"^\s*(?:\w+\s+){0,5}\w+\s*$",
)

_FOLLOWUP_WORDS_RE = re.compile(
    r"\b(?:why|how|what|when|explain|tell me more|elaborate|and|also|"
    r"what about|compared to|versus|vs)\b",
    re.IGNORECASE,
)

# Known words that look like tickers but are not
_TICKER_STOPWORDS = COMMON_TICKER_STOPWORDS | frozenset({
    "ASX", "ETF", "IPO", "CEO", "CFO", "COO", "CTO", "AGM", "EGM",
    "FY", "HY", "Q1", "Q2", "Q3", "Q4", "USA", "AUS", "GDP", "CPI",
    "RBA", "AUD", "USD", "EUR", "GBP", "JPY", "RAG", "LLM", "API",
    "THE", "AND", "FOR", "NOT", "BUT", "ARE", "WAS", "HAS", "HAD",
    "YES", "NO", "OK", "HI",
})


def classify_intent(
    message: str,
    *,
    active_ticker: str | None = None,
    conversation_history: list[dict] | None = None,
) -> QueryIntent:
    """Classify the user *message* into a QueryIntent.

    Parameters
    ----------
    message:
        The raw user message text.
    active_ticker:
        The currently active ticker in the cockpit session, if any.
    conversation_history:
        Recent conversation turns (role/content dicts), used to detect
        follow-up context.
    """
    text = str(message or "").strip()
    if not text:
        return QueryIntent.MARKET_WIDE

    continuity_kind = classify_continuity_turn(text)
    if continuity_kind == ContinuityTurnKind.PREVIOUS_TOOL_TRACE_QUESTION:
        return QueryIntent.PREVIOUS_TOOL_TRACE_QUESTION
    if continuity_kind == ContinuityTurnKind.CORRECTION_TURN:
        return QueryIntent.CORRECTION_TURN
    if continuity_kind == ContinuityTurnKind.THESIS_SAVE:
        return QueryIntent.THESIS_SAVE

    # 1. Command intent: starts with an imperative verb
    if _COMMAND_RE.match(text):
        return QueryIntent.COMMAND

    # 2. Explicit ticker mention in the message
    upper_words = {w.strip(".,!?;:'\"()[]") for w in text.split() if w.isupper() and 2 <= len(w.strip(".,!?;:'\"()[]")) <= 5}
    ticker_candidates = upper_words - _TICKER_STOPWORDS
    if ticker_candidates:
        return QueryIntent.TICKER_SPECIFIC

    # Check for "about BHP" style patterns
    m = _TICKER_IN_MESSAGE_RE.search(text)
    if m:
        candidate = m.group(1)
        if candidate not in _TICKER_STOPWORDS:
            return QueryIntent.TICKER_SPECIFIC

    # 3. Market-wide pattern
    if _MARKET_WIDE_RE.search(text):
        return QueryIntent.MARKET_WIDE

    # 4. Follow-up: short message in an active ticker thread
    if active_ticker and conversation_history:
        word_count = len(text.split())
        if word_count <= 8 and (_FOLLOWUP_WORDS_RE.search(text) or word_count <= 4):
            return QueryIntent.FOLLOWUP

    # 5. Default: if ticker is active and not explicitly market-wide, treat as follow-up
    if active_ticker:
        return QueryIntent.FOLLOWUP

    return QueryIntent.MARKET_WIDE
