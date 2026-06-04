from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import cockpit_api
from app.services import chat_evidence_guard, query_orchestrator, tenn_chat
from shared.evidence_labels import (
    ORCHESTRATOR_EVIDENCE_LABELS,
    SOURCE_LABEL_DEFINITIONS,
    SOURCE_LABEL_TAXONOMY_VERSION,
    VALID_SOURCE_LABELS,
    canonical_financial_truth_from_labels,
    claim_verified_from_labels,
    coverage_from_evidence_labels,
    effective_source_labels,
    normalize_source_labels,
    ordered_source_labels,
    primary_source_label,
)


def test_shared_taxonomy_is_backend_route_and_orchestrator_source() -> None:
    assert cockpit_api.SOURCE_LABEL_DEFINITIONS is SOURCE_LABEL_DEFINITIONS
    assert cockpit_api.SOURCE_LABEL_TAXONOMY_VERSION == SOURCE_LABEL_TAXONOMY_VERSION
    assert query_orchestrator.SOURCE_LABEL_TAXONOMY_VERSION == SOURCE_LABEL_TAXONOMY_VERSION
    assert "financial_truth_numeric" in VALID_SOURCE_LABELS
    assert "insufficient_for_recent_news" in VALID_SOURCE_LABELS
    assert "financial_truth_numeric" not in ORCHESTRATOR_EVIDENCE_LABELS
    assert "insufficient_for_recent_news" not in ORCHESTRATOR_EVIDENCE_LABELS


def test_shared_label_helpers_normalize_order_and_cover_labels() -> None:
    labels = normalize_source_labels(
        ["context_only", "unknown_label", "claim_verified", "no_hit"]
    )

    assert labels == {"context_only", "claim_verified", "no_hit"}
    assert ordered_source_labels(labels) == ["no_hit", "claim_verified", "context_only"]
    assert primary_source_label(labels) == "no_hit"
    assert primary_source_label({"insufficient_for_recent_news"}) == "context_only"
    assert coverage_from_evidence_labels({"context_only", "financial_truth"}) == (
        "context_only"
    )


def test_legacy_backend_helpers_delegate_to_shared_taxonomy() -> None:
    assert query_orchestrator._normalize_evidence_labels(
        ["financial_truth_numeric", "unknown_label"]
    ) == set()
    assert cockpit_api._normalize_source_labels(
        ["insufficient_for_recent_news", "unknown_label"]
    ) == {"insufficient_for_recent_news"}


def test_deep_taxonomy_keeps_memory_context_non_authoritative() -> None:
    labels = {
        "claim_verified",
        "financial_truth",
        "financial_truth_numeric",
        "memory_context",
    }

    effective = effective_source_labels(labels)

    assert "context_only" in effective
    assert "memory_context" in effective
    assert "claim_verified" not in effective
    assert "financial_truth" not in effective
    assert "financial_truth_numeric" not in effective
    assert claim_verified_from_labels(labels) is False
    assert canonical_financial_truth_from_labels(labels) is False
    assert coverage_from_evidence_labels(labels) == "context_only"


def test_query_envelope_does_not_promote_memory_payload_claims_to_truth() -> None:
    envelope = query_orchestrator.build_evidence_envelope(
        plan=None,
        source_plan=("company_memory",),
        evidence={
            "company_memory": {
                "items": [{"text": "Management described margin pressure."}],
                "evidence_labels": [
                    "claim_verified",
                    "financial_truth",
                    "financial_truth_numeric",
                ],
            },
        },
    )

    source = envelope["sources"][0]

    assert source["claim_verified"] is False
    assert "claim_verified" not in source["evidence_labels"]
    assert "financial_truth" not in source["evidence_labels"]
    assert "financial_truth_numeric" not in source["evidence_labels"]
    assert "memory_context" in source["evidence_labels"]
    assert "context_only" in source["evidence_labels"]
    assert envelope["claim_verified_source_count"] == 0
    assert envelope["source_coverage_status"] == "context_only"


def test_tenn_chat_context_rows_cannot_claim_verify_memory_matches() -> None:
    labels = tenn_chat._labels_for_context_row(
        {
            "source_type": "company_memory",
            "source_name": "BHP memory",
            "published_at": "2026-01-01",
        },
        [
            {
                "source_name": "BHP memory",
                "date": "2026-01-01",
            }
        ],
    )

    assert "memory_context" in labels
    assert "context_only" in labels
    assert "claim_verified" not in labels
    assert "financial_truth" not in labels


def test_chat_evidence_guard_uses_deep_taxonomy_for_memory_context() -> None:
    categories = chat_evidence_guard.evidence_categories_for_source(
        {
            "source_id": "company_memory:BHP:margin",
            "kind": "context",
            "doc_type": "company_memory",
            "claim_verified": True,
            "evidence_labels": [
                "claim_verified",
                "financial_truth",
                "financial_truth_numeric",
                "memory_context",
            ],
            "snippet": "Canonical financial revenue was allegedly 123.",
        }
    )

    assert "claim_verified" not in categories
    assert "extracted_metric" not in categories
    assert "financial_statement" not in categories
    assert "context_only" in categories


def test_cockpit_source_defaults_apply_deep_taxonomy_to_memory_context() -> None:
    labels = cockpit_api._default_source_labels(
        {
            "source_id": "company_memory:BHP:margin",
            "source_type": "company_memory",
            "claim_verified": True,
            "supports_claim": True,
            "evidence_labels": [
                "claim_verified",
                "financial_truth",
                "financial_truth_numeric",
            ],
        },
        kind="context",
    )

    assert "memory_context" in labels
    assert "context_only" in labels
    assert "claim_verified" not in labels
    assert "financial_truth" not in labels
    assert "financial_truth_numeric" not in labels
