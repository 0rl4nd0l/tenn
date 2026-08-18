from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping


_EXTRACTION_RE = re.compile(
    r"^(?P<label>[a-z_]+):(?P<location>page_[^:]+):(?P<detail>.+)$"
)
_DERIVED_RE = re.compile(r"^derived:(?P<label>[a-z_]+):(?P<detail>.+)$")
_UUID_LIKE_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

_PRECISE = "precise"
_DERIVED = "derived"
_LOW_TRACEABILITY = "low_traceability"
_PARTIAL = "partial"
_SYNTHETIC = "synthetic"
_MISSING = "missing"


def _clean_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clean_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _compose_period_ref(period_end: Any, period_type: Any) -> str | None:
    end = _clean_str(period_end)
    ptype = _clean_str(period_type)
    if end and ptype:
        return f"{end}:{ptype}"
    return end or ptype


def _truncate(text: str | None, limit: int = 140) -> str | None:
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _infer_synthetic(texts: list[str | None]) -> bool:
    haystack = " ".join(text for text in texts if text).lower()
    return any(
        token in haystack for token in ("placeholder", "synthetic", "not_configured")
    )


def _is_unknown_evidence(value: Any) -> bool:
    text = _clean_str(value)
    return text is not None and text.lower() == "unknown"


def _maybe_source_document_id(value: Any) -> str | None:
    text = _clean_str(value)
    if not text:
        return None
    if _UUID_LIKE_RE.match(text):
        return text
    return None


@dataclass(frozen=True)
class ProvenanceRecord:
    source_type: str | None = None
    source_document_id: str | None = None
    source_label: str | None = None
    location_ref: str | None = None
    period_ref: str | None = None
    evidence_text: str | None = None
    evidence_summary: str | None = None
    provenance_status: str = _MISSING
    confidence: float | None = None
    parent_reference_ids: tuple[str, ...] = field(default_factory=tuple)
    raw_reference: Any = None


@dataclass(frozen=True)
class ProvenanceIssue:
    code: str
    severity: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "field": self.field,
        }


def from_extraction_provenance(
    metric_name: str,
    provenance: str | None,
    *,
    source_document_id: str | None = None,
    period_ref: str | None = None,
    confidence: float | None = None,
) -> ProvenanceRecord:
    raw = _clean_str(provenance)
    metric = _clean_str(metric_name) or "metric"

    if not raw:
        return ProvenanceRecord(
            source_type="financial_statement",
            source_document_id=_clean_str(source_document_id),
            source_label=metric,
            period_ref=_clean_str(period_ref),
            evidence_summary=f"{metric} has no recorded provenance.",
            provenance_status=_MISSING,
            confidence=_clean_float(confidence),
            raw_reference=provenance,
        )

    if _infer_synthetic([metric, raw]):
        return ProvenanceRecord(
            source_type="financial_statement",
            source_document_id=_clean_str(source_document_id),
            source_label=metric,
            period_ref=_clean_str(period_ref),
            evidence_text=raw,
            evidence_summary=f"{metric} provenance appears synthetic or placeholder-backed.",
            provenance_status=_SYNTHETIC,
            confidence=_clean_float(confidence),
            raw_reference=raw,
        )

    derived_match = _DERIVED_RE.match(raw)
    if derived_match:
        detail = _clean_str(derived_match.group("detail"))
        parents = tuple(dict.fromkeys(re.findall(r"([a-z_]+)\(", raw)))
        return ProvenanceRecord(
            source_type="financial_statement",
            source_document_id=_clean_str(source_document_id),
            source_label=_clean_str(derived_match.group("label")),
            period_ref=_clean_str(period_ref),
            evidence_text=detail,
            evidence_summary=f"{metric} was derived from upstream extracted values.",
            provenance_status=_DERIVED,
            confidence=_clean_float(confidence),
            parent_reference_ids=parents,
            raw_reference=raw,
        )

    extraction_match = _EXTRACTION_RE.match(raw)
    if extraction_match:
        label = _clean_str(extraction_match.group("label"))
        location = _clean_str(extraction_match.group("location"))
        detail = _clean_str(extraction_match.group("detail"))
        status = _LOW_TRACEABILITY if label == "prose_note" else _PRECISE
        summary = (
            f"{metric} extracted from prose-note fallback."
            if status == _LOW_TRACEABILITY
            else f"{metric} extracted directly from {label}."
        )
        return ProvenanceRecord(
            source_type="financial_statement",
            source_document_id=_clean_str(source_document_id),
            source_label=label,
            location_ref=location,
            period_ref=_clean_str(period_ref),
            evidence_text=detail,
            evidence_summary=summary,
            provenance_status=status,
            confidence=_clean_float(confidence),
            raw_reference=raw,
        )

    return ProvenanceRecord(
        source_type="financial_statement",
        source_document_id=_clean_str(source_document_id),
        source_label=metric,
        period_ref=_clean_str(period_ref),
        evidence_text=raw,
        evidence_summary=f"{metric} provenance did not match a known extraction pattern.",
        provenance_status=_PARTIAL,
        confidence=_clean_float(confidence),
        raw_reference=raw,
    )


def _field_provenance_record(
    metric_name: str,
    field_provenance: Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    source_document_id: str | None = None,
) -> ProvenanceRecord:
    metric = _clean_str(metric_name) or _clean_str(
        field_provenance.get("metric")
    ) or "metric"
    source = _clean_str(field_provenance.get("source")) or _clean_str(
        field_provenance.get("table_label")
    )
    page_tag = _clean_str(field_provenance.get("page_tag"))
    if not page_tag:
        page_number = _clean_str(field_provenance.get("page_number"))
        page_tag = f"page_{page_number}" if page_number else None
    row_ref = field_provenance.get("row_ref")
    excerpt = field_provenance.get("excerpt")
    evidence = _clean_str(excerpt) or _clean_str(row_ref)
    period_ref = _compose_period_ref(
        field_provenance.get("period_end") or payload.get("period_end"),
        field_provenance.get("period_type") or payload.get("period_type"),
    )
    doc_id = (
        _clean_str(source_document_id)
        or _clean_str(field_provenance.get("source_document_id"))
        or _clean_str(payload.get("source_document_id"))
    )
    source_label = source or metric
    if source_label.startswith("derived:"):
        status = _DERIVED
        parents = tuple(dict.fromkeys(re.findall(r"([a-z_]+)\(", evidence or "")))
        summary = f"{metric} was derived from upstream extracted values."
    elif source_label == "prose_note":
        status = _LOW_TRACEABILITY
        parents = ()
        summary = f"{metric} extracted from prose-note fallback."
    else:
        unknown_evidence = _is_unknown_evidence(row_ref) or _is_unknown_evidence(
            excerpt
        )
        status = (
            _LOW_TRACEABILITY
            if unknown_evidence
            else (_PRECISE if page_tag else _PARTIAL)
        )
        parents = ()
        if unknown_evidence:
            summary = f"{metric} has structured provenance with unknown row evidence."
        elif status == _PRECISE:
            summary = f"{metric} extracted directly from {source_label}."
        else:
            summary = (
                f"{metric} has structured provenance with partial location evidence."
            )

    return ProvenanceRecord(
        source_type="financial_statement",
        source_document_id=doc_id,
        source_label=source_label,
        location_ref=page_tag,
        period_ref=period_ref,
        evidence_text=evidence,
        evidence_summary=summary,
        provenance_status=status,
        confidence=_clean_float(payload.get("confidence_metrics")),
        parent_reference_ids=parents,
        raw_reference=dict(field_provenance),
    )


def from_extraction_payload_metric(
    payload: Mapping[str, Any],
    metric_name: str,
    *,
    source_document_id: str | None = None,
) -> ProvenanceRecord:
    field_provenance = payload.get("field_provenance")
    if isinstance(field_provenance, Mapping):
        metric_provenance = field_provenance.get(metric_name)
        if isinstance(metric_provenance, Mapping):
            return _field_provenance_record(
                metric_name,
                metric_provenance,
                payload=payload,
                source_document_id=source_document_id,
            )

    provenance = payload.get("provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    period_ref = _compose_period_ref(
        payload.get("period_end"), payload.get("period_type")
    )
    doc_id = _clean_str(source_document_id) or _clean_str(
        payload.get("source_document_id")
    )
    return from_extraction_provenance(
        metric_name=str(metric_name),
        provenance=_clean_str(provenance.get(metric_name)),
        source_document_id=doc_id,
        period_ref=period_ref,
        confidence=payload.get("confidence_metrics"),
    )


def from_extraction_payload(
    payload: Mapping[str, Any], *, source_document_id: str | None = None
) -> list[ProvenanceRecord]:
    field_provenance = payload.get("field_provenance")
    provenance = payload.get("provenance")
    if isinstance(field_provenance, Mapping):
        metric_names: list[str] = []
        for source_map in (field_provenance, provenance):
            if not isinstance(source_map, Mapping):
                continue
            for metric_name in source_map:
                metric_names.append(str(metric_name))
        return [
            from_extraction_payload_metric(
                payload,
                metric_name,
                source_document_id=source_document_id,
            )
            for metric_name in dict.fromkeys(metric_names)
        ]

    if not isinstance(provenance, Mapping):
        return []

    period_ref = _compose_period_ref(
        payload.get("period_end"), payload.get("period_type")
    )
    doc_id = _clean_str(source_document_id) or _clean_str(
        payload.get("source_document_id")
    )
    confidence = _clean_float(payload.get("confidence_metrics"))
    return [
        from_extraction_provenance(
            metric_name=str(metric_name),
            provenance=_clean_str(metric_provenance),
            source_document_id=doc_id,
            period_ref=period_ref,
            confidence=confidence,
        )
        for metric_name, metric_provenance in provenance.items()
    ]


def from_orchestrator_evidence(
    source_name: str,
    payload: Mapping[str, Any] | None,
) -> ProvenanceRecord:
    source = _clean_str(source_name) or "unknown"
    raw_payload = dict(payload or {})
    status = _clean_str(raw_payload.get("status"))

    if source == "financial_truth":
        snapshot = raw_payload.get("latest_financial_snapshot")
        snapshot = snapshot if isinstance(snapshot, Mapping) else {}
        items = raw_payload.get("items")
        items = items if isinstance(items, list) else []
        first_item = items[0] if items and isinstance(items[0], Mapping) else {}
        doc_id = _clean_str(snapshot.get("source_document_id")) or _clean_str(
            first_item.get("source_document_id")
        )
        period_ref = _compose_period_ref(
            snapshot.get("period_end") or first_item.get("period_end"),
            snapshot.get("period_type") or first_item.get("period_type"),
        )
        ticker = _clean_str(
            raw_payload.get("ticker")
            or snapshot.get("ticker")
            or first_item.get("ticker")
        )
        summary = f"financial_truth payload for {ticker or 'unknown ticker'}"
        if status and status != "ok":
            summary = f"financial_truth payload status={status}"
        return ProvenanceRecord(
            source_type="financial_statement",
            source_document_id=doc_id,
            source_label=source,
            period_ref=period_ref,
            evidence_summary=summary,
            provenance_status=_PARTIAL
            if status in (None, "ok", "partial_error")
            else _MISSING,
            confidence=_clean_float(
                snapshot.get("confidence_metrics")
                or first_item.get("confidence_metrics")
            ),
            raw_reference=raw_payload,
        )

    items = raw_payload.get("items")
    item_count = len(items) if isinstance(items, list) else 0
    first_item = items[0] if item_count and isinstance(items[0], Mapping) else {}
    first_statement = _clean_str(
        first_item.get("statement") or first_item.get("content")
    )
    summary = f"{source} payload with {item_count} item(s)."
    synthetic = _infer_synthetic([status, source, first_statement])
    record_status = (
        _SYNTHETIC if synthetic else (_LOW_TRACEABILITY if item_count else _MISSING)
    )
    if status == "ok" and item_count:
        record_status = _LOW_TRACEABILITY
    return ProvenanceRecord(
        source_type=source,
        source_document_id=_maybe_source_document_id(
            first_item.get("source_document_id")
        ),
        source_label=source,
        evidence_text=first_statement,
        evidence_summary=summary,
        provenance_status=record_status,
        confidence=_clean_float(
            first_item.get("confidence") or raw_payload.get("confidence")
        ),
        raw_reference=raw_payload,
    )


def from_report_evidence_item(item: Any) -> ProvenanceRecord:
    evidence_id = _clean_str(getattr(item, "evidence_id", None))
    source_type = _clean_str(getattr(item, "source_type", None))
    source_id = _clean_str(getattr(item, "source_id", None))
    content = _clean_str(getattr(item, "content", None))
    confidence = _clean_float(getattr(item, "confidence", None))
    synthetic = _infer_synthetic([evidence_id, source_id, content])
    provenance_status = (
        _SYNTHETIC
        if synthetic
        else (_PARTIAL if source_type or source_id else _MISSING)
    )
    if source_type == "computed":
        provenance_status = _DERIVED
    return ProvenanceRecord(
        source_type=source_type,
        source_document_id=_maybe_source_document_id(source_id),
        source_label=source_id or evidence_id,
        evidence_text=content,
        evidence_summary=_truncate(content) or evidence_id,
        provenance_status=provenance_status,
        confidence=confidence,
        raw_reference=item,
    )


def from_report_evidence_bundle_item(item: Mapping[str, Any]) -> ProvenanceRecord:
    raw_item = dict(item)
    evidence_id = _clean_str(raw_item.get("evidence_id"))
    source_type = _clean_str(raw_item.get("source_type"))
    source_id = _clean_str(raw_item.get("source_id") or raw_item.get("source_url"))
    content = _clean_str(raw_item.get("content"))
    source_document_id = _clean_str(
        raw_item.get("source_document_id")
    ) or _maybe_source_document_id(source_id)
    synthetic = _infer_synthetic([evidence_id, source_id, content])
    provenance_status = (
        _SYNTHETIC
        if synthetic
        else (_PARTIAL if source_type or source_id else _MISSING)
    )
    return ProvenanceRecord(
        source_type=source_type,
        source_document_id=source_document_id,
        source_label=source_id or evidence_id,
        evidence_text=content,
        evidence_summary=_truncate(content) or evidence_id,
        provenance_status=provenance_status,
        confidence=_clean_float(raw_item.get("confidence")),
        raw_reference=raw_item,
    )


def validate_provenance_record(record: ProvenanceRecord) -> dict[str, Any]:
    issues: list[ProvenanceIssue] = []

    if not (record.source_type or record.source_document_id or record.source_label):
        issues.append(
            ProvenanceIssue(
                code="missing_source_identity",
                severity="error",
                message="Record has no source_type, source_document_id, or source_label.",
                field="source_type",
            )
        )

    if record.provenance_status == _PRECISE and not record.location_ref:
        issues.append(
            ProvenanceIssue(
                code="missing_location_ref",
                severity="error",
                message="Precise provenance requires a location_ref.",
                field="location_ref",
            )
        )

    if (
        record.source_type == "financial_statement"
        and record.provenance_status
        in {
            _PRECISE,
            _DERIVED,
        }
        and not record.period_ref
    ):
        issues.append(
            ProvenanceIssue(
                code="missing_period_ref",
                severity="warning",
                message="Period-specific financial evidence is missing period_ref.",
                field="period_ref",
            )
        )

    if not (record.evidence_text or record.evidence_summary):
        issues.append(
            ProvenanceIssue(
                code="empty_evidence_payload",
                severity="warning",
                message="Record has neither evidence_text nor evidence_summary.",
                field="evidence_text",
            )
        )

    if record.provenance_status == _SYNTHETIC:
        issues.append(
            ProvenanceIssue(
                code="synthetic_evidence",
                severity="warning",
                message="Record is marked synthetic or placeholder-backed.",
                field="provenance_status",
            )
        )

    if record.provenance_status == _DERIVED:
        issues.append(
            ProvenanceIssue(
                code="derived_evidence",
                severity="warning",
                message="Record is derived from other evidence rather than directly cited.",
                field="provenance_status",
            )
        )

    if record.provenance_status in {_LOW_TRACEABILITY, _PARTIAL, _MISSING}:
        issues.append(
            ProvenanceIssue(
                code="low_traceability",
                severity="warning",
                message="Record is missing precise traceability details.",
                field="provenance_status",
            )
        )

    return {
        "ok": not any(issue.severity == "error" for issue in issues),
        "issues": [issue.to_dict() for issue in issues],
        "error_count": sum(1 for issue in issues if issue.severity == "error"),
        "warning_count": sum(1 for issue in issues if issue.severity == "warning"),
    }


def validate_provenance_collection(records: list[ProvenanceRecord]) -> dict[str, Any]:
    record_results = []
    all_issues: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        result = validate_provenance_record(record)
        record_results.append(result)
        for issue in result["issues"]:
            all_issues.append({"record_index": index, **issue})

    return {
        "ok": all(result["ok"] for result in record_results),
        "record_count": len(records),
        "record_results": record_results,
        "issues": all_issues,
        "error_count": sum(result["error_count"] for result in record_results),
        "warning_count": sum(result["warning_count"] for result in record_results),
    }
