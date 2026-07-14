from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import agent_decision_ledger as decision_ledger
from scripts import agent_job_registry as registry


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCRIPT = REPO_ROOT / "scripts" / "agent_job_registry.py"


@pytest.fixture(autouse=True)
def isolated_registry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENN_AGENT_REGISTRY_ROOT", raising=False)
    monkeypatch.delenv("TENN_AGENT_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def task_card(
    repo: Path,
    *,
    job_id: str,
    lane: str = "Evaluation",
    allowed_files: list[str] | None = None,
    output_dir: str | None = None,
    production_data_access: bool = False,
    stale_after_seconds: int | None = None,
) -> Path:
    allowed_files = allowed_files or [f"src/{job_id}.py"]
    output_dir = output_dir or f"reports/agent_jobs/{job_id}"
    card = repo / "docs" / "agent_tasks" / f"{job_id}.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"job_id: {job_id}",
        f"lane: {lane}",
        "owner: Codex",
        "allowed_files:",
    ]
    lines.extend(f"  - {path}" for path in allowed_files)
    lines.extend(
        [
            "approval_required: true",
            "timeout_seconds: 300",
            f"output_dir: {output_dir}",
            "mutation_mode: safe_extension",
            f"production_data_access: {'true' if production_data_access else 'false'}",
        ]
    )
    if stale_after_seconds is not None:
        lines.append(f"stale_after_seconds: {stale_after_seconds}")
    lines.extend(["---", "", "Test task card.", ""])
    card.write_text("\n".join(lines), encoding="utf-8")
    return card


def v2_task_card(
    repo: Path,
    *,
    job_id: str = "job-v2",
    lane: str = "Evaluation",
    initialize_ledger: bool = True,
    metadata_overrides: dict[str, object] | None = None,
) -> tuple[Path, dict[str, object]]:
    metadata: dict[str, object] = {
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
    metadata.update(metadata_overrides or {})
    card = task_card(
        repo,
        job_id=job_id,
        lane=lane,
        allowed_files=[
            f"src/{job_id}.py",
            f"reports/agent_jobs/{job_id}/RUN_OUTCOME.json",
            f"reports/agent_jobs/{job_id}/DECISION_ENTRY.json",
        ],
    )
    lines = card.read_text(encoding="utf-8").splitlines()
    closing_index = lines.index("---", 1)
    rendered: list[str] = []
    for key, value in metadata.items():
        if isinstance(value, list):
            rendered.append(f"{key}:")
            rendered.extend(f"  - {item}" for item in value)
        else:
            rendered.append(f"{key}: {value}")
    lines[closing_index:closing_index] = rendered
    card.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if initialize_ledger:
        decision_ledger.initialize_ledger(
            decision_ledger.resolve_live_ledger_path(repo), authorized=True
        )
    return card, metadata


def v2_decision_entry(
    card: Path,
    **overrides: object,
) -> dict[str, object]:
    validation = registry.contract.validate_task_card_markdown(
        card.read_text(encoding="utf-8")
    )
    assert validation.ok is True
    metadata = validation.metadata
    entry: dict[str, object] = {
        "decision_id": f"{metadata['job_id']}-prior-decision",
        "task_id": f"{metadata['job_id']}-prior-task",
        "run_id": f"{metadata['job_id']}-prior-run",
        "project_id": metadata["project_id"],
        "claim_id": metadata["claim_id"],
        "hypothesis_id": metadata["hypothesis_id"],
        "program_track": metadata["program_track"],
        "source_class": metadata["source_class"],
        "dataset_version": metadata["dataset_version"],
        "evidence_hash": metadata["evidence_hash"],
        "target_transition": metadata["target_transition"],
        "phase_before": metadata["entry_state"],
        "phase_after": metadata["target_transition"],
        "decision": "PASS",
        "outcome_status": "ADVANCED",
        "decision_delta": "The prior evidence changed the recorded decision.",
        "evidence_refs": ["reports/agent_jobs/prior/evidence.json"],
        "blocks": [],
        "does_not_block": ["unrelated transitions"],
        "validated_at": "2026-07-14T07:00:00Z",
        "invalidation_conditions": ["The prior evidence is disproved."],
        "reopen_conditions": [metadata["resume_only_if"]],
    }
    entry.update(overrides)
    if "scope_fingerprint" not in overrides:
        entry["scope_fingerprint"] = decision_ledger.compute_scope_fingerprint(entry)
    return entry


def write_v2_closeout(
    repo: Path,
    card: Path,
    claim: dict[str, object],
    *,
    run_id: str | None = None,
    write_decision: bool = True,
    outcome_status: str = "ADVANCED",
    decision: str = "PASS",
    decision_delta: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    validation = registry.contract.validate_task_card_markdown(
        card.read_text(encoding="utf-8")
    )
    assert validation.ok is True
    metadata = validation.metadata
    record = claim["record"]
    assert isinstance(record, dict)
    selected_run_id = run_id or str(record["session_id"])
    selected_delta = decision_delta or (
        "The recorded evidence advances the requested transition."
        if outcome_status == "ADVANCED"
        else "NO_CHANGE"
    )
    state_after = (
        metadata["target_transition"]
        if outcome_status == "ADVANCED"
        else metadata["entry_state"]
    )
    outcome: dict[str, object] = {
        "status": outcome_status,
        "scope_fingerprint": metadata["computed_scope_fingerprint"],
        "state_before": metadata["entry_state"],
        "state_after": state_after,
        "decision_delta": selected_delta,
        "reused_claims": [],
        "changed_claims": (
            [metadata["claim_id"]] if outcome_status == "ADVANCED" else []
        ),
        "new_evidence": ["fixture evidence"] if outcome_status == "ADVANCED" else [],
        "produced_artifacts": [],
        "used_capabilities": ["READ", "REPORT_WRITE"],
        "resume_only_if": metadata["resume_only_if"],
        "new_goal_permitted": False,
        "blocked_by": [],
    }
    report_dir = repo / str(metadata["output_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "RUN_OUTCOME.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    entry: dict[str, object] = {
        "decision_id": f"{metadata['job_id']}-decision-v1",
        "scope_fingerprint": metadata["computed_scope_fingerprint"],
        "task_id": metadata["job_id"],
        "run_id": selected_run_id,
        "project_id": metadata["project_id"],
        "claim_id": metadata["claim_id"],
        "hypothesis_id": metadata["hypothesis_id"],
        "program_track": metadata["program_track"],
        "source_class": metadata["source_class"],
        "dataset_version": metadata["dataset_version"],
        "evidence_hash": metadata["evidence_hash"],
        "target_transition": metadata["target_transition"],
        "phase_before": outcome["state_before"],
        "phase_after": outcome["state_after"],
        "decision": decision,
        "outcome_status": outcome["status"],
        "decision_delta": selected_delta,
        "evidence_refs": [
            f"{metadata['output_dir']}/RUN_OUTCOME.json",
        ],
        "blocks": [],
        "does_not_block": ["unrelated transitions"],
        "validated_at": "2026-07-14T08:00:00Z",
        "invalidation_conditions": ["The fixture evidence is disproved."],
        "reopen_conditions": [metadata["resume_only_if"]],
    }
    if write_decision:
        (report_dir / "DECISION_ENTRY.json").write_text(
            json.dumps(entry, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return outcome, entry


def git_repo(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    run_git(tmp_path, "init")
    run_git(tmp_path, "config", "user.email", "agent-job-registry@example.invalid")
    run_git(tmp_path, "config", "user.name", "Agent Job Registry Tests")
    (tmp_path / ".gitignore").write_text(".tenn/\nreports/agent_jobs/\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("a = 1\n", encoding="utf-8")
    (src / "b.py").write_text("b = 1\n", encoding="utf-8")
    first = task_card(tmp_path, job_id="job-a", lane="Evaluation", allowed_files=["src/a.py"])
    second = task_card(tmp_path, job_id="job-b", lane="Reporting", allowed_files=["src/b.py"])
    run_git(tmp_path, "add", ".gitignore", "src/a.py", "src/b.py", str(first), str(second))
    run_git(tmp_path, "commit", "-m", "init")
    return tmp_path


def run_registry(repo: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(REGISTRY_SCRIPT), *args, "--repo-root", str(repo)],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed, json.loads(completed.stdout)


def active_record_path(repo: Path, job_id: str) -> Path:
    return registry.resolve_registry_location(repo).root / "active" / f"{job_id}.json"


def registry_file_snapshot(root: Path) -> dict[str, tuple[int, bytes]]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): (path.stat().st_mtime_ns, path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def tree_metadata_snapshot(root: Path) -> dict[str, tuple[str, int, bytes | None]]:
    if not root.exists():
        return {}
    snapshot: dict[str, tuple[str, int, bytes | None]] = {
        ".": ("dir", root.stat().st_mtime_ns, None),
    }
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        stat = path.stat()
        if path.is_dir():
            snapshot[relative] = ("dir", stat.st_mtime_ns, None)
        elif path.is_file():
            snapshot[relative] = ("file", stat.st_mtime_ns, path.read_bytes())
    return snapshot


def test_env_registry_root_overrides_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = git_repo(tmp_path / "repo")
    env_root = tmp_path / "env-registry"
    config_root = tmp_path / "config-registry"
    run_git(repo, "config", "tenn.agentRegistryRoot", str(config_root))
    monkeypatch.setenv("TENN_AGENT_REGISTRY_ROOT", str(env_root))

    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert Path(str(payload["registry_root"])) == env_root.resolve()
    assert payload["registry_scope"] == "shared"
    assert (env_root / "active" / "job-a.json").exists()
    assert not (config_root / "active" / "job-a.json").exists()


def test_git_config_registry_root_is_used_when_env_absent(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    config_root = tmp_path / "config-registry"
    run_git(repo, "config", "tenn.agentRegistryRoot", str(config_root))

    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert Path(str(payload["registry_root"])) == config_root.resolve()
    assert payload["registry_scope"] == "shared"
    assert (config_root / "active" / "job-a.json").exists()


def test_git_common_dir_fallback_is_shared_for_linked_worktrees(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")

    repo_location = registry.resolve_registry_location(repo)
    linked_location = registry.resolve_registry_location(linked)

    assert repo_location.registry_scope == "shared"
    assert linked_location.registry_scope == "shared"
    assert repo_location.git_common_dir is not None
    assert repo_location.root == repo_location.git_common_dir / "tenn-agent-registry"
    assert linked_location.root == repo_location.root


def test_repo_local_fallback_emits_warning(tmp_path: Path) -> None:
    non_git = tmp_path / "not-a-git-repo"
    non_git.mkdir()

    payload = registry.list_active_jobs(repo_root=non_git)

    assert payload["ok"] is True
    assert payload["registry_scope"] == "repo_local_fallback"
    assert Path(str(payload["registry_root"])) == (non_git / ".tenn" / "agent_jobs").resolve()
    assert "repo-local .tenn/agent_jobs fallback" in str(payload["warnings"])


def test_list_active_includes_registry_metadata(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)

    completed, payload = run_registry(repo, "list-active")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["read_only"] is False
    assert payload["lock_acquired"] is True
    assert payload["registry_root"]
    assert payload["registry_scope"] == "shared"
    assert payload["repo_root"] == str(repo.resolve())
    assert payload["git_common_dir"]


def test_list_active_read_only_does_not_create_registry_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = git_repo(tmp_path / "repo")
    env_root = tmp_path / "missing-registry-root"
    monkeypatch.setenv("TENN_AGENT_REGISTRY_ROOT", str(env_root))
    report_root = repo / "reports"
    before_reports = tree_metadata_snapshot(report_root)

    completed, payload = run_registry(repo, "list-active", "--read-only")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["lock_acquired"] is False
    assert payload["active_jobs"] == []
    assert not env_root.exists()
    assert not (env_root / ".lock").exists()
    assert not (env_root / ".lock" / "owner.json").exists()
    assert tree_metadata_snapshot(report_root) == before_reports


def test_list_active_read_only_reads_existing_records_without_mutating_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = git_repo(tmp_path / "repo")
    env_root = tmp_path / "shared-registry"
    monkeypatch.setenv("TENN_AGENT_REGISTRY_ROOT", str(env_root))
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    report_root = repo / "reports" / "agent_jobs" / "job-a"
    before_registry_files = registry_file_snapshot(env_root)
    before_registry_tree = tree_metadata_snapshot(env_root)
    before_status_tree = tree_metadata_snapshot(report_root)

    completed, payload = run_registry(repo, "list-active", "--read-only")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["lock_acquired"] is False
    assert [job["job_id"] for job in payload["active_jobs"]] == ["job-a"]
    assert registry_file_snapshot(env_root) == before_registry_files
    assert tree_metadata_snapshot(env_root) == before_registry_tree
    assert tree_metadata_snapshot(report_root) == before_status_tree
    assert not (env_root / ".lock").exists()
    assert not (env_root / ".lock" / "owner.json").exists()


def test_linked_worktrees_see_same_active_job(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")

    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    active = registry.list_active_jobs(repo_root=linked)

    assert active["registry_root"] == claim["registry_root"]
    assert [job["job_id"] for job in active["active_jobs"]] == ["job-a"]
    assert active["active_jobs"][0]["worktree"] == str(repo.resolve())


def test_overlapping_allowed_files_across_linked_worktrees_blocks(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    overlapping = task_card(
        linked,
        job_id="job-overlap",
        lane="Reporting",
        allowed_files=["src/a.py"],
    )

    result = registry.check_overlap_for_task_card(overlapping, repo_root=linked)

    assert result["ok"] is False
    assert "allowed_files src/a.py" in str(result["issues"])


def test_non_overlapping_files_across_different_lanes_passes_in_linked_worktree(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True

    result = registry.check_overlap_for_task_card(linked / "docs" / "agent_tasks" / "job-b.md", repo_root=linked)

    assert result["ok"] is True
    assert result["issues"] == []


def test_claim_valid_task_card_creates_active_and_status_records(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert active_record_path(repo, "job-a").exists()
    assert (repo / "reports" / "agent_jobs" / "job-a" / "status.json").exists()
    record = json.loads(active_record_path(repo, "job-a").read_text(encoding="utf-8"))
    assert record["allowed_files"] == ["src/a.py"]
    assert record["worktree"] == str(repo.resolve())
    assert record["started_at"] == record["last_seen_at"]
    assert record["status"] == "active"


def test_claim_v2_task_card_persists_semantic_identity_across_active_surfaces(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    card, metadata = v2_task_card(repo)
    expected_fingerprint = registry.contract.compute_scope_fingerprint(metadata)

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is True
    active = json.loads(active_record_path(repo, "job-v2").read_text(encoding="utf-8"))
    listed = registry.list_active_jobs(repo_root=repo)["active_jobs"][0]
    status = json.loads(
        (repo / "reports" / "agent_jobs" / "job-v2" / "status.json").read_text(encoding="utf-8")
    )
    expected = {
        "control_contract_version": 2,
        "claim_head_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip(),
        "scope_fingerprint": expected_fingerprint,
        "project_id": "greyhound",
        "claim_id": "historical_market_floor",
        "hypothesis_id": "thedogs_floor_v1",
        "program_track": "offline_development",
        "source_class": "thedogs_published_market_history",
        "dataset_version": "thedogs_20260709_v1",
        "evidence_hash": "sha256:" + "a" * 64,
        "target_transition": "floor_verified",
    }
    assert expected.items() <= claim["record"].items()
    assert expected.items() <= active.items()
    assert expected.items() <= listed.items()
    assert expected.items() <= status.items()


def test_v2_claim_fails_closed_when_decision_ledger_is_missing(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo, initialize_ledger=False)

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == "DATA_MISSING"
    assert "initialized decision ledger" in str(claim["issues"])
    assert not active_record_path(repo, "job-v2").exists()


def test_v2_claim_fails_closed_when_decision_ledger_is_invalid(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo, initialize_ledger=False)
    ledger_path = decision_ledger.resolve_live_ledger_path(repo)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("not-json\n", encoding="utf-8")

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == "DATA_MISSING"
    assert "cannot use the decision ledger" in str(claim["issues"])
    assert not active_record_path(repo, "job-v2").exists()


def test_v2_claim_fails_closed_when_active_registry_is_unreadable(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    corrupt = active_record_path(repo, "corrupt-prior-job")
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_text("{", encoding="utf-8")

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == "DATA_MISSING"
    assert "fully readable active registry" in str(claim["issues"])
    assert not active_record_path(repo, "job-v2").exists()


def test_v2_claim_rejects_exact_resolved_scope_without_creating_claim(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    entry = v2_decision_entry(card)
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        entry,
        seed_authorized=True,
    )

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == "REUSED_COMPLETE"
    assert not active_record_path(repo, "job-v2").exists()


def test_v2_claim_rejects_active_duplicate_even_without_file_or_lane_overlap(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    first_card, _ = v2_task_card(repo, job_id="semantic-first")
    first = registry.claim_task_card(first_card, repo_root=repo)
    assert first["ok"] is True
    second_card, _ = v2_task_card(
        repo,
        job_id="semantic-second",
        lane="Reporting",
    )

    second = registry.claim_task_card(second_card, repo_root=repo)

    assert second["ok"] is False
    assert second["scope_classification"]["status"] == "ACTIVE_DUPLICATE"
    assert second["scope_classification"]["matching_active_jobs"] == [
        "semantic-first"
    ]
    assert not active_record_path(repo, "semantic-second").exists()


@pytest.mark.parametrize(
    ("entry_overrides", "expected_status"),
    [
        (
            {
                "decision": "DATA_MISSING",
                "outcome_status": "DATA_MISSING",
                "decision_delta": "NO_DELTA",
            },
            "DATA_MISSING",
        ),
        (
            {
                "decision": "CONFLICT",
                "outcome_status": "EVIDENCE_CONFLICT",
                "decision_delta": "NO_DELTA",
            },
            "EVIDENCE_CONFLICT",
        ),
    ],
)
def test_v2_claim_rejects_exact_unresolved_stop_states(
    tmp_path: Path,
    entry_overrides: dict[str, object],
    expected_status: str,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    entry = v2_decision_entry(card, **entry_overrides)
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        entry,
        seed_authorized=True,
    )

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == expected_status
    assert not active_record_path(repo, "job-v2").exists()


def test_v2_claim_rejects_transition_blocked_by_related_decision(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    entry = v2_decision_entry(
        card,
        target_transition="related_transition_parked",
        phase_after="related_transition_parked",
        decision="PARKED",
        outcome_status="BLOCKED_NO_NEW_INPUT",
        decision_delta="NO_DELTA",
        blocks=["floor_verified"],
    )
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        entry,
        seed_authorized=True,
    )

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == "BLOCKED_BY_DECISION"


def test_v2_claim_stops_third_unchanged_no_delta_continuation(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    ledger_path = decision_ledger.resolve_live_ledger_path(repo)
    for index in (1, 2):
        decision_ledger.append_entry(
            ledger_path,
            v2_decision_entry(
                card,
                decision_id=f"no-delta-{index}",
                target_transition=f"related_transition_{index}",
                phase_after=f"related_transition_{index}",
                decision="DATA_MISSING",
                outcome_status="DATA_MISSING",
                decision_delta="NO_DELTA",
            ),
            seed_authorized=True,
        )

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert claim["scope_classification"]["status"] == "LOOP_GUARD_STOP"
    assert claim["scope_classification"]["no_delta_outcomes"] == 2


@pytest.mark.parametrize(
    ("entry_overrides", "expected_status"),
    [
        (
            {
                "dataset_version": "thedogs_20260714_v2",
                "evidence_hash": "sha256:" + "b" * 64,
            },
            "ALLOW_CHANGED_EVIDENCE",
        ),
        (
            {"hypothesis_id": "new_feature_hypothesis_v2"},
            "ALLOW_NEW_HYPOTHESIS",
        ),
    ],
)
def test_v2_claim_admits_changed_evidence_or_new_hypothesis(
    tmp_path: Path,
    entry_overrides: dict[str, object],
    expected_status: str,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    prior = v2_decision_entry(card, **entry_overrides)
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        prior,
        seed_authorized=True,
    )

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is True
    assert claim["scope_classification"]["status"] == expected_status


def test_list_active_warns_on_invalid_v2_semantic_identity(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    path = active_record_path(repo, "job-v2")
    record = json.loads(path.read_text(encoding="utf-8"))
    del record["project_id"]
    path.write_text(json.dumps(record), encoding="utf-8")

    listed = registry.list_active_jobs(repo_root=repo, read_only=True)

    assert any(
        warning["field"] == "active_jobs" and "invalid V2 active record" in warning["message"]
        for warning in listed["warnings"]
    )


def test_claim_v1_task_card_succeeds_with_migration_warning(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)

    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)

    assert claim["ok"] is True
    assert claim.get("issues", []) == []
    assert any(warning["field"] == "control_contract_version" for warning in claim["warnings"])
    assert "scope_fingerprint" not in claim["record"]


@pytest.mark.parametrize("declared", ["", "null", "~"])
def test_claim_rejects_explicit_empty_contract_version(tmp_path: Path, declared: str) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo, job_id="job-invalid-version")
    card.write_text(
        card.read_text(encoding="utf-8").replace(
            "control_contract_version: 2",
            f"control_contract_version: {declared}",
        ),
        encoding="utf-8",
    )

    claim = registry.claim_task_card(card, repo_root=repo)

    assert claim["ok"] is False
    assert "control_contract_version" in str(claim["issues"])
    assert not active_record_path(repo, "job-invalid-version").exists()


def test_claim_invalid_task_card_fails_without_active_record(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    invalid = task_card(
        repo,
        job_id="job-invalid",
        lane="Evaluation",
        allowed_files=["src/a.py"],
        production_data_access=True,
    )

    completed, payload = run_registry(repo, "claim", invalid.relative_to(repo).as_posix())

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "production_data_access" in str(payload["issues"])
    assert not active_record_path(repo, "job-invalid").exists()


def test_second_task_with_overlapping_allowed_files_fails(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    overlapping = task_card(
        repo,
        job_id="job-overlap",
        lane="Reporting",
        allowed_files=["src/a.py"],
    )

    result = registry.check_overlap_for_task_card(overlapping, repo_root=repo)

    assert result["ok"] is False
    assert "allowed_files" in str(result["issues"])


def test_different_lane_and_files_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True

    result = registry.check_overlap_for_task_card(repo / "docs" / "agent_tasks" / "job-b.md", repo_root=repo)

    assert result["ok"] is True
    assert result["issues"] == []


def test_stale_lock_produces_warning_without_blocking(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    started = datetime(2026, 5, 6, 0, 0, tzinfo=timezone.utc)
    claim = registry.claim_task_card(
        repo / "docs" / "agent_tasks" / "job-a.md",
        repo_root=repo,
        now=started,
        stale_after_seconds=60,
    )
    assert claim["ok"] is True

    active_path = active_record_path(repo, "job-a")
    active = json.loads(active_path.read_text(encoding="utf-8"))
    stale_at = (started - timedelta(seconds=120)).isoformat().replace("+00:00", "Z")
    active["heartbeat_at"] = stale_at
    active["last_seen_at"] = stale_at
    active_path.write_text(json.dumps(active), encoding="utf-8")

    overlapping = task_card(
        repo,
        job_id="job-overlap",
        lane="Evaluation",
        allowed_files=["src/a.py"],
        stale_after_seconds=60,
    )
    result = registry.check_overlap_for_task_card(
        overlapping,
        repo_root=repo,
        now=started,
        stale_after_seconds=60,
    )

    assert result["ok"] is True
    assert "stale lock warning-only" in str(result["warnings"])


def test_release_removes_active_record_and_updates_status(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True

    release = registry.release_job("job-a", repo_root=repo)

    assert release["ok"] is True
    assert not active_record_path(repo, "job-a").exists()
    status = json.loads((repo / "reports" / "agent_jobs" / "job-a" / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "released"


def test_release_writes_status_receipt_before_unlinking_active_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(
        repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo
    )
    assert claim["ok"] is True
    active_path = active_record_path(repo, "job-a")
    real_write_status = registry._write_status

    def observed_write_status(
        location: registry.RegistryLocation,
        record: dict[str, object],
        *,
        status: str,
        now: datetime,
    ) -> str:
        assert active_path.exists()
        return real_write_status(location, record, status=status, now=now)

    monkeypatch.setattr(registry, "_write_status", observed_write_status)

    release = registry.release_job("job-a", repo_root=repo)

    assert release["ok"] is True
    assert not active_path.exists()


def test_explicit_abandon_quarantines_corrupt_active_record(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(
        repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo
    )
    assert claim["ok"] is True
    active_path = active_record_path(repo, "job-a")
    corrupt = b"{not-json\n"
    active_path.write_bytes(corrupt)

    abandoned = registry.release_job(
        "job-a",
        repo_root=repo,
        abandon_reason="The active record was corrupted during an interrupted write.",
    )

    assert abandoned["ok"] is True
    assert abandoned["status"] == "abandoned"
    assert abandoned["closeout_validated"] is False
    assert not active_path.exists()
    quarantine_path = Path(str(abandoned["quarantined_record"]))
    if not quarantine_path.is_absolute():
        quarantine_path = repo / quarantine_path
    assert quarantine_path.read_bytes() == corrupt
    status_path = Path(str(abandoned["status_path"]))
    if not status_path.is_absolute():
        status_path = repo / status_path
    receipt = json.loads(status_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "abandoned"
    assert receipt["closeout_validated"] is False
    assert "invalid JSON" in receipt["record_issue"]


def test_v2_release_rejects_missing_closeout_and_keeps_claim(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert "RUN_OUTCOME.json" in str(release["issues"])
    assert active_record_path(repo, "job-v2").exists()


def test_v2_release_still_fails_closed_if_active_identity_is_stripped(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    active_path = active_record_path(repo, "job-v2")
    active = json.loads(active_path.read_text(encoding="utf-8"))
    for field in (
        "control_contract_version",
        "scope_fingerprint",
        *registry.V2_ACTIVE_RECORD_FIELDS[1:],
    ):
        active.pop(field, None)
    active_path.write_text(json.dumps(active, sort_keys=True), encoding="utf-8")

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert active_path.exists()
    assert "V2" in str(release["issues"])


def test_v2_release_rejects_missing_or_prior_run_decision_candidate(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    write_v2_closeout(repo, card, claim, write_decision=False)

    missing = registry.release_job("job-v2", repo_root=repo)
    assert missing["ok"] is False
    assert "DECISION_ENTRY.json" in str(missing["issues"])

    write_v2_closeout(repo, card, claim, run_id="prior-run")
    prior = registry.release_job("job-v2", repo_root=repo)

    assert prior["ok"] is False
    assert "run_id" in str(prior["issues"])
    assert active_record_path(repo, "job-v2").exists()


def test_standalone_append_rejects_current_active_run(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    _, entry = write_v2_closeout(repo, card, claim)

    with pytest.raises(
        decision_ledger.DecisionLedgerError,
        match="matching claim is active",
    ):
        decision_ledger.append_entry(
            decision_ledger.resolve_live_ledger_path(repo),
            entry,
            seed_authorized=True,
        )

    assert decision_ledger.load_entries(
        decision_ledger.resolve_live_ledger_path(repo)
    ) == []


def test_v2_release_succeeds_only_with_current_run_closeout_decision(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    _, entry = write_v2_closeout(repo, card, claim)

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is True
    assert release["decision_appended"] is True
    assert not active_record_path(repo, "job-v2").exists()
    assert decision_ledger.load_entries(
        decision_ledger.resolve_live_ledger_path(repo)
    ) == [entry]
    status = json.loads(
        (repo / "reports" / "agent_jobs" / "job-v2" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status["status"] == "released"
    assert status["closeout_validated"] is True
    assert status["decision_id"] == entry["decision_id"]


def test_v2_release_retry_reuses_identical_latest_decision_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    _, entry = write_v2_closeout(repo, card, claim)
    real_write_status = registry._write_status

    def fail_release_receipt(
        location: registry.RegistryLocation,
        record: dict[str, object],
        *,
        status: str,
        now: datetime,
    ) -> str:
        if status == "released":
            raise OSError("simulated receipt write failure")
        return real_write_status(location, record, status=status, now=now)

    monkeypatch.setattr(registry, "_write_status", fail_release_receipt)
    with pytest.raises(OSError, match="simulated receipt"):
        registry.release_job("job-v2", repo_root=repo)

    ledger_path = decision_ledger.resolve_live_ledger_path(repo)
    assert decision_ledger.load_entries(ledger_path) == [entry]
    assert active_record_path(repo, "job-v2").exists()

    monkeypatch.setattr(registry, "_write_status", real_write_status)
    retried = registry.release_job("job-v2", repo_root=repo)

    assert retried["ok"] is True
    assert retried["decision_appended"] is False
    assert decision_ledger.load_entries(ledger_path) == [entry]


def test_v2_release_rejects_superseded_current_run_decision(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    _, entry = write_v2_closeout(repo, card, claim)
    successor = {
        **entry,
        "decision_id": "job-v2-adversarial-successor",
        "task_id": "adversarial-task",
        "run_id": "adversarial-run",
        "phase_before": entry["phase_after"],
        "phase_after": "floor_decision_conflicted",
        "decision": "CONFLICT",
        "outcome_status": "EVIDENCE_CONFLICT",
        "decision_delta": "Later evidence materially conflicted with the decision.",
        "blocks": ["floor_verified"],
        "supersedes_decision_id": entry["decision_id"],
        "validated_at": "2026-07-14T09:00:00Z",
    }
    ledger_path = decision_ledger.resolve_live_ledger_path(repo)
    ledger_path.write_text(
        json.dumps(entry, sort_keys=True)
        + "\n"
        + json.dumps(successor, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    assert decision_ledger.validate_entries(
        decision_ledger.load_entries(ledger_path)
    ) == []

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert "not the latest decision" in str(release["issues"])
    assert active_record_path(repo, "job-v2").exists()


def test_v2_release_rejects_committed_paths_outside_claim_allowlist(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    _, entry = write_v2_closeout(repo, card, claim)
    (repo / "src" / "b.py").write_text("b = 2\n", encoding="utf-8")
    run_git(repo, "add", "src/b.py")
    run_git(repo, "commit", "-m", "out of scope")

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert "src/b.py" in str(release["issues"])
    assert "outside allowed_files" in str(release["issues"])
    assert decision_ledger.load_entries(
        decision_ledger.resolve_live_ledger_path(repo)
    ) == []
    assert active_record_path(repo, "job-v2").exists()


def test_v2_release_allows_committed_paths_inside_claim_allowlist(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    _, entry = write_v2_closeout(repo, card, claim)
    allowed = repo / "src" / "job-v2.py"
    allowed.write_text("value = 1\n", encoding="utf-8")
    run_git(repo, "add", "src/job-v2.py")
    run_git(repo, "commit", "-m", "in scope")

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is True
    assert decision_ledger.load_entries(
        decision_ledger.resolve_live_ledger_path(repo)
    ) == [entry]


def test_v2_release_rejects_out_of_scope_commit_even_when_later_reverted(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True
    write_v2_closeout(repo, card, claim)
    original = (repo / "src" / "b.py").read_text(encoding="utf-8")
    (repo / "src" / "b.py").write_text("b = 2\n", encoding="utf-8")
    run_git(repo, "add", "src/b.py")
    run_git(repo, "commit", "-m", "out of scope")
    (repo / "src" / "b.py").write_text(original, encoding="utf-8")
    run_git(repo, "add", "src/b.py")
    run_git(repo, "commit", "-m", "revert out of scope")

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert "src/b.py" in str(release["issues"])
    assert decision_ledger.load_entries(
        decision_ledger.resolve_live_ledger_path(repo)
    ) == []


def test_v2_release_rechecks_loop_guard_for_concurrent_no_delta_closeout(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, metadata = v2_task_card(repo)
    current_transition = str(metadata["target_transition"])
    prior = v2_decision_entry(
        card,
        decision_id="prior-no-delta",
        target_transition="related-transition-1",
        phase_after="floor_unverified",
        decision="DATA_MISSING",
        outcome_status="BLOCKED_NO_NEW_INPUT",
        decision_delta="NO_CHANGE",
        does_not_block=[current_transition],
    )
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        prior,
        seed_authorized=True,
    )
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True

    concurrent = v2_decision_entry(
        card,
        decision_id="concurrent-no-delta",
        target_transition="related-transition-2",
        phase_after="floor_unverified",
        decision="DATA_MISSING",
        outcome_status="BLOCKED_NO_NEW_INPUT",
        decision_delta="NO_CHANGE",
        does_not_block=[current_transition],
    )
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        concurrent,
        seed_authorized=True,
    )
    write_v2_closeout(
        repo,
        card,
        claim,
        outcome_status="BLOCKED_NO_NEW_INPUT",
        decision="DATA_MISSING",
        decision_delta="NO_CHANGE",
    )

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert "LOOP_GUARD_STOP" in str(release["issues"])
    assert active_record_path(repo, "job-v2").exists()


def test_v2_release_rejects_concurrent_block_even_with_material_candidate_delta(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, metadata = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True

    concurrent = v2_decision_entry(
        card,
        decision_id="concurrent-block",
        target_transition="prospective-prerequisite",
        decision="DATA_MISSING",
        outcome_status="DATA_MISSING",
        decision_delta="Strict prospective evidence is missing.",
        blocks=[metadata["target_transition"]],
        does_not_block=[],
    )
    decision_ledger.append_entry(
        decision_ledger.resolve_live_ledger_path(repo),
        concurrent,
        seed_authorized=True,
    )
    write_v2_closeout(repo, card, claim)

    release = registry.release_job("job-v2", repo_root=repo)

    assert release["ok"] is False
    assert "DATA_MISSING" in str(release["issues"])
    assert active_record_path(repo, "job-v2").exists()


def test_v2_abandon_is_explicit_and_does_not_claim_success(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    claim = registry.claim_task_card(card, repo_root=repo)
    assert claim["ok"] is True

    rejected = registry.release_job("job-v2", repo_root=repo, abandon_reason=" ")
    assert rejected["ok"] is False
    assert active_record_path(repo, "job-v2").exists()

    not_recovery = registry.release_job(
        "job-v2",
        repo_root=repo,
        abandon_reason="No new evidence was found.",
    )
    assert not_recovery["ok"] is False
    assert "must close with RUN_OUTCOME" in str(not_recovery["issues"])
    assert active_record_path(repo, "job-v2").exists()

    card.write_text(
        card.read_text(encoding="utf-8").replace(
            "evidence_hash: sha256:" + "a" * 64,
            "evidence_hash: sha256:" + "b" * 64,
        ),
        encoding="utf-8",
    )

    abandoned = registry.release_job(
        "job-v2",
        repo_root=repo,
        abandon_reason="Task-card evidence changed before implementation.",
    )

    assert abandoned["ok"] is True
    status = json.loads(
        (repo / "reports" / "agent_jobs" / "job-v2" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status["status"] == "abandoned"
    assert status["closeout_validated"] is False
    assert status["abandon_reason"] == "Task-card evidence changed before implementation."


def test_stale_v2_claim_requires_explicit_abandon_before_reclaim(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    card, _ = v2_task_card(repo)
    started = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)
    first = registry.claim_task_card(
        card,
        repo_root=repo,
        now=started,
        stale_after_seconds=60,
    )
    assert first["ok"] is True

    later = started + timedelta(seconds=120)
    reclaimed = registry.claim_task_card(
        card,
        repo_root=repo,
        now=later,
        stale_after_seconds=60,
    )
    assert reclaimed["ok"] is False
    assert "abandon" in str(reclaimed["issues"]).lower()

    abandoned = registry.release_job(
        "job-v2",
        repo_root=repo,
        now=later,
        abandon_reason="The original owner stopped heartbeating.",
    )
    assert abandoned["ok"] is True
    second = registry.claim_task_card(
        card,
        repo_root=repo,
        now=later,
        stale_after_seconds=60,
    )
    assert second["ok"] is True
