from __future__ import annotations

import re
from pathlib import Path
from typing import Final

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REQUEST_STANDARDS_DIR = _REPO_ROOT / "docs" / "cockpit_request_standards"

# Single mapping surface for request-type -> standards doc.
REQUEST_STANDARD_REGISTRY: Final[dict[str, str]] = {
    "company_analysis": "company_analysis.md",
    "daily_market_update": "daily_market_update.md",
    "sector_analysis": "sector_analysis.md",
    "watchlist_triage": "watchlist_triage.md",
}

# Explicit aliasing keeps request-type routing deterministic and testable.
REQUEST_STANDARD_ALIASES: Final[dict[str, str]] = {
    "company_analysis": "company_analysis",
    "company-analysis": "company_analysis",
    "company": "company_analysis",
    "daily_market_update": "daily_market_update",
    "daily-market-update": "daily_market_update",
    "market_update_daily": "daily_market_update",
    "sector_analysis": "sector_analysis",
    "sector-analysis": "sector_analysis",
    "industry_analysis": "sector_analysis",
    "industry-analysis": "sector_analysis",
    "watchlist_triage": "watchlist_triage",
    "watchlist-triage": "watchlist_triage",
}

_DAILY_MARKET_UPDATE_RE = re.compile(
    r"(^\s*/market-update\s+final\b)"
    r"|(\bdaily\s+(?:market\s+)?update\b)"
    r"|(\b(?:market\s+)?update\s+today\b)"
    r"|(\btoday'?s\s+(?:market\s+)?update\b)"
    r"|(\b(?:market\s+)?wrap(?:\s+for\s+today|\s+today)?\b)"
    r"|(\b(?:biggest|major|top)\s+(?:market\s+)?movers?\b)",
    flags=re.IGNORECASE,
)
_COMPANY_ANALYSIS_RE = re.compile(
    r"(\b(?:full|deep|comprehensive)\s+(?:company\s+)?(?:analysis|review)\b)"
    r"|(\bcompany\s+deep\s+dive\b)"
    r"|(\binvestment\s+(?:thesis|view|case)\b)"
    r"|(\b(?:bull|bear)\s+case\b)",
    flags=re.IGNORECASE,
)
_SECTOR_ANALYSIS_RE = re.compile(
    r"(\b(?:sector|industry)\s+analysis\b)"
    r"|(\banaly[sz]e\s+(?:the\s+)?(?:sector|industry)\b)"
    r"|(\b(?:tell\s+me\s+about|overview\s+of|explain|research)\s+"
    r"(?:the\s+)?[a-z][a-z0-9&\-/ ]{1,80}\s+(?:sector|industry)\b)",
    flags=re.IGNORECASE,
)
_WATCHLIST_TRIAGE_RE = re.compile(
    r"(^\s*/watch\s+scan\b)"
    r"|(\bwatchlist\s+triage\b)"
    r"|(\btriage\s+(?:the\s+)?watchlist\b)"
    r"|(\bscan\s+(?:my\s+)?watchlist\b)",
    flags=re.IGNORECASE,
)

_PROMPT_GUIDANCE_LINES: Final[dict[str, tuple[str, ...]]] = {
    "company_analysis": (
        "Keep confirmed financial truth separate from narrative/context interpretation.",
        "Use this output order: Verdict, Evidence, Risks, Counterpoints, Unknowns.",
        "In Evidence, cover financial truth first, then context, then peer comparison when available.",
        "Include a strategy-context confer check when strategy criteria are present.",
        "Run a bounded skeptic pass: include strongest disconfirming evidence.",
        "For missing data, explicitly list unknowns and do not infer absent numeric facts.",
        "Thesis-memory ideas must be optional and confirmation-gated.",
    ),
    "daily_market_update": (
        "Treat this as a market-wide update with transparent breadth and coverage.",
        "Lead with market-level summary, then highest-signal movers, then key macro/sector drivers.",
        "Separate confirmed market facts from interpretation, and timestamp any time-sensitive claims.",
        "If watchlist context is available, include a clearly labeled watchlist impact subsection.",
        "List notable unknowns (missing breadth, stale feeds, absent sectors) before concluding.",
    ),
    "sector_analysis": (
        "Anchor the analysis to one explicit sector/industry scope before presenting conclusions.",
        "Present current facts first, then structural drivers, then relative winners/laggards with evidence.",
        "Separate sector-wide claims from company-specific claims and label each section accordingly.",
        "State what evidence is unavailable (coverage gaps, missing peers, stale data) and avoid inferring missing values.",
        "Conclude with scenario-aware risks and counterpoints, not a single-path narrative.",
    ),
    "watchlist_triage": (
        "Treat this as prioritization, not full thesis output.",
        "Rank watchlist items by urgency/importance using only currently grounded evidence.",
        "For each ticker, provide a short rationale, key trigger, and immediate next action.",
        "Clearly separate confirmed triggers from speculative watch items.",
        "If evidence is insufficient for ranking, flag the ticker as unknown rather than forcing an order.",
    ),
}


def normalize_request_standard_type(request_type: str | None) -> str | None:
    raw = str(request_type or "").strip().lower()
    if not raw:
        return None
    key = re.sub(r"[\s-]+", "_", raw)
    alias = REQUEST_STANDARD_ALIASES.get(key, key)
    if alias not in REQUEST_STANDARD_REGISTRY:
        return None
    return alias


def get_request_standard_path(request_type: str | None) -> Path | None:
    key = normalize_request_standard_type(request_type)
    if key is None:
        return None
    filename = REQUEST_STANDARD_REGISTRY.get(key)
    if not filename:
        return None
    return _REQUEST_STANDARDS_DIR / filename


def select_request_standard_type(
    *,
    message: str,
    mode: str,
    ticker: str | None,
) -> str | None:
    text = str(message or "").strip()
    mode_key = str(mode or "").strip().lower()

    if mode_key == "deep_analysis" and ticker:
        return "company_analysis"
    if ticker and _COMPANY_ANALYSIS_RE.search(text):
        return "company_analysis"
    if _WATCHLIST_TRIAGE_RE.search(text):
        return "watchlist_triage"
    if _DAILY_MARKET_UPDATE_RE.search(text):
        return "daily_market_update"
    if _SECTOR_ANALYSIS_RE.search(text):
        return "sector_analysis"
    return None


def request_standard_prompt_guidance(request_type: str | None) -> str:
    normalized = normalize_request_standard_type(request_type)
    if normalized is None:
        return ""
    standard_path = get_request_standard_path(normalized)
    reference = (
        f"docs/cockpit_request_standards/{REQUEST_STANDARD_REGISTRY[normalized]}"
        if standard_path is None
        else str(standard_path.relative_to(_REPO_ROOT))
    )
    lines = _PROMPT_GUIDANCE_LINES.get(normalized, ())
    header = f"Request standard is active for this response [{normalized}] ({reference}).\n"
    if not lines:
        return header
    bullets = "".join(f"- {line}\n" for line in lines)
    return header + bullets


def build_request_standard_prompt_guidance(
    *,
    message: str,
    mode: str,
    ticker: str | None,
) -> str:
    request_type = select_request_standard_type(
        message=message,
        mode=mode,
        ticker=ticker,
    )
    return request_standard_prompt_guidance(request_type)


def company_analysis_prompt_guidance() -> str:
    # Backward-compat wrapper for the initial v1 hook.
    return request_standard_prompt_guidance("company_analysis")
