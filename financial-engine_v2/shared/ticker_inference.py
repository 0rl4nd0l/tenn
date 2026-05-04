from __future__ import annotations

import re
from typing import Iterable

EXPLICIT_TICKER_RE = re.compile(
    r"(?:\bASX:|\$)([A-Za-z]{2,5})\b|([A-Za-z0-9]{2,5})\.AX\b",
    re.IGNORECASE,
)
TICKER_TOKEN_RE = re.compile(
    r"\b(?:[A-Za-z][A-Za-z0-9]{1,4}|[0-9]+[A-Za-z][A-Za-z0-9]{0,3})\b"
)
WHOLE_MESSAGE_TICKER_RE = re.compile(
    r"^\s*([A-Za-z0-9]{2,5})(?:\s+(?:1m|5m|15m|30m|1h|4h|1d|1w|1M|news|announcements?|price|chart|financials?))?\s*$",
    re.IGNORECASE,
)
DEFAULT_TICKER_CUE_PATTERNS = (
    r"\b(?:about|on|for|vs|versus|compare|chart|price|financials?|announcements?|news|"
    r"analyse|analyze|analysis|ticker|stock|company|research|show|plot|candlestick|candle|"
    r"report|results?|strategy|thesis|risk|catalysts?|document|history|was)\s+{token}\b",
    r"\b(?:what(?:'s| is)?\s+happened|what\s+happened|what(?:'s| is)?\s+going\s+on|"
    r"what(?:'s| is)?\s+new|latest\s+on|recent\s+update|update\s+me\s+on)\s+(?:with\s+)?{token}\b",
    r"\bwhat\s+does\s+{token}\s+do\b",
    r"\b(?:what|who)\s+is\s+{token}\b",
    r"\bprice\s+history\s+{token}\b",
    r"\b{token}\s+(?:vs|versus|chart|price|financials?|announcements?|news|on|between|"
    r"close|closing|summary|performance|results?|strategy|thesis)\b",
)
COMMON_TICKER_STOPWORDS = frozenset(
    {
        "A",
        "AN",
        "AND",
        "ARE",
        "ASX",
        "ABOUT",
        "BUY",
        "CASE",
        "CASH",
        "COMPARE",
        "ACTION",
        "ACTIONS",
        "DEBT",
        "DATA",
        "DOES",
        "EBIT",
        "FAIL",
        "FINANCIAL",
        "FOR",
        "FROM",
        "GET",
        "GIVE",
        "GOING",
        "GROWTH",
        "HALF",
        "HOW",
        "IDEA",
        "IMPLY",
        "IN",
        "INTO",
        "IRON",
        "IS",
        "LAST",
        "MARKET",
        "ME",
        "MEAN",
        "NET",
        "NEWS",
        "NEXT",
        "NOTE",
        "NOTES",
        "NOW",
        "ONE",
        "OKAY",
        "ON",
        "ORE",
        "OUTLOOK",
        "PRICE",
        "PROFIT",
        "RATE",
        "RATES",
        "REVENUE",
        "RISK",
        "RISKS",
        "SAY",
        "SECTOR",
        "SHARE",
        "SHOULD",
        "SHOW",
        "SOURCE",
        "SOURCES",
        "STOCK",
        "SUMMARISE",
        "SUMMARIZE",
        "SUMMARY",
        "SURE",
        "TELL",
        "THAT",
        "THE",
        "THEIR",
        "THEM",
        "THESE",
        "THEY",
        "THIS",
        "THESIS",
        "THOSE",
        "TRY",
        "IT",
        "ITS",
        "WAS",
        "WHAT",
        "WHO",
        "WHY",
        "WITH",
    }
)


def extract_alpha_tokens(message: str) -> list[tuple[str, str]]:
    return [
        (match.group(0), match.group(0).upper())
        for match in TICKER_TOKEN_RE.finditer(str(message or ""))
    ]


def is_valid_ticker_token(
    token: str,
    *,
    stopwords: Iterable[str] | None = None,
) -> bool:
    cleaned = str(token or "").strip().upper()
    if not cleaned:
        return False
    if cleaned in _normalized_stopwords(stopwords):
        return False
    if not any(char.isalpha() for char in cleaned):
        return False
    return 2 <= len(cleaned) <= 5


def detect_tickers(
    message: str,
    *,
    stopwords: Iterable[str] | None = None,
    cue_patterns: Iterable[str] = DEFAULT_TICKER_CUE_PATTERNS,
) -> list[str]:
    text = str(message or "")
    explicit = EXPLICIT_TICKER_RE.search(text)
    if explicit:
        token = (explicit.group(1) or explicit.group(2) or "").upper()
        if is_valid_ticker_token(token, stopwords=stopwords):
            return [token]

    tokens = extract_alpha_tokens(text)
    uppercase_candidates = _unique_tickers(
        upper
        for original, upper in tokens
        if original.isupper() and is_valid_ticker_token(upper, stopwords=stopwords)
    )
    if uppercase_candidates:
        return uppercase_candidates

    whole_message = WHOLE_MESSAGE_TICKER_RE.fullmatch(text.strip())
    if whole_message:
        token = whole_message.group(1).upper()
        if is_valid_ticker_token(token, stopwords=stopwords):
            return [token]

    return _unique_tickers(
        upper
        for original, upper in tokens
        if is_valid_ticker_token(upper, stopwords=stopwords)
        and any(
            re.search(pattern.format(token=re.escape(original)), text, re.IGNORECASE)
            for pattern in cue_patterns
        )
    )


def detect_primary_ticker(
    message: str,
    *,
    stopwords: Iterable[str] | None = None,
    cue_patterns: Iterable[str] = DEFAULT_TICKER_CUE_PATTERNS,
) -> str | None:
    tickers = detect_tickers(
        message,
        stopwords=stopwords,
        cue_patterns=cue_patterns,
    )
    return tickers[0] if tickers else None


def detect_unique_ticker(
    message: str,
    *,
    stopwords: Iterable[str] | None = None,
    cue_patterns: Iterable[str] = DEFAULT_TICKER_CUE_PATTERNS,
) -> str | None:
    tickers = detect_tickers(
        message,
        stopwords=stopwords,
        cue_patterns=cue_patterns,
    )
    return tickers[0] if len(tickers) == 1 else None


def _normalized_stopwords(stopwords: Iterable[str] | None) -> set[str]:
    normalized = set(COMMON_TICKER_STOPWORDS)
    if stopwords is not None:
        normalized.update(
            str(word or "").strip().upper() for word in stopwords if str(word or "").strip()
        )
    return normalized


def _unique_tickers(tokens: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for token in tokens:
        if token not in unique:
            unique.append(token)
    return unique
