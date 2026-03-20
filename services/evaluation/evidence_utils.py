#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any


def normalize_numeric_string(s: Any) -> str:
    if s is None:
        return ""
    return re.sub(r"[^\d]", "", str(s))


def numeric_match(value: Any, text: str | None) -> bool:
    if text is None:
        return False
    raw = str(text)
    if not raw:
        return False

    candidates: list[str] = []
    v0 = normalize_numeric_string(value)
    if v0:
        candidates.append(v0)

    # Add common scale variants (k/m/b) so extracted normalized values can still be
    # verified against PDF-rendered units like "1,234" or "1.234".
    try:
        num = float(value)
    except (TypeError, ValueError):
        num = None
    if num is not None:
        for scale in (1.0, 1e3, 1e6, 1e9, 1e12):
            scaled = num / scale
            for rounded in (round(scaled), round(scaled, 1), round(scaled, 2)):
                c = normalize_numeric_string(rounded)
                if c:
                    candidates.append(c)

    # De-dup candidates and reject empty.
    seen: set[str] = set()
    uniq: list[str] = []
    for c in candidates:
        if c and c not in seen:
            uniq.append(c)
            seen.add(c)
    if not uniq:
        return False

    sep = r"[,\s\.\u00A0]*"
    for v in uniq:
        escaped_digits = [re.escape(ch) for ch in v]
        body = sep.join(escaped_digits)
        pattern = re.compile(rf"(?<!\d){body}(?!\d)")
        if pattern.search(raw):
            return True
    return False


def verify_with_context(value: Any, label: Any, raw_text: str | None, window: int = 120) -> bool:
    if raw_text is None:
        return False
    norm_value = normalize_numeric_string(value)
    if not norm_value:
        return False
    label_lower = str(label or "").strip().lower()
    if not label_lower:
        return False

    text = str(raw_text)
    text_lower = text.lower()
    for match in re.finditer(re.escape(label_lower), text_lower):
        start = max(0, match.start() - int(window))
        end = min(len(text_lower), match.end() + int(window))
        snippet = text[start:end]
        if numeric_match(value, snippet):
            return True
    return False
