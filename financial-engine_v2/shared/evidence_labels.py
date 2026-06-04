from __future__ import annotations

from typing import Any, Iterable

SOURCE_LABEL_TAXONOMY_VERSION = "source_label_semantics_v1"

SOURCE_LABEL_DEFINITIONS: dict[str, str] = {
    "claim_verified": "The source directly supports a claim in the answer.",
    "context_only": (
        "The source was used for background/context and does not by itself "
        "verify a claim."
    ),
    "no_hit": "A search/tool/source path was attempted but returned no relevant evidence.",
    "operational_trace": "The source is a tool/runtime/system trace, not financial evidence.",
    "local_personal_data": "User/cockpit-local data such as holdings, not financial truth.",
    "memory_context": (
        "Company/market/thesis memory context, not canonical truth unless "
        "separately supported."
    ),
    "external_web_context": "External web context, not canonical financial truth.",
    "local_news_context": (
        "Retrieved local/news context; not claim verification unless paired "
        "with claim_verified."
    ),
    "financial_truth": "Canonical numeric financial truth or structured extracted metrics.",
    "financial_truth_numeric": (
        "Structured numeric financial truth context, not event/news verification."
    ),
    "degraded_runtime": "The answer was produced under runtime/tool/synthesis degradation.",
    "missing_required_evidence": "The answer has a known evidence gap.",
    "insufficient_for_recent_news": "Recent-news/update evidence is missing or price-only.",
    "market_data_missing": "Market-price or technical-trend evidence is missing.",
    "metric_extraction_missing": "Canonical metric extraction evidence is missing.",
    "unsupported_or_not_verified": (
        "The answer contains unsupported or not-yet-verified claim families."
    ),
    "unknown_unclassified": "Safe fallback for unclassified sources; never treated as verified.",
}

VALID_SOURCE_LABELS = frozenset(SOURCE_LABEL_DEFINITIONS)

SOURCE_LABEL_PRIMARY_ORDER = (
    "missing_required_evidence",
    "degraded_runtime",
    "no_hit",
    "claim_verified",
    "financial_truth",
    "financial_truth_numeric",
    "local_personal_data",
    "memory_context",
    "external_web_context",
    "local_news_context",
    "operational_trace",
    "unknown_unclassified",
    "context_only",
)

SOURCE_ROLE_LABELS = frozenset(
    {
        "financial_truth",
        "local_personal_data",
        "memory_context",
        "external_web_context",
        "local_news_context",
        "operational_trace",
        "unknown_unclassified",
    }
)

ORCHESTRATOR_EVIDENCE_LABELS = frozenset(
    {
        "claim_verified",
        "context_only",
        "no_hit",
        "operational_trace",
        "local_personal_data",
        "memory_context",
        "external_web_context",
        "local_news_context",
        "financial_truth",
        "degraded_runtime",
        "missing_required_evidence",
        "unknown_unclassified",
    }
)

CHAT_SOURCE_LABEL_PRIMARY_ORDER = (
    "missing_required_evidence",
    "degraded_runtime",
    "no_hit",
    "claim_verified",
    "financial_truth",
    "local_personal_data",
    "memory_context",
    "external_web_context",
    "local_news_context",
    "operational_trace",
    "unknown_unclassified",
    "context_only",
)

EVIDENCE_STATE_LABELS = frozenset(
    {
        "degraded_runtime",
        "missing_required_evidence",
        "no_hit",
        "operational_trace",
        "context_only",
        "local_personal_data",
        "memory_context",
        "external_web_context",
        "local_news_context",
        "financial_truth",
        "unknown_unclassified",
    }
)

EVIDENCE_COVERAGE_PRIORITY = (
    "degraded_runtime",
    "missing_required_evidence",
    "unsupported_or_not_verified",
    "market_data_missing",
    "metric_extraction_missing",
    "insufficient_for_recent_news",
    "local_personal_data",
    "financial_truth",
    "no_hit",
    "context_only",
)

CONTEXT_ONLY_SOURCE_LABELS = frozenset(
    {
        "context_only",
        "memory_context",
        "external_web_context",
        "unknown_unclassified",
    }
)

NON_EVIDENCE_LABELS = frozenset(
    {
        "no_hit",
        "degraded_runtime",
        "missing_required_evidence",
        "insufficient_for_recent_news",
        "market_data_missing",
        "metric_extraction_missing",
        "unsupported_or_not_verified",
    }
)

CLAIM_VERIFIED_BLOCKING_LABELS = CONTEXT_ONLY_SOURCE_LABELS | NON_EVIDENCE_LABELS
CANONICAL_FINANCIAL_TRUTH_BLOCKING_LABELS = (
    CONTEXT_ONLY_SOURCE_LABELS
    | NON_EVIDENCE_LABELS
    | frozenset({"local_personal_data", "local_news_context", "operational_trace"})
)


def normalize_source_labels(
    value: Any,
    *,
    valid_labels: frozenset[str] = VALID_SOURCE_LABELS,
) -> set[str]:
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = []

    labels: set[str] = set()
    for item in raw_items:
        label = str(item or "").strip()
        if label in valid_labels:
            labels.add(label)
    return labels


def ordered_source_labels(
    labels: Iterable[str],
    *,
    valid_labels: frozenset[str] = VALID_SOURCE_LABELS,
    primary_order: tuple[str, ...] = SOURCE_LABEL_PRIMARY_ORDER,
) -> list[str]:
    label_set = {str(label) for label in labels if str(label) in valid_labels}
    ordered = [label for label in primary_order if label in label_set]
    ordered.extend(sorted(label_set.difference(ordered)))
    return ordered


def context_only_from_labels(labels: Iterable[str]) -> bool:
    label_set = {str(label) for label in labels}
    return bool(label_set & (CONTEXT_ONLY_SOURCE_LABELS | NON_EVIDENCE_LABELS))


def claim_verified_from_labels(labels: Iterable[str]) -> bool:
    label_set = {str(label) for label in labels}
    return "claim_verified" in label_set and not (
        label_set & CLAIM_VERIFIED_BLOCKING_LABELS
    )


def canonical_financial_truth_from_labels(labels: Iterable[str]) -> bool:
    label_set = {str(label) for label in labels}
    return "financial_truth" in label_set and not (
        label_set & CANONICAL_FINANCIAL_TRUTH_BLOCKING_LABELS
    )


def apply_context_only_boundaries(labels: Iterable[str]) -> set[str]:
    """Apply truth-boundary semantics without filtering unknown extension labels."""
    effective = {str(label) for label in labels if str(label).strip()}
    if context_only_from_labels(effective):
        effective.add("context_only")
    if not claim_verified_from_labels(effective):
        effective.discard("claim_verified")
    if not canonical_financial_truth_from_labels(effective):
        effective.discard("financial_truth")
        effective.discard("financial_truth_numeric")
    if not effective:
        effective.add("unknown_unclassified")
    return effective


def effective_source_labels(
    value: Any,
    *,
    valid_labels: frozenset[str] = VALID_SOURCE_LABELS,
) -> set[str]:
    return apply_context_only_boundaries(
        normalize_source_labels(value, valid_labels=valid_labels)
    )


def primary_source_label(
    labels: Iterable[str],
    *,
    primary_order: tuple[str, ...] = SOURCE_LABEL_PRIMARY_ORDER,
) -> str:
    label_set = apply_context_only_boundaries(labels)
    for label in primary_order:
        if label in label_set:
            return label
    return "unknown_unclassified"


def coverage_from_evidence_labels(
    labels: Iterable[str],
    *,
    coverage_priority: tuple[str, ...] = EVIDENCE_COVERAGE_PRIORITY,
) -> str | None:
    label_set = apply_context_only_boundaries(labels)
    for label in coverage_priority:
        if label in label_set:
            return label
    return None
