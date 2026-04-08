from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from services.extraction.routing_preferences import SCHEMA_VERSION

DEFAULT_EXTRACTOR = "financial_metrics_pdftotext"

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def update_preferences(
    *, assessment_report: dict[str, Any], method_accuracies: dict[str, dict[str, float]],
    current_prefs: dict[str, Any] | None, min_sample_count: int = 5,
) -> dict[str, Any]:
    existing_prefs = dict((current_prefs or {}).get("method_preferences", {}))
    stratified = (assessment_report.get("stratified") or {}).get("document_type") or {}
    now = _utc_now()
    for doc_type, doc_stats in stratified.items():
        if not isinstance(doc_stats, dict):
            continue
        doc_count = int(doc_stats.get("documents") or 0)
        if doc_count < min_sample_count:
            continue
        accuracies = method_accuracies.get(doc_type)
        if not accuracies or len(accuracies) < 2:
            continue
        sorted_methods = sorted(accuracies.items(), key=lambda x: (-x[1], x[0] != DEFAULT_EXTRACTOR))
        best_method, best_acc = sorted_methods[0]
        fallback_method, fallback_acc = sorted_methods[1]
        prev_sample_count = 0
        if doc_type in existing_prefs:
            prev_sample_count = int(existing_prefs[doc_type].get("sample_count") or 0)
        existing_prefs[doc_type] = {
            "preferred": best_method, "accuracy": round(best_acc, 6),
            "fallback": fallback_method, "fallback_accuracy": round(fallback_acc, 6),
            "sample_count": prev_sample_count + doc_count, "last_updated": now,
        }
    return {
        "schema_version": SCHEMA_VERSION, "updated_at": now,
        "source_run_id": str(assessment_report.get("source_run_id") or ""),
        "method_preferences": existing_prefs, "min_sample_count": min_sample_count,
    }
