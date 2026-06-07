from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import agent_job_contract as ajc


def task_card(**overrides: object) -> str:
    fields: dict[str, object] = {
        "job_id": "codex-dev-job-1",
        "lane": "Evaluation",
        "owner": "Codex",
        "allowed_files": ["scripts/agent_job_contract.py", "scripts/test_agent_job_contract.py"],
        "approval_required": True,
        "timeout_seconds": 300,
        "output_dir": "reports/agent_jobs/codex-dev-job-1",
        "mutation_mode": "safe_extension",
        "production_data_access": False,
    }
    fields.update(overrides)
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
            continue
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.extend(["---", "", "Task body."])
    return "\n".join(lines) + "\n"


def issue_fields(result: ajc.ValidationResult) -> set[str]:
    return {issue.field for issue in result.issues}


def diff_issue_fields(result: ajc.DiffCheckResult) -> set[str]:
    return {issue.field for issue in result.issues}


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def git_repo(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    run_git(tmp_path, "init")
    run_git(tmp_path, "config", "user.email", "agent-job-contract@example.invalid")
    run_git(tmp_path, "config", "user.name", "Agent Job Contract Tests")

    src = tmp_path / "src"
    src.mkdir()
    (src / "allowed.py").write_text("allowed = 1\n", encoding="utf-8")
    (src / "outside.py").write_text("outside = 1\n", encoding="utf-8")
    run_git(tmp_path, "add", "src/allowed.py", "src/outside.py")
    run_git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_valid_task_card_passes() -> None:
    result = ajc.validate_task_card_markdown(task_card())
    assert result.ok
    assert result.issues == []


def test_missing_lane_fails() -> None:
    markdown = task_card()
    markdown = markdown.replace("lane: Evaluation\n", "")
    result = ajc.validate_task_card_markdown(markdown)
    assert not result.ok
    assert "lane" in issue_fields(result)


def test_invalid_lane_fails() -> None:
    result = ajc.validate_task_card_markdown(task_card(lane="Runtime"))
    assert not result.ok
    assert "lane" in issue_fields(result)


def test_safe_extension_without_approval_fails_unless_explicitly_allowed() -> None:
    blocked = ajc.validate_task_card_markdown(task_card(approval_required=False, mutation_mode="safe_extension"))
    assert not blocked.ok
    assert "approval_required" in issue_fields(blocked)

    allowed = ajc.validate_task_card_markdown(
        task_card(
            approval_required=False,
            mutation_mode="safe_extension",
            allow_unapproved_safe_extension=True,
        )
    )
    assert allowed.ok


@pytest.mark.parametrize(
    "mutation_mode",
    [
        "audit_only",
        "blocked",
        "code_and_report_only",
        "controlled_artifact_provisioning",
        "report_only",
        "safe_extension",
    ],
)
def test_supported_mutation_modes_pass(mutation_mode: str) -> None:
    result = ajc.validate_task_card_markdown(task_card(mutation_mode=mutation_mode))
    assert result.ok


def test_approved_controlled_production_data_access_passes() -> None:
    result = ajc.validate_task_card_markdown(
        task_card(
            mutation_mode="controlled_artifact_provisioning",
            production_data_access=True,
            approval_required=True,
        )
    )
    assert result.ok


def test_production_data_access_true_without_approval_fails() -> None:
    result = ajc.validate_task_card_markdown(
        task_card(
            mutation_mode="controlled_artifact_provisioning",
            production_data_access=True,
            approval_required=False,
        )
    )
    assert not result.ok
    assert "production_data_access" in issue_fields(result)


def test_audit_only_production_data_access_fails() -> None:
    result = ajc.validate_task_card_markdown(
        task_card(
            mutation_mode="audit_only",
            production_data_access=True,
            approval_required=True,
        )
    )
    assert not result.ok
    assert "production_data_access" in issue_fields(result)


def test_production_data_access_must_be_boolean() -> None:
    result = ajc.validate_task_card_markdown(task_card(production_data_access="maybe"))
    assert not result.ok
    assert "production_data_access" in issue_fields(result)


def test_validation_json_output_handles_yaml_date_metadata() -> None:
    result = ajc.validate_task_card_markdown(task_card(reviewed_at="2026-06-07"))

    payload = result.to_dict()

    assert payload["metadata"]["reviewed_at"] == "2026-06-07"
    json.dumps(payload)


@pytest.mark.parametrize(
    "output_dir",
    [
        "reports/not_agent_jobs/codex-dev-job-1",
        "reports/agent_jobs/other-job",
        "../reports/agent_jobs/codex-dev-job-1",
        "/tmp/reports/agent_jobs/codex-dev-job-1",
    ],
)
def test_output_dir_outside_reports_agent_jobs_fails(output_dir: str) -> None:
    result = ajc.validate_task_card_markdown(task_card(output_dir=output_dir))
    assert not result.ok
    assert "output_dir" in issue_fields(result)


def test_resolve_report_dir_rejects_symlink_escape(tmp_path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    agent_jobs = tmp_path / "reports" / "agent_jobs"
    agent_jobs.mkdir(parents=True)
    (agent_jobs / "codex-dev-job-1").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked report directories"):
        ajc.resolve_report_dir(
            "reports/agent_jobs/codex-dev-job-1",
            "codex-dev-job-1",
            repo_root=tmp_path,
        )


def test_check_diff_clean_allowed_file_change_passes(tmp_path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    result = ajc.check_diff_for_task_card_markdown(
        task_card(allowed_files=["src/allowed.py"]),
        repo_root=repo,
    )

    assert result.ok
    assert [changed.path for changed in result.changed_files] == ["src/allowed.py"]
    assert result.disallowed_files == []
    assert result.report_path == "reports/agent_jobs/codex-dev-job-1/diff-check.json"
    assert (repo / result.report_path).exists()


def test_check_diff_changed_file_outside_allowed_files_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    result = ajc.check_diff_for_task_card_markdown(
        task_card(allowed_files=["src/allowed.py"]),
        repo_root=repo,
    )

    assert not result.ok
    assert "src/outside.py" in result.disallowed_files
    assert "changed_files" in diff_issue_fields(result)


def test_check_diff_untracked_outside_file_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "new_outside.py").write_text("outside = 2\n", encoding="utf-8")

    result = ajc.check_diff_for_task_card_markdown(
        task_card(allowed_files=["src/allowed.py"]),
        repo_root=repo,
    )

    assert not result.ok
    assert "src/new_outside.py" in result.disallowed_files


def test_check_diff_deleted_outside_file_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").unlink()

    result = ajc.check_diff_for_task_card_markdown(
        task_card(allowed_files=["src/allowed.py"]),
        repo_root=repo,
    )

    assert not result.ok
    assert "src/outside.py" in result.disallowed_files


def test_check_diff_missing_or_invalid_task_card_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_diff_for_task_card_markdown("Task body without frontmatter.\n", repo_root=repo)

    assert not result.ok
    assert "frontmatter" in diff_issue_fields(result)
    assert result.changed_files == []
    assert result.report_path is None


def test_check_diff_approved_production_data_access_true_passes(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_diff_for_task_card_markdown(
        task_card(
            mutation_mode="controlled_artifact_provisioning",
            production_data_access=True,
            approval_required=True,
        ),
        repo_root=repo,
    )

    assert result.ok


def test_check_diff_unapproved_production_data_access_true_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_diff_for_task_card_markdown(
        task_card(
            mutation_mode="controlled_artifact_provisioning",
            production_data_access=True,
            approval_required=False,
        ),
        repo_root=repo,
    )

    assert not result.ok
    assert "production_data_access" in diff_issue_fields(result)


def test_check_diff_output_dir_outside_agent_jobs_fails_without_report(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_diff_for_task_card_markdown(
        task_card(output_dir="reports/not_agent_jobs/codex-dev-job-1"),
        repo_root=repo,
    )

    assert not result.ok
    assert "output_dir" in diff_issue_fields(result)
    assert result.report_path is None
    assert not (repo / "reports" / "not_agent_jobs" / "codex-dev-job-1" / "diff-check.json").exists()


def test_check_diff_audit_only_code_changes_fail_unless_explicitly_allowed(tmp_path) -> None:
    blocked_repo = git_repo(tmp_path / "blocked")
    (blocked_repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    blocked = ajc.check_diff_for_task_card_markdown(
        task_card(
            allowed_files=["src/allowed.py"],
            mutation_mode="audit_only",
        ),
        repo_root=blocked_repo,
    )

    assert not blocked.ok
    assert "mutation_mode" in diff_issue_fields(blocked)

    allowed_repo = git_repo(tmp_path / "allowed")
    (allowed_repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    allowed = ajc.check_diff_for_task_card_markdown(
        task_card(
            allowed_files=["src/allowed.py"],
            mutation_mode="audit_only",
            allow_audit_code_changes=True,
        ),
        repo_root=allowed_repo,
    )

    assert allowed.ok


def test_check_diff_report_output_stays_under_task_output_dir(tmp_path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    result = ajc.check_diff_for_task_card_markdown(
        task_card(allowed_files=["src/allowed.py"]),
        repo_root=repo,
    )

    assert result.report_path is not None
    report_path = (repo / result.report_path).resolve()
    allowed_root = (repo / "reports" / "agent_jobs" / "codex-dev-job-1").resolve()
    assert report_path.relative_to(allowed_root)

    external = repo / "external"
    external.mkdir()
    job_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-2"
    job_dir.symlink_to(external, target_is_directory=True)
    escaped = ajc.check_diff_for_task_card_markdown(
        task_card(
            job_id="codex-dev-job-2",
            allowed_files=["src/allowed.py"],
            output_dir="reports/agent_jobs/codex-dev-job-2",
        ),
        repo_root=repo,
    )

    assert not escaped.ok
    assert "output_dir" in diff_issue_fields(escaped)
    assert not (external / "diff-check.json").exists()


def test_frontmatter_preservation_round_trip_keeps_metadata_intact() -> None:
    markdown = task_card()
    parsed_before = ajc.parse_task_card(markdown)
    updated = ajc.replace_body_preserving_frontmatter(markdown, "Replacement body.")
    parsed_after = ajc.parse_task_card(updated)
    assert parsed_after.frontmatter_block == parsed_before.frontmatter_block
    assert parsed_after.metadata == parsed_before.metadata
    assert "Replacement body." in parsed_after.body


def test_watchdog_returns_abort_reason_after_timeout_and_max_streak() -> None:
    started = datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc)
    timed_out = ajc.start_watchdog(timeout_seconds=10, max_timeout_streak=3, now=started)
    timed_out = ajc.record_watchdog_event(timed_out, timed_out=False, now=started + timedelta(seconds=11))
    assert timed_out.status == "aborted"
    assert timed_out.ended_at is not None
    assert timed_out.abort_reason is not None
    assert "timeout_seconds exceeded" in timed_out.abort_reason

    streaked = ajc.start_watchdog(timeout_seconds=100, max_timeout_streak=2, now=started)
    streaked = ajc.record_watchdog_event(streaked, timed_out=True, now=started + timedelta(seconds=1))
    assert streaked.status == "running"
    streaked = ajc.record_watchdog_event(streaked, timed_out=True, now=started + timedelta(seconds=2))
    assert streaked.status == "aborted"
    assert streaked.abort_reason is not None
    assert "max_timeout_streak reached" in streaked.abort_reason
