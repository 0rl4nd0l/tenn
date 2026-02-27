from __future__ import annotations

import re


_TICKER_STOPWORDS = {
    "A",
    "ALERT",
    "ALERTS",
    "AN",
    "AND",
    "ANY",
    "CHECK",
    "FOR",
    "IN",
    "IS",
    "LIST",
    "MY",
    "ON",
    "SHOW",
    "THE",
    "TO",
    "WHAT",
    "CHANGED",
    "CHANGE",
    "SINCE",
    "LAST",
    "WATCH",
    "WATCHLIST",
}


def _normalize_ticker(token: str | None) -> str | None:
    raw = str(token or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2,5}", raw):
        return None
    if raw in _TICKER_STOPWORDS:
        return None
    return raw


def _first_ticker_from_patterns(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue
        ticker = _normalize_ticker(m.group(1))
        if ticker:
            return ticker
    return None


def derive_conversational_command(message: str) -> str | None:
    text = str(message or "").strip()
    if not text or text.startswith("/"):
        return None

    lower = text.lower()
    lower_compact = re.sub(r"\s+", " ", lower).strip()

    if re.search(r"\b(access|permissions?)\b.*\b(status|state|have|current)\b", lower) or lower_compact in {
        "what access do you have",
        "what permissions do you have",
        "show access",
        "show permissions",
    }:
        return "/access"

    if re.search(r"\b(enable|turn on|allow|grant)\b.*\bweb\b", lower):
        return "/request-access web"
    if re.search(r"\b(disable|turn off|block)\b.*\bweb\b", lower):
        return "/web off"

    if re.search(r"\b(enable|turn on|allow|grant)\b.*\b(rag|qualitative context)\b", lower):
        return "/request-access rag"
    if re.search(r"\b(disable|turn off|block)\b.*\b(rag|qualitative context)\b", lower):
        return "/rag off"

    if re.search(r"\b(enable|turn on|allow|grant)\b.*\b(sql|dbdiag|diagnostic query|database diagnostics?)\b", lower):
        return "/request-access dbdiag"
    if re.search(r"\b(disable|turn off|block)\b.*\b(sql|dbdiag|diagnostic query|database diagnostics?)\b", lower):
        return "/dbdiag off"

    if "watchlist" in lower:
        if re.search(r"\b(sync|refresh|update)\b.*\bwatchlist\b", lower) or re.search(
            r"\bwatchlist\b.*\b(sync|refresh|update)\b",
            lower,
        ):
            return "/watch sync"
        if re.search(r"\b(clear|reset|empty)\b.*\bwatchlist\b", lower):
            return "/watch clear"
        if re.search(r"\b(show|list|what|which)\b.*\bwatchlist\b", lower) or lower in {"watchlist", "my watchlist"}:
            return "/watch list"

    remove_ticker = _first_ticker_from_patterns(
        text,
        [
            r"\bremove\s+([A-Za-z]{2,5})\s+from\s+(?:my\s+)?watchlist\b",
            r"\bunwatch\s+([A-Za-z]{2,5})\b",
            r"\bstop\s+watching\s+([A-Za-z]{2,5})\b",
        ],
    )
    if remove_ticker:
        return f"/watch remove {remove_ticker}"

    add_ticker = _first_ticker_from_patterns(
        text,
        [
            r"\badd\s+([A-Za-z]{2,5})\s+to\s+(?:my\s+)?watchlist\b",
            r"\bput\s+([A-Za-z]{2,5})\s+on\s+(?:my\s+)?watchlist\b",
            r"\b(?:watch|track|follow)\s+([A-Za-z]{2,5})\b",
        ],
    )
    if add_ticker and ("watch" in lower or "watchlist" in lower or "track" in lower or "follow" in lower):
        return f"/watch add {add_ticker}"

    if "alert" in lower:
        if re.search(r"\b(threshold|thresholds|settings|config)\b", lower):
            return "/alerts thresholds"
        alert_ticker = _first_ticker_from_patterns(
            text,
            [
                r"\balerts?\s+(?:for|on)\s+([A-Za-z]{2,5})\b",
                r"\bcheck\s+([A-Za-z]{2,5})\s+alerts?\b",
                r"\b([A-Za-z]{2,5})\s+alerts?\b",
            ],
        )
        if alert_ticker:
            return f"/alerts {alert_ticker}"
        return "/alerts"

    if "change" in lower:
        change_ticker = _first_ticker_from_patterns(
            text,
            [
                r"\bchanges?\s+(?:for|on)\s+([A-Za-z]{2,5})\b",
                r"\bwhat\s+changed\s+(?:for|on)\s+([A-Za-z]{2,5})\b",
                r"\b([A-Za-z]{2,5})\s+changes?\b",
            ],
        )
        if change_ticker:
            return f"/changes {change_ticker}"
        if re.search(r"\bwhat\s+changed\b", lower):
            return "/changes"

    return None
