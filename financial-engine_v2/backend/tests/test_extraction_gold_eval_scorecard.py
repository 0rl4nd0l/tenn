import hashlib
import json
from pathlib import Path

from app.services.extraction_gold_eval_scorecard import (
    CoverageSupportStatus,
    MetricContractStatus,
    PayloadScoreStatus,
    SourceAssetResolutionStatus,
    TerminalExtractionCandidateClass,
    TerminalExtractionRecommendedAction,
    build_confirmed_metric_coverage_scorecard,
    build_confirmed_metric_payload_scorecard,
    build_pre_persistence_scorecard_gate,
    build_terminal_extraction_candidate_manifest,
    build_metric_contract_parity_matrix,
    classify_terminal_extraction_candidate,
    get_scorecard_profiles,
    load_source_asset_manifest,
    metric_mapping_table,
    metric_contract_status_names,
    resolve_source_asset_manifest,
    resolve_source_asset_manifest_payload,
    terminal_extraction_candidate_manifest_to_csv,
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


SOURCE_ASSET_MANIFEST = (
    Path(__file__).parent
    / "eval_source_assets"
    / "confirmed_metric_coverage_source_assets.json"
)


def _source_asset_manifest(tmp_path: Path, assets: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "manifest_id": "synthetic_source_assets_v1",
        "dataset": "synthetic_source_assets",
        "asset_policy": {
            "metadata_only": True,
            "raw_pdfs_committed": False,
            "default_ci_requires_raw_pdfs": False,
            "source_openability_counts_as_metric_correctness": False,
        },
        "source_roots": [
            {
                "root_id": "synthetic_docs",
                "path": str(tmp_path / "docs"),
            }
        ],
        "assets": assets,
    }


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
    assert rows["revenue"]["ontology_version"] == "metric_ontology_v1"
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


def _empty_contract_matrix(tmp_path: Path) -> dict:
    confirmed_dir = tmp_path / "confirmed"
    real_gold_dir = tmp_path / "real_gold"
    confirmed_dir.mkdir()
    real_gold_dir.mkdir()
    return build_metric_contract_parity_matrix(
        confirmed_fixtures_dir=confirmed_dir,
        real_gold_fixtures_dir=real_gold_dir,
    )


def _contract_rows(matrix: dict) -> dict[str, dict]:
    return {row["family"]: row for row in matrix["metric_rows"]}


def test_metric_contract_parity_classifies_persisted_only_fields(tmp_path):
    matrix = _empty_contract_matrix(tmp_path)
    rows = _contract_rows(matrix)

    assert matrix["metric_ontology_version"] == "metric_ontology_v1"
    assert rows["total_equity"]["status"] == MetricContractStatus.PERSISTED_ONLY.value
    assert rows["total_equity"]["persisted"] is True
    assert rows["total_equity"]["extractor_supported"] is False
    assert rows["total_equity"]["evaluator_supported"] is False
    assert rows["total_equity"]["canonical_use_allowed"] is False

    assert rows["interest_expense"]["status"] == (
        MetricContractStatus.PERSISTED_ONLY.value
    )
    assert rows["interest_expense"]["persisted"] is True
    assert rows["interest_expense"]["extractor_supported"] is False
    assert rows["interest_expense"]["canonical_use_allowed"] is False

    assert matrix["policy_assertions"]["total_equity_not_promoted"] is True
    assert matrix["policy_assertions"]["interest_expense_not_promoted"] is True


def test_metric_contract_parity_classifies_supported_fields(tmp_path):
    matrix = _empty_contract_matrix(tmp_path)
    rows = _contract_rows(matrix)

    for family in (
        "revenue",
        "operating_cash_flow",
        "net_debt",
        "cash",
        "capex",
        "np_attributable",
    ):
        assert rows[family]["status"] == MetricContractStatus.SUPPORTED.value
        assert rows[family]["persisted"] is True
        assert rows[family]["extractor_supported"] is True
        assert rows[family]["evaluator_supported"] is True
        assert rows[family]["canonical_use_allowed"] is True

    assert rows["operating_cash_flow"]["canonical_field"] == "operating_cf"
    assert rows["cash"]["canonical_field"] == "cash_end"


def test_metric_contract_parity_classifies_planned_unsupported_and_internal_fields(
    tmp_path,
):
    matrix = _empty_contract_matrix(tmp_path)
    rows = _contract_rows(matrix)

    assert rows["eps"]["status"] == MetricContractStatus.PLANNED.value
    assert rows["dividends"]["status"] == MetricContractStatus.PLANNED.value
    assert rows["total_assets"]["status"] == MetricContractStatus.UNSUPPORTED.value
    assert rows["finance_costs"]["status"] == (
        MetricContractStatus.AMBIGUOUS_REQUIRES_POLICY.value
    )
    assert rows["debt_borrowings"]["status"] == MetricContractStatus.INTERNAL_ONLY.value
    assert rows["debt_borrowings"]["internal_extractor_supported"] is True
    assert rows["debt_borrowings"]["canonical_use_allowed"] is False


def test_metric_contract_parity_broad_catalogue_is_not_automatically_canonical(
    tmp_path,
):
    matrix = _empty_contract_matrix(tmp_path)
    rows = _contract_rows(matrix)

    for family in ("eps", "dividends", "finance_costs", "total_assets"):
        assert rows[family]["canonical_use_allowed"] is False
        assert rows[family]["extractor_supported"] is False
        assert rows[family]["evaluator_supported"] is False

    assert matrix["policy_assertions"][
        "broad_catalogue_not_automatically_canonical"
    ] is True
    assert MetricContractStatus.PERSISTED_ONLY.value in metric_contract_status_names()


def test_metric_contract_parity_marks_uncontracted_fixture_metrics_gold_only(
    tmp_path,
):
    confirmed_dir = tmp_path / "confirmed"
    real_gold_dir = tmp_path / "real_gold"
    confirmed_dir.mkdir()
    real_gold_dir.mkdir()
    _write_fixture(
        confirmed_dir / "gold_only.json",
        _base_fixture(metrics={"ebitda": 123.0}, expected_nulls=[]),
    )

    matrix = build_metric_contract_parity_matrix(
        confirmed_fixtures_dir=confirmed_dir,
        real_gold_fixtures_dir=real_gold_dir,
    )
    rows = _contract_rows(matrix)

    assert rows["ebitda"]["status"] == MetricContractStatus.GOLD_ONLY.value
    assert rows["ebitda"]["gold_or_confirmed_expectation_count"] == 1
    assert rows["ebitda"]["canonical_use_allowed"] is False


def test_confirmed_payload_scorecard_no_actual_payload_is_not_evaluated(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(
        fixtures_dir / "confirmed.json",
        _base_fixture(metrics={"revenue": 100.0}, expected_nulls=[]),
    )

    scorecard = build_confirmed_metric_payload_scorecard(
        fixtures_dir,
        financial_engine_root=tmp_path,
    )

    row = scorecard["metric_results"][0]
    assert row["source_pdf_exists"] is True
    assert row["source_openability_is_correctness"] is False
    assert row["result_class"] == (
        PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL.value
    )
    assert row["score"] is None
    assert scorecard["result_class_summary"][
        PayloadScoreStatus.PRESENT_CORRECT.value
    ] == 0


def test_confirmed_payload_scorecard_scores_value_and_missing_metric_cases(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(fixtures_dir / "confirmed.json", _base_fixture())

    scorecard = build_confirmed_metric_payload_scorecard(
        fixtures_dir,
        {
            "confirmed_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 90.0},
                "evidence": {"revenue": {"page": 1}},
            }
        },
        financial_engine_root=tmp_path,
    )

    by_metric = {row["metric_name"]: row for row in scorecard["metric_results"]}
    assert by_metric["revenue"]["result_class"] == (
        PayloadScoreStatus.PRESENT_WRONG_VALUE.value
    )
    assert by_metric["operating_cash_flow"]["result_class"] == (
        PayloadScoreStatus.MISSING_EXPECTED_METRIC.value
    )


def test_confirmed_payload_scorecard_separates_period_unit_and_evidence(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(
        fixtures_dir / "wrong_period.json",
        _base_fixture(
            document_id="wrong_period_doc",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "wrong_scale.json",
        _base_fixture(
            document_id="wrong_scale_doc",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "wrong_period_type.json",
        _base_fixture(
            document_id="wrong_period_type_doc",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "missing_evidence.json",
        _base_fixture(
            document_id="missing_evidence_doc",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )

    scorecard = build_confirmed_metric_payload_scorecard(
        fixtures_dir,
        {
            "wrong_period_doc": {
                "period_type": "H",
                "period_end": "2025-06-30",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
                "evidence": {"revenue": {"page": 1}},
            },
            "wrong_scale_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "thousands",
                "metrics": {"revenue": 100.0},
                "evidence": {"revenue": {"page": 1}},
            },
            "wrong_period_type_doc": {
                "period_type": "A",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
                "evidence": {"revenue": {"page": 1}},
            },
            "missing_evidence_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
            },
        },
        financial_engine_root=tmp_path,
    )

    by_doc = {row["document_id"]: row for row in scorecard["metric_results"]}
    assert by_doc["wrong_period_doc"]["result_class"] == (
        PayloadScoreStatus.WRONG_PERIOD.value
    )
    assert by_doc["wrong_scale_doc"]["result_class"] == (
        PayloadScoreStatus.WRONG_UNIT_CURRENCY_SCALE.value
    )
    assert by_doc["wrong_period_type_doc"]["result_class"] == (
        PayloadScoreStatus.WRONG_PERIOD.value
    )
    assert by_doc["missing_evidence_doc"]["result_class"] == (
        PayloadScoreStatus.MISSING_EVIDENCE.value
    )


def test_confirmed_payload_scorecard_abstains_or_quarantines_unscored_labels(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(
        fixtures_dir / "unsupported.json",
        _base_fixture(
            document_id="unsupported_doc",
            metrics={"ebitda": 200.0},
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

    scorecard = build_confirmed_metric_payload_scorecard(
        fixtures_dir,
        {
            "unsupported_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {},
            },
            "ambiguous_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"capex": -10.0},
            },
        },
        financial_engine_root=tmp_path,
    )

    by_doc = {row["document_id"]: row for row in scorecard["metric_results"]}
    assert by_doc["unsupported_doc"]["result_class"] == (
        PayloadScoreStatus.UNSUPPORTED_CORRECTLY_ABSTAINED.value
    )
    assert by_doc["ambiguous_doc"]["result_class"] == (
        PayloadScoreStatus.AMBIGUOUS_QUARANTINED.value
    )


def test_pre_persistence_scorecard_gate_passes_correct_and_allowed_abstention(
    tmp_path,
):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(fixtures_dir / "confirmed.json", _base_fixture())
    _write_fixture(
        fixtures_dir / "unsupported.json",
        _base_fixture(
            document_id="unsupported_doc",
            metrics={"ebitda": 200.0},
            expected_nulls=[],
        ),
    )

    scorecard = build_confirmed_metric_payload_scorecard(
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
                "evidence": {
                    "revenue": {"page": 1},
                    "operating_cf": {"page": 1},
                },
            },
            "unsupported_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {},
            },
        },
        financial_engine_root=tmp_path,
    )

    gate = build_pre_persistence_scorecard_gate(scorecard)

    assert gate["artifact_type"] == "pre_persistence_scorecard_gate_v1"
    assert gate["gate_status"] == "pass"
    assert gate["decision"] == "operator_review_eligible"
    assert gate["canonical_write_allowed"] is False
    assert gate["broad_backfill_authorized"] is False
    assert gate["operator_approval_required_for_canary"] is True
    assert gate["allowed_noncanonical_abstention_count"] == 1
    assert gate["blockers"] == []
    assert gate["blocking_examples"] == []


def test_pre_persistence_scorecard_gate_blocks_bad_and_missing_actuals(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(
        fixtures_dir / "wrong_value.json",
        _base_fixture(
            document_id="wrong_value_doc",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "wrong_period.json",
        _base_fixture(
            document_id="wrong_period_doc",
            metrics={"revenue": 100.0},
            expected_nulls=[],
        ),
    )
    _write_fixture(
        fixtures_dir / "missing_actual.json",
        _base_fixture(
            document_id="missing_actual_doc",
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

    scorecard = build_confirmed_metric_payload_scorecard(
        fixtures_dir,
        {
            "wrong_value_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 90.0},
                "evidence": {"revenue": {"page": 1}},
            },
            "wrong_period_doc": {
                "period_type": "A",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
                "evidence": {"revenue": {"page": 1}},
            },
            "ambiguous_doc": {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"capex": -10.0},
            },
        },
        financial_engine_root=tmp_path,
    )

    gate = build_pre_persistence_scorecard_gate(scorecard)
    blockers = {blocker["code"]: blocker["count"] for blocker in gate["blockers"]}

    assert gate["gate_status"] == "fail"
    assert gate["decision"] == "blocked"
    assert gate["canonical_write_allowed"] is False
    assert gate["broad_backfill_authorized"] is False
    assert blockers[PayloadScoreStatus.PRESENT_WRONG_VALUE.value] == 1
    assert blockers[PayloadScoreStatus.WRONG_PERIOD.value] == 1
    assert blockers[PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL.value] == 1
    assert blockers[PayloadScoreStatus.AMBIGUOUS_QUARANTINED.value] == 1
    assert {example["document_id"] for example in gate["blocking_examples"]} == {
        "ambiguous_doc",
        "missing_actual_doc",
        "wrong_period_doc",
        "wrong_value_doc",
    }


def test_pre_persistence_scorecard_gate_blocks_without_actual_payloads(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    pdf_path = tmp_path / "data" / "asx" / "docs" / "TEST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_fixture(
        fixtures_dir / "confirmed.json",
        _base_fixture(metrics={"revenue": 100.0}, expected_nulls=[]),
    )

    scorecard = build_confirmed_metric_payload_scorecard(
        fixtures_dir,
        financial_engine_root=tmp_path,
    )

    gate = build_pre_persistence_scorecard_gate(scorecard)
    blockers = {blocker["code"]: blocker["count"] for blocker in gate["blockers"]}

    assert gate["gate_status"] == "fail"
    assert gate["actual_payload_supplied"] is False
    assert blockers["actual_payload_not_supplied"] == 1
    assert blockers[PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL.value] == 1


def test_pre_persistence_scorecard_gate_blocks_summary_without_metric_rows():
    scorecard = {
        "artifact_type": "confirmed_metric_payload_scorecard_v1",
        "profile": "confirmed_metric_coverage",
        "scorecard_scope": "report_local_actual_payloads_only",
        "actual_payload_supplied": True,
        "actual_payload_document_count": 1,
        "scored_metric_expectations": 1,
        "total_metric_expectations": 1,
        "result_class_summary": {PayloadScoreStatus.PRESENT_CORRECT.value: 1},
    }

    gate = build_pre_persistence_scorecard_gate(scorecard)
    blockers = {blocker["code"]: blocker["count"] for blocker in gate["blockers"]}

    assert gate["gate_status"] == "fail"
    assert gate["metric_result_count"] == 0
    assert blockers["metric_results_missing"] == 1


def test_committed_source_asset_manifest_is_metadata_only():
    manifest = load_source_asset_manifest(SOURCE_ASSET_MANIFEST)
    asset_dir = SOURCE_ASSET_MANIFEST.parent

    assert manifest["asset_policy"]["metadata_only"] is True
    assert manifest["asset_policy"]["raw_pdfs_committed"] is False
    assert (
        manifest["asset_policy"]["source_openability_counts_as_metric_correctness"]
        is False
    )
    assert len(manifest["assets"]) == 30
    assert not list(asset_dir.rglob("*.pdf"))
    for asset in manifest["assets"]:
        assert "content" not in asset
        assert "bytes" not in asset
        assert "local_candidate_paths" in asset
        assert asset["source_kind"] in {"real_gold", "confirmed_metric_coverage"}


def test_source_asset_manifest_loads_and_reports_missing_without_pdf_requirement(
    tmp_path,
):
    manifest_path = tmp_path / "source_assets.json"
    manifest = _source_asset_manifest(
        tmp_path,
        [
            {
                "asset_id": "confirmed_metric:missing_doc",
                "ticker": "TST",
                "document_id": "missing_doc",
                "fixture_id": "missing_fixture",
                "expected_filename": "missing.pdf",
                "logical_source_name": "Synthetic missing report",
                "sha256": None,
                "size_bytes": None,
                "source_kind": "confirmed_metric_coverage",
                "local_candidate_paths": [str(tmp_path / "docs" / "TST" / "missing.pdf")],
                "reviewability_status": "DATA_MISSING",
                "missing_reason": "synthetic source PDF intentionally absent",
                "notes": "Used to prove raw PDFs are not required for CI.",
            }
        ],
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = load_source_asset_manifest(manifest_path)
    resolution = resolve_source_asset_manifest(manifest_path, workspace_root=tmp_path)

    assert loaded["manifest_id"] == "synthetic_source_assets_v1"
    assert resolution["total_asset_count"] == 1
    assert resolution["status_counts"][SourceAssetResolutionStatus.MISSING.value] == 1
    assert resolution["reviewability_only"] is True
    assert resolution["source_openability_counts_as_metric_correctness"] is False
    assert resolution["extraction_correctness_impact"] == "none"
    assert resolution["assets"][0]["present"] is False
    assert "synthetic source PDF intentionally absent" in resolution["assets"][0]["issues"]


def test_source_asset_resolver_verifies_present_hash_and_size(tmp_path):
    pdf_path = tmp_path / "docs" / "TST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_bytes = b"%PDF-1.4\nsynthetic source asset\n"
    pdf_path.write_bytes(pdf_bytes)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    manifest = _source_asset_manifest(
        tmp_path,
        [
            {
                "asset_id": "real_gold:present_doc",
                "ticker": "TST",
                "document_id": "present_doc",
                "fixture_id": None,
                "expected_filename": "report.pdf",
                "logical_source_name": "Synthetic present report",
                "sha256": digest,
                "size_bytes": len(pdf_bytes),
                "source_kind": "real_gold",
                "local_candidate_paths": [str(pdf_path)],
                "reviewability_status": "expected_present",
                "missing_reason": None,
                "notes": "Synthetic file only.",
            }
        ],
    )

    resolution = resolve_source_asset_manifest_payload(manifest, workspace_root=tmp_path)
    asset = resolution["assets"][0]

    assert asset["resolution_status"] == SourceAssetResolutionStatus.PRESENT_VERIFIED
    assert asset["present"] is True
    assert asset["size_bytes_status"] == "matched"
    assert asset["sha256_status"] == "matched"
    assert asset["actual_size_bytes"] == len(pdf_bytes)
    assert asset["actual_sha256"] == digest
    assert asset["source_openability_counts_as_metric_correctness"] is False


def test_source_asset_resolver_reports_metadata_mismatch_without_correctness_credit(
    tmp_path,
):
    pdf_path = tmp_path / "docs" / "TST" / "report.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\nsynthetic source asset\n")
    manifest = _source_asset_manifest(
        tmp_path,
        [
            {
                "asset_id": "real_gold:mismatch_doc",
                "ticker": "TST",
                "document_id": "mismatch_doc",
                "fixture_id": None,
                "expected_filename": "report.pdf",
                "logical_source_name": "Synthetic mismatch report",
                "sha256": "0" * 64,
                "size_bytes": 999,
                "source_kind": "real_gold",
                "local_candidate_paths": [str(pdf_path)],
                "reviewability_status": "expected_present",
                "missing_reason": None,
                "notes": "Synthetic mismatch file only.",
            }
        ],
    )

    resolution = resolve_source_asset_manifest_payload(manifest, workspace_root=tmp_path)
    asset = resolution["assets"][0]

    assert (
        asset["resolution_status"]
        == SourceAssetResolutionStatus.PRESENT_METADATA_MISMATCH
    )
    assert asset["present"] is True
    assert asset["size_bytes_status"] == "mismatch"
    assert asset["sha256_status"] == "mismatch"
    assert "size_bytes mismatch" in asset["issues"]
    assert "sha256 mismatch" in asset["issues"]
    assert resolution["source_openability_counts_as_metric_correctness"] is False


def test_source_asset_resolver_rejects_unsafe_candidate_paths(tmp_path):
    manifest = _source_asset_manifest(
        tmp_path,
        [
            {
                "asset_id": "real_gold:unsafe_doc",
                "ticker": "TST",
                "document_id": "unsafe_doc",
                "fixture_id": None,
                "expected_filename": "report.pdf",
                "logical_source_name": "Unsafe synthetic report",
                "sha256": None,
                "size_bytes": None,
                "source_kind": "real_gold",
                "local_candidate_paths": ["../outside/report.pdf"],
                "reviewability_status": "DATA_MISSING",
                "missing_reason": "unsafe candidate path",
                "notes": "Synthetic path-safety check.",
            }
        ],
    )

    resolution = resolve_source_asset_manifest_payload(manifest, workspace_root=tmp_path)
    asset = resolution["assets"][0]

    assert asset["resolution_status"] == SourceAssetResolutionStatus.MANIFEST_ERROR
    assert asset["present"] is False
    assert asset["candidate_results"][0]["safe"] is False
    assert "safe relative path" in asset["issues"][0]


def test_terminal_extraction_candidate_manifest_classifies_all_required_states():
    records = [
        {
            "document_id": "missing_asset",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/missing.pdf",
            "host_file_exists": False,
        },
        {
            "document_id": "no_run",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/no-run.pdf",
            "host_file_exists": True,
            "has_current_terminal_run": False,
        },
        {
            "document_id": "stale",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/stale.pdf",
            "host_file_exists": True,
            "extraction_status": "ok",
            "extractor_version": "docling_multipass_v0",
            "financial_row_count": 1,
        },
        {
            "document_id": "completed_rows",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/completed-rows.pdf",
            "host_file_exists": True,
            "extraction_status": "ok",
            "extractor_version": "docling_multipass_v1",
            "financial_row_count": 2,
        },
        {
            "document_id": "completed_zero",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/completed-zero.pdf",
            "host_file_exists": True,
            "extraction_status": "ok_low_confidence",
            "extractor_version": "docling_multipass_v1",
            "financial_row_count": 0,
        },
        {
            "document_id": "skipped",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/skipped.pdf",
            "host_file_exists": True,
            "extraction_status": "skipped",
            "extractor_version": "docling_multipass_v1",
        },
        {
            "document_id": "parser_error",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/parser-error.pdf",
            "host_file_exists": True,
            "extraction_status": "parser_error",
            "extractor_version": "docling_multipass_v1",
            "prior_error": "docling timeout",
        },
        {
            "document_id": "running",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/running.pdf",
            "host_file_exists": True,
            "extraction_status": "running",
            "extractor_version": "docling_multipass_v1",
        },
        {
            "document_id": "unknown",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/unknown.pdf",
        },
    ]

    manifest = build_terminal_extraction_candidate_manifest(
        records,
        current_extractor_version="docling_multipass_v1",
        generated_at="2026-05-27T00:00:00Z",
    )

    assert manifest["artifact_type"] == "terminal_extraction_candidate_manifest_v1"
    assert manifest["total_document_count"] == 9
    assert manifest["broad_backfill_authorized"] is False
    assert manifest["production_data_access"] is False
    for state in TerminalExtractionCandidateClass:
        assert manifest["candidate_class_counts"][state.value] == 1

    actions = manifest["recommended_action_counts"]
    assert actions[TerminalExtractionRecommendedAction.SKIP.value] == 2
    assert actions[TerminalExtractionRecommendedAction.REVIEW.value] == 3
    assert actions[TerminalExtractionRecommendedAction.CANARY_CANDIDATE.value] == 1
    assert actions[TerminalExtractionRecommendedAction.RETRY_CANDIDATE.value] == 2
    assert actions[TerminalExtractionRecommendedAction.BLOCKED_MISSING_ASSET.value] == 1


def test_terminal_extraction_candidate_distinguishes_missing_asset_from_no_run():
    missing = classify_terminal_extraction_candidate(
        {
            "document_id": "missing_asset",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/missing.pdf",
            "host_file_exists": False,
        }
    )
    existing_no_run = classify_terminal_extraction_candidate(
        {
            "document_id": "existing_no_run",
            "ticker": "TST",
            "pdf_path": "data/asx/docs/TST/existing.pdf",
            "host_file_exists": True,
            "has_current_terminal_run": False,
        }
    )

    assert missing["candidate_class"] == (
        TerminalExtractionCandidateClass.MISSING_HOST_FILE.value
    )
    assert missing["recommended_action"] == (
        TerminalExtractionRecommendedAction.BLOCKED_MISSING_ASSET.value
    )
    assert existing_no_run["candidate_class"] == (
        TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN.value
    )
    assert existing_no_run["recommended_action"] == (
        TerminalExtractionRecommendedAction.CANARY_CANDIDATE.value
    )


def test_terminal_candidate_manifest_excludes_advisory_only_documents():
    manifest = build_terminal_extraction_candidate_manifest(
        [
            {
                "document_id": "advisory_doc",
                "ticker": "PLS",
                "title": "March 2026 Quarterly Activities Report Advisory",
                "pdf_path": "data/asx/docs/PLS/advisory.pdf",
                "host_file_exists": True,
                "has_current_terminal_run": False,
            },
            {
                "document_id": "financial_doc",
                "ticker": "BHP",
                "title": "Annual Report",
                "pdf_path": "data/asx/docs/BHP/annual.pdf",
                "host_file_exists": True,
                "has_current_terminal_run": False,
            },
        ],
        current_extractor_version="docling_multipass_v1",
        generated_at="2026-05-29T00:00:00Z",
    )

    candidate_ids = {row["document_id"] for row in manifest["candidates"]}
    assert candidate_ids == {"financial_doc"}
    assert manifest["total_input_document_count"] == 2
    assert manifest["total_document_count"] == 2
    assert manifest["candidate_document_count"] == 1
    assert manifest["excluded_document_count"] == 1
    assert manifest["exclusion_reason_counts"] == {"advisory_only_document": 1}
    assert manifest["recommended_action_counts"][
        TerminalExtractionRecommendedAction.CANARY_CANDIDATE.value
    ] == 1

    excluded = manifest["excluded_candidates"][0]
    assert excluded["document_id"] == "advisory_doc"
    assert excluded["exclusion_reason"] == "advisory_only_document"
    assert excluded["quarantine_reason"] == "advisory_only_document"
    assert excluded["source_document_classification"]["document_class"] == (
        "advisory_only_document"
    )
    assert (
        excluded["recommended_action"]
        == "exclude_from_canary_candidate_manifest"
    )
    assert excluded["broad_backfill_authorized"] is False


def test_terminal_candidate_manifest_excludes_first_page_advisory_text():
    manifest = build_terminal_extraction_candidate_manifest(
        [
            {
                "document_id": "advisory_from_text",
                "ticker": "SFR",
                "title": "Market Update",
                "first_page_text": "Quarterly Report Advisory",
                "pdf_path": "data/asx/docs/SFR/advisory.pdf",
                "host_file_exists": True,
                "has_current_terminal_run": False,
            }
        ],
        current_extractor_version="docling_multipass_v1",
        generated_at="2026-05-29T00:00:00Z",
    )

    assert manifest["candidates"] == []
    assert manifest["excluded_candidates"][0]["document_id"] == "advisory_from_text"
    assert manifest["excluded_candidates"][0]["source_document_gate"] == (
        "advisory_only_document"
    )
    assert manifest["candidate_class_counts"][
        TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN.value
    ] == 0
    assert manifest["recommended_action_counts"][
        TerminalExtractionRecommendedAction.CANARY_CANDIDATE.value
    ] == 0


def test_terminal_manifest_does_not_imply_extraction_correctness():
    manifest = build_terminal_extraction_candidate_manifest(
        [
            {
                "document_id": "completed_rows",
                "ticker": "TST",
                "pdf_path": "data/asx/docs/TST/completed.pdf",
                "host_file_exists": True,
                "extraction_status": "ok",
                "extractor_version": "docling_multipass_v1",
                "financial_rows_written": 1,
                "source_asset_id": "real_gold:completed_rows",
            }
        ],
        current_extractor_version="docling_multipass_v1",
        generated_at="2026-05-27T00:00:00Z",
    )
    row = manifest["candidates"][0]

    assert row["candidate_class"] == (
        TerminalExtractionCandidateClass.COMPLETED_WITH_ROWS.value
    )
    assert row["recommended_action"] == TerminalExtractionRecommendedAction.SKIP.value
    assert manifest["source_reviewability_separate_from_extraction_correctness"] is True
    assert manifest["payload_scoreability_separate_from_terminal_state"] is True
    assert manifest["source_openability_counts_as_metric_correctness"] is False
    assert manifest["terminal_state_counts_as_metric_correctness"] is False
    assert row["source_openability_counts_as_metric_correctness"] is False
    assert row["terminal_state_counts_as_metric_correctness"] is False
    assert row["payload_scoreability_counts_as_terminal_state"] is False
    assert "#97 payload scorecard" in row["scorecard_readiness_notes"]


def test_terminal_candidate_manifest_csv_is_report_local_and_non_authorizing():
    manifest = build_terminal_extraction_candidate_manifest(
        [
            {
                "document_id": "candidate",
                "ticker": "TST",
                "document_type": "financial_performance",
                "pdf_path": "data/asx/docs/TST/candidate.pdf",
                "host_file_exists": True,
                "has_current_terminal_run": False,
            }
        ],
        current_extractor_version="docling_multipass_v1",
        generated_at="2026-05-27T00:00:00Z",
        data_missing=["live DB not queried"],
    )
    csv_text = terminal_extraction_candidate_manifest_to_csv(manifest)

    assert "candidate_class,recommended_action" in csv_text
    assert "file_exists_no_current_terminal_run,canary_candidate" in csv_text
    assert manifest["broad_backfill_authorized"] is False
    assert manifest["production_data_access"] is False
    assert manifest["data_missing"] == ["live DB not queried"]
