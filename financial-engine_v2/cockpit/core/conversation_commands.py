from __future__ import annotations

import re

# Ticker pattern: 2-5 uppercase letters (ASX-style)
_TICKER_RE = re.compile(r"\b([A-Z]{2,5})\b")

# Patterns ordered from most-specific to least-specific.
# Each entry: (regex, handler) where handler(match, msg) -> str
_RULES: list[tuple[re.Pattern[str], object]] = []


def _rule(pattern: str, flags: int = re.IGNORECASE):
    """Decorator: register a pattern rule that returns a command string."""
    def decorator(fn):
        _RULES.append((re.compile(pattern, flags), fn))
        return fn
    return decorator


def _extract_ticker(text: str) -> str | None:
    """Extract an all-caps 2-5 char token from text (first match)."""
    m = _TICKER_RE.search(text.upper())
    return m.group(1) if m else None


@_rule(r"\b(enable|turn\s+on)\s+sql\s+diagn")
def _(_m, _msg):
    return "/request-access dbdiag"


@_rule(r"\b(disable|turn\s+off)\s+dbdiag\b")
def _(_m, _msg):
    return "/dbdiag off"


@_rule(r"\benable\s+web\s+access\b")
def _(_m, _msg):
    return "/request-access web"


@_rule(r"\bdisable\s+web\s+access\b")
def _(_m, _msg):
    return "/web off"


@_rule(r"\bturn\s+on\s+rag\b")
def _(_m, _msg):
    return "/request-access rag"


@_rule(r"\bturn\s+off\s+rag\b")
def _(_m, _msg):
    return "/rag off"


@_rule(r"\bwhat\s+access\b")
def _(_m, _msg):
    return "/access"


@_rule(r"\bshow\s+alert\s+thresholds?\b")
def _(_m, _msg):
    return "/alerts thresholds"


@_rule(r"\bcheck\s+alerts?\s+for\s+([A-Za-z]+)\b")
def _(m, _msg):
    return f"/alerts {m.group(1).upper()}"


@_rule(r"\bcheck\s+alerts?\b")
def _(_m, _msg):
    return "/alerts"


@_rule(r"^([A-Za-z]{2,5})\s+alerts?\b")
def _(m, _msg):
    return f"/alerts {m.group(1).upper()}"


@_rule(r"\bwhat\s+changed\s+for\s+([A-Za-z]+)\b")
def _(m, _msg):
    return f"/changes {m.group(1).upper()}"


@_rule(r"^([A-Za-z]{2,5})\s+changes?\b")
def _(m, _msg):
    return f"/changes {m.group(1).upper()}"


@_rule(r"\bwhat\s+changed\b")
def _(_m, _msg):
    return "/changes"


@_rule(r"\bremove\s+([A-Za-z]{2,5})\s+from\s+watchlist\b")
def _(m, _msg):
    return f"/watch remove {m.group(1).upper()}"


@_rule(r"\bclear\s+watchlist\b")
def _(_m, _msg):
    return "/watch clear"


@_rule(r"\bsync\s+(my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch sync"


@_rule(r"\bshow\s+(my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch list"


@_rule(r"\b(add|watch|track)\s+([A-Za-z]{2,5})\b")
def _(m, _msg):
    # "add X to watchlist" or "watch X" or "track X"
    return f"/watch add {m.group(2).upper()}"


@_rule(r"\b(show|list)\s+(pending\s+)?transcripts?\b")
def _(m, _msg):
    return "/review list"


@_rule(r"\bapprove\s+all\s+transcripts?\b")
def _(m, _msg):
    return "/review approve-all"


def derive_conversational_command(message: str) -> str | None:
    """
    Map a natural-language message to a cockpit slash command.

    Returns None if the message is not a conversational control phrase,
    or if it is already a slash command (starts with '/').
    """
    if message.startswith("/"):
        return None
    for pattern, handler in _RULES:
        m = pattern.search(message)
        if m:
            result = handler(m, message)
            return result
    return None
