#!/usr/bin/env python3
"""Candidate-state helper for Tenn automation backlog findings."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = 1
DEFAULT_STATE_PATH = Path.home() / ".codex" / "automations" / "tenn" / "state" / "candidates.jsonl"
UTC = timezone.utc

SUPPRESSION_TTL_DAYS = {
    "rejected": 90,
    "deferred": 30,
    "defer": 30,
    "data_missing": 14,
    "needs_spec": 14,
    "failed_validation": 7,
}
INDEFINITE_SUPPRESSION_STATUSES = {"duplicate"}
TERMINAL_STATUSES = {"reviewed_accepted", "superseded"}


def normalize_status(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "data_missing"
    return value.strip().lower().replace("-", "_")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def format_time(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_parts(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if value not in {None, ""}}


def fingerprint_for(
    *,
    job: str,
    lane: str,
    evidence_path: str,
    root_cause: str,
    related_issue: str | None = None,
    related_pr: str | None = None,
    source_commit: str | None = None,
    evidence_hash: str | None = None,
) -> str:
    payload = _clean_parts(
        {
            "schema": "tenn_candidate_fingerprint_v1",
            "job": job.strip().lower(),
            "lane": lane.strip().lower(),
            "evidence_path": evidence_path.strip(),
            "root_cause": root_cause.strip().lower(),
            "related_issue": related_issue,
            "related_pr": related_pr,
            "source_commit": source_commit,
            "evidence_hash": evidence_hash,
        }
    )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "cand_v1_" + hashlib.sha256(encoded).hexdigest()[:24]


def default_suppress_until(status: str, now: datetime, ttl_days: int | None = None) -> str | None:
    normalized = normalize_status(status)
    if normalized in INDEFINITE_SUPPRESSION_STATUSES:
        return None
    days = ttl_days if ttl_days is not None else SUPPRESSION_TTL_DAYS.get(normalized)
    if days is None:
        return None
    return format_time(now + timedelta(days=days))


def build_record(
    *,
    job: str,
    lane: str,
    evidence_path: str,
    root_cause: str,
    status: str,
    title: str,
    detail: str = "",
    risk: str = "unknown",
    owner_action: str = "review this",
    recommended_command: str = "",
    related_issue: str | None = None,
    related_pr: str | None = None,
    source_commit: str | None = None,
    evidence_hash: str | None = None,
    linked_state_hash: str | None = None,
    url: str | None = None,
    now: datetime | None = None,
    ttl_days: int | None = None,
) -> dict[str, object]:
    timestamp = now or utc_now()
    normalized_status = normalize_status(status)
    fingerprint = fingerprint_for(
        job=job,
        lane=lane,
        evidence_path=evidence_path,
        root_cause=root_cause,
        related_issue=related_issue,
        related_pr=related_pr,
        source_commit=source_commit,
        evidence_hash=evidence_hash,
    )
    return _clean_parts(
        {
            "schema_version": SCHEMA_VERSION,
            "fingerprint": fingerprint,
            "status": normalized_status,
            "job": job,
            "lane": lane,
            "evidence_path": evidence_path,
            "root_cause": root_cause,
            "title": title,
            "detail": detail,
            "risk": risk,
            "owner_action": owner_action,
            "recommended_command": recommended_command,
            "related_issue": related_issue,
            "related_pr": related_pr,
            "source_commit": source_commit,
            "evidence_hash": evidence_hash,
            "linked_state_hash": linked_state_hash,
            "url": url,
            "created_at": format_time(timestamp),
            "updated_at": format_time(timestamp),
            "suppress_until": default_suppress_until(normalized_status, timestamp, ttl_days),
        }
    )


def load_records(path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    records: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []
    if not path.exists():
        return records, issues

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return records, [{"line": None, "issue": f"read_error: {exc}"}]

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append({"line": line_number, "issue": f"invalid_json: {exc}"})
            continue
        if not isinstance(payload, dict):
            issues.append({"line": line_number, "issue": "record_must_be_object"})
            continue
        record = dict(payload)
        record["_line_number"] = line_number
        _fill_legacy_fields(record, line_number)
        records.append(record)
    return records, issues


def _fill_legacy_fields(record: dict[str, object], line_number: int) -> None:
    record["status"] = normalize_status(
        record.get("status") or record.get("review_status") or record.get("outcome") or record.get("state")
    )
    if not isinstance(record.get("title"), str):
        record["title"] = str(record.get("summary") or record.get("fingerprint") or f"Candidate line {line_number}")
    if not isinstance(record.get("detail"), str):
        record["detail"] = str(record.get("reason") or record.get("status") or "")
    if not isinstance(record.get("evidence_path"), str):
        record["evidence_path"] = str(record.get("evidence") or f"candidates.jsonl:{line_number}")
    if not isinstance(record.get("job"), str):
        record["job"] = str(record.get("source") or "unknown")
    if not isinstance(record.get("lane"), str):
        record["lane"] = str(record.get("lane") or "unknown")
    if not isinstance(record.get("root_cause"), str):
        record["root_cause"] = str(record.get("root_cause") or record.get("detail") or record.get("title"))
    if not isinstance(record.get("fingerprint"), str):
        record["fingerprint"] = fingerprint_for(
            job=str(record["job"]),
            lane=str(record["lane"]),
            evidence_path=str(record["evidence_path"]),
            root_cause=str(record["root_cause"]),
            related_issue=_optional_string(record.get("related_issue")),
            related_pr=_optional_string(record.get("related_pr")),
            source_commit=_optional_string(record.get("source_commit")),
            evidence_hash=_optional_string(record.get("evidence_hash")),
        )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def latest_by_fingerprint(records: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    latest: dict[str, dict[str, object]] = {}
    for record in records:
        fingerprint = str(record.get("fingerprint"))
        previous = latest.get(fingerprint)
        if previous is None or _record_sort_key(record) >= _record_sort_key(previous):
            latest[fingerprint] = record
    return sorted(latest.values(), key=_record_sort_key)


def _record_sort_key(record: dict[str, object]) -> tuple[datetime, int]:
    parsed = parse_time(record.get("updated_at")) or parse_time(record.get("created_at")) or datetime.min.replace(tzinfo=UTC)
    line_number = record.get("_line_number")
    return parsed, line_number if isinstance(line_number, int) else 0


def should_resurface(
    record: dict[str, object],
    *,
    now: datetime | None = None,
    current_evidence_hash: str | None = None,
    current_linked_state_hash: str | None = None,
) -> tuple[bool, str | None]:
    if current_evidence_hash and record.get("evidence_hash") != current_evidence_hash:
        return True, "evidence_hash_changed"
    if current_linked_state_hash and record.get("linked_state_hash") != current_linked_state_hash:
        return True, "linked_state_changed"

    status = normalize_status(record.get("status"))
    if status not in SUPPRESSION_TTL_DAYS and status not in INDEFINITE_SUPPRESSION_STATUSES:
        return True, "not_suppressed"
    if status in INDEFINITE_SUPPRESSION_STATUSES:
        return False, None

    suppress_until = parse_time(record.get("suppress_until"))
    if suppress_until is None:
        return True, "missing_suppress_until"
    if (now or utc_now()) >= suppress_until:
        return True, "ttl_expired"
    return False, None


def candidate_items_for_brief(path: Path, *, now: datetime | None = None) -> tuple[list[dict[str, object]], dict[str, object]]:
    records, issues = load_records(path)
    latest = latest_by_fingerprint(records)
    items: list[dict[str, object]] = []
    suppressed = 0
    terminal = 0
    for record in latest:
        status = normalize_status(record.get("status"))
        if status in TERMINAL_STATUSES:
            terminal += 1
            continue
        visible, reason = should_resurface(record, now=now)
        if not visible:
            suppressed += 1
            continue
        detail = str(record.get("detail") or status)
        if reason and reason != "not_suppressed":
            detail = f"{detail} Resurface reason: {reason}."
        items.append(
            {
                "status": status,
                "title": str(record.get("title") or record.get("fingerprint")),
                "detail": detail,
                "owner_action": str(record.get("owner_action") or "review this"),
                "risk": str(record.get("risk") or "unknown"),
                "evidence": str(record.get("evidence_path") or path),
                "recommended_command": str(record.get("recommended_command") or f"sed -n '{record.get('_line_number', 1)}p' {path}"),
                "url": record.get("url") if isinstance(record.get("url"), str) else None,
            }
        )
    summary = {
        "records": len(records),
        "latest": len(latest),
        "visible": len(items),
        "suppressed": suppressed,
        "terminal": terminal,
        "issues": issues,
    }
    return items, summary


def append_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def summarize(path: Path, *, now: datetime | None = None) -> dict[str, object]:
    records, issues = load_records(path)
    latest = latest_by_fingerprint(records)
    status_counts = Counter(normalize_status(record.get("status")) for record in latest)
    _items, brief_summary = candidate_items_for_brief(path, now=now)
    return {
        "path": str(path),
        "records": len(records),
        "latest": len(latest),
        "status_counts": dict(sorted(status_counts.items())),
        "brief": brief_summary,
        "issues": issues,
    }


def duplicate_record_from_dedupe(
    candidate: dict[str, object],
    dedupe_result: dict[str, object],
    *,
    now: datetime | None = None,
) -> dict[str, object] | None:
    status = normalize_status(dedupe_result.get("status"))
    if status not in {"duplicate_issue", "duplicate_pr"}:
        return None
    best_match = dedupe_result.get("best_match")
    if not isinstance(best_match, dict):
        return None

    kind = best_match.get("kind")
    number = best_match.get("number")
    number_text = _dedupe_number_text(number)
    if kind == "issue":
        related_issue = number_text
        related_pr = _optional_string(candidate.get("related_pr"))
    elif kind == "pr":
        related_issue = _optional_string(candidate.get("related_issue"))
        related_pr = number_text
    else:
        return None

    timestamp = now or utc_now()
    title = str(candidate.get("title") or best_match.get("title") or "Duplicate automation candidate")
    detail = (
        f"Read-only GitHub dedupe classified this candidate as {status}; "
        f"best match: {kind} #{number_text or 'DATA_MISSING'} {best_match.get('title') or ''}."
    )
    record = build_record(
        job=str(candidate.get("job") or "automation_github_dedupe"),
        lane=str(candidate.get("lane") or "reporting"),
        evidence_path=str(candidate.get("evidence_path") or best_match.get("url") or "gh read-only dedupe"),
        root_cause=str(candidate.get("root_cause") or title),
        status="duplicate",
        title=title,
        detail=detail,
        risk=str(candidate.get("risk") or "low"),
        owner_action="review existing GitHub item",
        recommended_command=_dedupe_recommended_command(kind, number_text),
        related_issue=related_issue,
        related_pr=related_pr,
        source_commit=_optional_string(candidate.get("source_commit")),
        evidence_hash=_optional_string(candidate.get("evidence_hash")),
        linked_state_hash=_optional_string(candidate.get("linked_state_hash")),
        url=_optional_string(best_match.get("url")) or _optional_string(candidate.get("url")),
        now=timestamp,
    )
    original_fingerprint = _optional_string(candidate.get("fingerprint"))
    if original_fingerprint:
        record["fingerprint"] = original_fingerprint
    return record


def _dedupe_recommended_command(kind: object, number_text: str | None) -> str:
    if kind == "issue" and number_text:
        return f"gh issue view {number_text} --repo 0rl4nd0l/tenn"
    if kind == "pr" and number_text:
        return f"gh pr view {number_text} --repo 0rl4nd0l/tenn"
    return "python3 scripts/system_brief.py --json"


def _dedupe_number_text(value: object) -> str | None:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip().lstrip("#").isdigit():
        return value.strip().lstrip("#")
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    fingerprint = sub.add_parser("fingerprint", help="print a deterministic candidate fingerprint")
    _add_identity_args(fingerprint)

    upsert = sub.add_parser("upsert", help="append one candidate record")
    _add_identity_args(upsert)
    upsert.add_argument("--status", required=True)
    upsert.add_argument("--title", required=True)
    upsert.add_argument("--detail", default="")
    upsert.add_argument("--risk", default="unknown")
    upsert.add_argument("--owner-action", default="review this")
    upsert.add_argument("--recommended-command", default="")
    upsert.add_argument("--url")
    upsert.add_argument("--ttl-days", type=int)

    list_cmd = sub.add_parser("list", help="list visible brief candidates")
    list_cmd.add_argument("--include-summary", action="store_true")

    sub.add_parser("summarize", help="summarize candidate state")
    return parser


def _add_identity_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--job", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--root-cause", required=True)
    parser.add_argument("--related-issue")
    parser.add_argument("--related-pr")
    parser.add_argument("--source-commit")
    parser.add_argument("--evidence-hash")
    parser.add_argument("--linked-state-hash")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state_path = args.state_path.expanduser()
    if args.command == "fingerprint":
        print(
            fingerprint_for(
                job=args.job,
                lane=args.lane,
                evidence_path=args.evidence_path,
                root_cause=args.root_cause,
                related_issue=args.related_issue,
                related_pr=args.related_pr,
                source_commit=args.source_commit,
                evidence_hash=args.evidence_hash,
            )
        )
        return 0
    if args.command == "upsert":
        record = build_record(
            job=args.job,
            lane=args.lane,
            evidence_path=args.evidence_path,
            root_cause=args.root_cause,
            status=args.status,
            title=args.title,
            detail=args.detail,
            risk=args.risk,
            owner_action=args.owner_action,
            recommended_command=args.recommended_command,
            related_issue=args.related_issue,
            related_pr=args.related_pr,
            source_commit=args.source_commit,
            evidence_hash=args.evidence_hash,
            linked_state_hash=args.linked_state_hash,
            url=args.url,
            ttl_days=args.ttl_days,
        )
        append_record(state_path, record)
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0
    if args.command == "list":
        items, summary = candidate_items_for_brief(state_path)
        payload: dict[str, object] = {"items": items}
        if args.include_summary:
            payload["summary"] = summary
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "summarize":
        print(json.dumps(summarize(state_path), indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
