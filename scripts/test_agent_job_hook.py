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
    monkeypatch.delenv("TENN_V2_REQUIRED", raising=False)
    monkeypatch.delenv("TENN_TIER34_AUTHORIZED", raising=False)
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
    capabilities: list[str] | None = None,
) -> Path:
    card = repo / "docs" / "agent_tasks" / filename
    card.parent.mkdir(parents=True, exist_ok=True)
    production_access = "true" if production_data_access else "false"
    effective_allowed = list(allowed_files)
    if control_contract_version == 2:
        decision_candidate = (
            f"reports/agent_jobs/{job_id}/DECISION_ENTRY.json"
        )
        if decision_candidate not in effective_allowed:
            effective_allowed.append(decision_candidate)
    allowed = "\n".join(f"  - {path}" for path in effective_allowed)
    v2_fields: list[str] = []
    if control_contract_version is not None:
        v2_fields.append(f"control_contract_version: {control_contract_version}")
    if control_contract_version == 2:
        declared_capabilities = capabilities or ["READ", "REPORT_WRITE"]
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
                *[
                    f"  - {capability}"
                    for capability in declared_capabilities
                ],
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
    event: str = "BeforeTool",
    hook_input: dict[str, object] | None = None,
    v2_required: bool = True,
    tier34_authorized: bool = True,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    """Run an opted-in V2 check; default-policy tests disable both flags explicitly."""

    merged_env = os.environ.copy()
    if v2_required:
        merged_env["TENN_V2_REQUIRED"] = "1"
    if tier34_authorized:
        merged_env["TENN_TIER34_AUTHORIZED"] = "1"
    if env is not None:
        merged_env.update(env)
    payload = {"hook_event_name": event, **(hook_input or {})}
    completed = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT), "--platform", platform, "--event", event, "--repo-root", str(repo)],
        input=json.dumps(payload),
        cwd=repo,
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return completed, payload


def test_default_no_claim_file_mutation_preserves_legacy_behavior(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")

    completed, payload = run_hook(
        repo,
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
        hook_input={
            "tool_name": "apply_patch",
            "tool_input": {"patch": "*** Begin Patch\n*** Update File: src/allowed.py\n"},
        },
    )

    assert completed.returncode == 0
    assert payload.get("decision") != "block"


@pytest.mark.parametrize(
    "path",
    [
        "docs/guide.md",
        "financial-engine_v2/backend/app/example.py",
        "cockpit-ui/app/example.tsx",
    ],
)
def test_default_tier_one_edits_need_no_task_state(tmp_path: Path, path: str) -> None:
    repo = git_repo(tmp_path / "repo")

    completed, payload = run_hook(
        repo,
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
        hook_input={
            "tool_name": "apply_patch",
            "tool_input": {"patch": f"*** Begin Patch\n*** Update File: {path}\n"},
        },
    )

    assert completed.returncode == 0
    assert payload.get("decision") != "block"


def test_stop_is_nonblocking_even_for_invalid_opted_in_v2(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    card = task_card(repo, allowed_files=["src/allowed.py"], control_contract_version=2)
    card.write_text("not a task card\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": str(card.relative_to(repo))},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload.get("decision") != "block"


def test_default_non_v2_read_only_operation_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    _, payload = run_hook(
        repo,
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
        hook_input={"tool_name": "Bash", "tool_input": {"command": "git status --short"}},
    )
    assert payload.get("decision") != "block"


def test_default_non_v2_tier34_mutation_requires_explicit_authorization(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    hook_input = {
        "tool_name": "Bash",
        "tool_input": {"command": "systemctl --user start tenn.service"},
    }
    _, blocked = run_hook(
        repo,
        event="BeforeTool",
        hook_input=hook_input,
        v2_required=False,
        tier34_authorized=False,
    )
    _, allowed = run_hook(
        repo,
        env={"TENN_TIER34_AUTHORIZED": "1"},
        event="BeforeTool",
        hook_input=hook_input,
        v2_required=False,
        tier34_authorized=False,
    )
    assert blocked["decision"] == "block"
    assert "TENN_TIER34_AUTHORIZED=1" in str(blocked["reason"])
    assert allowed.get("decision") != "block"


def test_command_text_cannot_grant_tier34_authorization(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "TENN_TIER34_AUTHORIZED=1 "
                    "systemctl --user start tenn.service"
                )
            },
        },
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"
    assert "TENN_TIER34_AUTHORIZED=1" in str(payload["reason"])


@pytest.mark.parametrize(
    "command",
    [
        "git branch --show-current",
        "git branch topic",
        "git switch topic",
        "git switch -c topic",
        "git checkout topic",
        "git checkout -b topic",
        "git worktree add /tmp/topic topic",
        "git status --short",
        "git log -1",
        "git diff --stat",
        "git show HEAD",
        "git fetch origin",
        "systemctl --user status tenn.service",
        "docker ps",
        "kubectl get pods",
        "python3 audit_extract_report.py",
        "command -v git reset",
        "printf 'git reset --hard'",
    ],
)
def test_default_non_v2_safe_operations_pass(tmp_path: Path, command: str) -> None:
    repo = git_repo(tmp_path / "repo")
    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        v2_required=False,
        tier34_authorized=False,
    )
    assert payload.get("decision") != "block"


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard",
        "git checkout -- src/allowed.py",
        "sudo /bin/systemctl --user restart tenn.service",
        "env MODE=prod docker stop api",
        "command kubectl delete pod api",
        "git status && systemctl --user start tenn.service",
        "systemctl --user start tenn.service $(unexpected)",
    ],
)
def test_default_non_v2_high_risk_wrapped_or_compound_operations_block(tmp_path: Path, command: str) -> None:
    repo = git_repo(tmp_path / "repo")
    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        v2_required=False,
        tier34_authorized=False,
    )
    assert payload["decision"] == "block"


@pytest.mark.parametrize(
    "command",
    [
        "bash -c 'systemctl --user restart tenn.service'",
        "/bin/bash -lc 'systemctl --user restart tenn.service'",
        "bash -O extglob -c 'git reset --hard'",
        "sh -c 'git reset --hard'",
        "/bin/sh -ec 'git clean -fd'",
        "env MODE=prod bash -c 'systemctl --user restart tenn.service'",
        "MODE=prod command sh -c 'git reset --hard'",
        "sudo env MODE=prod command /bin/bash -c 'systemctl restart tenn.service'",
        "env -S \"bash -c 'git reset --hard'\"",
        "uv run python3 scripts/run_extraction_backfill.py --backfill",
        "git status || git reset --hard",
        "git status; git clean -fd",
        "printf ready | systemctl --user restart tenn.service",
        "systemctl --unknown restart tenn.service",
        "docker --context remote stop api",
        "kubectl --context remote delete pod api",
    ],
)
def test_default_gate_inspects_effective_commands_through_common_wrappers(
    tmp_path: Path,
    command: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"
    assert "TENN_TIER34_AUTHORIZED=1" in str(payload["reason"])


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard",
        "git clean -fdx",
        "git checkout -- src/allowed.py",
        "git checkout -f topic",
        "git checkout -B topic HEAD",
        "git switch --discard-changes topic",
        "git switch -C topic HEAD",
        "git restore src/allowed.py",
        "git restore --staged src/allowed.py",
        "git merge topic",
        "git rebase topic",
        "git cherry-pick HEAD~1",
        "git branch -D topic",
        "git branch --force topic HEAD",
        "git push --force-with-lease origin HEAD",
        "git push --delete origin topic",
        "git push origin :topic",
        "git worktree remove --force /tmp/unknown",
        "git worktree prune",
    ],
)
def test_default_gate_blocks_destructive_git_forms(
    tmp_path: Path,
    command: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"


@pytest.mark.parametrize(
    "command",
    [
        "sqlite3 data.sqlite 'SELECT 1'",
        "sqlite3 -readonly data.sqlite 'EXPLAIN SELECT * FROM results'",
        "sqlite3 data.sqlite \"SELECT 'delete'\"",
        "psql -d tenn -c 'SELECT 1'",
        "psql -d tenn -c \"SELECT 'update'\"",
        "psql --dbname=tenn --command='SHOW server_version'",
        "redis-cli GET current:status",
        "redis-cli GET set",
        "redis-cli --raw INFO server",
    ],
)
def test_default_gate_allows_clearly_read_only_datastore_commands(
    tmp_path: Path,
    command: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload.get("decision") != "block"


@pytest.mark.parametrize(
    "command",
    [
        "sqlite3 data.sqlite 'DELETE FROM results'",
        "sqlite3 data.sqlite \"SELECT writefile('/tmp/result', 'x')\"",
        "sqlite3 data.sqlite",
        "psql -d tenn -c 'UPDATE results SET value = 1'",
        "psql -d tenn -c \"SELECT setval('result_id_seq', 42)\"",
        "psql -d tenn -o /tmp/results.txt -c 'SELECT 1'",
        "psql -d tenn",
        "redis-cli SET current:status running",
        "redis-cli EVAL 'return redis.call(\"DEL\", KEYS[1])' 1 current:status",
    ],
)
def test_default_gate_blocks_mutating_or_ambiguous_datastore_commands(
    tmp_path: Path,
    command: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"
    assert "datastore" in str(payload["reason"])


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("Write", {"file_path": "data/results.sqlite", "content": "database"}),
        ("Edit", {"file_path": "runtime/state.json", "old_string": "a", "new_string": "b"}),
        (
            "apply_patch",
            {"patch": "*** Begin Patch\n*** Update File: queues/pending.json\n*** End Patch\n"},
        ),
        ("write_file", {"path": "stores/vector/index.json", "content": "index"}),
        ("Write", {"file_path": "extraction_outputs/run.json", "content": "output"}),
        ("Write", {"file_path": "secrets/token.txt", "content": "secret"}),
        ("Write", {"file_path": ".env", "content": "TOKEN=secret"}),
        ("Write", {"file_path": "/var/lib/tenn/results.sqlite", "content": "database"}),
    ],
)
def test_default_gate_blocks_direct_mutation_of_sensitive_shared_paths(
    tmp_path: Path,
    tool_name: str,
    tool_input: dict[str, str],
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": tool_name, "tool_input": tool_input},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"
    assert "sensitive shared-state path" in str(payload["reason"])


@pytest.mark.parametrize(
    "path",
    [
        "data/results.sqlite",
        "runtime/state.json",
        "queues/pending.json",
        "stores/vector/index.json",
    ],
)
def test_default_gate_blocks_raw_string_apply_patch_to_sensitive_shared_paths(
    tmp_path: Path,
    path: str,
) -> None:
    repo = git_repo(tmp_path / "repo")
    patch = f"*** Begin Patch\n*** Update File: {path}\n*** End Patch\n"

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": patch},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"
    assert "sensitive shared-state path" in str(payload["reason"])


def test_default_gate_allows_raw_string_apply_patch_to_ordinary_source(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    patch = (
        "*** Begin Patch\n"
        "*** Update File: scripts/example.py\n"
        "*** End Patch\n"
    )

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": patch},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload.get("decision") != "block"


@pytest.mark.parametrize(
    "embedded_authorization",
    [
        "+TENN_TIER34_AUTHORIZED=1\n",
        "+export TENN_TIER34_AUTHORIZED=1\n",
        '+{"TENN_TIER34_AUTHORIZED": "1"}\n',
    ],
)
def test_raw_string_patch_text_cannot_grant_tier34_authorization(
    tmp_path: Path,
    embedded_authorization: str,
) -> None:
    repo = git_repo(tmp_path / "repo")
    patch = (
        "*** Begin Patch\n"
        "*** Update File: data/results.sqlite\n"
        "@@\n"
        f"{embedded_authorization}"
        "*** End Patch\n"
    )

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": patch},
        v2_required=False,
        tier34_authorized=False,
    )

    assert payload["decision"] == "block"
    assert "sensitive shared-state path" in str(payload["reason"])


@pytest.mark.parametrize(
    "path",
    [
        "scripts/example.py",
        "docs/guide.md",
        "tests/test_example.py",
        "reports/agent_jobs/task-local/evidence.json",
        "tmp/task-local/evidence.txt",
        "/tmp/task-local/evidence.sqlite",
        ".env.example",
    ],
)
def test_default_gate_allows_direct_mutation_of_ordinary_task_files(
    tmp_path: Path,
    path: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
        hook_input={
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": "task-local"},
        },
    )

    assert payload.get("decision") != "block"


def test_default_gate_allows_sensitive_file_mutation_only_with_explicit_authorization(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    hook_input = {
        "tool_name": "Write",
        "tool_input": {"file_path": "data/results.sqlite", "content": "database"},
    }

    _, blocked = run_hook(
        repo,
        event="BeforeTool",
        hook_input=hook_input,
        v2_required=False,
        tier34_authorized=False,
    )
    _, allowed = run_hook(
        repo,
        env={"TENN_TIER34_AUTHORIZED": "1"},
        event="BeforeTool",
        hook_input=hook_input,
        v2_required=False,
        tier34_authorized=False,
    )

    assert blocked["decision"] == "block"
    assert allowed.get("decision") != "block"


def test_required_no_claim_blocks_runtime_mutation_but_allows_read_probe(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    env = {"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""}

    _, blocked = run_hook(
        repo,
        env=env,
        event="BeforeTool",
        tier34_authorized=False,
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": "systemctl --user start greyhound.service"},
        },
    )
    _, allowed = run_hook(
        repo,
        env=env,
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": "git status --short"},
        },
    )

    assert blocked["decision"] == "block"
    assert "Tenn Tier 3/4 action blocked" in str(blocked["reason"])
    assert allowed.get("decision") != "block"


def test_required_no_claim_blocks_missing_or_unknown_bash_command(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    env = {"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""}

    for tool_input in ({}, {"command": "custom-mutator --do-it"}):
        _, payload = run_hook(
            repo,
            env=env,
            event="BeforeTool",
            hook_input={"tool_name": "Bash", "tool_input": tool_input},
        )
        assert payload["decision"] == "block"


def test_required_no_claim_allows_only_single_task_card_bootstrap(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    env = {"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""}
    task_only = (
        "*** Begin Patch\n"
        "*** Add File: docs/agent_tasks/new-v2.md\n"
        "+---\n"
        "+control_contract_version: 2\n"
        "+---\n"
        "*** End Patch\n"
    )
    mixed = task_only.replace(
        "*** End Patch",
        "*** Update File: src/allowed.py\n@@\n-old\n+new\n*** End Patch",
    )

    _, allowed = run_hook(
        repo,
        env=env,
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": {"patch": task_only}},
    )
    _, blocked = run_hook(
        repo,
        env=env,
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": {"patch": mixed}},
    )

    assert allowed.get("decision") != "block"
    assert blocked["decision"] == "block"


@pytest.mark.parametrize("operation", ["Add", "Update"])
def test_required_no_claim_allows_raw_string_task_card_bootstrap(
    tmp_path: Path,
    operation: str,
) -> None:
    repo = git_repo(tmp_path / "repo")
    patch = (
        "*** Begin Patch\n"
        f"*** {operation} File: docs/agent_tasks/new-v2.md\n"
        "+---\n"
        "+control_contract_version: 2\n"
        "+---\n"
        "*** End Patch\n"
    )

    _, payload = run_hook(
        repo,
        env={"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""},
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": patch},
    )

    assert payload.get("decision") != "block"


@pytest.mark.parametrize(
    "patch",
    [
        (
            "*** Begin Patch\n"
            "*** Add File: docs/agent_tasks/new-v2.md\n"
            "+---\n"
            "+control_contract_version: 2\n"
            "+---\n"
            "*** Update File: src/allowed.py\n"
            "*** End Patch\n"
        ),
        "*** Begin Patch\n*** End Patch\n",
        (
            "*** Begin Patch\n"
            "*** Update File: docs/agent_tasks/new-v2.md\n"
            "*** Move to: docs/agent_tasks/moved-v2.md\n"
            "*** End Patch\n"
        ),
    ],
)
def test_required_no_claim_blocks_unsafe_raw_string_task_card_bootstrap(
    tmp_path: Path,
    patch: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        env={"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""},
        event="BeforeTool",
        hook_input={"tool_name": "apply_patch", "tool_input": patch},
    )

    assert payload["decision"] == "block"


def test_required_exact_v2_claim_command_breaks_bootstrap_deadlock(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    env = {
        "TENN_V2_REQUIRED": "1",
        "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
    }

    completed, payload = run_hook(
        repo,
        env=env,
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "python3 scripts/agent_job_registry.py claim "
                    "docs/agent_tasks/test-task.md --repo-root ."
                )
            },
        },
    )

    assert completed.returncode == 0
    assert payload.get("decision") != "block"
    assert "V2 claim bootstrap" in str(payload)


def test_required_exact_ledger_initialize_breaks_bootstrap_deadlock(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo", vendor_control_plane_scripts=False)
    command = (
        f"python3 {DECISION_LEDGER_SCRIPT} initialize --repo-root {repo} "
        "--authorize-create-empty-ledger"
    )

    _, allowed = run_hook(
        repo,
        env={"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""},
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
    )
    _, blocked = run_hook(
        repo,
        env={"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": f"python3 {DECISION_LEDGER_SCRIPT} initialize --repo-root {repo}"
            },
        },
    )

    assert allowed.get("decision") != "block"
    assert "initialization bootstrap admitted" in str(allowed)
    assert blocked["decision"] == "block"


def test_required_v1_mutation_blocks_while_default_v1_still_passes(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=1,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare v1 task")
    hook_input = {
        "tool_name": "apply_patch",
        "tool_input": {"patch": "*** Begin Patch\n*** Update File: src/allowed.py\n"},
    }
    selected = {"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()}

    _, default = run_hook(
        repo,
        env=selected,
        event="BeforeTool",
        hook_input=hook_input,
        v2_required=False,
        tier34_authorized=False,
    )
    _, required = run_hook(
        repo,
        env={**selected, "TENN_V2_REQUIRED": "1"},
        event="BeforeTool",
        hook_input=hook_input,
    )

    assert default.get("decision") != "block"
    assert required["decision"] == "block"
    assert "control_contract_version: 2" in str(required["reason"])


def test_required_stop_without_claim_allows_trivial_session(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, default = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""}, event="Stop")
    _, required = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "", "TENN_V2_REQUIRED": "1"},
        event="Stop",
    )

    assert default == {}
    assert required == {}


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


def release_v2_job(repo: Path, job_id: str = "hook-test-job") -> tuple[
    subprocess.CompletedProcess[str], dict[str, object]
]:
    completed = subprocess.run(
        [
            sys.executable,
            str(REGISTRY_SCRIPT),
            "release",
            job_id,
            "--repo-root",
            str(repo),
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed, json.loads(completed.stdout)


def claimed_active_record_path(repo: Path, claim: dict[str, object]) -> Path:
    path = Path(str(claim["active_record"]))
    return path if path.is_absolute() else repo / path


def write_matching_v2_decision(
    repo: Path,
    card: Path,
    *,
    run_id: str,
    seed: bool = False,
    **overrides: object,
) -> None:
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
    if not seed:
        candidate = (
            repo
            / "reports"
            / "agent_jobs"
            / str(metadata["job_id"])
            / "DECISION_ENTRY.json"
        )
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(
            json.dumps(entry, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return
    completed = subprocess.run(
        [
            sys.executable,
            str(DECISION_LEDGER_SCRIPT),
            "append",
            "--repo-root",
            str(repo),
            "--entry-json",
            json.dumps(entry, sort_keys=True),
            "--authorize-unclaimed-seed",
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
    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        v2_required=False,
        tier34_authorized=False,
    )

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
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {}
    assert not (repo / "scripts").exists()


def test_portable_v2_stop_passes_without_target_decision_ledger(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    completed, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
        },
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}
    assert not (repo / "scripts").exists()


def test_required_terminal_hook_accepts_validated_release_receipt(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    write_valid_v2_outcome(repo, card)
    run_id = str(claim["record"]["session_id"])
    write_matching_v2_decision(repo, card, run_id=run_id)
    released = subprocess.run(
        [
            sys.executable,
            str(REGISTRY_SCRIPT),
            "release",
            "hook-test-job",
            "--repo-root",
            str(repo),
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert released.returncode == 0, released.stdout + released.stderr
    assert json.loads(released.stdout)["closeout_validated"] is True

    completed, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
            "TENN_TIER34_AUTHORIZED": "1",
        },
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


def test_required_terminal_hook_passes_forged_release_decision_id(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    write_valid_v2_outcome(repo, card)
    write_matching_v2_decision(
        repo,
        card,
        run_id=str(claim["record"]["session_id"]),
    )
    released_completed, released_payload = release_v2_job(repo)
    assert released_completed.returncode == 0
    status_path = Path(str(released_payload["status_path"]))
    if not status_path.is_absolute():
        status_path = repo / status_path
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["decision_id"] = "forged-but-nonempty"
    status_path.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")

    _, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
        },
        event="Stop",
    )

    assert payload == {}


def test_required_terminal_hook_passes_superseded_release_decision(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    write_valid_v2_outcome(repo, card)
    write_matching_v2_decision(
        repo,
        card,
        run_id=str(claim["record"]["session_id"]),
    )
    released_completed, _ = release_v2_job(repo)
    assert released_completed.returncode == 0

    candidate_path = (
        repo
        / "reports"
        / "agent_jobs"
        / "hook-test-job"
        / "DECISION_ENTRY.json"
    )
    successor = json.loads(candidate_path.read_text(encoding="utf-8"))
    successor.update(
        {
            "decision_id": "hook-test-decision-superseding",
            "task_id": "later-task",
            "run_id": "later-run",
            "phase_before": successor["phase_after"],
            "phase_after": "contract_rejected",
            "decision": "FAIL",
            "decision_delta": "Later evidence invalidated the earlier pass.",
            "supersedes_decision_id": successor["decision_id"],
            "validated_at": "2026-07-14T01:00:00Z",
        }
    )
    appended = subprocess.run(
        [
            sys.executable,
            str(DECISION_LEDGER_SCRIPT),
            "append",
            "--repo-root",
            str(repo),
            "--entry-json",
            json.dumps(successor, sort_keys=True),
            "--authorize-unclaimed-seed",
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert appended.returncode == 0, appended.stdout + appended.stderr

    _, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
        },
        event="Stop",
    )

    assert payload == {}


def test_required_post_release_stop_without_selector_is_allowed(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    write_valid_v2_outcome(repo, card)
    write_matching_v2_decision(
        repo,
        card,
        run_id=str(claim["record"]["session_id"]),
    )
    released_completed, _ = release_v2_job(repo)
    assert released_completed.returncode == 0

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "", "TENN_V2_REQUIRED": "1"},
        event="Stop",
    )

    assert payload == {}


def test_exact_resolved_v2_scope_stops_without_new_report(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
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
    write_matching_v2_decision(
        repo,
        card,
        run_id="prior-resolved-run",
        seed=True,
    )

    _, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
        },
        event="Stop",
    )

    assert payload == {}
    assert not (repo / "reports" / "agent_jobs" / "hook-test-job").exists()


def test_exact_reuse_ignores_stale_nonrelease_status_receipt(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
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
    write_matching_v2_decision(
        repo,
        card,
        run_id="prior-resolved-run",
        seed=True,
    )
    status_path = (
        repo / "reports" / "agent_jobs" / "hook-test-job" / "status.json"
    )
    status_path.parent.mkdir(parents=True, exist_ok=True)
    stale = {"status": "abandoned", "job_id": "hook-test-job"}
    status_path.write_text(json.dumps(stale, sort_keys=True), encoding="utf-8")

    _, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
        },
        event="Stop",
    )

    assert payload == {}
    assert json.loads(status_path.read_text(encoding="utf-8")) == stale


def test_active_target_worktree_v2_job_is_enforced_when_opted_in(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare opted-in v2 task")
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
    claim_v2_job(repo, card)
    hook_input = {
        "tool_name": "apply_patch",
        "tool_input": {
            "patch": "*** Begin Patch\n*** Update File: src/outside.py\n*** End Patch\n"
        },
    }

    completed, opted_in = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        hook_input=hook_input,
    )
    _, default = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        hook_input=hook_input,
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert opted_in["decision"] == "block"
    assert "outside task-card allowed_files" in str(opted_in["reason"])
    assert default == {}
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
    assert "abandon and reclaim" in str(payload["reason"])


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


@pytest.mark.parametrize(
    ("failure_mode", "admitted"),
    [("drift", True), ("stale", True), ("corrupt", False)],
)
def test_v2_selector_failure_admits_exact_abandon_recovery(
    tmp_path: Path,
    failure_mode: str,
    admitted: bool,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    claim = claim_v2_job(repo, card)
    active_path = claimed_active_record_path(repo, claim)
    if failure_mode == "drift":
        card.write_text(
            card.read_text(encoding="utf-8").replace(
                "  - REPORT_WRITE",
                "  - REPORT_WRITE\n  - CODE_EDIT",
            ),
            encoding="utf-8",
        )
    elif failure_mode == "stale":
        record = json.loads(active_path.read_text(encoding="utf-8"))
        record["heartbeat_at"] = "2000-01-01T00:00:00Z"
        record["last_seen_at"] = "2000-01-01T00:00:00Z"
        active_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    else:
        active_path.write_text("{", encoding="utf-8")

    command = (
        f"python3 {REGISTRY_SCRIPT} release hook-test-job "
        f"--repo-root {repo} --abandon-reason recovery"
    )
    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "", "TENN_V2_REQUIRED": "1"},
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
    )

    if not admitted:
        assert payload["decision"] == "block"
        assert "invalid JSON" in str(payload["reason"])
        return
    assert payload.get("decision") != "block"
    assert "abandonment admitted" in str(payload)
    abandoned = subprocess.run(
        [
            sys.executable,
            str(REGISTRY_SCRIPT),
            "release",
            "hook-test-job",
            "--repo-root",
            str(repo),
            "--abandon-reason",
            "recovery",
        ],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert abandoned.returncode == 0, abandoned.stdout + abandoned.stderr
    assert json.loads(abandoned.stdout)["status"] == "abandoned"


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
    if event == "Stop":
        assert payload == {}
        return
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
    assert "abandon and reclaim" in str(payload["reason"])


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


def test_claimed_v2_blocks_runtime_command_without_runtime_capability(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare report-only v2 task")
    claim_v2_job(repo, card)

    completed, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix(),
            "TENN_V2_REQUIRED": "1",
            "TENN_TIER34_AUTHORIZED": "1",
        },
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": "systemctl --user start greyhound.service"},
        },
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "RUNTIME_CHANGE" in str(payload["reason"])


@pytest.mark.parametrize(
    "command",
    [
        "sed --in-place src/allowed.py",
        "sed -ni 1p src/allowed.py",
        "journalctl --vacuum-time=1s",
        "journalctl --rotate",
        "find . -fprint0 changed.bin",
        "git branch created-by-bypass",
        "git diff --output=changed.patch",
        "git ls-remote https://example.invalid/repo.git",
        "rg --pre /tmp/mutator needle .",
        "/tmp/git status",
        "python3 /tmp/agent_job_registry.py list-active --read-only",
    ],
)
def test_required_no_claim_blocks_adversarial_read_only_bypasses(
    tmp_path: Path,
    command: str,
) -> None:
    repo = git_repo(tmp_path / "repo")

    _, payload = run_hook(
        repo,
        env={"TENN_V2_REQUIRED": "1", "TENN_AGENT_TASK_CARD": ""},
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
    )

    assert payload["decision"] == "block"
    assert "claim one V2 task card" in str(payload["reason"])


@pytest.mark.parametrize(
    "command",
    [
        "custom-mutator --do-it",
        "python3 arbitrary.py",
        "systemctl --user start greyhound.service && true",
        "git reset --hard",
        "git clean -fd",
        "git checkout -- src/outside.py",
        "git switch master",
        "/tmp/git status",
        "mv src/outside.py src/allowed.py",
        "rm -rf src/allowed.py",
        "chmod -R 755 src/allowed.py",
        "mkdir -p src/allowed.py",
        "cp -R src/outside.py src/allowed.py",
    ],
)
def test_claimed_v2_blocks_unclassified_or_destructive_shell_commands(
    tmp_path: Path,
    command: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=[
            "READ",
            "REPORT_WRITE",
            "RESEARCH_FIT",
            "DATASET_MATERIALIZE",
            "CODE_EDIT",
            "MODEL_PERSIST",
            "DB_COPY_WRITE",
            "CANONICAL_DB_WRITE",
            "RUNTIME_CHANGE",
            "PUBLISH",
        ],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare comprehensive v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
    )

    assert payload["decision"] == "block"
    assert "v2-tool-classification" in str(payload["reason"])


def test_claimed_v2_blocks_adversarial_capability_escape_commands(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=[
            "READ",
            "REPORT_WRITE",
            "RESEARCH_FIT",
            "DATASET_MATERIALIZE",
            "CODE_EDIT",
            "MODEL_PERSIST",
            "DB_COPY_WRITE",
            "RUNTIME_CHANGE",
            "PUBLISH",
        ],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare adversarial v2 task")
    claim_v2_job(repo, card)
    commands = [
        "true & true",
        "systemctl -H status start prod.service",
        "systemctl --machine status stop prod.service",
        "systemctl status --host=prod sshd.service",
        "systemctl status --root=/tmp/root sshd.service",
        "systemctl status -Hremote sshd.service",
        "systemctl status -Mcontainer sshd.service",
        "git -c diff.external=/tmp/mutator diff",
        "git cherry-pick deadbeef",
        "git merge other-branch",
        "git worktree add /tmp/escape branch",
        "git push --force-if-includes origin HEAD",
        "gh workflow run deploy.yml",
        "curl -X DELETE https://example.invalid/runtime",
        "sqlite3 data/copy.db '.shell systemctl restart prod.service'",
        "sqlite3 data/copy.db \"SELECT writefile('/tmp/escape', 'x')\"",
        "python3 -m py_compile src/allowed.py",
        "python3 -m compileall src",
        "python3 train_challenger.py --output data/production.sqlite3",
        "pytest /tmp/test_escape.py",
        "pytest --junitxml=/tmp/result.xml src/allowed.py",
        "uv run --with pytest pytest src/allowed.py",
        (
            f"python3 {CONTRACT_SCRIPT} validate {card} --write-report"
        ),
        (
            f"python3 {REGISTRY_SCRIPT} release another-job --repo-root {repo}"
        ),
        (
            f"python3 {DECISION_LEDGER_SCRIPT} append --repo-root {repo} "
            "--ledger-path /tmp/outside.jsonl --entry-json '{}'"
        ),
    ]

    for command in commands:
        _, payload = run_hook(
            repo,
            env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
            event="BeforeTool",
            hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        )
        assert payload["decision"] == "block", command
        assert "v2-tool-classification" in str(payload["reason"]), command


def test_claimed_v2_trusts_only_digest_matching_portable_guard_copy(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    vendored_guard = (
        repo
        / ".agents"
        / "skills"
        / "tenn-git-guard"
        / "scripts"
        / "tenn_git_guard.py"
    )
    vendored_guard.parent.mkdir(parents=True)
    vendored_guard.write_text("print('mutated guard')\n", encoding="utf-8")
    run_git(repo, "add", vendored_guard.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "add modified portable guard")
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare guard digest task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    f"python3 {vendored_guard.relative_to(repo)} preflight "
                    f"--task-card {card.relative_to(repo)} --json"
                )
            },
        },
    )

    assert payload["decision"] == "block"
    assert "unclassified Python script" in str(payload["reason"])


def test_claimed_v2_admits_hardened_repo_local_pytest_and_frozen_uv_wrapper(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare local validation task")
    claim_v2_job(repo, card)
    hardened = (
        "env PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "
        "pytest -p no:cacheprovider src/allowed.py"
    )

    for command in (
        hardened,
        "uv run --no-sync --frozen " + hardened,
    ):
        _, payload = run_hook(
            repo,
            env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
            event="BeforeTool",
            hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        )
        assert payload.get("decision") != "block", (command, payload)


def test_claimed_v2_git_commit_requires_no_verify_and_classifies_staged_paths(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT", "PUBLISH"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare safe publication task")
    claim_v2_job(repo, card)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")
    run_git(repo, "add", "src/allowed.py")

    _, unsafe = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m test"},
        },
    )
    _, safe = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "git -c core.hooksPath=/dev/null -c core.fsmonitor=false "
                    "commit --no-verify --no-gpg-sign -m test"
                )
            },
        },
    )

    assert unsafe["decision"] == "block"
    assert "--no-verify" in str(unsafe["reason"])
    assert safe.get("decision") != "block"


def test_claimed_v2_git_commit_checks_both_paths_of_staged_rename(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/renamed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT", "PUBLISH"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare rename publication task")
    claim_v2_job(repo, card)
    run_git(repo, "mv", "src/outside.py", "src/renamed.py")

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "git -c core.hooksPath=/dev/null -c core.fsmonitor=false "
                    "commit --no-verify --no-gpg-sign -m rename"
                )
            },
        },
    )

    assert payload["decision"] == "block"
    assert "src/outside.py" in str(payload["reason"])


def test_claimed_v2_git_add_force_admits_only_exact_ignored_report_path(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    report_path = "reports/agent_jobs/hook-test-job/evidence.md"
    card = task_card(
        repo,
        allowed_files=["src/allowed.py", report_path],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "PUBLISH"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare ignored report publication task")
    claim_v2_job(repo, card)

    commands = {
        f"git add -f -- {report_path}": False,
        "git add -f -- reports/agent_jobs/hook-test-job/outside.md": True,
        f"git add -f -- {report_path} -outside.md": True,
        "git add --all": True,
    }
    for command, blocked in commands.items():
        _, payload = run_hook(
            repo,
            env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
            event="BeforeTool",
            hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        )
        assert (payload.get("decision") == "block") is blocked, (command, payload)


def test_research_fit_input_artifacts_are_not_misclassified_as_outputs(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "RESEARCH_FIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare research input task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "python3 train_challenger.py --dataset data/training.parquet "
                    "--model data/baseline.pkl"
                )
            },
        },
    )

    assert payload.get("decision") != "block"


@pytest.mark.parametrize(
    ("script", "capabilities"),
    [
        ("audit_capture_identity.py", ["READ", "REPORT_WRITE"]),
        (
            "evaluate_prediction_snapshots.py",
            ["READ", "REPORT_WRITE", "RESEARCH_FIT"],
        ),
        (
            "run_history_feature_challenger_retest.py",
            ["READ", "REPORT_WRITE", "RESEARCH_FIT"],
        ),
    ],
)
def test_greyhound_diagnostic_and_research_verbs_are_classified(
    tmp_path: Path,
    script: str,
    capabilities: list[str],
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=capabilities,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare Greyhound entrypoint task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": f"python3 {script}"},
        },
    )

    assert payload.get("decision") != "block"


def test_claimed_v2_git_push_requires_configured_remote_and_explicit_head(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    run_git(repo, "remote", "add", "origin", "https://example.invalid/repo.git")
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "PUBLISH"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare exact push task")
    claim_v2_job(repo, card)

    commands = {
        "git push --no-verify origin": True,
        "git push --no-verify origin HEAD:refs/heads/other": True,
        "git push --no-verify https://example.invalid/repo.git HEAD": True,
        "git push --no-verify origin HEAD": False,
    }
    for command, blocked in commands.items():
        _, payload = run_hook(
            repo,
            env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
            event="BeforeTool",
            hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
        )
        assert (payload.get("decision") == "block") is blocked, (command, payload)


def test_train_and_save_requires_research_and_model_persistence(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "RESEARCH_FIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare research-only v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": "python3 train_and_save_model.py"},
        },
    )

    assert payload["decision"] == "block"
    assert "MODEL_PERSIST" in str(payload["reason"])


@pytest.mark.parametrize("declared_capability", ["DB_COPY_WRITE", "CANONICAL_DB_WRITE"])
def test_database_file_write_uses_explicit_declared_path_class(
    tmp_path: Path,
    declared_capability: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    database_path = "data/results.db"
    card = task_card(
        repo,
        allowed_files=[database_path],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", declared_capability],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare path-classified database task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "write_file",
            "tool_input": {"file_path": database_path, "content": "db"},
        },
    )

    assert payload.get("decision") != "block"


def test_database_file_write_rejects_ambiguous_dual_path_class(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    database_path = "data/results.db"
    card = task_card(
        repo,
        allowed_files=[database_path],
        control_contract_version=2,
        capabilities=[
            "READ",
            "REPORT_WRITE",
            "DB_COPY_WRITE",
            "CANONICAL_DB_WRITE",
        ],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare ambiguous database task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "write_file",
            "tool_input": {"file_path": database_path, "content": "db"},
        },
    )

    assert payload["decision"] == "block"
    assert "ambiguous" in str(payload["reason"])


@pytest.mark.parametrize(
    "artifact_path",
    ["data/results.db-wal", "data/results.sqlite-shm", "models/challenger.safetensors"],
)
def test_sensitive_sidecar_and_model_paths_do_not_fall_back_to_code_edit(
    tmp_path: Path,
    artifact_path: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=[artifact_path],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare code-only artifact task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "write_file",
            "tool_input": {"file_path": artifact_path, "content": "artifact"},
        },
    )

    assert payload["decision"] == "block"
    assert any(
        capability in str(payload["reason"])
        for capability in ("DB_COPY_WRITE", "CANONICAL_DB_WRITE", "MODEL_PERSIST")
    )


@pytest.mark.parametrize(
    ("command", "capability"),
    [
        ("python3 train_challenger.py", "RESEARCH_FIT"),
        ("python3 build_dataset.py", "DATASET_MATERIALIZE"),
        ("python3 save_model.py", "MODEL_PERSIST"),
        ("systemctl --user set-property greyhound.service CPUWeight=10", "RUNTIME_CHANGE"),
        ("git push --no-verify origin HEAD", "PUBLISH"),
        ("gh pr create --title test", "PUBLISH"),
    ],
)
def test_claimed_report_only_v2_blocks_each_undeclared_capability(
    tmp_path: Path,
    command: str,
    capability: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    if command.startswith("git push"):
        run_git(repo, "remote", "add", "origin", "https://example.invalid/repo.git")
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare report-only v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={"tool_name": "Bash", "tool_input": {"command": command}},
    )

    assert payload["decision"] == "block"
    assert capability in str(payload["reason"])


@pytest.mark.parametrize(
    ("database_path", "capability"),
    [
        ("data/experiment_copy.db", "DB_COPY_WRITE"),
        ("data/canonical_results.db", "CANONICAL_DB_WRITE"),
    ],
)
def test_claimed_v2_classifies_database_write_lane(
    tmp_path: Path,
    database_path: str,
    capability: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=[database_path],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare database proof v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": f"sqlite3 {database_path} 'DELETE FROM races'"
            },
        },
    )

    assert payload["decision"] == "block"
    assert "sqlite3 shell execution is not admitted" in str(payload["reason"])


def test_claimed_v2_allows_classified_declared_research_fit(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "RESEARCH_FIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare research-fit v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "Bash",
            "tool_input": {"command": "python3 train_challenger.py"},
        },
    )

    assert payload.get("decision") != "block"


def test_report_directory_does_not_hide_model_persistence_capability(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    model_path = "reports/agent_jobs/hook-test-job/challenger.pkl"
    card = task_card(
        repo,
        allowed_files=[model_path],
        control_contract_version=2,
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare report-only model-path v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "write_file",
            "tool_input": {"file_path": model_path, "content": "model"},
        },
    )

    assert payload["decision"] == "block"
    assert "MODEL_PERSIST" in str(payload["reason"])


@pytest.mark.parametrize("tool_name", ["apply_patch", "write_file", "replace"])
def test_claimed_v2_blocks_proposed_file_outside_exact_allowlist(
    tmp_path: Path,
    tool_name: str,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare code-edit v2 task")
    claim_v2_job(repo, card)
    tool_input: dict[str, object]
    if tool_name == "apply_patch":
        tool_input = {
            "patch": "*** Begin Patch\n*** Update File: src/outside.py\n*** End Patch\n"
        }
    else:
        tool_input = {"file_path": "src/outside.py", "content": "outside = 2\n"}

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={"tool_name": tool_name, "tool_input": tool_input},
    )

    assert payload["decision"] == "block"
    assert "outside task-card allowed_files" in str(payload["reason"])


def test_claimed_v2_allows_proposed_file_inside_exact_allowlist(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path, vendor_control_plane_scripts=False)
    card = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        control_contract_version=2,
        capabilities=["READ", "REPORT_WRITE", "CODE_EDIT"],
    )
    run_git(repo, "add", card.relative_to(repo).as_posix())
    run_git(repo, "commit", "-m", "declare code-edit v2 task")
    claim_v2_job(repo, card)

    _, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": card.relative_to(repo).as_posix()},
        event="BeforeTool",
        hook_input={
            "tool_name": "apply_patch",
            "tool_input": {
                "patch": "*** Begin Patch\n*** Update File: src/allowed.py\n*** End Patch\n"
            },
        },
    )

    assert payload.get("decision") != "block"


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
    if event == "Stop":
        assert payload == {}
        return
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

    completed, payload = run_hook(
        repo,
        env=env,
        event=event,
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {}


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
    if event == "Stop":
        assert payload == {}
        return
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
        v2_required=False,
        tier34_authorized=False,
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
        v2_required=False,
        tier34_authorized=False,
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
        v2_required=False,
        tier34_authorized=False,
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
    if event == "Stop":
        assert payload == {}
        return
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
    if event == "Stop":
        assert payload == {}
        return
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


def test_v2_stop_passes_decision_entry_with_mismatched_phases(tmp_path: Path) -> None:
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
    write_matching_v2_decision(
        repo,
        card,
        run_id=str(claim["record"]["session_id"]),
        phase_after="different_phase",
    )

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


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
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {}


def test_active_valid_task_card_with_allowed_diff_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        v2_required=False,
        tier34_authorized=False,
    )

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
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {}


def test_before_tool_outside_diff_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {}


def test_before_tool_invalid_task_card_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(repo, allowed_files=["src/allowed.py"], production_data_access=True)
    run_git(repo, "add", "docs/agent_tasks/test-task.md")
    run_git(repo, "commit", "-m", "invalid task card")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {}


def test_stop_invalid_task_card_passes_without_warning(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(repo, allowed_files=["src/allowed.py"], production_data_access=True)
    run_git(repo, "add", "docs/agent_tasks/test-task.md")
    run_git(repo, "commit", "-m", "invalid task card")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


def test_explicit_v1_stop_contract_failure_passes_without_warning(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(
        repo,
        allowed_files=["src/allowed.py"],
        production_data_access=True,
        control_contract_version=1,
    )

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


@pytest.mark.parametrize("event", ["Stop", "SessionEnd"])
def test_v2_terminal_event_contract_failure_always_passes(tmp_path: Path, event: str) -> None:
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
    assert payload == {}


def test_invalid_v2_task_card_stop_always_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    outcome = "reports/agent_jobs/hook-test-job/RUN_OUTCOME.json"
    task_card(
        repo,
        allowed_files=["src/allowed.py", outcome],
        production_data_access=True,
        control_contract_version=2,
    )

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


@pytest.mark.parametrize("declared", ["", "null", "~", "2.0", "true", "'2'", "3"])
def test_malformed_declared_contract_version_stop_always_passes(
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
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


def test_stop_runtime_task_card_missing_closeout_proof_passes(tmp_path: Path) -> None:
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

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


def test_stop_runtime_task_card_control_plane_mention_passes(tmp_path: Path) -> None:
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

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        event="Stop",
    )

    assert completed.returncode == 0
    assert payload == {}


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
        v2_required=False,
        tier34_authorized=False,
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
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload["decision"] == "allow"
    assert "additionalContext" not in payload
    assert not (repo / "reports" / "agent_jobs" / "hook-test-job" / "diff-check.json").exists()


def test_gemini_before_tool_outside_diff_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="gemini",
        event="BeforeTool",
        v2_required=False,
        tier34_authorized=False,
    )

    assert completed.returncode == 0
    assert payload == {"decision": "allow"}


def test_active_task_marker_is_supported(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    marker = repo / ".tenn" / "active_agent_task"
    marker.parent.mkdir()
    marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        v2_required=False,
        tier34_authorized=False,
    )

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
        event="Stop",
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
        event="Stop",
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


def test_codex_before_tool_runs_task_card_hook_without_repo_wide_v2_flag() -> None:
    settings = json.loads(
        (REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
    )
    commands = [
        hook["command"]
        for group in settings["hooks"]["PreToolUse"]
        for hook in group["hooks"]
        if hook.get("type") == "command"
        and "agent_job_hook.py" in hook.get("command", "")
    ]

    assert any("--event BeforeTool" in command for command in commands)
    assert all("TENN_V2_REQUIRED" not in command for command in commands)
