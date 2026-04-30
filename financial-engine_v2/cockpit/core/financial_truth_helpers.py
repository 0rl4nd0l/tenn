from __future__ import annotations

from typing import Any

def _announcement_context_uses_document_excerpt_fallback(payload: dict[str, Any]) -> bool:
    rows = payload.get("announcement_context")
    if not isinstance(rows, list) or not rows:
        return False
    if bool(payload.get("announcement_context_fallback_used")):
        return True
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("context_source") or "").strip().lower() == "documents_pdf_excerpt":
            return True
    return False


def split_financial_truth_errors(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw_errors = payload.get("errors")
    errors = [str(item) for item in raw_errors] if isinstance(raw_errors, list) else []
    raw_warnings = payload.get("warnings")
    warnings = (
        [str(item) for item in raw_warnings] if isinstance(raw_warnings, list) else []
    )
    has_fallback_context = _announcement_context_uses_document_excerpt_fallback(payload)
    blocking_errors: list[str] = []
    for error in errors:
        lowered = error.lower()
        if has_fallback_context and lowered.startswith("announcement_context:"):
            warnings.append(
                "announcement_context: materialized context unavailable; "
                "documents_pdf_excerpt fallback returned context"
            )
            continue
        blocking_errors.append(error)
    return blocking_errors, warnings
