from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import cockpit_api
from app.services import query_orchestrator
from shared.evidence_labels import (
    ORCHESTRATOR_EVIDENCE_LABELS,
    SOURCE_LABEL_DEFINITIONS,
    SOURCE_LABEL_TAXONOMY_VERSION,
    VALID_SOURCE_LABELS,
    coverage_from_evidence_labels,
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
    assert primary_source_label({"insufficient_for_recent_news"}) == (
        "unknown_unclassified"
    )
    assert coverage_from_evidence_labels({"context_only", "financial_truth"}) == (
        "financial_truth"
    )


def test_legacy_backend_helpers_delegate_to_shared_taxonomy() -> None:
    assert query_orchestrator._normalize_evidence_labels(
        ["financial_truth_numeric", "unknown_label"]
    ) == set()
    assert cockpit_api._normalize_source_labels(
        ["insufficient_for_recent_news", "unknown_label"]
    ) == {"insufficient_for_recent_news"}
