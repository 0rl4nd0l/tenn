from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import agent_goal_contract as agc


def goal_markdown(**overrides: object) -> str:
    fields: dict[str, object] = {
        "schema_version": "goal_schema_v1",
        "goal_id": "example_goal_v1",
        "status": "draft",
        "owner": "Codex",
        "mode": "safe_extension",
        "objective": "Add a bounded repo-native orchestration slice.",
        "primary_lane": "Reporting",
        "supporting_lanes": ["Evaluation"],
        "task_card": "docs/agent_tasks/example_goal_task_v1.md",
        "output_dir": "reports/agent_jobs/example_goal_task_v1",
        "validation": ["python3 scripts/agent_job_contract.py validate docs/agent_tasks/example_goal_task_v1.md"],
        "hard_stops": ["Stop on overlap."],
        "merge_parking_status": "not_implemented",
        "save_recommendation": "Save after validation.",
    }
    fields.update(overrides)
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    lines.extend(["---", "", "# Goal", ""])
    return "\n".join(lines)


def write_goal(repo: Path, path: str = "docs/goals/example_goal_v1.md", **overrides: object) -> Path:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(goal_markdown(**overrides), encoding="utf-8")
    return target


def issue_fields(result: agc.ContractResult) -> set[str]:
    fields: set[str] = {issue.field for issue in result.issues}
    for checked in result.checked_files:
        fields.update(issue.field for issue in checked.issues)
    return fields


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
    run_git(tmp_path, "config", "user.email", "agent-goal-contract@example.invalid")
    run_git(tmp_path, "config", "user.name", "Agent Goal Contract Tests")
    return tmp_path


def test_valid_goal_passes(tmp_path: Path) -> None:
    repo = tmp_path
    path = write_goal(repo)

    result = agc.validate_paths([path], repo_root=repo)

    assert result.ok
    assert [checked.path for checked in result.checked_files] == ["docs/goals/example_goal_v1.md"]
    assert result.checked_files[0].artifact_type == "goal"


def test_missing_required_goal_field_fails(tmp_path: Path) -> None:
    repo = tmp_path
    path = write_goal(repo, task_card=None)

    result = agc.validate_paths([path], repo_root=repo)

    assert not result.ok
    assert "task_card" in issue_fields(result)


def test_invalid_lane_and_mode_fail(tmp_path: Path) -> None:
    repo = tmp_path
    path = write_goal(repo, primary_lane="Runtime", mode="destructive")

    result = agc.validate_paths([path], repo_root=repo)

    assert not result.ok
    assert {"primary_lane", "mode"}.issubset(issue_fields(result))


def test_task_card_output_dir_mismatch_fails(tmp_path: Path) -> None:
    repo = tmp_path
    path = write_goal(repo, output_dir="reports/agent_jobs/different_job")

    result = agc.validate_paths([path], repo_root=repo)

    assert not result.ok
    assert "output_dir" in issue_fields(result)


def test_changed_file_scope_does_not_scan_unchanged_historical_goal(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    write_goal(repo, "docs/goals/old_invalid_goal.md", task_card=None)
    run_git(repo, "add", "docs/goals/old_invalid_goal.md")
    run_git(repo, "commit", "-m", "add historical invalid goal")

    changed_goal = write_goal(repo, "docs/goals/current_goal.md")
    (repo / "docs" / "goals" / "README.md").write_text("# Goals\n", encoding="utf-8")

    result = agc.validate_paths([], repo_root=repo, changed=True)

    assert result.ok
    assert [checked.path for checked in result.checked_files] == [changed_goal.relative_to(repo).as_posix()]
    assert [skipped.path for skipped in result.skipped_files] == ["docs/goals/README.md"]


def test_no_paths_without_changed_fails_safely(tmp_path: Path) -> None:
    result = agc.validate_paths([], repo_root=tmp_path)

    assert not result.ok
    assert result.issues[0].code == "DATA_MISSING"
    assert "refusing to scan historical artifacts" in result.issues[0].message
