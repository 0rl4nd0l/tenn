from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPT = REPO_ROOT / "scripts" / "agent_job_hook.py"
CONTRACT_SCRIPT = REPO_ROOT / "scripts" / "agent_job_contract.py"
REGISTRY_SCRIPT = REPO_ROOT / "scripts" / "agent_job_registry.py"
DECISION_LEDGER_SCRIPT = REPO_ROOT / "scripts" / "agent_decision_ledger.py"


@pytest.fixture(autouse=True)
def isolated_registry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENN_AGENT_REGISTRY_ROOT", raising=False)
    monkeypatch.delenv("TENN_AGENT_TASK_CARD", raising=False)
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
    allowed_files: list[str],
    production_data_access: bool = False,
    job_id: str = "hook-test-job",
    lane: str = "Evaluation",
    filename: str = "test-task.md",
    body: str = "Test task card.",
    control_contract_version: int | None = None,
) -> Path:
    card = repo / "docs" / "agent_tasks" / filename
    card.parent.mkdir(parents=True, exist_ok=True)
    production_access = "true" if production_data_access else "false"
    allowed = "\n".join(f"  - {path}" for path in allowed_files)
    v2_fields: list[str] = []
    if control_contract_version is not None:
        v2_fields.append(f"control_contract_version: {control_contract_version}")
    if control_contract_version == 2:
        v2_fields.extend(
            [
                "project_id: hook_test",
                f"claim_id: {job_id}",
                "proof_question: Does the hook enforce V2 closeout failures?",
                "hypothesis_id: hook_v2_hard_stop",
                "program_track: offline_development",
                "entry_state: contract_unchecked",
                "target_transition: contract_checked",
                "exit_predicate: The V2 closeout contract passes.",
                "source_class: focused_test_fixture",
                "dataset_version: fixture_v1",
                f"evidence_hash: sha256:{'a' * 64}",
                "capabilities:",
                "  - READ",
                "  - REPORT_WRITE",
                "resume_only_if: The fixture or contract changes.",
            ]
        )
    card.write_text(
        "\n".join(
            [
                "---",
                f"job_id: {job_id}",
                f"lane: {lane}",
                "owner: Codex",
                "allowed_files:",
                allowed,
                "approval_required: true",
                "timeout_seconds: 300",
                f"output_dir: reports/agent_jobs/{job_id}",
                "mutation_mode: safe_extension",
                f"production_data_access: {production_access}",
                *v2_fields,
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return card


def git_repo(tmp_path: Path, *, vendor_control_plane_scripts: bool = True) -> Path:
    repo = tmp_path
    repo.mkdir(parents=True, exist_ok=True)
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "agent-job-hook@example.invalid")
    run_git(repo, "config", "user.name", "Agent Job Hook Tests")

    scripts = repo / "scripts"
    if vendor_control_plane_scripts:
        scripts.mkdir()
        (scripts / "agent_job_contract.py").write_text(CONTRACT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (scripts / "agent_job_registry.py").write_text(REGISTRY_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / ".gitignore").write_text(".tenn/\nreports/agent_jobs/\n__pycache__/\n", encoding="utf-8")

    src = repo / "src"
    src.mkdir()
    (src / "allowed.py").write_text("allowed = 1\n", encoding="utf-8")
    (src / "outside.py").write_text("outside = 1\n", encoding="utf-8")
    task_card(repo, allowed_files=["src/allowed.py"])

    tracked = [
        ".gitignore",
        "src/allowed.py",
        "src/outside.py",
        "docs/agent_tasks/test-task.md",
    ]
    if vendor_control_plane_scripts:
        tracked.extend(
            ["scripts/agent_job_contract.py", "scripts/agent_job_registry.py"]
        )
    run_git(repo, "add", *tracked)
    run_git(repo, "commit", "-m", "init")
    return repo


def run_hook(
    repo: Path,
    *,
    env: dict[str, str] | None = None,
    platform: str = "codex",
    event: str = "Stop",
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    completed = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT), "--platform", platform, "--event", event, "--repo-root", str(repo)],
        input=json.dumps({"hook_event_name": event}),
        cwd=repo,
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return completed, payload


def run_repo_registry(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    completed = subprocess.run(
        [sys.executable, str(repo / "scripts" / "agent_job_registry.py"), *args, "--repo-root", str(repo)],
        cwd=repo,
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed, json.loads(completed.stdout)


def write_valid_v2_outcome(repo: Path, card: Path) -> None:
    validated = subprocess.run(
        [sys.executable, str(CONTRACT_SCRIPT), "validate", str(card)],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    fingerprint = json.loads(validated.stdout)["metadata"][
        "computed_scope_fingerprint"
    ]
    output = repo / "reports" / "agent_jobs" / "hook-test-job" / "RUN_OUTCOME.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "status": "ADVANCED",
                "scope_fingerprint": fingerprint,
                "state_before": "contract_unchecked",
                "state_after": "contract_checked",
                "decision_delta": "The portable closeout contract passed.",
                "reused_claims": [],
                "changed_claims": ["portable V2 closeout is valid"],
                "new_evidence": ["focused hook fixture"],
                "produced_artifacts": [
                    "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
                ],
                "resume_only_if": "",
                "new_goal_permitted": False,
                "used_capabilities": ["READ", "REPORT_WRITE"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def claim_v2_job(repo: Path, card: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            sys.executable,
            str(REGISTRY_SCRIPT),
            "claim",
            str(card),
            "--repo-root",
            str(repo),
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def claimed_active_record_path(repo: Path, claim: dict[str, object]) -> Path:
    path = Path(str(claim["active_record"]))
    return path if path.is_absolute() else repo / path


def append_matching_v2_decision(repo: Path, card: Path, *, run_id: str, **overrides: object) -> None:
    validated = subprocess.run(
        [sys.executable, str(CONTRACT_SCRIPT), "validate", str(card)],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    metadata = json.loads(validated.stdout)["metadata"]
    entry: dict[str, object] = {
        "decision_id": "hook-test-decision",
        "scope_fingerprint": metadata["computed_scope_fingerprint"],
        "task_id": metadata["job_id"],
        "run_id": run_id,
        "project_id": metadata["project_id"],
        "claim_id": metadata["claim_id"],
        "hypothesis_id": metadata["hypothesis_id"],
        "program_track": metadata["program_track"],
        "source_class": metadata["source_class"],
        "dataset_version": metadata["dataset_version"],
        "evidence_hash": metadata["evidence_hash"],
        "target_transition": metadata["target_transition"],
        "phase_before": "contract_unchecked",
        "phase_after": "contract_checked",
        "decision": "PASS",
        "outcome_status": "ADVANCED",
        "decision_delta": "The portable closeout contract passed.",
        "evidence_refs": ["reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"],
        "blocks": [],
        "does_not_block": [],
        "validated_at": "2026-07-13T00:00:00Z",
        "invalidation_conditions": ["The scope fingerprint changes."],
        "reopen_conditions": ["The evidence changes."],
    }
    entry.update(overrides)
    completed = subprocess.run(
        [
            sys.executable,
            str(DECISION_LEDGER_SCRIPT),
            "append",
            "--repo-root",
            str(repo),
            "--entry-json",
            json.dumps(entry, sort_keys=True),
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_no_active_task_card_exits_success_with_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload == {}
    assert completed.stderr == ""


def test_hook_uses_own_control_plane_when_target_vendors_no_tenn_scripts(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
    )

    assert completed.returncode == 0
    assert payload == {}
    assert not (repo / "scripts").exists()


def test_portable_v2_stop_validates_target_decision_ledger(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    write_valid_v2_outcome(repo, card)

    missing_completed, missing_payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
    )

    assert missing_completed.returncode == 0
    assert missing_payload["decision"] == "block"
    assert "decision-ledger-validate" in str(missing_payload["reason"])

    initialized = subprocess.run(
        [
            sys.executable,
            str(DECISION_LEDGER_SCRIPT),
            "initialize",
            "--repo-root",
            str(repo),
            "--authorize-create-empty-ledger",
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert initialized.returncode == 0
    assert json.loads(initialized.stdout)["created"] is True

    claim = claim_v2_job(repo, card)
    run_id = str(claim["record"]["session_id"])

    empty_completed, empty_payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
    )

    assert empty_completed.returncode == 0
    assert empty_payload["decision"] == "block"
    assert "no validated entry matches" in str(empty_payload["reason"])

    append_matching_v2_decision(repo, card, run_id=run_id)
    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
    )

    assert completed.returncode == 0
    assert payload == {}
    assert not (repo / "scripts").exists()


def test_active_target_worktree_v2_job_is_enforced_without_override(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    initialized = subprocess.run(
        [
            sys.executable,
            str(DECISION_LEDGER_SCRIPT),
            "initialize",
            "--repo-root",
            str(repo),
            "--authorize-create-empty-ledger",
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert initialized.returncode == 0
    claim = claim_v2_job(repo, card)

    missing_completed, missing_payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
    )

    assert missing_completed.returncode == 0
    assert missing_payload["decision"] == "block"
    assert "RUN_OUTCOME.json" in str(missing_payload["reason"])

    write_valid_v2_outcome(repo, card)
    append_matching_v2_decision(
        repo,
        card,
        run_id=str(claim["record"]["session_id"]),
    )
    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload == {}
    assert not (repo / "scripts").exists()


@pytest.mark.parametrize("drift", ["allowed_files", "capabilities"])
def test_active_v2_selector_blocks_task_card_contract_drift_until_reclaim(
    tmp_path: Path,
    drift: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim_v2_job(repo, card)
    original = card.read_text(encoding="utf-8")
    if drift == "allowed_files":
        changed = original.replace(
            "  - src/allowed.py",
            "  - src/allowed.py\n  - src/outside.py",
        )
    else:
        changed = original.replace(
            "  - REPORT_WRITE",
            "  - REPORT_WRITE\n  - CODE_EDIT",
        )
    card.write_text(changed, encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "task_card_sha256" in str(payload["reason"])
    assert "release and reclaim" in str(payload["reason"])


def test_active_v2_selector_fails_closed_on_corrupt_unscoped_registry_record(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    claimed_active_record_path(repo, claim).write_text("{", encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "unscoped active registry parse/schema warning" in str(payload["reason"])


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_nonstale_v2_job_named_stale_fails_closed_on_invalid_fingerprint(
    tmp_path: Path,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        job_id="stale-selector-job",
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare stale-named v2 task")
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    record = json.loads(active_path.read_text(encoding="utf-8"))
    record["scope_fingerprint"] = "not-a-fingerprint"
    active_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "matching V2 selector stale-selector-job is invalid" in str(payload["reason"])
    assert "registry_validation" in str(payload["reason"])


def test_active_v2_selector_fails_closed_on_ambiguous_matching_jobs(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    duplicate = json.loads(active_path.read_text(encoding="utf-8"))
    duplicate["job_id"] = "second-hook-test-job"
    duplicate["session_id"] = "second-hook-test-session"
    (active_path.parent / "second-hook-test-job.json").write_text(
        json.dumps(duplicate, sort_keys=True),
        encoding="utf-8",
    )

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "multiple non-stale V2 jobs select this worktree" in str(payload["reason"])


@pytest.mark.parametrize("selector", ["env", "marker"])
def test_explicit_v2_selector_blocks_post_claim_card_drift(
    tmp_path: Path,
    selector: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim_v2_job(repo, card)
    card.write_text(
        card.read_text(encoding="utf-8").replace(
            "  - REPORT_WRITE",
            "  - REPORT_WRITE\n  - CODE_EDIT",
        ),
        encoding="utf-8",
    )
    env = {"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"}
    if selector == "marker":
        marker = repo / ".tenn" / "active_agent_task"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")
        env = {"TENN_AGENT_TASK_CARD": ""}

    completed, payload = run_hook(repo, env=env)

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "matching V2 selector task card changed after claim" in str(payload["reason"])
    assert "task_card_sha256" in str(payload["reason"])
    assert "release and reclaim" in str(payload["reason"])


@pytest.mark.parametrize("selector", ["env", "marker"])
@pytest.mark.parametrize("drift", ["allowed_files", "capabilities"])
def test_explicit_v2_before_tool_blocks_post_claim_contract_drift(
    tmp_path: Path,
    selector: str,
    drift: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim_v2_job(repo, card)
    original = card.read_text(encoding="utf-8")
    if drift == "allowed_files":
        changed = original.replace(
            "  - src/allowed.py",
            "  - src/allowed.py\n  - src/outside.py",
        )
    else:
        changed = original.replace(
            "  - REPORT_WRITE",
            "  - REPORT_WRITE\n  - CODE_EDIT",
        )
    card.write_text(changed, encoding="utf-8")
    env = {"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"}
    if selector == "marker":
        marker = repo / ".tenn" / "active_agent_task"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")
        env = {"TENN_AGENT_TASK_CARD": ""}

    completed, payload = run_hook(repo, env=env, event="BeforeTool")

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "matching V2 selector task card changed after claim" in str(payload["reason"])
    assert "task_card_sha256" in str(payload["reason"])


def test_explicit_valid_v2_before_tool_keeps_pass_context(tmp_path: Path) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare v2 task")
    claim_v2_job(repo, card)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload == {
        "systemMessage": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md"
    }


@pytest.mark.parametrize("selector", ["env", "marker"])
@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
@pytest.mark.parametrize("downgrade", ["removed", "changed_to_v1"])
def test_explicit_v2_claim_blocks_post_claim_version_downgrade(
    tmp_path: Path,
    selector: str,
    event: str,
    downgrade: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", "docs/agent_tasks/test-task.md"],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare v2 task")
    claim_v2_job(repo, card)
    original = card.read_text(encoding="utf-8")
    if downgrade == "removed":
        changed = original.replace("control_contract_version: 2\n", "")
    else:
        changed = original.replace(
            "control_contract_version: 2",
            "control_contract_version: 1",
        )
    card.write_text(changed, encoding="utf-8")
    env = {"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"}
    if selector == "marker":
        marker = repo / ".tenn" / "active_agent_task"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")
        env = {"TENN_AGENT_TASK_CARD": ""}

    completed, payload = run_hook(repo, env=env, event=event)

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "task_card_sha256" in str(payload["reason"])
    assert "changed after claim" in str(payload["reason"])


@pytest.mark.parametrize("selector", ["env", "marker"])
@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_explicit_valid_v1_without_active_v2_claim_preserves_behavior(
    tmp_path: Path,
    selector: str,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=1,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare v1 task")
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")
    env = {"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"}
    if selector == "marker":
        marker = repo / ".tenn" / "active_agent_task"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")
        env = {"TENN_AGENT_TASK_CARD": ""}

    completed, payload = run_hook(repo, env=env, event=event)

    assert completed.returncode == 0
    if event == "Stop":
        assert payload == {}
    else:
        assert payload == {
            "systemMessage": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md"
        }


def test_partial_v2_identity_without_version_or_fingerprint_fails_closed(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    partial = json.loads(active_path.read_text(encoding="utf-8"))
    del partial["control_contract_version"]
    del partial["scope_fingerprint"]
    active_path.write_text(json.dumps(partial, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "matching V2 selector" in str(payload["reason"])
    assert "control_contract_version" in str(payload["reason"])
    assert "scope_fingerprint" in str(payload["reason"])


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_unchanged_v2_card_blocks_fully_stripped_active_identity(
    tmp_path: Path,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    stripped = json.loads(active_path.read_text(encoding="utf-8"))
    for field in (
        "control_contract_version",
        "scope_fingerprint",
        "project_id",
        "claim_id",
        "hypothesis_id",
        "program_track",
        "source_class",
        "dataset_version",
        "evidence_hash",
        "target_transition",
    ):
        del stripped[field]
    active_path.write_text(json.dumps(stripped, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "matching V2 selector" in str(payload["reason"])
    assert "control_contract_version" in str(payload["reason"])
    assert "scope_fingerprint" in str(payload["reason"])
    assert "project_id" in str(payload["reason"])


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_unchanged_claimed_v1_card_stays_silent_without_explicit_selector(
    tmp_path: Path,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=1,
    )
    claim_v2_job(repo, card)

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload == {}


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_claimed_v1_record_without_task_card_stays_silent(
    tmp_path: Path,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=1,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    record = json.loads(active_path.read_text(encoding="utf-8"))
    del record["task_card"]
    active_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload == {}


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_claimed_v1_record_with_invalid_worktree_stays_silent(
    tmp_path: Path,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=1,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    record = json.loads(active_path.read_text(encoding="utf-8"))
    record["worktree"] = "\u0000invalid"
    active_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload == {}


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
@pytest.mark.parametrize("worktree_state", ["missing", "invalid"])
def test_unchanged_v2_card_blocks_stripped_identity_with_unscopable_worktree(
    tmp_path: Path,
    event: str,
    worktree_state: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    stripped = json.loads(active_path.read_text(encoding="utf-8"))
    for field in (
        "control_contract_version",
        "scope_fingerprint",
        "project_id",
        "claim_id",
        "hypothesis_id",
        "program_track",
        "source_class",
        "dataset_version",
        "evidence_hash",
        "target_transition",
    ):
        del stripped[field]
    if worktree_state == "missing":
        del stripped["worktree"]
    else:
        stripped["worktree"] = "\u0000invalid"
    active_path.write_text(json.dumps(stripped, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "missing or invalid worktree" in str(payload["reason"])
    assert "cannot be safely scoped" in str(payload["reason"])


@pytest.mark.parametrize("event", ["Stop", "BeforeTool"])
def test_declared_v2_card_blocks_unscopable_fully_stripped_record_without_hash(
    tmp_path: Path,
    event: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    stripped = json.loads(active_path.read_text(encoding="utf-8"))
    for field in (
        "control_contract_version",
        "scope_fingerprint",
        "task_card_sha256",
        "worktree",
        "project_id",
        "claim_id",
        "hypothesis_id",
        "program_track",
        "source_class",
        "dataset_version",
        "evidence_hash",
        "target_transition",
    ):
        del stripped[field]
    active_path.write_text(json.dumps(stripped, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        event=event,
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "missing or invalid worktree" in str(payload["reason"])
    assert "cannot be safely scoped" in str(payload["reason"])


@pytest.mark.parametrize("worktree_state", ["missing", "invalid"])
def test_v2_like_record_with_unscopable_worktree_fails_closed(
    tmp_path: Path,
    worktree_state: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    record = json.loads(active_path.read_text(encoding="utf-8"))
    if worktree_state == "missing":
        del record["worktree"]
    else:
        record["worktree"] = "\u0000invalid"
    active_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "missing or invalid worktree" in str(payload["reason"])
    assert "cannot be safely scoped" in str(payload["reason"])


def test_v2_stop_rejects_decision_entry_with_mismatched_phases(tmp_path: Path) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    write_valid_v2_outcome(repo, card)
    subprocess.run(
        [
            sys.executable,
            str(DECISION_LEDGER_SCRIPT),
            "initialize",
            "--repo-root",
            str(repo),
            "--authorize-create-empty-ledger",
        ],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    claim = claim_v2_job(repo, card)
    append_matching_v2_decision(
        repo,
        card,
        run_id=str(claim["record"]["session_id"]),
        phase_after="different_phase",
    )

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "no validated entry matches" in str(payload["reason"])


def test_no_active_task_card_stays_silent_with_shared_registry_jobs(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    shared_root = tmp_path / "shared-registry"
    claim_completed, claim_payload = run_repo_registry(
        repo,
        "claim",
        "docs/agent_tasks/test-task.md",
        env={"TENN_AGENT_REGISTRY_ROOT": str(shared_root)},
    )
    assert claim_completed.returncode == 0
    assert claim_payload["ok"] is True

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "", "TENN_AGENT_REGISTRY_ROOT": str(shared_root)},
    )

    assert completed.returncode == 0
    assert payload == {}


def test_active_valid_task_card_with_allowed_diff_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload == {}


def test_codex_before_tool_active_valid_task_card_keeps_pass_context(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="codex",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload == {"systemMessage": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md"}


def test_before_tool_outside_diff_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "src/outside.py" in str(payload["reason"])


def test_before_tool_invalid_task_card_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(repo, allowed_files=["src/allowed.py"], production_data_access=True)
    run_git(repo, "add", "docs/agent_tasks/test-task.md")
    run_git(repo, "commit", "-m", "invalid task card")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "production_data_access" in str(payload["reason"])


def test_stop_invalid_task_card_warns_without_blocking(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(repo, allowed_files=["src/allowed.py"], production_data_access=True)
    run_git(repo, "add", "docs/agent_tasks/test-task.md")
    run_git(repo, "commit", "-m", "invalid task card")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["systemMessage"].startswith("Tenn agent-job contract blocked")
    assert "production_data_access" in str(payload["systemMessage"])
    assert "decision" not in payload


def test_explicit_v1_stop_contract_failure_still_warns_without_blocking(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(
        repo,
        allowed_files=["src/allowed.py"],
        production_data_access=True,
        control_contract_version=1,
    )

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["systemMessage"].startswith("Tenn agent-job contract blocked")
    assert "production_data_access" in str(payload["systemMessage"])
    assert "decision" not in payload


@pytest.mark.parametrize("event", ["Stop", "SessionEnd"])
def test_v2_terminal_event_contract_failure_hard_blocks(tmp_path: Path, event: str) -> None:
    repo = git_repo(tmp_path)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event=event,
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "RUN_OUTCOME.json" in str(payload["reason"])


def test_invalid_v2_task_card_stop_hard_blocks(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        production_data_access=True,
        control_contract_version=2,
    )

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "production_data_access" in str(payload["reason"])


@pytest.mark.parametrize("declared", ["", "null", "~", "2.0", "true", "'2'", "3"])
def test_malformed_declared_contract_version_stop_hard_blocks(
    tmp_path: Path, declared: str
) -> None:
    repo = git_repo(tmp_path)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    card.write_text(
        card.read_text(encoding="utf-8").replace(
            "control_contract_version: 2",
            f"control_contract_version: {declared}",
        ),
        encoding="utf-8",
    )

    completed, payload = run_hook(
        repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"}
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "control_contract_version" in str(payload["reason"])


def test_stop_runtime_task_card_missing_closeout_proof_warns(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "hook-runtime-job"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text("State: DONE\nOnly logs were checked.\n", encoding="utf-8")
    task_card(
        repo,
        allowed_files=["reports/agent_jobs/hook-runtime-job/REPORT.md"],
        job_id="hook-runtime-job",
        body="Runtime service repair.",
    )

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["systemMessage"].startswith("Tenn agent-job contract blocked")
    assert "runtime_functionality_proof" in str(payload["systemMessage"])
    assert "cannot use DONE" in str(payload["systemMessage"])


def test_stop_runtime_task_card_control_plane_mention_still_warns(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "hook-runtime-job"
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text("State: DONE\nOnly logs were checked.\n", encoding="utf-8")
    task_card(
        repo,
        allowed_files=["reports/agent_jobs/hook-runtime-job/REPORT.md"],
        job_id="hook-runtime-job",
        body="Runtime service repair for a control-plane status check.",
    )

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["systemMessage"].startswith("Tenn agent-job contract blocked")
    assert "runtime_functionality_proof" in str(payload["systemMessage"])


def test_codex_stop_output_is_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="codex",
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}
    assert not (repo / "reports" / "agent_jobs" / "hook-test-job" / "diff-check.json").exists()


def test_claude_stop_and_session_end_outputs_are_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    for event in ("Stop", "SessionEnd"):
        completed, payload = run_hook(
            repo,
            env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
            platform="claude",
            event=event,
        )

        assert completed.returncode == 0
        assert isinstance(payload, dict)


def test_gemini_before_tool_no_active_task_card_allows_with_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        platform="gemini",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload == {"decision": "allow"}


def test_gemini_before_tool_active_task_card_allows_without_report_artifact(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="gemini",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload == {
        "decision": "allow",
        "additionalContext": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md",
    }
    assert not (repo / "reports" / "agent_jobs" / "hook-test-job" / "diff-check.json").exists()


def test_gemini_before_tool_outside_diff_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="gemini",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "src/outside.py" in str(payload["reason"])
    assert "src/outside.py" in str(payload["additionalContext"])


def test_active_task_marker_is_supported(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    marker = repo / ".tenn" / "active_agent_task"
    marker.parent.mkdir()
    marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload == {}


def test_stop_registry_check_is_read_only_without_creating_registry_root(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    missing_registry_root = tmp_path / "missing-registry"

    completed, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_REGISTRY_ROOT": str(missing_registry_root),
            "TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md",
        },
    )

    assert completed.returncode == 0
    assert payload == {}
    assert not missing_registry_root.exists()


def test_stop_does_not_block_on_registry_overlap(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    shared_root = tmp_path / "shared-registry"
    active = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        job_id="active-lock",
        lane="Evaluation",
        filename="active-lock.md",
    )
    overlap = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        job_id="hook-overlap",
        lane="Reporting",
        filename="overlap.md",
    )
    run_git(repo, "add", str(active.relative_to(repo)), str(overlap.relative_to(repo)))
    run_git(repo, "commit", "-m", "add shared registry hook cards")
    claim_completed, claim_payload = run_repo_registry(
        repo,
        "claim",
        active.relative_to(repo).as_posix(),
        env={"TENN_AGENT_REGISTRY_ROOT": str(shared_root)},
    )
    assert claim_completed.returncode == 0
    assert claim_payload["registry_root"] == str(shared_root.resolve())

    completed, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_REGISTRY_ROOT": str(shared_root),
            "TENN_AGENT_TASK_CARD": overlap.relative_to(repo).as_posix(),
        },
    )

    assert completed.returncode == 0
    assert payload == {}


def test_claude_stop_hook_no_longer_contains_plain_diff_output() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    stop_commands = [
        hook["command"]
        for group in settings["hooks"]["Stop"]
        for hook in group["hooks"]
        if hook.get("type") == "command"
    ]

    assert any("scripts/agent_job_hook.py --platform claude --event Stop" in command for command in stop_commands)
    assert not any(command.strip() == "git diff --stat HEAD 2>/dev/null || true" for command in stop_commands)


def test_gemini_before_tool_runs_task_card_hook() -> None:
    settings = json.loads((REPO_ROOT / ".gemini" / "settings.json").read_text(encoding="utf-8"))
    before_tool_commands = [
        hook["command"]
        for group in settings["hooks"]["BeforeTool"]
        for hook in group["hooks"]
        if hook.get("type") == "command"
    ]

    assert any(
        "scripts/agent_job_hook.py --platform gemini --event BeforeTool" in command
        for command in before_tool_commands
    )
