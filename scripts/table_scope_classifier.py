#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Dict


NOTES_PATTERNS = (
    re.compile(r"\bnotes?\s+to\b", re.IGNORECASE),
    re.compile(r"\bnote\s+\d+\b", re.IGNORECASE),
)
GEOGRAPHIC_PATTERNS = (
    re.compile(r"\bgeographic(?:al)?\b", re.IGNORECASE),
    re.compile(r"\bregion(?:al)?\b", re.IGNORECASE),
    re.compile(r"\bcountry\b", re.IGNORECASE),
)
SEGMENT_PATTERNS = (
    re.compile(r"\boperating\s+segment\b", re.IGNORECASE),
    re.compile(r"\bsegment\b", re.IGNORECASE),
    re.compile(r"\bdivision\b", re.IGNORECASE),
    re.compile(r"\bbusiness\s+unit\b", re.IGNORECASE),
)
CONSOLIDATED_PATTERNS = (
    re.compile(r"\bconsolidated\b", re.IGNORECASE),
    re.compile(r"\bgroup\b", re.IGNORECASE),
    re.compile(r"\bcompany\b", re.IGNORECASE),
    re.compile(r"\bparent\b", re.IGNORECASE),
)


def _has_any(text: str, patterns) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def classify_table_scope(header_text: str, table_text: str) -> Dict[str, object]:
    try:
        header_text = str(header_text or "")
        table_text = str(table_text or "")
        header = " ".join(header_text.split()).lower()
        text = f"{header_text} {table_text}".lower()
        combined = " ".join(text.split())

        if _has_any(header, NOTES_PATTERNS) or _has_any(combined, NOTES_PATTERNS):
            return {"table_scope": "notes", "confidence": 0.95 if _has_any(header, NOTES_PATTERNS) else 0.8}
        if _has_any(header, GEOGRAPHIC_PATTERNS):
            return {"table_scope": "geographic", "confidence": 0.95}
        if _has_any(combined, GEOGRAPHIC_PATTERNS):
            return {"table_scope": "geographic", "confidence": 0.85}
        if _has_any(header, SEGMENT_PATTERNS):
            return {"table_scope": "segment", "confidence": 0.95}
        if _has_any(combined, SEGMENT_PATTERNS):
            return {"table_scope": "segment", "confidence": 0.85}
        if _has_any(header, CONSOLIDATED_PATTERNS):
            return {"table_scope": "consolidated", "confidence": 0.95}
        if _has_any(combined, CONSOLIDATED_PATTERNS):
            return {"table_scope": "consolidated", "confidence": 0.8}
        return {"table_scope": "unknown", "confidence": 0.0}
    except Exception:
        return {"table_scope": "unknown", "confidence": 0.0}
