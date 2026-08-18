#!/usr/bin/env python3
"""Manifest-only strict write gate for Tenn automation candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = 1
SAFE_LANES = {"reporting", "repo_hygiene", "evaluation", "query_orchestration"}
FORBIDDEN_LANES = {"runtime", "data", "financial_truth", "provenance", "extraction", "source_pdf", "gold_label"}
SAFE_RISKS = {"low", "medium"}
HIGH_RISKS = {"high", "critical"}
SAFE_WRITE_STATUSES = {"needs_review", "failed_validation", "owner_decision_required", "new"}
VALID_DEDUPE_STATUSES = {"new", "duplicate_issue", "duplicate_pr", "needs_review", "data_missing"}
ACTION_APPROVAL_PHRASES = {
    "open_issue": "open issue",
    "comment_existing_issue": "comment on existing issue",
    "comment_existing_pr": "comment on existing pr",
    "create_draft_pr": "create draft PR",
    "park_high_risk": "start high-risk experiment",
    "review_only": "review this",
}
VALID_ACTIONS = set(ACTION_APPROVAL_PHRASES) | {"auto"}


def normalize_token(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def normalize_phrase(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def _string_value(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def _number_text(value: object) -> str | None:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip().lstrip("#").isdigit():
        return value.strip().lstrip("#")
    return None


def _best_match(dedupe_result: dict[str, object]) -> dict[str, object]:
    best = dedupe_result.get("best_match")
    return best if isinstance(best, dict) else {}


def _candidate_summary(candidate: dict[str, object]) -> dict[str, object]:
    keys = [
        "fingerprint",
        "status",
        "title",
        "root_cause",
        "evidence_path",
        "lane",
        "risk",
        "related_issue",
        "related_pr",
        "url",
    ]
    return {key: candidate[key] for key in keys if key in candidate and candidate[key] not in {None, ""}}


def _dedupe_summary(dedupe_result: dict[str, object]) -> dict[str, object]:
    best = _best_match(dedupe_result)
    summary: dict[str, object] = {
        "status": normalize_token(dedupe_result.get("status")) or "data_missing",
        "errors": dedupe_result.get("errors") if isinstance(dedupe_result.get("errors"), list) else [],
    }
    if best:
        summary["best_match"] = {
            key: best[key]
            for key in ["kind", "number", "title", "url", "confidence", "score"]
            if key in best and best[key] not in {None, ""}
        }
    return summary


def _target_for_existing(kind: str, best_match: dict[str, object]) -> dict[str, object]:
    return {
        "kind": kind,
        "number": _number_text(best_match.get("number")) or "DATA_MISSING",
        "title": str(best_match.get("title") or ""),
        "url": str(best_match.get("url") or ""),
    }


def _target_for_open_issue(candidate: dict[str, object]) -> dict[str, object]:
    return {
        "title": _string_value(candidate, "title"),
        "body_source": _string_value(candidate, "evidence_path"),
        "root_cause": _string_value(candidate, "root_cause"),
        "lane": normalize_token(candidate.get("lane")),
        "risk": normalize_token(candidate.get("risk")),
    }


def _target_for_draft_pr(candidate: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    draft = candidate.get("draft_pr")
    if not isinstance(draft, dict):
        return {}, ["draft_pr_metadata_missing"]
    required = ["branch", "base", "title", "body", "validation"]
    missing = [f"draft_pr_{key}_missing" for key in required if not isinstance(draft.get(key), str) or not draft.get(key)]
    if missing:
        return {}, missing
    return {
        "branch": str(draft["branch"]),
        "base": str(draft["base"]),
        "title": str(draft["title"]),
        "body": str(draft["body"]),
        "validation": str(draft["validation"]),
    }, []


def _target_for_high_risk(candidate: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    isolation = candidate.get("isolation")
    if not isinstance(isolation, dict):
        return {}, ["isolation_missing"]
    required = ["branch", "worktree", "base"]
    missing = [f"isolation_{key}_missing" for key in required if not isinstance(isolation.get(key), str) or not isolation.get(key)]
    if missing:
        return {}, missing
    return {
        "branch": str(isolation["branch"]),
        "worktree": str(isolation["worktree"]),
        "base": str(isolation["base"]),
    }, []


def _base_blockers(candidate: dict[str, object], dedupe_result: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    for key in ["title", "root_cause", "evidence_path"]:
        if not _string_value(candidate, key):
            blockers.append(f"candidate_{key}_missing")

    dedupe_status = normalize_token(dedupe_result.get("status"))
    errors = dedupe_result.get("errors")
    if dedupe_status == "data_missing" or (isinstance(errors, list) and errors):
        blockers.append("dedupe_data_missing")
    elif not dedupe_status:
        blockers.append("dedupe_data_missing")
    elif dedupe_status not in VALID_DEDUPE_STATUSES:
        blockers.append("dedupe_data_missing")
    return blockers


def _safety_notes(candidate: dict[str, object]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    blockers: list[str] = []
    lane = normalize_token(candidate.get("lane"))
    risk = normalize_token(candidate.get("risk"))
    status = normalize_token(candidate.get("status")) or "new"

    if lane in SAFE_LANES:
        reasons.append(f"safe_lane:{lane}")
    elif lane in FORBIDDEN_LANES:
        blockers.append(f"forbidden_lane:{lane}")
    else:
        blockers.append("lane_not_safe")

    if risk in SAFE_RISKS:
        reasons.append(f"safe_risk:{risk}")
    elif risk in HIGH_RISKS:
        blockers.append(f"high_risk:{risk}")
    else:
        blockers.append("risk_not_safe")

    if status in SAFE_WRITE_STATUSES:
        reasons.append(f"candidate_status:{status}")
    else:
        blockers.append(f"candidate_status_not_write_safe:{status}")
    return reasons, blockers


def _resolve_action(
    candidate: dict[str, object],
    dedupe_result: dict[str, object],
    requested_action: str,
) -> tuple[str, dict[str, object], list[str], list[str], str]:
    dedupe_status = normalize_token(dedupe_result.get("status"))
    best = _best_match(dedupe_result)
    reasons: list[str] = []
    blockers: list[str] = []
    status = "eligible"

    if dedupe_status == "duplicate_issue":
        if requested_action in {"auto", "comment_existing_issue"}:
            target = _target_for_existing("issue", best)
            if target["number"] == "DATA_MISSING":
                blockers.append("duplicate_issue_number_missing")
            reasons.append("duplicate_issue")
            return "comment_existing_issue", target, reasons, blockers, status
        blockers.append("duplicate_blocks_new_write")
        return "review_only", {}, ["duplicate_issue"], blockers, "blocked"

    if dedupe_status == "duplicate_pr":
        if requested_action in {"auto", "comment_existing_pr"}:
            target = _target_for_existing("pr", best)
            if target["number"] == "DATA_MISSING":
                blockers.append("duplicate_pr_number_missing")
            reasons.append("duplicate_pr")
            return "comment_existing_pr", target, reasons, blockers, status
        blockers.append("duplicate_blocks_new_write")
        return "review_only", {}, ["duplicate_pr"], blockers, "blocked"

    if dedupe_status == "needs_review":
        return "review_only", {}, ["dedupe_needs_review"], ["dedupe_needs_review"], "owner_review_required"

    if requested_action == "auto":
        requested_action = "open_issue"

    if requested_action == "open_issue":
        safety_reasons, safety_blockers = _safety_notes(candidate)
        reasons.extend(safety_reasons)
        blockers.extend(safety_blockers)
        return "open_issue", _target_for_open_issue(candidate), reasons, blockers, status

    if requested_action == "create_draft_pr":
        safety_reasons, safety_blockers = _safety_notes(candidate)
        reasons.extend(safety_reasons)
        blockers.extend(safety_blockers)
        target, target_blockers = _target_for_draft_pr(candidate)
        blockers.extend(target_blockers)
        return "create_draft_pr", target, reasons, blockers, status

    if requested_action == "park_high_risk":
        target, target_blockers = _target_for_high_risk(candidate)
        blockers.extend(target_blockers)
        risk = normalize_token(candidate.get("risk"))
        lane = normalize_token(candidate.get("lane"))
        if risk not in HIGH_RISKS and lane not in FORBIDDEN_LANES:
            blockers.append("candidate_not_high_risk")
        reasons.append("isolated_high_risk_consideration")
        return "park_high_risk", target, reasons, blockers, status

    if requested_action == "review_only":
        return "review_only", {}, ["owner_review_requested"], [], "owner_review_required"

    return "review_only", {}, [], ["requested_action_unknown"], "blocked"


def _approval(required_phrase: str, approval_phrase: str | None) -> dict[str, object]:
    if not approval_phrase:
        return {"status": "missing", "provided": None}
    matched = normalize_phrase(approval_phrase) == normalize_phrase(required_phrase)
    return {
        "status": "matched" if matched else "mismatch",
        "provided": approval_phrase,
    }


def build_manifest(
    candidate: dict[str, object],
    dedupe_result: dict[str, object],
    *,
    requested_action: str = "auto",
    approval_phrase: str | None = None,
) -> dict[str, object]:
    requested = normalize_token(requested_action) or "auto"
    if requested not in VALID_ACTIONS:
        requested = "unknown"

    action_type, target, reasons, action_blockers, status = _resolve_action(candidate, dedupe_result, requested)
    blockers = [*_base_blockers(candidate, dedupe_result), *action_blockers]
    if status == "eligible" and blockers:
        status = "data_missing" if "dedupe_data_missing" in blockers else "blocked"
    if "dedupe_data_missing" in blockers:
        action_type = "review_only"
        target = {}

    required_phrase = ACTION_APPROVAL_PHRASES.get(action_type, "review this")
    approval = _approval(required_phrase, approval_phrase)
    may_execute = status == "eligible" and approval["status"] == "matched"
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "status": status,
        "requested_action": requested_action,
        "action": {
            "type": action_type,
            "target": target,
        },
        "required_approval_phrase": required_phrase,
        "approval": approval,
        "may_execute": may_execute,
        "candidate": _candidate_summary(candidate),
        "dedupe": _dedupe_summary(dedupe_result),
        "reasons": sorted(set(reasons)),
        "blockers": sorted(set(blockers)),
        "forbidden_without_executor": [
            "gh issue create",
            "gh issue comment",
            "gh pr create",
            "gh pr comment",
            "git push",
            "systemctl",
        ],
    }


def load_json_source(inline_json: str | None, path: Path | None, *, source_name: str) -> dict[str, object]:
    if inline_json and path:
        raise ValueError(f"{source_name}: provide inline JSON or path, not both")
    if not inline_json and not path:
        raise ValueError(f"{source_name}: JSON source is required")
    text = inline_json if inline_json is not None else path.read_text(encoding="utf-8")  # type: ignore[union-attr]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{source_name}: JSON must be an object")
    return dict(payload)


def format_manifest(manifest: dict[str, object]) -> str:
    action = manifest.get("action") if isinstance(manifest.get("action"), dict) else {}
    lines = [
        f"status: {manifest.get('status')}",
        f"action: {action.get('type')}",
        f"may_execute: {str(manifest.get('may_execute')).lower()}",
        f"required_approval_phrase: {manifest.get('required_approval_phrase')}",
        "read_only: true",
    ]
    blockers = manifest.get("blockers")
    if isinstance(blockers, list) and blockers:
        lines.append("blockers:")
        lines.extend(f"- {blocker}" for blocker in blockers)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest", help="build a strict write manifest without performing writes")
    candidate_group = manifest.add_mutually_exclusive_group(required=True)
    candidate_group.add_argument("--candidate-json")
    candidate_group.add_argument("--candidate-path", type=Path)
    dedupe_group = manifest.add_mutually_exclusive_group(required=True)
    dedupe_group.add_argument("--dedupe-json")
    dedupe_group.add_argument("--dedupe-path", type=Path)
    manifest.add_argument(
        "--requested-action",
        default="auto",
        choices=sorted(VALID_ACTIONS - {"auto"}) + ["auto"],
    )
    manifest.add_argument("--approval-phrase")
    manifest.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "manifest":
        try:
            candidate = load_json_source(args.candidate_json, args.candidate_path, source_name="candidate")
            dedupe_result = load_json_source(args.dedupe_json, args.dedupe_path, source_name="dedupe")
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        manifest = build_manifest(
            candidate,
            dedupe_result,
            requested_action=args.requested_action,
            approval_phrase=args.approval_phrase,
        )
        if args.json:
            print(json.dumps(manifest, indent=2, sort_keys=True))
        else:
            print(format_manifest(manifest))
        return 0 if manifest["status"] != "data_missing" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
