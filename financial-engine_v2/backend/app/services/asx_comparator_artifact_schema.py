"""Report-only ASX comparator artifact schema helpers.

This module defines a pure metadata contract for future deterministic ASX
sidecar parser prototypes. It does not import extraction, routing, database,
runtime, model, or persistence modules.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


ARTIFACT_TYPE = "asx_comparator_artifact_v1"
SCHEMA_VERSION = 1
METRIC_STATUSES = {"candidate", "review_only", "abstain", "unsupported"}
REVIEW_ONLY_STATUSES = {"review_only", "unsupported"}
CASH_FLOW_APPENDIX_TYPES = {"appendix_4c", "appendix_5b"}
APPENDIX_4D_4E_TYPES = {"appendix_4d", "appendix_4e"}
CASH_FLOW_FORBIDDEN_CANONICAL_METRICS = {"revenue", "npat", "net_debt"}
REVIEW_ONLY_METRICS = {"eps", "nta", "dividends", "ebitda", "total_debt"}

_REQUIRED_ARTIFACT_FIELDS = {
    "artifact_type",
    "schema_version",
    "canonical_write",
    "document_id",
    "ticker",
    "document_type",
    "parser_id",
    "parser_version",
    "generated_at",
    "period_end",
    "reporting_period",
    "currency",
    "scale",
    "tables",
    "metric_candidates",
    "unsupported_metric_candidates",
    "abstain_reasons",
    "warnings",
    "provenance",
    "validation_summary",
}
_REQUIRED_METRIC_FIELDS = {
    "metric_name",
    "candidate_value",
    "raw_value",
    "normalized_value",
    "unit",
    "currency",
    "scale",
    "period",
    "source_table_id",
    "page",
    "row_label",
    "column_label",
    "line_item_id",
    "evidence_text",
    "confidence",
    "status",
    "canonical_write",
    "abstain_reasons",
    "warnings",
}
_REQUIRED_NON_ABSTAIN_EVIDENCE_FIELDS = {
    "source_table_id",
    "page",
    "row_label",
    "column_label",
    "evidence_text",
}
_REQUIRED_TABLE_FIELDS = {
    "table_id",
    "page",
    "bbox",
    "caption",
    "headers",
    "rows",
    "source_anchor",
    "parser_confidence",
    "warnings",
}
_METRIC_ALIASES = {
    "earningspershare": "eps",
    "eps": "eps",
    "nettangibleassets": "nta",
    "nettangibleassetbacking": "nta",
    "nta": "nta",
    "dividend": "dividends",
    "dividends": "dividends",
    "ebitda": "ebitda",
    "totaldebt": "total_debt",
    "debt": "total_debt",
    "netdebt": "net_debt",
    "netborrowings": "net_debt",
    "npat": "npat",
    "netprofitaftertax": "npat",
    "profitaftertax": "npat",
    "revenue": "revenue",
    "salesrevenue": "revenue",
    "totalrevenue": "revenue",
}


def build_comparator_artifact(
    *,
    document_id: str,
    ticker: str,
    document_type: str,
    source_pdf_path: str | None = None,
    source_reference: str | None = None,
    source_sha256: str | None = None,
    source_checksum: str | None = None,
    parser_id: str,
    parser_version: str,
    period_end: str,
    reporting_period: str,
    currency: str,
    scale: str,
    tables: Sequence[Mapping[str, Any]] | None = None,
    metric_candidates: Sequence[Mapping[str, Any]] | None = None,
    unsupported_metric_candidates: Sequence[Mapping[str, Any]] | None = None,
    abstain_reasons: Sequence[str] | None = None,
    warnings: Sequence[str] | None = None,
    provenance: Mapping[str, Any] | None = None,
    validation_summary: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a report-only comparator artifact with canonical writes disabled."""

    artifact: dict[str, Any] = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "canonical_write": False,
        "document_id": document_id,
        "ticker": ticker,
        "document_type": document_type,
        "source_pdf_path": source_pdf_path,
        "source_reference": source_reference,
        "source_sha256": source_sha256,
        "source_checksum": source_checksum,
        "parser_id": parser_id,
        "parser_version": parser_version,
        "generated_at": generated_at or _utc_now(),
        "period_end": period_end,
        "reporting_period": reporting_period,
        "currency": currency,
        "scale": scale,
        "tables": [dict(table) for table in tables or []],
        "metric_candidates": [dict(candidate) for candidate in metric_candidates or []],
        "unsupported_metric_candidates": [
            dict(candidate) for candidate in unsupported_metric_candidates or []
        ],
        "abstain_reasons": list(abstain_reasons or []),
        "warnings": list(warnings or []),
        "provenance": dict(provenance or {}),
        "validation_summary": dict(validation_summary or {"schema_validation": "not_run"}),
    }
    return artifact


def validate_comparator_artifact(artifact: Mapping[str, Any]) -> list[str]:
    """Return schema issues for a comparator artifact without mutating it."""

    if not isinstance(artifact, Mapping):
        return ["artifact must be a mapping"]

    issues: list[str] = []
    for field in sorted(_REQUIRED_ARTIFACT_FIELDS):
        if field not in artifact or _is_missing(artifact.get(field)):
            issues.append(f"artifact missing required field: {field}")

    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        issues.append(f"artifact_type must be {ARTIFACT_TYPE!r}")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION}")

    issues.extend(assert_no_canonical_write(artifact))
    issues.extend(_validate_artifact_source(artifact))
    issues.extend(_validate_sequence_field(artifact, "tables", "artifact"))
    issues.extend(_validate_sequence_field(artifact, "metric_candidates", "artifact"))
    issues.extend(_validate_sequence_field(artifact, "unsupported_metric_candidates", "artifact"))
    issues.extend(_validate_sequence_field(artifact, "abstain_reasons", "artifact"))
    issues.extend(_validate_sequence_field(artifact, "warnings", "artifact"))

    if "provenance" in artifact and not isinstance(artifact.get("provenance"), Mapping):
        issues.append("artifact provenance must be a mapping")
    if "validation_summary" in artifact and not isinstance(artifact.get("validation_summary"), Mapping):
        issues.append("artifact validation_summary must be a mapping")

    document_type = _normalize_document_type(artifact.get("document_type"))
    for index, table in enumerate(_as_sequence(artifact.get("tables"))):
        issues.extend(_validate_table(table, index=index))

    for index, candidate in enumerate(_as_sequence(artifact.get("metric_candidates"))):
        issues.extend(
            validate_metric_candidate(
                candidate,
                document_type=document_type,
                path=f"metric_candidates[{index}]",
            )
        )

    for index, candidate in enumerate(_as_sequence(artifact.get("unsupported_metric_candidates"))):
        issues.extend(
            validate_metric_candidate(
                candidate,
                document_type=document_type,
                unsupported_collection=True,
                path=f"unsupported_metric_candidates[{index}]",
            )
        )

    return issues


def validate_metric_candidate(
    candidate: Mapping[str, Any],
    *,
    document_type: str | None = None,
    unsupported_collection: bool = False,
    path: str = "metric_candidate",
) -> list[str]:
    """Return schema issues for one metric candidate."""

    if not isinstance(candidate, Mapping):
        return [f"{path} must be a mapping"]

    issues: list[str] = []
    for field in sorted(_REQUIRED_METRIC_FIELDS):
        if field not in candidate:
            issues.append(f"{path} missing required field: {field}")

    status = candidate.get("status")
    if status not in METRIC_STATUSES:
        issues.append(f"{path} status must be one of {sorted(METRIC_STATUSES)}")
    if _is_missing(candidate.get("metric_name")):
        issues.append(f"{path} metric_name must be present")

    if candidate.get("canonical_write") is not False:
        issues.append(f"{path} canonical_write must be false")

    if status != "abstain":
        for field in sorted(_REQUIRED_NON_ABSTAIN_EVIDENCE_FIELDS):
            if _is_missing(candidate.get(field)):
                issues.append(f"{path} missing evidence field for non-abstain candidate: {field}")
    elif not candidate.get("abstain_reasons"):
        issues.append(f"{path} abstain status requires abstain_reasons")

    if "abstain_reasons" in candidate and not isinstance(candidate.get("abstain_reasons"), list):
        issues.append(f"{path} abstain_reasons must be a list")
    if "warnings" in candidate and not isinstance(candidate.get("warnings"), list):
        issues.append(f"{path} warnings must be a list")

    metric_key = _metric_key(candidate.get("metric_name"))
    normalized_document_type = _normalize_document_type(document_type)
    if unsupported_collection and status not in REVIEW_ONLY_STATUSES:
        issues.append(f"{path} unsupported metric status must be review_only or unsupported")
    if metric_key in REVIEW_ONLY_METRICS and status not in REVIEW_ONLY_STATUSES:
        issues.append(f"{path} {metric_key} must be review_only or unsupported")
    if (
        normalized_document_type in CASH_FLOW_APPENDIX_TYPES
        and metric_key in CASH_FLOW_FORBIDDEN_CANONICAL_METRICS
        and status == "candidate"
    ):
        issues.append(
            f"{path} {metric_key} cannot be a candidate for {normalized_document_type} artifacts"
        )
    if (
        normalized_document_type in APPENDIX_4D_4E_TYPES
        and metric_key in {"eps", "nta", "dividends"}
        and status not in REVIEW_ONLY_STATUSES
    ):
        issues.append(f"{path} {metric_key} must be review_only or unsupported for {normalized_document_type}")

    return issues


def assert_no_canonical_write(artifact: Mapping[str, Any]) -> list[str]:
    """Return issues for any canonical write flag that is not literal false."""

    if not isinstance(artifact, Mapping):
        return ["artifact must be a mapping"]

    issues: list[str] = []
    if artifact.get("canonical_write") is not False:
        issues.append("artifact canonical_write must be false")

    for collection_name in ("metric_candidates", "unsupported_metric_candidates"):
        for index, candidate in enumerate(_as_sequence(artifact.get(collection_name))):
            if isinstance(candidate, Mapping) and candidate.get("canonical_write") is not False:
                issues.append(f"{collection_name}[{index}] canonical_write must be false")
    return issues


def stable_artifact_checksum(artifact: Mapping[str, Any]) -> str:
    """Return a deterministic checksum for a JSON-serializable artifact."""

    payload = _without_self_checksum(artifact)
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_artifact_source(artifact: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if _is_missing(artifact.get("source_pdf_path")) and _is_missing(artifact.get("source_reference")):
        issues.append("artifact requires source_pdf_path or source_reference")
    if _is_missing(artifact.get("source_sha256")) and _is_missing(artifact.get("source_checksum")):
        issues.append("artifact requires source_sha256 or source_checksum")
    return issues


def _validate_table(table: Any, *, index: int) -> list[str]:
    path = f"tables[{index}]"
    if not isinstance(table, Mapping):
        return [f"{path} must be a mapping"]

    issues: list[str] = []
    for field in sorted(_REQUIRED_TABLE_FIELDS):
        if field not in table:
            issues.append(f"{path} missing supported field: {field}")
    if "headers" in table and not isinstance(table.get("headers"), list):
        issues.append(f"{path} headers must be a list")
    if "rows" in table and not isinstance(table.get("rows"), list):
        issues.append(f"{path} rows must be a list")
    if "warnings" in table and not isinstance(table.get("warnings"), list):
        issues.append(f"{path} warnings must be a list")
    if "page" in table and not isinstance(table.get("page"), int):
        issues.append(f"{path} page must be an integer")
    return issues


def _validate_sequence_field(artifact: Mapping[str, Any], field: str, path: str) -> list[str]:
    if field not in artifact:
        return []
    if not isinstance(artifact.get(field), list):
        return [f"{path} {field} must be a list"]
    return []


def _as_sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _metric_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    compact = re.sub(r"[^a-z0-9]+", "", value.lower())
    return _METRIC_ALIASES.get(compact, compact)


def _normalize_document_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    normalized = normalized.replace("appendix_05b", "appendix_5b")
    return normalized


def _without_self_checksum(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_self_checksum(item)
            for key, item in value.items()
            if key not in {"artifact_checksum", "stable_artifact_checksum"}
        }
    if isinstance(value, list):
        return [_without_self_checksum(item) for item in value]
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
