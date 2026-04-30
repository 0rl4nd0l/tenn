from __future__ import annotations

import re

# Patterns ordered from most-specific to least-specific.
# Each entry: (regex, handler) where handler(match, msg) -> str
_RULES: list[tuple[re.Pattern[str], object]] = []


def _rule(pattern: str, flags: int = re.IGNORECASE):
    """Decorator: register a pattern rule that returns a command string."""

    def decorator(fn):
        _RULES.append((re.compile(pattern, flags), fn))
        return fn

    return decorator


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


@_rule(r"^([A-Za-z0-9]{1,10})\s+filestats?\b")
def _(m, _msg):
    return f"/filestats {m.group(1).upper()}"


@_rule(r"^([A-Za-z0-9]{1,10})\s+memory\s*$")
def _(m, _msg):
    return f"/memory show {m.group(1).upper()}"


@_rule(r"\bshow\s+memory\s+for\s+([A-Za-z0-9]{1,10})\b")
def _(m, _msg):
    return f"/memory show {m.group(1).upper()}"


@_rule(r"\bwhat\s+changed\b")
def _(_m, _msg):
    return "/changes"


# ---------------------------------------------------------------------------
# Holdings (cockpit-local portfolio state — see SYSTEM_CONTRACT §1.2).
# These rules MUST be registered before the generic
# ``\b(add|watch|track)\s+([A-Za-z]{2,5})\b`` watchlist rule below, so that
# "add BHP to holdings" is not eaten as "/watch add BHP".
# ---------------------------------------------------------------------------


@_rule(r"\b(?:show|list)\s+(?:my\s+)?hold(?:ings?|iongs?)\b")
def _(_m, _msg):
    return "/holdings list"


@_rule(r"\bwhat\s+(?:(?:am\s+i)|(?:are|r)\s+my)\s+hold(?:ings?|iongs?)\b")
def _(_m, _msg):
    return "/holdings list"


@_rule(r"\bwhat\s+(?:stocks?|stoicks?)\s+(?:am\s+i|are\s+we)\s+holding\b")
def _(_m, _msg):
    return "/holdings list"


@_rule(r"^\s*hold(?:ings?|iongs?)\s*$")
def _(_m, _msg):
    return "/holdings list"


@_rule(r"\badd\s+([A-Za-z]{2,5})\s+to\s+(?:my\s+)?hold(?:ings?|iongs?)\b")
def _(m, _msg):
    return f"/holdings add {m.group(1).upper()}"


@_rule(r"\bremove\s+([A-Za-z]{2,5})\s+from\s+(?:my\s+)?hold(?:ings?|iongs?)\b")
def _(m, _msg):
    return f"/holdings remove {m.group(1).upper()}"


@_rule(r"\barchive\s+([A-Za-z]{2,5})\s+hold(?:ings?|iongs?)\b")
def _(m, _msg):
    return f"/holdings archive {m.group(1).upper()}"


@_rule(r"\barchive\s+hold(?:ings?|iongs?)\s+([A-Za-z]{2,5})\b")
def _(m, _msg):
    return f"/holdings archive {m.group(1).upper()}"


@_rule(r"\bremove\s+([A-Za-z]{2,5})\s+from\s+watchlist\b")
def _(m, _msg):
    return f"/watch remove {m.group(1).upper()}"


@_rule(r"\bclear\s+watchlist\b")
def _(_m, _msg):
    return "/watch clear"


@_rule(r"\bsync\s+(my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch sync"


@_rule(r"\bscan\s+(my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch scan"


@_rule(r"\brun\s+watchlist\s+scan\b")
def _(_m, _msg):
    return "/watch scan"


@_rule(r"\bshow\s+(my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch list"


@_rule(r"\bwhat\s+is\s+in\s+(?:my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch list"


@_rule(r"\bwhat\s+stocks?\s+are\s+in\s+(?:my\s+)?watchlist\b")
def _(_m, _msg):
    return "/watch list"


@_rule(r"\b(add|watch|track)\s+([A-Za-z]{2,5})\b")
def _(m, _msg):
    # "add X to watchlist" or "watch X" or "track X"
    return f"/watch add {m.group(2).upper()}"


@_rule(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=[A-Za-z0-9_\-]{11}[^\s]*|youtu\.be/[A-Za-z0-9_\-]{11}[^\s]*)",
    flags=0,
)
def _(m, _msg):
    return f"/ingest {m.group(0)}"


@_rule(r"\b(show|list)\s+(pending\s+)?transcripts?\b")
def _(m, _msg):
    return "/review list"


@_rule(r"\bapprove\s+all\s+transcripts?\b")
def _(m, _msg):
    return "/review approve-all"


@_rule(r"\bwhat\s+(?:is|are)\s+my\s+(?:strategy|criteria|investment\s+criteria)\b")
def _(_m, _msg):
    return "/strategy list"


@_rule(
    r"\bwhat\s+(?:do\s+I\s+think|is\s+my\s+(?:decision|view|take))\s+(?:about|on)\s+([A-Za-z]{2,5})\b"
)
def _(m, _msg):
    return f"/strategy list {m.group(1).upper()}"


@_rule(r"\bset\s+(?:my\s+)?decision\s+on\s+([A-Za-z]{2,5})\s+to\s+(\w+)")
def _(m, _msg):
    return f"/strategy decide {m.group(1).upper()} {m.group(2).lower()}"


# ---------------------------------------------------------------------------
# Market update (P3 of cockpit verbal market updates v1).
# Specific run_type rules must come BEFORE the generic ``market update``
# catch-all so phrases like "noon market update" are tagged with the
# right run_type instead of dropping back to /market-update.
# ---------------------------------------------------------------------------


@_rule(r"\bnoon\s+(?:market\s+)?update\b")
def _(_m, _msg):
    return "/market-update noon"


@_rule(r"\bfinal\s+(?:market\s+)?update\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"\b(?:eod|end[- ]of[- ]day)\s+(?:market\s+)?update\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"\bmanual\s+(?:market\s+)?update\b")
def _(_m, _msg):
    return "/market-update manual"


@_rule(r"\bdaily\s+(?:market\s+)?update\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"\b(?:market\s+)?update\s+today\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"\btoday'?s\s+(?:market\s+)?update\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"\bwhat\s+happened\s+(?:on|in|with)\s+(?:the\s+)?market\s+today\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"\bwhat(?:'s|\s+is)\s+happening\s+(?:on|in)\s+(?:the\s+)?market\s+today\b")
def _(_m, _msg):
    return "/market-update final"


@_rule(r"^\s*(?:the\s+)?market\s+updat(?:e|er)\s*[?!.]*\s*$")
def _(_m, _msg):
    # Bare conversational requests should show the latest cached report quickly.
    # Explicit fresh-run phrases ("run", "daily", "today", "final") keep using
    # the run-type routes above/below.
    return "/market-update latest"


@_rule(r"\b(?:run\s+)?(?:a\s+|the\s+)?market\s+updat(?:e|er)\b")
def _(_m, _msg):
    # Explicit run phrasing should run a fresh final update.
    return "/market-update final"


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
