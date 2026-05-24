"""Read-only Appendix 5B candidate artifact generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from app.services.asx_appendix5b_parser import parse_appendix5b_tables


APPENDIX5B_CANDIDATE_METRICS = {
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "cash_end",
    "capex",
}

_SCALE_MULTIPLIERS = {
    None: Decimal("1"),
    "": Decimal("1"),
    "ones": Decimal("1"),
    "thousands": Decimal("1000"),
    "millions": Decimal("1000000"),
    "billions": Decimal("1000000000"),
}


@dataclass(frozen=True)
class ManifestTable:
    page_number: int
    caption: str
    rows: list[list[str]]
    headers: list[str]


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")


def build_artifact_from_manifest(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    documents_payload = manifest.get("documents")
    if not isinstance(documents_payload, list):
        raise ValueError("manifest.documents must be a list")

    documents = [
        _build_document_artifact(document, repo_root=repo_root)
        for document in documents_payload
    ]
    summary = _summarize_documents(documents)
    return {
        "artifact_type": "appendix5b_candidate_eval_v1",
        "run_id": str(manifest.get("run_id") or "appendix5b_candidate_eval"),
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "parser_method": "appendix5b_deterministic_v1",
        "canonical_write": False,
        "runtime": "read_only_manifest",
        "document_count": len(documents),
        "summary": summary,
        "documents": documents,
    }


def run_manifest_to_artifact(
    *,
    manifest_path: Path,
    output_path: Path,
    repo_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    artifact = build_artifact_from_manifest(
        load_manifest(manifest_path),
        repo_root=repo_root,
        generated_at=generated_at,
    )
    write_artifact(output_path, artifact)
    return artifact


def _build_document_artifact(document: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    document_id = str(document.get("document_id") or "")
    if not document_id:
        raise ValueError("manifest document is missing document_id")

    tables = [_manifest_table(table) for table in document.get("tables", [])]
    parse_result = parse_appendix5b_tables(tables)
    gold = _load_gold(document, repo_root=repo_root)

    comparisons = _compare_candidates_to_gold(parse_result.to_dict(), gold)
    return {
        "document_id": document_id,
        "ticker": document.get("ticker") or gold.get("ticker"),
        "period_end": document.get("period_end") or gold.get("period_end"),
        "period_type": document.get("period_type") or gold.get("period_type"),
        "gold_fixture_path": document.get("gold_fixture_path"),
        "document_type": parse_result.document_type,
        "parse_status": parse_result.status,
        "tables_seen": parse_result.tables_seen,
        "candidate_count": len(parse_result.candidates),
        "missing_count": len(parse_result.missing),
        "candidates": parse_result.to_dict()["candidates"],
        "missing": parse_result.to_dict()["missing"],
        "comparisons": comparisons,
        "summary": _summarize_comparisons(comparisons),
    }


def _manifest_table(payload: dict[str, Any]) -> ManifestTable:
    rows = payload.get("rows") or []
    headers = payload.get("headers") or (rows[0] if rows else [])
    return ManifestTable(
        page_number=int(payload.get("page_number") or 0),
        caption=str(payload.get("caption") or ""),
        rows=[[str(cell or "") for cell in row] for row in rows],
        headers=[str(cell or "") for cell in headers],
    )


def _load_gold(document: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    fixture_path = document.get("gold_fixture_path")
    if fixture_path:
        path = Path(str(fixture_path))
        if not path.is_absolute():
            path = repo_root / path
        return json.loads(path.read_text(encoding="utf-8"))
    gold = document.get("gold")
    if isinstance(gold, dict):
        return gold
    return {"metrics": {}, "expected_nulls": []}


def _compare_candidates_to_gold(
    parse_payload: dict[str, Any],
    gold: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates_by_metric = {
        candidate["metric_name"]: candidate
        for candidate in parse_payload.get("candidates", [])
        if candidate.get("column_role") == "current_quarter"
    }
    gold_metrics = {
        metric_name: value
        for metric_name, value in (gold.get("metrics") or {}).items()
        if metric_name in APPENDIX5B_CANDIDATE_METRICS
    }
    expected_nulls = set(gold.get("expected_nulls") or [])
    tolerances = gold.get("tolerances") or {}

    comparisons: list[dict[str, Any]] = []
    for metric_name in sorted(APPENDIX5B_CANDIDATE_METRICS):
        candidate = candidates_by_metric.get(metric_name)
        has_gold = metric_name in gold_metrics
        expected_null = metric_name in expected_nulls

        if has_gold and candidate is not None:
            comparisons.append(_matched_or_mismatched(metric_name, candidate, gold, tolerances))
        elif has_gold:
            comparisons.append(
                {
                    "metric_name": metric_name,
                    "status": "candidate_missing",
                    "gold_value": _json_number(gold_metrics[metric_name]),
                    "candidate_value": None,
                    "failure_reason": "DATA_MISSING: parser did not produce current_quarter candidate for labelled metric",
                }
            )
        elif candidate is not None and expected_null:
            comparisons.append(
                {
                    "metric_name": metric_name,
                    "status": "unexpected_candidate_for_expected_null",
                    "gold_value": None,
                    "candidate_value": _json_decimal(_normalized_candidate_value(candidate)),
                    "failure_reason": "candidate produced for metric labelled expected null",
                    "candidate": candidate,
                }
            )
        elif candidate is not None:
            comparisons.append(
                {
                    "metric_name": metric_name,
                    "status": "candidate_unlabelled",
                    "gold_value": None,
                    "candidate_value": _json_decimal(_normalized_candidate_value(candidate)),
                    "failure_reason": "candidate metric is not labelled in gold fixture",
                    "candidate": candidate,
                }
            )
        elif expected_null:
            comparisons.append(
                {
                    "metric_name": metric_name,
                    "status": "expected_null_respected",
                    "gold_value": None,
                    "candidate_value": None,
                }
            )
    return comparisons


def _matched_or_mismatched(
    metric_name: str,
    candidate: dict[str, Any],
    gold: dict[str, Any],
    tolerances: dict[str, Any],
) -> dict[str, Any]:
    gold_value = _decimal(gold["metrics"][metric_name])
    candidate_value = _normalized_candidate_value(candidate)
    tolerance = _decimal(tolerances.get(metric_name, 0))
    allowed_delta = abs(gold_value) * tolerance
    actual_delta = abs(candidate_value - gold_value)
    status = "match" if actual_delta <= allowed_delta else "mismatch"
    payload = {
        "metric_name": metric_name,
        "status": status,
        "gold_value": _json_decimal(gold_value),
        "candidate_value": _json_decimal(candidate_value),
        "raw_candidate_value": candidate.get("value"),
        "candidate_scale": candidate.get("scale"),
        "tolerance": _json_decimal(tolerance),
        "allowed_delta": _json_decimal(allowed_delta),
        "actual_delta": _json_decimal(actual_delta),
        "candidate": candidate,
    }
    if status != "match":
        payload["failure_reason"] = "candidate value does not match gold tolerance"
    return payload


def _normalized_candidate_value(candidate: dict[str, Any]) -> Decimal:
    scale = str(candidate.get("scale") or "").lower()
    multiplier = _SCALE_MULTIPLIERS.get(scale)
    if multiplier is None:
        multiplier = Decimal("1")
    return _decimal(candidate["value"]) * multiplier


def _summarize_documents(documents: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "documents_parsed": 0,
        "documents_not_applicable": 0,
        "candidate_count": 0,
        "missing_count": 0,
    }
    status_counts: dict[str, int] = {}
    for document in documents:
        if document["parse_status"] == "parsed":
            totals["documents_parsed"] += 1
        if document["parse_status"] == "not_applicable":
            totals["documents_not_applicable"] += 1
        totals["candidate_count"] += int(document["candidate_count"])
        totals["missing_count"] += int(document["missing_count"])
        for status, count in document["summary"].items():
            status_counts[status] = status_counts.get(status, 0) + int(count)
    totals.update(status_counts)
    return totals


def _summarize_comparisons(comparisons: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for comparison in comparisons:
        status = str(comparison["status"])
        summary[status] = summary.get(status, 0) + 1
    return summary


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal value: {value!r}") from exc


def _json_number(value: Any) -> int | float:
    decimal = _decimal(value)
    return _json_decimal(decimal)


def _json_decimal(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)
