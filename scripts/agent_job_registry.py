#!/usr/bin/env python3
"""Track active Tenn dev-agent jobs and lane/file overlap locks."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

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
DECISION_ENTRY_FILENAME = "DECISION_ENTRY.json"
GIT_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
V2_ACTIVE_RECORD_FIELDS = (
    "control_contract_version",
    "project_id",
    "claim_id",
    "hypothesis_id",
    "program_track",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
)


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


def _read_git_head(repo_root: Path) -> str | None:
    value = _git_output(repo_root, ["rev-parse", "--verify", "HEAD"])
    if value is None or GIT_OBJECT_ID_RE.fullmatch(value) is None:
        return None
    return value


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


def _v2_active_record_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata.get("control_contract_version") != contract.CONTROL_CONTRACT_VERSION_V2:
        return {}
    return {
        **{field: metadata[field] for field in V2_ACTIVE_RECORD_FIELDS},
        "scope_fingerprint": metadata["computed_scope_fingerprint"],
    }


def _record_is_v2_like(record: Mapping[str, Any]) -> bool:
    return (
        record.get("control_contract_version") == contract.CONTROL_CONTRACT_VERSION_V2
        or "scope_fingerprint" in record
        or any(field in record for field in V2_ACTIVE_RECORD_FIELDS[1:])
    )


def _task_card_text_declares_v2(markdown: str) -> bool:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")):
            continue
        key, separator, raw_value = line.partition(":")
        if separator and key.strip() == "control_contract_version":
            return raw_value.split("#", 1)[0].strip() == "2"
    return False


def _claimed_job_is_v2_like(
    location: RegistryLocation, record: Mapping[str, Any]
) -> bool:
    """Detect V2 even when mutable fields were stripped from the active record."""

    if _record_is_v2_like(record):
        return True
    task_card = record.get("task_card")
    if isinstance(task_card, str) and task_card.strip():
        try:
            markdown, _ = _read_task_card(Path(task_card), location.repo_root)
        except (OSError, UnicodeDecodeError):
            markdown = ""
        if _task_card_text_declares_v2(markdown):
            return True
    output_dir = record.get("output_dir")
    job_id = record.get("job_id")
    if isinstance(output_dir, str) and isinstance(job_id, str):
        try:
            status_path = _status_path(location.repo_root, output_dir, job_id)
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            status = None
        if isinstance(status, Mapping) and _record_is_v2_like(status):
            return True
    return False


def _read_task_card(task_card: Path, repo_root: Path) -> tuple[str, str]:
    candidate = task_card.expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    display_path = _display_path(candidate, repo_root)
    return candidate.read_text(encoding="utf-8"), display_path


def _validate_task_card(
    markdown: str,
) -> tuple[bool, dict[str, Any], list[RegistryIssue], list[RegistryIssue], dict[str, Any]]:
    validation = contract.validate_task_card_markdown(markdown)
    issues = [RegistryIssue(issue.field, issue.message) for issue in validation.issues]
    warnings = [RegistryIssue(warning.field, warning.message) for warning in validation.warnings]
    if validation.ok:
        issues.extend(_registry_validation_issues(validation.metadata))
    return not issues, validation.metadata, issues, warnings, validation.to_dict()


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
        warnings.extend(_v2_active_record_issues(loaded, path=path, repo_root=repo_root))
        jobs.append(LoadedJob(path=path, record=loaded))
    return jobs, warnings


def _v2_active_record_issues(
    record: dict[str, Any],
    *,
    path: Path,
    repo_root: Path,
) -> list[RegistryIssue]:
    """Validate semantic identity on active records that claim V2 scope."""

    version = record.get("control_contract_version")
    has_v2_identity = "scope_fingerprint" in record or any(
        field in record for field in V2_ACTIVE_RECORD_FIELDS[1:]
    )
    if version != contract.CONTROL_CONTRACT_VERSION_V2:
        if not has_v2_identity:
            return []
        return [
            RegistryIssue(
                "active_jobs",
                f"{_display_path(path, repo_root)} has V2 semantic fields without control_contract_version: 2",
                job_id=str(record.get("job_id") or "") or None,
            )
        ]

    problems: list[str] = []
    for field in V2_ACTIVE_RECORD_FIELDS[1:]:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{field} must be a non-empty string")
    if record.get("program_track") not in contract.PROGRAM_TRACKS:
        problems.append("program_track is invalid")

    fingerprint = record.get("scope_fingerprint")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint.strip()) is None:
        problems.append("scope_fingerprint must be a lowercase SHA-256 digest")
    else:
        try:
            expected = contract.compute_scope_fingerprint(record)
        except ValueError:
            expected = None
        if expected is not None and fingerprint.strip() != expected:
            problems.append(f"scope_fingerprint does not match semantic fields; expected {expected}")

    claim_head_sha = record.get("claim_head_sha")
    if (
        not isinstance(claim_head_sha, str)
        or GIT_OBJECT_ID_RE.fullmatch(claim_head_sha.strip()) is None
    ):
        problems.append("claim_head_sha must identify the Git HEAD recorded at claim time")

    if not problems:
        return []
    display = _display_path(path, repo_root)
    job_id = str(record.get("job_id") or "") or None
    return [
        RegistryIssue(
            "active_jobs",
            f"{display} has an invalid V2 active record: {'; '.join(problems)}",
            job_id=job_id,
        )
    ]


def _read_active_record(path: Path, repo_root: Path) -> tuple[dict[str, Any] | None, RegistryIssue | None]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, RegistryIssue("active_jobs", f"{_display_path(path, repo_root)} is invalid JSON: {exc}")
    except UnicodeDecodeError:
        return None, RegistryIssue(
            "active_jobs",
            f"{_display_path(path, repo_root)} is not UTF-8 JSON",
        )
    except OSError as exc:
        return None, RegistryIssue(
            "active_jobs",
            f"{_display_path(path, repo_root)} is unreadable: {exc}",
        )
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
    read_only: bool = False,
) -> dict[str, Any]:
    location = resolve_registry_location(repo_root)
    root = location.repo_root
    current = _coerce_now(now)
    fallback_stale_after = _configured_stale_after(override=stale_after_seconds)

    if read_only:
        jobs, warnings = _load_active_jobs(location.root, root)
    else:
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
        "read_only": read_only,
        "lock_acquired": not read_only,
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

    valid, metadata, validation_issues, validation_warnings, validation = _validate_task_card(markdown)
    if not valid:
        return {
            "ok": False,
            **location.metadata(),
            "validation": validation,
            "issues": [issue.to_dict() for issue in validation_issues],
            "warnings": [issue.to_dict() for issue in [*location.warnings, *validation_warnings]],
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
    warnings = [*location.warnings, *validation_warnings, *load_warnings]
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
        "task_card_sha256": record.get("task_card_sha256"),
        "worktree": record.get("worktree"),
        "branch": record.get("branch"),
        "git_common_dir": record.get("git_common_dir"),
        "claim_head_sha": record.get("claim_head_sha"),
        "started_at": record.get("started_at"),
        "last_seen_at": record.get("last_seen_at"),
        "claimed_at": record.get("claimed_at"),
        "heartbeat_at": record.get("heartbeat_at"),
        "updated_at": _to_iso(now),
        "active_record": _display_path(active_path, repo_root),
        **{field: record[field] for field in (*V2_ACTIVE_RECORD_FIELDS, "scope_fingerprint") if field in record},
        **{
            field: record[field]
            for field in ("closeout_validated", "decision_id", "abandon_reason")
            if field in record
        },
        **location.metadata(),
    }
    if status == "released":
        payload["released_at"] = _to_iso(now)
    elif status == "abandoned":
        payload["abandoned_at"] = _to_iso(now)

    status_path = _status_path(repo_root, str(record["output_dir"]), str(record["job_id"]))
    _atomic_write_json(status_path, payload)
    return _display_path(status_path, repo_root)


def _classify_v2_claim_locked(
    location: RegistryLocation,
    metadata: Mapping[str, Any],
    existing_jobs: Sequence[LoadedJob],
    *,
    now: datetime,
    fallback_stale_after_seconds: int,
) -> tuple[dict[str, Any], list[RegistryIssue]]:
    """Load, validate, and classify V2 semantic state under the registry lock."""

    ledger_path = location.root / "decision-ledger.jsonl"
    try:
        try:
            from scripts import agent_decision_ledger as decision_ledger
        except ModuleNotFoundError:  # pragma: no cover - direct script execution
            import agent_decision_ledger as decision_ledger  # type: ignore

        ledger_path = location.root / decision_ledger.LIVE_LEDGER_NAME
        if not ledger_path.is_file():
            classification = {
                "status": decision_ledger.DATA_MISSING,
                "scope_admitted": False,
                "no_delta_outcomes": 0,
                "decision_ledger": str(ledger_path),
            }
            return classification, [
                RegistryIssue(
                    "decision_ledger",
                    f"V2 claim requires an initialized decision ledger: {ledger_path}",
                    job_id=str(metadata.get("job_id") or "") or None,
                )
            ]
        entries = decision_ledger.load_entries(ledger_path)
        ledger_issues = decision_ledger.validate_entries(
            entries, source=str(ledger_path)
        )
    except (ImportError, ValueError, OSError) as exc:
        classification = {
            "status": "DATA_MISSING",
            "scope_admitted": False,
            "no_delta_outcomes": 0,
            "decision_ledger": str(ledger_path),
        }
        return classification, [
            RegistryIssue(
                "decision_ledger",
                f"V2 claim cannot use the decision ledger: {exc}",
                job_id=str(metadata.get("job_id") or "") or None,
            )
        ]

    if ledger_issues:
        classification = {
            "status": decision_ledger.DATA_MISSING,
            "scope_admitted": False,
            "no_delta_outcomes": 0,
            "decision_ledger": str(ledger_path),
        }
        return classification, [
            RegistryIssue(
                "decision_ledger",
                "V2 claim requires a valid decision ledger: "
                + "; ".join(ledger_issues),
                job_id=str(metadata.get("job_id") or "") or None,
            )
        ]

    active_jobs = [
        _job_summary(
            loaded,
            repo_root=location.repo_root,
            now=now,
            fallback_stale_after_seconds=fallback_stale_after_seconds,
        )
        for loaded in existing_jobs
    ]
    classification = decision_ledger.classify_v2_scope(
        metadata,
        active_jobs=active_jobs,
        decision_matches=entries,
    )
    classification["decision_ledger"] = str(ledger_path)
    if classification.get("scope_admitted") is True:
        return classification, []

    status = str(classification.get("status") or "BLOCKED_BY_DECISION")
    return classification, [
        RegistryIssue(
            "scope_fingerprint",
            f"V2 scope admission stopped with {status}",
            job_id=str(metadata.get("job_id") or "") or None,
        )
    ]


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

    valid, metadata, validation_issues, validation_warnings, validation = _validate_task_card(markdown)
    if not valid:
        return {
            "ok": False,
            **location.metadata(),
            "validation": validation,
            "issues": [issue.to_dict() for issue in validation_issues],
            "warnings": [issue.to_dict() for issue in [*location.warnings, *validation_warnings]],
        }

    job_id = str(metadata["job_id"])
    fallback_stale_after = _configured_stale_after(metadata, override=stale_after_seconds)
    scope_classification: dict[str, Any] | None = None
    with RegistryLock(location.root):
        existing_jobs, load_warnings = _load_active_jobs(location.root, root)
        if (
            metadata.get("control_contract_version")
            == contract.CONTROL_CONTRACT_VERSION_V2
            and load_warnings
        ):
            return {
                "ok": False,
                **location.metadata(),
                "scope_classification": {
                    "status": "DATA_MISSING",
                    "scope_admitted": False,
                    "no_delta_outcomes": 0,
                },
                "issues": [
                    RegistryIssue(
                        "active_jobs",
                        "V2 claim requires a fully readable active registry",
                        job_id=job_id,
                    ).to_dict()
                ],
                "warnings": [
                    issue.to_dict()
                    for issue in [
                        *location.warnings,
                        *validation_warnings,
                        *load_warnings,
                    ]
                ],
            }
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
                    "warnings": [
                        issue.to_dict()
                        for issue in [*location.warnings, *validation_warnings, *load_warnings]
                    ],
                }
            if _claimed_job_is_v2_like(location, existing.record) or (
                metadata.get("control_contract_version")
                == contract.CONTROL_CONTRACT_VERSION_V2
            ):
                return {
                    "ok": False,
                    **location.metadata(),
                    "issues": [
                        RegistryIssue(
                            "job_id",
                            (
                                f"stale V2 job still exists for {job_id}; explicitly "
                                "release it with --abandon-reason before reclaiming"
                            ),
                            job_id=job_id,
                        ).to_dict()
                    ],
                    "warnings": [
                        issue.to_dict()
                        for issue in [
                            *location.warnings,
                            *validation_warnings,
                            *load_warnings,
                        ]
                    ],
                }

        if (
            metadata.get("control_contract_version")
            == contract.CONTROL_CONTRACT_VERSION_V2
        ):
            scope_classification, scope_issues = _classify_v2_claim_locked(
                location,
                metadata,
                existing_jobs,
                now=current,
                fallback_stale_after_seconds=fallback_stale_after,
            )
            if scope_issues:
                return {
                    "ok": False,
                    **location.metadata(),
                    "scope_classification": scope_classification,
                    "issues": [issue.to_dict() for issue in scope_issues],
                    "warnings": [
                        issue.to_dict()
                        for issue in [
                            *location.warnings,
                            *validation_warnings,
                            *load_warnings,
                        ]
                    ],
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
            **_v2_active_record_fields(metadata),
        }
        if (
            metadata.get("control_contract_version")
            == contract.CONTROL_CONTRACT_VERSION_V2
        ):
            claim_head_sha = _read_git_head(root)
            if claim_head_sha is None:
                return {
                    "ok": False,
                    **location.metadata(),
                    "issues": [
                        RegistryIssue(
                            "git",
                            "V2 claim requires a readable committed Git HEAD",
                            job_id=job_id,
                        ).to_dict()
                    ],
                    "warnings": [
                        issue.to_dict()
                        for issue in [
                            *location.warnings,
                            *validation_warnings,
                            *load_warnings,
                        ]
                    ],
                }
            record["claim_head_sha"] = claim_head_sha
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
        **(
            {"scope_classification": scope_classification}
            if scope_classification is not None
            else {}
        ),
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


def _release_issue(field: str, message: str, record: Mapping[str, Any]) -> RegistryIssue:
    job_id = record.get("job_id")
    return RegistryIssue(
        field,
        message,
        job_id=str(job_id) if isinstance(job_id, str) and job_id else None,
    )


def _json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_name_status_z(output: str) -> list[str]:
    """Return every old/new repo path from Git ``--name-status -z`` output."""

    fields = output.split("\0")
    if fields and not fields[-1]:
        fields.pop()
    paths: list[str] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        if not status or index + path_count > len(fields):
            raise ValueError("git diff returned malformed --name-status -z output")
        for _ in range(path_count):
            paths.append(_normalize_repo_path(fields[index]))
            index += 1
    return paths


def _committed_paths_outside_card(
    metadata: Mapping[str, Any],
    record: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[list[str], RegistryIssue | None]:
    """Find committed paths outside the exact V2 allowlist since claim HEAD."""

    claim_head_sha = record.get("claim_head_sha")
    if (
        not isinstance(claim_head_sha, str)
        or GIT_OBJECT_ID_RE.fullmatch(claim_head_sha.strip()) is None
    ):
        return [], _release_issue(
            "claim_head_sha",
            "V2 release requires the Git HEAD recorded at claim time",
            record,
        )
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", claim_head_sha, "HEAD"],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ancestry.returncode != 0:
        message = ancestry.stderr.strip() or "claim HEAD is not an ancestor of HEAD"
        return [], _release_issue(
            "git",
            f"cannot verify committed V2 scope since claim: {message}",
            record,
        )
    completed = subprocess.run(
        [
            "git",
            "log",
            "--format=",
            "--name-status",
            "-z",
            "--find-renames",
            f"{claim_head_sha}..HEAD",
            "--",
        ],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or "git log failed"
        return [], _release_issue(
            "git",
            f"cannot verify committed V2 scope since claim: {message}",
            record,
        )
    try:
        changed_paths = _parse_name_status_z(completed.stdout)
        allowed = set(_allowed_files(dict(metadata)))
    except ValueError as exc:
        return [], _release_issue("git", str(exc), record)
    return sorted({path for path in changed_paths if path not in allowed}), None


def _quarantine_abandoned_record_locked(
    location: RegistryLocation,
    active_path: Path,
    job_id: str,
    *,
    abandon_reason: str,
    now: datetime,
    record_issue: RegistryIssue | None = None,
) -> tuple[str, str]:
    """Write an abandonment receipt, then atomically remove a bad active record."""

    raw = active_path.read_bytes()
    timestamp = _to_iso(now)
    file_timestamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    abandoned_dir = location.root / "abandoned"
    quarantine_path = abandoned_dir / f"{job_id}-{file_timestamp}.active.json"
    receipt_path = abandoned_dir / f"{job_id}-{file_timestamp}.status.json"
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "status": "abandoned",
        "closeout_validated": False,
        "abandon_reason": abandon_reason,
        "abandoned_at": timestamp,
        "active_record": _display_path(active_path, location.repo_root),
        "active_record_sha256": hashlib.sha256(raw).hexdigest(),
        "quarantined_record": _display_path(quarantine_path, location.repo_root),
        **location.metadata(),
    }
    if record_issue is not None:
        payload["record_issue"] = record_issue.message

    _atomic_write_json(receipt_path, payload)
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(active_path, quarantine_path)
    return (
        _display_path(receipt_path, location.repo_root),
        _display_path(quarantine_path, location.repo_root),
    )


def _v2_release_validation_locked(
    location: RegistryLocation,
    record: dict[str, Any],
    active_path: Path,
) -> tuple[list[RegistryIssue], dict[str, Any] | None]:
    """Validate and publish one V2 closeout while the registry lock is held."""

    root = location.repo_root
    issues = _v2_active_record_issues(record, path=active_path, repo_root=root)
    if issues:
        return issues, None

    task_card = record.get("task_card")
    if not isinstance(task_card, str) or not task_card.strip():
        return [_release_issue("task_card", "V2 release requires its recorded task card", record)], None
    try:
        markdown, task_card_path = _read_task_card(Path(task_card), root)
    except (OSError, UnicodeDecodeError) as exc:
        return [_release_issue("task_card", f"cannot read recorded V2 task card: {exc}", record)], None

    recorded_hash = record.get("task_card_sha256")
    observed_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if recorded_hash != observed_hash:
        return [
            _release_issue(
                "task_card_sha256",
                "V2 task card changed after claim; abandon and reclaim instead of releasing success",
                record,
            )
        ], None

    validation = contract.validate_task_card_markdown(markdown)
    if not validation.ok:
        return [
            _release_issue(issue.field, issue.message, record)
            for issue in validation.issues
        ], None
    metadata = validation.metadata
    identity_mismatches: list[str] = []
    comparisons = {
        "job_id": metadata.get("job_id"),
        "task_card": task_card_path,
        "scope_fingerprint": metadata.get("computed_scope_fingerprint"),
        **{field: metadata.get(field) for field in V2_ACTIVE_RECORD_FIELDS},
    }
    for field, expected in comparisons.items():
        if record.get(field) != expected:
            identity_mismatches.append(field)
    if identity_mismatches:
        return [
            _release_issue(
                "active_job",
                "V2 active claim no longer matches its task card: "
                + ", ".join(sorted(identity_mismatches)),
                record,
            )
        ], None

    closeout = contract.check_closeout_for_task_card_markdown(markdown, repo_root=root)
    if not closeout.ok:
        return [
            _release_issue(issue.field, issue.message, record)
            for issue in closeout.issues
        ], None

    output_dir = metadata.get("output_dir")
    if not isinstance(output_dir, str):
        return [_release_issue("output_dir", "V2 release requires output_dir", record)], None
    report_dir = contract.resolve_report_dir(
        output_dir,
        str(metadata["job_id"]),
        repo_root=root,
    )
    outcome_path = report_dir / contract.RUN_OUTCOME_FILENAME
    try:
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_release_issue("RUN_OUTCOME.json", str(exc), record)], None
    if not isinstance(outcome, Mapping):
        return [_release_issue("RUN_OUTCOME.json", "must contain a JSON object", record)], None

    committed_outside_card, committed_issue = _committed_paths_outside_card(
        metadata,
        record,
        repo_root=root,
    )
    if committed_issue is not None:
        return [committed_issue], None
    if committed_outside_card:
        return [
            _release_issue(
                "changed_files",
                "commits since claim changed paths outside allowed_files: "
                + ", ".join(committed_outside_card),
                record,
            )
        ], None

    try:
        try:
            from scripts import agent_decision_ledger as decision_ledger
        except ModuleNotFoundError:  # pragma: no cover - direct script execution
            import agent_decision_ledger as decision_ledger  # type: ignore

        ledger_path = location.root / decision_ledger.LIVE_LEDGER_NAME
        if not ledger_path.is_file():
            return [
                _release_issue(
                    "decision_ledger",
                    f"V2 release decision ledger is missing: {ledger_path}",
                    record,
                )
            ], None
        entries = decision_ledger.load_entries(ledger_path)
        ledger_issues = decision_ledger.validate_entries(
            entries, source=str(ledger_path)
        )
    except (OSError, decision_ledger.DecisionLedgerError) as exc:
        return [_release_issue("decision_ledger", str(exc), record)], None
    if ledger_issues:
        return [
            _release_issue("decision_ledger", issue, record)
            for issue in ledger_issues
        ], None

    decision_relative_path = (
        f"{output_dir.rstrip('/')}/{DECISION_ENTRY_FILENAME}"
    )
    try:
        allowed_files = set(_allowed_files(metadata))
    except ValueError as exc:
        return [_release_issue("allowed_files", str(exc), record)], None
    if decision_relative_path not in allowed_files:
        return [
            _release_issue(
                "allowed_files",
                f"V2 release requires exact decision candidate path {decision_relative_path}",
                record,
            )
        ], None

    decision_path = report_dir / DECISION_ENTRY_FILENAME
    if decision_path.is_symlink():
        return [
            _release_issue(
                DECISION_ENTRY_FILENAME,
                "decision candidate must not be a symbolic link",
                record,
            )
        ], None
    try:
        candidates = decision_ledger.load_entry_file(decision_path)
    except (OSError, decision_ledger.DecisionLedgerError) as exc:
        return [_release_issue(DECISION_ENTRY_FILENAME, str(exc), record)], None
    if len(candidates) != 1:
        return [
            _release_issue(
                DECISION_ENTRY_FILENAME,
                f"must contain exactly one decision entry; found {len(candidates)}",
                record,
            )
        ], None
    candidate = candidates[0]
    candidate_issues = decision_ledger.validate_entry(
        candidate,
        source=decision_relative_path,
    )
    if candidate_issues:
        return [
            _release_issue(DECISION_ENTRY_FILENAME, issue, record)
            for issue in candidate_issues
        ], None

    expected_identity = {
        "scope_fingerprint": record.get("scope_fingerprint"),
        "task_id": record.get("job_id"),
        "run_id": record.get("session_id"),
        "outcome_status": outcome.get("status"),
        "phase_before": outcome.get("state_before"),
        "phase_after": outcome.get("state_after"),
        **{field: record.get(field) for field in V2_ACTIVE_RECORD_FIELDS[1:]},
    }
    mismatched_fields = sorted(
        field
        for field, expected in expected_identity.items()
        if candidate.get(field) != expected
    )
    if _json_key(candidate.get("decision_delta")) != _json_key(
        outcome.get("decision_delta")
    ):
        mismatched_fields.append("decision_delta")
    if mismatched_fields:
        return [
            _release_issue(
                DECISION_ENTRY_FILENAME,
                "decision candidate does not match current card/outcome identity: "
                + ", ".join(mismatched_fields),
                record,
            )
        ], None
    decision_id = candidate.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id.strip():
        return [_release_issue("decision_id", "matching decision has no identifier", record)], None

    existing_candidate = next(
        (entry for entry in entries if entry.get("decision_id") == decision_id),
        None,
    )
    identical_latest_retry = False
    if existing_candidate is not None:
        if _json_key(existing_candidate) != _json_key(candidate):
            return [
                _release_issue(
                    "decision_id",
                    "existing decision id does not match the current release candidate",
                    record,
                )
            ], None
        if not decision_ledger.is_latest_chain_head(entries, existing_candidate):
            return [
                _release_issue(
                    "decision_id",
                    "identical existing release entry is not the latest decision in its scope fingerprint and program track",
                    record,
                )
            ], None
        identical_latest_retry = True

    if not identical_latest_retry:
        closeout_classification = decision_ledger.classify_v2_scope(
            metadata,
            active_jobs=[],
            decision_matches=entries,
        )
        classification_status = str(
            closeout_classification.get("status") or "BLOCKED_BY_DECISION"
        )
        material_loop_override = (
            classification_status == "LOOP_GUARD_STOP"
            and decision_ledger.has_decision_delta(candidate.get("decision_delta"))
        )
        if (
            closeout_classification.get("scope_admitted") is not True
            and not material_loop_override
        ):
            return [
                _release_issue(
                    "semantic_closeout",
                    (
                        "V2 closeout is no longer admissible against the current "
                        f"decision ledger: {classification_status}"
                    ),
                    record,
                )
            ], None

    try:
        appended = decision_ledger.append_entry_locked(
            ledger_path,
            candidate,
            existing=entries,
            allow_existing_identical=True,
        )
    except decision_ledger.DecisionLedgerError as exc:
        return [_release_issue("decision_ledger", str(exc), record)], None
    return [], {
        "decision_id": decision_id,
        "decision_appended": appended,
    }


def _v2_abandonment_is_recovery(
    location: RegistryLocation,
    record: dict[str, Any],
    active_path: Path,
    *,
    now: datetime,
) -> bool:
    """Limit abandonment to stale or invalid administrative claim recovery."""

    if _v2_active_record_issues(
        record, path=active_path, repo_root=location.repo_root
    ):
        return True
    stale, _, _ = _stale_state(
        record,
        now=now,
        fallback_stale_after_seconds=_configured_stale_after(record),
    )
    if stale:
        return True

    task_card = record.get("task_card")
    if not isinstance(task_card, str) or not task_card.strip():
        return True
    try:
        markdown, _ = _read_task_card(Path(task_card), location.repo_root)
    except (OSError, UnicodeDecodeError):
        return True
    observed_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if record.get("task_card_sha256") != observed_hash:
        return True
    validation = contract.validate_task_card_markdown(markdown)
    if not validation.ok:
        return True
    expected = {
        "job_id": validation.metadata.get("job_id"),
        "scope_fingerprint": validation.metadata.get("computed_scope_fingerprint"),
        **{
            field: validation.metadata.get(field)
            for field in V2_ACTIVE_RECORD_FIELDS
        },
    }
    return any(record.get(field) != value for field, value in expected.items())


def release_job(
    job_id: str,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
    abandon_reason: str | None = None,
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

        if abandon_reason is not None and not abandon_reason.strip():
            return {
                "ok": False,
                **location.metadata(),
                "issues": [
                    RegistryIssue(
                        "abandon_reason",
                        "must be a non-empty explanation when provided",
                        job_id=job_id,
                    ).to_dict()
                ],
                "warnings": [issue.to_dict() for issue in location.warnings],
            }

        record, issue = _read_active_record(active_path, root)
        if issue is not None or record is None:
            if abandon_reason is not None:
                status_path, quarantined_record = _quarantine_abandoned_record_locked(
                    location,
                    active_path,
                    job_id,
                    abandon_reason=abandon_reason.strip(),
                    now=current,
                    record_issue=issue,
                )
                return {
                    "ok": True,
                    **location.metadata(),
                    "job_id": job_id,
                    "removed_active_record": _display_path(active_path, root),
                    "quarantined_record": quarantined_record,
                    "status_path": status_path,
                    "status": "abandoned",
                    "closeout_validated": False,
                    "warnings": [
                        warning.to_dict() for warning in location.warnings
                    ],
                }
            return {
                "ok": False,
                **location.metadata(),
                "issues": [
                    issue.to_dict() if issue else RegistryIssue("active_jobs", "active record is unreadable").to_dict()
                ],
                "warnings": [issue.to_dict() for issue in location.warnings],
            }

        is_v2 = _claimed_job_is_v2_like(location, record)
        decision_id: str | None = None
        decision_appended: bool | None = None
        if (
            is_v2
            and abandon_reason is not None
            and not _v2_abandonment_is_recovery(
                location, record, active_path, now=current
            )
        ):
            return {
                "ok": False,
                **location.metadata(),
                "issues": [
                    RegistryIssue(
                        "abandon_reason",
                        (
                            "valid non-stale V2 claims must close with RUN_OUTCOME "
                            "and a decision entry; abandonment is only for stale, "
                            "corrupt, or contract-drift recovery"
                        ),
                        job_id=job_id,
                    ).to_dict()
                ],
                "warnings": [
                    warning.to_dict() for warning in location.warnings
                ],
            }
        if is_v2 and abandon_reason is None:
            release_issues, decision_publication = _v2_release_validation_locked(
                location, record, active_path
            )
            if release_issues:
                return {
                    "ok": False,
                    **location.metadata(),
                    "issues": [issue.to_dict() for issue in release_issues],
                    "warnings": [issue.to_dict() for issue in location.warnings],
                }
            assert decision_publication is not None
            decision_id = str(decision_publication["decision_id"])
            decision_appended = bool(decision_publication["decision_appended"])

        record["last_seen_at"] = _to_iso(current)
        if abandon_reason is not None:
            record["status"] = "abandoned"
            record["abandon_reason"] = abandon_reason.strip()
            record["closeout_validated"] = False
        else:
            record["status"] = "released"
            if is_v2:
                record["closeout_validated"] = True
                record["decision_id"] = decision_id
        quarantined_record: str | None = None
        try:
            status_path = _write_status(
                location, record, status=str(record["status"]), now=current
            )
        except (KeyError, OSError, TypeError, ValueError):
            if abandon_reason is None:
                raise
            status_path, quarantined_record = _quarantine_abandoned_record_locked(
                location,
                active_path,
                job_id,
                abandon_reason=abandon_reason.strip(),
                now=current,
                record_issue=RegistryIssue(
                    "active_jobs",
                    "active record has no usable report status location",
                    job_id=job_id,
                ),
            )
        else:
            active_path.unlink()
    return {
        "ok": True,
        **location.metadata(),
        "job_id": job_id,
        "removed_active_record": _display_path(active_path, root),
        "status_path": status_path,
        "status": record["status"],
        "closeout_validated": record.get("closeout_validated"),
        **(
            {"quarantined_record": quarantined_record}
            if quarantined_record is not None
            else {}
        ),
        **({"decision_id": decision_id} if decision_id else {}),
        **(
            {"decision_appended": decision_appended}
            if decision_appended is not None
            else {}
        ),
        "warnings": [issue.to_dict() for issue in location.warnings],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    list_active = sub.add_parser("list-active", help="list active Tenn dev-agent jobs")
    list_active.add_argument("--repo-root", type=Path, default=Path.cwd())
    list_active.add_argument("--stale-after-seconds", type=int)
    list_active.add_argument(
        "--read-only",
        action="store_true",
        help="read active jobs without acquiring or creating a registry lock",
    )

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
    release.add_argument(
        "--abandon-reason",
        help="explicitly abandon a V2 claim without claiming successful closeout",
    )

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
            result = list_active_jobs(
                repo_root=args.repo_root,
                stale_after_seconds=args.stale_after_seconds,
                read_only=args.read_only,
            )
        elif args.command == "claim":
            result = claim_task_card(
                args.task_card,
                repo_root=args.repo_root,
                stale_after_seconds=args.stale_after_seconds,
            )
        elif args.command == "heartbeat":
            result = heartbeat_job(args.job_id, repo_root=args.repo_root)
        elif args.command == "release":
            result = release_job(
                args.job_id,
                repo_root=args.repo_root,
                abandon_reason=args.abandon_reason,
            )
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
