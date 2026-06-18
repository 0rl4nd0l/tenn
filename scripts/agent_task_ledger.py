#!/usr/bin/env python3
"""Manage Tenn Agent Task Ledger JSONL records."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from scripts import agent_job_registry
except ModuleNotFoundError:  # pragma: no cover - used when executed as scripts/agent_task_ledger.py
    import agent_job_registry  # type: ignore


DATA_MISSING = "DATA_MISSING"
LIVE_LEDGER_NAME = "task-ledger.jsonl"
COMMITTED_LEDGER_JSONL = Path("docs/agent_registry/task_ledger/LEDGER.jsonl")
COMMITTED_LEDGER_MD = Path("docs/agent_registry/task_ledger/LEDGER.md")

REQUIRED_FIELDS = (
    "task_id",
    "parent_task_id",
    "workflow",
    "status",
    "started_at",
    "updated_at",
    "owner",
    "session_id",
    "thread_id",
    "codex_goal_id",
    "source_session_ref",
    "issue_refs",
    "pr_refs",
    "branch",
    "worktree",
    "base",
    "files_touched",
    "artifacts",
    "summary",
    "validation",
    "next_action",
    "owner_boundary",
    "supersedes",
    "superseded_by",
)

STATUSES = {
    "claimed",
    "implementation_started",
    "blocked",
    "waiting_on_user",
    "waiting_on_timer",
    "pr_opened",
    "merged",
    "done",
    "parked",
    "superseded",
    "owner_boundary",
}

SUMMARY_ORDER = (
    "claimed",
    "implementation_started",
    "blocked",
    "waiting_on_user",
    "waiting_on_timer",
    "pr_opened",
    "merged",
    "done",
    "parked",
    "superseded",
    "owner_boundary",
)

EVIDENCE_GRADES = {
    "VERIFIED",
    "USER_REPORTED",
    "INFERRED",
    "UNKNOWN",
    "CONFLICT",
    DATA_MISSING,
}

VALIDATION_STATUSES = {
    "not_run",
    "passed",
    "failed",
    "partial",
    "blocked",
    "skipped",
    "data_missing",
    DATA_MISSING,
}


class LedgerError(ValueError):
    """Raised for user-facing ledger validation or parsing errors."""


def _repo_root(repo_root: Path | None) -> Path:
    start = (repo_root or Path.cwd()).resolve()
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve(strict=False)
    return start


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
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve(strict=False)


def _fallback_registry_root(repo_root: Path) -> Path:
    raw_common = _git_output(repo_root, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    if raw_common:
        return (Path(raw_common) / agent_job_registry.SHARED_REGISTRY_DIR_NAME).resolve(strict=False)

    raw_common = _git_output(repo_root, ["rev-parse", "--git-common-dir"])
    if raw_common:
        return (_path_from_config(raw_common, repo_root) / agent_job_registry.SHARED_REGISTRY_DIR_NAME).resolve(
            strict=False
        )

    return (repo_root / agent_job_registry.REPO_LOCAL_REGISTRY_ROOT).resolve(strict=False)


def resolve_live_ledger_path(repo_root: Path | None = None) -> Path:
    """Resolve the branch-independent live ledger path."""

    root = _repo_root(repo_root)
    try:
        location = agent_job_registry.resolve_registry_location(root)
        registry_root = Path(location.root)
    except Exception:
        registry_root = _fallback_registry_root(root)
    return (registry_root / LIVE_LEDGER_NAME).resolve(strict=False)


def committed_ledger_path(repo_root: Path | None = None) -> Path:
    return _repo_root(repo_root) / COMMITTED_LEDGER_JSONL


def _json_line(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def _loads_json(text: str, *, source: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{source}: invalid JSON: line {exc.lineno} column {exc.colno}: {exc.msg}") from exc


def _load_entries_from_text(text: str, *, source: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []

    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        entries: list[dict[str, Any]] = []
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LedgerError(
                    f"{source}:{line_no}: invalid JSON: column {exc.colno}: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise LedgerError(f"{source}:{line_no}: entry must be a JSON object")
            entries.append(value)
        return entries

    if isinstance(loaded, dict):
        return [loaded]
    if isinstance(loaded, list):
        entries = []
        for idx, value in enumerate(loaded):
            if not isinstance(value, dict):
                raise LedgerError(f"{source}[{idx}]: entry must be a JSON object")
            entries.append(value)
        return entries
    raise LedgerError(f"{source}: expected a JSON object, array, or JSONL objects")


def load_entries(path: Path) -> list[dict[str, Any]]:
    try:
        return _load_entries_from_text(path.read_text(encoding="utf-8"), source=str(path))
    except OSError as exc:
        raise LedgerError(f"{path}: unable to read file: {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        raise LedgerError(f"{path}: file must be UTF-8 text") from exc


def _require_str(entry: dict[str, Any], field: str, issues: list[str], *, allow_data_missing: bool = True) -> None:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{field}: must be a non-empty string")
        return
    if not allow_data_missing and value == DATA_MISSING:
        issues.append(f"{field}: DATA_MISSING is not allowed")


def _require_nullable_str(entry: dict[str, Any], field: str, issues: list[str]) -> None:
    value = entry.get(field)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        issues.append(f"{field}: must be null or a non-empty string")


def _require_bool(entry: dict[str, Any], field: str, issues: list[str]) -> None:
    if not isinstance(entry.get(field), bool):
        issues.append(f"{field}: must be a boolean")


def _require_str_list(entry: dict[str, Any], field: str, issues: list[str]) -> None:
    value = entry.get(field)
    if not isinstance(value, list):
        issues.append(f"{field}: must be a list")
        return
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"{field}[{idx}]: must be a non-empty string")


def _require_ref_list(entry: dict[str, Any], field: str, issues: list[str]) -> None:
    value = entry.get(field)
    if not isinstance(value, list):
        issues.append(f"{field}: must be a list")
        return
    for idx, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (str, int)):
            issues.append(f"{field}[{idx}]: must be a string or integer reference")
        elif isinstance(item, str) and not item.strip():
            issues.append(f"{field}[{idx}]: must be non-empty")


def validate_entry(entry: dict[str, Any], *, source: str = "<entry>") -> list[str]:
    issues: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            issues.append(f"{field}: required field is missing")

    if issues:
        return [f"{source}: {issue}" for issue in issues]

    _require_str(entry, "task_id", issues, allow_data_missing=False)
    _require_nullable_str(entry, "parent_task_id", issues)
    for field in (
        "workflow",
        "started_at",
        "updated_at",
        "owner",
        "session_id",
        "thread_id",
        "codex_goal_id",
        "source_session_ref",
        "branch",
        "worktree",
        "base",
        "summary",
        "next_action",
    ):
        _require_str(entry, field, issues)

    status = entry.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        issues.append(f"status: must be one of {', '.join(sorted(STATUSES))}")

    for field in ("issue_refs", "pr_refs"):
        _require_ref_list(entry, field, issues)
    for field in ("files_touched", "artifacts", "supersedes", "superseded_by"):
        _require_str_list(entry, field, issues)
    _require_bool(entry, "owner_boundary", issues)

    validation = entry.get("validation")
    if not isinstance(validation, dict):
        issues.append("validation: must be an object")
    else:
        validation_status = validation.get("status")
        if not isinstance(validation_status, str) or validation_status not in VALIDATION_STATUSES:
            issues.append(
                "validation.status: must be one of "
                + ", ".join(sorted(str(status) for status in VALIDATION_STATUSES))
            )
        commands = validation.get("commands", [])
        if not isinstance(commands, list):
            issues.append("validation.commands: must be a list when present")
        else:
            for idx, command in enumerate(commands):
                if not isinstance(command, str) or not command.strip():
                    issues.append(f"validation.commands[{idx}]: must be a non-empty string")

    evidence_grade = entry.get("evidence_grade")
    if evidence_grade is not None and evidence_grade not in EVIDENCE_GRADES:
        issues.append(f"evidence_grade: must be one of {', '.join(sorted(EVIDENCE_GRADES))}")

    evidence_grades = entry.get("evidence_grades")
    if evidence_grades is not None:
        if not isinstance(evidence_grades, dict):
            issues.append("evidence_grades: must be an object when present")
        else:
            for key, value in evidence_grades.items():
                if not isinstance(key, str) or not key:
                    issues.append("evidence_grades: keys must be non-empty strings")
                if value not in EVIDENCE_GRADES:
                    issues.append(f"evidence_grades.{key}: must be one of {', '.join(sorted(EVIDENCE_GRADES))}")

    evidence_status = entry.get("evidence_status")
    if evidence_status is not None and evidence_status not in EVIDENCE_GRADES:
        issues.append(f"evidence_status: must be one of {', '.join(sorted(EVIDENCE_GRADES))}")

    return [f"{source}: {issue}" for issue in issues]


def validate_entries(entries: Iterable[dict[str, Any]], *, source: str) -> list[str]:
    issues: list[str] = []
    for idx, entry in enumerate(entries, start=1):
        issues.extend(validate_entry(entry, source=f"{source}:{idx}"))
    return issues


def _coerce_updated_at(entry: dict[str, Any]) -> dict[str, Any]:
    updated = dict(entry)
    if not updated.get("updated_at") and isinstance(updated.get("started_at"), str):
        updated["updated_at"] = updated["started_at"]
    return updated


def _read_entry_arg(args: argparse.Namespace) -> dict[str, Any]:
    if args.entry_json:
        loaded = _loads_json(args.entry_json, source="--entry-json")
        if not isinstance(loaded, dict):
            raise LedgerError("--entry-json: expected a JSON object")
        return loaded
    if args.entry_file:
        entries = load_entries(args.entry_file)
        if len(entries) != 1:
            raise LedgerError(f"{args.entry_file}: expected exactly one entry, found {len(entries)}")
        return entries[0]
    raise LedgerError("append requires --entry-json or --entry-file")


def _query_goal_db(thread_id: str) -> dict[str, str]:
    db_path = Path.home() / ".codex" / "goals_1.sqlite"
    if not thread_id or thread_id == DATA_MISSING or not db_path.exists():
        return {}
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "select goal_id from thread_goals where thread_id = ?",
                (thread_id,),
            ).fetchone()
    except sqlite3.Error:
        return {}
    if not row or not row[0]:
        return {}
    return {"codex_goal_id": str(row[0])}


def discover_identity() -> dict[str, str]:
    session_id = DATA_MISSING
    for key in ("TENN_AGENT_SESSION_ID", "CODEX_SESSION_ID", "OPENAI_SESSION_ID", "CLAUDE_SESSION_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            session_id = value
            break

    thread_id = DATA_MISSING
    for key in ("CODEX_THREAD_ID", "OPENAI_THREAD_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            thread_id = value
            break

    codex_goal_id = os.environ.get("CODEX_GOAL_ID", "").strip() or DATA_MISSING
    goal_row = _query_goal_db(thread_id)
    if codex_goal_id == DATA_MISSING:
        codex_goal_id = goal_row.get("codex_goal_id", DATA_MISSING)

    if thread_id != DATA_MISSING:
        source_session_ref = f"codex:thread:{thread_id}"
    elif session_id != DATA_MISSING:
        source_session_ref = f"codex:session:{session_id}"
    else:
        source_session_ref = DATA_MISSING

    return {
        "session_id": session_id,
        "thread_id": thread_id,
        "codex_goal_id": codex_goal_id,
        "source_session_ref": source_session_ref,
    }


def fill_identity(entry: dict[str, Any]) -> dict[str, Any]:
    identity = discover_identity()
    updated = dict(entry)
    for key, value in identity.items():
        if updated.get(key) in (None, "", DATA_MISSING) and value != DATA_MISSING:
            updated[key] = value
    return updated


def append_entry(path: Path, entry: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _json_line(entry).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(path, flags, 0o644)
    except OSError as exc:
        raise LedgerError(f"{path}: unable to open ledger for append: {exc.strerror or exc}") from exc
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise LedgerError(f"{path}: unable to append entry: wrote zero bytes")
            remaining = remaining[written:]
    except OSError as exc:
        raise LedgerError(f"{path}: unable to append entry: {exc.strerror or exc}") from exc
    finally:
        os.close(fd)


def _write_temp_text(target: Path, text: str) -> Path:
    try:
        fd, raw_tmp_path = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    except OSError as exc:
        raise LedgerError(f"{target}: unable to create temporary file: {exc.strerror or exc}") from exc
    tmp_path = Path(raw_tmp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise LedgerError(f"{target}: unable to write temporary file: {exc.strerror or exc}") from exc
    return tmp_path


def write_committed_snapshot(md_path: Path, md_text: str, jsonl_path: Path, jsonl_text: str) -> None:
    targets = ((md_path, md_text), (jsonl_path, jsonl_text))
    temp_paths: list[Path] = []
    try:
        for path, _text in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.is_dir():
                raise LedgerError(f"{path}: target is a directory")
        for path, text in targets:
            temp_paths.append(_write_temp_text(path, text))
        for tmp_path, (target_path, _text) in zip(temp_paths, targets):
            os.replace(tmp_path, target_path)
    except OSError as exc:
        raise LedgerError(f"committed ledger snapshot: unable to publish: {exc.strerror or exc}") from exc
    finally:
        for tmp_path in temp_paths:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass


def _source_payload(kind: str, path: Path, exists: bool, entry_count: int = 0) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": str(path),
        "exists": exists,
        "entry_count": entry_count,
    }


def _load_source(kind: str, path: Path, *, required: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    if not path.exists():
        source = _source_payload(kind, path, False)
        issue = f"{kind}: missing: {path}" if required else ""
        return [], source, [issue] if issue else []
    try:
        entries = load_entries(path)
    except LedgerError as exc:
        return [], _source_payload(kind, path, True), [str(exc)]
    return entries, _source_payload(kind, path, True, len(entries)), []


def _default_sources(repo_root: Path | None) -> list[tuple[str, Path, bool]]:
    root = _repo_root(repo_root)
    return [
        ("live", resolve_live_ledger_path(root), False),
        ("committed", root / COMMITTED_LEDGER_JSONL, False),
    ]


def _selected_sources(args: argparse.Namespace) -> list[tuple[str, Path, bool]]:
    if getattr(args, "ledger_path", None):
        return [("custom", path, True) for path in args.ledger_path]
    return _default_sources(args.repo_root)


def load_selected_entries(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    issues: list[str] = []
    for kind, path, required in _selected_sources(args):
        loaded, source, source_issues = _load_source(kind, path, required=required)
        entries.extend(loaded)
        sources.append(source)
        issues.extend(source_issues)
    return entries, sources, issues


def _normalize_ref(value: str) -> str:
    return value.strip().lstrip("#")


def _refs_match(values: Iterable[Any], query: str) -> bool:
    wanted = _normalize_ref(query)
    for value in values:
        text = _normalize_ref(str(value))
        if text == wanted:
            return True
    return False


def _path_match(paths: Iterable[Any], query: str) -> bool:
    wanted = query.strip().replace("\\", "/")
    for value in paths:
        text = str(value).replace("\\", "/")
        if text == wanted or wanted in text:
            return True
    return False


def entry_matches(entry: dict[str, Any], args: argparse.Namespace) -> bool:
    checks: list[bool] = []
    exact_fields = {
        "task_id": "task_id",
        "parent_task_id": "parent_task_id",
        "session_id": "session_id",
        "thread_id": "thread_id",
    }
    for arg_name, field in exact_fields.items():
        value = getattr(args, arg_name, None)
        if value:
            checks.append(entry.get(field) == value)

    for arg_name, field in (("branch", "branch"), ("worktree", "worktree")):
        value = getattr(args, arg_name, None)
        if value:
            checks.append(value in str(entry.get(field, "")))

    if getattr(args, "issue", None):
        checks.append(_refs_match(entry.get("issue_refs", []), args.issue))
    if getattr(args, "pr", None):
        checks.append(_refs_match(entry.get("pr_refs", []), args.pr))
    if getattr(args, "path", None):
        checks.append(
            _path_match(entry.get("files_touched", []), args.path)
            or _path_match(entry.get("artifacts", []), args.path)
        )
    if getattr(args, "text", None):
        haystack = json.dumps(entry, sort_keys=True).lower()
        checks.append(args.text.lower() in haystack)

    if not checks:
        return True
    return all(checks)


def _match_order_key(match: dict[str, Any]) -> tuple[str, int]:
    entry = match.get("entry", {})
    timestamp = ""
    if isinstance(entry, dict):
        for field in ("updated_at", "started_at"):
            value = entry.get(field)
            if isinstance(value, str) and value.strip() and value != DATA_MISSING:
                timestamp = value
                break
    line = match.get("line", 0)
    return timestamp, line if isinstance(line, int) else 0


def latest_matches_by_task(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(matches):
        entry = match.get("entry", {})
        task_id = entry.get("task_id") if isinstance(entry, dict) else None
        key = str(task_id) if task_id else f"__match_{index}"
        current = latest.get(key)
        if current is None or _match_order_key(match) >= _match_order_key(current):
            latest[key] = match
    return list(latest.values())


def latest_entries_by_task(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = [{"line": index, "entry": entry} for index, entry in enumerate(entries, start=1)]
    return [match["entry"] for match in latest_matches_by_task(matches)]


def classify_matches(matches: list[dict[str, Any]], data_missing: list[str]) -> str:
    if data_missing:
        return "DATA_MISSING_FALLBACK_REQUIRED"
    if not matches:
        return "UNKNOWN_ASK"

    latest_matches = latest_matches_by_task(matches)
    statuses = {str(match["entry"].get("status")) for match in latest_matches}
    owner_boundary = any(match["entry"].get("owner_boundary") is True for match in latest_matches)
    if owner_boundary or statuses & {"owner_boundary", "waiting_on_user"}:
        return "OWNER_BOUNDARY"
    if statuses & {"claimed", "implementation_started"}:
        return "ACTIVE_CONTINUE"
    if "pr_opened" in statuses:
        return "OPEN_PR_WAIT"
    if statuses & {"merged", "done"}:
        return "MERGED_USE_CANONICAL"
    if "superseded" in statuses:
        return "SUPERSEDED_IGNORE"
    if statuses & {"blocked", "waiting_on_timer", "parked"}:
        return "STALE_PRESERVE"
    return "UNKNOWN_ASK"


def group_by_status(entries: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped = {status: [] for status in SUMMARY_ORDER}
    for entry in latest_entries_by_task(entries):
        grouped.setdefault(str(entry.get("status")), []).append(entry)
    return grouped


def render_markdown_summary(entries: list[dict[str, Any]], sources: list[dict[str, Any]]) -> str:
    grouped = group_by_status(entries)
    lines = [
        "# Agent Task Ledger Summary",
        "",
        "Generated from ledger entries. Refresh from the live ledger before relying on this snapshot.",
        "",
        "## Sources Checked",
        "",
    ]
    for source in sources:
        state = "present" if source.get("exists") else "DATA_MISSING"
        lines.append(f"- {source['kind']}: `{source['path']}` ({state}, entries={source.get('entry_count', 0)})")
    lines.append("")

    for status in SUMMARY_ORDER:
        lines.append(f"## {status}")
        lines.append("")
        status_entries = grouped.get(status, [])
        if not status_entries:
            lines.append("- None")
            lines.append("")
            continue
        for entry in status_entries:
            task_id = entry.get("task_id", DATA_MISSING)
            branch = entry.get("branch", DATA_MISSING)
            next_action = entry.get("next_action", DATA_MISSING)
            summary = entry.get("summary", "")
            lines.append(f"- `{task_id}` on `{branch}`: {summary} Next: {next_action}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_resolve_path(args: argparse.Namespace) -> int:
    print(resolve_live_ledger_path(args.repo_root))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    entries: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    issues: list[str] = []
    data_missing: list[str] = []

    if args.entry_file:
        try:
            file_entries = load_entries(args.entry_file)
        except LedgerError as exc:
            issues.append(str(exc))
            file_entries = []
        entries.extend(file_entries)
        sources.append(_source_payload("entry_file", args.entry_file, args.entry_file.exists(), len(file_entries)))
        if not args.entry_file.exists():
            issues.append(f"entry_file: missing: {args.entry_file}")
    else:
        for kind, path, _required in _default_sources(args.repo_root):
            try:
                loaded, source, source_issues = _load_source(kind, path, required=False)
            except LedgerError as exc:
                loaded = []
                source = _source_payload(kind, path, path.exists())
                source_issues = [str(exc)]
            entries.extend(loaded)
            sources.append(source)
            issues.extend(source_issues)
            if not source["exists"]:
                data_missing.append(kind)

    issues.extend(validate_entries(entries, source="ledger"))
    payload = {
        "ok": not issues,
        "entry_count": len(entries),
        "sources_checked": sources,
        "data_missing": data_missing,
        "issues": issues,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not issues else 1


def cmd_append(args: argparse.Namespace) -> int:
    try:
        entry = _read_entry_arg(args)
        entry = _coerce_updated_at(entry)
        if args.fill_identity:
            entry = fill_identity(entry)
        issues = validate_entry(entry)
        if issues:
            raise LedgerError("; ".join(issues))
        path = args.ledger_path or resolve_live_ledger_path(args.repo_root)
        append_entry(path, entry)
    except LedgerError as exc:
        print(json.dumps({"ok": False, "issues": [str(exc)]}, indent=2, sort_keys=True))
        return 1

    print(json.dumps({"ok": True, "path": str(path), "entry": entry}, indent=2, sort_keys=True))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    entries: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    issues: list[str] = []
    data_missing: list[str] = []
    matches: list[dict[str, Any]] = []

    for kind, path, required in _selected_sources(args):
        loaded, source, source_issues = _load_source(kind, path, required=required)
        sources.append(source)
        issues.extend(source_issues)
        if not source["exists"]:
            data_missing.append(kind)
            continue
        entries.extend(loaded)
        for line_no, entry in enumerate(loaded, start=1):
            if entry_matches(entry, args):
                matches.append({"source": kind, "path": str(path), "line": line_no, "entry": entry})

    validation_issues = validate_entries(entries, source="ledger")
    issues.extend(validation_issues)
    payload = {
        "ok": not issues,
        "matches": matches,
        "sources_checked": sources,
        "data_missing": data_missing,
        "issues": issues,
        "duplicate_work_classification": classify_matches(matches, data_missing),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not issues else 1


def cmd_summarize(args: argparse.Namespace) -> int:
    entries, sources, issues = load_selected_entries(args)
    validation_issues = validate_entries(entries, source="ledger")
    issues.extend(validation_issues)
    if args.format == "json":
        payload = {
            "ok": not issues,
            "sources_checked": sources,
            "issues": issues,
            "groups": group_by_status(entries),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if issues:
            print("<!-- issues: " + json.dumps(issues, sort_keys=True) + " -->")
        print(render_markdown_summary(entries, sources), end="")
    return 0 if not issues else 1


def cmd_export_summary(args: argparse.Namespace) -> int:
    root = _repo_root(args.repo_root)
    live_path = args.live_ledger_path or resolve_live_ledger_path(root)
    loaded, source, source_issues = _load_source("live", live_path, required=True)
    issues = [*source_issues, *validate_entries(loaded, source="live")]
    if issues:
        print(
            json.dumps(
                {"ok": False, "source": source, "issues": issues, "write": False},
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    sources = [source]
    md_text = render_markdown_summary(loaded, sources)
    jsonl_text = "".join(_json_line(entry) for entry in loaded)
    md_path = root / COMMITTED_LEDGER_MD
    jsonl_path = root / COMMITTED_LEDGER_JSONL

    if args.write:
        try:
            write_committed_snapshot(md_path, md_text, jsonl_path, jsonl_text)
        except LedgerError as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "write": True,
                        "source": source,
                        "targets": {"markdown": str(md_path), "jsonl": str(jsonl_path)},
                        "issues": [str(exc)],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1

    payload = {
        "ok": True,
        "write": bool(args.write),
        "source": source,
        "targets": {"markdown": str(md_path), "jsonl": str(jsonl_path)},
    }
    if not args.write:
        payload["markdown"] = md_text
        payload["jsonl"] = jsonl_text
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    resolve_path = sub.add_parser("resolve-path", help="print resolved live ledger path")
    resolve_path.set_defaults(func=cmd_resolve_path)

    validate = sub.add_parser("validate", help="validate ledger entries")
    validate.add_argument("--entry-file", type=Path)
    validate.set_defaults(func=cmd_validate)

    append = sub.add_parser("append", help="append one validated JSONL entry")
    append_source = append.add_mutually_exclusive_group(required=True)
    append_source.add_argument("--entry-json")
    append_source.add_argument("--entry-file", type=Path)
    append.add_argument("--ledger-path", type=Path)
    append.add_argument("--fill-identity", action="store_true")
    append.set_defaults(func=cmd_append)

    search = sub.add_parser("search", help="search live and committed ledgers")
    search.add_argument("--ledger-path", type=Path, action="append")
    search.add_argument("--task-id")
    search.add_argument("--parent-task-id")
    search.add_argument("--session-id")
    search.add_argument("--thread-id")
    search.add_argument("--issue")
    search.add_argument("--pr")
    search.add_argument("--branch")
    search.add_argument("--worktree")
    search.add_argument("--path")
    search.add_argument("--text")
    search.set_defaults(func=cmd_search)

    summarize = sub.add_parser("summarize", help="summarize ledger entries by status")
    summarize.add_argument("--ledger-path", type=Path, action="append")
    summarize.add_argument("--format", choices=("markdown", "json"), default="markdown")
    summarize.set_defaults(func=cmd_summarize)

    export_summary = sub.add_parser("export-summary", help="export live ledger into committed summary files")
    export_summary.add_argument("--live-ledger-path", type=Path)
    export_summary.add_argument("--write", action="store_true")
    export_summary.set_defaults(func=cmd_export_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
