from __future__ import annotations

from typing import Any

_ANNOUNCEMENT_CONTEXT_FALLBACK_MARKER = "using documents_pdf_excerpt fallback"


def split_financial_truth_errors(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw_errors = payload.get("errors")
    errors = [str(item) for item in raw_errors] if isinstance(raw_errors, list) else []
    raw_warnings = payload.get("warnings")
    warnings = (
        [str(item) for item in raw_warnings] if isinstance(raw_warnings, list) else []
    )
    has_fallback_context = bool(payload.get("announcement_context") or [])
    blocking_errors: list[str] = []
    for error in errors:
        lowered = error.lower()
        if (
            has_fallback_context
            and "announcement_context:" in lowered
            and _ANNOUNCEMENT_CONTEXT_FALLBACK_MARKER in lowered
        ):
            warnings.append(
                "announcement_context: materialized context unavailable; "
                "documents_pdf_excerpt fallback returned context"
            )
            continue
        blocking_errors.append(error)
    return blocking_errors, warnings
