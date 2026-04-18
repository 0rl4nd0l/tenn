from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from app.services.company_memory import CompanyMemoryStore
from app.services.market_memory import MarketMemoryStore
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
    },
    "strategy": {
        "financial_periods": 0,
        "company_items": 4,
        "sector_items": 0,
        "macro_items": 0,
    },
    "market": {
        "financial_periods": 0,
        "company_items": 0,
        "sector_items": 3,
        "macro_items": 2,
    },
    "risk_catalyst": {
        "financial_periods": 0,
        "company_items": 4,
        "sector_items": 2,
        "macro_items": 2,
    },
    "financial_interpretation": {
        "financial_periods": 2,
        "company_items": 3,
        "sector_items": 2,
        "macro_items": 1,
    },
    "mixed": {
        "financial_periods": 2,
        "company_items": 3,
        "sector_items": 2,
        "macro_items": 1,
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
    return {
        "primary_ticker": tickers[0] if tickers else None,
        "tickers": tickers,
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
            sources=("company_memory",),
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
            sources=("company_memory", "market_memory"),
            needs_numbers=False,
            needs_meaning=True,
            needs_environment=True,
        ),
        "financial_interpretation": QueryPlan(
            intent="financial_interpretation",
            sources=("financial_truth", "company_memory", "market_memory"),
            needs_numbers=True,
            needs_meaning=True,
            needs_environment=True,
        ),
        "mixed": QueryPlan(
            intent="mixed",
            sources=("financial_truth", "company_memory", "market_memory"),
            needs_numbers=True,
            needs_meaning=True,
            needs_environment=True,
        ),
    }
    return mapping.get(intent, mapping["mixed"])


def retrieve(
    plan: QueryPlan,
    *,
    query: str,
    entities: dict[str, Any],
    financial_truth_provider: EvidenceProvider,
    company_memory_provider: EvidenceProvider,
    market_memory_provider: EvidenceProvider,
) -> dict[str, dict[str, Any]]:
    providers = {
        "financial_truth": financial_truth_provider,
        "company_memory": company_memory_provider,
        "market_memory": market_memory_provider,
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

    financial_truth = evidence.get("financial_truth") or {}
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
        item_type = str(item.get("type") or "").strip().lower()
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
    ) -> None:
        self._financial_truth_provider = financial_truth_provider or _NullProvider(
            "financial_truth"
        )
        self._company_memory_provider = company_memory_provider or CompanyMemoryStore()
        self._market_memory_provider = market_memory_provider or MarketMemoryStore()

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
        evidence = retrieve(
            plan,
            query=query,
            entities=entities,
            financial_truth_provider=self._financial_truth_provider,
            company_memory_provider=self._company_memory_provider,
            market_memory_provider=self._market_memory_provider,
        )
        answer = compose_answer(intent, plan, evidence)
        answer_input = build_answer_input(
            query,
            intent,
            entities,
            plan,
            evidence,
            answer,
        )
        return OrchestratedQueryResult(
            query=query,
            intent=intent,
            entities=entities,
            plan=plan,
            source_plan=plan.sources,
            financial_truth_results=evidence.get("financial_truth") or {},
            company_memory_results=evidence.get("company_memory") or {},
            market_memory_results=evidence.get("market_memory") or {},
            evidence=evidence,
            raw_supporting_evidence=evidence,
            answer_input=answer_input,
            answer=answer,
        )


def orchestrate_query(
    query: str,
    *,
    financial_truth_provider: EvidenceProvider | None = None,
    company_memory_provider: EvidenceProvider | None = None,
    market_memory_provider: EvidenceProvider | None = None,
    context: dict[str, Any] | None = None,
) -> OrchestratedQueryResult:
    return QueryOrchestrator(
        financial_truth_provider=financial_truth_provider,
        company_memory_provider=company_memory_provider,
        market_memory_provider=market_memory_provider,
    ).orchestrate_query_with_context(query, context=context)
