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
    "local_personal_data",
    "financial_truth",
    "no_hit",
    "context_only",
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


def primary_source_label(
    labels: Iterable[str],
    *,
    primary_order: tuple[str, ...] = SOURCE_LABEL_PRIMARY_ORDER,
) -> str:
    label_set = {str(label) for label in labels}
    for label in primary_order:
        if label in label_set:
            return label
    return "unknown_unclassified"


def coverage_from_evidence_labels(
    labels: Iterable[str],
    *,
    coverage_priority: tuple[str, ...] = EVIDENCE_COVERAGE_PRIORITY,
) -> str | None:
    label_set = {str(label) for label in labels}
    for label in coverage_priority:
        if label in label_set:
            return label
    return None
