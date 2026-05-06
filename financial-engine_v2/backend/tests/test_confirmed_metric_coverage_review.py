from pathlib import Path

from app.services import confirmed_metric_coverage_review as coverage_review


def test_review_packet_records_provenance_and_quality_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(
        coverage_review,
        "_git_provenance",
        lambda _workspace_root=coverage_review.WORKSPACE_ROOT: {
            "git_available": True,
            "git_head": "adb76fac485e0000000000000000000000000000",
            "git_head_short": "adb76fac485e",
            "git_branch": "test/provenance",
            "git_dirty": False,
            "git_status_short_summary": {
                "line_count": 0,
                "entries": [],
                "truncated": False,
            },
            "git_unavailable_reason": None,
        },
    )

    packet = coverage_review.run_confirmed_metric_coverage_review(
        reports_dir=tmp_path / "reports"
    )

    assert packet["profile"] == "confirmed_metric_coverage"
    assert packet["git_available"] is True
    assert packet["git_head"] == "adb76fac485e0000000000000000000000000000"
    assert packet["git_head_short"] == "adb76fac485e"
    assert packet["git_branch"] == "test/provenance"
    assert packet["git_dirty"] is False
    assert packet["git_status_short_summary"]["line_count"] == 0
    assert packet["artifact_path"] == packet["artifacts"]["json_path"]
    assert Path(packet["artifact_path"]).exists()
    assert packet["summary"]["artifact_path"] == packet["artifact_path"]

    rows = {
        (row["ticker"], row["metric_name"]): row
        for row in packet["rows"]
        if row.get("ticker")
    }
    confirmed = rows[("BHP", "revenue")]
    assert confirmed["source_pdf_present"] == (
        confirmed["source_pdf_status"] == "present"
    )
    assert confirmed["source_page_present"] is True
    assert confirmed["source_table_present"] is True
    assert confirmed["source_row_present"] is True
    assert isinstance(confirmed["precise_source_evidence"], bool)
    assert confirmed["blocked_ambiguous"] is False

    candidate = rows[("ANZ", "shares_outstanding")]
    assert candidate["classification"] == "CANDIDATE_REVIEW_REQUIRED"
    assert candidate["human_review_required"] is True

    ambiguous = rows[("DXS", "net_debt")]
    assert ambiguous["classification"] == "AMBIGUOUS_OR_DERIVED"
    assert ambiguous["blocked_ambiguous"] is True
    assert ambiguous["human_review_required"] is True


def test_git_provenance_explains_unavailable_metadata(tmp_path):
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
