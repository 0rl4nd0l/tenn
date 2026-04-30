from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

from app.services.company_memory import CompanyMemoryStore
from app.services.memory_assembler import MemoryAssembler
from app.services.market_memory import MarketMemoryStore
from app.services.market_sector_inference import infer_sector
from shared.ticker_inference import COMMON_TICKER_STOPWORDS, detect_tickers


QueryIntent = str
SourceName = str

_FINANCIAL_KEYWORDS = (
    "revenue",
    "ebit",
    "ebitda",
    "npat",
    "profit",
    "earnings",
    "cash flow",
    "cashflow",
    "net debt",
    "debt",
    "margin",
    "capex",
    "dividend",
    "balance sheet",
    "financial",
)
_INTERPRETATION_KEYWORDS = (
    "what does",
    "what do",
    "imply",
    "mean",
    "quality",
    "sustainable",
    "strong",
    "weak",
    "interpret",
)
_STRATEGY_KEYWORDS = (
    "strategy",
    "thesis",
    "investment case",
    "why own",
    "should i buy",
    "should we buy",
    "positioning",
)
_RISK_CATALYST_KEYWORDS = (
    "risk",
    "risks",
    "catalyst",
    "catalysts",
    "upside",
    "downside",
)
_MARKET_KEYWORDS = (
    "market",
    "sector",
    "industry",
    "macro",
    "commodity",
    "iron ore",
    "lithium",
    "rates",
    "inflation",
)
_TICKER_STOPWORDS = COMMON_TICKER_STOPWORDS
_QUERY_BUDGETS = {
    "financial_fact": {
        "financial_periods": 2,
        "company_items": 0,
        "sector_items": 0,
        "macro_items": 0,
        "user_thesis_items": 0,
    },
    "strategy": {
        "financial_periods": 0,
        "company_items": 4,
        "sector_items": 0,
        "macro_items": 0,
        "user_thesis_items": 3,
    },
    "market": {
        "financial_periods": 0,
        "company_items": 0,
        "sector_items": 3,
        "macro_items": 2,
        "user_thesis_items": 0,
    },
    "risk_catalyst": {
        "financial_periods": 0,
        "company_items": 4,
        "sector_items": 2,
        "macro_items": 2,
        "user_thesis_items": 2,
    },
    "financial_interpretation": {
        "financial_periods": 2,
        "company_items": 3,
        "sector_items": 2,
        "macro_items": 1,
        "user_thesis_items": 2,
    },
    "mixed": {
        "financial_periods": 2,
        "company_items": 3,
        "sector_items": 2,
        "macro_items": 1,
        "user_thesis_items": 2,
    },
}
_COMPANY_TYPE_PRIORITY = {
    "strategy": (
        "strategic_initiative",
        "management_guidance",
        "observed_fact",
        "operating_context",
        "catalyst",
        "interpretation",
        "risk",
    ),
    "risk_catalyst": (
        "risk",
        "catalyst",
        "operating_context",
        "management_guidance",
        "observed_fact",
        "interpretation",
        "strategic_initiative",
    ),
    "financial_interpretation": (
        "observed_fact",
        "management_guidance",
        "interpretation",
        "operating_context",
        "risk",
        "catalyst",
        "strategic_initiative",
    ),
    "mixed": (
        "observed_fact",
        "management_guidance",
        "risk",
        "catalyst",
        "strategic_initiative",
        "operating_context",
        "interpretation",
    ),
}
_MARKET_TYPE_PRIORITY = {
    "market": ("sector_trend", "macro_theme", "sector_risk", "macro_risk"),
    "risk_catalyst": ("sector_risk", "macro_risk", "sector_trend", "macro_theme"),
    "financial_interpretation": (
        "sector_trend",
        "macro_theme",
        "sector_risk",
        "macro_risk",
    ),
    "mixed": ("sector_trend", "macro_theme", "sector_risk", "macro_risk"),
}
_USER_THESIS_TYPE_PRIORITY = {
    "strategy": ("thesis", "supporting_evidence", "disconfirming_evidence"),
    "risk_catalyst": ("disconfirming_evidence", "thesis", "supporting_evidence"),
    "financial_interpretation": (
        "thesis",
        "supporting_evidence",
        "disconfirming_evidence",
    ),
    "mixed": ("thesis", "supporting_evidence", "disconfirming_evidence"),
}
_ALL_SOURCE_PLAN: tuple[SourceName, ...] = (
    "financial_truth",
    "company_memory",
    "market_memory",
    "user_thesis_memory",
)
_PEER_QUERY_RE = re.compile(
    r"\b(peer|peers|comparable|comparables|vs\.?|versus|relative to|compare)\b",
    flags=re.IGNORECASE,
)
_RECENT_CONTEXT_RE = re.compile(
    r"\b(news|announcement|update|recent|latest|this week|today)\b",
    flags=re.IGNORECASE,
)
_STALE_EVIDENCE_HOURS = 96.0
_ANNOUNCEMENT_CONTEXT_LIMIT = 3
_ANNOUNCEMENT_EXCERPT_CHARS = 700
_CRITICAL_COMPANY_ANALYSIS_BLOCKERS = {
    "financials",
    "business_profile_context",
    "announcements_news_context",
}


class EvidenceProvider(Protocol):
    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: QueryIntent,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class QueryPlan:
    intent: QueryIntent
    sources: tuple[SourceName, ...]
    needs_numbers: bool
    needs_meaning: bool
    needs_environment: bool


@dataclass(frozen=True)
class OrchestratedQueryResult:
    query: str
    intent: QueryIntent
    entities: dict[str, Any]
    plan: QueryPlan
    source_plan: tuple[SourceName, ...]
    financial_truth_results: dict[str, Any]
    company_memory_results: dict[str, Any]
    market_memory_results: dict[str, Any]
    evidence: dict[str, dict[str, Any]]
    raw_supporting_evidence: dict[str, dict[str, Any]]
    answer_input: str
    answer: dict[str, Any]
    missing_categories_before_recovery: tuple[str, ...] = ()
    missing_categories_after_recovery: tuple[str, ...] = ()
    missing_data_recovery: dict[str, Any] = field(default_factory=dict)
    sufficient_for_analysis: bool = True


class _NullProvider:
    def __init__(self, source_name: SourceName) -> None:
        self._source_name = source_name

    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: QueryIntent,
    ) -> dict[str, Any]:
        return {
            "source": self._source_name,
            "status": "not_configured",
            "items": [],
            "query": query,
            "intent": intent,
            "entities": entities,
        }


def classify(query: str) -> QueryIntent:
    lowered = (query or "").strip().lower()
    if not lowered:
        return "mixed"

    has_financial = any(token in lowered for token in _FINANCIAL_KEYWORDS)
    has_interpretation = any(token in lowered for token in _INTERPRETATION_KEYWORDS)
    has_strategy = any(token in lowered for token in _STRATEGY_KEYWORDS)
    has_risk_catalyst = any(token in lowered for token in _RISK_CATALYST_KEYWORDS)
    has_market = any(token in lowered for token in _MARKET_KEYWORDS)

    active_domains = sum(
        [
            bool(has_financial),
            bool(has_strategy),
            bool(has_risk_catalyst),
            bool(has_market),
        ]
    )

    if has_financial and has_interpretation and not (has_strategy or has_risk_catalyst):
        return "financial_interpretation"
    if has_risk_catalyst and not (has_financial or has_strategy or has_market):
        return "risk_catalyst"
    if has_strategy and not (has_financial or has_risk_catalyst or has_market):
        return "strategy"
    if has_market and not (has_financial or has_strategy or has_risk_catalyst):
        return "market"
    if has_financial and active_domains <= 1:
        return "financial_fact"
    if active_domains > 1 or (has_financial and has_market):
        return "mixed"
    return "mixed"


def resolve(query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    tickers = _extract_tickers(query)
    prior_ticker = str((context or {}).get("prior_ticker") or "").strip().upper()
    if not tickers and prior_ticker:
        tickers.append(prior_ticker)
    sector = infer_sector(query, tickers)
    return {
        "primary_ticker": tickers[0] if tickers else None,
        "tickers": tickers,
        "sector": sector,
    }


def _extract_tickers(query: str) -> list[str]:
    return detect_tickers(query, stopwords=_TICKER_STOPWORDS)


def build_plan(intent: QueryIntent) -> QueryPlan:
    mapping: dict[str, QueryPlan] = {
        "financial_fact": QueryPlan(
            intent="financial_fact",
            sources=("financial_truth",),
            needs_numbers=True,
            needs_meaning=False,
            needs_environment=False,
        ),
        "strategy": QueryPlan(
            intent="strategy",
            sources=("company_memory", "user_thesis_memory"),
            needs_numbers=False,
            needs_meaning=True,
            needs_environment=False,
        ),
        "market": QueryPlan(
            intent="market",
            sources=("market_memory",),
            needs_numbers=False,
            needs_meaning=False,
            needs_environment=True,
        ),
        "risk_catalyst": QueryPlan(
            intent="risk_catalyst",
            sources=("company_memory", "market_memory", "user_thesis_memory"),
            needs_numbers=False,
            needs_meaning=True,
            needs_environment=True,
        ),
        "financial_interpretation": QueryPlan(
            intent="financial_interpretation",
            sources=(
                "financial_truth",
                "company_memory",
                "market_memory",
                "user_thesis_memory",
            ),
            needs_numbers=True,
            needs_meaning=True,
            needs_environment=True,
        ),
        "mixed": QueryPlan(
            intent="mixed",
            sources=(
                "financial_truth",
                "company_memory",
                "market_memory",
                "user_thesis_memory",
            ),
            needs_numbers=True,
            needs_meaning=True,
            needs_environment=True,
        ),
    }
    return mapping.get(intent, mapping["mixed"])


def _is_company_analysis_request(
    query: str,
    *,
    context: dict[str, Any] | None,
) -> bool:
    if context is None:
        return False
    normalized_standard = (
        str((context or {}).get("request_standard") or "").strip().lower()
    )
    if normalized_standard == "company_analysis":
        return True
    analysis_mode = str((context or {}).get("analysis_mode") or "").strip().lower()
    if analysis_mode == "deep":
        return True
    return False


def _timestamp_from_payload_row(row: Any) -> datetime | None:
    if not isinstance(row, dict):
        return None
    raw = str(
        row.get("published_at")
        or row.get("lodged_at")
        or row.get("created_at")
        or row.get("date")
        or ""
    ).strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        ts = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _latest_payload_timestamp(rows: list[Any]) -> datetime | None:
    latest: datetime | None = None
    for row in rows:
        ts = _timestamp_from_payload_row(row)
        if ts is None:
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


def _has_contradiction_metadata(items: list[Any]) -> bool:
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = dict(item.get("metadata") or {})
        if metadata.get("contradicted_entry_ids"):
            return True
    return False


def _detect_missing_categories(
    *,
    query: str,
    plan: QueryPlan,
    evidence: dict[str, dict[str, Any]],
    company_analysis_request: bool,
) -> list[str]:
    categories: list[str] = []
    category_set: set[str] = set()

    def _add(category: str) -> None:
        if category in category_set:
            return
        category_set.add(category)
        categories.append(category)

    financial_truth = evidence.get("financial_truth") or {}
    financials = financial_truth.get("financials")
    financial_rows = financials if isinstance(financials, list) else []
    latest_snapshot = financial_truth.get("latest_financial_snapshot")
    snapshot = latest_snapshot if isinstance(latest_snapshot, dict) else {}
    docs = financial_truth.get("docs")
    doc_rows = docs if isinstance(docs, list) else []
    announcements = financial_truth.get("announcement_context")
    announcement_rows = announcements if isinstance(announcements, list) else []

    company_memory = evidence.get("company_memory") or {}
    company_items = (
        company_memory.get("items") if isinstance(company_memory.get("items"), list) else []
    )
    market_memory = evidence.get("market_memory") or {}
    market_items = market_memory.get("items")
    merged_market_items = market_items if isinstance(market_items, list) else []
    if not merged_market_items:
        sector_items = market_memory.get("sector_items")
        macro_items = market_memory.get("macro_items")
        merged_market_items = (
            (sector_items if isinstance(sector_items, list) else [])
            + (macro_items if isinstance(macro_items, list) else [])
        )

    has_financial_truth = bool(snapshot) or bool(financial_rows)
    has_announcements = bool(doc_rows) or bool(announcement_rows)
    has_company_context = bool(company_items) or bool(announcement_rows)
    has_market_context = bool(merged_market_items)

    if company_analysis_request and not has_financial_truth:
        _add("financials")
    if company_analysis_request and not has_company_context:
        _add("business_profile_context")
    if (company_analysis_request or _RECENT_CONTEXT_RE.search(query)) and not has_announcements:
        _add("announcements_news_context")
    if plan.needs_environment and not has_market_context:
        _add("market_context")

    if _PEER_QUERY_RE.search(query):
        peer_signals = 0
        for item in company_items + merged_market_items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("statement") or "").lower()
            if "peer" in text or "comparable" in text:
                peer_signals += 1
        if peer_signals == 0:
            _add("peer_set")

    if "financial_truth" in plan.sources and (
        "extraction_failures" not in financial_truth
        and "low_confidence_financials" not in financial_truth
    ):
        _add("data_quality_status")

    latest_context_ts = _latest_payload_timestamp(doc_rows + announcement_rows)
    if latest_context_ts is not None:
        age_hours = (datetime.now(timezone.utc) - latest_context_ts).total_seconds() / 3600.0
        if age_hours > _STALE_EVIDENCE_HOURS:
            _add("stale_evidence")

    if _has_contradiction_metadata(company_items) or _has_contradiction_metadata(
        merged_market_items
    ):
        _add("contradictory_evidence")

    return categories


def _payload_signal_count(source: SourceName, payload: dict[str, Any]) -> int:
    if source == "financial_truth":
        financials = payload.get("financials")
        docs = payload.get("docs")
        announcements = payload.get("announcement_context")
        snapshot = payload.get("latest_financial_snapshot")
        return (
            (len(financials) if isinstance(financials, list) else 0)
            + (len(docs) if isinstance(docs, list) else 0)
            + (len(announcements) if isinstance(announcements, list) else 0)
            + (1 if isinstance(snapshot, dict) and snapshot else 0)
        )
    items = payload.get("items")
    if isinstance(items, list):
        return len(items)
    sector_items = payload.get("sector_items")
    macro_items = payload.get("macro_items")
    return (len(sector_items) if isinstance(sector_items, list) else 0) + (
        len(macro_items) if isinstance(macro_items, list) else 0
    )


def _prefer_payload(
    source: SourceName,
    current_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
) -> dict[str, Any]:
    current_status = str(current_payload.get("status") or "ok")
    candidate_status = str(candidate_payload.get("status") or "ok")
    if current_status != "ok" and candidate_status == "ok":
        return candidate_payload
    current_score = _payload_signal_count(source, current_payload)
    candidate_score = _payload_signal_count(source, candidate_payload)
    if candidate_score > current_score:
        return candidate_payload
    return current_payload


def _merge_evidence_payloads(
    *,
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    sources: tuple[SourceName, ...],
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for source in sources:
        base_payload = base.get(source) or {}
        candidate_payload = candidate.get(source) or {}
        merged[source] = _prefer_payload(source, base_payload, candidate_payload)
    return merged


def _build_recovery_query(
    query: str,
    *,
    entities: dict[str, Any],
    missing_categories: list[str],
) -> str:
    ticker = str(entities.get("primary_ticker") or "").strip().upper()
    focus_terms: list[str] = []
    if "financials" in missing_categories:
        focus_terms.append("latest financial statements")
    if "business_profile_context" in missing_categories:
        focus_terms.append("business model and strategy")
    if "announcements_news_context" in missing_categories:
        focus_terms.append("recent announcements and news")
    if "peer_set" in missing_categories:
        focus_terms.append("peers and comparables")
    if "market_context" in missing_categories:
        focus_terms.append("sector and macro backdrop")
    if not focus_terms:
        return query
    if not ticker:
        return query + " | recovery focus: " + ", ".join(focus_terms)
    return f"{query}\nRecovery focus for {ticker}: " + ", ".join(focus_terms)


def _is_sufficient_for_company_analysis(
    *,
    evidence: dict[str, dict[str, Any]],
    missing_categories: list[str],
) -> bool:
    financial_truth = evidence.get("financial_truth") or {}
    has_financials = bool(
        (financial_truth.get("latest_financial_snapshot") or {})
    ) or bool(financial_truth.get("financials") or [])
    has_company_context = bool((evidence.get("company_memory") or {}).get("items") or [])
    has_announcement_context = bool(financial_truth.get("announcement_context") or [])
    has_announcements = bool(financial_truth.get("docs") or []) or bool(
        has_announcement_context
    )
    has_market_context = bool((evidence.get("market_memory") or {}).get("items") or [])
    if not has_financials:
        return False
    if not (
        has_company_context
        or has_announcement_context
        or has_announcements
        or has_market_context
    ):
        return False
    blocker_set = set(missing_categories)
    if blocker_set & _CRITICAL_COMPANY_ANALYSIS_BLOCKERS:
        return False
    return True


def _is_sector_analysis_request(
    *,
    intent: QueryIntent,
    entities: dict[str, Any],
) -> bool:
    return intent == "market" and bool(str(entities.get("sector") or "").strip())


def _is_sufficient_for_sector_analysis(
    *,
    evidence: dict[str, dict[str, Any]],
    missing_categories: list[str],
) -> bool:
    has_market_context = bool((evidence.get("market_memory") or {}).get("items") or [])
    if not has_market_context:
        return False
    return "market_context" not in set(missing_categories)


def _confirmed_evidence_categories(
    evidence: dict[str, dict[str, Any]],
) -> list[str]:
    categories: list[str] = []
    financial_truth = evidence.get("financial_truth") or {}
    if bool(financial_truth.get("latest_financial_snapshot") or {}) or bool(
        financial_truth.get("financials") or []
    ):
        categories.append("financial truth")
    has_announcement_context = bool(financial_truth.get("announcement_context") or [])
    if bool((evidence.get("company_memory") or {}).get("items") or []) or (
        has_announcement_context
    ):
        categories.append("business/profile context")
    if bool((evidence.get("market_memory") or {}).get("items") or []):
        categories.append("market context")
    if bool(financial_truth.get("docs") or []) or bool(
        financial_truth.get("announcement_context") or []
    ):
        categories.append("announcements/news context")
    if (
        "extraction_failures" in financial_truth
        or "low_confidence_financials" in financial_truth
    ):
        categories.append("data-quality status")
    return categories


def retrieve(
    plan: QueryPlan,
    *,
    query: str,
    entities: dict[str, Any],
    financial_truth_provider: EvidenceProvider,
    company_memory_provider: EvidenceProvider,
    market_memory_provider: EvidenceProvider,
    user_thesis_memory_provider: EvidenceProvider,
) -> dict[str, dict[str, Any]]:
    providers = {
        "financial_truth": financial_truth_provider,
        "company_memory": company_memory_provider,
        "market_memory": market_memory_provider,
        "user_thesis_memory": user_thesis_memory_provider,
    }
    evidence: dict[str, dict[str, Any]] = {}
    for source in plan.sources:
        provider = providers[source]
        payload = provider.retrieve(query=query, entities=entities, intent=plan.intent)
        evidence[source] = payload if isinstance(payload, dict) else {"items": payload}
    return evidence


def compose_answer(
    intent: QueryIntent,
    plan: QueryPlan,
    evidence: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    notes: list[str] = []
    statuses: dict[str, str] = {}
    for source in plan.sources:
        payload = evidence.get(source, {})
        status = str(payload.get("status") or "ok")
        statuses[source] = status
        if status != "ok":
            notes.append(f"{source} is not configured for this orchestrator yet")

    return {
        "intent": intent,
        "sources_used": list(plan.sources),
        "source_status": statuses,
        "notes": notes,
    }


def build_answer_input(
    query: str,
    intent: QueryIntent,
    entities: dict[str, Any],
    plan: QueryPlan,
    evidence: dict[str, dict[str, Any]],
    answer: dict[str, Any],
) -> str:
    budgets = _QUERY_BUDGETS.get(intent, _QUERY_BUDGETS["mixed"])
    lines = [f"Query intent: {intent}"]
    ticker = str(entities.get("primary_ticker") or "").strip().upper()
    if ticker:
        lines.append(f"Primary ticker: {ticker}")
    lines.append("Source priority: " + " -> ".join(plan.sources))
    lines.append(f"User question: {query}")
    lines.append(
        "Use financial truth for explicit numbers, company memory for business meaning, and market memory only when it adds relevant external context."
    )
    recovery = (
        dict(answer.get("missing_data_recovery") or {})
        if isinstance(answer.get("missing_data_recovery"), dict)
        else {}
    )
    missing_before = [
        str(item)
        for item in (answer.get("missing_categories_before_recovery") or [])
        if str(item).strip()
    ]
    missing_after = [
        str(item)
        for item in (answer.get("missing_categories_after_recovery") or [])
        if str(item).strip()
    ]
    financial_truth = evidence.get("financial_truth") or {}
    if recovery.get("attempted"):
        lines.append("Confirmed evidence already present:")
        confirmed = _confirmed_evidence_categories(evidence)
        if confirmed:
            for category in confirmed:
                lines.append(f"- {category}")
        else:
            lines.append("- none")

        lines.append("Missing or weak evidence categories:")
        if missing_before:
            for category in missing_before:
                lines.append(f"- {category}")
        else:
            lines.append("- none detected")

        lines.append("Additional retrieval attempts:")
        lines.append(
            "- ran one bounded recovery pass across expanded sources before final verdict"
        )
        recovery_sources = recovery.get("sources")
        if isinstance(recovery_sources, list) and recovery_sources:
            lines.append("- recovery sources: " + ", ".join(str(src) for src in recovery_sources))

        lines.append("Updated evidence state:")
        resolved = recovery.get("resolved_categories")
        if isinstance(resolved, list) and resolved:
            lines.append("- resolved gaps: " + ", ".join(str(item) for item in resolved))
        if missing_after:
            lines.append("- unresolved gaps: " + ", ".join(missing_after))
        else:
            lines.append("- unresolved gaps: none")

        if not bool(answer.get("sufficient_for_analysis", True)):
            _append_announcement_context_lines(lines, financial_truth)
            lines.append("Final verdict: abstain until blocking evidence gaps are resolved.")
            lines.append("Unknowns:")
            if missing_after:
                for category in missing_after:
                    lines.append(f"- {category}")
            else:
                lines.append("- unresolved evidence blockers")
            return "\n".join(lines)
        lines.append("Recovery outcome: sufficient evidence available; proceeding with analysis.")

    if not bool(answer.get("sufficient_for_analysis", True)):
        lines.append("Confirmed evidence already present:")
        confirmed = _confirmed_evidence_categories(evidence)
        if confirmed:
            for category in confirmed:
                lines.append(f"- {category}")
        else:
            lines.append("- none")
        lines.append("Missing or weak evidence categories:")
        if missing_after:
            for category in missing_after:
                lines.append(f"- {category}")
        else:
            lines.append("- unresolved evidence blockers")
        _append_announcement_context_lines(lines, financial_truth)
        lines.append("Final verdict: abstain until blocking evidence gaps are resolved.")
        lines.append("Unknowns:")
        if missing_after:
            for category in missing_after:
                lines.append(f"- {category}")
        else:
            lines.append("- unresolved evidence blockers")
        return "\n".join(lines)

    snapshot = financial_truth.get("latest_financial_snapshot") or {}
    financials = financial_truth.get("financials") or []
    if "financial_truth" in plan.sources:
        lines.append("Facts from financial truth:")
        if snapshot:
            summary_bits = []
            for field in (
                "period_end",
                "period_type",
                "revenue",
                "ebit",
                "np_attributable",
                "operating_cf",
                "net_debt",
                "cash_end",
            ):
                value = snapshot.get(field)
                if value not in (None, ""):
                    summary_bits.append(f"{field}={value}")
            if summary_bits:
                lines.append("- latest snapshot: " + ", ".join(summary_bits))
        if financials:
            periods = [
                str(row.get("period_end") or "")
                for row in financials[: budgets["financial_periods"]]
                if row
            ]
            if periods:
                lines.append("- financial periods available: " + ", ".join(periods))
        if not snapshot and not financials:
            lines.append("- no canonical financial rows were returned")
        _append_announcement_context_lines(lines, financial_truth)

    company_memory = evidence.get("company_memory") or {}
    if "company_memory" in plan.sources:
        company_items = _select_memory_items(
            company_memory.get("items") or [],
            intent=intent,
            query=query,
            limit=budgets["company_items"],
            priorities=_COMPANY_TYPE_PRIORITY.get(
                intent, _COMPANY_TYPE_PRIORITY["mixed"]
            ),
        )
        lines.append("Interpretation from company memory:")
        if company_items:
            for item in company_items:
                lines.append(f"- {_format_company_item(item)}")
        else:
            lines.append("- no company-memory signals matched")

    market_memory = evidence.get("market_memory") or {}
    if "market_memory" in plan.sources:
        sector = market_memory.get("sector")
        sector_items = _select_memory_items(
            market_memory.get("sector_items") or [],
            intent=intent,
            query=query,
            limit=budgets["sector_items"],
            priorities=_MARKET_TYPE_PRIORITY.get(
                intent, _MARKET_TYPE_PRIORITY["mixed"]
            ),
        )
        macro_items = _select_memory_items(
            market_memory.get("macro_items") or [],
            intent=intent,
            query=query,
            limit=budgets["macro_items"],
            priorities=_MARKET_TYPE_PRIORITY.get(
                intent, _MARKET_TYPE_PRIORITY["mixed"]
            ),
        )
        lines.append("External context from market memory:")
        if sector:
            lines.append(f"- relevant sector: {sector}")
        for item in sector_items:
            lines.append(f"- sector: {_memory_statement(item)}")
        for item in macro_items:
            lines.append(f"- macro: {_memory_statement(item)}")
        if not sector_items and not macro_items:
            lines.append("- no shared market-memory signals matched")

    user_thesis_memory = evidence.get("user_thesis_memory") or {}
    if "user_thesis_memory" in plan.sources:
        thesis_items = _select_memory_items(
            user_thesis_memory.get("items") or [],
            intent=intent,
            query=query,
            limit=budgets["user_thesis_items"],
            priorities=_USER_THESIS_TYPE_PRIORITY.get(
                intent, _USER_THESIS_TYPE_PRIORITY["mixed"]
            ),
        )
        lines.append("User thesis memory (confirmed):")
        if thesis_items:
            for item in thesis_items:
                lines.append(f"- {_format_user_thesis_item(item)}")
        else:
            lines.append("- no confirmed thesis items matched")

    uncertainty_notes = _uncertainty_notes(
        company_items=company_memory.get("items") or [],
        market_items=(market_memory.get("sector_items") or [])
        + (market_memory.get("macro_items") or []),
    )
    if uncertainty_notes:
        lines.append("Uncertainty:")
        for note in uncertainty_notes:
            lines.append(f"- {note}")

    notes = answer.get("notes") or []
    if notes:
        lines.append("Notes:")
        for note in notes:
            lines.append(f"- {note}")

    if plan.needs_numbers:
        lines.append("Numbers must come from canonical financial truth only.")
    return "\n".join(lines)


def _select_memory_items(
    items: list[Any],
    *,
    intent: str,
    query: str,
    limit: int,
    priorities: tuple[str, ...],
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    priority_map = {
        name: len(priorities) - index for index, name in enumerate(priorities)
    }
    query_terms = _query_terms(query)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        if float(item.get("active_score") or 0.0) < 0.55:
            continue
        item_type = str(item.get("type") or item.get("entry_type") or "").strip().lower()
        metadata = dict(item.get("metadata") or {})
        item_terms = _query_terms(str(item.get("statement") or ""))
        theme_terms = {str(theme).lower() for theme in metadata.get("themes") or []}
        overlap_bonus = (
            0.05 if (item_terms & query_terms or theme_terms & query_terms) else 0.0
        )
        score = (
            float(item.get("active_score") or 0.0)
            + (priority_map.get(item_type, 0) * 0.01)
            + overlap_bonus
        )
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:limit]]


def _memory_statement(item: dict[str, Any]) -> str:
    statement = str(item.get("statement") or "").strip()
    metadata = dict(item.get("metadata") or {})
    suffixes: list[str] = []
    if metadata.get("superseded_entry_ids"):
        suffixes.append("updates an earlier view")
    if metadata.get("contradicted_entry_ids"):
        suffixes.append("conflicts with an earlier view")
    return statement if not suffixes else f"{statement} ({'; '.join(suffixes)})"


def _format_company_item(item: dict[str, Any]) -> str:
    label = str(item.get("type") or "context").replace("_", " ")
    return f"{label}: {_memory_statement(item)}"


def _format_user_thesis_item(item: dict[str, Any]) -> str:
    label = str(item.get("entry_type") or item.get("type") or "thesis").replace(
        "_", " "
    )
    signal = str(item.get("signal") or "").strip()
    prefix = f"{label} ({signal})" if signal else label
    return f"{prefix}: {_memory_statement(item)}"


def _compact_line(value: Any, *, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _select_announcement_context_rows(
    financial_truth: dict[str, Any],
    *,
    limit: int = _ANNOUNCEMENT_CONTEXT_LIMIT,
) -> list[dict[str, Any]]:
    rows = financial_truth.get("announcement_context")
    if not isinstance(rows, list) or limit <= 0:
        return []
    selected: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        excerpt = str(row.get("excerpt") or "").strip()
        if not title and not excerpt:
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _append_announcement_context_lines(
    lines: list[str],
    financial_truth: dict[str, Any],
) -> None:
    rows = _select_announcement_context_rows(financial_truth)
    if not rows:
        return
    lines.append("Available announcement/news context from financial truth:")
    for row in rows:
        parts: list[str] = []
        published_at = _compact_line(row.get("published_at"), max_chars=32)
        title = _compact_line(row.get("title"), max_chars=120)
        excerpt = _compact_line(
            row.get("excerpt"),
            max_chars=_ANNOUNCEMENT_EXCERPT_CHARS,
        )
        if published_at:
            parts.append(published_at)
        if title:
            parts.append(title)
        line = " | ".join(parts) if parts else "announcement context"
        if excerpt:
            line += f": {excerpt}"
        source_url = _compact_line(row.get("source_url"), max_chars=180)
        if source_url:
            line += f" (source: {source_url})"
        lines.append(f"- {line}")


def _uncertainty_notes(
    *,
    company_items: list[Any],
    market_items: list[Any],
) -> list[str]:
    notes: list[str] = []
    if any(
        isinstance(item, dict)
        and dict(item.get("metadata") or {}).get("contradicted_entry_ids")
        for item in company_items
    ):
        notes.append(
            "company memory includes updated or conflicting qualitative signals; treat them as directional rather than settled fact"
        )
    if any(
        isinstance(item, dict)
        and dict(item.get("metadata") or {}).get("contradicted_entry_ids")
        for item in market_items
    ):
        notes.append(
            "market context includes conflicting signals, so external backdrop should be treated as uncertain"
        )
    return notes


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", str(query or "").lower())
        if len(token) > 2
    }


class QueryOrchestrator:
    def __init__(
        self,
        *,
        financial_truth_provider: EvidenceProvider | None = None,
        company_memory_provider: EvidenceProvider | None = None,
        market_memory_provider: EvidenceProvider | None = None,
        user_thesis_memory_provider: EvidenceProvider | None = None,
        memory_assembler: MemoryAssembler | None = None,
    ) -> None:
        self._financial_truth_provider = financial_truth_provider or _NullProvider(
            "financial_truth"
        )
        self._company_memory_provider = company_memory_provider or CompanyMemoryStore()
        self._market_memory_provider = market_memory_provider or MarketMemoryStore()
        self._user_thesis_memory_provider = (
            user_thesis_memory_provider or _NullProvider("user_thesis_memory")
        )
        self._memory_assembler = memory_assembler or MemoryAssembler(
            financial_truth_provider=self._financial_truth_provider,
            company_memory_provider=self._company_memory_provider,
            market_memory_provider=self._market_memory_provider,
            user_thesis_memory_provider=self._user_thesis_memory_provider,
        )

    def orchestrate_query(self, query: str) -> OrchestratedQueryResult:
        return self.orchestrate_query_with_context(query)

    def orchestrate_query_with_context(
        self,
        query: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> OrchestratedQueryResult:
        intent = classify(query)
        entities = resolve(query, context=context)
        plan = build_plan(intent)
        memory_bundle = self._memory_assembler.assemble(
            mode="cockpit_chat",
            query=query,
            intent=plan.intent,
            entities=entities,
            source_plan=plan.sources,
        )
        evidence = memory_bundle.evidence
        raw_evidence = memory_bundle.raw_evidence
        company_analysis_request = _is_company_analysis_request(
            query,
            context=context,
        )
        sector_analysis_request = _is_sector_analysis_request(
            intent=intent,
            entities=entities,
        )
        missing_before = _detect_missing_categories(
            query=query,
            plan=plan,
            evidence=evidence,
            company_analysis_request=company_analysis_request,
        )
        missing_after = list(missing_before)
        recovery_summary: dict[str, Any] = {
            "attempted": False,
            "sources": [],
            "resolved_categories": [],
            "remaining_categories": list(missing_after),
        }
        effective_plan = plan

        if company_analysis_request and missing_before:
            recovery_entities = dict(entities)
            recovery_entities["recovery_level"] = "deep"
            recovery_entities["recovery_targets"] = list(missing_before)
            recovery_sources = tuple(dict.fromkeys(plan.sources + _ALL_SOURCE_PLAN))
            recovery_query = _build_recovery_query(
                query,
                entities=entities,
                missing_categories=missing_before,
            )
            recovery_bundle = self._memory_assembler.assemble(
                mode="cockpit_chat_missing_data_recovery",
                query=recovery_query,
                intent=plan.intent,
                entities=recovery_entities,
                source_plan=recovery_sources,
            )
            evidence = _merge_evidence_payloads(
                base=evidence,
                candidate=recovery_bundle.evidence,
                sources=recovery_sources,
            )
            raw_evidence = _merge_evidence_payloads(
                base=raw_evidence,
                candidate=recovery_bundle.raw_evidence,
                sources=recovery_sources,
            )
            missing_after = _detect_missing_categories(
                query=query,
                plan=plan,
                evidence=evidence,
                company_analysis_request=company_analysis_request,
            )
            resolved = [category for category in missing_before if category not in missing_after]
            recovery_summary = {
                "attempted": True,
                "sources": list(recovery_sources),
                "query": recovery_query,
                "resolved_categories": resolved,
                "remaining_categories": list(missing_after),
            }
            effective_plan = QueryPlan(
                intent=plan.intent,
                sources=recovery_sources,
                needs_numbers=plan.needs_numbers,
                needs_meaning=plan.needs_meaning,
                needs_environment=plan.needs_environment,
            )

        sufficient_for_analysis = True
        if company_analysis_request:
            sufficient_for_analysis = _is_sufficient_for_company_analysis(
                evidence=evidence,
                missing_categories=missing_after,
            )
        elif sector_analysis_request:
            sufficient_for_analysis = _is_sufficient_for_sector_analysis(
                evidence=evidence,
                missing_categories=missing_after,
            )

        answer = compose_answer(intent, effective_plan, evidence)
        answer["missing_categories_before_recovery"] = list(missing_before)
        answer["missing_categories_after_recovery"] = list(missing_after)
        answer["missing_data_recovery"] = recovery_summary
        answer["sufficient_for_analysis"] = sufficient_for_analysis
        if recovery_summary.get("attempted") and not sufficient_for_analysis:
            answer.setdefault("notes", []).append(
                "insufficient evidence after bounded recovery pass; abstain with explicit blockers"
            )
        elif sector_analysis_request and not sufficient_for_analysis:
            answer.setdefault("notes", []).append(
                "insufficient sector evidence; abstain with explicit market-context blocker"
            )
        answer_input = build_answer_input(
            query,
            intent,
            entities,
            effective_plan,
            evidence,
            answer,
        )
        return OrchestratedQueryResult(
            query=query,
            intent=intent,
            entities=entities,
            plan=effective_plan,
            source_plan=effective_plan.sources,
            financial_truth_results=evidence.get("financial_truth") or {},
            company_memory_results=evidence.get("company_memory") or {},
            market_memory_results=evidence.get("market_memory") or {},
            evidence=evidence,
            raw_supporting_evidence=raw_evidence,
            answer_input=answer_input,
            answer=answer,
            missing_categories_before_recovery=tuple(missing_before),
            missing_categories_after_recovery=tuple(missing_after),
            missing_data_recovery=recovery_summary,
            sufficient_for_analysis=sufficient_for_analysis,
        )


def orchestrate_query(
    query: str,
    *,
    financial_truth_provider: EvidenceProvider | None = None,
    company_memory_provider: EvidenceProvider | None = None,
    market_memory_provider: EvidenceProvider | None = None,
    user_thesis_memory_provider: EvidenceProvider | None = None,
    context: dict[str, Any] | None = None,
) -> OrchestratedQueryResult:
    return QueryOrchestrator(
        financial_truth_provider=financial_truth_provider,
        company_memory_provider=company_memory_provider,
        market_memory_provider=market_memory_provider,
        user_thesis_memory_provider=user_thesis_memory_provider,
    ).orchestrate_query_with_context(query, context=context)
