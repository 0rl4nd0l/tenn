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

from shared.ticker_inference import COMMON_TICKER_STOPWORDS

__all__ = ["CommandRoute", "route_command"]


@dataclass
class CommandRoute:
    """A pre-parsed command that can skip or shortcut the agent loop."""
    matched: bool
    action_type: str | None = None   # "action_proposal", "direct_tool", None
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    explanation: str | None = None


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_INGEST_RE = re.compile(
    r"^\s*(?:"
    r"ingest\s+(?:news\s+(?:for\s+)?)?([A-Z]{2,5})\s+news\b|"
    r"ingest\s+news\s+(?:for\s+)?([A-Z]{2,5})\b|"
    r"fetch\s+(?:news\s+(?:for\s+)?)?([A-Z]{2,5})\b|"
    r"fetch\s+([A-Z]{2,5})\s+news\b"
    r")",
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
_ANALYSIS_RE = re.compile(
    r"""
    ^\s*(?:
        (?:
            (?:run\s+)?
            (?:full\s+)?
            (?:company\s+)?
            (?:analysis|analyse|analyze|research)
            (?:\s+(?:on|for|of))?
            \s+([A-Za-z]{2,5})
        )
        |
        (?:
            ([A-Za-z]{2,5})
            \s+(?:analysis|analyse|analyze|research)
        )
    )\s*[?!.]*\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_CHART_RE = re.compile(
    r"^\s*(?:chart|show\s+chart|candlestick)\s+([A-Z]{2,5})\b|"
    r"^\s*([A-Z]{2,5})\s+chart\s*$",
    re.IGNORECASE,
)
_RSI_RE = re.compile(
    r"^\s*(?:rsi\s+(?:for\s+)?([A-Z]{2,5})|([A-Z]{2,5})\s+rsi)\s*[?!.]*\s*$",
    re.IGNORECASE,
)
_SCREENER_RE = re.compile(
    r"^\s*(?:run\s+)?(?:tv\s+|tradingview\s+)?screener\s*(?:for\s+([A-Za-z]{2,8}))?\s*[?!.]*\s*$",
    re.IGNORECASE,
)
_TRADINGVIEW_TOOL_RE = re.compile(
    r"""
    ^\s*
    (?:
        (?:use|run|open|invoke)\s+
        (?:the\s+)?
        (?:tv|trading\s*view|tradingview|tradin\s*view|tradinview)
        (?:\s+(?:tool|screener))?
      |
        (?:tv|trading\s*view|tradingview|tradin\s*view|tradinview)
        \s+(?:tool|screener)
    )
    \s*[?!.]*\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_MARKET_MOVERS_RE = re.compile(
    r"""
    \b(?:
        market\s+movers?
      | biggest\s+(?:stock\s+)?movers?
      | top\s+(?:asx\s+|stock\s+)?(?:gainers|losers|movers?)
      | stocks?\s+(?:with\s+)?(?:the\s+)?(?:biggest|largest)\s+(?:price\s+)?moves?
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
_BACKFILL_RE = re.compile(
    r"^\s*(?:backfill|run\s+backfill)\s+([A-Z]{2,5})\b",
    re.IGNORECASE,
)
_SOURCE_GATHER_RE = re.compile(
    r"""
    ^\s*
    (?:(?:ok(?:ay)?|yes|yep|sure|please|go\s+ahead|alright|all\s+right)[,.\s]+)?
    (?:
        (?:(?:gather|collect|fetch|pull|get)\s+(?:the\s+)?)
        (?:sources?|evidence|documents?|announcements?|filings?)
      |
        (?:sources?|evidence|documents?|announcements?|filings?)\s+please
    )
    \s*[?!.]*\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_CHECK_CHANNEL_RECENT_RES = (
    re.compile(
        r"""
        ^\s*
        (?:
            check|show|list
        )
        \s+
        (?:recent\s+)?
        (?:youtube\s+)?
        (?:videos?\s+from\s+|channel\s+)
        (.+?)
        (?:\s+for\s+recent\s+videos?)?
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
    re.compile(
        r"""
        ^\s*
        check\s+
        (?:youtube\s+)?
        (.+?)
        \s+for\s+recent\s+videos?
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
)
_BARE_YOUTUBE_CHANNEL_QUERY_RE = re.compile(
    r"""
    ^\s*
    (?!what\b|how\b|why\b|when\b|where\b)
    (.+?)
    \s+
    youtube
    (?:\s+(?:videos?|channel))?
    \s*[?!.]*\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_YOUTUBE_CONTEXT_ACCESS_RE = re.compile(
    r"""
    ^\s*
    (?:
        (?:yes\s+)?
        (?:
            access|open|show|list|get|fetch
        )
        \s+
        (?:
            them|those|the\s+(?:videos?|links?)
        )
      |
        can\s+(?:u|you|we)\s+ingest(?:\s+(?:them|those|these|videos?))?
    )
    \s*[?!.]*\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_WATCH_CHANNEL_RE = re.compile(
    r"""
    ^\s*
    (?:
        watch\s+(?:youtube\s+(?:videos?\s+from\s+|channel\s+|)|videos?\s+from\s+|channel\s+)
      | monitor\s+(?:youtube\s+(?:channel\s+|)|channel\s+)
      | add\s+(?:youtube\s+)?channel\s+
      | subscribe\s+to\s+
      | follow\s+(?:youtube\s+(?:channel\s+|)|channel\s+)
    )
    (.+)$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TICKER_STOPWORDS = COMMON_TICKER_STOPWORDS | frozenset({
    "ASX", "ETF", "IPO", "CEO", "AGM", "EGM", "FY", "HY",
    "USA", "AUS", "GDP", "CPI", "RBA", "AUD", "USD",
    "CLOUD", "LOCAL", "ADVISOR", "OPS",
    "SHOW",
})


def route_command(
    message: str,
    *,
    active_ticker: str | None = None,
    recent_youtube_channel: str | None = None,
    recent_youtube_videos: list[dict[str, Any]] | None = None,
) -> CommandRoute:
    """Attempt to match *message* as a direct command.

    Returns a ``CommandRoute`` with ``matched=True`` if the message
    is a recognized imperative command, along with the pre-built
    action proposal payload. Returns ``matched=False`` otherwise.
    """
    text = str(message or "").strip()

    active = str(active_ticker or "").strip().upper()
    if active and active not in _TICKER_STOPWORDS and _SOURCE_GATHER_RE.match(text):
        return CommandRoute(
            matched=True,
            action_type="action_proposal",
            tool="run_backfill",
            arguments={"ticker": active, "years": 2},
            explanation=(
                f"Gather source documents for {active} by backfilling ASX "
                "announcements for 2 years."
            ),
        )

    youtube_selection_text, youtube_selection_weight = _strip_youtube_selection_weight(text)
    if recent_youtube_videos and recent_youtube_channel:
        if _YOUTUBE_CONTEXT_ACCESS_RE.match(youtube_selection_text):
            limit = min(max(len(recent_youtube_videos), 8), 20)
            return CommandRoute(
                matched=True,
                action_type="direct_tool",
                tool="check_youtube_channel_recent_videos",
                arguments={"channel_name": recent_youtube_channel, "limit": limit},
                explanation=(
                    "Show the recent YouTube video links again before selecting "
                    "transcripts to ingest."
                ),
            )

    youtube_selection = _parse_youtube_video_selection(
        youtube_selection_text,
        max_index=len(recent_youtube_videos or []),
    )
    if youtube_selection is None and recent_youtube_videos:
        youtube_selection = _parse_youtube_contextual_numbered_selection(
            youtube_selection_text,
            max_index=len(recent_youtube_videos),
        )
    if youtube_selection is None and recent_youtube_videos:
        youtube_selection = _parse_youtube_contextual_first_selection(
            youtube_selection_text
        )
    if youtube_selection is not None and recent_youtube_videos:
        if not youtube_selection:
            return CommandRoute(
                matched=True,
                action_type=None,
                explanation=(
                    f"I only have {len(recent_youtube_videos)} recent YouTube "
                    "video option(s) in context. Pick a listed number or say "
                    '"ingest all".'
                ),
            )
        selected: list[dict[str, Any]] = []
        urls: list[str] = []
        for index in youtube_selection:
            row = recent_youtube_videos[index - 1]
            if not isinstance(row, dict):
                continue
            url = str(row.get("webpage_url") or row.get("url") or "").strip()
            if not url:
                continue
            selected.append(row)
            urls.append(url)
        if not urls:
            return CommandRoute(
                matched=True,
                action_type=None,
                explanation=(
                    "I found the selected YouTube video number(s), but no video "
                    "URL was preserved. Ask me to list the channel's recent videos "
                    "again, then choose from that list."
                ),
            )
        arguments: dict[str, Any] = {
            "urls": urls,
            "selected_videos": selected,
            "takeaway_limit": 5,
        }
        if youtube_selection_weight is not None:
            arguments["credibility_weight"] = youtube_selection_weight

        return CommandRoute(
            matched=True,
            action_type="direct_tool",
            tool="ingest_youtube_videos",
            arguments=arguments,
            explanation=(
                f"Stage {len(urls)} selected YouTube transcript"
                f"{'' if len(urls) == 1 else 's'} for review."
            ),
        )

    # ingest [ticker] news
    m = _INGEST_RE.match(text)
    if m:
        ticker = next((g for g in m.groups() if g), "").upper()
        if ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="action_proposal",
                tool="run_news_ingest",
                arguments={"since_hours": 24, "tickers": ticker},
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

    # analyse/analyze [ticker] should run the backend analysis pipeline.
    m = _ANALYSIS_RE.match(text)
    if m:
        ticker = (m.group(1) or m.group(2) or "").upper()
        if ticker and ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="direct_tool",
                tool="run_analysis",
                arguments={"ticker": ticker},
                explanation=f"Run full analysis pipeline for {ticker}.",
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

    # RSI [ticker] / [ticker] RSI
    m = _RSI_RE.match(text)
    if m:
        ticker = (m.group(1) or m.group(2) or "").upper()
        if ticker and ticker not in _TICKER_STOPWORDS:
            return CommandRoute(
                matched=True,
                action_type="direct_tool",
                tool="get_tv_indicators",
                arguments={"ticker": ticker, "indicators": ["RSI"]},
                explanation=f"Fetch RSI for {ticker}.",
            )

    # TradingView screener
    m = _SCREENER_RE.match(text)
    if m:
        market = (m.group(1) or "australia").strip().lower()
        return CommandRoute(
            matched=True,
            action_type="direct_tool",
            tool="tv_screener",
            arguments={"market": market, "limit": 20, "filters": {}},
            explanation=f"Run TradingView screener for {market}.",
        )

    if _TRADINGVIEW_TOOL_RE.match(text):
        return CommandRoute(
            matched=True,
            action_type="direct_tool",
            tool="tv_screener",
            arguments={"market": "australia", "limit": 20, "filters": {}},
            explanation="Run TradingView screener for australia.",
        )

    # Market movers: use backend-owned TradingView screener data instead of
    # stale broad news articles. Fetch both gainers and decliners.
    if _MARKET_MOVERS_RE.search(text):
        return CommandRoute(
            matched=True,
            action_type="direct_tool",
            tool="tv_screener",
            arguments={
                "market": "australia",
                "limit": 20,
                "filters": {},
                "mode": "market_movers",
                "sort_by": "change",
            },
            explanation="Fetch ASX market movers from TradingView.",
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

    # check/show/list recent YouTube videos from a channel
    for pattern in _CHECK_CHANNEL_RECENT_RES:
        m = pattern.match(text)
        if m:
            channel_name = m.group(1).strip()
            if channel_name:
                return CommandRoute(
                    matched=True,
                    action_type="direct_tool",
                    tool="check_youtube_channel_recent_videos",
                    arguments={"channel_name": channel_name, "limit": 8},
                    explanation=f"Check recent YouTube videos from {channel_name!r}.",
                )

    m = _BARE_YOUTUBE_CHANNEL_QUERY_RE.match(text)
    if m:
        channel_name = m.group(1).strip()
        if channel_name:
            return CommandRoute(
                matched=True,
                action_type="direct_tool",
                tool="check_youtube_channel_recent_videos",
                arguments={"channel_name": channel_name, "limit": 8},
                explanation=f"Check recent YouTube videos from {channel_name!r}.",
            )

    if re.fullmatch(
        r"(?:most\s+recent|latest|recent)\s+(?:youtube\s+)?videos?\s*\??",
        text,
        re.IGNORECASE,
    ):
        channel_name = str(recent_youtube_channel or "").strip()
        if channel_name:
            return CommandRoute(
                matched=True,
                action_type="direct_tool",
                tool="check_youtube_channel_recent_videos",
                arguments={"channel_name": channel_name, "limit": 8},
                explanation=f"Check recent YouTube videos from {channel_name!r}.",
            )
        return CommandRoute(
            matched=True,
            action_type=None,
            explanation=(
                "Which YouTube channel should I check? "
                'For example: "check youtube channel Kneppy Invests".'
            ),
        )

    # watch/monitor/add/subscribe/follow youtube channel
    m = _WATCH_CHANNEL_RE.match(text)
    if m:
        channel_name = m.group(1).strip()
        if channel_name:
            return CommandRoute(
                matched=True,
                action_type="direct_tool",
                tool="watch_youtube_channel",
                arguments={"channel_name": channel_name},
                explanation=f"Add YouTube channel {channel_name!r} to the watch list.",
            )

    return CommandRoute(matched=False)


_YOUTUBE_SELECTION_TOKEN_RE = re.compile(
    r"\#?\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|last",
    re.IGNORECASE,
)
_YOUTUBE_SELECTION_RE = re.compile(
    r"""
    ^\s*
    (?:
        (?:(?:ingest|stage|select|use)\s+)?
        (?:(?:the\s+)?(?:video|videos|transcript|transcripts)\s+)?
    )
    (?P<selection>
        all
        |
        (?:
            \#?\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|last
        )
        (?:
            \s*(?:,|and)\s*
            (?:
                \#?\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|last
            )
        )*
    )
    \s*
    (?:(?:video|videos|transcript|transcripts)\s*)?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)
_YOUTUBE_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
}
_YOUTUBE_SELECTION_WEIGHT_RE = re.compile(
    r"""
    \s+
    (?:
        (?:(?:with|at)\s+)?
        (?:credibility(?:_|\s+)?weight|weight|credibility)
        \s*=?\s*
        |
        at\s+
    )
    (?P<weight>-?(?:\d+(?:\.\d+)?|\.\d+))
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_YOUTUBE_CONTEXTUAL_FIRST_SELECTION_RE = re.compile(
    r"""
    ^\s*
    (?:yes\s+)?
    (?:
        (?:
            ingest|stage|select|use|access|fetch|get
        )
        \s+
        (?:the\s+)?
    )?
    (?:
        (?:(?:most\s+recent|latest|recent)\s+(?:youtube\s+)?)?
        (?:
            videos? | transcripts?
        )
        |
        (?:(?:most\s+recent|latest|recent)\s+(?:youtube\s+)?videos?)
    )
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_YOUTUBE_CONTEXTUAL_NUMBERED_SELECTION_RE = re.compile(
    r"""
    \b
    (?:
        takeaways?|summary|summari[sz]e|process|ingest|stage|select|use|access|fetch|get
    )
    \b
    .{0,80}?
    \b
    (?:
        videos?|transcripts?
    )
    \s+
    (?P<selection>
        \#?\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|last
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)
_YOUTUBE_PROCESS_REFERENT_RE = re.compile(
    r"""
    ^\s*
    (?:yes\s+)?
    (?:
        process|ingest|stage|select|use
    )
    \s+
    (?:it|that)
    \s*[?!.]*\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _strip_youtube_selection_weight(text: str) -> tuple[str, float | None]:
    cleaned = str(text or "").strip()
    match = _YOUTUBE_SELECTION_WEIGHT_RE.search(cleaned)
    if not match:
        return cleaned, None
    try:
        weight = float(match.group("weight"))
    except (TypeError, ValueError):
        return cleaned, None
    return cleaned[: match.start()].strip(), weight


def _parse_youtube_contextual_first_selection(text: str) -> list[int] | None:
    cleaned = str(text or "").strip()
    if _YOUTUBE_PROCESS_REFERENT_RE.match(cleaned):
        return [1]
    if not _YOUTUBE_CONTEXTUAL_FIRST_SELECTION_RE.match(cleaned):
        return None
    lowered = cleaned.lower()
    has_action = bool(
        re.search(r"\b(?:ingest|stage|select|use|access|fetch|get)\b", lowered)
    )
    has_confirmation = lowered.startswith("yes ")
    has_transcript = bool(re.search(r"\btranscripts?\b", lowered))
    has_recency = bool(re.search(r"\b(?:most\s+recent|latest|recent)\b", lowered))
    if has_action or has_confirmation or has_transcript:
        return [1]
    if has_recency:
        return None
    return None


def _youtube_selection_token_to_index(token: str, *, max_index: int) -> int | None:
    cleaned = str(token or "").lower().lstrip("#")
    if cleaned == "last":
        return max_index
    if cleaned in _YOUTUBE_ORDINALS:
        return _YOUTUBE_ORDINALS[cleaned]
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_youtube_contextual_numbered_selection(
    text: str,
    *,
    max_index: int,
) -> list[int] | None:
    if max_index <= 0:
        return None
    match = _YOUTUBE_CONTEXTUAL_NUMBERED_SELECTION_RE.search(str(text or "").strip())
    if not match:
        return None
    index = _youtube_selection_token_to_index(match.group("selection"), max_index=max_index)
    if index is None:
        return None
    if index < 1 or index > max_index:
        return []
    return [index]


def _parse_youtube_video_selection(text: str, *, max_index: int) -> list[int] | None:
    if max_index <= 0:
        return None
    match = _YOUTUBE_SELECTION_RE.match(str(text or "").strip())
    if not match:
        return None
    selection = str(match.group("selection") or "").strip().lower()
    if selection == "all":
        return list(range(1, max_index + 1))

    indexes: list[int] = []
    for token_match in _YOUTUBE_SELECTION_TOKEN_RE.finditer(selection):
        index = _youtube_selection_token_to_index(
            token_match.group(0),
            max_index=max_index,
        )
        if index is None:
            continue
        if index < 1 or index > max_index:
            return []
        if index not in indexes:
            indexes.append(index)
    return indexes
