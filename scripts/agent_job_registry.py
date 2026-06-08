#!/usr/bin/env python3
"""Track active Tenn dev-agent jobs and lane/file overlap locks."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

try:
    from scripts import agent_job_contract as contract
except ModuleNotFoundError:  # pragma: no cover - used when executed as scripts/agent_job_registry.py
    import agent_job_contract as contract  # type: ignore


REPO_LOCAL_REGISTRY_ROOT = Path(".tenn/agent_jobs")
ACTIVE_JOB_SUBDIR = "active"
SHARED_REGISTRY_DIR_NAME = "tenn-agent-registry"
DEFAULT_STALE_AFTER_SECONDS = 30 * 60
LOCK_TIMEOUT_SECONDS = 10.0
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RegistryIssue:
    field: str
    message: str
    job_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {"field": self.field, "message": self.message}
        if self.job_id:
            payload["job_id"] = self.job_id
        return payload


@dataclass(frozen=True)
class LoadedJob:
    path: Path
    record: dict[str, Any]


@dataclass(frozen=True)
class RegistryLocation:
    root: Path
    registry_scope: str
    repo_root: Path
    git_common_dir: Path | None
    warnings: tuple[RegistryIssue, ...] = ()

    def metadata(self) -> dict[str, Any]:
        return {
            "registry_root": str(self.root),
            "registry_scope": self.registry_scope,
            "repo_root": str(self.repo_root),
            "git_common_dir": None if self.git_common_dir is None else str(self.git_common_dir),
        }


class RegistryLock:
    """Small local-filesystem lock using atomic directory creation."""

    def __init__(self, registry_root: Path, *, timeout_seconds: float = LOCK_TIMEOUT_SECONDS) -> None:
        self.registry_root = registry_root
        self.timeout_seconds = timeout_seconds
        self.lock_dir = registry_root / ".lock"
        self._acquired = False

    def __enter__(self) -> RegistryLock:
        self.registry_root.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self.lock_dir.mkdir()
                self._acquired = True
                owner = {
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "locked_at": _to_iso(_coerce_now()),
                }
                try:
                    _atomic_write_json(self.lock_dir / "owner.json", owner)
                except Exception:
                    self._cleanup()
                    raise
                return self
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for registry lock: {self.lock_dir}") from exc
                time.sleep(0.05)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if not self._acquired:
            return
        try:
            self._cleanup()
        finally:
            self._acquired = False

    def _cleanup(self) -> None:
        owner_path = self.lock_dir / "owner.json"
        if owner_path.exists():
            owner_path.unlink()
        self.lock_dir.rmdir()


def _coerce_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return _coerce_now(dt).isoformat().replace("+00:00", "Z")


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _normalize_repo_path(path_text: str) -> str:
    path = PurePosixPath(path_text.strip().replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"path must be repo-relative without parent segments: {path_text}")
    return path.as_posix()


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve(strict=False))


def _git_output(repo_root: Path, args: Sequence[str]) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _path_from_config(raw_path: str, repo_root: Path) -> Path:
    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve(strict=False)


def _read_git_common_dir(repo_root: Path) -> Path | None:
    raw = _git_output(repo_root, ["rev-parse", "--git-common-dir"])
    if not raw:
        return None
    return _path_from_config(raw, repo_root)


def _read_git_config_registry_root(repo_root: Path) -> Path | None:
    raw = _git_output(repo_root, ["config", "--get", "tenn.agentRegistryRoot"])
    if not raw:
        return None
    return _path_from_config(raw, repo_root)


def _resolve_repo_root(repo_root: Path | None = None) -> Path:
    start = (repo_root or Path.cwd()).resolve()
    raw = _git_output(start, ["rev-parse", "--show-toplevel"])
    if raw:
        return _path_from_config(raw, start)
    return start


def resolve_registry_location(repo_root: Path | None = None) -> RegistryLocation:
    root = _resolve_repo_root(repo_root)
    git_common_dir = _read_git_common_dir(root)

    env_root = os.environ.get("TENN_AGENT_REGISTRY_ROOT", "").strip()
    if env_root:
        return RegistryLocation(
            root=_path_from_config(env_root, root),
            registry_scope="shared",
            repo_root=root,
            git_common_dir=git_common_dir,
        )

    configured_root = _read_git_config_registry_root(root)
    if configured_root is not None:
        return RegistryLocation(
            root=configured_root,
            registry_scope="shared",
            repo_root=root,
            git_common_dir=git_common_dir,
        )

    if git_common_dir is not None:
        return RegistryLocation(
            root=(git_common_dir / SHARED_REGISTRY_DIR_NAME).resolve(strict=False),
            registry_scope="shared",
            repo_root=root,
            git_common_dir=git_common_dir,
        )

    fallback_root = (root / REPO_LOCAL_REGISTRY_ROOT).resolve(strict=False)
    return RegistryLocation(
        root=fallback_root,
        registry_scope="repo_local_fallback",
        repo_root=root,
        git_common_dir=None,
        warnings=(
            RegistryIssue(
                "registry_root",
                "using repo-local .tenn/agent_jobs fallback; cross-worktree visibility is unavailable",
            ),
        ),
    )


def _read_git_branch(repo_root: Path) -> str | None:
    return _git_output(repo_root, ["branch", "--show-current"])


def _read_session_id(job_id: str) -> str:
    for key in ("TENN_AGENT_SESSION_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return f"{socket.gethostname()}:{os.getpid()}:{job_id}"


def _configured_stale_after(
    metadata: dict[str, Any] | None = None,
    *,
    override: int | None = None,
) -> int:
    if override is not None:
        return override

    if metadata:
        value = metadata.get("stale_after_seconds")
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value

    env_value = os.environ.get("TENN_AGENT_STALE_AFTER_SECONDS", "").strip()
    if env_value:
        try:
            parsed = int(env_value)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed

    return DEFAULT_STALE_AFTER_SECONDS


def _validate_stale_after_override(value: int | None) -> RegistryIssue | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return RegistryIssue("stale_after_seconds", "must be a positive integer")
    return None


def _registry_validation_issues(metadata: dict[str, Any]) -> list[RegistryIssue]:
    value = metadata.get("stale_after_seconds")
    if value is None:
        return []
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return [RegistryIssue("stale_after_seconds", "must be a positive integer when provided")]
    return []


def _read_task_card(task_card: Path, repo_root: Path) -> tuple[str, str]:
    candidate = task_card.expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    display_path = _display_path(candidate, repo_root)
    return candidate.read_text(encoding="utf-8"), display_path


def _validate_task_card(markdown: str) -> tuple[bool, dict[str, Any], list[RegistryIssue], dict[str, Any]]:
    validation = contract.validate_task_card_markdown(markdown)
    issues = [RegistryIssue(issue.field, issue.message) for issue in validation.issues]
    if validation.ok:
        issues.extend(_registry_validation_issues(validation.metadata))
    return not issues, validation.metadata, issues, validation.to_dict()


def _active_record_path(registry_root: Path, job_id: str) -> Path:
    if not contract.JOB_ID_RE.fullmatch(job_id):
        raise ValueError("job_id must contain only letters, numbers, dot, underscore, or dash")
    return registry_root / ACTIVE_JOB_SUBDIR / f"{job_id}.json"


def _status_path(repo_root: Path, output_dir: str, job_id: str) -> Path:
    report_dir = contract.resolve_report_dir(output_dir, job_id, repo_root=repo_root)
    return report_dir / "status.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _load_active_jobs(registry_root: Path, repo_root: Path) -> tuple[list[LoadedJob], list[RegistryIssue]]:
    active_dir = registry_root / ACTIVE_JOB_SUBDIR
    if not active_dir.exists():
        return [], []

    jobs: list[LoadedJob] = []
    warnings: list[RegistryIssue] = []
    for path in sorted(active_dir.glob("*.json")):
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            warnings.append(RegistryIssue("active_jobs", f"{_display_path(path, repo_root)} is invalid JSON: {exc}"))
            continue
        if not isinstance(loaded, dict):
            warnings.append(RegistryIssue("active_jobs", f"{_display_path(path, repo_root)} must contain a JSON object"))
            continue
        jobs.append(LoadedJob(path=path, record=loaded))
    return jobs, warnings


def _read_active_record(path: Path, repo_root: Path) -> tuple[dict[str, Any] | None, RegistryIssue | None]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, RegistryIssue("active_jobs", f"{_display_path(path, repo_root)} is invalid JSON: {exc}")
    if not isinstance(loaded, dict):
        return None, RegistryIssue("active_jobs", f"{_display_path(path, repo_root)} must contain a JSON object")
    return loaded, None


def _record_timestamp(record: dict[str, Any]) -> datetime | None:
    for key in ("last_seen_at", "heartbeat_at", "started_at", "claimed_at"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            try:
                return _from_iso(value)
            except ValueError:
                return None
    return None


def _stale_state(
    record: dict[str, Any],
    *,
    now: datetime,
    fallback_stale_after_seconds: int,
) -> tuple[bool, float | None, int]:
    stale_after = _configured_stale_after(record, override=None)
    if "stale_after_seconds" not in record:
        stale_after = fallback_stale_after_seconds

    timestamp = _record_timestamp(record)
    if timestamp is None:
        return True, None, stale_after
    age_seconds = max(0.0, (now - timestamp).total_seconds())
    return age_seconds > stale_after, age_seconds, stale_after


def _job_summary(
    loaded: LoadedJob,
    *,
    repo_root: Path,
    now: datetime,
    fallback_stale_after_seconds: int,
) -> dict[str, Any]:
    record = dict(loaded.record)
    stale, age_seconds, stale_after_seconds = _stale_state(
        record,
        now=now,
        fallback_stale_after_seconds=fallback_stale_after_seconds,
    )
    record["active_record"] = _display_path(loaded.path, repo_root)
    record["stale"] = stale
    record["stale_after_seconds"] = stale_after_seconds
    record["age_seconds"] = None if age_seconds is None else round(age_seconds, 3)
    return record


def _path_matches(pattern: str, path: str) -> bool:
    pattern = pattern.rstrip("/")
    path = path.rstrip("/")
    if any(char in pattern for char in "*?["):
        return fnmatch.fnmatchcase(path, pattern)
    return path == pattern or path.startswith(f"{pattern}/")


def _paths_overlap(left: str, right: str) -> bool:
    return _path_matches(left, right) or _path_matches(right, left)


def _allowed_files(metadata: dict[str, Any]) -> list[str]:
    return [_normalize_repo_path(str(item)) for item in metadata.get("allowed_files", [])]


def _overlapping_files(left: Sequence[str], right: Sequence[str]) -> list[str]:
    overlaps: list[str] = []
    for left_path in left:
        for right_path in right:
            if _paths_overlap(left_path, right_path):
                overlaps.append(left_path if left_path == right_path else f"{left_path} <-> {right_path}")
    return sorted(set(overlaps))


def _is_registry_internal_path(path: str, *, repo_root: Path, registry_root: Path) -> bool:
    if (
        path == ".tenn/active_agent_task"
        or path.startswith(".tenn/agent_jobs/")
        or path.startswith("reports/agent_jobs/")
    ):
        return True

    try:
        registry_path = registry_root.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return False
    return path == registry_path or path.startswith(f"{registry_path}/")


def _dirty_files_outside_card(
    metadata: dict[str, Any],
    *,
    task_card_path: str | None,
    repo_root: Path,
    registry_root: Path,
    changed_files: Sequence[contract.ChangedFile] | None = None,
) -> tuple[list[str], list[RegistryIssue]]:
    try:
        changes = list(changed_files) if changed_files is not None else contract.read_git_changed_files(repo_root)
        allowed_patterns = _allowed_files(metadata)
        output_dir = metadata.get("output_dir")
        if isinstance(output_dir, str) and output_dir.strip():
            allowed_patterns.append(_normalize_repo_path(output_dir))
        if task_card_path:
            allowed_patterns.append(_normalize_repo_path(task_card_path))
    except (subprocess.CalledProcessError, ValueError) as exc:
        return [], [RegistryIssue("git", str(exc))]

    dirty = []
    for changed in changes:
        if _is_registry_internal_path(changed.path, repo_root=repo_root, registry_root=registry_root):
            continue
        if not any(_path_matches(pattern, changed.path) for pattern in allowed_patterns):
            dirty.append(changed.path)
    return sorted(set(dirty)), []


def list_active_jobs(
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
) -> dict[str, Any]:
    location = resolve_registry_location(repo_root)
    root = location.repo_root
    current = _coerce_now(now)
    fallback_stale_after = _configured_stale_after(override=stale_after_seconds)
    with RegistryLock(location.root):
        jobs, warnings = _load_active_jobs(location.root, root)
    active = [
        _job_summary(
            job,
            repo_root=root,
            now=current,
            fallback_stale_after_seconds=fallback_stale_after,
        )
        for job in jobs
    ]
    stale_warnings = [
        RegistryIssue(
            "active_jobs",
            f"active job {job.get('job_id', '<unknown>')} is stale; last heartbeat age is {job['age_seconds']}s",
            job_id=str(job.get("job_id") or ""),
        )
        for job in active
        if job.get("stale")
    ]
    return {
        "ok": True,
        **location.metadata(),
        "active_jobs": active,
        "warnings": [issue.to_dict() for issue in [*location.warnings, *warnings, *stale_warnings]],
    }


def _check_overlap_for_task_card_locked(
    task_card: Path,
    *,
    location: RegistryLocation,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
    changed_files: Sequence[contract.ChangedFile] | None = None,
) -> dict[str, Any]:
    root = location.repo_root
    current = _coerce_now(now)

    try:
        markdown, task_card_path = _read_task_card(task_card, root)
    except FileNotFoundError:
        return {
            "ok": False,
            **location.metadata(),
            "issues": [RegistryIssue("task_card", f"task card not found: {task_card}").to_dict()],
            "warnings": [issue.to_dict() for issue in location.warnings],
            "active_jobs": [],
        }

    valid, metadata, validation_issues, validation = _validate_task_card(markdown)
    if not valid:
        return {
            "ok": False,
            **location.metadata(),
            "validation": validation,
            "issues": [issue.to_dict() for issue in validation_issues],
            "warnings": [issue.to_dict() for issue in location.warnings],
            "active_jobs": [],
        }

    job_id = str(metadata["job_id"])
    lane = str(metadata["lane"])
    output_dir = str(metadata["output_dir"])
    allowed = _allowed_files(metadata)
    fallback_stale_after = _configured_stale_after(metadata, override=stale_after_seconds)
    loaded_jobs, load_warnings = _load_active_jobs(location.root, root)
    active_jobs = [
        _job_summary(
            job,
            repo_root=root,
            now=current,
            fallback_stale_after_seconds=fallback_stale_after,
        )
        for job in loaded_jobs
    ]

    issues: list[RegistryIssue] = []
    warnings = [*location.warnings, *load_warnings]
    for active in active_jobs:
        active_job_id = str(active.get("job_id") or "")
        if active_job_id == job_id:
            continue

        active_allowed = [
            _normalize_repo_path(str(item))
            for item in active.get("allowed_files", [])
            if isinstance(item, str) and item.strip()
        ]
        overlapping = _overlapping_files(allowed, active_allowed)
        reasons: list[str] = []
        if active.get("lane") == lane:
            reasons.append(f"lane {lane}")
        if overlapping:
            sample = ", ".join(overlapping[:5])
            if len(overlapping) > 5:
                sample = f"{sample}, +{len(overlapping) - 5} more"
            reasons.append(f"allowed_files {sample}")
        if active.get("output_dir") == output_dir:
            reasons.append(f"output_dir {output_dir}")
        if not reasons:
            continue

        message = f"active job {active_job_id or '<unknown>'} overlaps current task by {', '.join(reasons)}"
        if active.get("stale"):
            warnings.append(RegistryIssue("active_jobs", f"stale lock warning-only: {message}", job_id=active_job_id))
        else:
            issues.append(RegistryIssue("active_jobs", message, job_id=active_job_id))

    dirty_files, dirty_issues = _dirty_files_outside_card(
        metadata,
        task_card_path=task_card_path,
        repo_root=root,
        registry_root=location.root,
        changed_files=changed_files,
    )
    issues.extend(dirty_issues)
    for path in dirty_files:
        issues.append(RegistryIssue("changed_files", f"{path} is dirty outside current task card allowed_files"))

    return {
        "ok": not issues,
        **location.metadata(),
        "job_id": job_id,
        "lane": lane,
        "task_card": task_card_path,
        "active_jobs": active_jobs,
        "issues": [issue.to_dict() for issue in issues],
        "warnings": [issue.to_dict() for issue in warnings],
    }


def check_overlap_for_task_card(
    task_card: Path,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
    changed_files: Sequence[contract.ChangedFile] | None = None,
) -> dict[str, Any]:
    location = resolve_registry_location(repo_root)
    with RegistryLock(location.root):
        return _check_overlap_for_task_card_locked(
            task_card,
            location=location,
            now=now,
            stale_after_seconds=stale_after_seconds,
            changed_files=changed_files,
        )


def _write_status(location: RegistryLocation, record: dict[str, Any], *, status: str, now: datetime) -> str:
    repo_root = location.repo_root
    active_path = _active_record_path(location.root, str(record["job_id"]))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "job_id": record["job_id"],
        "status": status,
        "lane": record.get("lane"),
        "owner": record.get("owner"),
        "agent": record.get("agent"),
        "session_id": record.get("session_id"),
        "allowed_files": record.get("allowed_files", []),
        "output_dir": record.get("output_dir"),
        "task_card": record.get("task_card"),
        "worktree": record.get("worktree"),
        "branch": record.get("branch"),
        "git_common_dir": record.get("git_common_dir"),
        "started_at": record.get("started_at"),
        "last_seen_at": record.get("last_seen_at"),
        "claimed_at": record.get("claimed_at"),
        "heartbeat_at": record.get("heartbeat_at"),
        "updated_at": _to_iso(now),
        "active_record": _display_path(active_path, repo_root),
        **location.metadata(),
    }
    if status == "released":
        payload["released_at"] = _to_iso(now)

    status_path = _status_path(repo_root, str(record["output_dir"]), str(record["job_id"]))
    _atomic_write_json(status_path, payload)
    return _display_path(status_path, repo_root)


def claim_task_card(
    task_card: Path,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
) -> dict[str, Any]:
    location = resolve_registry_location(repo_root)
    root = location.repo_root
    current = _coerce_now(now)

    try:
        markdown, task_card_path = _read_task_card(task_card, root)
    except FileNotFoundError:
        return {
            "ok": False,
            **location.metadata(),
            "issues": [RegistryIssue("task_card", f"task card not found: {task_card}").to_dict()],
            "warnings": [issue.to_dict() for issue in location.warnings],
        }

    valid, metadata, validation_issues, validation = _validate_task_card(markdown)
    if not valid:
        return {
            "ok": False,
            **location.metadata(),
            "validation": validation,
            "issues": [issue.to_dict() for issue in validation_issues],
            "warnings": [issue.to_dict() for issue in location.warnings],
        }

    job_id = str(metadata["job_id"])
    fallback_stale_after = _configured_stale_after(metadata, override=stale_after_seconds)
    with RegistryLock(location.root):
        existing_jobs, load_warnings = _load_active_jobs(location.root, root)
        for existing in existing_jobs:
            existing_job_id = str(existing.record.get("job_id") or "")
            if existing_job_id != job_id:
                continue
            stale, _, _ = _stale_state(
                existing.record,
                now=current,
                fallback_stale_after_seconds=fallback_stale_after,
            )
            if not stale:
                return {
                    "ok": False,
                    **location.metadata(),
                    "issues": [
                        RegistryIssue("job_id", f"active job already exists for {job_id}", job_id=job_id).to_dict()
                    ],
                    "warnings": [issue.to_dict() for issue in [*location.warnings, *load_warnings]],
                }

        overlap = _check_overlap_for_task_card_locked(
            task_card,
            location=location,
            now=current,
            stale_after_seconds=stale_after_seconds,
        )
        if not overlap.get("ok"):
            return {
                "ok": False,
                **location.metadata(),
                "issues": overlap.get("issues", []),
                "warnings": [*overlap.get("warnings", []), *[issue.to_dict() for issue in load_warnings]],
                "overlap": overlap,
            }

        timestamp = _to_iso(current)
        record = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "lane": metadata["lane"],
            "owner": metadata["owner"],
            "agent": metadata["owner"],
            "session_id": _read_session_id(job_id),
            "allowed_files": _allowed_files(metadata),
            "approval_required": metadata["approval_required"],
            "timeout_seconds": metadata["timeout_seconds"],
            "output_dir": metadata["output_dir"],
            "mutation_mode": metadata["mutation_mode"],
            "production_data_access": metadata["production_data_access"],
            "task_card": task_card_path,
            "task_card_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            "worktree": str(root),
            "branch": _read_git_branch(root),
            "git_common_dir": None if location.git_common_dir is None else str(location.git_common_dir),
            "started_at": timestamp,
            "last_seen_at": timestamp,
            "claimed_at": timestamp,
            "heartbeat_at": timestamp,
            "status": "active",
            "stale_after_seconds": fallback_stale_after,
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
        }
        active_path = _active_record_path(location.root, job_id)
        _atomic_write_json(active_path, record)
        status_path = _write_status(location, record, status="active", now=current)

    return {
        "ok": True,
        **location.metadata(),
        "job_id": job_id,
        "active_record": _display_path(active_path, root),
        "status_path": status_path,
        "record": record,
        "warnings": [*overlap.get("warnings", []), *[issue.to_dict() for issue in load_warnings]],
    }


def heartbeat_job(
    job_id: str,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    location = resolve_registry_location(repo_root)
    root = location.repo_root
    current = _coerce_now(now)
    try:
        active_path = _active_record_path(location.root, job_id)
    except ValueError as exc:
        return {
            "ok": False,
            **location.metadata(),
            "issues": [RegistryIssue("job_id", str(exc)).to_dict()],
            "warnings": [issue.to_dict() for issue in location.warnings],
        }

    with RegistryLock(location.root):
        if not active_path.exists():
            return {
                "ok": False,
                **location.metadata(),
                "issues": [RegistryIssue("job_id", f"active job not found: {job_id}", job_id=job_id).to_dict()],
                "warnings": [issue.to_dict() for issue in location.warnings],
            }

        record, issue = _read_active_record(active_path, root)
        if issue is not None or record is None:
            return {
                "ok": False,
                **location.metadata(),
                "issues": [
                    issue.to_dict() if issue else RegistryIssue("active_jobs", "active record is unreadable").to_dict()
                ],
                "warnings": [issue.to_dict() for issue in location.warnings],
            }

        timestamp = _to_iso(current)
        record["heartbeat_at"] = timestamp
        record["last_seen_at"] = timestamp
        record["status"] = "active"
        _atomic_write_json(active_path, record)
        status_path = _write_status(location, record, status="active", now=current)
    return {
        "ok": True,
        **location.metadata(),
        "job_id": job_id,
        "active_record": _display_path(active_path, root),
        "status_path": status_path,
        "record": record,
        "warnings": [issue.to_dict() for issue in location.warnings],
    }


def release_job(
    job_id: str,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    location = resolve_registry_location(repo_root)
    root = location.repo_root
    current = _coerce_now(now)
    try:
        active_path = _active_record_path(location.root, job_id)
    except ValueError as exc:
        return {
            "ok": False,
            **location.metadata(),
            "issues": [RegistryIssue("job_id", str(exc)).to_dict()],
            "warnings": [issue.to_dict() for issue in location.warnings],
        }

    with RegistryLock(location.root):
        if not active_path.exists():
            return {
                "ok": False,
                **location.metadata(),
                "issues": [RegistryIssue("job_id", f"active job not found: {job_id}", job_id=job_id).to_dict()],
                "warnings": [issue.to_dict() for issue in location.warnings],
            }

        record, issue = _read_active_record(active_path, root)
        if issue is not None or record is None:
            return {
                "ok": False,
                **location.metadata(),
                "issues": [
                    issue.to_dict() if issue else RegistryIssue("active_jobs", "active record is unreadable").to_dict()
                ],
                "warnings": [issue.to_dict() for issue in location.warnings],
            }

        record["last_seen_at"] = _to_iso(current)
        record["status"] = "released"
        active_path.unlink()
        status_path = _write_status(location, record, status="released", now=current)
    return {
        "ok": True,
        **location.metadata(),
        "job_id": job_id,
        "removed_active_record": _display_path(active_path, root),
        "status_path": status_path,
        "warnings": [issue.to_dict() for issue in location.warnings],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    list_active = sub.add_parser("list-active", help="list active Tenn dev-agent jobs")
    list_active.add_argument("--repo-root", type=Path, default=Path.cwd())
    list_active.add_argument("--stale-after-seconds", type=int)

    claim = sub.add_parser("claim", help="claim a task card lane/files")
    claim.add_argument("task_card", type=Path)
    claim.add_argument("--repo-root", type=Path, default=Path.cwd())
    claim.add_argument("--stale-after-seconds", type=int)

    heartbeat = sub.add_parser("heartbeat", help="refresh an active job heartbeat")
    heartbeat.add_argument("job_id")
    heartbeat.add_argument("--repo-root", type=Path, default=Path.cwd())

    release = sub.add_parser("release", help="release an active job")
    release.add_argument("job_id")
    release.add_argument("--repo-root", type=Path, default=Path.cwd())

    check_overlap = sub.add_parser("check-overlap", help="check a task card against active lane/file locks")
    check_overlap.add_argument("task_card", type=Path)
    check_overlap.add_argument("--repo-root", type=Path, default=Path.cwd())
    check_overlap.add_argument("--stale-after-seconds", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    stale_issue = _validate_stale_after_override(getattr(args, "stale_after_seconds", None))
    if stale_issue is not None:
        print(json.dumps({"ok": False, "issues": [stale_issue.to_dict()], "warnings": []}, indent=2, sort_keys=True))
        return 1

    try:
        if args.command == "list-active":
            result = list_active_jobs(repo_root=args.repo_root, stale_after_seconds=args.stale_after_seconds)
        elif args.command == "claim":
            result = claim_task_card(
                args.task_card,
                repo_root=args.repo_root,
                stale_after_seconds=args.stale_after_seconds,
            )
        elif args.command == "heartbeat":
            result = heartbeat_job(args.job_id, repo_root=args.repo_root)
        elif args.command == "release":
            result = release_job(args.job_id, repo_root=args.repo_root)
        elif args.command == "check-overlap":
            result = check_overlap_for_task_card(
                args.task_card,
                repo_root=args.repo_root,
                stale_after_seconds=args.stale_after_seconds,
            )
        else:  # pragma: no cover - argparse prevents this
            return 2
    except Exception as exc:
        result = {
            "ok": False,
            "issues": [RegistryIssue("registry", str(exc)).to_dict()],
            "warnings": [],
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
