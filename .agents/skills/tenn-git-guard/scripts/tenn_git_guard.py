#!/usr/bin/env python3
"""Repo-agnostic Tenn git guard preflight.

The guard runner lives with the Tenn skill surface and inspects a target repo via
--repo-root. Runtime/product repos do not need to vendor Tenn control-plane
scripts for guard preflight to work.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


DATA_MISSING = "DATA_MISSING"
REQUIRED_CONTROL_PLANE_FILES = (
    "scripts/agent_job_registry.py",
    "scripts/agent_task_ledger.py",
    "scripts/agent_job_contract.py",
)
KNOWN_CONTROL_PLANE_ROOTS = (
    "tenn-control-plane-task-ledger-status-refresh-v1-20260623",
    "tenn-control-plane-runtime-functionality-proof-v1-20260622",
    "tenn-agent-ledger-runtime-handoff-replay-v1-20260618",
    "tenn-agent-ledger-runtime-handoff-v1-20260617",
)
DEFAULT_FALLBACK_BASE = "origin/migration/clean-runtime-baseline-reconstruct-v1"
DEFAULT_CANONICAL_BRANCH = DEFAULT_FALLBACK_BASE
CANONICAL_BRANCH_REF = "refs/heads/migration/clean-runtime-baseline-reconstruct-v1"
PATH_CLASSIFICATIONS = {
    "VALID_CANONICAL_WORKTREE",
    "VALID_TASK_WORKTREE",
    "SPARSE_EVIDENCE_DIR",
    "RUNTIME_DIR",
    "NOT_GIT_REPO",
    "STALE_PATH",
    "DIRTY_RELATED_WORKTREE",
    "DIRTY_UNRELATED_WORKTREE",
    DATA_MISSING,
}
PATH_BLOCKING_CLASSIFICATIONS = {
    "SPARSE_EVIDENCE_DIR",
    "RUNTIME_DIR",
    "NOT_GIT_REPO",
    "STALE_PATH",
    "DIRTY_RELATED_WORKTREE",
    DATA_MISSING,
}
BLOCKING_DUPLICATE_CLASSES = {
    "ACTIVE_CONTINUE",
    "OPEN_PR_WAIT",
    "MERGED_USE_CANONICAL",
    "STALE_PRESERVE",
    "OWNER_BOUNDARY",
}
DUPLICATE_STATUS_MAP = {
    "ACTIVE_CONTINUE": "CONTINUE",
    "OPEN_PR_WAIT": "DUPLICATE",
    "MERGED_USE_CANONICAL": "ADOPT",
    "STALE_PRESERVE": "PARK",
    "SUPERSEDED_IGNORE": "SUPERSEDE",
    "OWNER_BOUNDARY": "BLOCKED",
    "UNKNOWN_ASK": DATA_MISSING,
    "DATA_MISSING_FALLBACK_REQUIRED": DATA_MISSING,
    "DATA_MISSING_FALLBACK_CHECKED": DATA_MISSING,
    "NO_MATCHING_ACTIVE_WORK_FOUND": "not_applicable",
}


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env or os.environ),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "command": list(command),
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout.rstrip("\n"),
        "stderr": completed.stderr.rstrip("\n"),
    }


def git_command(repo_root: Path, *args: str) -> dict[str, Any]:
    return run_command(["git", "-C", str(repo_root), *args], cwd=repo_root)


def git_text(repo_root: Path, *args: str) -> str | None:
    result = git_command(repo_root, *args)
    if result["returncode"] != 0:
        return None
    return str(result["stdout"]).strip() or None


def topic_tokens(topic: str | None) -> set[str]:
    if not topic:
        return set()
    return {token for token in re.split(r"[^a-z0-9]+", topic.lower()) if len(token) >= 4}


def dirty_rows_match_topic(rows: Sequence[str], topic: str | None) -> bool:
    tokens = topic_tokens(topic)
    if not tokens:
        return False
    haystack = "\n".join(rows).lower()
    return any(token in haystack for token in tokens)


def path_indicates_runtime(path: Path, requested_path: Path | None = None) -> bool:
    for candidate in (requested_path, path):
        if candidate is None:
            continue
        if candidate.name.endswith("-runtime"):
            return True
        if "runtime" in candidate.parts:
            return True
    return False


def json_from_stdout(result: Mapping[str, Any]) -> Any:
    stdout = str(result.get("stdout") or "")
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def valid_control_plane_root(path: Path | None) -> bool:
    return bool(
        path
        and path.exists()
        and all((path / relpath).is_file() for relpath in REQUIRED_CONTROL_PLANE_FILES)
    )


def git_config_global(name: str) -> str | None:
    result = run_command(
        ["git", "config", "--global", "--get", name],
        cwd=Path.home(),
        timeout_seconds=5,
    )
    if result["returncode"] != 0:
        return None
    value = str(result["stdout"]).strip()
    return value or None


def discover_control_plane_root(env: Mapping[str, str]) -> tuple[Path | None, list[str]]:
    checked: list[str] = []
    explicit_values = (
        env.get("TENN_CONTROL_PLANE_ROOT"),
        git_config_global("tenn.controlPlaneRoot"),
    )
    for value in explicit_values:
        if not value:
            continue
        candidate = Path(value).expanduser().resolve()
        checked.append(str(candidate))
        if valid_control_plane_root(candidate):
            return candidate, checked

    for dirname in KNOWN_CONTROL_PLANE_ROOTS:
        candidate = (Path.home() / dirname).resolve()
        checked.append(str(candidate))
        if valid_control_plane_root(candidate):
            return candidate, checked

    for ledger_path in sorted(Path.home().glob("tenn-*/scripts/agent_task_ledger.py")):
        candidate = ledger_path.parents[1].resolve()
        checked.append(str(candidate))
        if valid_control_plane_root(candidate):
            return candidate, checked

    return None, checked


def resolve_git_common_dir(repo_root: Path) -> Path | None:
    result = git_command(
        repo_root,
        "--path-format=absolute",
        "rev-parse",
        "--git-common-dir",
    )
    if result["returncode"] == 0 and result["stdout"]:
        return Path(str(result["stdout"])).resolve()
    result = git_command(repo_root, "rev-parse", "--git-common-dir")
    if result["returncode"] != 0 or not result["stdout"]:
        return None
    path = Path(str(result["stdout"]))
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def resolve_registry_root(
    repo_root: Path,
    env: Mapping[str, str],
) -> tuple[Path, str, list[str]]:
    checked: list[str] = []
    for source, value in (
        ("env:TENN_AGENT_REGISTRY_ROOT", env.get("TENN_AGENT_REGISTRY_ROOT")),
        ("git_global:tenn.agentRegistryRoot", git_config_global("tenn.agentRegistryRoot")),
    ):
        if not value:
            continue
        candidate = Path(value).expanduser().resolve()
        checked.append(f"{source}={candidate}")
        return candidate, source, checked

    common_dir = resolve_git_common_dir(repo_root)
    if common_dir is not None:
        candidate = common_dir / "tenn-agent-registry"
        checked.append(f"git_common_dir={candidate}")
        return candidate, "git_common_dir", checked

    candidate = repo_root / ".tenn/agent_jobs"
    checked.append(f"repo_local={candidate}")
    return candidate, "repo_local", checked


def selected_base(repo_root: Path) -> tuple[str | None, str | None, list[str]]:
    checked: list[str] = []
    upstream = git_text(
        repo_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    if upstream:
        checked.append(f"upstream={upstream}")
        merge_base = git_text(repo_root, "merge-base", "HEAD", upstream)
        return upstream, merge_base, checked

    checked.append("upstream=DATA_MISSING")
    fallback_exists = git_command(
        repo_root,
        "rev-parse",
        "--verify",
        "--quiet",
        DEFAULT_FALLBACK_BASE,
    )
    if fallback_exists["returncode"] == 0:
        checked.append(f"fallback={DEFAULT_FALLBACK_BASE}")
        merge_base = git_text(repo_root, "merge-base", "HEAD", DEFAULT_FALLBACK_BASE)
        return DEFAULT_FALLBACK_BASE, merge_base, checked

    checked.append(f"fallback={DEFAULT_FALLBACK_BASE}:DATA_MISSING")
    return None, None, checked


def canonical_head(repo_root: Path, base: str | None) -> str | None:
    if not base:
        return None
    return git_text(repo_root, "rev-parse", "--verify", base)


def local_branch_name(ref: str | None) -> str | None:
    if not ref:
        return None
    if ref.startswith("refs/heads/"):
        return ref.removeprefix("refs/heads/")
    if ref.startswith("origin/"):
        return ref.removeprefix("origin/")
    return ref


def path_ownership_for_git_worktree(
    *,
    path: Path,
    requested_path: Path | None = None,
    topic: str | None,
    canonical_branch: str | None,
    canonical_head_value: str | None,
) -> dict[str, Any]:
    git_root = git_text(path, "rev-parse", "--show-toplevel")
    branch = git_text(path, "branch", "--show-current")
    head = git_text(path, "rev-parse", "HEAD")
    status_result = git_command(path, "status", "--short", "--untracked-files=all")
    dirty_status = status_result["stdout"].splitlines() if status_result["returncode"] == 0 else []
    merge_base = (
        git_text(path, "merge-base", "HEAD", canonical_branch)
        if canonical_branch and head
        else None
    )

    reasons: list[str] = []
    if dirty_status:
        if dirty_rows_match_topic(dirty_status, topic):
            classification = "DIRTY_RELATED_WORKTREE"
            reasons.append("dirty status overlaps topic terms")
        else:
            classification = "DIRTY_UNRELATED_WORKTREE"
            reasons.append("dirty status exists but does not overlap topic terms")
    elif path_indicates_runtime(path, requested_path):
        classification = "RUNTIME_DIR"
        reasons.append("path name indicates runtime surface")
    elif (
        canonical_head_value
        and head == canonical_head_value
        and branch == "migration/clean-runtime-baseline-reconstruct-v1"
    ):
        classification = "VALID_CANONICAL_WORKTREE"
        reasons.append("checked-out branch is canonical and HEAD equals canonical head")
    elif (
        canonical_head_value
        and head != canonical_head_value
        and branch == local_branch_name(canonical_branch)
    ):
        classification = "STALE_PATH"
        reasons.append("checked-out canonical branch is not at canonical head")
    elif canonical_head_value and head != canonical_head_value and merge_base == head:
        classification = "STALE_PATH"
        reasons.append("HEAD is an ancestor of canonical head")
    elif canonical_head_value and merge_base and merge_base != canonical_head_value:
        classification = "STALE_PATH"
        reasons.append("branch is not based on current canonical head")
    else:
        classification = "VALID_TASK_WORKTREE"
        reasons.append("valid git worktree; use only if branch/task ownership is correct")

    return {
        "path": str(requested_path or path),
        "resolved_path": str(path),
        "exists": path.exists(),
        "classification": classification,
        "is_git_worktree": True,
        "git_root": git_root,
        "branch": branch,
        "head": head,
        "canonical_branch": canonical_branch,
        "canonical_head": canonical_head_value,
        "merge_base_with_canonical": merge_base,
        "dirty_status": dirty_status,
        "reasons": reasons,
    }


def path_ownership_for_path(
    path: Path,
    *,
    topic: str | None,
    canonical_branch: str | None,
    canonical_head_value: str | None,
) -> dict[str, Any]:
    requested_path = path.expanduser()
    path = requested_path.resolve(strict=False)
    if not path.exists():
        return {
            "path": str(requested_path),
            "resolved_path": str(path),
            "exists": False,
            "classification": DATA_MISSING,
            "is_git_worktree": False,
            "reasons": ["path does not exist"],
        }

    git_root = git_text(path, "rev-parse", "--show-toplevel")
    if git_root is not None:
        return path_ownership_for_git_worktree(
            path=path,
            requested_path=requested_path,
            topic=topic,
            canonical_branch=canonical_branch,
            canonical_head_value=canonical_head_value,
        )

    reasons: list[str] = []
    if path_indicates_runtime(path, requested_path):
        classification = "RUNTIME_DIR"
        reasons.append("path exists but is not a git repo and name indicates runtime surface")
    elif any((path / marker).exists() for marker in ("reports", "docs", ".agents")):
        classification = "SPARSE_EVIDENCE_DIR"
        reasons.append("path contains repo-like evidence directories but is not a git worktree")
    else:
        classification = "NOT_GIT_REPO"
        reasons.append("path exists but git rev-parse failed")

    return {
        "path": str(requested_path),
        "resolved_path": str(path),
        "exists": True,
        "classification": classification,
        "is_git_worktree": False,
        "reasons": reasons,
    }


def duplicate_classification_from_ledger(ledger_payload: Mapping[str, Any]) -> tuple[str | None, list[Any]]:
    search = ledger_payload.get("search")
    if not isinstance(search, Mapping):
        return None, []
    classification = search.get("duplicate_work_classification")
    if not isinstance(classification, str) or not classification:
        return None, []
    matches = search.get("matches")
    if isinstance(matches, list):
        return classification, matches
    return classification, []


def duplicate_status_for_classification(classification: str) -> str:
    return DUPLICATE_STATUS_MAP.get(classification, DATA_MISSING)


def control_plane_env(env: Mapping[str, str], registry_root: Path) -> dict[str, str]:
    merged = dict(env)
    merged["TENN_AGENT_REGISTRY_ROOT"] = str(registry_root)
    return merged


def run_registry_check(
    *,
    control_plane_root: Path | None,
    repo_root: Path,
    registry_root: Path,
    env: Mapping[str, str],
) -> tuple[str, dict[str, Any] | None, list[str]]:
    if control_plane_root is None:
        return DATA_MISSING, None, ["control_plane_root"]
    script = control_plane_root / "scripts/agent_job_registry.py"
    result = run_command(
        [
            sys.executable,
            str(script),
            "list-active",
            "--read-only",
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
        env=control_plane_env(env, registry_root),
    )
    payload = json_from_stdout(result)
    if result["returncode"] != 0 or not isinstance(payload, Mapping):
        return DATA_MISSING, {"command_result": result}, ["registry_read_only_result"]
    if payload.get("ok") is not True or payload.get("read_only") is not True:
        return DATA_MISSING, dict(payload), ["registry_not_confirmed_read_only"]
    return "PASS", dict(payload), []


def run_ledger_checks(
    *,
    control_plane_root: Path | None,
    repo_root: Path,
    registry_root: Path,
    env: Mapping[str, str],
    topic: str | None,
) -> tuple[str, dict[str, Any], list[str]]:
    if control_plane_root is None:
        return DATA_MISSING, {}, ["control_plane_root"]
    script = control_plane_root / "scripts/agent_task_ledger.py"
    merged_env = control_plane_env(env, registry_root)
    resolve_result = run_command(
        [sys.executable, str(script), "resolve-path"],
        cwd=repo_root,
        env=merged_env,
    )
    validate_result = run_command(
        [sys.executable, str(script), "validate"],
        cwd=repo_root,
        env=merged_env,
    )
    search_result = None
    if topic:
        search_result = run_command(
            [sys.executable, str(script), "search", "--text", topic],
            cwd=repo_root,
            env=merged_env,
        )
    validate_payload = json_from_stdout(validate_result)
    data_missing: list[str] = []
    status = "PASS"
    if resolve_result["returncode"] != 0:
        status = DATA_MISSING
        data_missing.append("ledger_resolve_path")
    if validate_result["returncode"] != 0 or not isinstance(validate_payload, Mapping):
        status = DATA_MISSING
        data_missing.append("ledger_validate")
    elif validate_payload.get("data_missing"):
        status = DATA_MISSING
        data_missing.extend(
            f"ledger:{item}" for item in validate_payload.get("data_missing") or []
        )
    payload: dict[str, Any] = {
        "resolve_path": resolve_result,
        "validate": validate_payload if isinstance(validate_payload, Mapping) else validate_result,
    }
    if search_result is not None:
        payload["search"] = json_from_stdout(search_result) or search_result
        if search_result["returncode"] != 0:
            status = DATA_MISSING
            data_missing.append("ledger_search")
    return status, payload, data_missing


def safe_count_paths(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.exists():
        return {"path": relative, "exists": False, "count": 0}
    if path.is_file():
        return {"path": relative, "exists": True, "count": 1}
    return {
        "path": relative,
        "exists": True,
        "count": sum(1 for child in path.rglob("*") if child.is_file()),
    }


def fallback_sources(repo_root: Path, topic: str | None) -> dict[str, Any]:
    branches = git_command(repo_root, "branch", "-a")
    worktrees = git_command(repo_root, "worktree", "list", "--porcelain")
    status = git_command(repo_root, "status", "--short", "--untracked-files=all")
    return {
        "topic": topic,
        "task_cards": safe_count_paths(repo_root, "docs/agent_tasks"),
        "reports": safe_count_paths(repo_root, "reports/agent_jobs"),
        "local_and_remote_branches": branches["stdout"].splitlines()
        if branches["returncode"] == 0
        else [],
        "worktrees": worktrees["stdout"].splitlines() if worktrees["returncode"] == 0 else [],
        "dirty_status_rows": status["stdout"].splitlines() if status["returncode"] == 0 else [],
    }


def preflight(
    *,
    repo_root: Path,
    topic: str | None = None,
    audit_paths: Sequence[Path] | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = dict(env or os.environ)
    repo_root = repo_root.expanduser().resolve()
    git_root = git_text(repo_root, "rev-parse", "--show-toplevel")
    if git_root is None:
        path_ownership = path_ownership_for_path(
            repo_root,
            topic=topic,
            canonical_branch=DEFAULT_CANONICAL_BRANCH,
            canonical_head_value=None,
        )
        return {
            "schema_version": "tenn_git_guard_preflight_v1",
            "repo_root": str(repo_root),
            "status": "ERROR",
            "final_decision": "block",
            "errors": ["repo_root_is_not_a_git_repository"],
            "canonical_branch": DEFAULT_CANONICAL_BRANCH,
            "canonical_branch_ref": CANONICAL_BRANCH_REF,
            "canonical_head": None,
            "path_ownership": path_ownership,
            "path_ownership_blocks_implementation": True,
            "stop_reimplementation": True,
        }

    branch = git_text(repo_root, "branch", "--show-current")
    head = git_text(repo_root, "rev-parse", "HEAD")
    remotes = git_command(repo_root, "remote", "-v")
    status_result = git_command(repo_root, "status", "--short", "--untracked-files=all")
    base, merge_base, base_checked = selected_base(repo_root)
    canonical_head_value = canonical_head(repo_root, DEFAULT_CANONICAL_BRANCH)
    control_plane_root, control_plane_checked = discover_control_plane_root(env)
    registry_root, registry_source, registry_checked = resolve_registry_root(repo_root, env)
    registry_status, registry_payload, registry_missing = run_registry_check(
        control_plane_root=control_plane_root,
        repo_root=repo_root,
        registry_root=registry_root,
        env=env,
    )
    ledger_status, ledger_payload, ledger_missing = run_ledger_checks(
        control_plane_root=control_plane_root,
        repo_root=repo_root,
        registry_root=registry_root,
        env=env,
        topic=topic,
    )
    fallback = fallback_sources(repo_root, topic)
    path_ownership = path_ownership_for_path(
        repo_root,
        topic=topic,
        canonical_branch=DEFAULT_CANONICAL_BRANCH,
        canonical_head_value=canonical_head_value,
    )
    audited_paths = [
        path_ownership_for_path(
            candidate,
            topic=topic,
            canonical_branch=DEFAULT_CANONICAL_BRANCH,
            canonical_head_value=canonical_head_value,
        )
        for candidate in (audit_paths or [])
    ]

    data_missing_sources: list[str] = []
    if control_plane_root is None:
        data_missing_sources.append("control_plane_root")
    if base is None:
        data_missing_sources.append("comparison_base")
    if merge_base is None:
        data_missing_sources.append("merge_base")
    data_missing_sources.extend(registry_missing)
    data_missing_sources.extend(ledger_missing)
    data_missing_sources = sorted(set(data_missing_sources))

    guard_support_status = "PASS" if control_plane_root is not None else DATA_MISSING
    ledger_duplicate_classification, ledger_duplicate_matches = duplicate_classification_from_ledger(ledger_payload)
    if ledger_duplicate_classification in BLOCKING_DUPLICATE_CLASSES:
        duplicate_work_classification = ledger_duplicate_classification
        duplicate_work_blocks_implementation = True
    elif ledger_duplicate_classification == "UNKNOWN_ASK" and ledger_duplicate_matches:
        duplicate_work_classification = ledger_duplicate_classification
        duplicate_work_blocks_implementation = True
    elif data_missing_sources:
        duplicate_work_classification = "DATA_MISSING_FALLBACK_CHECKED"
        duplicate_work_blocks_implementation = False
    elif ledger_duplicate_classification == "SUPERSEDED_IGNORE":
        duplicate_work_classification = ledger_duplicate_classification
        duplicate_work_blocks_implementation = False
    else:
        duplicate_work_classification = "NO_MATCHING_ACTIVE_WORK_FOUND"
        duplicate_work_blocks_implementation = False
    duplicate_work_status = duplicate_status_for_classification(duplicate_work_classification)
    path_ownership_classification = path_ownership.get("classification")
    path_ownership_blocks_implementation = path_ownership_classification in PATH_BLOCKING_CLASSIFICATIONS
    if duplicate_work_blocks_implementation or path_ownership_blocks_implementation:
        final_decision = "block"
    elif data_missing_sources:
        final_decision = "warning"
    else:
        final_decision = "pass"

    return {
        "schema_version": "tenn_git_guard_preflight_v1",
        "repo_root": str(repo_root),
        "git_root": git_root,
        "branch": branch,
        "head": head,
        "upstream": base if base and base != DEFAULT_FALLBACK_BASE else None,
        "base": base,
        "canonical_branch": DEFAULT_CANONICAL_BRANCH,
        "canonical_branch_ref": CANONICAL_BRANCH_REF,
        "canonical_head": canonical_head_value,
        "merge_base": merge_base,
        "remotes": remotes["stdout"].splitlines() if remotes["returncode"] == 0 else [],
        "dirty_status": status_result["stdout"].splitlines()
        if status_result["returncode"] == 0
        else [],
        "guard_runner_path": str(Path(__file__).resolve()),
        "control_plane_root": None if control_plane_root is None else str(control_plane_root),
        "control_plane_roots_checked": control_plane_checked,
        "guard_support_status": guard_support_status,
        "registry_root": str(registry_root),
        "registry_source": registry_source,
        "registry_checked": registry_checked,
        "registry_status": registry_status,
        "registry": registry_payload,
        "ledger_status": ledger_status,
        "ledger": ledger_payload,
        "duplicate_work_classification": duplicate_work_classification,
        "duplicate_work_status": duplicate_work_status,
        "duplicate_work_statuses": [
            "ADOPT",
            "CONTINUE",
            "MERGE_READY",
            "PARK",
            "SUPERSEDE",
            "BLOCKED",
            "DUPLICATE",
            DATA_MISSING,
        ],
        "duplicate_work_matches": ledger_duplicate_matches,
        "path_ownership_blocks_implementation": path_ownership_blocks_implementation,
        "stop_reimplementation": final_decision == "block",
        "path_ownership": path_ownership,
        "path_ownership_audit": audited_paths,
        "path_classifications": sorted(PATH_CLASSIFICATIONS),
        "fallback_sources_checked": fallback,
        "comparison_base_checked": base_checked,
        "data_missing_sources": data_missing_sources,
        "final_decision": final_decision,
    }


def print_human(payload: Mapping[str, Any]) -> None:
    print(f"repo_root: {payload.get('repo_root')}")
    print(f"branch: {payload.get('branch')}")
    print(f"head: {payload.get('head')}")
    print(f"base: {payload.get('base')}")
    print(f"merge_base: {payload.get('merge_base')}")
    path_ownership = payload.get("path_ownership")
    if isinstance(path_ownership, Mapping):
        print(f"path_ownership: {path_ownership.get('classification')}")
    print(f"guard_support_status: {payload.get('guard_support_status')}")
    print(f"control_plane_root: {payload.get('control_plane_root')}")
    print(f"registry_status: {payload.get('registry_status')}")
    print(f"ledger_status: {payload.get('ledger_status')}")
    print(f"duplicate_work_classification: {payload.get('duplicate_work_classification')}")
    print(f"duplicate_work_status: {payload.get('duplicate_work_status')}")
    print(f"final_decision: {payload.get('final_decision')}")
    if payload.get("data_missing_sources"):
        print("data_missing_sources:")
        for source in payload.get("data_missing_sources") or []:
            print(f"- {source}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--repo-root", required=True, type=Path)
    preflight_parser.add_argument("--topic", default=None)
    preflight_parser.add_argument("--audit-path", action="append", type=Path, default=[])
    preflight_parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "preflight":
        payload = preflight(repo_root=args.repo_root, topic=args.topic, audit_paths=args.audit_path)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        else:
            print_human(payload)
        return 2 if payload.get("status") == "ERROR" else 0
    raise SystemExit(f"unknown_command:{args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
