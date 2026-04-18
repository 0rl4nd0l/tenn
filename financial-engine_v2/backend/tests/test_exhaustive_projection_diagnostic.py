from __future__ import annotations

import json

from app.services.exhaustive_projection_diagnostic import (
    CANONICAL_GATE_LABEL,
    PROVISIONAL_LABEL,
    build_exhaustive_projection_diagnostic,
    write_exhaustive_projection_artifacts,
)


def _all_keys(payload: object) -> set[str]:
    if isinstance(payload, dict):
        keys = set(payload)
        for value in payload.values():
            keys |= _all_keys(value)
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for item in payload:
            keys |= _all_keys(item)
        return keys
    return set()


def _datapoint(
    document_id: str,
    datapoint_id: str,
    row_label: str,
    raw_value: str,
    *,
    context_text: str = "",
    raw_scale: str | None = None,
    unit_type: str | None = None,
    currency: str | None = None,
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "datapoint_id": datapoint_id,
        "row_label": row_label,
        "context_text": context_text,
        "raw_value": raw_value,
        "raw_scale": raw_scale,
        "unit_type": unit_type,
        "currency": currency,
    }


def test_projection_scorecard_counts_and_comparison_are_deterministic(tmp_path):
    datapoints = [
        _datapoint(
            "doc-a",
            "doc-a__1",
            "Revenue",
            "100",
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
        _datapoint(
            "doc-a",
            "doc-a__2",
            "Underlying EBIT",
            "50",
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
        _datapoint(
            "doc-a",
            "doc-a__3",
            "Dividend per share (cents)",
            "12",
            context_text="Capital management | Dividend per share (cents)",
            unit_type="per_share",
        ),
        _datapoint(
            "doc-a",
            "doc-a__4",
            "Net debt",
            "7%",
            context_text="Movement in net debt by category | (7%)",
            unit_type="percent_or_ratio",
        ),
        _datapoint(
            "doc-a",
            "doc-a__5",
            "Total",
            "90",
            context_text="Revenue | breakdown | Total",
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
        _datapoint(
            "doc-a",
            "doc-a__6",
            "Ordinary shares issued and fully paid",
            "197631816",
            unit_type="currency",
        ),
        _datapoint(
            "doc-b",
            "doc-b__1",
            "Profit attributable to members profit after tax",
            "33",
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
    ]
    canonical_presence = {
        "doc-a": ("revenue", "shares_outstanding"),
        "doc-b": ("np_attributable",),
    }

    scorecard = build_exhaustive_projection_diagnostic(
        datapoints,
        canonical_family_presence_by_document=canonical_presence,
        exhaustive_audit_summary={
            "generated_at_utc": "2026-04-10T15:12:36+00:00",
            "documents_processed": 2,
            "datapoints": 7,
        },
        sample_limit=5,
    )

    assert scorecard["artifact_kind"] == "exhaustive_projection_diagnostic_scorecard"
    assert scorecard["provisional_label"] == PROVISIONAL_LABEL
    assert scorecard["canonical_release_gate"] == CANONICAL_GATE_LABEL
    assert scorecard["matcher_like_comparison_performed"] is False

    run_summary = scorecard["run_summary"]
    assert run_summary["datapoints_processed"] == 7
    assert run_summary["documents_processed"] == 2
    assert run_summary["projected_strong_target_rows"] == 2
    assert run_summary["projected_supplemental_rows"] == 1
    assert run_summary["unsupported_rows"] == 1
    assert run_summary["family_distribution"] == {
        "__none__": 2,
        "ebit": 1,
        "np_attributable": 1,
        "revenue": 2,
        "shares_outstanding": 1,
    }
    assert run_summary["unit_type_distribution"] == {
        "count": 1,
        "currency": 4,
        "per_share": 1,
        "percentage": 1,
    }
    assert run_summary["confidence_distribution"] == {
        "medium": 2,
        "strong": 2,
        "supplemental": 1,
        "unsupported": 1,
        "weak": 1,
    }
    assert run_summary["auto_collapse_safe_distribution"] == {
        "false": 5,
        "true": 2,
    }

    ambiguity = scorecard["ambiguity_summary"]
    assert ambiguity["unsupported_rows"] == 1
    assert ambiguity["weak_mappings"] == 1
    assert ambiguity["medium_mappings"] == 2
    assert ambiguity["supplemental_rows"] == 1
    assert ambiguity["unit_conflict_rows"] == 1
    assert ambiguity["coherence_rejected_rows"] == 1
    assert ambiguity["collapse_blocked_rows"] == 3
    assert ambiguity["qualifier_blocked_rows"] == 1

    coverage = scorecard["projected_canonical_like_coverage"]
    assert coverage["totals_by_family"] == {
        "revenue": 1,
        "shares_outstanding": 1,
    }
    assert coverage["counts_by_document"] == [
        {
            "document_id": "doc-a",
            "strong_target_row_count": 2,
            "strong_target_row_counts": {
                "revenue": 1,
                "shares_outstanding": 1,
            },
            "supported_target_row_counts": {
                "ebit": 1,
                "revenue": 2,
                "shares_outstanding": 1,
            },
        },
        {
            "document_id": "doc-b",
            "strong_target_row_count": 0,
            "strong_target_row_counts": {},
            "supported_target_row_counts": {
                "np_attributable": 1,
            },
        },
    ]

    suspicious = scorecard["suspicious_cases"]
    assert suspicious["strong_signal_but_not_auto_collapse_safe"]["count"] == 2
    assert suspicious["context_text_appears_important_for_mapping"]["count"] == 1
    assert suspicious["could_be_confused_with_another_family"]["count"] == 1
    assert suspicious["could_be_confused_with_another_family"]["samples"][0][
        "candidate_families"
    ] == ["net_income", "np_attributable"]

    coarse = scorecard["coarse_canonical_comparison"]
    assert coarse["available"] is True
    assert coarse["documents_with_both_surfaces"] == 2
    assert coarse["canonical_only_documents"] == []
    assert coarse["projection_only_documents"] == []
    assert coarse["by_family"] == [
        {
            "family": "ebit",
            "canonical_doc_presence_count": 0,
            "projected_strong_doc_presence_count": 0,
            "projected_strong_row_count": 0,
            "projected_supported_row_count": 1,
        },
        {
            "family": "np_attributable",
            "canonical_doc_presence_count": 1,
            "projected_strong_doc_presence_count": 0,
            "projected_strong_row_count": 0,
            "projected_supported_row_count": 1,
        },
        {
            "family": "revenue",
            "canonical_doc_presence_count": 1,
            "projected_strong_doc_presence_count": 1,
            "projected_strong_row_count": 1,
            "projected_supported_row_count": 2,
        },
        {
            "family": "shares_outstanding",
            "canonical_doc_presence_count": 1,
            "projected_strong_doc_presence_count": 1,
            "projected_strong_row_count": 1,
            "projected_supported_row_count": 1,
        },
    ]

    keys = _all_keys(scorecard)
    assert "precision_strict" not in keys
    assert "recall_family" not in keys
    assert "matched_exact" not in keys

    artifact_paths = write_exhaustive_projection_artifacts(scorecard, tmp_path)
    payload = json.loads(artifact_paths["scorecard_json"].read_text(encoding="utf-8"))
    summary_md = artifact_paths["summary_markdown"].read_text(encoding="utf-8")

    assert payload["artifact_paths"]["scorecard_json"].endswith(
        "projection_scorecard.json"
    )
    assert payload["artifact_paths"]["summary_markdown"].endswith(
        "projection_summary.md"
    )
    assert PROVISIONAL_LABEL in summary_md
    assert CANONICAL_GATE_LABEL in summary_md
    assert "does not implement tuple matching" in summary_md
