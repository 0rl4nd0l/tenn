#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Sequence


STATEMENT_KEYWORDS = {
    "income_statement": (
        re.compile(r"\brevenue\b", re.IGNORECASE),
        re.compile(r"\bgross\s+profit\b", re.IGNORECASE),
        re.compile(r"\boperating\s+profit\b", re.IGNORECASE),
        re.compile(r"\bnet\s+profit\b", re.IGNORECASE),
        re.compile(r"\bearnings\s+per\s+share\b", re.IGNORECASE),
    ),
    "balance_sheet": (
        re.compile(r"\bassets?\b", re.IGNORECASE),
        re.compile(r"\bliabilities?\b", re.IGNORECASE),
        re.compile(r"\bequity\b", re.IGNORECASE),
        re.compile(r"\bshare\s+capital\b", re.IGNORECASE),
        re.compile(r"\bretained\s+earnings\b", re.IGNORECASE),
    ),
    "cash_flow_statement": (
        re.compile(r"\boperating\s+cash\s+flow\b", re.IGNORECASE),
        re.compile(r"\binvesting\s+activities\b", re.IGNORECASE),
        re.compile(r"\bfinancing\s+activities\b", re.IGNORECASE),
        re.compile(r"\bnet\s+change\s+in\s+cash\b", re.IGNORECASE),
    ),
}

NOTES_KEYWORDS = (
    re.compile(r"\bnotes?\s+to\s+the\s+financial\s+statements?\b", re.IGNORECASE),
    re.compile(r"\bdisclosure\b", re.IGNORECASE),
    re.compile(r"\bcontingent\s+liabilities?\b", re.IGNORECASE),
    re.compile(r"\bcommitments?\b", re.IGNORECASE),
    re.compile(r"^\s*note\s*$", re.IGNORECASE),
)


def _iter_text(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_text(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _iter_text(item)
        return
    text = str(value).strip()
    if text and text.lower() != "nan":
        yield text


def _count_matches(text: str, patterns: Sequence[re.Pattern[str]]) -> int:
    return sum(1 for pattern in patterns if pattern.search(text))


def classify_table_statement(table_rows: Any) -> Dict[str, object]:
    text = "\n".join(_iter_text(table_rows)).strip()
    if not text:
        return {"statement_type": "unknown", "confidence": 0.0}

    scores = {
        statement_type: _count_matches(text, patterns)
        for statement_type, patterns in STATEMENT_KEYWORDS.items()
    }
    note_hits = _count_matches(text, NOTES_KEYWORDS)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best_type, best_hits = ranked[0]
    second_hits = ranked[1][1] if len(ranked) > 1 else 0

    if note_hits >= 2 and best_hits <= 1:
        confidence = round(min(0.99, note_hits / len(NOTES_KEYWORDS)), 2)
        return {"statement_type": "notes", "confidence": confidence}

    if best_hits <= 0:
        if note_hits > 0:
            confidence = round(min(0.99, note_hits / len(NOTES_KEYWORDS)), 2)
            return {"statement_type": "notes", "confidence": confidence}
        return {"statement_type": "unknown", "confidence": 0.0}

    if best_hits == second_hits:
        return {"statement_type": "unknown", "confidence": 0.0}

    confidence = round(
        min(
            0.99,
            (best_hits / len(STATEMENT_KEYWORDS[best_type]))
            + (0.15 * ((best_hits - second_hits) / len(STATEMENT_KEYWORDS[best_type]))),
        ),
        2,
    )
    return {"statement_type": best_type, "confidence": confidence}
