from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_app
from app.services import confirmed_metric_coverage_review as coverage_review


def test_confirmed_metric_coverage_default_fixtures_follow_backend_module_root():
    expected = (
        Path(coverage_review.__file__).resolve().parents[2]
        / "tests"
        / "eval_fixtures"
    )

    assert coverage_review.DEFAULT_COVERAGE_FIXTURES_DIR == expected
    assert expected.exists()


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_REPORTS_DIR",
        tmp_path / "reports" / "extraction_eval",
    )
    return TestClient(main_app.app)


def test_confirmed_metric_coverage_summary_returns_profile_counts(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)

    run_response = client.post(
        "/api/extraction-eval/confirmed-metric-coverage/run"
    )
    assert run_response.status_code == 200

    response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/summary"
    )
    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert payload["status"] == "ready_with_warnings"
    assert summary["profile"] == "confirmed_metric_coverage"
    assert summary["fixture_count"] == 15
    assert summary["total_expectations"] == 146
    assert summary["scored_count"] == 73
    assert summary["candidate_review_required_count"] == 70
    assert summary["ambiguous_count"] == 3
    assert summary["unsupported_count"] == 0
    assert summary["canonical_labels_mutated"] is False


def test_confirmed_metric_coverage_rows_return_expected_fields(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    assert client.post(
        "/api/extraction-eval/confirmed-metric-coverage/run"
    ).status_code == 200

    response = client.get("/api/extraction-eval/confirmed-metric-coverage/rows")
    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == 146
    row = next(
        item
        for item in payload["rows"]
        if item["ticker"] == "BHP" and item["metric_name"] == "revenue"
    )
    assert row["fixture_id"] == "bhp_fy2021_preliminary_final"
    assert row["period"]["period_end"] == "2021-06-30"
    assert row["expected_value"] == 60817000000
    assert row["currency"] == "USD"
    assert row["scale"] == "millions"
    assert row["source_pdf_path"].endswith(".pdf")
    assert row["source_page"] == 44
    assert row["source_table"] == "43"
    assert row["classification"] == "CONFIRMED_SOURCE_EVIDENCED"
    assert row["schema_support"]["schema_supported"] is True
    assert row["recommended_action"] == "score_in_confirmed_metric_coverage"
    assert row["production_metric_tier"] == "core"


def test_confirmed_metric_coverage_run_is_dry_run_only(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)

    def extraction_must_not_run(*_args, **_kwargs):
        raise AssertionError("confirmed metric coverage API must not run extraction")

    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        extraction_must_not_run,
    )

    response = client.post(
        "/api/extraction-eval/confirmed-metric-coverage/run"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_expectations"] == 146
    assert payload["artifacts"]["json_path"].endswith("review_packet.json")
    assert payload["artifacts"]["markdown_path"].endswith("review_packet.md")
    assert Path(payload["artifacts"]["json_path"]).exists()
    assert Path(payload["artifacts"]["markdown_path"]).exists()


def test_confirmed_metric_coverage_missing_fixtures_returns_clean_error(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(
        coverage_review,
        "DEFAULT_COVERAGE_FIXTURES_DIR",
        tmp_path / "missing-fixtures",
    )

    response = client.post(
        "/api/extraction-eval/confirmed-metric-coverage/run"
    )

    assert response.status_code == 400
    assert "confirmed metric coverage fixtures not found" in response.json()["detail"]


def test_confirmed_metric_coverage_preserves_canonical_profile_semantics(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/extraction-eval/confirmed-metric-coverage/run"
    )

    assert response.status_code == 200
    payload = response.json()
    semantics = payload["scorecard"]["canonical_trust_semantics"]
    assert semantics == {
        "canonical_core_unchanged": True,
        "expanded_required_unchanged": True,
        "mutates_canonical_trust": False,
    }
