from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def test_production_data_access_true_fails() -> None:
    result = ajc.validate_task_card_markdown(task_card(production_data_access=True))
    assert not result.ok
    assert "production_data_access" in issue_fields(result)


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
