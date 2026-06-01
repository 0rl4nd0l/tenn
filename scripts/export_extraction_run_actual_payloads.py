#!/usr/bin/env python3
"""Export selected extraction run payloads for report-local scorecard review.

This script is intentionally read-only. It converts explicit
``extraction_runs.structured_json`` rows into the actual-payload map accepted by
``scripts/extraction_gold_eval_scorecard.py --profile confirmed_metric_payload``.
It does not run extraction, create gold labels, or authorize canonical writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_ALLOWED_STATUSES = ("ok", "ok_low_confidence")
SUMMARY_ARTIFACT_TYPE = "extraction_run_actual_payload_export_summary_v1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read selected extraction_runs rows from SQLite and export an "
            "actual-payload map for report-local scorecard review."
        )
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help=(
            "SQLite DB path. Defaults to DATABASE_URL when it is a sqlite URL, "
            "else /data/fe_local.db."
        ),
    )
    parser.add_argument(
        "--run-id",
        action="append",
        default=[],
        help="Extraction run id to export. May be repeated.",
    )
    parser.add_argument(
        "--document-id",
        action="append",
        default=[],
        help=(
            "Document id to export using the latest matching allowed-status "
            "run. May be repeated."
        ),
    )
    parser.add_argument(
        "--allowed-status",
        action="append",
        default=[],
        help=(
            "Accepted extraction status. Defaults to ok and ok_low_confidence. "
            "Repeat to set a custom allowlist."
        ),
    )
    parser.add_argument(
        "--key",
        choices=("document_id", "run_id"),
        default="document_id",
        help="Top-level actual-payload map key.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        required=True,
        help="Output actual-payload map path.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional export summary path.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for output files.",
    )
    return parser.parse_args()


def _db_path_from_args(raw_path: Path | None) -> Path:
    if raw_path is not None:
        return raw_path

    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if raw_url.startswith("sqlite:///"):
        parsed = urlparse(raw_url)
        if parsed.path:
            return Path(parsed.path)

    return Path("/data/fe_local.db")


def _normalize_id(raw: str) -> str:
    return str(raw or "").strip().lower().replace("-", "")


def _display_id(raw: Any) -> str:
    value = str(raw or "").strip()
    normalized = _normalize_id(value)
    if len(normalized) == 32:
        try:
            return str(uuid.UUID(hex=normalized))
        except ValueError:
            return value
    return value


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    uri = f"file:{db_path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_rows(
    conn: sqlite3.Connection,
    *,
    run_ids: Iterable[str],
    document_ids: Iterable[str],
    allowed_statuses: set[str],
) -> list[sqlite3.Row]:
    rows: list[sqlite3.Row] = []
    seen_runs: set[str] = set()

    normalized_run_ids = [_normalize_id(run_id) for run_id in run_ids if run_id]
    if normalized_run_ids:
        placeholders = ",".join("?" for _ in normalized_run_ids)
        query = f"""
            SELECT run_id, document_id, extractor_version, model_name, prompt_hash,
                   status, confidence_overall, error, structured_json, created_at
            FROM extraction_runs
            WHERE replace(lower(cast(run_id AS text)), '-', '') IN ({placeholders})
            ORDER BY created_at ASC
        """
        for row in conn.execute(query, normalized_run_ids):
            rows.append(row)
            seen_runs.add(_normalize_id(str(row["run_id"])))

    normalized_document_ids = [
        _normalize_id(document_id) for document_id in document_ids if document_id
    ]
    if normalized_document_ids:
        placeholders = ",".join("?" for _ in normalized_document_ids)
        status_placeholders = ",".join("?" for _ in allowed_statuses)
        query = f"""
            SELECT run_id, document_id, extractor_version, model_name, prompt_hash,
                   status, confidence_overall, error, structured_json, created_at
            FROM extraction_runs
            WHERE replace(lower(cast(document_id AS text)), '-', '') IN ({placeholders})
              AND lower(status) IN ({status_placeholders})
            ORDER BY document_id ASC, created_at DESC
        """
        params = normalized_document_ids + sorted(allowed_statuses)
        latest_by_document: dict[str, sqlite3.Row] = {}
        for row in conn.execute(query, params):
            document_key = _normalize_id(str(row["document_id"]))
            latest_by_document.setdefault(document_key, row)
        for row in latest_by_document.values():
            run_key = _normalize_id(str(row["run_id"]))
            if run_key not in seen_runs:
                rows.append(row)
                seen_runs.add(run_key)

    return rows


def _parse_structured_json(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row["structured_json"]
    if isinstance(raw, Mapping):
        payload = dict(raw)
    elif isinstance(raw, str) and raw.strip():
        payload = json.loads(raw)
    else:
        raise ValueError("structured_json is empty")
    if not isinstance(payload, dict):
        raise ValueError("structured_json must be a JSON object")
    return payload


def _metrics_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping):
        raise ValueError("structured_json.metrics must be a JSON object")
    return dict(metrics)


def _truthy(raw: Any) -> bool:
    if raw is None:
        return False
    if isinstance(raw, str):
        value = raw.strip()
        return bool(value) and value.lower() not in {"unknown", "n/a", "none"}
    if isinstance(raw, Mapping) or isinstance(raw, list):
        return bool(raw)
    return True


def _metric_evidence(payload: Mapping[str, Any], metrics: Mapping[str, Any]) -> dict[str, Any]:
    evidence: dict[str, dict[str, Any]] = {}

    def add(metric: str, field: str, value: Any) -> None:
        if not _truthy(value):
            return
        evidence.setdefault(metric, {})[field] = value

    for field in ("evidence", "metric_evidence", "provenance"):
        raw_map = payload.get(field)
        if not isinstance(raw_map, Mapping):
            continue
        for metric in metrics:
            add(metric, field, raw_map.get(metric))

    row_refs = payload.get("row_refs")
    if isinstance(row_refs, Mapping):
        for metric in metrics:
            add(metric, "row_ref", row_refs.get(metric))

    source_snippets = payload.get("source_snippets")
    if isinstance(source_snippets, Mapping):
        for metric in metrics:
            add(metric, "source_snippet", source_snippets.get(metric))

    return {metric: value for metric, value in evidence.items() if value}


def _payload_for_row(row: Mapping[str, Any]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    structured = _parse_structured_json(row)
    metrics = _metrics_from_payload(structured)
    run_id = _display_id(row["run_id"])
    document_id = _display_id(row["document_id"])
    evidence = _metric_evidence(structured, metrics)
    payload = {
        "period_type": structured.get("period_type"),
        "period_end": structured.get("period_end"),
        "currency": structured.get("currency"),
        "scale": structured.get("scale"),
        "metrics": metrics,
        "evidence": evidence,
        "provenance": structured.get("provenance") or {},
        "extraction_run_provenance": {
            "run_id": run_id,
            "document_id": document_id,
            "status": row["status"],
            "extractor_version": row["extractor_version"],
            "model_name": row["model_name"],
            "prompt_hash": row["prompt_hash"],
            "confidence_overall": row["confidence_overall"],
            "created_at": row["created_at"],
            "source": "extraction_runs.structured_json",
            "actual_payload_only": True,
            "gold_label": False,
            "canonical_write_allowed": False,
            "broad_backfill_authorized": False,
        },
    }
    summary = {
        "run_id": run_id,
        "document_id": document_id,
        "status": row["status"],
        "metric_count": len(metrics),
        "non_null_metric_count": sum(value is not None for value in metrics.values()),
        "evidence_metric_count": len(evidence),
        "created_at": row["created_at"],
    }
    return run_id, document_id, payload, summary


def build_export(
    *,
    db_path: Path,
    run_ids: Iterable[str],
    document_ids: Iterable[str],
    allowed_statuses: Iterable[str],
    key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_allowed = {status.lower() for status in allowed_statuses if status}
    if not normalized_allowed:
        normalized_allowed = set(DEFAULT_ALLOWED_STATUSES)

    requested_run_ids = [item for item in run_ids if item]
    requested_document_ids = [item for item in document_ids if item]
    if not requested_run_ids and not requested_document_ids:
        raise ValueError("at least one --run-id or --document-id selector is required")

    with _connect_readonly(db_path) as conn:
        rows = _fetch_rows(
            conn,
            run_ids=requested_run_ids,
            document_ids=requested_document_ids,
            allowed_statuses=normalized_allowed,
        )

    rows_by_run = {_normalize_id(str(row["run_id"])): row for row in rows}
    missing_run_ids = [
        run_id
        for run_id in requested_run_ids
        if _normalize_id(run_id) not in rows_by_run
    ]
    rows_by_document = {_normalize_id(str(row["document_id"])): row for row in rows}
    missing_document_ids = [
        document_id
        for document_id in requested_document_ids
        if _normalize_id(document_id) not in rows_by_document
    ]

    exported: dict[str, Any] = {}
    selected_summaries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for row in rows:
        run_id = _display_id(row["run_id"])
        document_id = _display_id(row["document_id"])
        status = str(row["status"] or "").lower()
        if status not in normalized_allowed:
            errors.append(
                {
                    "run_id": run_id,
                    "document_id": document_id,
                    "error": f"status '{row['status']}' is not in allowed statuses",
                }
            )
            continue
        try:
            parsed_run_id, parsed_document_id, payload, summary = _payload_for_row(row)
        except Exception as exc:  # noqa: BLE001 - convert row parse errors to report errors.
            errors.append(
                {
                    "run_id": run_id,
                    "document_id": document_id,
                    "error": str(exc),
                }
            )
            continue
        export_key = parsed_document_id if key == "document_id" else parsed_run_id
        if export_key in exported:
            errors.append(
                {
                    "run_id": parsed_run_id,
                    "document_id": parsed_document_id,
                    "error": f"duplicate export key '{export_key}'",
                }
            )
            continue
        exported[export_key] = payload
        selected_summaries.append(summary)

    for run_id in missing_run_ids:
        errors.append({"run_id": run_id, "document_id": "", "error": "run not found"})
    for document_id in missing_document_ids:
        errors.append(
            {
                "run_id": "",
                "document_id": document_id,
                "error": "document has no matching allowed-status run",
            }
        )

    summary = {
        "artifact_type": SUMMARY_ARTIFACT_TYPE,
        "input_db_path": str(db_path),
        "selectors": {
            "run_ids": requested_run_ids,
            "document_ids": requested_document_ids,
            "key": key,
            "allowed_statuses": sorted(normalized_allowed),
        },
        "selected_run_count": len(rows),
        "exported_payload_count": len(exported),
        "selected_runs": selected_summaries,
        "errors": errors,
        "failed_closed": bool(errors),
        "boundaries": {
            "ran_extraction": False,
            "mutated_database": False,
            "mutated_canonical_truth": False,
            "created_gold_labels": False,
            "canonical_write_allowed": False,
            "broad_backfill_authorized": False,
            "actual_payload_only": True,
        },
    }
    return exported, summary


def _write_json(path: Path, payload: Mapping[str, Any], *, indent: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=indent, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    db_path = _db_path_from_args(args.db_path)
    try:
        actuals, summary = build_export(
            db_path=db_path,
            run_ids=args.run_id,
            document_ids=args.document_id,
            allowed_statuses=args.allowed_status or DEFAULT_ALLOWED_STATUSES,
            key=args.key,
        )
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 2

    if summary["errors"]:
        if args.summary_json is not None:
            _write_json(args.summary_json, summary, indent=args.indent)
        print(json.dumps(summary, indent=args.indent, sort_keys=True), file=sys.stderr)
        return 2

    _write_json(args.out_json, actuals, indent=args.indent)
    if args.summary_json is not None:
        _write_json(args.summary_json, summary, indent=args.indent)
    print(f"Wrote actual payload map: {args.out_json}")
    if args.summary_json is not None:
        print(f"Wrote export summary: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
