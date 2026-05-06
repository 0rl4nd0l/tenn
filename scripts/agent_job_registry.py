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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

try:
    from scripts import agent_job_contract as contract
except ModuleNotFoundError:  # pragma: no cover - used when executed as scripts/agent_job_registry.py
    import agent_job_contract as contract  # type: ignore


ACTIVE_JOB_DIR = Path(".tenn/agent_jobs/active")
DEFAULT_STALE_AFTER_SECONDS = 30 * 60
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


def _read_git_branch(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    branch = completed.stdout.strip()
    return branch or None


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


def _active_record_path(repo_root: Path, job_id: str) -> Path:
    if not contract.JOB_ID_RE.fullmatch(job_id):
        raise ValueError("job_id must contain only letters, numbers, dot, underscore, or dash")
    return repo_root / ACTIVE_JOB_DIR / f"{job_id}.json"


def _status_path(repo_root: Path, output_dir: str, job_id: str) -> Path:
    report_dir = contract.resolve_report_dir(output_dir, job_id, repo_root=repo_root)
    return report_dir / "status.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _load_active_jobs(repo_root: Path) -> tuple[list[LoadedJob], list[RegistryIssue]]:
    active_dir = repo_root / ACTIVE_JOB_DIR
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
    for key in ("heartbeat_at", "claimed_at"):
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


def _is_registry_internal_path(path: str) -> bool:
    return (
        path == ".tenn/active_agent_task"
        or path.startswith(".tenn/agent_jobs/")
        or path.startswith("reports/agent_jobs/")
    )


def _dirty_files_outside_card(
    metadata: dict[str, Any],
    *,
    task_card_path: str | None,
    repo_root: Path,
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
        if _is_registry_internal_path(changed.path):
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
    root = (repo_root or Path.cwd()).resolve()
    current = _coerce_now(now)
    fallback_stale_after = _configured_stale_after(override=stale_after_seconds)
    jobs, warnings = _load_active_jobs(root)
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
        "active_jobs": active,
        "warnings": [issue.to_dict() for issue in [*warnings, *stale_warnings]],
    }


def check_overlap_for_task_card(
    task_card: Path,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
    changed_files: Sequence[contract.ChangedFile] | None = None,
) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    current = _coerce_now(now)

    try:
        markdown, task_card_path = _read_task_card(task_card, root)
    except FileNotFoundError:
        return {
            "ok": False,
            "issues": [RegistryIssue("task_card", f"task card not found: {task_card}").to_dict()],
            "warnings": [],
            "active_jobs": [],
        }

    valid, metadata, validation_issues, validation = _validate_task_card(markdown)
    if not valid:
        return {
            "ok": False,
            "validation": validation,
            "issues": [issue.to_dict() for issue in validation_issues],
            "warnings": [],
            "active_jobs": [],
        }

    job_id = str(metadata["job_id"])
    lane = str(metadata["lane"])
    output_dir = str(metadata["output_dir"])
    allowed = _allowed_files(metadata)
    fallback_stale_after = _configured_stale_after(metadata, override=stale_after_seconds)
    loaded_jobs, load_warnings = _load_active_jobs(root)
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
    warnings = list(load_warnings)
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
        changed_files=changed_files,
    )
    issues.extend(dirty_issues)
    for path in dirty_files:
        issues.append(RegistryIssue("changed_files", f"{path} is dirty outside current task card allowed_files"))

    return {
        "ok": not issues,
        "job_id": job_id,
        "lane": lane,
        "task_card": task_card_path,
        "active_jobs": active_jobs,
        "issues": [issue.to_dict() for issue in issues],
        "warnings": [issue.to_dict() for issue in warnings],
    }


def _write_status(repo_root: Path, record: dict[str, Any], *, status: str, now: datetime) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "job_id": record["job_id"],
        "status": status,
        "lane": record.get("lane"),
        "owner": record.get("owner"),
        "allowed_files": record.get("allowed_files", []),
        "output_dir": record.get("output_dir"),
        "task_card": record.get("task_card"),
        "claimed_at": record.get("claimed_at"),
        "heartbeat_at": record.get("heartbeat_at"),
        "updated_at": _to_iso(now),
        "active_record": f"{ACTIVE_JOB_DIR.as_posix()}/{record['job_id']}.json",
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
    root = (repo_root or Path.cwd()).resolve()
    current = _coerce_now(now)

    try:
        markdown, task_card_path = _read_task_card(task_card, root)
    except FileNotFoundError:
        return {
            "ok": False,
            "issues": [RegistryIssue("task_card", f"task card not found: {task_card}").to_dict()],
            "warnings": [],
        }

    valid, metadata, validation_issues, validation = _validate_task_card(markdown)
    if not valid:
        return {
            "ok": False,
            "validation": validation,
            "issues": [issue.to_dict() for issue in validation_issues],
            "warnings": [],
        }

    job_id = str(metadata["job_id"])
    fallback_stale_after = _configured_stale_after(metadata, override=stale_after_seconds)
    existing_jobs, load_warnings = _load_active_jobs(root)
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
                "issues": [
                    RegistryIssue("job_id", f"active job already exists for {job_id}", job_id=job_id).to_dict()
                ],
                "warnings": [issue.to_dict() for issue in load_warnings],
            }

    overlap = check_overlap_for_task_card(
        task_card,
        repo_root=root,
        now=current,
        stale_after_seconds=stale_after_seconds,
    )
    if not overlap.get("ok"):
        return {
            "ok": False,
            "issues": overlap.get("issues", []),
            "warnings": [*overlap.get("warnings", []), *[issue.to_dict() for issue in load_warnings]],
            "overlap": overlap,
        }

    record = {
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "lane": metadata["lane"],
        "owner": metadata["owner"],
        "allowed_files": _allowed_files(metadata),
        "approval_required": metadata["approval_required"],
        "timeout_seconds": metadata["timeout_seconds"],
        "output_dir": metadata["output_dir"],
        "mutation_mode": metadata["mutation_mode"],
        "production_data_access": metadata["production_data_access"],
        "task_card": task_card_path,
        "task_card_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "claimed_at": _to_iso(current),
        "heartbeat_at": _to_iso(current),
        "status": "active",
        "stale_after_seconds": fallback_stale_after,
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "branch": _read_git_branch(root),
    }
    active_path = _active_record_path(root, job_id)
    _atomic_write_json(active_path, record)
    status_path = _write_status(root, record, status="active", now=current)

    return {
        "ok": True,
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
    root = (repo_root or Path.cwd()).resolve()
    current = _coerce_now(now)
    try:
        active_path = _active_record_path(root, job_id)
    except ValueError as exc:
        return {"ok": False, "issues": [RegistryIssue("job_id", str(exc)).to_dict()], "warnings": []}

    if not active_path.exists():
        return {
            "ok": False,
            "issues": [RegistryIssue("job_id", f"active job not found: {job_id}", job_id=job_id).to_dict()],
            "warnings": [],
        }

    record, issue = _read_active_record(active_path, root)
    if issue is not None or record is None:
        return {
            "ok": False,
            "issues": [issue.to_dict() if issue else RegistryIssue("active_jobs", "active record is unreadable").to_dict()],
            "warnings": [],
        }

    record["heartbeat_at"] = _to_iso(current)
    record["status"] = "active"
    _atomic_write_json(active_path, record)
    status_path = _write_status(root, record, status="active", now=current)
    return {
        "ok": True,
        "job_id": job_id,
        "active_record": _display_path(active_path, root),
        "status_path": status_path,
        "record": record,
        "warnings": [],
    }


def release_job(
    job_id: str,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    current = _coerce_now(now)
    try:
        active_path = _active_record_path(root, job_id)
    except ValueError as exc:
        return {"ok": False, "issues": [RegistryIssue("job_id", str(exc)).to_dict()], "warnings": []}

    if not active_path.exists():
        return {
            "ok": False,
            "issues": [RegistryIssue("job_id", f"active job not found: {job_id}", job_id=job_id).to_dict()],
            "warnings": [],
        }

    record, issue = _read_active_record(active_path, root)
    if issue is not None or record is None:
        return {
            "ok": False,
            "issues": [issue.to_dict() if issue else RegistryIssue("active_jobs", "active record is unreadable").to_dict()],
            "warnings": [],
        }

    active_path.unlink()
    status_path = _write_status(root, record, status="released", now=current)
    return {
        "ok": True,
        "job_id": job_id,
        "removed_active_record": _display_path(active_path, root),
        "status_path": status_path,
        "warnings": [],
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

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
