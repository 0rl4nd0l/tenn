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
    assert run_summary["projected_medium_target_rows"] == 2
    assert run_summary["projected_strong_or_medium_target_rows"] == 4
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

    residual = scorecard["sampled_residual_adjudication"]
    assert residual["sample_limit_per_bucket"] == 5
    assert residual["source_buckets"]["weak_rows"]["population_count"] == 1
    assert residual["source_buckets"]["coherence_rejected_rows"]["population_count"] == 1
    assert residual["source_buckets"]["collapse_blocked_rows"]["population_count"] == 3
    assert residual["source_buckets"]["unsupported_rows_near_canonical"][
        "population_count"
    ] == 1
    assert residual["overall_sampled_label_distribution"] == {
        "ambiguous": 2,
        "should_project_to_family": 2,
        "truly_unsupported": 2,
    }

    freeze = scorecard["bridge_freeze_assessment"]
    assert freeze["prior_run_available"] is False
    assert freeze["status"] == "insufficient_baseline"
    assert freeze["freeze_recommended"] is None
    assert freeze["coverage_signals"][0]["name"] == "projected_strong_target_rows"

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
    assert "Sampled Residual Adjudication" in summary_md
    assert "Bridge Freeze Assessment" in summary_md


def test_residual_adjudication_and_freeze_rule_can_recommend_freeze():
    datapoints = [
        _datapoint(
            "doc-x",
            "doc-x__weak_supplemental",
            "Potash",
            "10",
            context_text=(
                "Underlying EBITDA – Segment | in depreciation, | amortisation and | "
                "impairments1 | Underlying | EBITDA | Potash"
            ),
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
        _datapoint(
            "doc-x",
            "doc-x__weak_target",
            "Payments for",
            "-",
            context_text=(
                "Cash flows from operating activities | Receipts from customers | "
                "Payments for"
            ),
            raw_scale="thousands",
            unit_type="currency",
            currency="AUD",
        ),
        _datapoint(
            "doc-x",
            "doc-x__coherence_rejected",
            "Underlying EBITDA margin",
            "12%",
            context_text="Underlying EBITDA margin",
            unit_type="currency",
        ),
        _datapoint(
            "doc-x",
            "doc-x__collapse_blocked_target",
            "Underlying EBIT",
            "50",
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
        _datapoint(
            "doc-x",
            "doc-x__unsupported_near_canonical",
            "customers",
            "100",
            context_text="Revenue from contracts with customers",
            raw_scale="millions",
            unit_type="currency",
            currency="USD",
        ),
    ]
    prior_scorecard = {
        "run_summary": {
            "projected_strong_target_rows": 0,
            "projected_strong_or_medium_target_rows": 1,
            "auto_collapse_safe_distribution": {"false": 5, "true": 0},
        },
        "ambiguity_summary": {
            "weak_mappings": 2,
            "coherence_rejected_rows": 1,
            "collapse_blocked_rows": 3,
            "unsupported_rows": 2,
            "supplemental_rows": 0,
        },
        "coarse_canonical_comparison": {
            "documents_with_both_surfaces": 0,
        },
        "sampled_residual_adjudication": {
            "overall_sampled_label_distribution": {
                "ambiguous": 1,
                "should_project_to_family": 1,
            }
        },
    }

    scorecard = build_exhaustive_projection_diagnostic(
        datapoints,
        previous_scorecard=prior_scorecard,
        sample_limit=5,
    )

    residual = scorecard["sampled_residual_adjudication"]
    labels = residual["overall_sampled_label_distribution"]
    assert labels["supplemental"] >= 1
    assert labels["ambiguous"] >= 1
    assert labels["truly_unsupported"] >= 1
    assert labels["should_project_to_family"] >= 1

    freeze = scorecard["bridge_freeze_assessment"]
    assert freeze["prior_run_available"] is True
    assert freeze["material_coverage_increase"] is False
    assert freeze["freeze_recommended"] is True
    assert freeze["status"] == "freeze_bridge_for_now"
    assert freeze["bucket_or_label_churn_magnitude"] > 0
