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
):
    return {
        "period_type": period_type,
        "period_end": period_end,
        "currency": currency,
        "scale": scale,
        "metrics": metrics or {},
    }


def test_load_fixtures_discover_new_scaffold_files():
    fixture_ids = {f.fixture_id for f in load_fixtures(FIXTURES_DIR)}
    assert "correct_ok" in fixture_ids
    assert "wrong_value" in fixture_ids
    assert "missing_metric" in fixture_ids
    assert "optional_abstain" in fixture_ids
    assert "context_mismatch" in fixture_ids
    assert "scoring_mix" in fixture_ids


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


def test_scorecard_helper_includes_status_totals_and_context_summaries():
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

    # context_mismatch fixture keeps period/scale correct but currency mismatched.
    payloads["context_mismatch"]["currency"] = "AUD"

    scorecard = build_fixture_scorecard(FIXTURES_DIR, payloads)

    assert scorecard["total_fixture_count"] == 6
    assert scorecard["total_metric_expectations"] == 14
    assert scorecard["correct_count"] == 6
    assert scorecard["wrong_count"] == 3
    assert scorecard["missing_count"] == 1
    assert scorecard["abstained_count"] == 3
    assert scorecard["quarantined_count"] == 1

    assert scorecard["period_correctness_summary"] == {
        "expected_count": 6,
        "matched_count": 6,
        "mismatched_count": 0,
        "missing_count": 0,
    }
    assert scorecard["currency_correctness_summary"] == {
        "expected_count": 6,
        "matched_count": 5,
        "mismatched_count": 1,
        "missing_count": 0,
    }
    assert scorecard["scale_correctness_summary"] == {
        "expected_count": 6,
        "matched_count": 6,
        "mismatched_count": 0,
        "missing_count": 0,
    }


def test_scorecard_per_fixture_entries_are_stable_and_complete():
    payloads = _fixture_payload_map()
    scorecard = build_fixture_scorecard(FIXTURES_DIR, payloads)
    entries = scorecard["fixture_summaries"]
    assert [e["fixture_id"] for e in entries] == [
        "context_mismatch",
        "correct_ok",
        "missing_metric",
        "optional_abstain",
        "scoring_mix",
        "wrong_value",
    ]

    by_fixture = {e["fixture_id"]: e for e in entries}
    correct_ok = by_fixture["correct_ok"]
    assert correct_ok["metric_count"] == 5
    assert correct_ok["correct_count"] == 4
    assert correct_ok["abstain_count"] == 1
    assert correct_ok["context_ok"] is True

    context_mismatch = by_fixture["context_mismatch"]
    assert context_mismatch["context_ok"] is True
    assert context_mismatch["quarantine_count"] == 0
    assert context_mismatch["metric_count"] == 1
