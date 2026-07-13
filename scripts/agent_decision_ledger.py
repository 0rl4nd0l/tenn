#!/usr/bin/env python3
"""Manage the append-only Tenn Semantic Anti-Loop decision ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from scripts import agent_job_registry
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import agent_job_registry  # type: ignore


LIVE_LEDGER_NAME = "decision-ledger.jsonl"
DATA_MISSING = "DATA_MISSING"

PROGRAM_TRACKS = {"offline_development", "prospective_readiness"}
DECISIONS = {"PASS", "FAIL", DATA_MISSING, "CONFLICT", "PARKED"}
OUTCOME_STATUSES = {
    "ADVANCED",
    "REUSED_COMPLETE",
    "ACTIVE_DUPLICATE",
    "WAITING_ON_AUTHORIZATION",
    DATA_MISSING,
    "EVIDENCE_CONFLICT",
    "BLOCKED_NO_NEW_INPUT",
    "LOOP_GUARD_STOP",
}
REQUIRED_FIELDS = (
    "decision_id",
    "scope_fingerprint",
    "task_id",
    "run_id",
    "project_id",
    "claim_id",
    "hypothesis_id",
    "program_track",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
    "phase_before",
    "phase_after",
    "decision",
    "outcome_status",
    "decision_delta",
    "evidence_refs",
    "blocks",
    "does_not_block",
    "validated_at",
    "invalidation_conditions",
    "reopen_conditions",
)
STRING_FIELDS = (
    "decision_id",
    "task_id",
    "run_id",
    "project_id",
    "claim_id",
    "hypothesis_id",
    "source_class",
    "dataset_version",
    "target_transition",
    "phase_before",
    "phase_after",
)
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$", re.IGNORECASE)
NO_DELTA_SENTINELS = {"", "NONE", "NO_CHANGE", "NO_DELTA", "UNCHANGED"}
DECISION_OUTCOME_COMPATIBILITY = {
    "PASS": {"ADVANCED", "REUSED_COMPLETE"},
    "FAIL": {"ADVANCED", "REUSED_COMPLETE"},
    DATA_MISSING: {DATA_MISSING, "BLOCKED_NO_NEW_INPUT", "LOOP_GUARD_STOP"},
    "CONFLICT": {"EVIDENCE_CONFLICT", "BLOCKED_NO_NEW_INPUT", "LOOP_GUARD_STOP"},
    "PARKED": {
        "ADVANCED",
        "REUSED_COMPLETE",
        "ACTIVE_DUPLICATE",
        "WAITING_ON_AUTHORIZATION",
        "BLOCKED_NO_NEW_INPUT",
        "LOOP_GUARD_STOP",
    },
}
SCOPE_FINGERPRINT_FIELDS = (
    "project_id",
    "claim_id",
    "hypothesis_id",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
)


class DecisionLedgerError(ValueError):
    """Raised for user-facing decision-ledger errors."""


def resolve_live_ledger_path(repo_root: Path | None = None) -> Path:
    """Resolve the decision ledger beside the task ledger in the shared registry."""

    location = agent_job_registry.resolve_registry_location(repo_root)
    return (Path(location.root) / LIVE_LEDGER_NAME).resolve(strict=False)


def _json_line(value: Mapping[str, Any]) -> str:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        )
    except (TypeError, ValueError) as exc:
        raise DecisionLedgerError(f"entry is not JSON serializable: {exc}") from exc


def _load_flexible_entries_from_text(text: str, *, source: str) -> list[dict[str, Any]]:
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
                raise DecisionLedgerError(
                    f"{source}:{line_no}: invalid JSON: column {exc.colno}: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise DecisionLedgerError(
                    f"{source}:{line_no}: entry must be a JSON object"
                )
            entries.append(value)
        return entries

    if isinstance(loaded, dict):
        return [loaded]
    if isinstance(loaded, list):
        entries = []
        for index, value in enumerate(loaded):
            if not isinstance(value, dict):
                raise DecisionLedgerError(
                    f"{source}[{index}]: entry must be a JSON object"
                )
            entries.append(value)
        return entries
    raise DecisionLedgerError(
        f"{source}: expected a JSON object, array, or JSONL objects"
    )


def _load_jsonl_entries_from_text(text: str, *, source: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DecisionLedgerError(
                f"{source}:{line_no}: invalid JSONL object: column {exc.colno}: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise DecisionLedgerError(
                f"{source}:{line_no}: live ledger line must be one JSON object"
            )
        entries.append(value)
    return entries


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DecisionLedgerError(
            f"{path}: unable to read file: {exc.strerror or exc}"
        ) from exc
    except UnicodeDecodeError as exc:
        raise DecisionLedgerError(f"{path}: file must be UTF-8 text") from exc


def load_entries(path: Path) -> list[dict[str, Any]]:
    """Load a live/custom ledger as strict one-object-per-line JSONL."""

    return _load_jsonl_entries_from_text(_read_text(path), source=str(path))


def load_entry_file(path: Path) -> list[dict[str, Any]]:
    """Load a flexible JSON entry file; callers must enforce a single entry."""

    return _load_flexible_entries_from_text(_read_text(path), source=str(path))


def has_decision_delta(value: Any) -> bool:
    """Return whether a delta represents semantic change instead of a no-delta marker."""

    if isinstance(value, str):
        normalized = re.sub(r"[\s-]+", "_", value.strip().upper())
        return normalized not in NO_DELTA_SENTINELS
    if isinstance(value, (list, dict)):
        return bool(value)
    return False


def normalize_evidence_hash(value: Any) -> str:
    """Return the same canonical evidence-hash spelling used by task contracts."""

    if not isinstance(value, str):
        raise ValueError("evidence_hash must be a string")
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.removeprefix("sha256:")
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise ValueError("evidence_hash must be a SHA-256 hex digest")
    return f"sha256:{normalized}"


def compute_scope_fingerprint(entry: Mapping[str, Any]) -> str:
    """Compute the V2 fingerprint using the task-contract field order."""

    values: list[str] = []
    for field in SCOPE_FINGERPRINT_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field} must be a non-empty string before fingerprinting"
            )
        normalized = value.strip()
        if field == "evidence_hash":
            normalized = normalize_evidence_hash(normalized)
        values.append(normalized)
    canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_non_empty_string(
    entry: Mapping[str, Any], field: str, issues: list[str]
) -> None:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{field}: must be a non-empty string")


def _require_string_list(
    entry: Mapping[str, Any],
    field: str,
    issues: list[str],
    *,
    require_item: bool = False,
) -> None:
    value = entry.get(field)
    if not isinstance(value, list):
        issues.append(f"{field}: must be a list")
        return
    if require_item and not value:
        issues.append(f"{field}: must contain at least one reference")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"{field}[{index}]: must be a non-empty string")


def _require_conditions(
    entry: Mapping[str, Any], field: str, issues: list[str]
) -> None:
    value = entry.get(field)
    if isinstance(value, str):
        if not value.strip():
            issues.append(f"{field}: must be a non-empty string or list of conditions")
        return
    if not isinstance(value, list) or not value:
        issues.append(f"{field}: must be a non-empty string or list of conditions")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"{field}[{index}]: must be a non-empty string")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_entry(entry: Mapping[str, Any], *, source: str = "<entry>") -> list[str]:
    """Validate one decision entry without reading or mutating a ledger."""

    issues: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            issues.append(f"{field}: required field is missing")

    for field in STRING_FIELDS:
        if field in entry:
            _require_non_empty_string(entry, field, issues)

    fingerprint = entry.get("scope_fingerprint")
    if "scope_fingerprint" in entry and (
        not isinstance(fingerprint, str)
        or HEX_64_RE.fullmatch(fingerprint.strip()) is None
    ):
        issues.append(
            "scope_fingerprint: must be a lowercase 64-character SHA-256 hex digest"
        )
    elif isinstance(fingerprint, str):
        try:
            expected_fingerprint = compute_scope_fingerprint(entry)
        except ValueError:
            expected_fingerprint = None
        if (
            expected_fingerprint is not None
            and fingerprint.strip() != expected_fingerprint
        ):
            issues.append(
                "scope_fingerprint: does not match the V2 semantic scope fields; "
                f"expected {expected_fingerprint}"
            )

    evidence_hash = entry.get("evidence_hash")
    if "evidence_hash" in entry and (
        not isinstance(evidence_hash, str)
        or EVIDENCE_HASH_RE.fullmatch(evidence_hash.strip()) is None
    ):
        issues.append(
            "evidence_hash: must be a SHA-256 hex digest, optionally prefixed with sha256:"
        )

    program_track = entry.get("program_track")
    if "program_track" in entry and program_track not in PROGRAM_TRACKS:
        issues.append(
            f"program_track: must be one of {', '.join(sorted(PROGRAM_TRACKS))}"
        )

    decision = entry.get("decision")
    if "decision" in entry and decision not in DECISIONS:
        issues.append(f"decision: must be one of {', '.join(sorted(DECISIONS))}")

    outcome_status = entry.get("outcome_status")
    if "outcome_status" in entry and outcome_status not in OUTCOME_STATUSES:
        issues.append(
            f"outcome_status: must be one of {', '.join(sorted(OUTCOME_STATUSES))}"
        )
    if decision in DECISION_OUTCOME_COMPATIBILITY and outcome_status in OUTCOME_STATUSES:
        compatible = DECISION_OUTCOME_COMPATIBILITY[str(decision)]
        if outcome_status not in compatible:
            issues.append(
                "outcome_status: is incompatible with decision "
                f"{decision}; expected one of {', '.join(sorted(compatible))}"
            )

    if "decision_delta" in entry and not isinstance(
        entry.get("decision_delta"), (str, list, dict)
    ):
        issues.append("decision_delta: must be a string, list, or object")
    if outcome_status == "ADVANCED" and not has_decision_delta(
        entry.get("decision_delta")
    ):
        issues.append("decision_delta: ADVANCED requires a semantic decision delta")

    if "evidence_refs" in entry:
        _require_string_list(entry, "evidence_refs", issues, require_item=True)
    for field in ("blocks", "does_not_block"):
        if field in entry:
            _require_string_list(entry, field, issues)

    blocks = entry.get("blocks")
    does_not_block = entry.get("does_not_block")
    if isinstance(blocks, list) and isinstance(does_not_block, list):
        overlap = sorted(
            {item.strip() for item in blocks if isinstance(item, str)}
            & {item.strip() for item in does_not_block if isinstance(item, str)}
        )
        if overlap:
            issues.append("blocks and does_not_block overlap: " + ", ".join(overlap))

    if "validated_at" in entry and not _valid_timestamp(entry.get("validated_at")):
        issues.append(
            "validated_at: must be an ISO-8601 timestamp with an explicit timezone"
        )

    for field in ("invalidation_conditions", "reopen_conditions"):
        if field in entry:
            _require_conditions(entry, field, issues)

    return [f"{source}: {issue}" for issue in issues]


def validate_entries(
    entries: Iterable[Mapping[str, Any]], *, source: str = "ledger"
) -> list[str]:
    """Validate all entries and reject duplicate decision identifiers."""

    materialized = list(entries)
    issues: list[str] = []
    seen_ids: dict[str, int] = {}
    for line_no, entry in enumerate(materialized, start=1):
        issues.extend(validate_entry(entry, source=f"{source}:{line_no}"))
        decision_id = entry.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id.strip():
            continue
        if decision_id in seen_ids:
            issues.append(
                f"{source}:{line_no}: decision_id: duplicate {decision_id!r}; "
                f"first appears at line {seen_ids[decision_id]}"
            )
        else:
            seen_ids[decision_id] = line_no
    return issues


def _append_bytes(path: Path, entry: Mapping[str, Any]) -> None:
    payload = _json_line(entry).encode("utf-8")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    except OSError as exc:
        raise DecisionLedgerError(
            f"{path}: unable to open ledger for append: {exc.strerror or exc}"
        ) from exc
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise DecisionLedgerError(
                    f"{path}: unable to append entry: wrote zero bytes"
                )
            remaining = remaining[written:]
        os.fsync(fd)
    except OSError as exc:
        raise DecisionLedgerError(
            f"{path}: unable to append entry: {exc.strerror or exc}"
        ) from exc
    finally:
        os.close(fd)


def append_entry(path: Path, entry: Mapping[str, Any]) -> None:
    """Append one validated, uniquely identified entry under the registry lock."""

    new_issues = validate_entry(entry)
    if new_issues:
        raise DecisionLedgerError("; ".join(new_issues))

    try:
        with agent_job_registry.RegistryLock(path.parent):
            existing = load_entries(path) if path.exists() else []
            existing_issues = validate_entries(existing, source=str(path))
            if existing_issues:
                raise DecisionLedgerError(
                    "existing ledger is invalid: " + "; ".join(existing_issues)
                )
            decision_id = entry.get("decision_id")
            if any(
                existing_entry.get("decision_id") == decision_id
                for existing_entry in existing
            ):
                raise DecisionLedgerError(f"decision_id: duplicate {decision_id!r}")
            _append_bytes(path, entry)
    except DecisionLedgerError:
        raise
    except (OSError, TimeoutError) as exc:
        raise DecisionLedgerError(
            f"{path}: unable to lock ledger for append: {exc}"
        ) from exc


def initialize_ledger(path: Path, *, authorized: bool) -> dict[str, Any]:
    """Create an absent empty ledger under the registry lock without truncation."""

    if not authorized:
        raise DecisionLedgerError(
            "initialization requires explicit --authorize-create-empty-ledger authorization"
        )

    try:
        with agent_job_registry.RegistryLock(path.parent):
            if path.exists():
                try:
                    entries = load_entries(path)
                except DecisionLedgerError as exc:
                    raise DecisionLedgerError(
                        f"existing ledger is invalid: {exc}"
                    ) from exc
                issues = validate_entries(entries, source=str(path))
                if issues:
                    raise DecisionLedgerError(
                        "existing ledger is invalid: " + "; ".join(issues)
                    )
                return {
                    "path": str(path),
                    "created": False,
                    "already_initialized": True,
                    "entry_count": len(entries),
                }

            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except OSError as exc:
                raise DecisionLedgerError(
                    f"{path}: unable to initialize ledger: {exc.strerror or exc}"
                ) from exc
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            return {
                "path": str(path),
                "created": True,
                "already_initialized": False,
                "entry_count": 0,
            }
    except DecisionLedgerError:
        raise
    except (OSError, TimeoutError) as exc:
        raise DecisionLedgerError(
            f"{path}: unable to lock ledger for initialization: {exc}"
        ) from exc


def _source_payload(
    path: Path, *, kind: str, exists: bool, entry_count: int = 0
) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": str(path),
        "exists": exists,
        "entry_count": entry_count,
    }


def _ledger_path(args: argparse.Namespace) -> tuple[str, Path]:
    if getattr(args, "ledger_path", None) is not None:
        return "custom", args.ledger_path.resolve(strict=False)
    return "live", resolve_live_ledger_path(args.repo_root)


def _load_ledger_source(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str], list[str]]:
    kind, path = _ledger_path(args)
    if not path.exists():
        source = _source_payload(path, kind=kind, exists=False)
        return (
            [],
            source,
            ["decision_ledger"],
            [f"{kind}: missing decision ledger: {path}"],
        )
    try:
        entries = load_entries(path)
    except DecisionLedgerError as exc:
        return [], _source_payload(path, kind=kind, exists=True), [], [str(exc)]
    return (
        entries,
        _source_payload(path, kind=kind, exists=True, entry_count=len(entries)),
        [],
        [],
    )


def _read_single_entry(args: argparse.Namespace) -> dict[str, Any]:
    if args.entry_json is not None:
        try:
            loaded = json.loads(args.entry_json)
        except json.JSONDecodeError as exc:
            raise DecisionLedgerError(
                f"--entry-json: invalid JSON: line {exc.lineno} column {exc.colno}: {exc.msg}"
            ) from exc
        if not isinstance(loaded, dict):
            raise DecisionLedgerError("--entry-json: entry must be a JSON object")
        return loaded

    entries = load_entry_file(args.entry_file)
    if len(entries) != 1:
        raise DecisionLedgerError(
            f"{args.entry_file}: append requires exactly one entry; found {len(entries)}"
        )
    return entries[0]


def _entry_matches(entry: Mapping[str, Any], args: argparse.Namespace) -> bool:
    exact_fields = (
        "decision_id",
        "scope_fingerprint",
        "task_id",
        "run_id",
        "project_id",
        "claim_id",
        "hypothesis_id",
        "program_track",
        "source_class",
        "dataset_version",
        "evidence_hash",
        "target_transition",
        "decision",
        "outcome_status",
    )
    for field in exact_fields:
        expected = getattr(args, field, None)
        if expected is not None and entry.get(field) != expected:
            return False
    if getattr(args, "no_delta_only", False) and has_decision_delta(
        entry.get("decision_delta")
    ):
        return False
    text = getattr(args, "text", None)
    if (
        text is not None
        and text.lower() not in json.dumps(entry, sort_keys=True).lower()
    ):
        return False
    return True


def _match_payload(
    entry: dict[str, Any], *, path: Path, kind: str, line_no: int
) -> dict[str, Any]:
    has_delta = has_decision_delta(entry.get("decision_delta"))
    return {
        "source": kind,
        "path": str(path),
        "line": line_no,
        "has_decision_delta": has_delta,
        "is_no_delta": not has_delta,
        "entry": entry,
    }


def _group_entries(
    entries: Iterable[dict[str, Any]], field: str, values: Iterable[str]
) -> dict[str, list[dict[str, Any]]]:
    groups = {value: [] for value in sorted(values)}
    for entry in entries:
        groups.setdefault(str(entry.get(field)), []).append(entry)
    return groups


def _summary_payload(entries: list[dict[str, Any]]) -> dict[str, Any]:
    decision_groups = _group_entries(entries, "decision", DECISIONS)
    outcome_groups = _group_entries(entries, "outcome_status", OUTCOME_STATUSES)
    return {
        "total_entries": len(entries),
        "no_delta_count": sum(
            not has_decision_delta(entry.get("decision_delta")) for entry in entries
        ),
        "by_decision": {name: len(group) for name, group in decision_groups.items()},
        "by_outcome_status": {
            name: len(group) for name, group in outcome_groups.items()
        },
        "groups": decision_groups,
        "outcome_groups": outcome_groups,
    }


def _render_markdown_summary(
    entries: list[dict[str, Any]], source: Mapping[str, Any]
) -> str:
    summary = _summary_payload(entries)
    lines = [
        "# Agent Decision Ledger Summary",
        "",
        f"Source: `{source['path']}`",
        "",
        f"- Total entries: {summary['total_entries']}",
        f"- No-delta entries: {summary['no_delta_count']}",
        "",
    ]
    groups = summary["groups"]
    assert isinstance(groups, dict)
    for decision in sorted(DECISIONS):
        lines.extend([f"## {decision}", ""])
        decision_entries = groups.get(decision, [])
        if not decision_entries:
            lines.extend(["- None", ""])
            continue
        for entry in decision_entries:
            lines.append(
                f"- `{entry.get('decision_id', DATA_MISSING)}`: "
                f"`{entry.get('project_id', DATA_MISSING)}/{entry.get('claim_id', DATA_MISSING)}` "
                f"from `{entry.get('phase_before', DATA_MISSING)}` "
                f"to `{entry.get('phase_after', DATA_MISSING)}` "
                f"(`{entry.get('outcome_status', DATA_MISSING)}`)"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_resolve_path(args: argparse.Namespace) -> int:
    print(resolve_live_ledger_path(args.repo_root))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    entries: list[dict[str, Any]] = []
    issues: list[str] = []
    data_missing: list[str] = []
    sources: list[dict[str, Any]] = []

    if args.entry_file is not None:
        if not args.entry_file.exists():
            data_missing.append("entry_file")
        try:
            entries = load_entry_file(args.entry_file)
        except DecisionLedgerError as exc:
            issues.append(str(exc))
        if len(entries) != 1:
            issues.append(
                f"{args.entry_file}: entry-file validation requires exactly one entry; "
                f"found {len(entries)}"
            )
        sources.append(
            _source_payload(
                args.entry_file,
                kind="entry_file",
                exists=args.entry_file.exists(),
                entry_count=len(entries),
            )
        )
    else:
        entries, source, data_missing, source_issues = _load_ledger_source(args)
        sources.append(source)
        issues.extend(source_issues)

    issues.extend(validate_entries(entries))
    payload = {
        "ok": not issues and not data_missing,
        "entry_count": len(entries),
        "sources_checked": sources,
        "data_missing": data_missing,
        "issues": issues,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


def cmd_append(args: argparse.Namespace) -> int:
    try:
        entry = _read_single_entry(args)
        path = (
            args.ledger_path.resolve(strict=False)
            if args.ledger_path
            else resolve_live_ledger_path(args.repo_root)
        )
        append_entry(path, entry)
    except DecisionLedgerError as exc:
        print(
            json.dumps(
                {"ok": False, "data_missing": [], "issues": [str(exc)]},
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "data_missing": [],
                "issues": [],
                "path": str(path),
                "entry": entry,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_initialize(args: argparse.Namespace) -> int:
    kind, path = _ledger_path(args)
    try:
        result = initialize_ledger(
            path,
            authorized=args.authorize_create_empty_ledger,
        )
    except DecisionLedgerError as exc:
        print(
            json.dumps(
                {"ok": False, "data_missing": [], "issues": [str(exc)]},
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "data_missing": [],
                "issues": [],
                "source": kind,
                **result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    entries, source, data_missing, issues = _load_ledger_source(args)
    issues.extend(validate_entries(entries))
    path = Path(source["path"])
    matches = [
        _match_payload(entry, path=path, kind=str(source["kind"]), line_no=line_no)
        for line_no, entry in enumerate(entries, start=1)
        if _entry_matches(entry, args)
    ]
    payload = {
        "ok": not issues and not data_missing,
        "entry_count": len(entries),
        "matches": matches,
        "sources_checked": [source],
        "data_missing": data_missing,
        "issues": issues,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


def cmd_summarize(args: argparse.Namespace) -> int:
    entries, source, data_missing, issues = _load_ledger_source(args)
    issues.extend(validate_entries(entries))
    ok = not issues and not data_missing
    if args.format == "markdown":
        if issues or data_missing:
            print(
                "<!-- issues: "
                + json.dumps({"data_missing": data_missing, "issues": issues})
                + " -->"
            )
        print(_render_markdown_summary(entries, source), end="")
    else:
        payload = {
            "ok": ok,
            "sources_checked": [source],
            "data_missing": data_missing,
            "issues": issues,
            **_summary_payload(entries),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


def _add_repo_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=Path, default=argparse.SUPPRESS)


def _add_ledger_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ledger-path", type=Path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_path = subparsers.add_parser(
        "resolve-path", help="print the resolved live decision-ledger path"
    )
    _add_repo_root(resolve_path)
    resolve_path.set_defaults(func=cmd_resolve_path)

    validate = subparsers.add_parser(
        "validate", help="validate a decision ledger or entry file"
    )
    _add_repo_root(validate)
    _add_ledger_path(validate)
    validate.add_argument("--entry-file", type=Path)
    validate.set_defaults(func=cmd_validate)

    initialize = subparsers.add_parser(
        "initialize",
        help="explicitly create the absent live ledger as an empty append-only file",
    )
    _add_repo_root(initialize)
    _add_ledger_path(initialize)
    initialize.add_argument(
        "--authorize-create-empty-ledger",
        action="store_true",
        help="confirm authorization to create the absent empty ledger; existing data is never truncated",
    )
    initialize.set_defaults(func=cmd_initialize)

    append = subparsers.add_parser("append", help="append one validated decision entry")
    _add_repo_root(append)
    source = append.add_mutually_exclusive_group(required=True)
    source.add_argument("--entry-json")
    source.add_argument("--entry-file", type=Path)
    _add_ledger_path(append)
    append.set_defaults(func=cmd_append)

    search = subparsers.add_parser(
        "search", help="search the live or selected decision ledger"
    )
    _add_repo_root(search)
    _add_ledger_path(search)
    for field in (
        "decision-id",
        "scope-fingerprint",
        "task-id",
        "run-id",
        "project-id",
        "claim-id",
        "hypothesis-id",
        "program-track",
        "source-class",
        "dataset-version",
        "evidence-hash",
        "target-transition",
        "decision",
        "outcome-status",
    ):
        search.add_argument(f"--{field}")
    search.add_argument("--no-delta-only", action="store_true")
    search.add_argument("--text")
    search.set_defaults(func=cmd_search)

    summarize = subparsers.add_parser(
        "summarize", help="summarize decision and outcome states"
    )
    _add_repo_root(summarize)
    _add_ledger_path(summarize)
    summarize.add_argument("--format", choices=("json", "markdown"), default="json")
    summarize.set_defaults(func=cmd_summarize)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
