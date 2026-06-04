from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

QueryIntent = str
SourceName = str


@dataclass(frozen=True)
class AnswerSourceRole:
    name: SourceName
    evidence_labels: tuple[str, ...]
    canonical_numeric_truth: bool
    context_only: bool
    missing_categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnswerSourcePlan:
    intent: QueryIntent
    sources: tuple[SourceName, ...]
    needs_numbers: bool
    needs_meaning: bool
    needs_environment: bool
    answer_guidance: str = (
        "Use financial truth for explicit numbers, company memory for business "
        "meaning, and market memory only when it adds relevant external context."
    )

    @property
    def canonical_numeric_sources(self) -> tuple[SourceName, ...]:
        return tuple(
            source
            for source in self.sources
            if (source_role_for(source) or _UNKNOWN_ROLE).canonical_numeric_truth
        )

    @property
    def context_only_sources(self) -> tuple[SourceName, ...]:
        return tuple(
            source
            for source in self.sources
            if (source_role_for(source) or _UNKNOWN_ROLE).context_only
        )

    def missing_categories_for_source(
        self,
        source: SourceName,
        missing_categories: Iterable[str],
    ) -> tuple[str, ...]:
        return source_missing_categories(source, missing_categories)

    def recovery_sources(self) -> tuple[SourceName, ...]:
        return tuple(dict.fromkeys(self.sources + ALL_ANSWER_SOURCE_NAMES))


_UNKNOWN_ROLE = AnswerSourceRole(
    name="unknown",
    evidence_labels=(),
    canonical_numeric_truth=False,
    context_only=True,
)

_SOURCE_ROLES: dict[SourceName, AnswerSourceRole] = {
    "financial_truth": AnswerSourceRole(
        name="financial_truth",
        evidence_labels=("financial_truth",),
        canonical_numeric_truth=True,
        context_only=False,
        missing_categories=("announcements_news_context", "financials"),
    ),
    "company_memory": AnswerSourceRole(
        name="company_memory",
        evidence_labels=("memory_context",),
        canonical_numeric_truth=False,
        context_only=True,
        missing_categories=("business_profile_context", "peer_set"),
    ),
    "market_memory": AnswerSourceRole(
        name="market_memory",
        evidence_labels=("memory_context",),
        canonical_numeric_truth=False,
        context_only=True,
        missing_categories=("market_context", "peer_set"),
    ),
    "user_thesis_memory": AnswerSourceRole(
        name="user_thesis_memory",
        evidence_labels=("memory_context",),
        canonical_numeric_truth=False,
        context_only=True,
    ),
}

ALL_ANSWER_SOURCE_NAMES: tuple[SourceName, ...] = (
    "financial_truth",
    "company_memory",
    "market_memory",
    "user_thesis_memory",
)

_ANSWER_SOURCE_PLANS: dict[QueryIntent, AnswerSourcePlan] = {
    "general": AnswerSourcePlan(
        intent="general",
        sources=(),
        needs_numbers=False,
        needs_meaning=False,
        needs_environment=False,
    ),
    "financial_fact": AnswerSourcePlan(
        intent="financial_fact",
        sources=("financial_truth",),
        needs_numbers=True,
        needs_meaning=False,
        needs_environment=False,
    ),
    "strategy": AnswerSourcePlan(
        intent="strategy",
        sources=("company_memory", "user_thesis_memory"),
        needs_numbers=False,
        needs_meaning=True,
        needs_environment=False,
    ),
    "market": AnswerSourcePlan(
        intent="market",
        sources=("market_memory",),
        needs_numbers=False,
        needs_meaning=False,
        needs_environment=True,
    ),
    "risk_catalyst": AnswerSourcePlan(
        intent="risk_catalyst",
        sources=("company_memory", "market_memory", "user_thesis_memory"),
        needs_numbers=False,
        needs_meaning=True,
        needs_environment=True,
    ),
    "financial_interpretation": AnswerSourcePlan(
        intent="financial_interpretation",
        sources=ALL_ANSWER_SOURCE_NAMES,
        needs_numbers=True,
        needs_meaning=True,
        needs_environment=True,
    ),
    "mixed": AnswerSourcePlan(
        intent="mixed",
        sources=ALL_ANSWER_SOURCE_NAMES,
        needs_numbers=True,
        needs_meaning=True,
        needs_environment=True,
    ),
}


def build_answer_source_plan(intent: QueryIntent) -> AnswerSourcePlan:
    return _ANSWER_SOURCE_PLANS.get(intent, _ANSWER_SOURCE_PLANS["general"])


def source_role_for(source: SourceName) -> AnswerSourceRole | None:
    return _SOURCE_ROLES.get(str(source or "").strip().lower())


def source_missing_categories(
    source: SourceName,
    missing_categories: Iterable[str],
) -> tuple[str, ...]:
    role = source_role_for(source)
    if role is None:
        return ()
    missing = {str(category).strip() for category in missing_categories if str(category).strip()}
    return tuple(category for category in role.missing_categories if category in missing)
