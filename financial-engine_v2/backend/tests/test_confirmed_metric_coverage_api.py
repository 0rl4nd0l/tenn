from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_app
from app.services import confirmed_metric_coverage_review as coverage_review


def _clear_git_env(monkeypatch):
    for key in (
        "TENN_GIT_HEAD",
        "TENN_GIT_HEAD_SHORT",
        "TENN_GIT_BRANCH",
        "TENN_GIT_DIRTY",
        "TENN_GIT_STATUS_LINE_COUNT",
        "TENN_BUILD_TIME",
    ):
        monkeypatch.delenv(key, raising=False)


def test_confirmed_metric_coverage_default_fixtures_follow_backend_module_root():
    expected = (
        Path(coverage_review.__file__).resolve().parents[2] / "tests" / "eval_fixtures"
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

    run_response = client.post("/api/extraction-eval/confirmed-metric-coverage/run")
    assert run_response.status_code == 200

    response = client.get("/api/extraction-eval/confirmed-metric-coverage/summary")
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
    assert "git_available" in summary
    assert "git_unavailable_reason" in summary
    assert payload["artifact_path"].endswith("review_packet.json")
    assert summary["artifact_path"].endswith("review_packet.json")


def test_confirmed_metric_coverage_rows_return_expected_fields(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    assert (
        client.post("/api/extraction-eval/confirmed-metric-coverage/run").status_code
        == 200
    )

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
    assert row["source_pdf_present"] == (row["source_pdf_status"] == "present")
    assert row["source_page_present"] is True
    assert row["source_table_present"] is True
    assert row["source_row_present"] is True
    assert isinstance(row["precise_source_evidence"], bool)
    assert row["blocked_ambiguous"] is False
    assert row["schema_support"]["schema_supported"] is True
    assert row["recommended_action"] == "score_in_confirmed_metric_coverage"
    assert row["production_metric_tier"] == "core"


def test_confirmed_metric_coverage_source_serves_allowlisted_pdf(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    source_root = tmp_path / "financial-engine_v2" / "data" / "asx" / "docs"
    source_pdf = source_root / "BHP" / "report.pdf"
    source_pdf.parent.mkdir(parents=True)
    source_pdf.write_bytes(b"%PDF-1.4\n% source review fixture\n")
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_SOURCE_ROOTS",
        (source_root,),
    )

    response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/source",
        params={"path": "data/asx/docs/BHP/report.pdf", "page": "44"},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.4")
    assert response.headers["content-type"].startswith("application/pdf")
    assert "inline" in response.headers["content-disposition"]
    assert response.headers["x-tenn-source-page"] == "44"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_confirmed_metric_coverage_source_rejects_traversal(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    source_root = tmp_path / "source-root"
    source_root.mkdir()
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_SOURCE_ROOTS",
        (source_root,),
    )

    response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/source",
        params={"path": "../secret.pdf"},
    )

    assert response.status_code == 400
    assert "invalid source PDF path" in response.json()["detail"]


def test_confirmed_metric_coverage_source_rejects_unsafe_path_forms(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    source_root = tmp_path / "source-root"
    source_root.mkdir()
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_SOURCE_ROOTS",
        (source_root,),
    )

    cases = [
        ("https://example.com/report.pdf", "source PDF path must be a local path"),
        ("data\\asx\\docs\\BHP\\report.pdf", "source PDF path must use POSIX separators"),
        ("data/asx/docs/BHP/report.txt", "source path must reference a PDF file"),
    ]
    for source_path, expected_detail in cases:
        response = client.get(
            "/api/extraction-eval/confirmed-metric-coverage/source",
            params={"path": source_path},
        )

        assert response.status_code == 400
        assert expected_detail in response.json()["detail"]


def test_confirmed_metric_coverage_source_rejects_outside_allowlist(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    source_root = tmp_path / "source-root"
    source_root.mkdir()
    outside_pdf = tmp_path / "outside.pdf"
    outside_pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_SOURCE_ROOTS",
        (source_root,),
    )

    response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/source",
        params={"path": str(outside_pdf)},
    )

    assert response.status_code == 403
    assert "outside allowed source roots" in response.json()["detail"]


def test_confirmed_metric_coverage_source_missing_file_is_data_missing(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    source_root = tmp_path / "financial-engine_v2" / "data" / "asx" / "docs"
    source_root.mkdir(parents=True)
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_SOURCE_ROOTS",
        (source_root,),
    )

    response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/source",
        params={"path": "data/asx/docs/BHP/missing.pdf"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "DATA_MISSING: source PDF not found"


def test_confirmed_metric_coverage_source_is_read_only(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    source_root = tmp_path / "financial-engine_v2" / "data" / "asx" / "docs"
    source_pdf = source_root / "BHP" / "report.pdf"
    source_pdf.parent.mkdir(parents=True)
    source_pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        coverage_review,
        "CONFIRMED_COVERAGE_SOURCE_ROOTS",
        (source_root,),
    )

    def extraction_must_not_run(*_args, **_kwargs):
        raise AssertionError("source viewer must not run extraction")

    def rag_must_not_run(*_args, **_kwargs):
        raise AssertionError("source viewer must not query RAG/Qdrant")

    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        extraction_must_not_run,
    )
    monkeypatch.setattr(main_app, "query_rag", rag_must_not_run)

    response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/source",
        params={"path": "data/asx/docs/BHP/report.pdf"},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.4")


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

    response = client.post("/api/extraction-eval/confirmed-metric-coverage/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_expectations"] == 146
    assert payload["artifacts"]["json_path"].endswith("review_packet.json")
    assert payload["artifacts"]["markdown_path"].endswith("review_packet.md")
    assert Path(payload["artifacts"]["json_path"]).exists()
    assert Path(payload["artifacts"]["markdown_path"]).exists()
    assert payload["artifact_path"] == payload["artifacts"]["json_path"]


def test_confirmed_metric_coverage_run_records_git_provenance(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)

    monkeypatch.setattr(
        coverage_review,
        "_git_provenance",
        lambda _workspace_root=coverage_review.WORKSPACE_ROOT: {
            "git_available": True,
            "git_head": "adb76fac485e0000000000000000000000000000",
            "git_head_short": "adb76fac485e",
            "git_branch": "test/provenance",
            "git_dirty": False,
            "git_metadata_source": "git_command",
            "git_status_short_summary": {
                "line_count": 0,
                "entries": [],
                "truncated": False,
            },
            "git_unavailable_reason": None,
        },
    )

    response = client.post("/api/extraction-eval/confirmed-metric-coverage/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["git_available"] is True
    assert payload["git_head"] == "adb76fac485e0000000000000000000000000000"
    assert payload["git_head_short"] == "adb76fac485e"
    assert payload["git_branch"] == "test/provenance"
    assert payload["git_dirty"] is False
    assert payload["git_status_short_summary"]["line_count"] == 0
    assert payload["git_unavailable_reason"] is None
    assert payload["summary"]["git_head_short"] == "adb76fac485e"
    assert payload["summary"]["git_branch"] == "test/provenance"
    assert payload["summary"]["artifact_path"] == payload["artifact_path"]


def test_confirmed_metric_coverage_api_summary_exposes_environment_provenance(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setenv(
        "TENN_GIT_HEAD", "ffffb2f2aeb8651c20216cfa4d98e204bd431d43"
    )
    monkeypatch.setenv("TENN_GIT_HEAD_SHORT", "ffffb2f2aeb8")
    monkeypatch.setenv("TENN_GIT_BRANCH", "test/env-provenance")
    monkeypatch.setenv("TENN_GIT_DIRTY", "false")
    monkeypatch.setenv("TENN_GIT_STATUS_LINE_COUNT", "0")

    response = client.post("/api/extraction-eval/confirmed-metric-coverage/run")
    assert response.status_code == 200
    payload = response.json()

    assert payload["git_available"] is True
    assert payload["git_metadata_source"] == "environment"
    assert payload["git_head"] == "ffffb2f2aeb8651c20216cfa4d98e204bd431d43"
    assert payload["git_head_short"] == "ffffb2f2aeb8"
    assert payload["git_branch"] == "test/env-provenance"
    assert payload["git_dirty"] is False
    assert payload["git_status_short_summary"] == {
        "entries": [],
        "line_count": 0,
        "truncated": False,
    }
    assert payload["summary"]["git_metadata_source"] == "environment"

    summary_response = client.get(
        "/api/extraction-eval/confirmed-metric-coverage/summary"
    )
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["git_available"] is True
    assert summary_payload["git_metadata_source"] == "environment"
    assert summary_payload["summary"]["git_metadata_source"] == "environment"
    assert summary_payload["summary"]["git_branch"] == "test/env-provenance"


def test_git_provenance_explains_unavailable_metadata(monkeypatch, tmp_path):
    _clear_git_env(monkeypatch)
    missing_git_root = tmp_path / "not-a-repo"
    missing_git_root.mkdir()

    provenance = coverage_review._git_provenance(missing_git_root)

    assert provenance["git_available"] is False
    assert provenance["git_head"] is None
    assert provenance["git_branch"] is None
    assert provenance["git_dirty"] is None
    assert provenance["git_unavailable_reason"]
    assert provenance["git_status_short_summary"] == {
        "line_count": 0,
        "entries": [],
        "truncated": False,
    }


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

    response = client.post("/api/extraction-eval/confirmed-metric-coverage/run")

    assert response.status_code == 400
    assert "confirmed metric coverage fixtures not found" in response.json()["detail"]


def test_confirmed_metric_coverage_preserves_canonical_profile_semantics(
    monkeypatch,
    tmp_path,
):
    client = _client(monkeypatch, tmp_path)

    response = client.post("/api/extraction-eval/confirmed-metric-coverage/run")

    assert response.status_code == 200
    payload = response.json()
    semantics = payload["scorecard"]["canonical_trust_semantics"]
    assert semantics == {
        "canonical_core_unchanged": True,
        "expanded_required_unchanged": True,
        "mutates_canonical_trust": False,
    }
