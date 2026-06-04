from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.answer_source_plan import (
    ALL_ANSWER_SOURCE_NAMES,
    build_answer_source_plan,
    source_role_for,
)


def test_financial_fact_plan_uses_only_canonical_financial_truth() -> None:
    plan = build_answer_source_plan("financial_fact")

    assert plan.sources == ("financial_truth",)
    assert plan.needs_numbers is True
    assert plan.canonical_numeric_sources == ("financial_truth",)
    assert plan.context_only_sources == ()

    role = source_role_for("financial_truth")
    assert role is not None
    assert role.canonical_numeric_truth is True
    assert role.context_only is False


def test_interpretation_plan_orders_truth_before_context_only_memory() -> None:
    plan = build_answer_source_plan("financial_interpretation")

    assert plan.sources == (
        "financial_truth",
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    )
    assert plan.canonical_numeric_sources == ("financial_truth",)
    assert plan.context_only_sources == (
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    )
    assert plan.answer_guidance == (
        "Use financial truth for explicit numbers, company memory for business "
        "meaning, and market memory only when it adds relevant external context."
    )


def test_memory_roles_cannot_satisfy_numeric_truth() -> None:
    for source_name in ("company_memory", "market_memory", "user_thesis_memory"):
        role = source_role_for(source_name)
        assert role is not None
        assert role.context_only is True
        assert role.canonical_numeric_truth is False
        assert "memory_context" in role.evidence_labels


def test_recovery_sources_are_deterministic_superset() -> None:
    plan = build_answer_source_plan("strategy")

    assert plan.sources == ("company_memory", "user_thesis_memory")
    assert plan.recovery_sources() == (
        "company_memory",
        "user_thesis_memory",
        "financial_truth",
        "market_memory",
    )
    assert plan.recovery_sources() == tuple(dict.fromkeys(plan.sources + ALL_ANSWER_SOURCE_NAMES))


def test_missing_category_mapping_is_source_specific() -> None:
    plan = build_answer_source_plan("mixed")
    missing = {
        "financials",
        "announcements_news_context",
        "business_profile_context",
        "market_context",
        "peer_set",
    }

    assert plan.missing_categories_for_source("financial_truth", missing) == (
        "announcements_news_context",
        "financials",
    )
    assert plan.missing_categories_for_source("company_memory", missing) == (
        "business_profile_context",
        "peer_set",
    )
    assert plan.missing_categories_for_source("market_memory", missing) == (
        "market_context",
        "peer_set",
    )
