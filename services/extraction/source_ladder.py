#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

# Tier labels emitted in routed extraction JSON (stable API).
TIER_STRUCTURED_SOURCE = "structured_source"
TIER_NATIVE_PDF_LAYOUT = "native_pdf_layout"
TIER_SCANNED_PDF_LAYOUT = "scanned_pdf_layout"
TIER_CONSTRAINED_REPAIR = "constrained_repair"

_SOURCE_TIERS = frozenset(
    {
        TIER_STRUCTURED_SOURCE,
        TIER_NATIVE_PDF_LAYOUT,
        TIER_SCANNED_PDF_LAYOUT,
        TIER_CONSTRAINED_REPAIR,
    }
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _accumulate_keyword_score(text: str, patterns: tuple[tuple[str, float], ...]) -> float:
    """Sum weighted substring hits; normalize so a few strong hits reach ~1.0."""
    if not text:
        return 0.0
    t = text.lower()
    score = 0.0
    for pat, weight in patterns:
        if pat.lower() in t:
            score += weight
    return _clamp01(score / 3.0)


def _pdf_binary_sniff(pdf_path: Path, max_bytes: int = 65536) -> dict[str, Any]:
    hits: list[str] = []
    if not pdf_path.is_file():
        return {"binary_hits": hits}
    try:
        chunk = pdf_path.read_bytes()[:max_bytes]
    except OSError:
        return {"binary_hits": hits}
    needles = (
        (b"inline xbrl", "inline_xbrl_binary"),
        (b"InlineXBRL", "inline_xbrl_binary"),
        (b"IXBRL", "ixbrl_binary"),
        (b"ixbrl", "ixbrl_binary"),
        (b"XBRL", "xbrl_binary"),
        (b"xbrl", "xbrl_binary"),
        (b"ESEF", "esef_binary"),
        (b"esef", "esef_binary"),
        (b"taxonomy", "taxonomy_binary"),
        (b"linkbase", "linkbase_binary"),
        (b"edgar", "edgar_binary"),
    )
    lower = chunk.lower()
    for needle, label in needles:
        if needle.lower() in lower:
            hits.append(label)
    return {"binary_hits": sorted(set(hits))}


def _pdf_metadata_strings(pdf_path: Path) -> dict[str, Any]:
    """Best-effort PDF metadata / trailer strings (no network). Optional pymupdf."""
    meta_blob = ""
    if pdf_path.is_file():
        try:
            import fitz  # type: ignore[import-untyped]

            doc = fitz.open(pdf_path)
            m = doc.metadata
            if isinstance(m, dict):
                parts = [str(v) for v in m.values() if isinstance(v, str) and v.strip()]
                meta_blob = " ".join(parts)
            doc.close()
        except Exception:
            meta_blob = ""

    sniff = _pdf_binary_sniff(pdf_path)
    return {"metadata_text": meta_blob, **sniff}


def detect_structured_reporting_signals(
    pdf_path: str | Path,
    raw_text: str,
    filename: str,
) -> dict[str, Any]:
    """
    Heuristic cues for XBRL / iXBRL / ESEF / SEC-style structured reporting.
    Uses filename, extracted text, local PDF bytes/metadata only (no network).
    """
    path = Path(pdf_path)
    name = _norm(filename or path.name)
    text = raw_text or ""
    blob = _norm(text) + " " + name

    xbrl_patterns = (
        ("xbrl", 1.0),
        ("extensible business reporting", 1.2),
        ("taxonomy package", 0.8),
        ("taxonomy", 0.4),
        ("linkbase", 0.8),
        ("instance document", 0.6),
        ("xbrl instance", 0.9),
        ("contextref", 0.5),
        ("schemaref", 0.5),
    )
    ixbrl_patterns = (
        ("ixbrl", 1.0),
        ("inline xbrl", 1.1),
        ("inline-xbrl", 1.0),
        ("inline xhtml", 0.5),
        ("ix:nonfraction", 1.0),
        ("ix:nonnumeric", 1.0),
        ("ix:header", 0.6),
    )
    esef_patterns = (
        ("esef", 1.0),
        ("european single electronic format", 1.2),
        ("efrag", 0.5),
        ("dcef", 0.4),
        ("authority esef", 0.6),
    )
    sec_patterns = (
        ("sec filing", 0.9),
        ("united states securities", 0.7),
        ("edgar", 0.8),
        ("form 10-k", 0.9),
        ("form 10-q", 0.9),
        ("form 20-f", 0.8),
        ("form 8-k", 0.7),
        ("regulation s-k", 0.5),
        ("item 1a", 0.3),
        ("item 7", 0.3),
        ("10-k", 0.5),
        ("10-q", 0.5),
        ("20-f", 0.4),
        ("8-k", 0.3),
    )

    xbrl_score = max(
        _accumulate_keyword_score(blob, xbrl_patterns),
        0.25 if re.search(r"\bxbrl\b", blob, re.I) else 0.0,
    )
    ixbrl_score = max(
        _accumulate_keyword_score(blob, ixbrl_patterns),
        0.35 if re.search(r"\bixbrl\b|inline\s+xbrl", blob, re.I) else 0.0,
    )
    esef_score = max(
        _accumulate_keyword_score(blob, esef_patterns),
        0.3 if re.search(r"\besef\b", blob, re.I) else 0.0,
    )
    sec_like_score = max(
        _accumulate_keyword_score(blob, sec_patterns),
        0.25 if re.search(r"\b10[- ]?[kq]\b|\b20[-]?f\b|\b8[-]?k\b", blob, re.I) else 0.0,
    )

    filename_boost = 0.0
    if re.search(r"xbrl|ixbrl|inline", name, re.I):
        filename_boost = max(filename_boost, 0.35)
    if re.search(r"esef|european", name, re.I):
        filename_boost = max(filename_boost, 0.25)
    if re.search(r"10[-_]?[kq]|20[-_]?f|8[-_]?k|edgar|sec[_-]?filing", name, re.I):
        filename_boost = max(filename_boost, 0.2)

    pdf_extra = _pdf_metadata_strings(path)
    meta_text = str(pdf_extra.get("metadata_text") or "")
    if meta_text:
        meta_blob = _norm(meta_text)
        xbrl_score = max(xbrl_score, _accumulate_keyword_score(meta_blob, xbrl_patterns) * 0.9)
        ixbrl_score = max(ixbrl_score, _accumulate_keyword_score(meta_blob, ixbrl_patterns) * 0.9)
        esef_score = max(esef_score, _accumulate_keyword_score(meta_blob, esef_patterns) * 0.9)
        sec_like_score = max(sec_like_score, _accumulate_keyword_score(meta_blob, sec_patterns) * 0.9)

    binary_hits: list[str] = list(pdf_extra.get("binary_hits") or [])
    if binary_hits:
        if any("xbrl" in h for h in binary_hits):
            xbrl_score = max(xbrl_score, 0.45)
        if any("ixbrl" in h or "inline" in h for h in binary_hits):
            ixbrl_score = max(ixbrl_score, 0.5)
        if any("esef" in h for h in binary_hits):
            esef_score = max(esef_score, 0.45)

    xbrl_score = _clamp01(xbrl_score + filename_boost * 0.5)
    ixbrl_score = _clamp01(ixbrl_score + filename_boost * 0.5)
    esef_score = _clamp01(esef_score + filename_boost * 0.4)
    sec_like_score = _clamp01(sec_like_score + filename_boost * 0.4)

    combined = _clamp01(
        max(xbrl_score, ixbrl_score, esef_score * 0.95, sec_like_score * 0.9)
        + 0.05 * min(1.0, (xbrl_score + ixbrl_score + esef_score + sec_like_score) / 4.0)
    )

    return {
        "xbrl_score": round(xbrl_score, 6),
        "ixbrl_score": round(ixbrl_score, 6),
        "esef_score": round(esef_score, 6),
        "sec_like_score": round(sec_like_score, 6),
        "combined_structured_score": round(combined, 6),
        "xbrl_hint": xbrl_score >= 0.35,
        "ixbrl_hint": ixbrl_score >= 0.35,
        "esef_hint": esef_score >= 0.35,
        "sec_like_hint": sec_like_score >= 0.35,
        "filename_boost": round(filename_boost, 6),
        "pdf_binary_hits": binary_hits,
    }


def choose_source_tier(
    *,
    structured_signals: Mapping[str, Any],
    raw_text_len: int = 0,
    probe_row_count: int = 0,
    fallback_triggered: bool = False,
    docling_executed: bool = False,
    verification_ratio: float = 1.0,
    classifier: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """
    Map heuristics to a source tier for downstream extraction planning.
    Returns (tier, tier_reason).
    """
    sig = dict(structured_signals or {})
    combined = float(sig.get("combined_structured_score") or 0.0)
    xbrl = float(sig.get("xbrl_score") or 0.0)
    ixbrl = float(sig.get("ixbrl_score") or 0.0)
    esef = float(sig.get("esef_score") or 0.0)
    sec = float(sig.get("sec_like_score") or 0.0)

    if (
        combined >= 0.48
        or ixbrl >= 0.55
        or (xbrl >= 0.55 and (sig.get("ixbrl_hint") or ixbrl >= 0.35))
        or esef >= 0.55
        or (sec >= 0.6 and combined >= 0.35)
    ):
        return (
            TIER_STRUCTURED_SOURCE,
            "strong_structured_reporting_signals",
        )

    clf = dict(classifier or {})
    complexity = 0.0
    try:
        complexity = float(clf.get("complexity_score") or 0.0)
    except (TypeError, ValueError):
        complexity = 0.0

    text_len = max(0, int(raw_text_len))
    probe_rows = max(0, int(probe_row_count))
    vr = float(verification_ratio)
    if vr < 0.0:
        vr = 0.0
    if vr > 1.0:
        vr = 1.0

    # Likely image-only or heavily garbled text layer
    if text_len < 120 and probe_rows == 0 and combined < 0.25:
        return (
            TIER_SCANNED_PDF_LAYOUT,
            "minimal_extracted_text_and_no_table_rows",
        )
    if text_len < 400 and probe_rows <= 1 and complexity >= 0.55 and combined < 0.2:
        return (
            TIER_SCANNED_PDF_LAYOUT,
            "low_text_signal_with_layout_complexity",
        )

    # Evidence-text alignment weak or remediation-heavy
    if vr < 0.38 and combined < 0.35:
        return (
            TIER_CONSTRAINED_REPAIR,
            "low_verification_ratio_needs_constrained_repair",
        )
    if fallback_triggered and docling_executed and vr < 0.55 and complexity >= 0.45:
        return (
            TIER_CONSTRAINED_REPAIR,
            "fallback_docling_still_low_verification",
        )
    if complexity >= 0.72 and probe_rows >= 10 and vr < 0.62:
        return (
            TIER_CONSTRAINED_REPAIR,
            "high_layout_complexity_with_moderate_verification",
        )

    return (
        TIER_NATIVE_PDF_LAYOUT,
        "default_digital_pdf_text_layer",
    )


def is_valid_tier(tier: str) -> bool:
    return tier in _SOURCE_TIERS
