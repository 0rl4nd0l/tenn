from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import pytest

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


def sample_scope_metadata(**overrides: object) -> dict[str, object]:
    entry = sample_entry(**overrides)
    return {
        "job_id": overrides.get("job_id", "candidate-job"),
        "computed_scope_fingerprint": entry["scope_fingerprint"],
        **{field: entry[field] for field in ledger.SCOPE_FINGERPRINT_FIELDS},
        "program_track": entry["program_track"],
    }


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
    decision_ledger = ledger.resolve_live_ledger_path(repo)

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
    decision_ledger = ledger.resolve_live_ledger_path(repo)
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, sample_entry())

    appended, append_payload = run_cli(
        repo,
        "append",
        "--entry-file",
        str(entry_file),
        "--authorize-unclaimed-seed",
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


def test_standalone_append_requires_explicit_unclaimed_seed_authorization(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = ledger.resolve_live_ledger_path(repo)
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, sample_entry())

    completed, payload = run_cli(
        repo,
        "append",
        "--entry-file",
        str(entry_file),
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "--authorize-unclaimed-seed" in str(payload["issues"])
    assert not decision_ledger.exists()


def test_append_rejects_duplicate_id_without_writing_a_second_line(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path / "repo")
    decision_ledger = ledger.resolve_live_ledger_path(repo)
    entry_file = tmp_path / "entry.json"
    write_entries(decision_ledger, sample_entry())
    write_entries(entry_file, sample_entry(run_id="run-2"))

    completed, payload = run_cli(
        repo,
        "append",
        "--entry-file",
        str(entry_file),
        "--authorize-unclaimed-seed",
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("duplicate" in issue for issue in payload["issues"])
    assert len(decision_ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_standalone_seed_append_rejects_custom_ledger_path(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo")
    outside = tmp_path / "outside.jsonl"
    entry_file = tmp_path / "entry.json"
    write_entries(entry_file, sample_entry())

    completed, payload = run_cli(
        repo,
        "append",
        "--entry-file",
        str(entry_file),
        "--ledger-path",
        str(outside),
        "--authorize-unclaimed-seed",
    )

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "live shared ledger" in str(payload["issues"])
    assert not outside.exists()


def test_append_rejects_semantic_replay_with_new_identity(
    tmp_path: Path,
) -> None:
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    original = sample_entry()
    ledger.append_entry(decision_ledger, original, seed_authorized=True)
    replay = sample_entry(
        decision_id="greyhound-floor-663-reclaimed-v2",
        task_id="greyhound_historical_floor_review_reclaimed_v2",
        run_id="run-2",
        validated_at="2026-07-13T02:00:00Z",
        evidence_refs=["reports/weekly/copied_report.json"],
        supersedes_decision_id=original["decision_id"],
    )

    with pytest.raises(ledger.DecisionLedgerError, match="semantic replay"):
        ledger.append_entry(decision_ledger, replay, seed_authorized=True)

    assert len(decision_ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_append_does_not_treat_outcome_status_toggle_as_material_change(
    tmp_path: Path,
) -> None:
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    original = sample_entry()
    ledger.append_entry(decision_ledger, original, seed_authorized=True)
    replay = sample_entry(
        decision_id="greyhound-floor-663-reused-v2",
        task_id="greyhound_historical_floor_reuse_v2",
        run_id="run-2",
        outcome_status="REUSED_COMPLETE",
        decision_delta="The prior decision was reused without changing proof state.",
        supersedes_decision_id=original["decision_id"],
        validated_at="2026-07-13T02:00:00Z",
    )

    with pytest.raises(ledger.DecisionLedgerError, match="semantic replay"):
        ledger.append_entry(decision_ledger, replay, seed_authorized=True)


def test_validate_rejects_no_delta_explicit_supersession() -> None:
    original = sample_entry()
    successor = sample_entry(
        decision_id="greyhound-floor-663-conflict-v2",
        run_id="run-2",
        phase_before=original["phase_after"],
        phase_after="historical_floor_conflicted",
        decision="CONFLICT",
        outcome_status="EVIDENCE_CONFLICT",
        decision_delta="NO_DELTA",
        supersedes_decision_id=original["decision_id"],
        validated_at="2026-07-13T02:00:00Z",
    )

    issues = ledger.validate_entries([original, successor])

    assert any(
        "explicit supersession requires a semantic decision delta" in issue
        for issue in issues
    )


def test_classify_v2_scope_exact_resolved_and_active_duplicate() -> None:
    entry = sample_entry()
    metadata = sample_scope_metadata()

    resolved = ledger.classify_v2_scope(
        metadata,
        active_jobs=[],
        decision_matches=[entry],
    )
    duplicate = ledger.classify_v2_scope(
        metadata,
        active_jobs=[
            {
                "job_id": "other-job",
                "scope_fingerprint": metadata["computed_scope_fingerprint"],
                "status": "active",
                "stale": False,
            }
        ],
        decision_matches=[],
    )

    assert resolved["status"] == "REUSED_COMPLETE"
    assert resolved["scope_admitted"] is False
    assert duplicate["status"] == "ACTIVE_DUPLICATE"
    assert duplicate["scope_admitted"] is False


def test_classify_v2_scope_admits_changed_evidence_and_new_hypothesis() -> None:
    prior = sample_entry()
    changed_evidence = sample_scope_metadata(
        dataset_version="663-race-snapshot-20260714",
        evidence_hash="sha256:" + "3" * 64,
    )
    new_hypothesis = sample_scope_metadata(hypothesis_id="feature_repair_v2")

    changed = ledger.classify_v2_scope(
        changed_evidence,
        active_jobs=[],
        decision_matches=[prior],
    )
    hypothesis = ledger.classify_v2_scope(
        new_hypothesis,
        active_jobs=[],
        decision_matches=[prior],
    )

    assert changed["status"] == "ALLOW_CHANGED_EVIDENCE"
    assert changed["scope_admitted"] is True
    assert hypothesis["status"] == "ALLOW_NEW_HYPOTHESIS"
    assert hypothesis["scope_admitted"] is True


def test_classify_v2_scope_stops_third_unchanged_no_delta_continuation() -> None:
    first = sample_entry(
        decision_id="no-delta-1",
        target_transition="related_transition_one",
        decision="DATA_MISSING",
        outcome_status="DATA_MISSING",
        decision_delta="NO_DELTA",
    )
    second = sample_entry(
        decision_id="no-delta-2",
        target_transition="related_transition_two",
        decision="DATA_MISSING",
        outcome_status="DATA_MISSING",
        decision_delta="UNCHANGED",
    )

    classified = ledger.classify_v2_scope(
        sample_scope_metadata(),
        active_jobs=[],
        decision_matches=[first, second],
    )

    assert classified["status"] == "LOOP_GUARD_STOP"
    assert classified["scope_admitted"] is False
    assert classified["no_delta_outcomes"] == 2


def test_loop_guard_precedes_explicit_does_not_block_on_same_track() -> None:
    first = sample_entry(
        decision_id="no-delta-explicit-nonblock-1",
        target_transition="related_transition_one",
        decision="DATA_MISSING",
        outcome_status="DATA_MISSING",
        decision_delta="NO_DELTA",
        does_not_block=["historical_sample_floor_cleared"],
    )
    second = sample_entry(
        decision_id="no-delta-explicit-nonblock-2",
        target_transition="related_transition_two",
        decision="DATA_MISSING",
        outcome_status="DATA_MISSING",
        decision_delta="UNCHANGED",
        does_not_block=["historical_sample_floor_cleared"],
    )

    classified = ledger.classify_v2_scope(
        sample_scope_metadata(),
        active_jobs=[],
        decision_matches=[first, second],
    )

    assert classified["status"] == "LOOP_GUARD_STOP"
    assert classified["scope_admitted"] is False
    assert classified["no_delta_outcomes"] == 2


def test_classify_v2_scope_keeps_prospective_gate_off_offline_track() -> None:
    prospective = sample_entry(
        decision_id="prospective-gate-missing",
        program_track="prospective_readiness",
        target_transition="promotion_ready",
        phase_after="promotion_blocked",
        decision="DATA_MISSING",
        outcome_status="DATA_MISSING",
        decision_delta="NO_DELTA",
        blocks=["promotion_ready"],
        does_not_block=["historical_sample_floor_cleared"],
    )

    classified = ledger.classify_v2_scope(
        sample_scope_metadata(),
        active_jobs=[],
        decision_matches=[prospective],
    )

    assert classified["status"] == "ALLOW_NEW_SCOPE"
    assert classified["scope_admitted"] is True


def test_classify_v2_scope_stays_in_parity_with_portable_git_guard() -> None:
    guard_namespace = runpy.run_path(
        str(
            REPO_ROOT
            / ".agents"
            / "skills"
            / "tenn-git-guard"
            / "scripts"
            / "tenn_git_guard.py"
        )
    )
    guard_classifier = guard_namespace["classify_v2_scope"]
    metadata = sample_scope_metadata()
    scenarios = [
        ([], [sample_entry()]),
        (
            [
                {
                    "job_id": "other-job",
                    "scope_fingerprint": metadata["computed_scope_fingerprint"],
                    "status": "active",
                    "stale": False,
                }
            ],
            [],
        ),
        (
            [],
            [
                sample_entry(
                    decision_id="no-delta-1",
                    target_transition="related-one",
                    decision="DATA_MISSING",
                    outcome_status="DATA_MISSING",
                    decision_delta="NO_DELTA",
                ),
                sample_entry(
                    decision_id="no-delta-2",
                    target_transition="related-two",
                    decision="DATA_MISSING",
                    outcome_status="DATA_MISSING",
                    decision_delta="UNCHANGED",
                ),
            ],
        ),
    ]

    for active_jobs, entries in scenarios:
        decision_matches = [
            {
                "entry": entry,
                "is_no_delta": not ledger.has_decision_delta(
                    entry.get("decision_delta")
                ),
            }
            for entry in entries
        ]
        assert ledger.classify_v2_scope(
            metadata,
            active_jobs=active_jobs,
            decision_matches=decision_matches,
        ) == guard_classifier(
            metadata,
            active_jobs=active_jobs,
            decision_matches=decision_matches,
        )


def test_append_requires_explicit_latest_head_for_material_same_scope_change(
    tmp_path: Path,
) -> None:
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    original = sample_entry()
    ledger.append_entry(decision_ledger, original, seed_authorized=True)
    conflict = sample_entry(
        decision_id="greyhound-floor-663-conflict-v2",
        run_id="run-2",
        phase_before=original["phase_after"],
        phase_after="historical_floor_conflicted",
        decision="CONFLICT",
        outcome_status="EVIDENCE_CONFLICT",
        decision_delta="A source-integrity check disproved the recorded floor.",
        blocks=["historical sample-floor claim"],
        does_not_block=["offline parser research"],
        validated_at="2026-07-13T02:00:00Z",
    )

    with pytest.raises(ledger.DecisionLedgerError, match="supersedes_decision_id"):
        ledger.append_entry(decision_ledger, conflict, seed_authorized=True)

    conflict["supersedes_decision_id"] = original["decision_id"]
    ledger.append_entry(decision_ledger, conflict, seed_authorized=True)
    assert [
        entry["decision"] for entry in ledger.load_entries(decision_ledger)
    ] == ["PASS", "CONFLICT"]


def test_append_rejects_stale_supersession_and_phase_discontinuity(
    tmp_path: Path,
) -> None:
    decision_ledger = tmp_path / "decision-ledger.jsonl"
    original = sample_entry()
    conflict = sample_entry(
        decision_id="greyhound-floor-663-conflict-v2",
        run_id="run-2",
        phase_before=original["phase_after"],
        phase_after="historical_floor_conflicted",
        decision="CONFLICT",
        outcome_status="EVIDENCE_CONFLICT",
        decision_delta="The source-integrity check changed the decision.",
        blocks=["historical sample-floor claim"],
        validated_at="2026-07-13T02:00:00Z",
        supersedes_decision_id=original["decision_id"],
    )
    ledger.append_entry(decision_ledger, original, seed_authorized=True)
    ledger.append_entry(decision_ledger, conflict, seed_authorized=True)

    stale = sample_entry(
        decision_id="greyhound-floor-663-reopened-v3",
        run_id="run-3",
        phase_before="wrong_phase",
        phase_after="historical_floor_reopened",
        decision="PASS",
        outcome_status="ADVANCED",
        decision_delta="New integrity evidence restored the decision.",
        supersedes_decision_id=original["decision_id"],
        validated_at="2026-07-13T03:00:00Z",
    )
    with pytest.raises(ledger.DecisionLedgerError, match="latest decision"):
        ledger.append_entry(decision_ledger, stale, seed_authorized=True)

    stale["supersedes_decision_id"] = conflict["decision_id"]
    with pytest.raises(ledger.DecisionLedgerError, match="phase_before"):
        ledger.append_entry(decision_ledger, stale, seed_authorized=True)


def test_validate_keeps_legacy_same_scope_rows_compatible(tmp_path: Path) -> None:
    original = sample_entry()
    legacy_duplicate = sample_entry(
        decision_id="legacy-reclaimed-copy",
        task_id="legacy-reclaimed-task",
        run_id="legacy-run-2",
        validated_at="2026-07-13T02:00:00Z",
    )

    issues = ledger.validate_entries(
        [original, legacy_duplicate], source=str(tmp_path / "legacy-ledger.jsonl")
    )

    assert issues == []


def test_validate_rejects_invalid_explicit_lineage(tmp_path: Path) -> None:
    original = sample_entry()
    invalid_successor = sample_entry(
        decision_id="invalid-explicit-successor",
        run_id="run-2",
        phase_before="wrong-phase",
        phase_after="historical_floor_conflicted",
        decision="CONFLICT",
        outcome_status="EVIDENCE_CONFLICT",
        decision_delta="The decision changed.",
        supersedes_decision_id="not-the-current-head",
        validated_at="2026-07-13T02:00:00Z",
    )

    issues = ledger.validate_entries(
        [original, invalid_successor], source=str(tmp_path / "ledger.jsonl")
    )

    assert any("latest chain head" in issue for issue in issues)
    assert any("phase_before" in issue for issue in issues)


def test_concurrent_semantic_replays_append_exactly_once(tmp_path: Path) -> None:
    decision_ledger = tmp_path / "registry" / "decision-ledger.jsonl"
    candidates = (
        sample_entry(decision_id="scope-race-1", run_id="run-1"),
        sample_entry(decision_id="scope-race-2", run_id="run-2"),
    )

    def append(candidate: dict[str, object]) -> str:
        try:
            ledger.append_entry(
                decision_ledger, candidate, seed_authorized=True
            )
        except ledger.DecisionLedgerError as exc:
            return str(exc)
        return "ok"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, candidates))

    assert results.count("ok") == 1
    assert sum("semantic replay" in result for result in results) == 1
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
