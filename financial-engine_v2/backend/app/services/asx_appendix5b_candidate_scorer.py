"""Read-only scoring for Appendix 5B candidate artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any


SCORE_REPORT_TYPE = "appendix5b_candidate_score_report_v1"
LABEL_SCHEMA = "appendix5b_candidate_labels_v1"

_SCALE_MULTIPLIERS = {
    None: Decimal("1"),
    "": Decimal("1"),
    "ones": Decimal("1"),
    "thousands": Decimal("1000"),
    "millions": Decimal("1000000"),
    "billions": Decimal("1000000000"),
}


def score_appendix5b_candidate_artifacts(
    *,
    artifact_paths: list[Path],
    labels_path: Path,
    output_path: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Score committed/read-only Appendix 5B candidate artifacts against labels.

    The scorer does not run extraction and does not promote any value. It only
    compares candidate artifacts to an explicit label file and preserves the
    candidate evidence in the score report.
    """

    labels = _load_labels(labels_path)
    documents: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        artifact = _load_json(artifact_path)
        for document in artifact.get("documents") or []:
            documents.append(
                _score_document(
                    document,
                    labels_by_document=labels["documents_by_id"],
                    artifact_path=artifact_path,
                )
            )

    report = {
        "artifact_type": SCORE_REPORT_TYPE,
        "label_schema": labels["label_schema"],
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "canonical_write": False,
        "score_scope": "report_local_labels_only",
        "labels_path": str(labels_path),
        "artifact_paths": [str(path) for path in artifact_paths],
        "summary": _summarize_documents(documents),
        "documents": documents,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _score_document(
    document: dict[str, Any],
    *,
    labels_by_document: dict[str, dict[str, Any]],
    artifact_path: Path,
) -> dict[str, Any]:
    document_id = str(document.get("document_id") or "")
    label = labels_by_document.get(document_id)
    candidates = [
        candidate
        for candidate in document.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    current_quarter_candidates = [
        candidate
        for candidate in candidates
        if str(candidate.get("column_role") or "current_quarter") == "current_quarter"
    ]
    if label is None:
        comparisons = [
            _candidate_unlabelled(candidate, reason="document has no label entry")
            for candidate in current_quarter_candidates
        ]
        status = "UNSCORED"
    else:
        comparisons = _score_labelled_document(current_quarter_candidates, label)
        status = _document_status(comparisons)

    return {
        "artifact_path": str(artifact_path),
        "document_id": document_id,
        "ticker": document.get("ticker"),
        "period_end": document.get("period_end"),
        "period_type": document.get("period_type"),
        "document_type": document.get("document_type"),
        "parse_status": document.get("parse_status"),
        "candidate_count": len(candidates),
        "current_quarter_candidate_count": len(current_quarter_candidates),
        "status": status,
        "summary": _summarize_comparisons(comparisons),
        "comparisons": comparisons,
    }


def _score_labelled_document(
    candidates: list[dict[str, Any]],
    label: dict[str, Any],
) -> list[dict[str, Any]]:
    metrics = label.get("metrics") or {}
    expected_nulls = set(label.get("expected_nulls") or [])
    consumed_candidate_ids: set[int] = set()
    comparisons: list[dict[str, Any]] = []

    for metric_name in sorted(metrics):
        metric_label = _metric_label(metric_name, metrics[metric_name], label)
        matching_candidates = _matching_candidates(candidates, metric_label)
        if not matching_candidates:
            comparisons.append(_candidate_missing(metric_label))
            continue
        if len(matching_candidates) > 1 and not metric_label.get("line_item"):
            comparisons.append(_ambiguous_candidate(metric_label, matching_candidates))
            continue

        candidate = matching_candidates[0]
        consumed_candidate_ids.add(id(candidate))
        comparisons.append(_matched_or_mismatched(metric_label, candidate))

    for metric_name in sorted(expected_nulls):
        if metric_name in metrics:
            continue
        metric_label = {
            "metric_name": metric_name,
            "column_role": "current_quarter",
            "line_item": None,
        }
        matching_candidates = _matching_candidates(candidates, metric_label)
        if matching_candidates:
            comparisons.append(_unexpected_candidate_for_expected_null(metric_name, matching_candidates))
            consumed_candidate_ids.update(id(candidate) for candidate in matching_candidates)
        else:
            comparisons.append(
                {
                    "metric_name": metric_name,
                    "status": "expected_null_respected",
                    "gold_value": None,
                    "candidate_value": None,
                }
            )

    for candidate in candidates:
        if id(candidate) not in consumed_candidate_ids:
            comparisons.append(_candidate_unlabelled(candidate))

    return comparisons


def _metric_label(metric_name: str, payload: Any, document_label: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        value = payload.get("value")
        column_role = str(payload.get("column_role") or "current_quarter")
        line_item = payload.get("line_item")
        tolerance_absolute = payload.get("tolerance_absolute")
        tolerance_relative = payload.get("tolerance_relative")
        source_evidence = payload.get("source_evidence")
    else:
        value = payload
        column_role = "current_quarter"
        line_item = None
        tolerance_absolute = None
        tolerance_relative = None
        source_evidence = None

    tolerances = document_label.get("tolerances") or {}
    metric_tolerance = tolerances.get(metric_name)
    if tolerance_relative is None and not isinstance(metric_tolerance, dict):
        tolerance_relative = metric_tolerance
    if isinstance(metric_tolerance, dict):
        tolerance_absolute = metric_tolerance.get("absolute", tolerance_absolute)
        tolerance_relative = metric_tolerance.get("relative", tolerance_relative)

    return {
        "metric_name": metric_name,
        "value": _decimal(value),
        "column_role": column_role,
        "line_item": str(line_item) if line_item else None,
        "tolerance_absolute": _decimal(tolerance_absolute or 0),
        "tolerance_relative": _decimal(tolerance_relative or 0),
        "source_evidence": source_evidence,
    }


def _matching_candidates(
    candidates: list[dict[str, Any]],
    metric_label: dict[str, Any],
) -> list[dict[str, Any]]:
    matches = [
        candidate
        for candidate in candidates
        if candidate.get("metric_name") == metric_label["metric_name"]
        and candidate.get("column_role") == metric_label["column_role"]
    ]
    line_item = metric_label.get("line_item")
    if line_item:
        matches = [
            candidate
            for candidate in matches
            if (candidate.get("evidence") or {}).get("line_item") == line_item
        ]
    return matches


def _matched_or_mismatched(
    metric_label: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    gold_value = metric_label["value"]
    candidate_value = _normalized_candidate_value(candidate)
    allowed_delta = max(
        metric_label["tolerance_absolute"],
        abs(gold_value) * metric_label["tolerance_relative"],
    )
    actual_delta = abs(candidate_value - gold_value)
    status = "match" if actual_delta <= allowed_delta else "mismatch"
    comparison = {
        "metric_name": metric_label["metric_name"],
        "status": status,
        "gold_value": _json_decimal(gold_value),
        "candidate_value": _json_decimal(candidate_value),
        "raw_candidate_value": candidate.get("value"),
        "candidate_scale": candidate.get("scale"),
        "tolerance_absolute": _json_decimal(metric_label["tolerance_absolute"]),
        "tolerance_relative": _json_decimal(metric_label["tolerance_relative"]),
        "allowed_delta": _json_decimal(allowed_delta),
        "actual_delta": _json_decimal(actual_delta),
        "label_source_evidence": metric_label.get("source_evidence"),
        "candidate": candidate,
    }
    if status == "mismatch":
        comparison["failure_reason"] = "candidate value does not match labelled value within tolerance"
    return comparison


def _candidate_missing(metric_label: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_name": metric_label["metric_name"],
        "status": "candidate_missing",
        "gold_value": _json_decimal(metric_label["value"]),
        "candidate_value": None,
        "label_source_evidence": metric_label.get("source_evidence"),
        "failure_reason": "DATA_MISSING: labelled metric has no matching current_quarter candidate",
    }


def _ambiguous_candidate(
    metric_label: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "metric_name": metric_label["metric_name"],
        "status": "ambiguous_candidate",
        "gold_value": _json_decimal(metric_label["value"]),
        "candidate_value": None,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "failure_reason": "multiple candidates match labelled metric; label requires line_item evidence binding",
    }


def _unexpected_candidate_for_expected_null(
    metric_name: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "metric_name": metric_name,
        "status": "unexpected_candidate_for_expected_null",
        "gold_value": None,
        "candidate_value": [_json_decimal(_normalized_candidate_value(candidate)) for candidate in candidates],
        "candidates": candidates,
        "failure_reason": "candidate produced for metric labelled expected null",
    }


def _candidate_unlabelled(
    candidate: dict[str, Any],
    *,
    reason: str = "candidate metric is not labelled",
) -> dict[str, Any]:
    return {
        "metric_name": candidate.get("metric_name"),
        "status": "candidate_unlabelled",
        "gold_value": None,
        "candidate_value": _json_decimal(_normalized_candidate_value(candidate)),
        "failure_reason": reason,
        "candidate": candidate,
    }


def _document_status(comparisons: list[dict[str, Any]]) -> str:
    statuses = {comparison["status"] for comparison in comparisons}
    if not comparisons or statuses <= {"candidate_unlabelled"}:
        return "UNSCORED"
    if statuses & {
        "mismatch",
        "candidate_missing",
        "unexpected_candidate_for_expected_null",
        "ambiguous_candidate",
    }:
        return "FAIL"
    return "PASS"


def _summarize_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "documents_scored": len(documents),
        "document_pass": 0,
        "document_fail": 0,
        "document_unscored": 0,
        "candidate_count": 0,
        "current_quarter_candidate_count": 0,
        "labelled_metric_count": 0,
        "labelled_metrics_with_candidate": 0,
        "trusted_metric_count": 0,
    }
    status_counts: dict[str, int] = {}
    for document in documents:
        status = str(document.get("status"))
        if status == "PASS":
            summary["document_pass"] += 1
        elif status == "FAIL":
            summary["document_fail"] += 1
        else:
            summary["document_unscored"] += 1
        summary["candidate_count"] += int(document.get("candidate_count") or 0)
        summary["current_quarter_candidate_count"] += int(
            document.get("current_quarter_candidate_count") or 0
        )
        for comparison in document.get("comparisons") or []:
            comparison_status = str(comparison.get("status"))
            status_counts[comparison_status] = status_counts.get(comparison_status, 0) + 1

    summary.update(status_counts)
    labelled_metric_count = (
        status_counts.get("match", 0)
        + status_counts.get("mismatch", 0)
        + status_counts.get("candidate_missing", 0)
        + status_counts.get("ambiguous_candidate", 0)
    )
    labelled_metrics_with_candidate = (
        status_counts.get("match", 0)
        + status_counts.get("mismatch", 0)
        + status_counts.get("ambiguous_candidate", 0)
    )
    summary["labelled_metric_count"] = labelled_metric_count
    summary["labelled_metrics_with_candidate"] = labelled_metrics_with_candidate
    summary["trusted_metric_count"] = status_counts.get("match", 0)
    summary["labelled_metric_coverage"] = _ratio(
        labelled_metrics_with_candidate,
        labelled_metric_count,
    )
    summary["exact_match_rate"] = _ratio(
        status_counts.get("match", 0),
        labelled_metrics_with_candidate,
    )
    return summary


def _summarize_comparisons(comparisons: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for comparison in comparisons:
        status = str(comparison["status"])
        summary[status] = summary.get(status, 0) + 1
    return summary


def _load_labels(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    label_schema = str(payload.get("label_schema") or LABEL_SCHEMA)
    documents_payload = payload.get("documents")
    if not isinstance(documents_payload, list):
        raise ValueError("labels.documents must be a list")
    documents_by_id: dict[str, dict[str, Any]] = {}
    for document in documents_payload:
        document_id = str(document.get("document_id") or "")
        if not document_id:
            raise ValueError("label document is missing document_id")
        documents_by_id[document_id] = document
    return {"label_schema": label_schema, "documents_by_id": documents_by_id}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized_candidate_value(candidate: dict[str, Any]) -> Decimal:
    scale = str(candidate.get("scale") or "").lower()
    multiplier = _SCALE_MULTIPLIERS.get(scale, Decimal("1"))
    return _decimal(candidate["value"]) * multiplier


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal value: {value!r}") from exc


def _json_decimal(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)
