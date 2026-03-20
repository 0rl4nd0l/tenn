#!/usr/bin/env python3
"""Deterministic forced-OCR policy for hard PDFs (scanned / weak text layer)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

# Tunable thresholds: low text layer vs page count => scanned-like.
DEFAULT_CHARS_PER_PAGE_SCANNED_LIKE = 72.0
# Absolute floor: tiny extract on a multi-page doc is almost always scanned or protected.
DEFAULT_MIN_TEXT_LAYER_CHARS = 400


@dataclass(frozen=True)
class OcrPolicySignals:
    text_layer_chars: int
    pdf_page_count: int
    docling_row_count_before_filtering: int
    tsr_tables_processed: int
    canonical_numeric_rows: int
    context_row_count: int

    @property
    def chars_per_page(self) -> float:
        return float(self.text_layer_chars) / float(max(1, self.pdf_page_count))

    def as_dict(self) -> dict[str, Any]:
        return {
            "text_layer_chars": self.text_layer_chars,
            "pdf_page_count": self.pdf_page_count,
            "chars_per_page": round(self.chars_per_page, 6),
            "docling_row_count_before_filtering": self.docling_row_count_before_filtering,
            "tsr_tables_processed": self.tsr_tables_processed,
            "canonical_numeric_rows": self.canonical_numeric_rows,
            "context_row_count": self.context_row_count,
        }


def pdf_page_count(pdf_path: Path, *, timeout_sec: float = 30.0) -> int:
    """Best-effort page count via poppler ``pdfinfo``; defaults to 1 if unavailable."""
    try:
        cp = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        if cp.returncode == 0:
            for line in cp.stdout.splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("pages:"):
                    raw = stripped.split(":", 1)[1].strip().split()
                    if raw:
                        return max(1, int(raw[0]))
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return 1


def count_numeric_canonical_rows(rows: Sequence[Mapping[str, Any]]) -> int:
    """Rows with a parseable numeric ``value`` (strict metric extraction output)."""
    n = 0
    for row in rows:
        raw = row.get("value")
        if raw is None:
            continue
        text = str(raw).strip().replace(",", "")
        if not text:
            continue
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]
        try:
            float(text)
        except (TypeError, ValueError):
            continue
        n += 1
    return n


def decide_forced_ocr(
    signals: OcrPolicySignals | Mapping[str, Any],
    *,
    user_requested_docling_ocr: bool = False,
    policy_disabled: bool = False,
    chars_per_page_scanned_like: float = DEFAULT_CHARS_PER_PAGE_SCANNED_LIKE,
    min_text_layer_chars: int = DEFAULT_MIN_TEXT_LAYER_CHARS,
) -> dict[str, Any]:
    """
    Return whether Docling should run again with OCR enabled.

    If ``user_requested_docling_ocr`` is True, policy never forces (OCR already on).
    """
    if isinstance(signals, Mapping):
        s = OcrPolicySignals(
            text_layer_chars=int(signals.get("text_layer_chars") or 0),
            pdf_page_count=max(1, int(signals.get("pdf_page_count") or 1)),
            docling_row_count_before_filtering=int(signals.get("docling_row_count_before_filtering") or 0),
            tsr_tables_processed=int(signals.get("tsr_tables_processed") or 0),
            canonical_numeric_rows=int(signals.get("canonical_numeric_rows") or 0),
            context_row_count=int(signals.get("context_row_count") or 0),
        )
    else:
        s = signals

    base: dict[str, Any] = {
        "forced": False,
        "reasons": [],
        "signals": s.as_dict(),
        "force_full_page_ocr": True,
        "skipped_reason": None,
    }

    if user_requested_docling_ocr:
        base["skipped_reason"] = "user_requested_docling_ocr"
        return base

    if policy_disabled:
        base["skipped_reason"] = "policy_disabled"
        return base

    if s.canonical_numeric_rows > 0:
        base["skipped_reason"] = "sufficient_numeric_canonical_rows"
        return base

    reasons: list[str] = []

    cpp = s.chars_per_page
    low_density = cpp < float(chars_per_page_scanned_like)
    low_absolute = s.text_layer_chars < int(min_text_layer_chars)
    scanned_like = low_density or low_absolute
    if low_density:
        reasons.append("low_text_layer_density")
    if low_absolute:
        reasons.append("low_absolute_text_layer_chars")
    if scanned_like:
        reasons.append("scanned_like")

    empty_structure = s.docling_row_count_before_filtering == 0 and s.tsr_tables_processed == 0
    empty_candidates = s.context_row_count == 0
    if empty_structure and empty_candidates:
        reasons.append("empty_docling_structure_and_empty_candidates")

    if s.docling_row_count_before_filtering > 0:
        reasons.append("zero_numeric_rows_despite_docling_rows")

    seen: set[str] = set()
    deduped: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            deduped.append(r)

    empty_and_barren = empty_structure and empty_candidates
    docling_found_rows_but_no_numbers = s.docling_row_count_before_filtering > 0

    forced = scanned_like or empty_and_barren or docling_found_rows_but_no_numbers
    out = dict(base)
    out["reasons"] = deduped if forced else []
    out["forced"] = forced
    if not forced:
        out["skipped_reason"] = "policy_not_triggered"
    return out


def apply_force_full_page_ocr_to_pipeline(pipeline_options: object, enabled: bool) -> bool:
    """
    Apply ``force_full_page_ocr`` when supported by the installed docling version.
    Returns True if a known attribute was set.
    """
    if not enabled:
        return False
    if hasattr(pipeline_options, "force_full_page_ocr"):
        setattr(pipeline_options, "force_full_page_ocr", True)
        return True
    ocr_opts = getattr(pipeline_options, "ocr_options", None)
    if ocr_opts is not None and hasattr(ocr_opts, "force_full_page_ocr"):
        setattr(ocr_opts, "force_full_page_ocr", True)
        return True
    return False
