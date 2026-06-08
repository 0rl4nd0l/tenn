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
