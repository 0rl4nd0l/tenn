import json
from pathlib import Path

from app.services.extraction_gold_eval_scorecard import (
    CoverageSupportStatus,
    build_confirmed_metric_coverage_scorecard,
    get_scorecard_profiles,
    metric_mapping_table,
)


def _write_fixture(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_fixture(**overrides):
    payload = {
        "_source": "Hand-verified from source PDF page 1.",
        "_verification": "hand-verified",
        "_verification_confidence": "high",
        "document_id": "confirmed_doc",
        "pdf_path": "data/asx/docs/TEST/report.pdf",
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "revenue": 100.0,
            "operating_cash_flow": 25.0,
        },
        "expected_nulls": ["net_debt"],
        "tolerances": {"revenue": 0.01, "operating_cash_flow": 0.01},
    }
    payload.update(overrides)
    return payload


def test_profile_metadata_preserves_existing_scorecard_semantics():
    profiles = get_scorecard_profiles()

    assert profiles["canonical_core"]["expected_document_count"] == 10
    assert profiles["canonical_core"]["expected_metric_checks"] == 24
    assert profiles["canonical_core"]["mutates_canonical_trust"] is False
    assert profiles["expanded_required"]["expected_document_count"] == 15
    assert profiles["expanded_required"]["expected_metric_checks"] == 39
    assert profiles["expanded_required"]["mutates_canonical_trust"] is False
    assert profiles["confirmed_metric_coverage"]["mutates_canonical_trust"] is False


def test_metric_name_mapping_is_deterministic_and_schema_supported():
    rows = {row["fixture_name"]: row for row in metric_mapping_table()}

    assert rows["revenue"]["canonical_field"] == "revenue"
    assert rows["operating_cash_flow"]["canonical_field"] == "operating_cf"
    assert rows["operating_cf"]["canonical_field"] == "operating_cf"
    assert rows["shares_outstanding"]["canonical_field"] == "shares_outstanding"
    assert rows["operating_cf"]["schema_supported"] is True
    assert rows["capex"]["evaluator_supported"] is True
    assert rows["net_debt"]["ambiguity_risk"].startswith("medium:")


def test_confirmed_metric_coverage_inventory_classifies_non_gold_inputs(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")

    _write_fixture(fixtures_dir / "confirmed.json", _base_fixture())
    _write_fixture(
        fixtures_dir / "candidate.json",
        _base_fixture(
            document_id="candidate_doc",
            _source="Claude API verified from source PDF page 1.",
            _verification="claude-api-sonnet",
            _verification_confidence="lower - not hand-verified",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "missing_source.json",
        _base_fixture(
            document_id="missing_source_doc",
            _source="",
            _verification="",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "ambiguous.json",
        _base_fixture(
            document_id="ambiguous_doc",
            metrics={"capex": -10.0},
            expected_nulls=[],
            notes={"capex": "Capex convention unresolved for this fixture."},
        ),
    )
    _write_fixture(
        fixtures_dir / "unsupported.json",
        _base_fixture(
            document_id="unsupported_doc",
            metrics={"ebitda": 200.0},
            expected_nulls=[],
        ),
    )

    scorecard = build_confirmed_metric_coverage_scorecard(
        fixtures_dir,
        financial_engine_root=tmp_path,
    )

    assert scorecard["profile"] == "confirmed_metric_coverage"
    assert scorecard["total_fixture_count"] == 5
    assert scorecard["scored_metric_expectations"] == 3
    assert scorecard["candidate_review_required_count"] == 1
    assert scorecard["missing_source_evidence_count"] == 1
    assert scorecard["unsupported_metric_count"] == 1
    assert scorecard["ambiguous_metric_count"] == 1
    assert scorecard["status_summary"]["not_evaluated"] == 3

    by_metric = {
        (row["document_id"], row["metric_name"]): row
        for row in scorecard["metric_expectations"]
    }
    assert by_metric[("candidate_doc", "revenue")]["support_status"] == (
        CoverageSupportStatus.CANDIDATE_REVIEW_REQUIRED.value
    )
    assert by_metric[("missing_source_doc", "revenue")]["support_status"] == (
        CoverageSupportStatus.MISSING_SOURCE_EVIDENCE.value
    )
    assert by_metric[("ambiguous_doc", "capex")]["support_status"] == (
        CoverageSupportStatus.AMBIGUOUS_LABEL.value
    )
    assert by_metric[("unsupported_doc", "ebitda")]["support_status"] == (
        CoverageSupportStatus.UNSUPPORTED_SCHEMA.value
    )
    assert by_metric[("confirmed_doc", "net_debt")]["expectation_type"] == (
        "expected_null"
    )


def test_confirmed_metric_coverage_scores_only_confirmed_labels(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(fixtures_dir / "confirmed.json", _base_fixture())
    _write_fixture(
        fixtures_dir / "candidate.json",
        _base_fixture(
            document_id="candidate_doc",
            _verification="claude-opus",
            _verification_confidence="high but model-derived",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )

    scorecard = build_confirmed_metric_coverage_scorecard(
        fixtures_dir,
        {
            "confirmed_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {
                    "revenue": 100.0,
                    "operating_cf": 25.0,
                    "net_debt": None,
                },
            },
            "candidate_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
            },
        },
        financial_engine_root=tmp_path,
    )

    assert scorecard["status_summary"]["correct"] == 3
    assert scorecard["status_summary"]["not_evaluated"] == 0
    by_metric = {
        (row["document_id"], row["metric_name"]): row
        for row in scorecard["metric_expectations"]
    }
    assert by_metric[("confirmed_doc", "operating_cash_flow")][
        "canonical_field"
    ] == "operating_cf"
    assert by_metric[("confirmed_doc", "net_debt")]["evaluation_status"] == "correct"
    assert by_metric[("candidate_doc", "revenue")]["evaluation_status"] is None


def test_confirmed_metric_coverage_uses_fixture_labels_not_extractor_output_as_gold(
    tmp_path,
):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(
        fixtures_dir / "confirmed.json",
        _base_fixture(metrics={"revenue": 100.0}, expected_nulls=[]),
    )

    scorecard = build_confirmed_metric_coverage_scorecard(
        fixtures_dir,
        {
            "confirmed_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 999.0},
            },
        },
        financial_engine_root=tmp_path,
    )

    metric = scorecard["metric_expectations"][0]
    assert metric["expected_value"] == 100.0
    assert metric["actual_value"] == 999.0
    assert metric["evaluation_status"] == "wrong"
