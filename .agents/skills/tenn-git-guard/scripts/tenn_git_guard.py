#!/usr/bin/env python3
"""Repo-agnostic Tenn git guard preflight.

The guard runner lives with the Tenn skill surface and inspects a target repo via
--repo-root. Runtime/product repos do not need to vendor Tenn control-plane
scripts for guard preflight to work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


DATA_MISSING = "DATA_MISSING"
DEFAULT_FALLBACK_DETAIL = "summary"
DEFAULT_FALLBACK_SAMPLE_LIMIT = 20
REQUIRED_CONTROL_PLANE_FILES = (
    "scripts/agent_job_registry.py",
    "scripts/agent_task_ledger.py",
    "scripts/agent_job_contract.py",
)
REQUIRED_V2_CONTROL_PLANE_FILES = (
    *REQUIRED_CONTROL_PLANE_FILES,
    "scripts/agent_decision_ledger.py",
    "scripts/agent_job_hook.py",
)
KNOWN_CONTROL_PLANE_ROOTS = (
    "tenn-semantic-anti-loop-v2-canonical",
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
    "REUSED_COMPLETE": "ADOPT",
    "ACTIVE_DUPLICATE": "DUPLICATE",
    "LOOP_GUARD_STOP": "BLOCKED",
}
V2_RESOLVED_DECISIONS = {"PASS", "FAIL", "PARKED"}
V2_STOP_STATUSES = {
    "REUSED_COMPLETE",
    "ACTIVE_DUPLICATE",
    "LOOP_GUARD_STOP",
    "DATA_MISSING",
    "EVIDENCE_CONFLICT",
    "BLOCKED_BY_DECISION",
}
NO_DELTA_VALUES = {"", "NONE", "NO_CHANGE", "NO_DELTA", "UNCHANGED"}
V2_ACTIVE_SEMANTIC_FIELDS = (
    "project_id",
    "claim_id",
    "hypothesis_id",
    "program_track",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
)
SCOPE_FINGERPRINT_FIELDS = (
    "project_id",
    "claim_id",
    "hypothesis_id",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
)


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


def valid_control_plane_root(
    path: Path | None,
    *,
    require_v2: bool = False,
) -> bool:
    required_files = (
        REQUIRED_V2_CONTROL_PLANE_FILES
        if require_v2
        else REQUIRED_CONTROL_PLANE_FILES
    )
    return bool(
        path
        and path.exists()
        and all((path / relpath).is_file() for relpath in required_files)
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


def git_config_local(repo_root: Path, name: str) -> str | None:
    result = git_command(repo_root, "config", "--local", "--get", name)
    if result["returncode"] != 0:
        return None
    value = str(result["stdout"]).strip()
    return value or None


def discover_control_plane_root(
    env: Mapping[str, str],
    *,
    require_v2: bool = False,
) -> tuple[Path | None, list[str]]:
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
        if valid_control_plane_root(candidate, require_v2=require_v2):
            return candidate, checked

    for dirname in KNOWN_CONTROL_PLANE_ROOTS:
        candidate = (Path.home() / dirname).resolve()
        checked.append(str(candidate))
        if valid_control_plane_root(candidate, require_v2=require_v2):
            return candidate, checked

    for ledger_path in sorted(Path.home().glob("tenn-*/scripts/agent_task_ledger.py")):
        candidate = ledger_path.parents[1].resolve()
        checked.append(str(candidate))
        if valid_control_plane_root(candidate, require_v2=require_v2):
            return candidate, checked

    return None, checked


def _hook_blocking_payload(message: str, *, platform: str) -> dict[str, str]:
    if platform == "gemini":
        return {
            "decision": "block",
            "reason": message,
            "additionalContext": message,
        }
    return {
        "decision": "block",
        "reason": message,
        "systemMessage": message,
    }


def portable_hook(
    *,
    repo_root: Path,
    platform: str,
    event: str,
    stdin_text: str = "",
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Dispatch a target-repo hook through a discovered V2 control plane."""

    merged_env = dict(os.environ)
    if env is not None:
        merged_env.update(env)
    control_plane_root, checked = discover_control_plane_root(
        merged_env,
        require_v2=True,
    )
    if control_plane_root is None:
        return _hook_blocking_payload(
            "Tenn V2 hook blocked: no V2-capable control plane found; checked "
            + ", ".join(checked),
            platform=platform,
        )

    hook_script = control_plane_root / "scripts/agent_job_hook.py"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(hook_script),
                "--platform",
                platform,
                "--event",
                event,
                "--repo-root",
                str(repo_root.resolve()),
            ],
            cwd=repo_root,
            env=merged_env,
            input=stdin_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _hook_blocking_payload(
            f"Tenn V2 hook failed via {hook_script}: {exc}",
            platform=platform,
        )

    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else None
    except json.JSONDecodeError:
        payload = None
    if completed.returncode != 0 or not isinstance(payload, Mapping):
        detail = completed.stderr.strip() or completed.stdout.strip() or (
            f"exit {completed.returncode}"
        )
        return _hook_blocking_payload(
            f"Tenn V2 hook failed via {hook_script}: {detail[:500]}",
            platform=platform,
        )
    return dict(payload)


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
        ("git_local:tenn.agentRegistryRoot", git_config_local(repo_root, "tenn.agentRegistryRoot")),
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
    branch = git_text(repo_root, "branch", "--show-current")
    upstream = git_text(
        repo_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    remote = (
        git_text(repo_root, "config", "--get", f"branch.{branch}.remote")
        if branch
        else None
    )
    merge_ref = (
        git_text(repo_root, "config", "--get", f"branch.{branch}.merge")
        if branch
        else None
    )
    tracked_branch = (
        merge_ref.removeprefix("refs/heads/")
        if merge_ref and merge_ref.startswith("refs/heads/")
        else merge_ref
    )
    self_published_upstream = bool(
        upstream
        and branch
        and remote
        and remote != "."
        and tracked_branch == branch
    )
    remote_default = (
        remote_default_head(repo_root, remote)
        if self_published_upstream and remote
        else None
    )

    if upstream and (not self_published_upstream or upstream == remote_default):
        checked.append(f"upstream={upstream}")
        merge_base = git_text(repo_root, "merge-base", "HEAD", upstream)
        return upstream, merge_base, checked

    if upstream:
        checked.append(f"upstream={upstream}:SELF_PUBLISHED_TOPIC")
    else:
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
    if remote_default:
        checked.append(f"remote_default={remote_default}")
        merge_base = git_text(repo_root, "merge-base", "HEAD", remote_default)
        return remote_default, merge_base, checked
    return None, None, checked


def remote_default_head(repo_root: Path, remote: str) -> str | None:
    """Resolve a tracking remote's symbolic default without assuming origin."""

    if not remote or remote == ".":
        return None
    symbolic = git_text(
        repo_root,
        "symbolic-ref",
        "--quiet",
        "--short",
        f"refs/remotes/{remote}/HEAD",
    )
    if symbolic:
        return symbolic

    advertised = git_command(repo_root, "ls-remote", "--symref", remote, "HEAD")
    if advertised["returncode"] != 0:
        return None
    prefix = "ref: refs/heads/"
    for line in str(advertised["stdout"]).splitlines():
        if not line.startswith(prefix) or not line.endswith("\tHEAD"):
            continue
        branch = line[len(prefix) : -len("\tHEAD")]
        candidate = f"{remote}/{branch}"
        if git_command(repo_root, "rev-parse", "--verify", "--quiet", candidate)[
            "returncode"
        ] == 0:
            return candidate
    return None


def canonical_head(repo_root: Path, base: str | None) -> str | None:
    if not base:
        return None
    return git_text(repo_root, "rev-parse", "--verify", base)


def canonical_ref(repo_root: Path, base: str | None) -> str:
    if not base or base == DEFAULT_FALLBACK_BASE:
        return CANONICAL_BRANCH_REF
    return (
        git_text(repo_root, "rev-parse", "--symbolic-full-name", base)
        or base
    )


def local_branch_name(ref: str | None) -> str | None:
    if not ref:
        return None
    if ref.startswith("refs/heads/"):
        return ref.removeprefix("refs/heads/")
    if ref.startswith("refs/remotes/"):
        remote_ref = ref.removeprefix("refs/remotes/")
        return remote_ref.split("/", 1)[1] if "/" in remote_ref else remote_ref
    if "/" in ref:
        return ref.split("/", 1)[1]
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
        and branch == local_branch_name(canonical_branch)
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
    active_jobs = payload.get("active_jobs")
    if not isinstance(active_jobs, list) or any(
        not isinstance(active_job, Mapping) for active_job in active_jobs
    ):
        return DATA_MISSING, dict(payload), ["registry_active_jobs_invalid"]
    return "PASS", dict(payload), []


def _compute_scope_fingerprint(metadata: Mapping[str, Any]) -> str:
    values: list[str] = []
    for field in SCOPE_FINGERPRINT_FIELDS:
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        normalized = value.strip()
        if field == "evidence_hash":
            normalized = _normalize_evidence_hash(normalized)
            if not normalized:
                raise ValueError("evidence_hash must be a SHA-256 digest")
        values.append(normalized)
    canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def v2_registry_evidence_issues(payload: Mapping[str, Any]) -> list[str]:
    """Return fail-closed issues for unreadable or invalid V2 active records."""

    issues: list[str] = []
    warnings = payload.get("warnings")
    if isinstance(warnings, list):
        for warning in warnings:
            if not isinstance(warning, Mapping) or warning.get("field") != "active_jobs":
                continue
            message = str(warning.get("message") or "")
            if " is stale;" not in message:
                issues.append(f"registry warning: {message or 'unreadable active record'}")

    active_jobs = payload.get("active_jobs")
    if not isinstance(active_jobs, list):
        return [*issues, "active_jobs must be a list"]
    for index, active in enumerate(active_jobs):
        if not isinstance(active, Mapping):
            issues.append(f"active_jobs[{index}] must be an object")
            continue
        version = active.get("control_contract_version")
        has_v2_identity = "scope_fingerprint" in active or any(
            field in active for field in V2_ACTIVE_SEMANTIC_FIELDS
        )
        if not has_v2_identity and version is None:
            continue
        if type(version) is not int or version != 2:
            issues.append(f"active_jobs[{index}] has V2 identity without control_contract_version: 2")
            continue
        missing = [
            field
            for field in V2_ACTIVE_SEMANTIC_FIELDS
            if not isinstance(active.get(field), str) or not str(active[field]).strip()
        ]
        if missing:
            issues.append(f"active_jobs[{index}] missing semantic fields: {', '.join(missing)}")
            continue
        if active.get("program_track") not in {"offline_development", "prospective_readiness"}:
            issues.append(f"active_jobs[{index}] has invalid program_track")
            continue
        fingerprint = _normalize_fingerprint(active.get("scope_fingerprint"))
        try:
            expected = _compute_scope_fingerprint(active)
        except ValueError as exc:
            issues.append(f"active_jobs[{index}] invalid semantic fields: {exc}")
            continue
        if not fingerprint or fingerprint != expected:
            issues.append(f"active_jobs[{index}] scope_fingerprint does not match semantic fields")
    return issues


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


def resolve_task_card_path(repo_root: Path, task_card: Path) -> Path:
    candidate = task_card.expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve(strict=False)


def _task_card_requires_strict_v2_closeout(path: Path) -> bool:
    """Treat every explicitly declared non-integer-v1 contract as strict/fail-closed."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")):
            continue
        key, separator, raw_value = line.partition(":")
        if separator and key.strip() == "control_contract_version":
            # Only an unquoted YAML integer 1 is legacy. Quoted, floating-point,
            # boolean, unknown, and V2 declarations are strict contracts.
            return raw_value.split("#", 1)[0].strip() != "1"
    return False


def run_task_card_validation(
    *,
    control_plane_root: Path | None,
    repo_root: Path,
    task_card: Path | None,
    env: Mapping[str, str],
) -> tuple[str, dict[str, Any] | None, list[str]]:
    if task_card is None:
        return "NOT_REQUESTED", None, []
    resolved = resolve_task_card_path(repo_root, task_card)
    if not resolved.is_file():
        return "INVALID", {"task_card": str(resolved)}, ["task_card_missing"]
    strict_contract = _task_card_requires_strict_v2_closeout(resolved)
    if control_plane_root is None:
        status = "V2_INVALID" if strict_contract else DATA_MISSING
        return status, {"task_card": str(resolved), "strict_contract": strict_contract}, ["control_plane_root"]

    script = control_plane_root / "scripts/agent_job_contract.py"
    result = run_command(
        [sys.executable, str(script), "validate", str(resolved)],
        cwd=repo_root,
        env=env,
    )
    payload = json_from_stdout(result)
    wrapped = {
        "task_card": str(resolved),
        "strict_contract": strict_contract,
        "command_result": result,
        "validation": payload,
    }
    if not isinstance(payload, Mapping):
        return "INVALID", wrapped, ["task_card_validation_result"]
    metadata = payload.get("metadata")
    version = metadata.get("control_contract_version") if isinstance(metadata, Mapping) else None
    if result["returncode"] != 0 or payload.get("ok") is not True:
        return "V2_INVALID" if strict_contract else "INVALID", wrapped, ["task_card_invalid"]
    if type(version) is int and version == 2:
        return "V2", wrapped, []
    return "V1_WARNING", wrapped, []


def run_decision_ledger_checks(
    *,
    control_plane_root: Path | None,
    repo_root: Path,
    registry_root: Path,
    env: Mapping[str, str],
    metadata: Mapping[str, Any],
) -> tuple[str, dict[str, Any], list[str]]:
    if control_plane_root is None:
        return DATA_MISSING, {}, ["control_plane_root"]
    script = control_plane_root / "scripts/agent_decision_ledger.py"
    if not script.is_file():
        return DATA_MISSING, {"script": str(script)}, ["decision_ledger_helper"]

    merged_env = control_plane_env(env, registry_root)
    validate_result = run_command(
        [sys.executable, str(script), "validate", "--repo-root", str(repo_root)],
        cwd=repo_root,
        env=merged_env,
    )
    validate_payload = json_from_stdout(validate_result)
    payload: dict[str, Any] = {
        "validate": validate_payload if isinstance(validate_payload, Mapping) else validate_result,
    }
    missing: list[str] = []
    if (
        validate_result["returncode"] != 0
        or not isinstance(validate_payload, Mapping)
        or validate_payload.get("ok") is not True
        or validate_payload.get("data_missing")
    ):
        missing.append("decision_ledger_validate")
        return DATA_MISSING, payload, missing

    search_result = run_command(
        [
            sys.executable,
            str(script),
            "search",
            "--repo-root",
            str(repo_root),
            "--project-id",
            str(metadata.get("project_id", "")),
            "--claim-id",
            str(metadata.get("claim_id", "")),
        ],
        cwd=repo_root,
        env=merged_env,
    )
    search_payload = json_from_stdout(search_result)
    payload["search"] = search_payload if isinstance(search_payload, Mapping) else search_result
    if search_result["returncode"] != 0 or not isinstance(search_payload, Mapping) or search_payload.get("ok") is not True:
        return DATA_MISSING, payload, ["decision_ledger_search"]
    return "PASS", payload, []


def _decision_entry(match: Any) -> Mapping[str, Any] | None:
    if not isinstance(match, Mapping):
        return None
    entry = match.get("entry")
    if isinstance(entry, Mapping):
        return entry
    return match


def _is_no_delta_match(match: Any, entry: Mapping[str, Any]) -> bool:
    if isinstance(match, Mapping) and isinstance(match.get("is_no_delta"), bool):
        return bool(match.get("is_no_delta"))
    delta = entry.get("decision_delta")
    if isinstance(delta, str):
        normalized = re.sub(r"[\s-]+", "_", delta.strip().upper())
        return normalized in NO_DELTA_VALUES
    if isinstance(delta, (list, dict)):
        return not bool(delta)
    return delta is None


def _entry_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_evidence_hash(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.removeprefix("sha256:")
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        return ""
    return f"sha256:{normalized}"


def _normalize_fingerprint(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        return ""
    return normalized


def _entry_matches_track(entry: Mapping[str, Any], current_track: Any) -> bool:
    return entry.get("program_track") == current_track


def classify_v2_scope(
    metadata: Mapping[str, Any],
    *,
    active_jobs: Sequence[Mapping[str, Any]],
    decision_matches: Sequence[Any],
) -> dict[str, Any]:
    fingerprint = _normalize_fingerprint(metadata.get("computed_scope_fingerprint"))
    job_id = str(metadata.get("job_id") or "")
    all_entries_with_matches = [
        (match, entry)
        for match in decision_matches
        if (entry := _decision_entry(match)) is not None
        and entry.get("project_id") == metadata.get("project_id")
        and entry.get("claim_id") == metadata.get("claim_id")
    ]
    current_track = metadata.get("program_track")
    same_track_entries = [
        pair
        for pair in all_entries_with_matches
        if _entry_matches_track(pair[1], current_track)
    ]
    exact = [
        pair
        for pair in same_track_entries
        if _normalize_fingerprint(pair[1].get("scope_fingerprint")) == fingerprint
    ]

    if exact:
        _, latest_exact = exact[-1]
        latest_decision = latest_exact.get("decision")
        if latest_decision in V2_RESOLVED_DECISIONS:
            return {
                "status": "REUSED_COMPLETE",
                "scope_admitted": False,
                "no_delta_outcomes": 0,
                "matching_decision_ids": [latest_exact.get("decision_id")],
            }
        if latest_decision == "DATA_MISSING":
            return {
                "status": DATA_MISSING,
                "scope_admitted": False,
                "no_delta_outcomes": 1 if _is_no_delta_match(exact[-1][0], latest_exact) else 0,
                "matching_decision_ids": [latest_exact.get("decision_id")],
            }
        if latest_decision == "CONFLICT":
            return {
                "status": "EVIDENCE_CONFLICT",
                "scope_admitted": False,
                "no_delta_outcomes": 1 if _is_no_delta_match(exact[-1][0], latest_exact) else 0,
                "matching_decision_ids": [latest_exact.get("decision_id")],
            }

    active_matches = [
        active
        for active in active_jobs
        if _normalize_fingerprint(active.get("scope_fingerprint")) == fingerprint
        and str(active.get("job_id") or "") != job_id
        and active.get("status", "active") == "active"
        and active.get("stale") is not True
    ]
    if active_matches:
        return {
            "status": "ACTIVE_DUPLICATE",
            "scope_admitted": False,
            "no_delta_outcomes": 0,
            "matching_active_jobs": [active.get("job_id") for active in active_matches],
        }

    if not all_entries_with_matches:
        return {"status": "ALLOW_NEW_SCOPE", "scope_admitted": True, "no_delta_outcomes": 0}

    current_evidence = _normalize_evidence_hash(metadata.get("evidence_hash"))
    current_dataset = str(metadata.get("dataset_version") or "").strip()
    evidence_versions = {
        (
            str(entry.get("dataset_version") or "").strip(),
            _normalize_evidence_hash(entry.get("evidence_hash")),
        )
        for _, entry in all_entries_with_matches
    }
    if (current_dataset, current_evidence) not in evidence_versions:
        return {"status": "ALLOW_CHANGED_EVIDENCE", "scope_admitted": True, "no_delta_outcomes": 0}

    current_pair_entries = [
        pair
        for pair in all_entries_with_matches
        if _normalize_evidence_hash(pair[1].get("evidence_hash")) == current_evidence
        and str(pair[1].get("dataset_version") or "").strip() == current_dataset
    ]
    same_track_current_pair = [
        pair
        for pair in current_pair_entries
        if _entry_matches_track(pair[1], current_track)
    ]

    target_transition = str(metadata.get("target_transition") or "")
    blocking_entries = [
        entry
        for _, entry in current_pair_entries
        if target_transition in _entry_list(entry.get("blocks"))
    ]
    if blocking_entries:
        decisions = {entry.get("decision") for entry in blocking_entries}
        if "DATA_MISSING" in decisions:
            status = DATA_MISSING
        elif "CONFLICT" in decisions:
            status = "EVIDENCE_CONFLICT"
        else:
            status = "BLOCKED_BY_DECISION"
        return {
            "status": status,
            "scope_admitted": False,
            "no_delta_outcomes": 0,
            "matching_decision_ids": [entry.get("decision_id") for entry in blocking_entries],
        }

    explicitly_not_blocked = any(
        target_transition in _entry_list(entry.get("does_not_block"))
        for _, entry in same_track_current_pair
    )
    if explicitly_not_blocked:
        return {
            "status": "ALLOW_EXPLICITLY_NOT_BLOCKED",
            "scope_admitted": True,
            "no_delta_outcomes": 0,
        }

    if not same_track_current_pair:
        return {"status": "ALLOW_NEW_SCOPE", "scope_admitted": True, "no_delta_outcomes": 0}

    hypotheses = {entry.get("hypothesis_id") for _, entry in same_track_current_pair}
    if metadata.get("hypothesis_id") not in hypotheses:
        return {"status": "ALLOW_NEW_HYPOTHESIS", "scope_admitted": True, "no_delta_outcomes": 0}

    unchanged = [
        (match, entry)
        for match, entry in same_track_current_pair
        if entry.get("hypothesis_id") == metadata.get("hypothesis_id")
    ]
    no_delta_count = 0
    for match, entry in reversed(unchanged):
        if not _is_no_delta_match(match, entry):
            break
        no_delta_count += 1
    if no_delta_count >= 2:
        return {
            "status": "LOOP_GUARD_STOP",
            "scope_admitted": False,
            "no_delta_outcomes": no_delta_count,
        }

    return {
        "status": "ALLOW_RELATED_SCOPE",
        "scope_admitted": True,
        "no_delta_outcomes": no_delta_count,
    }


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


def summarize_lines(
    rows: Sequence[str],
    *,
    topic: str | None,
    limit: int = DEFAULT_FALLBACK_SAMPLE_LIMIT,
) -> dict[str, Any]:
    tokens = topic_tokens(topic)
    matched = [
        row
        for row in rows
        if tokens and any(token in row.lower() for token in tokens)
    ]
    selected: list[str] = []
    for row in [*matched, *rows]:
        if row in selected:
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    return {
        "count": len(rows),
        "sample_limit": limit,
        "sample": selected,
        "matched_sample_count": min(len(matched), limit),
        "truncated": len(rows) > len(selected),
    }


def fallback_sources(
    repo_root: Path,
    topic: str | None,
    *,
    detail: str = DEFAULT_FALLBACK_DETAIL,
    sample_limit: int = DEFAULT_FALLBACK_SAMPLE_LIMIT,
) -> dict[str, Any]:
    branches = git_command(repo_root, "branch", "-a")
    worktrees = git_command(repo_root, "worktree", "list", "--porcelain")
    status = git_command(repo_root, "status", "--short", "--untracked-files=all")
    branch_rows = branches["stdout"].splitlines() if branches["returncode"] == 0 else []
    worktree_rows = worktrees["stdout"].splitlines() if worktrees["returncode"] == 0 else []
    if detail == "full":
        branch_payload: Any = branch_rows
        worktree_payload: Any = worktree_rows
    else:
        branch_payload = summarize_lines(branch_rows, topic=topic, limit=sample_limit)
        worktree_payload = summarize_lines(worktree_rows, topic=topic, limit=sample_limit)
    return {
        "topic": topic,
        "detail": detail,
        "task_cards": safe_count_paths(repo_root, "docs/agent_tasks"),
        "reports": safe_count_paths(repo_root, "reports/agent_jobs"),
        "local_and_remote_branches": branch_payload,
        "worktrees": worktree_payload,
        "dirty_status_rows": status["stdout"].splitlines() if status["returncode"] == 0 else [],
    }


def preflight(
    *,
    repo_root: Path,
    topic: str | None = None,
    task_card: Path | None = None,
    audit_paths: Sequence[Path] | None = None,
    env: Mapping[str, str] | None = None,
    fallback_detail: str = DEFAULT_FALLBACK_DETAIL,
    fallback_sample_limit: int = DEFAULT_FALLBACK_SAMPLE_LIMIT,
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
    canonical_branch_value = base or DEFAULT_CANONICAL_BRANCH
    canonical_branch_ref_value = canonical_ref(repo_root, base)
    canonical_head_value = canonical_head(repo_root, canonical_branch_value)
    task_card_path = (
        resolve_task_card_path(repo_root, task_card)
        if task_card is not None
        else None
    )
    require_v2_control = bool(
        task_card_path
        and task_card_path.is_file()
        and _task_card_requires_strict_v2_closeout(task_card_path)
    )
    control_plane_root, control_plane_checked = discover_control_plane_root(
        env,
        require_v2=require_v2_control,
    )
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
    control_contract_status, task_card_payload, task_card_missing = run_task_card_validation(
        control_plane_root=control_plane_root,
        repo_root=repo_root,
        task_card=task_card,
        env=control_plane_env(env, registry_root),
    )
    task_metadata: Mapping[str, Any] = {}
    if isinstance(task_card_payload, Mapping):
        validation_payload = task_card_payload.get("validation")
        if isinstance(validation_payload, Mapping) and isinstance(validation_payload.get("metadata"), Mapping):
            task_metadata = validation_payload["metadata"]

    if control_contract_status == "V2" and registry_status == "PASS":
        if not isinstance(registry_payload, Mapping):
            registry_status = DATA_MISSING
            registry_missing.append("registry_v2_evidence")
        else:
            registry_v2_issues = v2_registry_evidence_issues(registry_payload)
            if registry_v2_issues:
                registry_status = DATA_MISSING
                registry_payload = {**registry_payload, "v2_active_record_issues": registry_v2_issues}
                registry_missing.append("registry_v2_active_records")

    decision_ledger_status = "NOT_APPLICABLE"
    decision_ledger_payload: dict[str, Any] = {}
    decision_ledger_missing: list[str] = []
    semantic_result: dict[str, Any] = {
        "status": "V1_NOT_APPLICABLE" if control_contract_status == "V1_WARNING" else "NOT_EVALUATED",
        "scope_admitted": control_contract_status in {"V1_WARNING", "NOT_REQUESTED"},
        "no_delta_outcomes": 0,
    }
    if control_contract_status == "V2":
        decision_ledger_status, decision_ledger_payload, decision_ledger_missing = run_decision_ledger_checks(
            control_plane_root=control_plane_root,
            repo_root=repo_root,
            registry_root=registry_root,
            env=env,
            metadata=task_metadata,
        )
        if decision_ledger_status == "PASS" and registry_status == "PASS":
            active_jobs: list[Mapping[str, Any]] = []
            if isinstance(registry_payload, Mapping) and isinstance(registry_payload.get("active_jobs"), list):
                active_jobs = [
                    job for job in registry_payload["active_jobs"] if isinstance(job, Mapping)
                ]
            search_payload = decision_ledger_payload.get("search")
            decision_matches: list[Any] = []
            if isinstance(search_payload, Mapping) and isinstance(search_payload.get("matches"), list):
                decision_matches = list(search_payload["matches"])
            semantic_result = classify_v2_scope(
                task_metadata,
                active_jobs=active_jobs,
                decision_matches=decision_matches,
            )
        else:
            semantic_result = {
                "status": DATA_MISSING,
                "scope_admitted": False,
                "no_delta_outcomes": 0,
            }
    elif control_contract_status in {"INVALID", "V2_INVALID", DATA_MISSING}:
        semantic_result = {
            "status": "INVALID_CONTRACT" if control_contract_status != DATA_MISSING else DATA_MISSING,
            "scope_admitted": False,
            "no_delta_outcomes": 0,
        }
    fallback = fallback_sources(
        repo_root,
        topic,
        detail=fallback_detail,
        sample_limit=fallback_sample_limit,
    )
    path_ownership = path_ownership_for_path(
        repo_root,
        topic=topic,
        canonical_branch=canonical_branch_value,
        canonical_head_value=canonical_head_value,
    )
    audited_paths = [
        path_ownership_for_path(
            candidate,
            topic=topic,
            canonical_branch=canonical_branch_value,
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
    data_missing_sources.extend(task_card_missing)
    data_missing_sources.extend(decision_ledger_missing)
    data_missing_sources = sorted(set(data_missing_sources))

    guard_support_status = "PASS" if control_plane_root is not None else DATA_MISSING
    ledger_duplicate_classification, ledger_duplicate_matches = duplicate_classification_from_ledger(ledger_payload)
    semantic_control_status = str(semantic_result.get("status") or "NOT_EVALUATED")
    semantic_scope_admitted = semantic_result.get("scope_admitted") is True
    semantic_blocks_implementation = semantic_control_status in V2_STOP_STATUSES or control_contract_status in {
        "INVALID",
        "V2_INVALID",
        DATA_MISSING,
    }
    if semantic_control_status in {"REUSED_COMPLETE", "ACTIVE_DUPLICATE", "LOOP_GUARD_STOP"}:
        duplicate_work_classification = semantic_control_status
        duplicate_work_blocks_implementation = True
    elif ledger_duplicate_classification in BLOCKING_DUPLICATE_CLASSES:
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
    if semantic_blocks_implementation or duplicate_work_blocks_implementation or path_ownership_blocks_implementation:
        final_decision = "block"
    elif data_missing_sources:
        final_decision = "warning"
    else:
        final_decision = "pass"

    substantive_work_permitted = final_decision != "block" and semantic_scope_admitted
    report_write_permitted = substantive_work_permitted and semantic_control_status not in V2_STOP_STATUSES

    return {
        "schema_version": "tenn_git_guard_preflight_v2",
        "repo_root": str(repo_root),
        "git_root": git_root,
        "branch": branch,
        "head": head,
        "upstream": base if base and base != DEFAULT_FALLBACK_BASE else None,
        "base": base,
        "canonical_branch": canonical_branch_value,
        "canonical_branch_ref": canonical_branch_ref_value,
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
        "task_card": task_card_payload,
        "control_contract_status": control_contract_status,
        "decision_ledger_status": decision_ledger_status,
        "decision_ledger": decision_ledger_payload,
        "semantic_control_status": semantic_control_status,
        "semantic_scope_admitted": semantic_scope_admitted,
        "semantic_control": semantic_result,
        "no_delta_outcomes": int(semantic_result.get("no_delta_outcomes") or 0),
        "substantive_work_permitted": substantive_work_permitted,
        "report_write_permitted": report_write_permitted,
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
    print(f"control_contract_status: {payload.get('control_contract_status')}")
    print(f"decision_ledger_status: {payload.get('decision_ledger_status')}")
    print(f"semantic_control_status: {payload.get('semantic_control_status')}")
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
    preflight_parser.add_argument(
        "--task-card",
        type=Path,
        help="Validate a task card and apply V2 decision reuse/loop control before substantive work.",
    )
    preflight_parser.add_argument("--audit-path", action="append", type=Path, default=[])
    preflight_parser.add_argument(
        "--fallback-detail",
        choices=("summary", "full"),
        default=DEFAULT_FALLBACK_DETAIL,
        help="Use summary for fast/small work; use full for hygiene, parking, merge, or deep duplicate-work audits.",
    )
    preflight_parser.add_argument(
        "--fallback-sample-limit",
        type=int,
        default=DEFAULT_FALLBACK_SAMPLE_LIMIT,
        help="Maximum branch/worktree fallback rows retained in summary mode.",
    )
    preflight_parser.add_argument("--json", action="store_true")

    hook_parser = subparsers.add_parser(
        "hook",
        help="dispatch a target-repo hook through a discovered V2-capable Tenn control plane",
    )
    hook_parser.add_argument("--repo-root", required=True, type=Path)
    hook_parser.add_argument(
        "--platform",
        choices=("codex", "claude", "gemini"),
        default="codex",
    )
    hook_parser.add_argument(
        "--event",
        choices=("Stop", "SessionEnd", "BeforeTool"),
        default="Stop",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "hook":
        payload = portable_hook(
            repo_root=args.repo_root,
            platform=args.platform,
            event=args.event,
            stdin_text=sys.stdin.read(),
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    if args.command == "preflight":
        payload = preflight(
            repo_root=args.repo_root,
            topic=args.topic,
            task_card=args.task_card,
            audit_paths=args.audit_path,
            fallback_detail=args.fallback_detail,
            fallback_sample_limit=max(1, args.fallback_sample_limit),
        )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        else:
            print_human(payload)
        if payload.get("status") == "ERROR":
            return 2
        if args.task_card is not None and payload.get("control_contract_status") in {
            "INVALID",
            "V2_INVALID",
            DATA_MISSING,
        }:
            return 2
        if payload.get("control_contract_status") == "V2" and payload.get("final_decision") == "block":
            return 3
        return 0
    raise SystemExit(f"unknown_command:{args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
