"""Import confirmed Appendix 5B labels from eval fixtures into scorer format."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from app.services.extraction_gold_eval_scorecard import (
    build_confirmed_metric_coverage_scorecard,
)


LABEL_SCHEMA = "appendix5b_candidate_labels_v1"
IMPORT_REPORT_TYPE = "appendix5b_confirmed_label_import_report_v1"

APPENDIX5B_METRIC_ALIASES = {
    "operating_cash_flow": "operating_cf",
    "operating_cf": "operating_cf",
    "investing_cf": "investing_cf",
    "financing_cf": "financing_cf",
    "cash_end": "cash_end",
    "capex": "capex",
}

_PREFERRED_LINE_ITEMS_BY_METRIC = {
    "cash_end": ("5.5",),
}

_SCALE_MULTIPLIERS = {
    None: Decimal("1"),
    "": Decimal("1"),
    "ones": Decimal("1"),
    "thousands": Decimal("1000"),
    "millions": Decimal("1000000"),
    "billions": Decimal("1000000000"),
}


def import_confirmed_appendix5b_labels(
    *,
    artifact_paths: list[Path],
    fixtures_dir: Path,
    output_labels_path: Path | None = None,
    output_report_path: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Import confirmed fixture labels only when a candidate artifact matches.

    Matching is intentionally strict: document_id, period, metric, current-quarter
    column, and candidate value must agree. Duplicate candidate metrics are not
    imported unless there is a single matching line item.
    """

    fixtures = _load_fixtures(fixtures_dir)
    scorecard = build_confirmed_metric_coverage_scorecard(fixtures_dir)
    expectations = [
        expectation
        for expectation in scorecard.get("metric_expectations") or []
        if isinstance(expectation, dict)
    ]
    expectations_by_document = _confirmed_appendix5b_expectations_by_document(expectations)

    import_documents: list[dict[str, Any]] = []
    report_documents: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        artifact = _load_json(artifact_path)
        for document in artifact.get("documents") or []:
            import_document, report_document = _import_document(
                document,
                artifact_path=artifact_path,
                fixture=fixtures.get(str(document.get("document_id") or "")),
                expectations=expectations_by_document.get(
                    str(document.get("document_id") or ""), []
                ),
            )
            if import_document is not None:
                import_documents.append(import_document)
            report_documents.append(report_document)

    labels = {
        "label_schema": LABEL_SCHEMA,
        "label_scope": "confirmed_eval_fixture_import_report_local",
        "canonical_write": False,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "fixtures_dir": str(fixtures_dir),
        "artifact_paths": [str(path) for path in artifact_paths],
        "documents": import_documents,
    }
    report = {
        "artifact_type": IMPORT_REPORT_TYPE,
        "generated_at": labels["generated_at"],
        "canonical_write": False,
        "fixtures_dir": str(fixtures_dir),
        "artifact_paths": [str(path) for path in artifact_paths],
        "summary": _summarize_report_documents(report_documents),
        "labels_path": str(output_labels_path) if output_labels_path else None,
        "documents": report_documents,
    }
    if output_labels_path is not None:
        _write_json(output_labels_path, labels)
    if output_report_path is not None:
        _write_json(output_report_path, report)
    return {"labels": labels, "report": report}


def _import_document(
    document: dict[str, Any],
    *,
    artifact_path: Path,
    fixture: dict[str, Any] | None,
    expectations: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    document_id = str(document.get("document_id") or "")
    current_candidates = [
        candidate
        for candidate in document.get("candidates") or []
        if isinstance(candidate, dict)
        and str(candidate.get("column_role") or "") == "current_quarter"
    ]
    report_rows: list[dict[str, Any]] = []
    imported_metrics: dict[str, Any] = {}
    expected_nulls: list[str] = []

    if fixture is None:
        return None, {
            "artifact_path": str(artifact_path),
            "document_id": document_id,
            "ticker": document.get("ticker"),
            "period_end": document.get("period_end"),
            "period_type": document.get("period_type"),
            "status": "NO_MATCHING_FIXTURE",
            "reason": "DATA_MISSING: no eval fixture with matching document_id",
            "candidate_count": len(current_candidates),
            "imported_metric_count": 0,
            "rows": [],
        }

    context_mismatches = _context_mismatches(document, fixture)
    if context_mismatches:
        return None, {
            "artifact_path": str(artifact_path),
            "document_id": document_id,
            "ticker": document.get("ticker"),
            "period_end": document.get("period_end"),
            "period_type": document.get("period_type"),
            "status": "CONTEXT_MISMATCH",
            "reason": "DATA_MISSING: candidate artifact context does not match fixture",
            "context_mismatches": context_mismatches,
            "candidate_count": len(current_candidates),
            "imported_metric_count": 0,
            "rows": [],
        }

    for expectation in expectations:
        metric_name = APPENDIX5B_METRIC_ALIASES.get(str(expectation.get("metric_name") or ""))
        if not metric_name:
            continue
        if expectation.get("expectation_type") == "expected_null":
            expected_nulls.append(metric_name)
            report_rows.append(
                {
                    "metric_name": metric_name,
                    "status": "expected_null_imported",
                    "source_fixture_path": expectation.get("fixture_path"),
                }
            )
            continue
        row = _import_metric(
            metric_name,
            expectation,
            candidates=current_candidates,
        )
        report_rows.append(row)
        if row["status"] == "imported":
            imported_metrics[metric_name] = row["label"]

    if not imported_metrics and not expected_nulls:
        import_document = None
    else:
        import_document = {
            "document_id": document_id,
            "ticker": document.get("ticker") or fixture.get("ticker"),
            "period_end": document.get("period_end"),
            "period_type": document.get("period_type"),
            "metrics": imported_metrics,
            "expected_nulls": sorted(set(expected_nulls)),
        }

    return import_document, {
        "artifact_path": str(artifact_path),
        "document_id": document_id,
        "ticker": document.get("ticker") or fixture.get("ticker"),
        "period_end": document.get("period_end"),
        "period_type": document.get("period_type"),
        "status": "IMPORTED" if imported_metrics or expected_nulls else "NO_IMPORTS",
        "candidate_count": len(current_candidates),
        "imported_metric_count": len(imported_metrics),
        "expected_null_count": len(set(expected_nulls)),
        "rows": report_rows,
    }


def _import_metric(
    metric_name: str,
    expectation: dict[str, Any],
    *,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    metric_candidates = [
        candidate
        for candidate in candidates
        if APPENDIX5B_METRIC_ALIASES.get(str(candidate.get("metric_name") or ""))
        == metric_name
    ]
    if not metric_candidates:
        return {
            "metric_name": metric_name,
            "status": "candidate_missing",
            "reason": "DATA_MISSING: no current_quarter candidate for confirmed fixture metric",
            "source_fixture_path": expectation.get("fixture_path"),
        }
    matching_value_candidates = [
        candidate
        for candidate in metric_candidates
        if _values_match(candidate, expectation)
    ]
    if not matching_value_candidates:
        return {
            "metric_name": metric_name,
            "status": "candidate_value_mismatch",
            "reason": "candidate value does not match confirmed fixture value within tolerance",
            "source_fixture_path": expectation.get("fixture_path"),
            "candidate_count": len(metric_candidates),
        }
    if len(matching_value_candidates) > 1:
        preferred_candidate = _preferred_matching_candidate(metric_name, matching_value_candidates)
        if preferred_candidate is not None:
            return _import_candidate(metric_name, expectation, preferred_candidate)
        return {
            "metric_name": metric_name,
            "status": "ambiguous_candidate",
            "reason": "multiple matching candidates require manual line-item selection",
            "source_fixture_path": expectation.get("fixture_path"),
            "candidate_count": len(matching_value_candidates),
            "line_items": sorted(
                {
                    str((candidate.get("evidence") or {}).get("line_item") or "")
                    for candidate in matching_value_candidates
                }
            ),
        }

    candidate = matching_value_candidates[0]
    return _import_candidate(metric_name, expectation, candidate)


def _preferred_matching_candidate(
    metric_name: str,
    matching_value_candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    preferred_lines = _PREFERRED_LINE_ITEMS_BY_METRIC.get(metric_name)
    if not preferred_lines:
        return None
    preferred = [
        candidate
        for candidate in matching_value_candidates
        if str((candidate.get("evidence") or {}).get("line_item") or "") in preferred_lines
    ]
    if len(preferred) != 1:
        return None
    return preferred[0]


def _import_candidate(
    metric_name: str,
    expectation: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    evidence = candidate.get("evidence") or {}
    label = {
        "value": _json_decimal(_decimal(expectation["expected_value"])),
        "line_item": evidence.get("line_item"),
        "column_role": "current_quarter",
        "tolerance_relative": expectation.get("tolerance", 0.0),
        "source_evidence": {
            "source_type": "confirmed_eval_fixture",
            "fixture_path": expectation.get("fixture_path"),
            "fixture_source_status": expectation.get("source_status"),
            "source_span": evidence.get("source_span"),
            "page": evidence.get("page"),
            "table_index": evidence.get("table_index"),
            "row_index": evidence.get("row_index"),
            "column_index": evidence.get("column_index"),
            "row_label": evidence.get("row_label"),
            "column_label": evidence.get("column_label"),
            "line_item": evidence.get("line_item"),
        },
        "review_status": "confirmed_source_evidenced",
    }
    return {
        "metric_name": metric_name,
        "status": "imported",
        "source_fixture_path": expectation.get("fixture_path"),
        "candidate_source_span": evidence.get("source_span"),
        "candidate_line_item": evidence.get("line_item"),
        "label": label,
    }


def _confirmed_appendix5b_expectations_by_document(
    expectations: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for expectation in expectations:
        if expectation.get("support_status") != "scored":
            continue
        metric_name = str(expectation.get("metric_name") or "")
        if metric_name not in APPENDIX5B_METRIC_ALIASES:
            continue
        document_id = str(expectation.get("document_id") or "")
        output.setdefault(document_id, []).append(expectation)
    return output


def _context_mismatches(document: dict[str, Any], fixture: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key in ("period_end", "period_type"):
        if str(document.get(key) or "") != str(fixture.get(key) or ""):
            mismatches.append(key)
    if str(document.get("ticker") or "") and str(fixture.get("ticker") or ""):
        if str(document.get("ticker")) != str(fixture.get("ticker")):
            mismatches.append("ticker")
    return mismatches


def _values_match(candidate: dict[str, Any], expectation: dict[str, Any]) -> bool:
    expected = _decimal(expectation["expected_value"])
    actual = _normalized_candidate_value(candidate)
    tolerance = _decimal(expectation.get("tolerance", 0.0))
    allowed_delta = abs(expected) * tolerance
    return abs(actual - expected) <= allowed_delta


def _load_fixtures(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}
    for path in sorted(fixtures_dir.glob("*.json")):
        payload = _load_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"fixture must be a JSON object: {path}")
        document_id = str(payload.get("document_id") or "")
        if document_id:
            payload = dict(payload)
            payload["_fixture_path"] = str(path)
            fixtures[document_id] = payload
    return fixtures


def _summarize_report_documents(documents: list[dict[str, Any]]) -> dict[str, int]:
    imported_documents = sum(1 for document in documents if document.get("status") == "IMPORTED")
    rows = [
        row
        for document in documents
        for row in document.get("rows") or []
        if isinstance(row, dict)
    ]
    return {
        "documents_seen": len(documents),
        "documents_imported": imported_documents,
        "labels_imported": sum(int(document.get("imported_metric_count") or 0) for document in documents),
        "expected_nulls_imported": sum(int(document.get("expected_null_count") or 0) for document in documents),
        "candidate_missing": sum(1 for row in rows if row.get("status") == "candidate_missing"),
        "candidate_value_mismatch": sum(1 for row in rows if row.get("status") == "candidate_value_mismatch"),
        "ambiguous_candidate": sum(1 for row in rows if row.get("status") == "ambiguous_candidate"),
        "no_matching_fixture": sum(1 for document in documents if document.get("status") == "NO_MATCHING_FIXTURE"),
        "context_mismatch": sum(1 for document in documents if document.get("status") == "CONTEXT_MISMATCH"),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
