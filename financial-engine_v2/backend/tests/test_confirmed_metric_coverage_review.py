from pathlib import Path

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
            "git_metadata_source": "git_command",
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


def test_git_provenance_uses_environment_before_git_commands(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "TENN_GIT_HEAD", "adb76fac485e0000000000000000000000000000"
    )
    monkeypatch.setenv("TENN_GIT_HEAD_SHORT", "adb76fac485e")
    monkeypatch.setenv("TENN_GIT_BRANCH", "test/env-provenance")
    monkeypatch.setenv("TENN_GIT_DIRTY", "true")
    monkeypatch.setenv("TENN_GIT_STATUS_LINE_COUNT", "7")
    monkeypatch.setenv("TENN_BUILD_TIME", "2026-05-06T00:00:00Z")

    def git_must_not_run(*_args, **_kwargs):
        raise AssertionError("environment provenance must not shell out to git")

    monkeypatch.setattr(coverage_review, "_git_command", git_must_not_run)

    provenance = coverage_review._git_provenance(tmp_path)

    assert provenance["git_available"] is True
    assert provenance["git_metadata_source"] == "environment"
    assert provenance["git_head"] == "adb76fac485e0000000000000000000000000000"
    assert provenance["git_head_short"] == "adb76fac485e"
    assert provenance["git_branch"] == "test/env-provenance"
    assert provenance["git_dirty"] is True
    assert provenance["git_status_short_summary"] == {
        "line_count": 7,
        "entries": [],
        "truncated": True,
    }
    assert provenance["git_unavailable_reason"] is None
    assert provenance["build_time"] == "2026-05-06T00:00:00Z"


def test_git_provenance_falls_back_to_git_commands_when_env_absent(
    monkeypatch, tmp_path
):
    _clear_git_env(monkeypatch)

    def fake_git_command(_workspace_root, *args):
        if args == ("rev-parse", "--git-dir"):
            return {"returncode": 0, "stdout": ".git\n", "stderr": "", "reason": None}
        if args == ("rev-parse", "HEAD"):
            return {
                "returncode": 0,
                "stdout": "ffffb2f2aeb8651c20216cfa4d98e204bd431d43\n",
                "stderr": "",
                "reason": None,
            }
        if args == ("rev-parse", "--short=12", "HEAD"):
            return {
                "returncode": 0,
                "stdout": "ffffb2f2aeb8\n",
                "stderr": "",
                "reason": None,
            }
        if args == ("branch", "--show-current"):
            return {
                "returncode": 0,
                "stdout": "test/git-fallback\n",
                "stderr": "",
                "reason": None,
            }
        if args == ("status", "--short"):
            return {
                "returncode": 0,
                "stdout": " M backend/app.py\n?? local.env\n",
                "stderr": "",
                "reason": None,
            }
        raise AssertionError(f"unexpected git args: {args}")

    monkeypatch.setattr(coverage_review, "_git_command", fake_git_command)

    provenance = coverage_review._git_provenance(tmp_path)

    assert provenance["git_available"] is True
    assert provenance["git_metadata_source"] == "git_command"
    assert provenance["git_head"] == "ffffb2f2aeb8651c20216cfa4d98e204bd431d43"
    assert provenance["git_head_short"] == "ffffb2f2aeb8"
    assert provenance["git_branch"] == "test/git-fallback"
    assert provenance["git_dirty"] is True
    assert provenance["git_status_short_summary"] == {
        "line_count": 2,
        "entries": [],
        "truncated": True,
    }
    assert provenance["git_unavailable_reason"] is None


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


def test_git_provenance_explains_missing_git_executable(monkeypatch, tmp_path):
    _clear_git_env(monkeypatch)

    def missing_git(_workspace_root, *_args):
        return {
            "returncode": 127,
            "stdout": "",
            "stderr": "",
            "reason": "git executable not found",
        }

    monkeypatch.setattr(coverage_review, "_git_command", missing_git)

    provenance = coverage_review._git_provenance(tmp_path)

    assert provenance["git_available"] is False
    assert provenance["git_metadata_source"] is None
    assert provenance["git_head"] is None
    assert provenance["git_branch"] is None
    assert provenance["git_dirty"] is None
    assert provenance["git_unavailable_reason"] == "git executable not found"
