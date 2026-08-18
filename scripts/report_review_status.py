#!/usr/bin/env python3
"""Parse optional Tenn report-review status markers.

The marker is advisory evidence for report-review state only. It is not proof
of runtime functionality, GitHub state, PR readiness, financial truth approval,
or issue-closeout permission.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


MARKER_FILENAME = "REPORT_REVIEW_STATUS.json"
DATA_MISSING = "DATA_MISSING"
SCHEMA_VERSION = 1

ALLOWED_REVIEW_STATUSES = {
    "PENDING_REVIEW",
    "REVIEWED_ACCEPTED",
    "REVIEWED_REJECTED",
    "NEEDS_MORE_EVIDENCE",
    "SUPERSEDED",
    "PARKED",
    "PROMOTED_TO_TASK_CARD",
    "OWNER_DECISION_REQUIRED",
    DATA_MISSING,
    "FAILED_SCHEMA_VALIDATION",
}

ALLOWED_NEXT_ACTIONS = {
    "none",
    "promote_task_card",
    "ask_owner",
    "collect_more_evidence",
    "park",
    "supersede",
    DATA_MISSING,
}

REQUIRED_FIELDS = [
    "schema_version",
    "job_id",
    "review_status",
    "reviewed_at",
    "reviewed_by",
    "review_evidence",
    "source_report_paths",
    "summary",
    "next_action",
    "runtime_functionality_proven",
    "github_state_checked",
]

EVIDENCE_REQUIRED_STATUSES = {
    "REVIEWED_ACCEPTED",
    "PROMOTED_TO_TASK_CARD",
    "SUPERSEDED",
    "PARKED",
}

RUNTIME_PROOF_FIELD_LABELS = [
    "intended output",
    "live output location",
    "pre-run max timestamp or count",
    "post-run max timestamp or count",
    "rows/files inserted or updated after run start",
    "readiness/gate status",
    "exact command/query used",
    "remaining blocker",
]
RUNTIME_PROOF_RESULT_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?result\s*:\s*`?([A-Za-z_]+)`?\b")


@dataclass(frozen=True)
class ReviewStatusIssue:
    field: str
    message: str


@dataclass(frozen=True)
class ReviewStatusResult:
    ok: bool
    marker_exists: bool
    marker_path: str
    job_id: str
    review_status: str
    payload: dict[str, Any] | None
    issues: list[ReviewStatusIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "marker_exists": self.marker_exists,
            "marker_path": self.marker_path,
            "job_id": self.job_id,
            "review_status": self.review_status,
            "payload": self.payload,
            "issues": [asdict(issue) for issue in self.issues],
        }


def marker_path_for_report(report_dir: Path) -> Path:
    return report_dir / MARKER_FILENAME


def load_report_review_status(
    report_dir: Path,
    *,
    repo_root: Path | None = None,
    require_existing_source_paths: bool = False,
) -> ReviewStatusResult:
    """Load and validate a report-review marker.

    Missing markers are valid optional absence and return review_status
    DATA_MISSING.
    """

    resolved_report_dir = report_dir.resolve()
    marker_path = marker_path_for_report(resolved_report_dir)
    job_id = resolved_report_dir.name

    if not marker_path.exists():
        return ReviewStatusResult(
            ok=True,
            marker_exists=False,
            marker_path=str(marker_path),
            job_id=job_id,
            review_status=DATA_MISSING,
            payload=None,
            issues=[],
        )

    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ReviewStatusResult(
            ok=False,
            marker_exists=True,
            marker_path=str(marker_path),
            job_id=job_id,
            review_status="FAILED_SCHEMA_VALIDATION",
            payload=None,
            issues=[ReviewStatusIssue("json", str(exc))],
        )

    return validate_report_review_status_payload(
        payload,
        report_dir=resolved_report_dir,
        repo_root=repo_root,
        marker_path=marker_path,
        require_existing_source_paths=require_existing_source_paths,
    )


def validate_report_review_status_payload(
    payload: Any,
    *,
    report_dir: Path,
    repo_root: Path | None = None,
    marker_path: Path | None = None,
    require_existing_source_paths: bool = False,
) -> ReviewStatusResult:
    report_dir = report_dir.resolve()
    marker_path = marker_path or marker_path_for_report(report_dir)
    job_id = report_dir.name
    issues: list[ReviewStatusIssue] = []

    if not isinstance(payload, dict):
        return ReviewStatusResult(
            ok=False,
            marker_exists=True,
            marker_path=str(marker_path),
            job_id=job_id,
            review_status="FAILED_SCHEMA_VALIDATION",
            payload=None,
            issues=[ReviewStatusIssue("payload", "must be a JSON object")],
        )

    for field in REQUIRED_FIELDS:
        if field not in payload:
            issues.append(ReviewStatusIssue(field, "required field is missing"))

    extra_fields = sorted(set(payload) - set(REQUIRED_FIELDS))
    for field in extra_fields:
        issues.append(ReviewStatusIssue(field, "additional field is not allowed"))

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != SCHEMA_VERSION:
        issues.append(ReviewStatusIssue("schema_version", "must be integer 1"))

    payload_job_id = payload.get("job_id")
    if payload_job_id != job_id:
        issues.append(ReviewStatusIssue("job_id", f"must match containing report directory {job_id!r}"))

    review_status = payload.get("review_status")
    if not isinstance(review_status, str) or review_status not in ALLOWED_REVIEW_STATUSES:
        issues.append(ReviewStatusIssue("review_status", "must be an allowed review status"))
        review_status_text = "FAILED_SCHEMA_VALIDATION"
    else:
        review_status_text = str(review_status)

    next_action = payload.get("next_action")
    if not isinstance(next_action, str) or next_action not in ALLOWED_NEXT_ACTIONS:
        issues.append(ReviewStatusIssue("next_action", "must be an allowed next action"))

    _require_non_empty_string(payload, "reviewed_at", issues, allow_data_missing=True)
    _require_non_empty_string(payload, "reviewed_by", issues, allow_data_missing=True)
    _require_non_empty_string(payload, "summary", issues, allow_data_missing=False)

    review_evidence = _require_string_list(payload, "review_evidence", issues)
    source_report_paths = _require_string_list(payload, "source_report_paths", issues)

    if review_status_text != DATA_MISSING and not any(path != DATA_MISSING for path in source_report_paths):
        issues.append(ReviewStatusIssue("source_report_paths", f"{review_status_text} requires a concrete source path"))

    if review_status_text in EVIDENCE_REQUIRED_STATUSES and not any(item != DATA_MISSING for item in review_evidence):
        issues.append(ReviewStatusIssue("review_evidence", f"{review_status_text} requires concrete review evidence"))

    for source_path in source_report_paths:
        _validate_source_report_path(
            source_path,
            report_dir=report_dir,
            repo_root=repo_root,
            require_existing=require_existing_source_paths,
            issues=issues,
        )

    runtime_value = payload.get("runtime_functionality_proven")
    if not _is_bool_or_data_missing(runtime_value):
        issues.append(
            ReviewStatusIssue(
                "runtime_functionality_proven",
                "must be a boolean or DATA_MISSING",
            )
        )
    elif runtime_value is True and not _source_reports_prove_runtime_working(source_report_paths, report_dir, repo_root):
        issues.append(
            ReviewStatusIssue(
                "runtime_functionality_proven",
                "true requires a covered source report with Runtime Functionality Proof result WORKING",
            )
        )

    github_value = payload.get("github_state_checked")
    if not _is_bool_or_data_missing(github_value):
        issues.append(ReviewStatusIssue("github_state_checked", "must be a boolean or DATA_MISSING"))
    elif github_value is True and not _has_github_evidence(review_evidence):
        issues.append(
            ReviewStatusIssue(
                "github_state_checked",
                "true requires current-turn GitHub evidence in review_evidence",
            )
        )

    return ReviewStatusResult(
        ok=not issues,
        marker_exists=True,
        marker_path=str(marker_path),
        job_id=job_id,
        review_status=review_status_text,
        payload=dict(payload),
        issues=issues,
    )


def scan_report_review_statuses(
    reports_root: Path,
    *,
    repo_root: Path | None = None,
) -> list[ReviewStatusResult]:
    if not reports_root.exists():
        return []
    return [
        load_report_review_status(path, repo_root=repo_root)
        for path in sorted(reports_root.iterdir())
        if path.is_dir()
    ]


def _require_non_empty_string(
    payload: dict[str, Any],
    field: str,
    issues: list[ReviewStatusIssue],
    *,
    allow_data_missing: bool,
) -> None:
    value = payload.get(field)
    if value == DATA_MISSING and allow_data_missing:
        return
    if not isinstance(value, str) or not value.strip():
        issues.append(ReviewStatusIssue(field, "must be a non-empty string"))


def _require_string_list(
    payload: dict[str, Any],
    field: str,
    issues: list[ReviewStatusIssue],
) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        issues.append(ReviewStatusIssue(field, "must be a non-empty list"))
        return []

    strings: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(ReviewStatusIssue(f"{field}[{idx}]", "must be a non-empty string"))
            continue
        strings.append(item)
    return strings


def _is_bool_or_data_missing(value: Any) -> bool:
    return isinstance(value, bool) or value == DATA_MISSING


def _validate_source_report_path(
    path_text: str,
    *,
    report_dir: Path,
    repo_root: Path | None,
    require_existing: bool,
    issues: list[ReviewStatusIssue],
) -> None:
    if path_text == DATA_MISSING:
        return

    try:
        path = PurePosixPath(path_text)
    except ValueError:
        issues.append(ReviewStatusIssue("source_report_paths", f"{path_text!r} is not a valid path"))
        return

    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        issues.append(ReviewStatusIssue("source_report_paths", f"{path_text!r} must be relative without parent segments"))
        return

    resolved = _resolve_source_report_path(path_text, report_dir, repo_root)
    try:
        resolved.resolve(strict=False).relative_to(report_dir.resolve(strict=False))
    except ValueError:
        issues.append(ReviewStatusIssue("source_report_paths", f"{path_text!r} must stay inside the report directory"))
        return

    if require_existing and not resolved.exists():
        issues.append(ReviewStatusIssue("source_report_paths", f"{path_text!r} does not exist"))


def _resolve_source_report_path(path_text: str, report_dir: Path, repo_root: Path | None) -> Path:
    path = PurePosixPath(path_text)
    if len(path.parts) >= 3 and path.parts[:2] == ("reports", "agent_jobs"):
        root = repo_root.resolve() if repo_root else _infer_repo_root(report_dir)
        return root.joinpath(*path.parts)
    return report_dir.joinpath(*path.parts)


def _infer_repo_root(report_dir: Path) -> Path:
    marker = ("reports", "agent_jobs")
    parts = report_dir.resolve().parts
    for idx in range(len(parts) - len(marker)):
        if tuple(parts[idx : idx + len(marker)]) == marker:
            return Path(*parts[:idx])
    return report_dir.resolve().parents[2]


def _source_reports_prove_runtime_working(
    source_report_paths: Sequence[str],
    report_dir: Path,
    repo_root: Path | None,
) -> bool:
    for path_text in source_report_paths:
        if path_text == DATA_MISSING:
            continue
        source_path = _resolve_source_report_path(path_text, report_dir, repo_root)
        if not source_path.is_file():
            continue
        try:
            text = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = source_path.read_bytes().decode("utf-8", errors="ignore")
        if _has_working_runtime_proof(text):
            return True
    return False


def _has_working_runtime_proof(text: str) -> bool:
    lower = text.lower()
    if any(field not in lower for field in RUNTIME_PROOF_FIELD_LABELS):
        return False
    return any(match.group(1).upper() == "WORKING" for match in RUNTIME_PROOF_RESULT_RE.finditer(text))


def _has_github_evidence(review_evidence: Sequence[str]) -> bool:
    evidence = "\n".join(review_evidence).lower()
    return "github" in evidence or re.search(r"\bgh\s+", evidence) is not None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate one report directory marker")
    validate.add_argument("report_dir", type=Path)
    validate.add_argument("--repo-root", type=Path)
    validate.add_argument("--require-existing-source-paths", action="store_true")

    scan = sub.add_parser("scan", help="scan immediate report directories for markers")
    scan.add_argument("reports_root", type=Path, nargs="?", default=Path("reports/agent_jobs"))
    scan.add_argument("--repo-root", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        result = load_report_review_status(
            args.report_dir,
            repo_root=args.repo_root,
            require_existing_source_paths=args.require_existing_source_paths,
        )
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.ok else 1

    if args.command == "scan":
        results = scan_report_review_statuses(args.reports_root, repo_root=args.repo_root)
        payload = {
            "ok": all(result.ok for result in results),
            "reports_root": str(args.reports_root),
            "results": [result.to_dict() for result in results],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
