#!/usr/bin/env python3
"""Deterministic routing remediation for strict-mode / fail-closed extraction outputs."""

from __future__ import annotations

from typing import Any, Mapping

from services.evaluation.normalizer import normalize_numeric


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_candidate_profile(method_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Summarize extractor output for deterministic routing/remediation (no PDF side effects)."""
    payload = dict(method_payload or {})
    completeness = payload.get("completeness")
    comp = dict(completeness) if isinstance(completeness, Mapping) else {}
    row_count = _safe_int(comp.get("row_count"))
    rows_with_numeric = _safe_int(comp.get("rows_with_numeric_value"))
    cm = payload.get("canonical_metrics")
    canonical_numeric_count = 0
    if isinstance(cm, Mapping):
        for v in cm.values():
            if normalize_numeric(v) is not None:
                canonical_numeric_count += 1
    status = str(payload.get("status") or "").strip().lower()
    return {
        "row_count": row_count,
        "rows_with_numeric_value": rows_with_numeric,
        "canonical_numeric_metric_count": canonical_numeric_count,
        "method_status": status,
    }


def financial_like_table_signals(classifier: Mapping[str, Any] | None) -> dict[str, Any]:
    """Heuristic table/candidate density from merged router classifier output."""
    c = dict(classifier or {})
    features = dict(c.get("features") or {})
    ctx = _safe_int(features.get("context_rows"))
    pdftext_rows = _safe_int(features.get("pdftotext_row_count"))
    tsr = _safe_int(features.get("tsr_tables_processed"))
    td = _safe_float(c.get("table_density"))
    comp_score = _safe_float(c.get("complexity_score"))
    strong = (
        td >= 0.10
        or ctx >= 40
        or pdftext_rows >= 15
        or tsr >= 2
        or comp_score >= 0.45
    )
    return {
        "strong_financial_table_signal": bool(strong),
        "context_rows": ctx,
        "table_density": td,
        "pdftotext_row_count": pdftext_rows,
        "tsr_tables_processed": tsr,
        "complexity_score": comp_score,
    }


def assess_non_financial_explicit_drop(
    classifier: Mapping[str, Any] | None,
    profile: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Tag likely non-financial documents when the classifier is non-financial and the
    candidate profile has no numeric signal (fail-closed: no invented metrics).
    """
    c = dict(classifier or {})
    p = dict(profile or {})
    if c.get("is_financial") is not False:
        return {"applied": False, "reason": None, "detail": "classifier_not_non_financial"}
    cmc = _safe_int(p.get("canonical_numeric_metric_count"))
    rw = _safe_int(p.get("rows_with_numeric_value"))
    if cmc > 0 or rw > 0:
        return {"applied": False, "reason": None, "detail": "has_numeric_signal"}
    row_count = _safe_int(p.get("row_count"))
    if row_count > 0:
        return {"applied": False, "reason": None, "detail": "label_only_rows_need_escalation"}
    signals = financial_like_table_signals(c)
    if signals["strong_financial_table_signal"]:
        return {
            "applied": False,
            "reason": None,
            "detail": "strong_table_signal_overrides_non_financial_classifier",
        }
    return {
        "applied": True,
        "reason": "non_financial_classifier_no_extractable_numeric_signal",
        "detail": "explicit_drop",
    }


def label_only_or_empty_numeric_candidates(profile: Mapping[str, Any] | None) -> bool:
    """
    True when the extractor produced label/text scaffolding but no numeric candidates,
    or succeeded structurally with an empty numeric profile.
    """
    p = dict(profile or {})
    cmc = _safe_int(p.get("canonical_numeric_metric_count"))
    rw = _safe_int(p.get("rows_with_numeric_value"))
    if cmc > 0 or rw > 0:
        return False
    row_count = _safe_int(p.get("row_count"))
    if row_count > 0:
        return True
    status = str(p.get("method_status") or "").lower()
    if status in {"ok", "success"} and row_count == 0 and cmc == 0:
        return True
    return False


def should_escalate_docling_after_probe(
    *,
    classifier: Mapping[str, Any] | None,
    profile: Mapping[str, Any] | None,
    fallback_reasons: list[str],
    explicit_non_financial_drop: bool,
) -> tuple[bool, str]:
    """
    Stronger retry path: Docling when the probe is vacuous but the document still looks
    financial or table-heavy. Skipped when normal fallback already runs or when an
    explicit non-financial drop applies.
    """
    if fallback_reasons:
        return False, "fallback_reasons_already_trigger_docling"
    if explicit_non_financial_drop:
        return False, "non_financial_explicit_drop_skip_escalation"
    c = dict(classifier or {})
    signals = financial_like_table_signals(c)
    is_financial = c.get("is_financial") is True
    if label_only_or_empty_numeric_candidates(profile) and (is_financial or signals["strong_financial_table_signal"]):
        return True, "label_only_or_empty_numeric_financial_like_escalation"
    return False, "no_escalation_criteria"


def should_suppress_docling_for_explicit_non_financial(
    explicit_drop_assessment: Mapping[str, Any] | None,
    fallback_reasons: list[str],
) -> bool:
    """Avoid expensive Docling when classifier + profile agree on non-financial, unless safety flags fire."""
    assessment = dict(explicit_drop_assessment or {})
    if not assessment.get("applied"):
        return False
    if any(r in ("financial_anomaly", "inconsistent_metric_values") for r in fallback_reasons):
        return False
    return True
