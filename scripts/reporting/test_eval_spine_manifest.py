from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.reporting import eval_spine_manifest as manifest_tool


def write_task_card(path: Path, job_id: str = "synthetic_eval_job") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f"job_id: {job_id}",
                "lane: Evaluation",
                "owner: Codex",
                "mutation_mode: safe_extension",
                "approval_required: false",
                "allow_unapproved_safe_extension: true",
                "production_data_access: false",
                "timeout_seconds: 300",
                f"output_dir: reports/agent_jobs/{job_id}",
                "allowed_files:",
                f"  - docs/agent_tasks/{job_id}.md",
                f"  - reports/agent_jobs/{job_id}/manifest.json",
                "---",
                "",
                "# Synthetic task",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def base_manifest() -> dict[str, object]:
    payload = manifest_tool.empty_manifest()
    payload.update(
        {
            "job_id": "job",
            "lane": "Evaluation",
            "mode": "safe_extension",
            "production_data_access": False,
            "branch": "safe/job",
            "head": "abc123def456",
            "base_head": None,
            "worktree": "/tmp/job",
            "task_card": {"path": "docs/agent_tasks/job.md", "sha256": "abc", "validation_ok": True},
            "output_dir": "reports/agent_jobs/job",
            "started_at": "2026-05-20T00:00:00Z",
            "completed_at": "2026-05-20T00:01:00Z",
            "status": "complete",
            "save_recommendation": "SAVE_DEFERRED",
            "data_missing": [
                {
                    "field": "base_head",
                    "code": "missing_base_head",
                    "description": "No base head was recorded.",
                    "source_artifact": "test",
                }
            ],
        }
    )
    return payload


def test_manifest_generator_reads_synthetic_report_dir(tmp_path: Path) -> None:
    repo = tmp_path
    job_id = "synthetic_eval_job"
    task_card = repo / "docs" / "agent_tasks" / f"{job_id}.md"
    report_dir = repo / "reports" / "agent_jobs" / job_id
    report_dir.mkdir(parents=True)
    write_task_card(task_card, job_id=job_id)
    (report_dir / "status.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "lane": "Evaluation",
                "mutation_mode": "safe_extension",
                "production_data_access": False,
                "branch": "safe/synthetic",
                "worktree": str(repo),
                "started_at": "2026-05-20T00:00:00Z",
                "released_at": "2026-05-20T00:05:00Z",
                "status": "released",
                "output_dir": f"reports/agent_jobs/{job_id}",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (report_dir / "diff-check.json").write_text(
        json.dumps(
            {
                "ok": True,
                "changed_files": [{"path": "scripts/reporting/example.py", "status": "??"}],
                "disallowed_files": [],
                "validation": {"metadata": {"job_id": job_id, "lane": "Evaluation", "mutation_mode": "safe_extension"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (report_dir / "validation.json").write_text(
        json.dumps({"commands": [{"command": "pytest scripts/reporting", "result": "passed", "exit_code": 0}]}) + "\n",
        encoding="utf-8",
    )
    (report_dir / "README.md").write_text(
        "\n".join(
            [
                "# Synthetic Report",
                "- Head: `abc123def456`",
                "- Evaluation spine status: `EVALUATION_SPINE_READY_FOR_DESIGN`",
                "- Project Memory save recommendation: `SAVE_DEFERRED`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = manifest_tool.build_manifest(report_dir, task_card=task_card, repo_root=repo)
    issues = manifest_tool.validate_manifest(payload)

    assert issues == []
    assert payload["job_id"] == job_id
    assert payload["head"] == "abc123def456"
    assert payload["changed_files"] == [
        {"path": "scripts/reporting/example.py", "status": "??", "allowed_by_task_card": True}
    ]
    assert payload["validation_commands"][0]["exit_code"] == 0
    assert payload["verdicts"][0]["verdict"] == "EVALUATION_SPINE_READY_FOR_DESIGN"


def test_missing_fields_become_data_missing_not_fake_values(tmp_path: Path) -> None:
    repo = tmp_path
    job_id = "missing_eval_job"
    task_card = repo / "docs" / "agent_tasks" / f"{job_id}.md"
    report_dir = repo / "reports" / "agent_jobs" / job_id
    report_dir.mkdir(parents=True)
    write_task_card(task_card, job_id=job_id)

    payload = manifest_tool.build_manifest(report_dir, task_card=task_card, repo_root=repo)
    missing_fields = {item["field"] for item in payload["data_missing"]}

    assert payload["head"] is None
    assert payload["branch"] is None
    assert {"head", "branch", "base_head", "status", "started_at", "completed_at"} <= missing_fields
    assert manifest_tool.validate_manifest(payload) == []


def test_scorecard_profile_is_required_when_scorecard_rows_exist() -> None:
    payload = base_manifest()
    payload["scorecards"] = [{"status": "passed"}]

    issues = manifest_tool.validate_manifest(payload)

    assert any("scorecards[0].scorecard_profile" in issue for issue in issues)


def test_canonical_core_requires_do_not_overclaim_guard() -> None:
    payload = base_manifest()
    payload["do_not_overclaim"] = []
    payload["scorecards"] = [{"scorecard_profile": "canonical_core", "status": "passed"}]

    issues = manifest_tool.validate_manifest(payload)

    assert any("canonical_core requires" in issue for issue in issues)
    payload["do_not_overclaim"] = ["canonical_core must not be presented as broad production extraction coverage"]
    assert manifest_tool.validate_manifest(payload) == []


def test_expected_404_and_empty_states_are_not_failures() -> None:
    payload = base_manifest()
    payload["degraded_states"] = [
        {"classification": "expected_404", "route_path": "/api/missing", "is_failure": False},
        {"classification": "expected_empty_state", "surface": "Home", "is_failure": False},
    ]

    assert manifest_tool.validate_manifest(payload) == []


def test_manifest_script_does_not_import_backend_modules() -> None:
    tree = ast.parse(Path(manifest_tool.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    assert not any(name == "app" or name.startswith("app.") for name in imported)
    assert not any("financial_engine" in name or "financial-engine" in name for name in imported)
