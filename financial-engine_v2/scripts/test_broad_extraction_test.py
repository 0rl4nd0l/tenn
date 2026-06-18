from broad_extraction_test import (
    SCALE_TABLE_PROVENANCE_REQUIRED_FIELDS,
    build_scale_table_provenance_harness_manifest,
    compute_summary,
    get_scale_table_provenance_harness_cases,
)


def test_compute_summary_preserves_source_noncandidate_reason():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": "validation_gate:source_noncandidate:meeting_or_proxy_notice",
                "ticker": "EQR",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {
        "source_noncandidate:meeting_or_proxy_notice": 1
    }


def test_compute_summary_preserves_director_interest_notice_reason():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": "validation_gate:source_noncandidate:director_interest_notice",
                "ticker": "EOS",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {
        "source_noncandidate:director_interest_notice": 1
    }


def test_compute_summary_keeps_other_validation_gates_grouped():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": "validation_gate:scale_unknown",
                "ticker": "WHC",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {"validation_gate:scale_unknown": 1}


def test_compute_summary_groups_accepted_output_risk_gate():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": (
                    "validation_gate:accepted_output_scale_magnitude_risk:"
                    "metric_revenue_ratio_high"
                ),
                "ticker": "EDU",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {
        "validation_gate:accepted_output_scale_magnitude_risk": 1
    }


def test_scale_table_provenance_harness_includes_required_fixed_cases():
    cases = get_scale_table_provenance_harness_cases()
    tickers = {case["ticker"] for case in cases}

    assert {"AZJ", "EDU", "WHC", "NIC", "DXC", "HUB", "LBL", "CTN"} <= tickers
    assert any(case["case_role"] == "clean_scale_known_control" for case in cases)
    assert any(case["case_role"] == "clean_noncandidate_control" for case in cases)


def test_scale_table_provenance_harness_defines_required_evidence_fields():
    cases = get_scale_table_provenance_harness_cases()
    required_case_keys = {
        "expected_document_class",
        "expected_status_or_gate",
        "source_path",
        "selected_table_or_page",
        "table_local_scale_evidence",
        "same_page_scale_evidence",
        "document_level_scale_evidence",
        "row_cell_provenance_fields_required",
        "forbidden_outputs",
        "current_behavior_expected_or_bug",
    }

    for case in cases:
        assert required_case_keys <= case.keys()
        assert set(SCALE_TABLE_PROVENANCE_REQUIRED_FIELDS) <= set(
            case["row_cell_provenance_fields_required"]
        )


def test_scale_table_provenance_manifest_keeps_audit_decision_fail_closed():
    manifest = build_scale_table_provenance_harness_manifest(
        generated_at="2026-06-07T00:00:00Z"
    )

    assert manifest["forbidden_actions"]["count24_rerun"] is True
    assert manifest["forbidden_actions"]["count32"] is True
    assert manifest["audit_questions"]["same_page_scale_propagation_required"] == ["AZJ"]
    assert "EDU" in manifest["audit_questions"]["must_fail_closed_mixed_or_unclean"]
    assert manifest["repair_decision"]["production_extraction_code_repair_made"] is False
    assert manifest["repair_decision"]["count24_rerun_justified"] is False
    assert manifest["repair_decision"]["count32_status"] == "blocked"


def test_broad_run_metric_provenance_audit_surfaces_payload_evidence():
    from broad_extraction_test import _build_metric_provenance_audit

    audit = _build_metric_provenance_audit(
        {
            "metrics": {"revenue": 100, "ebit": 10, "np_attributable": None},
            "row_refs": {"revenue": "Total revenue"},
            "provenance": {"revenue": "income_statement:page_4:Total revenue"},
            "metric_source_scales": {"revenue": "thousands"},
            "metric_scale_sources": {"revenue": "table"},
            "field_provenance": {
                "revenue": {
                    "source": "income_statement",
                    "table_label": "income_statement",
                    "page_number": 4,
                    "page_tag": "page_4",
                    "row_ref": "Total revenue",
                    "excerpt": "Revenue from contracts with customers",
                    "scale": "thousands",
                    "scale_source": "table",
                }
            },
        }
    )

    assert audit["provenance_available"] == ["revenue"]
    assert audit["provenance_missing"] == ["ebit"]
    assert audit["metric_provenance"]["revenue"]["row_ref"] == "Total revenue"
    assert (
        audit["metric_provenance"]["revenue"]["excerpt"]
        == "Revenue from contracts with customers"
    )
    assert audit["metric_provenance"]["revenue"]["page_number"] == 4
    assert audit["metric_provenance"]["revenue"]["table_label"] == "income_statement"
    assert audit["metric_provenance"]["revenue"]["metric_source_scale"] == "thousands"
    assert audit["metric_provenance"]["revenue"]["provenance_available"] is True
    assert audit["metric_provenance"]["ebit"]["provenance_missing"] is True
    assert "np_attributable" not in audit["metric_provenance"]


def test_broad_run_scale_magnitude_risk_flags_are_machine_readable():
    from broad_extraction_test import _build_scale_magnitude_risk

    risk = _build_scale_magnitude_risk(
        {
            "period_type": "H",
            "period_end": "2025-12-31",
            "scale": "millions",
            "currency": "AUD",
            "metrics": {
                "revenue": 20_000_000,
                "np_attributable": 600_000_000_001,
                "cash_end": 400_000_000,
            },
            "metric_source_scales": {
                "revenue": "thousands",
                "np_attributable": "millions",
                "cash_end": "thousands",
            },
        },
        accepted_output=True,
    )

    flags = {flag["code"]: flag for flag in risk["flags"]}

    assert risk["accepted_output"] is True
    assert risk["risk_level"] == "review"
    assert "metric_exceeds_native_sanity_cap" in flags
    assert flags["metric_exceeds_native_sanity_cap"]["metric"] == "np_attributable"
    assert "mixed_metric_source_scales" in flags
    assert "payload_scale_differs_from_metric_source_scale" in flags
    assert "metric_revenue_ratio_high" in flags


def test_broad_run_review_risk_fails_closed_for_accepted_output():
    from broad_extraction_test import _accepted_output_risk_gate_error

    error = _accepted_output_risk_gate_error(
        {
            "accepted_output": True,
            "risk_level": "review",
            "flag_codes": [
                "metric_revenue_ratio_high",
                "metric_revenue_ratio_high",
                "mixed_metric_source_scales",
            ],
            "flags": [],
        }
    )

    assert error == (
        "validation_gate:accepted_output_scale_magnitude_risk:"
        "metric_revenue_ratio_high,mixed_metric_source_scales"
    )


def test_broad_run_info_risk_remains_accepted_for_audit_visibility():
    from broad_extraction_test import _accepted_output_risk_gate_error

    error = _accepted_output_risk_gate_error(
        {
            "accepted_output": True,
            "risk_level": "info",
            "flag_codes": ["metric_source_scale_missing"],
            "flags": [],
        }
    )

    assert error is None


def test_broad_run_review_risk_does_not_override_already_failed_rows():
    from broad_extraction_test import _accepted_output_risk_gate_error

    error = _accepted_output_risk_gate_error(
        {
            "accepted_output": False,
            "risk_level": "review",
            "flag_codes": ["metric_revenue_ratio_high"],
            "flags": [],
        }
    )

    assert error is None


def test_broad_run_summary_rolls_up_provenance_and_risk_flags():
    summary = compute_summary(
        [
            {
                "status": "ok",
                "error": None,
                "ticker": "AAA",
                "metrics": {"revenue": 100, "ebit": 10, "np_attributable": None},
                "non_null_metrics": 2,
                "elapsed_s": 1.0,
                "scale": "millions",
                "sanity": {},
                "provenance_audit": {
                    "metrics_with_provenance": ["revenue"],
                    "metrics_missing_provenance": ["ebit"],
                },
                "risk_flags": [],
            },
            {
                "status": "ok",
                "error": None,
                "ticker": "BBB",
                "metrics": {"revenue": 999_999_999_999_999},
                "non_null_metrics": 1,
                "elapsed_s": 1.0,
                "scale": "millions",
                "sanity": {},
                "provenance_audit": {
                    "metrics_with_provenance": ["revenue"],
                    "metrics_missing_provenance": [],
                },
                "risk_flags": [
                    "metric_exceeds_native_sanity_cap",
                    "metric_revenue_ratio_high",
                ],
            },
        ]
    )

    assert summary["provenance_coverage"]["metrics_with_provenance"] == {
        "revenue": 2
    }
    assert summary["provenance_coverage"]["metrics_missing_provenance"] == {"ebit": 1}
    assert summary["provenance_coverage"]["documents_with_missing_provenance"] == 1
    assert summary["risk_flag_distribution"] == {
        "metric_exceeds_native_sanity_cap": 1,
        "metric_revenue_ratio_high": 1,
    }
    assert summary["risk_flagged_documents"] == 1
