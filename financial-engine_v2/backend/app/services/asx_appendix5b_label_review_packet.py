"""Build manual-review packets from Appendix 5B candidate artifacts."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any


REVIEW_PACKET_TYPE = "appendix5b_label_review_packet_v1"
LABEL_TEMPLATE_SCHEMA = "appendix5b_candidate_label_review_template_v1"

_SCALE_MULTIPLIERS = {
    None: Decimal("1"),
    "": Decimal("1"),
    "ones": Decimal("1"),
    "thousands": Decimal("1000"),
    "millions": Decimal("1000000"),
    "billions": Decimal("1000000000"),
}

_CSV_COLUMNS = [
    "review_id",
    "document_id",
    "ticker",
    "period_end",
    "period_type",
    "metric_name",
    "column_role",
    "line_item",
    "candidate_value",
    "normalized_value",
    "scale",
    "currency",
    "page",
    "table_index",
    "row_index",
    "column_index",
    "row_label",
    "column_label",
    "source_span",
    "duplicate_count",
    "review_status",
]


def build_appendix5b_label_review_packet(
    *,
    artifact_paths: list[Path],
    output_json_path: Path | None = None,
    output_csv_path: Path | None = None,
    labels_template_path: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a review packet and optional CSV/template artifacts.

    Candidate values are intentionally marked `needs_confirmation`; this helper
    prepares manual-review inputs and must not be treated as production gold.
    """

    documents: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        artifact = _load_json(artifact_path)
        for document in artifact.get("documents") or []:
            documents.append(_review_document(document, artifact_path=artifact_path))

    packet = {
        "artifact_type": REVIEW_PACKET_TYPE,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "canonical_write": False,
        "review_scope": "manual_confirmation_required",
        "artifact_paths": [str(path) for path in artifact_paths],
        "summary": _summarize_documents(documents),
        "documents": documents,
    }

    if output_json_path is not None:
        _write_json(output_json_path, packet)
    if output_csv_path is not None:
        _write_csv(output_csv_path, packet)
    if labels_template_path is not None:
        _write_json(labels_template_path, build_labels_template(packet))
    return packet


def build_labels_template(packet: dict[str, Any]) -> dict[str, Any]:
    """Create a non-promotable label template from a review packet."""

    documents = []
    for document in packet.get("documents") or []:
        documents.append(
            {
                "document_id": document["document_id"],
                "ticker": document.get("ticker"),
                "period_end": document.get("period_end"),
                "period_type": document.get("period_type"),
                "metrics": {},
                "expected_nulls": [],
                "candidate_label_options": [
                    {
                        "metric_name": item["metric_name"],
                        "value": item["normalized_value"],
                        "line_item": item["line_item"],
                        "column_role": item["column_role"],
                        "review_status": "needs_confirmation",
                        "source_evidence": item["source_evidence"],
                        "review_id": item["review_id"],
                    }
                    for item in document.get("review_items") or []
                ],
            }
        )
    return {
        "label_schema": LABEL_TEMPLATE_SCHEMA,
        "label_scope": "manual_confirmation_required_not_production_gold",
        "canonical_write": False,
        "instructions": (
            "Review candidate_label_options against the source PDF/table evidence. "
            "Only move confirmed values into metrics after human confirmation."
        ),
        "documents": documents,
    }


def _review_document(document: dict[str, Any], *, artifact_path: Path) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in document.get("candidates") or []
        if isinstance(candidate, dict)
        and str(candidate.get("column_role") or "") == "current_quarter"
    ]
    duplicate_counts = _duplicate_counts(candidates)
    review_items = [
        _review_item(
            candidate,
            document=document,
            artifact_path=artifact_path,
            duplicate_count=duplicate_counts[
                (
                    str(candidate.get("metric_name") or ""),
                    str(candidate.get("column_role") or ""),
                )
            ],
        )
        for candidate in candidates
    ]
    return {
        "artifact_path": str(artifact_path),
        "document_id": document.get("document_id"),
        "ticker": document.get("ticker"),
        "period_end": document.get("period_end"),
        "period_type": document.get("period_type"),
        "document_type": document.get("document_type"),
        "parse_status": document.get("parse_status"),
        "review_item_count": len(review_items),
        "duplicate_candidate_groups": sum(
            1 for count in duplicate_counts.values() if count > 1
        ),
        "review_items": review_items,
    }


def _review_item(
    candidate: dict[str, Any],
    *,
    document: dict[str, Any],
    artifact_path: Path,
    duplicate_count: int,
) -> dict[str, Any]:
    evidence = candidate.get("evidence") or {}
    source_span = str(evidence.get("source_span") or "")
    review_id = ":".join(
        [
            str(document.get("document_id") or ""),
            str(candidate.get("metric_name") or ""),
            str(evidence.get("line_item") or ""),
            str(candidate.get("column_role") or ""),
            source_span,
        ]
    )
    return {
        "review_id": review_id,
        "review_status": "needs_confirmation",
        "trust_status": "unconfirmed_candidate",
        "artifact_path": str(artifact_path),
        "document_id": document.get("document_id"),
        "ticker": document.get("ticker"),
        "period_end": document.get("period_end"),
        "period_type": document.get("period_type"),
        "metric_name": candidate.get("metric_name"),
        "candidate_value": candidate.get("value"),
        "normalized_value": _json_decimal(_normalized_candidate_value(candidate)),
        "raw_value": candidate.get("raw_value"),
        "unit": candidate.get("unit"),
        "currency": candidate.get("currency"),
        "scale": candidate.get("scale"),
        "column_role": candidate.get("column_role"),
        "period_label": candidate.get("period_label"),
        "line_item": evidence.get("line_item"),
        "page": evidence.get("page"),
        "table_index": evidence.get("table_index"),
        "row_index": evidence.get("row_index"),
        "column_index": evidence.get("column_index"),
        "row_label": evidence.get("row_label"),
        "column_label": evidence.get("column_label"),
        "source_span": source_span,
        "source_evidence": {
            "artifact_path": str(artifact_path),
            "source_span": source_span,
            "page": evidence.get("page"),
            "table_index": evidence.get("table_index"),
            "row_index": evidence.get("row_index"),
            "column_index": evidence.get("column_index"),
            "row_label": evidence.get("row_label"),
            "column_label": evidence.get("column_label"),
            "line_item": evidence.get("line_item"),
        },
        "duplicate_count": duplicate_count,
        "manual_confirmation_required": True,
    }


def _duplicate_counts(candidates: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for candidate in candidates:
        key = (
            str(candidate.get("metric_name") or ""),
            str(candidate.get("column_role") or ""),
        )
        counts[key] = counts.get(key, 0) + 1
    return counts


def _summarize_documents(documents: list[dict[str, Any]]) -> dict[str, int]:
    review_item_count = sum(int(document["review_item_count"]) for document in documents)
    duplicate_groups = sum(
        int(document["duplicate_candidate_groups"]) for document in documents
    )
    metrics = {
        item["metric_name"]
        for document in documents
        for item in document.get("review_items") or []
        if item.get("metric_name")
    }
    return {
        "documents": len(documents),
        "review_items": review_item_count,
        "metrics": len(metrics),
        "duplicate_candidate_groups": duplicate_groups,
        "manual_confirmation_required": review_item_count,
    }


def _write_csv(path: Path, packet: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for document in packet.get("documents") or []:
            for item in document.get("review_items") or []:
                writer.writerow({column: item.get(column) for column in _CSV_COLUMNS})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
