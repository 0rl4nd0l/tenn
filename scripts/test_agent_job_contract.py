from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import agent_job_contract as ajc


def task_card(body: str = "Task body.", **overrides: object) -> str:
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
    lines.extend(["---", "", body])
    return "\n".join(lines) + "\n"


def v2_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "control_contract_version": 2,
        "project_id": "greyhound",
        "claim_id": "historical_market_floor",
        "proof_question": "Does the recorded historical snapshot clear the floor?",
        "hypothesis_id": "thedogs_floor_v1",
        "program_track": "offline_development",
        "entry_state": "floor_unverified",
        "target_transition": "floor_verified",
        "exit_predicate": "The immutable evidence snapshot contains at least 300 complete races.",
        "source_class": "thedogs_published_market_history",
        "dataset_version": "thedogs_20260709_v1",
        "evidence_hash": "sha256:" + "a" * 64,
        "capabilities": ["READ", "REPORT_WRITE"],
        "resume_only_if": "The dataset version, evidence hash, or hypothesis changes.",
    }
    fields.update(overrides)
    return fields


def v2_task_card(body: str = "Task body.", **overrides: object) -> str:
    fields = v2_fields()
    fields.update(overrides)
    return task_card(body=body, **fields)


def write_v2_outcome(repo: Path, **overrides: object) -> Path:
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": "ADVANCED",
        "scope_fingerprint": ajc.compute_scope_fingerprint(v2_fields()),
        "state_before": "floor_unverified",
        "state_after": "floor_verified",
        "decision_delta": "The immutable snapshot clears the floor.",
        "reused_claims": [],
        "changed_claims": ["historical_market_floor"],
        "new_evidence": ["artifacts/floor.json"],
        "produced_artifacts": ["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"],
        "resume_only_if": "",
        "new_goal_permitted": False,
        "used_capabilities": ["READ", "REPORT_WRITE"],
        "blocked_by": [],
    }
    payload.update(overrides)
    path = report_dir / "RUN_OUTCOME.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def runtime_proof_report(*, proof_result: str = "WORKING", state: str = "DONE") -> str:
    return "\n".join(
        [
            f"State: {state}",
            "",
            "## Runtime Functionality Proof",
            "- intended output: rows in the live output table",
            "- live output location: `sqlite:///tmp/runtime-proof.db`",
            "- pre-run max timestamp or count: 10",
            "- post-run max timestamp or count: 11",
            "- rows/files inserted or updated after run start: 1",
            "- readiness/gate status: validation gate passed",
            "- exact command/query used: `select count(*) from output`",
            f"- result: {proof_result}",
            "- remaining blocker: none",
            "",
        ]
    )


def board_decision_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "tenn_review_board_decision_v1",
        "decision": "proceed",
        "evidence_grade": "VERIFIED",
        "reason": "Closeout evidence is valid and in scope.",
        "task_tier": "medium",
        "recommended_model": "standard coding model",
        "actual_model": "GPT-5 Codex",
        "why_this_model": "Shared control-plane closeout tooling needs focused implementation.",
        "worker_model_allowed": "no",
        "worker_decision_limit": "none",
        "escalation_needed": "none",
        "ledger_sources_checked": ["live ledger", "committed ledger"],
        "duplicate_work_classification": "NO_MATCHING_ACTIVE_WORK_FOUND",
        "matching_candidates": [],
        "duplicate_work_decision": "continue narrow implementation",
        "minority_objection": "none_found",
        "minority_objection_checks": "Reviewed scope, tests, and owner boundaries.",
        "counter_lineage_required": False,
        "functionality_proof_required": False,
        "functionality_proof_status": "not_applicable",
        "functionality_proof_remaining_blocker": "none",
        "zoom_out_required": False,
        "root_problem_check": "closeout should validate board decision shape automatically",
        "overfitting_risk": "low",
        "report_only_loop_risk": "low",
        "broad_system_progress": "adds a reusable closeout gate",
        "class_based_approach_better": "no",
        "production_readiness_value_next_action": "run check-closeout",
        "financial_extraction_breadth_provenance_confidence_regression_check": "not applicable",
        "required_changes": [],
        "owner_approval_needed": [],
        "next_goal": "commit closeout gate wiring",
    }
    payload.update(overrides)
    return payload


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


def test_v1_task_card_passes_with_migration_warning() -> None:
    result = ajc.validate_task_card_markdown(task_card())

    assert result.ok
    assert result.issues == []
    assert any(warning.field == "control_contract_version" for warning in result.warnings)


def test_valid_v2_task_card_computes_scope_fingerprint() -> None:
    result = ajc.validate_task_card_markdown(v2_task_card())

    assert result.ok
    assert result.warnings == []
    assert result.metadata["computed_scope_fingerprint"] == ajc.compute_scope_fingerprint(v2_fields())
    assert len(str(result.metadata["computed_scope_fingerprint"])) == 64


@pytest.mark.parametrize("declared", ["", "null", "~", "2.0", "true", "'2'", "3"])
def test_declared_contract_version_must_be_strict_integer(declared: str) -> None:
    markdown = v2_task_card().replace("control_contract_version: 2", f"control_contract_version: {declared}")

    result = ajc.validate_task_card_markdown(markdown)

    assert not result.ok
    assert "control_contract_version" in issue_fields(result)


@pytest.mark.parametrize(
    "field",
    [
        "project_id",
        "claim_id",
        "proof_question",
        "hypothesis_id",
        "program_track",
        "entry_state",
        "target_transition",
        "exit_predicate",
        "source_class",
        "dataset_version",
        "evidence_hash",
        "capabilities",
        "resume_only_if",
    ],
)
def test_v2_task_card_missing_required_control_field_fails(field: str) -> None:
    markdown = v2_task_card()
    parsed = ajc.parse_task_card(markdown)
    metadata = dict(parsed.metadata)
    metadata.pop(field)

    # Use YAML directly here so removal is independent of the task-card rendering helper.
    malformed = "---\n" + __import__("yaml").safe_dump(metadata, sort_keys=False) + "---\n\nTask body.\n"
    result = ajc.validate_task_card_markdown(malformed)

    assert not result.ok
    assert field in issue_fields(result)


def test_v2_task_card_rejects_invalid_or_missing_capabilities() -> None:
    empty = ajc.validate_task_card_markdown(v2_task_card(capabilities=[]))
    unknown = ajc.validate_task_card_markdown(v2_task_card(capabilities=["READ", "TRAIN_MODEL"]))

    assert not empty.ok
    assert "capabilities" in issue_fields(empty)
    assert not unknown.ok
    assert "capabilities[1]" in issue_fields(unknown)


def test_scope_fingerprint_is_stable_across_field_order_and_yaml_whitespace() -> None:
    fields = v2_fields()
    reverse_order = dict(reversed(list(fields.items())))
    padded = dict(fields)
    for key in ajc.SCOPE_FINGERPRINT_FIELDS:
        padded[key] = f"  {fields[key]}  "

    assert ajc.compute_scope_fingerprint(fields) == ajc.compute_scope_fingerprint(reverse_order)
    assert ajc.compute_scope_fingerprint(fields) == ajc.compute_scope_fingerprint(padded)


def test_scope_fingerprint_canonicalizes_evidence_hash_spelling() -> None:
    bare = v2_fields(evidence_hash="A" * 64)
    prefixed = v2_fields(evidence_hash="  SHA256:" + "a" * 64 + "  ")

    assert ajc.compute_scope_fingerprint(bare) == ajc.compute_scope_fingerprint(prefixed)


def test_v2_task_card_rejects_manually_supplied_scope_fingerprint() -> None:
    result = ajc.validate_task_card_markdown(v2_task_card(scope_fingerprint="0" * 64))

    assert not result.ok
    assert "scope_fingerprint" in issue_fields(result)


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


def test_check_diff_production_data_access_true_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_diff_for_task_card_markdown(
        task_card(production_data_access=True),
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


def test_check_report_artifacts_requires_allowed_output_files(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_report_artifacts_for_task_card_markdown(task_card(), repo_root=repo)

    assert not result.ok
    assert "allowed_files" in diff_issue_fields(result)
    assert "output_dir" in diff_issue_fields(result)


def test_check_report_artifacts_passes_for_non_empty_report_files(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    report = report_dir / "REPORT.md"
    report.write_text("done\n", encoding="utf-8")

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"]),
        repo_root=repo,
    )

    assert result.ok
    assert result.output_dir == "reports/agent_jobs/codex-dev-job-1"
    assert result.artifacts[0].path == "reports/agent_jobs/codex-dev-job-1/REPORT.md"
    assert result.artifacts[0].size_bytes == 5


def test_check_report_artifacts_fails_for_missing_or_empty_report_files(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    empty = report_dir / "EMPTY.md"
    empty.write_text("", encoding="utf-8")

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(
            allowed_files=[
                "reports/agent_jobs/codex-dev-job-1/EMPTY.md",
                "reports/agent_jobs/codex-dev-job-1/MISSING.md",
            ],
        ),
        repo_root=repo,
    )

    assert not result.ok
    messages = [issue.message for issue in result.issues]
    assert "reports/agent_jobs/codex-dev-job-1/EMPTY.md is empty" in messages
    assert "reports/agent_jobs/codex-dev-job-1/MISSING.md is missing" in messages


def test_check_report_artifacts_returns_structured_error_for_invalid_allowed_file(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(allowed_files=["../outside.md"]),
        repo_root=repo,
    )

    assert not result.ok
    messages = [issue.message for issue in result.issues if issue.field == "allowed_files"]
    assert any("repo-relative without parent segments" in message for message in messages)


def test_check_report_artifacts_cli_returns_json_for_invalid_allowed_file(tmp_path) -> None:
    repo = git_repo(tmp_path)
    task = repo / "task.md"
    task.write_text(task_card(allowed_files=["../outside.md"]), encoding="utf-8")

    completed = subprocess.run(
        [
            "python3",
            str(Path(ajc.__file__).resolve()),
            "check-artifacts",
            str(task),
            "--repo-root",
            str(repo),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    assert '"ok": false' in completed.stdout
    assert "repo-relative without parent segments" in completed.stdout


def test_check_report_artifacts_rejects_symlink_escape(tmp_path) -> None:
    repo = git_repo(tmp_path)
    external = repo / "external"
    external.mkdir()
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    linked = report_dir / "LINKED.md"
    linked.symlink_to(external / "outside.md")
    (external / "outside.md").write_text("outside\n", encoding="utf-8")

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/LINKED.md"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any("resolves outside output_dir" in issue.message for issue in result.issues)


def test_check_report_artifacts_cli_outputs_json(tmp_path) -> None:
    repo = git_repo(tmp_path)
    task = repo / "task.md"
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text("done\n", encoding="utf-8")
    task.write_text(
        task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"]),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "python3",
            str(Path(ajc.__file__).resolve()),
            "check-report-artifacts",
            str(task),
            "--repo-root",
            str(repo),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 0
    assert '"ok": true' in completed.stdout


def test_check_report_artifacts_runtime_done_without_proof_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text("State: DONE\nOnly logs were checked.\n", encoding="utf-8")

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(
            body="Runtime service repair.",
            allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"],
        ),
        repo_root=repo,
    )

    assert not result.ok
    messages = [issue.message for issue in result.issues if issue.field == "runtime_functionality_proof"]
    assert any("missing Runtime Functionality Proof fields" in message for message in messages)
    assert any("cannot use DONE" in message for message in messages)


def test_check_report_artifacts_runtime_done_with_working_proof_passes(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text(runtime_proof_report(), encoding="utf-8")

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(
            body="Runtime service repair.",
            allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"],
        ),
        repo_root=repo,
    )

    assert result.ok


def test_check_report_artifacts_runtime_data_missing_uses_done_with_risk(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text(
        runtime_proof_report(proof_result="DATA_MISSING", state="DONE_WITH_RISK"),
        encoding="utf-8",
    )

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(
            body="Runtime service repair.",
            allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"],
        ),
        repo_root=repo,
    )

    assert result.ok


def test_check_report_artifacts_runtime_data_missing_cannot_use_done(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text(
        runtime_proof_report(proof_result="DATA_MISSING", state="DONE"),
        encoding="utf-8",
    )

    result = ajc.check_report_artifacts_for_task_card_markdown(
        task_card(
            body="Runtime service repair.",
            allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"],
        ),
        repo_root=repo,
    )

    assert not result.ok
    assert any("non-WORKING Runtime Functionality Proof" in issue.message for issue in result.issues)


def test_check_closeout_runtime_card_control_plane_mention_still_requires_proof(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(body="Runtime service repair for a control-plane status check."),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "allowed_files" for issue in result.issues)


def test_check_closeout_runtime_card_negative_report_only_mention_still_requires_proof(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(body="Runtime service repair. This task is not report-only."),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "allowed_files" for issue in result.issues)


def test_check_closeout_explicit_closeout_scope_metadata_is_exempt(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(
            body="Runtime Functionality Proof control-plane closeout validator.",
            closeout_scope="control_plane_only",
        ),
        repo_root=repo,
    )

    assert result.ok
    assert result.artifacts == []


def test_check_closeout_explicit_closeout_scope_body_line_is_exempt(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(body="Closeout scope: report-only\n\nRuntime service investigation."),
        repo_root=repo,
    )

    assert result.ok
    assert result.artifacts == []


def test_check_closeout_docs_only_control_plane_task_is_exempt_without_report(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(body="Closeout scope: docs-only\n\nControl-plane note about Runtime Functionality Proof."),
        repo_root=repo,
    )

    assert result.ok
    assert result.artifacts == []


def test_check_closeout_runtime_card_requires_report_artifacts(tmp_path) -> None:
    repo = git_repo(tmp_path)

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(body="Runtime service repair."),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "allowed_files" for issue in result.issues)


def test_check_closeout_non_runtime_invalid_board_decision_fails(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "BOARD_DECISION.json").write_text(
        json.dumps({"decision": "ship_it"}) + "\n",
        encoding="utf-8",
    )

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(
            body="Closeout scope: control-plane-only\n\nReview-board closeout.",
            allowed_files=["reports/agent_jobs/codex-dev-job-1/BOARD_DECISION.json"],
            closeout_scope="control_plane_only",
        ),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "board_decision" and "decision" in issue.message for issue in result.issues)


def test_check_closeout_non_runtime_valid_board_decision_passes(tmp_path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "BOARD_DECISION.json").write_text(
        json.dumps(board_decision_payload(), indent=2) + "\n",
        encoding="utf-8",
    )

    result = ajc.check_closeout_for_task_card_markdown(
        task_card(
            body="Closeout scope: control-plane-only\n\nReview-board closeout.",
            allowed_files=["reports/agent_jobs/codex-dev-job-1/BOARD_DECISION.json"],
            closeout_scope="control_plane_only",
        ),
        repo_root=repo,
    )

    assert result.ok
    assert [artifact.path for artifact in result.artifacts] == [
        "reports/agent_jobs/codex-dev-job-1/BOARD_DECISION.json"
    ]


def test_check_closeout_valid_v2_advanced_outcome_passes(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(repo)

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(
            allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"],
            closeout_scope="control_plane_only",
        ),
        repo_root=repo,
    )

    assert result.ok
    assert [artifact.path for artifact in result.artifacts] == [
        "reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"
    ]


def test_check_closeout_v2_advanced_requires_decision_delta(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(repo, decision_delta="")

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "decision_delta" for issue in result.issues)


@pytest.mark.parametrize("decision_delta", [False, 0, "UNCHANGED", "no-change", [], {}])
def test_check_closeout_v2_rejects_invalid_or_noop_decision_delta(
    tmp_path: Path, decision_delta: object
) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(repo, decision_delta=decision_delta)

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "decision_delta" for issue in result.issues)


def test_check_closeout_v2_rejects_v1_board_decision(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(repo)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    (report_dir / "BOARD_DECISION.json").write_text(
        json.dumps(board_decision_payload(), indent=2) + "\n", encoding="utf-8"
    )

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(
            allowed_files=[
                "reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json",
                "reports/agent_jobs/codex-dev-job-1/BOARD_DECISION.json",
            ]
        ),
        repo_root=repo,
    )

    assert not result.ok
    assert any("schema_version" in issue.message for issue in result.issues)


def test_check_closeout_v2_cross_checks_board_against_run_outcome(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(repo)
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    board = board_decision_payload(
        schema_version="tenn_review_board_decision_v2",
        run_outcome_status="DATA_MISSING",
        target_transition="different_transition",
        next_goal_permitted=True,
        next_goal_target_transition="another_transition",
        resume_only_if="Different evidence arrives.",
    )
    (report_dir / "BOARD_DECISION.json").write_text(
        json.dumps(board, indent=2) + "\n", encoding="utf-8"
    )

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(
            allowed_files=[
                "reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json",
                "reports/agent_jobs/codex-dev-job-1/BOARD_DECISION.json",
            ]
        ),
        repo_root=repo,
    )

    assert not result.ok
    messages = "\n".join(issue.message for issue in result.issues)
    assert "run_outcome_status" in messages
    assert "target_transition" in messages
    assert "next_goal_permitted" in messages
    assert "resume_only_if" in messages


def test_check_closeout_v2_normalizes_string_and_list_resume_conditions(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    condition = "The exact prospective evidence becomes available."
    write_v2_outcome(
        repo,
        status="DATA_MISSING",
        state_after="floor_unverified",
        decision_delta="NO_CHANGE",
        changed_claims=[],
        new_evidence=[],
        resume_only_if=condition,
        new_goal_permitted=False,
    )
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    board = board_decision_payload(
        schema_version="tenn_review_board_decision_v2",
        run_outcome_status="DATA_MISSING",
        target_transition="floor_verified",
        next_goal_permitted=False,
        next_goal_target_transition="",
        resume_only_if=[condition],
        next_goal="",
    )
    (report_dir / "BOARD_DECISION.json").write_text(
        json.dumps(board, indent=2) + "\n", encoding="utf-8"
    )

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(
            allowed_files=[
                "reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json",
                "reports/agent_jobs/codex-dev-job-1/BOARD_DECISION.json",
            ]
        ),
        repo_root=repo,
    )

    assert result.ok


def test_check_closeout_v2_report_creation_alone_is_not_progress(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(
        repo,
        state_after="floor_unverified",
        decision_delta="A report file was created.",
        changed_claims=[],
        new_evidence=[],
    )

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "status" and "artifact" in issue.message for issue in result.issues)


@pytest.mark.parametrize(
    "status",
    [
        "REUSED_COMPLETE",
        "ACTIVE_DUPLICATE",
        "WAITING_ON_AUTHORIZATION",
        "DATA_MISSING",
        "EVIDENCE_CONFLICT",
        "BLOCKED_NO_NEW_INPUT",
        "LOOP_GUARD_STOP",
    ],
)
def test_check_closeout_v2_terminal_outcome_rejects_next_goal(tmp_path, status: str) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(
        repo,
        status=status,
        state_after="floor_unverified",
        decision_delta="",
        changed_claims=[],
        new_evidence=[],
        resume_only_if="The immutable evidence changes.",
        new_goal_permitted=True,
        next_goal_target_transition="try_the_same_report_again",
    )
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    (report_dir / "NEXT_GOAL.md").write_text("repeat\n", encoding="utf-8")

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(
            allowed_files=[
                "reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json",
                "reports/agent_jobs/codex-dev-job-1/NEXT_GOAL.md",
            ]
        ),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "new_goal_permitted" for issue in result.issues)
    assert any(issue.field == "NEXT_GOAL.md" for issue in result.issues)


def test_check_closeout_v2_blocked_outcome_requires_resume_condition(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(
        repo,
        status="DATA_MISSING",
        state_after="floor_unverified",
        decision_delta="",
        changed_claims=[],
        new_evidence=[],
        resume_only_if="",
    )

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "resume_only_if" for issue in result.issues)


def test_check_closeout_v2_rejects_undeclared_capability_use(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(repo, used_capabilities=["READ", "REPORT_WRITE", "RESEARCH_FIT"])

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "used_capabilities" and "RESEARCH_FIT" in issue.message for issue in result.issues)


def test_check_closeout_v2_offline_transition_rejects_implicit_prospective_blocker(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(
        repo,
        status="DATA_MISSING",
        state_after="floor_unverified",
        decision_delta="",
        changed_claims=[],
        new_evidence=[],
        resume_only_if="Prospective Sportsbet evidence is captured.",
        blocked_by=[
            {
                "claim_id": "strict_sportsbet_same_floor",
                "program_track": "prospective_readiness",
                "explicit_dependency": False,
            }
        ],
    )

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json"]),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "blocked_by" and "prospective" in issue.message for issue in result.issues)


def test_check_closeout_v2_new_goal_must_target_different_transition(tmp_path) -> None:
    repo = git_repo(tmp_path)
    write_v2_outcome(
        repo,
        new_goal_permitted=True,
        next_goal_target_transition="floor_verified",
    )
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    (report_dir / "NEXT_GOAL.md").write_text("advance\n", encoding="utf-8")

    result = ajc.check_closeout_for_task_card_markdown(
        v2_task_card(
            allowed_files=[
                "reports/agent_jobs/codex-dev-job-1/RUN_OUTCOME.json",
                "reports/agent_jobs/codex-dev-job-1/NEXT_GOAL.md",
            ]
        ),
        repo_root=repo,
    )

    assert not result.ok
    assert any(issue.field == "next_goal_target_transition" for issue in result.issues)


def test_check_artifacts_alias_still_outputs_json(tmp_path) -> None:
    repo = git_repo(tmp_path)
    task = repo / "task.md"
    report_dir = repo / "reports" / "agent_jobs" / "codex-dev-job-1"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text("done\n", encoding="utf-8")
    task.write_text(
        task_card(allowed_files=["reports/agent_jobs/codex-dev-job-1/REPORT.md"]),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "python3",
            str(Path(ajc.__file__).resolve()),
            "check-artifacts",
            str(task),
            "--repo-root",
            str(repo),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 0
    assert '"ok": true' in completed.stdout


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
