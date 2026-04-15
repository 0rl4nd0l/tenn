from pathlib import Path

from app.services.extraction_eval import (
    ExtractionFixture,
    MetricEvalStatus,
    build_fixture_scorecard,
    evaluate_fixture,
    load_fixtures,
    summarize_overall_score,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction_eval"


def _load_fixture(fixture_id: str) -> ExtractionFixture:
    fixtures = {f.fixture_id: f for f in load_fixtures(FIXTURES_DIR)}
    return fixtures[fixture_id]


def _payload(
    period_type: str = "A",
    period_end: str = "2024-12-31",
    currency: str = "AUD",
    scale: str = "thousands",
    metrics: dict[str, int | float | None] | None = None,
    provenance: dict[str, str] | None = None,
    source_document_id: str | None = None,
):
    return {
        "period_type": period_type,
        "period_end": period_end,
        "currency": currency,
        "scale": scale,
        "metrics": metrics or {},
        "provenance": provenance,
        "source_document_id": source_document_id,
    }


def test_load_fixtures_discover_new_scaffold_files():
    fixture_ids = {f.fixture_id for f in load_fixtures(FIXTURES_DIR)}
    assert "currency_mismatch" in fixture_ids
    assert "correct_ok" in fixture_ids
    assert "wrong_value" in fixture_ids
    assert "missing_metric" in fixture_ids
    assert "optional_abstain" in fixture_ids
    assert "context_mismatch" in fixture_ids
    assert "scoring_mix" in fixture_ids
    assert "period_mismatch" in fixture_ids
    assert "scale_mismatch" in fixture_ids
    assert "mixed_status" in fixture_ids
    assert "quarantine_context_conflict" in fixture_ids
    assert "shares_fallback_disagreement" in fixture_ids
    assert "statutory_underlying_wrong_value" in fixture_ids
    assert "wrong_current_period_column" in fixture_ids
    # Phase 02 regression fixtures
    assert "quarterly_cashflow_only" in fixture_ids
    assert "net_debt_derived_row_abstain" in fixture_ids


def test_metric_statuses_include_correct_wrong_missing_abstain():
    payload = _payload(
        metrics={
            "revenue": 1_500_000,
            "ebit": 120_000,
            "np_attributable": 49_700,
            "net_debt": None,
        }
    )
    result = evaluate_fixture(_load_fixture("correct_ok"), payload["metrics"], payload)
    assert result.context_ok is True
    assert result.metric_status("revenue") == MetricEvalStatus.CORRECT
    assert result.metric_status("ebit") == MetricEvalStatus.CORRECT
    assert result.metric_status("np_attributable") == MetricEvalStatus.CORRECT
    assert result.metric_status("net_debt") == MetricEvalStatus.CORRECT
    assert result.metric_status("shares_outstanding") == MetricEvalStatus.ABSTAIN

    wrong = evaluate_fixture(
        _load_fixture("wrong_value"),
        {"revenue": 1_200_000},
        _payload(metrics={"revenue": 1_200_000}),
    )
    assert wrong.metric_status("revenue") == MetricEvalStatus.WRONG

    missing = evaluate_fixture(
        _load_fixture("missing_metric"),
        {},
        _payload(metrics={}),
    )
    assert missing.metric_status("revenue") == MetricEvalStatus.MISSING


def test_optional_metric_classifies_as_abstain_when_absent():
    optional = evaluate_fixture(
        _load_fixture("optional_abstain"),
        {"revenue": 1_500_000},
        _payload(metrics={"revenue": 1_500_000}),
    )
    assert optional.metric_status("shares_outstanding") == MetricEvalStatus.ABSTAIN
    assert optional.metric_status("revenue") == MetricEvalStatus.CORRECT


def test_eval_normalizes_clean_provenance_without_affecting_metric_scores():
    payload = _payload(
        metrics={
            "revenue": 1_500_000,
            "ebit": 120_000,
            "np_attributable": 49_700,
            "net_debt": None,
        },
        provenance={
            "revenue": "income_statement:page_7:Revenue from contracts with customers",
            "ebit": "income_statement:page_8:Earnings before interest and tax",
            "np_attributable": "income_statement:page_9:Profit attributable to owners",
            "net_debt": "balance_sheet:page_12:Net debt",
        },
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
    )

    result = evaluate_fixture(_load_fixture("correct_ok"), payload["metrics"], payload)

    assert result.metric_status("revenue") == MetricEvalStatus.CORRECT
    assert result.metric_status("ebit") == MetricEvalStatus.CORRECT
    assert result.provenance_summary["available"] is True
    assert result.provenance_summary["status"] == "clean"
    assert result.provenance_summary["issue_count"] == 0
    assert result.provenance_summary["status_counts"] == {"precise": 4}


def test_eval_surfaces_provenance_issues_independently_of_metric_correctness():
    payload = _payload(
        metrics={
            "revenue": 1_500_000,
            "ebit": 120_000,
            "np_attributable": 49_700,
            "net_debt": None,
        },
        provenance={
            "revenue": "placeholder provenance not_configured for this fixture",
            "ebit": "derived:income_statement:Revenue(1500000)-expenses(1380000)",
            "np_attributable": "income_statement:page_9:Profit attributable to owners",
        },
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
    )

    result = evaluate_fixture(_load_fixture("correct_ok"), payload["metrics"], payload)

    assert result.context_ok is True
    assert result.metric_status("revenue") == MetricEvalStatus.CORRECT
    assert result.provenance_summary["status"] == "issues_detected"
    assert result.provenance_summary["issue_count"] >= 2
    issue_codes = {issue["code"] for issue in result.provenance_summary["issues"]}
    assert "synthetic_evidence" in issue_codes
    assert "derived_evidence" in issue_codes


def test_context_mismatch_marks_all_metrics_as_quarantine():
    payload = _payload(currency="AUD", metrics={"revenue": 1_500_000})
    quarantine = evaluate_fixture(
        _load_fixture("context_mismatch"), payload["metrics"], payload
    )
    assert quarantine.context_ok is False
    assert "currency" in quarantine.context_mismatches
    for metric_eval in quarantine.metrics:
        assert metric_eval.status == MetricEvalStatus.QUARANTINE


def test_period_and_scale_mismatch_are_enforced_in_context_validation():
    payload = _payload(
        period_end="2025-06-30", scale="millions", metrics={"revenue": 1_500_000}
    )
    mismatch = evaluate_fixture(
        _load_fixture("correct_ok"), payload["metrics"], payload
    )
    assert mismatch.context_ok is False
    assert set(mismatch.context_mismatches) == {"period_end", "scale"}


def test_scoring_prefers_abstain_over_wrong_for_aggregate_metrics():
    payload = _payload(
        metrics={
            "revenue": 1_000_000,  # correct
            "ebit": 50_000,  # wrong (expected 90k)
            "net_debt": 2_000,  # wrong (expected null)
            "shares_outstanding": None,  # abstain
        }
    )
    mixed = evaluate_fixture(_load_fixture("scoring_mix"), payload["metrics"], payload)

    assert mixed.metric_status("revenue") == MetricEvalStatus.CORRECT
    assert mixed.metric_status("ebit") == MetricEvalStatus.WRONG
    assert mixed.metric_status("net_debt") == MetricEvalStatus.WRONG
    assert mixed.metric_status("shares_outstanding") == MetricEvalStatus.ABSTAIN
    assert mixed.overall_score == 0.375

    summary = summarize_overall_score([mixed])
    assert summary["considered_items"] == 4
    assert summary["overall_score"] == 0.375
    assert summary["metric_scores"]["revenue"] == 1.0
    assert summary["metric_scores"]["ebit"] == 0.0
    assert summary["metric_scores"]["net_debt"] == 0.0
    assert summary["metric_scores"]["shares_outstanding"] == 0.5


def _fixture_payload_map() -> dict[str, dict]:
    fixtures = load_fixtures(FIXTURES_DIR)
    payloads: dict[str, dict] = {}
    for fixture in fixtures:
        payloads[fixture.fixture_id] = {
            "period_type": fixture.context.period_type,
            "period_end": fixture.context.period_end,
            "currency": fixture.context.currency,
            "scale": fixture.context.scale,
            "metrics": dict(fixture.metrics),
        }
    return payloads


def _build_extended_payloads() -> dict[str, dict]:
    payloads = _fixture_payload_map()

    # wrong_value fixture intentionally mismatches a required metric.
    payloads["wrong_value"]["metrics"]["revenue"] = 1_200_000

    # missing_metric fixture simulates absent extraction for a required metric.
    payloads["missing_metric"]["metrics"] = {}

    # scoring_mix fixture intentionally mixes correct, wrong, and abstain.
    payloads["scoring_mix"]["metrics"] = {
        "revenue": 1_000_000,
        "ebit": 50_000,
        "net_debt": 2_000,
    }

    # Context boundary cases: keep period_type constant but break other checks.
    payloads["context_mismatch"]["currency"] = "AUD"
    payloads["period_mismatch"]["period_end"] = "2024-12-31"
    payloads["scale_mismatch"]["scale"] = "thousands"
    payloads["currency_mismatch"]["currency"] = "AUD"
    payloads["quarantine_context_conflict"]["currency"] = "AUD"

    # Mixed risk/status fixture with required + wrong + optional-abstain.
    payloads["mixed_status"]["metrics"] = {
        "revenue": 2_000_000,
        "ebit": 100_000,
        "net_debt": 500_000,
        "shares_outstanding": 4_500_000,
    }

    # Shares/underlying-vs-statutory / wrong value cases.
    payloads["shares_fallback_disagreement"]["metrics"]["shares_outstanding"] = (
        4_500_000
    )
    payloads["statutory_underlying_wrong_value"]["metrics"]["np_attributable"] = 60_000

    # Current-period boundary fixture remains in-context but wrong by value.
    payloads["wrong_current_period_column"]["metrics"]["revenue"] = 900_000

    # Phase 02 regression fixtures: correct payloads (no override needed).
    # quarterly_cashflow_only: operating_cf matches; revenue/ebit/np_attributable absent
    # (expected_nulls) — extracted None matches expected None → all correct.
    # net_debt_derived_row_abstain: revenue + operating_cf match; net_debt absent
    # (expected_null) — extracted None matches expected None → all correct.

    return payloads


def test_scorecard_helper_includes_status_totals_and_context_summaries():
    payloads = _build_extended_payloads()

    scorecard = build_fixture_scorecard(FIXTURES_DIR, payloads)

    assert scorecard["total_fixture_count"] == 16
    assert scorecard["total_metric_expectations"] == 33
    assert scorecard["correct_count"] == 15
    assert scorecard["wrong_count"] == 7
    assert scorecard["missing_count"] == 1
    assert scorecard["abstained_count"] == 4
    assert scorecard["quarantined_count"] == 6

    assert scorecard["period_correctness_summary"] == {
        "expected_count": 16,
        "matched_count": 15,
        "mismatched_count": 1,
        "missing_count": 0,
    }
    assert scorecard["currency_correctness_summary"] == {
        "expected_count": 16,
        "matched_count": 13,
        "mismatched_count": 3,
        "missing_count": 0,
    }
    assert scorecard["scale_correctness_summary"] == {
        "expected_count": 16,
        "matched_count": 15,
        "mismatched_count": 1,
        "missing_count": 0,
    }


def test_scorecard_per_fixture_entries_are_stable_and_complete():
    payloads = _build_extended_payloads()
    scorecard = build_fixture_scorecard(FIXTURES_DIR, payloads)
    entries = scorecard["fixture_summaries"]

    assert [e["fixture_id"] for e in entries] == [
        "context_mismatch",
        "correct_ok",
        "currency_mismatch",
        "missing_metric",
        "mixed_status",
        "net_debt_derived_row_abstain",
        "optional_abstain",
        "period_mismatch",
        "quarantine_context_conflict",
        "quarterly_cashflow_only",
        "scale_mismatch",
        "scoring_mix",
        "shares_fallback_disagreement",
        "statutory_underlying_wrong_value",
        "wrong_current_period_column",
        "wrong_value",
    ]

    by_fixture = {entry["fixture_id"]: entry for entry in entries}

    correct_ok = by_fixture["correct_ok"]
    assert correct_ok["metric_count"] == 5
    assert correct_ok["correct_count"] == 4
    assert correct_ok["abstain_count"] == 1
    assert correct_ok["context_ok"] is True

    mixed_status = by_fixture["mixed_status"]
    assert mixed_status["metric_count"] == 4
    assert mixed_status["correct_count"] == 2
    assert mixed_status["wrong_count"] == 1
    assert mixed_status["abstain_count"] == 1
    assert mixed_status["quarantine_count"] == 0
    assert mixed_status["context_ok"] is True

    context_mismatch = by_fixture["context_mismatch"]
    assert context_mismatch["context_ok"] is False
    assert context_mismatch["quarantine_count"] == 1
    assert context_mismatch["metric_count"] == 1
    assert set(context_mismatch["context_mismatches"]) == {"currency"}

    quarantine_entry = by_fixture["quarantine_context_conflict"]
    assert quarantine_entry["context_ok"] is False
    assert quarantine_entry["quarantine_count"] == 1
    assert quarantine_entry["metric_count"] == 1

    wrong_current = by_fixture["wrong_current_period_column"]
    assert wrong_current["context_ok"] is True
    assert wrong_current["wrong_count"] == 1

    # Phase 02 regression fixtures
    net_debt_derived = by_fixture["net_debt_derived_row_abstain"]
    assert net_debt_derived["metric_count"] == 3
    assert net_debt_derived["correct_count"] == 3
    assert net_debt_derived["context_ok"] is True

    quarterly_cf = by_fixture["quarterly_cashflow_only"]
    assert quarterly_cf["metric_count"] == 4
    assert quarterly_cf["correct_count"] == 4
    assert quarterly_cf["context_ok"] is True


def test_scorecard_includes_provenance_diagnostics_when_available():
    payloads = _build_extended_payloads()
    payloads["correct_ok"]["source_document_id"] = (
        "123e4567-e89b-12d3-a456-426614174000"
    )
    payloads["correct_ok"]["provenance"] = {
        "revenue": "income_statement:page_7:Revenue from contracts with customers",
        "ebit": "income_statement:page_8:Earnings before interest and tax",
    }
    payloads["wrong_value"]["source_document_id"] = (
        "123e4567-e89b-12d3-a456-426614174001"
    )
    payloads["wrong_value"]["provenance"] = {
        "revenue": "placeholder provenance not_configured for this fixture",
    }

    scorecard = build_fixture_scorecard(FIXTURES_DIR, payloads)
    by_fixture = {
        entry["fixture_id"]: entry for entry in scorecard["fixture_summaries"]
    }

    assert scorecard["provenance_summary"]["available_fixture_count"] == 2
    assert scorecard["provenance_summary"]["fixture_with_issues_count"] == 1
    assert scorecard["provenance_summary"]["status"] == "issues_detected"
    assert scorecard["provenance_summary"]["status_counts"] == {
        "precise": 2,
        "synthetic": 1,
    }

    assert by_fixture["correct_ok"]["provenance_status"] == "clean"
    assert by_fixture["correct_ok"]["provenance_issue_count"] == 0
    assert by_fixture["wrong_value"]["provenance_status"] == "issues_detected"
    assert by_fixture["wrong_value"]["provenance_issue_count"] >= 1


def test_scorecard_extended_payloads_capture_negative_paths():
    scorecard = build_fixture_scorecard(FIXTURES_DIR, _build_extended_payloads())

    assert scorecard["wrong_count"] >= 1
    assert scorecard["missing_count"] >= 1
    assert scorecard["quarantined_count"] >= 1

    by_fixture = {
        entry["fixture_id"]: entry for entry in scorecard["fixture_summaries"]
    }

    assert by_fixture["wrong_value"]["wrong_count"] == 1
    assert by_fixture["missing_metric"]["missing_count"] == 1
    assert by_fixture["quarantine_context_conflict"]["quarantine_count"] == 1

    assert (
        by_fixture["period_mismatch"]["context_ok"] is False
        or by_fixture["currency_mismatch"]["context_ok"] is False
        or by_fixture["scale_mismatch"]["context_ok"] is False
    )
