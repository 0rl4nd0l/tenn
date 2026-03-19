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
    v = normalize_numeric_string(value)
    t = normalize_numeric_string(text)
    if not v:
        return False
    return v in t


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
