"""Read-only review packet builder for confirmed metric coverage.

This is an evaluation/reporting sidecar. It reads fixture labels and writes
review artifacts only under reports; it does not run extraction or mutate
canonical labels, database rows, or vector collections.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import PROJECT_ROOT, is_running_in_docker
from app.services.extraction_gold_eval_scorecard import (
    build_confirmed_metric_coverage_scorecard,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COVERAGE_FIXTURES_DIR = BACKEND_ROOT / "tests" / "eval_fixtures"
WORKSPACE_ROOT = Path(
    os.getenv("COCKPIT_WORKSPACE_ROOT")
    or os.getenv("TENN_WORKSPACE_ROOT")
    or PROJECT_ROOT.parent
)
CONFIRMED_COVERAGE_REPORTS_DIR = WORKSPACE_ROOT / "reports" / "extraction_eval"
PROFILE_NAME = "confirmed_metric_coverage"
ARTIFACT_PREFIX = "confirmed_metric_coverage_review_"

CLASS_CONFIRMED = "CONFIRMED_SOURCE_EVIDENCED"
CLASS_CANDIDATE = "CANDIDATE_REVIEW_REQUIRED"
CLASS_AMBIGUOUS = "AMBIGUOUS_OR_DERIVED"
CLASS_UNSUPPORTED = "UNSUPPORTED"


def latest_confirmed_metric_coverage_packet() -> dict[str, Any] | None:
    """Return the newest generated review packet, if one exists."""

    packet_path = _latest_packet_path()
    if packet_path is None:
        return None
    return _read_packet(packet_path)


def confirmed_metric_coverage_summary() -> dict[str, Any]:
    """Return latest artifact summary or a not-generated status."""

    packet = latest_confirmed_metric_coverage_packet()
    if packet is None:
        return {
            "status": "not_generated",
            "profile": PROFILE_NAME,
            "summary": None,
            "artifacts": None,
            "errors": [],
            "warnings": ["No confirmed metric coverage review artifact exists yet."],
        }
    provenance = _packet_provenance(packet)
    return {
        "status": packet.get("status", "ready"),
        "profile": packet.get("profile", PROFILE_NAME),
        "generated_at": packet.get("generated_at"),
        "head": packet.get("head"),
        "branch": packet.get("branch"),
        **provenance,
        "summary": packet.get("summary"),
        "artifacts": packet.get("artifacts"),
        "artifact_path": packet.get("artifact_path"),
        "errors": packet.get("errors", []),
        "warnings": packet.get("warnings", []),
    }


def confirmed_metric_coverage_rows() -> dict[str, Any]:
    """Return latest artifact rows or a not-generated status."""

    packet = latest_confirmed_metric_coverage_packet()
    if packet is None:
        return {
            "status": "not_generated",
            "profile": PROFILE_NAME,
            "rows": [],
            "count": 0,
            "artifacts": None,
            "errors": [],
            "warnings": ["No confirmed metric coverage review artifact exists yet."],
        }
    rows = packet.get("rows") if isinstance(packet.get("rows"), list) else []
    provenance = _packet_provenance(packet)
    return {
        "status": packet.get("status", "ready"),
        "profile": packet.get("profile", PROFILE_NAME),
        "generated_at": packet.get("generated_at"),
        "head": packet.get("head"),
        "branch": packet.get("branch"),
        **provenance,
        "rows": rows,
        "count": len(rows),
        "artifacts": packet.get("artifacts"),
        "artifact_path": packet.get("artifact_path"),
        "errors": packet.get("errors", []),
        "warnings": packet.get("warnings", []),
    }


def run_confirmed_metric_coverage_review(
    *,
    fixtures_dir: str | Path | None = None,
    reports_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build and persist a review packet from fixtures only."""

    resolved_fixtures_dir = Path(fixtures_dir or DEFAULT_COVERAGE_FIXTURES_DIR)
    if not resolved_fixtures_dir.exists():
        raise FileNotFoundError(
            f"confirmed metric coverage fixtures not found: {resolved_fixtures_dir}"
        )

    scorecard = build_confirmed_metric_coverage_scorecard(
        resolved_fixtures_dir,
        financial_engine_root=PROJECT_ROOT,
    )
    if int(scorecard.get("total_fixture_count") or 0) <= 0:
        raise ValueError(
            f"confirmed metric coverage fixtures are empty: {resolved_fixtures_dir}"
        )

    packet = _build_packet(scorecard, resolved_fixtures_dir)
    artifact_dir = _artifact_dir(Path(reports_dir or CONFIRMED_COVERAGE_REPORTS_DIR))
    artifact_dir.mkdir(parents=True, exist_ok=False)
    json_path = artifact_dir / "review_packet.json"
    md_path = artifact_dir / "review_packet.md"
    artifacts = {
        "artifact_dir": str(artifact_dir),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    packet["artifacts"] = artifacts
    packet["artifact_path"] = str(json_path)
    summary = packet.get("summary")
    if isinstance(summary, dict):
        summary["artifact_path"] = str(json_path)
    json_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown_packet(packet), encoding="utf-8")
    return packet


def _build_packet(
    scorecard: Mapping[str, Any],
    fixtures_dir: Path,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    provenance = _build_provenance(generated_at, fixtures_dir)
    fixture_payloads = _load_fixture_payloads(fixtures_dir)
    rows = [
        _build_row(row, fixture_payloads)
        for row in scorecard.get("metric_expectations", [])
        if isinstance(row, Mapping)
    ]
    _apply_review_quality_flags(rows)
    summary = _build_summary(scorecard, rows, provenance)
    warnings = _packet_warnings(scorecard, rows)
    return {
        "status": "ready_with_warnings" if warnings else "ready",
        "profile": PROFILE_NAME,
        "generated_at": generated_at,
        "head": provenance["git_head_short"],
        "branch": provenance["git_branch"],
        **provenance,
        "fixtures_dir": str(fixtures_dir),
        "fixture_dir": str(fixtures_dir),
        "artifact_path": None,
        "summary": summary,
        "rows": rows,
        "artifacts": None,
        "errors": [],
        "warnings": warnings,
        "scorecard": {
            "metric_family_summary": scorecard.get("metric_family_summary", {}),
            "source_status_counts": scorecard.get("source_status_counts", {}),
            "canonical_trust_semantics": scorecard.get("canonical_trust_semantics", {}),
        },
        "copy": {
            "review_only": "This review does not run extraction.",
            "candidate_review": (
                "Candidate metrics require human source-evidence review before "
                "production scoring."
            ),
            "trust_semantics": "Canonical trust semantics are unchanged.",
        },
    }


def _build_summary(
    scorecard: Mapping[str, Any],
    rows: list[dict[str, Any]],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    classified = _count_by(rows, "classification")
    reviewed = _count_by(rows, "review_status")
    missing_pdf_count = sum(
        1 for row in rows if row.get("source_pdf_status") == "missing"
    )
    return {
        "profile": PROFILE_NAME,
        "fixture_count": int(scorecard.get("total_fixture_count") or 0),
        "total_expectations": int(scorecard.get("total_metric_expectations") or 0),
        "scored_count": int(scorecard.get("scored_metric_expectations") or 0),
        "candidate_review_required_count": int(
            scorecard.get("candidate_review_required_count") or 0
        ),
        "ambiguous_count": int(scorecard.get("ambiguous_metric_count") or 0),
        "unsupported_count": int(scorecard.get("unsupported_metric_count") or 0)
        + int(scorecard.get("missing_source_evidence_count") or 0),
        "missing_source_evidence_count": int(
            scorecard.get("missing_source_evidence_count") or 0
        ),
        "missing_source_pdf_count": missing_pdf_count,
        "classification_counts": classified,
        "review_status_counts": reviewed,
        "generated_at": provenance.get("generated_at"),
        "head": provenance.get("git_head_short"),
        "branch": provenance.get("git_branch"),
        "git_available": provenance.get("git_available"),
        "git_head": provenance.get("git_head"),
        "git_head_short": provenance.get("git_head_short"),
        "git_branch": provenance.get("git_branch"),
        "git_dirty": provenance.get("git_dirty"),
        "git_status_short_summary": provenance.get("git_status_short_summary"),
        "git_unavailable_reason": provenance.get("git_unavailable_reason"),
        "fixture_dir": provenance.get("fixture_dir"),
        "artifact_path": provenance.get("artifact_path"),
        "app_runtime_context": provenance.get("app_runtime_context"),
        "canonical_core_unchanged": bool(
            scorecard.get("canonical_trust_semantics", {}).get(
                "canonical_core_unchanged"
            )
        ),
        "expanded_required_unchanged": bool(
            scorecard.get("canonical_trust_semantics", {}).get(
                "expanded_required_unchanged"
            )
        ),
        "canonical_labels_mutated": False,
    }


def _build_row(
    expectation: Mapping[str, Any],
    fixture_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    document_id = str(
        expectation.get("document_id") or expectation.get("fixture_id") or ""
    )
    fixture = str(expectation.get("fixture") or "")
    payload = fixture_payloads.get(fixture) or fixture_payloads.get(document_id) or {}
    metric = str(expectation.get("metric_name") or "")
    note = _metric_note(payload, metric)
    source_pdf_path = _str_or_none(
        payload.get("pdf_path") or payload.get("source_file")
    )
    source_page = _extract_source_page(note)
    source_table = _extract_source_table(note)
    classification = _classification_for_support_status(
        str(expectation.get("support_status") or "")
    )
    return {
        "fixture_id": str(expectation.get("fixture_id") or document_id),
        "document_id": document_id,
        "fixture": fixture,
        "ticker": _str_or_none(payload.get("ticker")),
        "period": {
            "period_type": _str_or_none(payload.get("period_type")),
            "period_end": _str_or_none(payload.get("period_end")),
        },
        "metric_name": metric,
        "canonical_field": _str_or_none(expectation.get("canonical_field")),
        "expectation_type": str(expectation.get("expectation_type") or ""),
        "expected_value": expectation.get("expected_value"),
        "expected_null": str(expectation.get("expectation_type") or "")
        == "expected_null",
        "currency": _str_or_none(payload.get("currency")),
        "scale": _str_or_none(payload.get("scale")),
        "source_pdf_path": source_pdf_path,
        "source_pdf_exists": expectation.get("source_pdf_exists"),
        "source_pdf_status": _source_pdf_status(expectation.get("source_pdf_exists")),
        "source_page": source_page,
        "source_table": source_table,
        "source_row": _extract_source_row(note),
        "source_evidence_status": str(expectation.get("source_status") or ""),
        "classification": classification,
        "schema_support": {
            "schema_supported": bool(expectation.get("schema_supported")),
            "extractor_output_supported": bool(
                expectation.get("extractor_output_supported")
            ),
            "evaluator_supported": bool(expectation.get("evaluator_supported")),
        },
        "ambiguity_reason": expectation.get("ambiguity"),
        "recommended_action": str(expectation.get("recommendation") or ""),
        "production_metric_tier": str(expectation.get("tier") or ""),
        "review_status": _review_status_for_classification(classification),
        "evaluation_status": expectation.get("evaluation_status"),
        "actual_value": expectation.get("actual_value"),
        "score": expectation.get("score"),
        "reason": expectation.get("reason"),
    }


def _apply_review_quality_flags(rows: list[dict[str, Any]]) -> None:
    source_counts: dict[tuple[Any, ...], int] = {}
    for row in rows:
        signature = _source_signature(row)
        if signature is None:
            continue
        source_counts[signature] = source_counts.get(signature, 0) + 1

    for row in rows:
        source_pdf_present = row.get("source_pdf_status") == "present"
        source_page_present = row.get("source_page") is not None
        source_row_present = bool(row.get("source_row"))
        source_table_present = bool(row.get("source_table"))
        signature = _source_signature(row)
        duplicate_source_reference = (
            signature is not None and source_counts.get(signature, 0) > 1
        )
        precise_source_evidence = (
            source_pdf_present
            and source_page_present
            and source_row_present
            and not duplicate_source_reference
        )
        classification = str(row.get("classification") or "")
        broad_or_suspect_source_evidence = (
            not precise_source_evidence
            or duplicate_source_reference
            or classification in {CLASS_CANDIDATE, CLASS_AMBIGUOUS, CLASS_UNSUPPORTED}
        )

        row["source_pdf_present"] = source_pdf_present
        row["source_page_present"] = source_page_present
        row["source_row_present"] = source_row_present
        row["source_table_present"] = source_table_present
        row["precise_source_evidence"] = precise_source_evidence
        row["broad_or_suspect_source_evidence"] = broad_or_suspect_source_evidence
        row["human_review_required"] = (
            classification in {CLASS_CANDIDATE, CLASS_AMBIGUOUS, CLASS_UNSUPPORTED}
            or broad_or_suspect_source_evidence
        )
        row["blocked_ambiguous"] = classification == CLASS_AMBIGUOUS


def _source_signature(row: Mapping[str, Any]) -> tuple[Any, ...] | None:
    document_id = row.get("document_id")
    page = row.get("source_page")
    table = row.get("source_table")
    source_row = row.get("source_row")
    if not document_id or page is None or not source_row:
        return None
    return (document_id, page, table, source_row)


def _load_fixture_payloads(fixtures_dir: Path) -> dict[str, Mapping[str, Any]]:
    payloads: dict[str, Mapping[str, Any]] = {}
    for path in sorted(fixtures_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            continue
        document_id = str(payload.get("document_id") or path.stem)
        payloads[path.name] = payload
        payloads[document_id] = payload
    return payloads


def _metric_note(payload: Mapping[str, Any], metric: str) -> str:
    for key in ("notes", "_notes"):
        notes = payload.get(key)
        if isinstance(notes, Mapping):
            value = notes.get(metric)
            if value is not None:
                return str(value)
    return str(payload.get("_source") or "")


def _classification_for_support_status(support_status: str) -> str:
    if support_status == "scored":
        return CLASS_CONFIRMED
    if support_status == "candidate_review_required":
        return CLASS_CANDIDATE
    if support_status == "ambiguous_label":
        return CLASS_AMBIGUOUS
    return CLASS_UNSUPPORTED


def _review_status_for_classification(classification: str) -> str:
    if classification == CLASS_CONFIRMED:
        return "review_only_confirmed"
    if classification == CLASS_CANDIDATE:
        return "needs_human_review"
    if classification == CLASS_AMBIGUOUS:
        return "blocked_ambiguous"
    return "blocked_unsupported"


def _source_pdf_status(value: Any) -> str:
    if value is True:
        return "present"
    if value is False:
        return "missing"
    return "not_declared"


def _extract_source_page(text: str) -> int | None:
    match = re.search(r"\bp(?:age)?\.?\s*(\d{1,4})\b", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_source_table(text: str) -> str | None:
    match = re.search(r"\btable\s+([A-Za-z0-9_.-]+)", text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _extract_source_row(text: str) -> str | None:
    match = re.search(r"'([^']{3,120})'", text)
    return match.group(1) if match else None


def _packet_warnings(
    scorecard: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if int(scorecard.get("missing_source_evidence_count") or 0) > 0:
        warnings.append("One or more expectations are missing source evidence.")
    if any(row.get("source_pdf_status") == "missing" for row in rows):
        warnings.append("One or more source PDF paths are missing on disk.")
    if int(scorecard.get("candidate_review_required_count") or 0) > 0:
        warnings.append("Candidate rows require human source-evidence review.")
    if int(scorecard.get("ambiguous_metric_count") or 0) > 0:
        warnings.append("Ambiguous rows are excluded from production scoring.")
    return warnings


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "DATA_MISSING")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _artifact_dir(reports_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return reports_dir / f"{ARTIFACT_PREFIX}{stamp}"


def _latest_packet_path() -> Path | None:
    root = CONFIRMED_COVERAGE_REPORTS_DIR
    if not root.exists():
        return None
    candidates = sorted(
        root.glob(f"{ARTIFACT_PREFIX}*/review_packet.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_packet(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"review packet is not a JSON object: {path}")
    return payload


def _render_markdown_packet(packet: Mapping[str, Any]) -> str:
    summary = (
        packet.get("summary") if isinstance(packet.get("summary"), Mapping) else {}
    )
    artifacts = (
        packet.get("artifacts") if isinstance(packet.get("artifacts"), Mapping) else {}
    )
    lines = [
        "# Confirmed Metric Coverage Review",
        "",
        "- This review does not run extraction.",
        "- Candidate metrics require human source-evidence review before production scoring.",
        "- Canonical trust semantics are unchanged.",
        "",
        "## Summary",
        "",
    ]
    for key in (
        "profile",
        "fixture_count",
        "total_expectations",
        "scored_count",
        "candidate_review_required_count",
        "ambiguous_count",
        "unsupported_count",
        "missing_source_pdf_count",
        "generated_at",
        "head",
        "branch",
        "git_available",
        "git_head",
        "git_head_short",
        "git_branch",
        "git_dirty",
        "git_unavailable_reason",
        "fixture_dir",
        "artifact_path",
    ):
        lines.append(f"- {key}: `{summary.get(key, packet.get(key, 'DATA_MISSING'))}`")
    lines.extend(["", "## Artifacts", ""])
    for key, value in artifacts.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Rows", ""])
    lines.append(
        "| ticker | fixture | period | metric | classification | source | action |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in packet.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        period = row.get("period") if isinstance(row.get("period"), Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                _md_cell(value)
                for value in (
                    row.get("ticker"),
                    row.get("fixture"),
                    period.get("period_end"),
                    row.get("metric_name"),
                    row.get("classification"),
                    row.get("source_pdf_status"),
                    row.get("recommended_action"),
                )
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _md_cell(value: Any) -> str:
    return str(value if value not in (None, "") else "-").replace("|", "\\|")


def _packet_provenance(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "git_available": packet.get("git_available"),
        "git_head": packet.get("git_head"),
        "git_head_short": packet.get("git_head_short"),
        "git_branch": packet.get("git_branch"),
        "git_dirty": packet.get("git_dirty"),
        "git_status_short_summary": packet.get("git_status_short_summary"),
        "git_unavailable_reason": packet.get("git_unavailable_reason"),
        "fixture_dir": packet.get("fixture_dir") or packet.get("fixtures_dir"),
        "artifact_path": packet.get("artifact_path"),
        "app_runtime_context": packet.get("app_runtime_context"),
    }


def _build_provenance(generated_at: str, fixtures_dir: Path) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "profile": PROFILE_NAME,
        "fixture_dir": str(fixtures_dir),
        "artifact_path": None,
        **_git_provenance(WORKSPACE_ROOT),
        "app_runtime_context": {
            "cwd": str(Path.cwd()),
            "workspace_root": str(WORKSPACE_ROOT),
            "project_root": str(PROJECT_ROOT),
            "backend_root": str(BACKEND_ROOT),
            "running_in_docker": is_running_in_docker(),
        },
    }


def _git_provenance(workspace_root: Path = WORKSPACE_ROOT) -> dict[str, Any]:
    git_dir_check = _git_command(workspace_root, "rev-parse", "--git-dir")
    if git_dir_check["returncode"] != 0:
        return _git_unavailable(
            git_dir_check["reason"]
            or _stderr_reason(git_dir_check["stderr"])
            or f"git metadata unavailable from workspace_root={workspace_root}"
        )

    head = _git_command(workspace_root, "rev-parse", "HEAD")
    head_short = _git_command(workspace_root, "rev-parse", "--short=12", "HEAD")
    branch = _git_command(workspace_root, "branch", "--show-current")
    status = _git_command(workspace_root, "status", "--short")

    for result in (head, head_short, status):
        if result["returncode"] != 0:
            return _git_unavailable(
                result["reason"]
                or _stderr_reason(result["stderr"])
                or f"git command failed in workspace_root={workspace_root}"
            )

    branch_value = branch["stdout"].strip() if branch["returncode"] == 0 else ""
    if not branch_value:
        branch_value = "DETACHED_HEAD"
    status_lines = [line for line in status["stdout"].splitlines() if line.strip()]
    return {
        "git_available": True,
        "git_head": head["stdout"].strip(),
        "git_head_short": head_short["stdout"].strip(),
        "git_branch": branch_value,
        "git_dirty": bool(status_lines),
        "git_status_short_summary": {
            "line_count": len(status_lines),
            "entries": status_lines[:20],
            "truncated": len(status_lines) > 20,
        },
        "git_unavailable_reason": None,
    }


def _git_unavailable(reason: str) -> dict[str, Any]:
    return {
        "git_available": False,
        "git_head": None,
        "git_head_short": None,
        "git_branch": None,
        "git_dirty": None,
        "git_status_short_summary": {
            "line_count": 0,
            "entries": [],
            "truncated": False,
        },
        "git_unavailable_reason": reason,
    }


def _git_command(workspace_root: Path, *args: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except FileNotFoundError:
        return {
            "returncode": 127,
            "stdout": "",
            "stderr": "",
            "reason": "git executable not found",
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": 124,
            "stdout": "",
            "stderr": "",
            "reason": f"git command timed out in workspace_root={workspace_root}",
        }
    except OSError as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": "",
            "reason": f"git command failed in workspace_root={workspace_root}: {exc}",
        }
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "reason": None,
    }


def _stderr_reason(stderr: str) -> str:
    text = str(stderr or "").strip()
    return text or "git command failed without stderr"


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
