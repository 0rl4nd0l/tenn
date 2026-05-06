from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import cockpit_api
from app.services.query_orchestrator import (
    SOURCE_LABEL_TAXONOMY_VERSION,
    build_evidence_envelope,
    build_plan,
)


def _source(envelope: dict, source_name: str) -> dict:
    for item in envelope["sources"]:
        if item["source_name"] == source_name:
            return item
    raise AssertionError(f"missing source envelope for {source_name}")


def test_orchestrator_envelope_source_item_is_cockpit_metadata_compatible() -> None:
    envelope = build_evidence_envelope(
        plan=build_plan("financial_fact"),
        source_plan=("financial_truth",),
        evidence={
            "financial_truth": {
                "status": "ok",
                "financials": [{"ticker": "BHP", "period_end": "2025-12-31"}],
            }
        },
    )

    normalized = cockpit_api._normalize_source_item(
        _source(envelope, "financial_truth"),
        kind="financial_truth",
    )

    assert envelope["source_label_taxonomy_version"] == SOURCE_LABEL_TAXONOMY_VERSION
    assert normalized is not None
    assert normalized["evidence_labels"] == ["financial_truth"]
    assert normalized["claim_verified"] is False


def test_orchestrator_envelope_preserves_a2m_local_news_as_context() -> None:
    envelope = build_evidence_envelope(
        plan=build_plan("mixed"),
        source_plan=("local_news",),
        evidence={
            "local_news": {
                "status": "ok",
                "items": [
                    {
                        "ticker": "A2M",
                        "title": "A2M recall update",
                        "source_type": "news",
                    }
                ],
            }
        },
    )

    labels = set(_source(envelope, "local_news")["evidence_labels"])
    assert "local_news_context" in labels
    assert "context_only" in labels
    assert "claim_verified" not in labels
    assert "financial_truth" not in labels


def test_unknown_source_type_defaults_to_unclassified_not_verified() -> None:
    envelope = build_evidence_envelope(
        plan=build_plan("mixed"),
        source_plan=("third_party_context",),
        evidence={
            "third_party_context": {
                "status": "ok",
                "items": [{"title": "Unclassified context"}],
            }
        },
    )

    source = _source(envelope, "third_party_context")
    assert "unknown_unclassified" in source["evidence_labels"]
    assert "context_only" in source["evidence_labels"]
    assert source["claim_verified"] is False
    assert "claim_verified" not in envelope["evidence_labels"]
