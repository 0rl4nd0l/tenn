from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from scripts import agent_decision_ledger as ledger


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "agent_decision_ledger.py"


def sample_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "decision_id": "greyhound-floor-663-v1",
        "task_id": "greyhound_historical_floor_review_v1",
        "run_id": "run-20260713T010000Z",
        "project_id": "greyhound_racing_collector",
        "claim_id": "historical_source_floor",
        "hypothesis_id": "thedogs_history_clears_floor",
        "program_track": "offline_development",
        "source_class": "thedogs_published_market_history",
        "dataset_version": "663-race-snapshot-20260709",
        "evidence_hash": "sha256:" + "2" * 64,
        "target_transition": "historical_sample_floor_cleared",
        "phase_before": "historical_floor_unproven",
        "phase_after": "historical_floor_cleared",
        "decision": "PASS",
        "outcome_status": "ADVANCED",
        "decision_delta": "The verified snapshot contains 663 eligible races.",
        "evidence_refs": ["reports/weekly/rolling_model_comparison.json"],
        "blocks": [],
        "does_not_block": ["prospective Sportsbet capture"],
        "validated_at": "2026-07-13T01:00:00Z",
        "invalidation_conditions": ["The recorded evidence hash is disproved."],
        "reopen_conditions": ["A new dataset version or evidence hash is supplied."],
    }
    entry.update(overrides)
    if "scope_fingerprint" not in overrides:
        entry["scope_fingerprint"] = ledger.compute_scope_fingerprint(entry)
    return entry


def write_entries(path: Path, *entries: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )


def run_cli(
    repo: Path, command: str, *args: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), command, "--repo-root", str(repo), *args],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert completed.stderr == ""
    return completed, json.loads(completed.stdout)


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def make_git_repo(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init")
    run_git(path, "config", "user.email", "decision-ledger@example.invalid")
    run_git(path, "config", "user.name", "Decision Ledger Tests")
    (path / "README.md").write_text("test\n", encoding="utf-8")
    run_git(path, "add", "README.md")
    run_git(path, "commit", "-m", "init")
    return path


def test_linked_worktrees_resolve_one_shared_decision_ledger(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")

    with mock.patch.dict(
        os.environ,
        {"TENN_AGENT_REGISTRY_ROOT": "", "GIT_CONFIG_GLOBAL": os.devnull},
    ):
        primary_path = ledger.resolve_live_ledger_path(repo)
        linked_path = ledger.resolve_live_ledger_path(linked)

    assert primary_path == linked_path
    assert primary_path.name == "decision-ledger.jsonl"
    assert primary_path.parent.name == "tenn-agent-registry"


def test_validate_accepts_complete_entry_with_post_command_repo_root(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, sample_entry())

    completed, payload = run_cli(repo, "validate", "--entry-file", str(entry_file))

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["data_missing"] == []


def test_initialize_requires_explicit_authorization(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")

    completed, payload = run_cli(repo, "initialize")

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "--authorize-create-empty-ledger" in payload["issues"][0]
    assert not ledger.resolve_live_ledger_path(repo).exists()


def test_initialize_is_idempotent_and_never_truncates_existing_ledger(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "registry" / "decision-ledger.jsonl"

    first, first_payload = run_cli(
        repo,
        "initialize",
        "--ledger-path",
        str(decision_ledger),
        "--authorize-create-empty-ledger",
    )
    write_entries(decision_ledger, sample_entry())
    before = decision_ledger.read_bytes()
    repeated, repeated_payload = run_cli(
        repo,
        "initialize",
        "--ledger-path",
        str(decision_ledger),
        "--authorize-create-empty-ledger",
    )

    assert first.returncode == 0
    assert first_payload["created"] is True
    assert first_payload["already_initialized"] is False
    assert repeated.returncode == 0
    assert repeated_payload["created"] is False
    assert repeated_payload["already_initialized"] is True
    assert repeated_payload["entry_count"] == 1
    assert decision_ledger.read_bytes() == before


def test_initialize_is_safe_under_concurrent_calls(tmp_path: Path) -> None:
    path = tmp_path / "registry" / "decision-ledger.jsonl"

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: ledger.initialize_ledger(path, authorized=True),
                range(8),
            )
        )

    assert sum(result["created"] is True for result in results) == 1
    assert sum(result["already_initialized"] is True for result in results) == 7
    assert path.is_file()
    assert path.read_bytes() == b""


def test_initialize_rejects_invalid_existing_ledger_without_truncation(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "registry" / "decision-ledger.jsonl"
    decision_ledger.parent.mkdir(parents=True)
    decision_ledger.write_text("not-json\n", encoding="utf-8")
    before = decision_ledger.read_bytes()

    completed, payload = run_cli(
        repo,
        "initialize",
        "--ledger-path",
        str(decision_ledger),
        "--authorize-create-empty-ledger",
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "existing ledger is invalid" in payload["issues"][0]
    assert decision_ledger.read_bytes() == before


def test_validate_rejects_missing_and_invalid_schema_fields(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    entry = sample_entry(program_track="runtime_guess", outcome_status="DONE")
    del entry["phase_after"]
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, entry)

    completed, payload = run_cli(repo, "validate", "--entry-file", str(entry_file))

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("phase_after" in issue for issue in payload["issues"])
    assert any("program_track" in issue for issue in payload["issues"])
    assert any("outcome_status" in issue for issue in payload["issues"])


def test_validate_rejects_fingerprint_that_does_not_match_semantic_scope(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, sample_entry(scope_fingerprint="f" * 64))

    completed, payload = run_cli(repo, "validate", "--entry-file", str(entry_file))

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("does not match" in issue for issue in payload["issues"])


def test_scope_fingerprint_is_stable_across_mapping_order_and_whitespace() -> None:
    entry = sample_entry()
    reversed_entry = dict(reversed(list(entry.items())))
    padded_entry = dict(entry, project_id="  greyhound_racing_collector  ")

    assert ledger.compute_scope_fingerprint(entry) == ledger.compute_scope_fingerprint(
        reversed_entry
    )
    assert ledger.compute_scope_fingerprint(entry) == ledger.compute_scope_fingerprint(
        padded_entry
    )


def test_scope_fingerprint_canonicalizes_evidence_hash_spelling() -> None:
    upper_bare = sample_entry(evidence_hash="A" * 64)
    lower_prefixed = sample_entry(evidence_hash="  SHA256:" + "a" * 64 + "  ")

    assert ledger.compute_scope_fingerprint(upper_bare) == ledger.compute_scope_fingerprint(
        lower_prefixed
    )


def test_validate_rejects_duplicate_decision_ids(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    write_entries(
        decision_ledger,
        sample_entry(),
        sample_entry(
            run_id="run-2", outcome_status="REUSED_COMPLETE", decision_delta="NO_DELTA"
        ),
    )

    completed, payload = run_cli(
        repo, "validate", "--ledger-path", str(decision_ledger)
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any(
        "duplicate" in issue and "decision_id" in issue for issue in payload["issues"]
    )


def test_markdown_summary_reports_invalid_entries_without_crashing(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    invalid_entry = sample_entry(decision="UNKNOWN")
    del invalid_entry["project_id"]
    write_entries(decision_ledger, invalid_entry)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "summarize",
            "--repo-root",
            str(repo),
            "--ledger-path",
            str(decision_ledger),
            "--format",
            "markdown",
        ],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    assert "<!-- issues:" in completed.stdout
    assert "# Agent Decision Ledger Summary" in completed.stdout


def test_append_search_and_summarize_use_validated_append_only_records(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "registry" / "decision-ledger.jsonl"
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, sample_entry())

    appended, append_payload = run_cli(
        repo,
        "append",
        "--entry-file",
        str(entry_file),
        "--ledger-path",
        str(decision_ledger),
    )
    searched, search_payload = run_cli(
        repo,
        "search",
        "--ledger-path",
        str(decision_ledger),
        "--project-id",
        "greyhound_racing_collector",
        "--claim-id",
        "historical_source_floor",
    )
    summarized, summary_payload = run_cli(
        repo,
        "summarize",
        "--ledger-path",
        str(decision_ledger),
        "--format",
        "json",
    )

    assert appended.returncode == 0
    assert append_payload["ok"] is True
    assert len(decision_ledger.read_text(encoding="utf-8").splitlines()) == 1
    assert searched.returncode == 0
    assert search_payload["ok"] is True
    assert (
        search_payload["matches"][0]["entry"]["decision_id"] == "greyhound-floor-663-v1"
    )
    assert summarized.returncode == 0
    assert summary_payload["total_entries"] == 1
    assert summary_payload["by_decision"]["PASS"] == 1


def test_append_rejects_duplicate_id_without_writing_a_second_line(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    entry_file = tmp_path / "entry.json"
    write_entries(decision_ledger, sample_entry())
    write_entries(entry_file, sample_entry(run_id="run-2"))

    completed, payload = run_cli(
        repo,
        "append",
        "--entry-file",
        str(entry_file),
        "--ledger-path",
        str(decision_ledger),
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("duplicate" in issue for issue in payload["issues"])
    assert len(decision_ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_no_delta_fields_are_exposed_for_loop_guard_recognition(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    no_delta = sample_entry(
        decision_id="greyhound-floor-continuation-1",
        run_id="run-continuation-1",
        decision="PARKED",
        outcome_status="BLOCKED_NO_NEW_INPUT",
        phase_after="historical_floor_unproven",
        decision_delta="NO_DELTA",
    )
    write_entries(decision_ledger, no_delta)

    searched, search_payload = run_cli(
        repo,
        "search",
        "--ledger-path",
        str(decision_ledger),
        "--project-id",
        "greyhound_racing_collector",
        "--claim-id",
        "historical_source_floor",
        "--no-delta-only",
    )
    summarized, summary_payload = run_cli(
        repo,
        "summarize",
        "--ledger-path",
        str(decision_ledger),
    )

    assert searched.returncode == 0
    assert len(search_payload["matches"]) == 1
    assert search_payload["matches"][0]["has_decision_delta"] is False
    assert search_payload["matches"][0]["is_no_delta"] is True
    assert summarized.returncode == 0
    assert summary_payload["no_delta_count"] == 1


def test_advanced_outcome_requires_a_real_decision_delta() -> None:
    issues = ledger.validate_entry(sample_entry(decision_delta="no change"))

    assert any("ADVANCED requires" in issue for issue in issues)


def test_scope_fingerprint_requires_lowercase_policy() -> None:
    issues = ledger.validate_entry(sample_entry(scope_fingerprint="A" * 64))

    assert any("lowercase" in issue for issue in issues)


def test_decision_and_outcome_must_be_compatible() -> None:
    issues = ledger.validate_entry(
        sample_entry(decision="PASS", outcome_status="DATA_MISSING")
    )

    assert any("incompatible" in issue for issue in issues)


def test_live_ledger_requires_strict_one_object_per_jsonl_line(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    pretty_ledger = tmp_path / "pretty-ledger.jsonl"
    pretty_ledger.write_text(
        json.dumps(sample_entry(), indent=2) + "\n", encoding="utf-8"
    )

    completed, payload = run_cli(
        repo, "validate", "--ledger-path", str(pretty_ledger)
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("invalid JSONL object" in issue for issue in payload["issues"])


def test_entry_file_accepts_one_flexible_pretty_json_object(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    entry_file = tmp_path / "entry.json"
    entry_file.write_text(json.dumps(sample_entry(), indent=2) + "\n", encoding="utf-8")

    completed, payload = run_cli(repo, "validate", "--entry-file", str(entry_file))

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["entry_count"] == 1


def test_missing_live_ledger_is_data_missing_and_read_only(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    registry_root = tmp_path / "missing-registry"

    with mock.patch.dict(os.environ, {"TENN_AGENT_REGISTRY_ROOT": str(registry_root)}):
        completed, payload = run_cli(repo, "validate")

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert payload["data_missing"] == ["decision_ledger"]
    assert not registry_root.exists()
