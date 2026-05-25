from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from scripts import merge_parking_registry as mpr


def render_yaml_value(lines: list[str], key: str, value: object, *, indent: int = 0) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        lines.append(f"{prefix}{key}:")
        for child_key, child_value in value.items():
            render_yaml_value(lines, str(child_key), child_value, indent=indent + 2)
    elif isinstance(value, list):
        if not value:
            lines.append(f"{prefix}{key}: []")
            return
        lines.append(f"{prefix}{key}:")
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}  -")
                for child_key, child_value in item.items():
                    render_yaml_value(lines, str(child_key), child_value, indent=indent + 4)
            else:
                lines.append(f"{prefix}  - {json.dumps(item)}")
    elif isinstance(value, bool):
        lines.append(f"{prefix}{key}: {str(value).lower()}")
    elif isinstance(value, str):
        lines.append(f"{prefix}{key}: {json.dumps(value)}")
    else:
        lines.append(f"{prefix}{key}: {value}")


def entry_markdown(**overrides: object) -> str:
    fields: dict[str, Any] = {
        "schema_version": "merge_parking_entry_v1",
        "parking_id": "example_parking_v1",
        "status": "PARKED_READY_FOR_REVIEW",
        "job_id": "example_job_v1",
        "lane": "Reporting",
        "mode": "safe_extension",
        "source_branch": "safe/example-job-v1",
        "source_worktree": "/home/l4nd0/tenn-example-job-v1",
        "base_head": "0" * 40,
        "current_head": "1" * 40,
        "task_card": "docs/agent_tasks/example_job_v1.md",
        "report_dir": "reports/agent_jobs/example_job_v1",
        "output_dir": "reports/agent_jobs/example_job_v1",
        "changed_files": ["docs/example.md"],
        "validation_commands": ["python3 scripts/agent_job_contract.py validate docs/agent_tasks/example_job_v1.md"],
        "validation_result": "passed",
        "blocked_by": [],
        "ready_for_merge": True,
        "review_required": {"human": True, "gpt": True, "notes": ["Review remains required."]},
        "do_not_merge_before": "Read task card, report, diff, validation, branch/head, and registry state.",
        "data_missing": [],
        "next_agent_should": ["Open a separate integration task card."],
        "next_agent_must_not": ["Treat parking as approval to merge."],
    }
    fields.update(overrides)
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        render_yaml_value(lines, key, value)
    lines.extend(["---", "", "# Merge Parking Entry", ""])
    return "\n".join(lines)


def write_entry(
    repo: Path,
    path: str = "docs/agent_registry/merge_parking/example_parking_v1.md",
    **overrides: object,
) -> Path:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(entry_markdown(**overrides), encoding="utf-8")
    return target


def issue_fields(result: mpr.ValidationResult) -> set[str]:
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
    run_git(tmp_path, "config", "user.email", "merge-parking@example.invalid")
    run_git(tmp_path, "config", "user.name", "Merge Parking Tests")
    return tmp_path


def test_valid_entry_passes(tmp_path: Path) -> None:
    path = write_entry(tmp_path)

    result = mpr.validate_paths([path], repo_root=tmp_path)

    assert result.ok
    assert result.checked_files[0].artifact_type == "entry_markdown"


def test_invalid_status_fails(tmp_path: Path) -> None:
    path = write_entry(tmp_path, status="READY")

    result = mpr.validate_paths([path], repo_root=tmp_path)

    assert not result.ok
    assert "status" in issue_fields(result)


def test_missing_required_field_fails(tmp_path: Path) -> None:
    path = write_entry(tmp_path, current_head=None)

    result = mpr.validate_paths([path], repo_root=tmp_path)

    assert not result.ok
    assert "current_head" in issue_fields(result)


def test_ready_for_merge_true_requires_review_metadata(tmp_path: Path) -> None:
    path = write_entry(tmp_path, ready_for_merge=True, review_required=None)

    result = mpr.validate_paths([path], repo_root=tmp_path)

    assert not result.ok
    assert "review_required" in issue_fields(result)


def test_changed_file_scope_does_not_scan_unchanged_historical_entry(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    write_entry(repo, "docs/agent_registry/merge_parking/old_invalid.md", status="READY")
    run_git(repo, "add", "docs/agent_registry/merge_parking/old_invalid.md")
    run_git(repo, "commit", "-m", "add historical invalid parking entry")

    changed_entry = write_entry(repo, "docs/agent_registry/merge_parking/current.md")
    (repo / "docs" / "agent_registry" / "merge_parking" / "README.md").write_text("# Parking\n", encoding="utf-8")

    result = mpr.validate_paths([], repo_root=repo, changed=True)

    assert result.ok
    assert [checked.path for checked in result.checked_files] == [changed_entry.relative_to(repo).as_posix()]
    assert [skipped.path for skipped in result.skipped_files] == [
        "docs/agent_registry/merge_parking/README.md"
    ]


def test_template_frontmatter_passes(tmp_path: Path) -> None:
    path = write_entry(tmp_path, "docs/agent_registry/merge_parking/_entry_template.md")

    result = mpr.validate_paths([path], repo_root=tmp_path)

    assert result.ok
    assert result.checked_files[0].path == "docs/agent_registry/merge_parking/_entry_template.md"
