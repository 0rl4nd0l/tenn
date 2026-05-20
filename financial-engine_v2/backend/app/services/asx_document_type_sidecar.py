"""Read-only ASX document-type classifier sidecar artifact builder.

The sidecar is a metadata artifact for fixture/surrogate comparison only. It
does not route parsers, infer financial metrics, or authorize canonical writes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.asx_document_type_classifier import classify_asx_document_type


ARTIFACT_TYPE = "asx_document_type_sidecar_v1"
SCHEMA_VERSION = 1
CLASSIFIER_VERSION = "asx_document_type_classifier_v1"
DEFAULT_SOURCE = "synthetic_fixture"
_INPUT_KEYS = ("fixture_id", "document_id", "ticker", "source_text_surrogate")
_EVIDENCE_KEYS = ("document_type", "anchor", "matched_text")
_MAX_EVIDENCE_TEXT_LENGTH = 180


def load_fixture_json(path: str | Path) -> dict[str, Any]:
    """Load a fixture JSON object without invoking backend startup."""

    with Path(path).open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"fixture JSON must contain an object: {path}")
    return loaded


def build_asx_document_type_sidecar(
    payload: Mapping[str, Any],
    *,
    source: str = DEFAULT_SOURCE,
    fixture_id: str | None = None,
    document_id: str | None = None,
    ticker: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a sidecar artifact from a fixture object or surrogate mapping.

    If *payload* includes ``source_text_surrogate`` it is treated as a
    fixture-shaped object. Otherwise the payload itself is treated as the
    surrogate and callers must provide ``document_id`` explicitly.
    """

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")

    source_label = _coerce_non_empty_string(source, field_name="source")
    fixture = _fixture_view(
        payload,
        fixture_id=fixture_id,
        document_id=document_id,
        ticker=ticker,
    )
    if not fixture["document_id"]:
        raise ValueError("document_id is required for ASX document-type sidecars")
    if not fixture["ticker"]:
        raise ValueError("ticker is required for ASX document-type sidecars")

    surrogate = fixture["source_text_surrogate"]
    classification = classify_asx_document_type(surrogate).to_dict()
    artifact: dict[str, Any] = {
        "artifact_type": ARTIFACT_TYPE,
        "document_id": fixture["document_id"],
        "ticker": fixture["ticker"],
        "source": source_label,
        "classifier_version": CLASSIFIER_VERSION,
        "document_type": classification["document_type"],
        "confidence_band": classification["confidence_band"],
        "abstain": classification["abstain"],
        "canonical_write": False,
        "positive_evidence": _compact_evidence(classification.get("positive_evidence", [])),
        "negative_evidence": _compact_evidence(classification.get("negative_evidence", [])),
        "abstain_reasons": list(classification.get("abstain_reasons", [])),
        "warnings": _artifact_warnings(classification.get("warnings", [])),
        "generated_at": generated_at or _utc_now(),
        "input_checksum": _input_checksum(fixture),
        "schema_version": SCHEMA_VERSION,
    }
    if fixture["fixture_id"]:
        artifact["fixture_id"] = fixture["fixture_id"]
    return artifact


def build_sidecar_from_fixture_json(
    path: str | Path,
    *,
    source: str = DEFAULT_SOURCE,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Load a fixture JSON file and return its sidecar artifact."""

    fixture = load_fixture_json(path)
    return build_asx_document_type_sidecar(
        fixture,
        source=source,
        generated_at=generated_at,
    )


def _fixture_view(
    payload: Mapping[str, Any],
    *,
    fixture_id: str | None,
    document_id: str | None,
    ticker: str | None,
) -> dict[str, Any]:
    if isinstance(payload.get("source_text_surrogate"), Mapping):
        surrogate = payload["source_text_surrogate"]
        return {
            "fixture_id": fixture_id if fixture_id is not None else _optional_string(payload.get("fixture_id")),
            "document_id": document_id if document_id is not None else _optional_string(payload.get("document_id")),
            "ticker": ticker if ticker is not None else _optional_string(payload.get("ticker")),
            "source_text_surrogate": surrogate,
        }

    return {
        "fixture_id": fixture_id,
        "document_id": document_id,
        "ticker": ticker,
        "source_text_surrogate": payload,
    }


def _input_checksum(fixture: Mapping[str, Any]) -> str:
    checksum_payload = {key: fixture.get(key) for key in _INPUT_KEYS}
    encoded = json.dumps(
        checksum_payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _compact_evidence(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    evidence: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        compact: dict[str, str] = {}
        for key in _EVIDENCE_KEYS:
            raw_value = item.get(key)
            if isinstance(raw_value, str):
                compact[key] = _trim(raw_value)
        if compact:
            evidence.append(compact)
    return evidence


def _artifact_warnings(classifier_warnings: Any) -> list[str]:
    warnings: list[str] = []
    if isinstance(classifier_warnings, list):
        warnings.extend(item for item in classifier_warnings if isinstance(item, str))
    warnings.append("sidecar artifact is metadata only and does not authorize canonical writes")
    return warnings


def _trim(value: str) -> str:
    if len(value) <= _MAX_EVIDENCE_TEXT_LENGTH:
        return value
    return f"{value[: _MAX_EVIDENCE_TEXT_LENGTH - 3]}..."


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _coerce_non_empty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
