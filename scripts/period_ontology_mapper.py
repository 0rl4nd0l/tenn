#!/usr/bin/env python3
"""Canonical period-label normalization helpers for financial extraction."""

from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Callable, List, MutableMapping, Tuple


MONTH_TOKEN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

DATE_WORD_RE = re.compile(rf"\b(\d{{1,2}})\s+({MONTH_TOKEN})\s+(20\d{{2}})\b", re.IGNORECASE)
ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
FY_RE = re.compile(r"\bFY\s*[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
HY_RE = re.compile(r"\b(?:HY|H1|1H)\s*(?:FY\s*)?[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
H2_RE = re.compile(r"\b(?:H2|2H)\s*(?:FY\s*)?[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
FY_QUARTER_RE = re.compile(r"\bQ([1-4])\s*(?:FY\s*)?[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
CALENDAR_QUARTER_RE = re.compile(r"\bQ([1-4])\s+(20\d{2})\b", re.IGNORECASE)

PeriodResolver = Callable[[str, str, bool], Tuple[str, str]]


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_year(year_text: str) -> int:
    year = int(year_text)
    if year < 100:
        return 2000 + year
    return year


def _parse_date_label(text: str) -> date | None:
    iso_match = ISO_DATE_RE.search(text or "")
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None

    word_match = DATE_WORD_RE.search(text or "")
    if not word_match:
        return None

    day = int(word_match.group(1))
    year = int(word_match.group(3))
    month_token = word_match.group(2)[:3].title()
    try:
        month = list(calendar.month_abbr).index(month_token)
    except ValueError:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _quarter_end_for_doc_date(doc_date: date, previous: bool = False) -> date:
    quarter = ((doc_date.month - 1) // 3) + 1
    quarter_month = quarter * 3
    current = date(doc_date.year, quarter_month, calendar.monthrange(doc_date.year, quarter_month)[1])
    if not previous:
        return current
    if current.month == 3:
        year = current.year - 1
        month = 12
    else:
        year = current.year
        month = current.month - 3
    return date(year, month, calendar.monthrange(year, month)[1])


def canonicalize_period_label(period_label: object) -> str:
    """Return a normalized FY/H1/H2/Qn label when recognized."""
    label = _normalize_text(period_label)
    if not label:
        return ""

    match = HY_RE.search(label)
    if match:
        return f"H1 FY{_normalize_year(match.group(1))}"
    match = H2_RE.search(label)
    if match:
        return f"H2 FY{_normalize_year(match.group(1))}"
    match = FY_QUARTER_RE.search(label)
    if match:
        return f"Q{int(match.group(1))} FY{_normalize_year(match.group(2))}"
    match = FY_RE.search(label)
    if match:
        return f"FY{_normalize_year(match.group(1))}"
    match = CALENDAR_QUARTER_RE.search(label)
    if match:
        return f"Q{int(match.group(1))} {int(match.group(2))}"
    return label


def normalize_period_label(
    period_label: object,
    doc_date: str = "",
    allow_doc_date_fallback: bool = True,
) -> Tuple[str, str]:
    """Resolve a period label to canonical end/sort dates."""
    label = _normalize_text(period_label)
    if not label:
        if allow_doc_date_fallback and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(doc_date or "")):
            return str(doc_date), str(doc_date)
        return "", ""

    explicit = _parse_date_label(label)
    if explicit is not None:
        iso = explicit.isoformat()
        return iso, iso

    match = H2_RE.search(label)
    if match:
        fy_year = _normalize_year(match.group(1))
        iso = date(fy_year, 6, 30).isoformat()
        return iso, iso

    match = HY_RE.search(label)
    if match:
        fy_year = _normalize_year(match.group(1))
        iso = date(fy_year - 1, 12, 31).isoformat()
        return iso, iso

    match = FY_QUARTER_RE.search(label)
    if match:
        quarter = int(match.group(1))
        fy_year = _normalize_year(match.group(2))
        mapping = {
            1: date(fy_year - 1, 9, 30),
            2: date(fy_year - 1, 12, 31),
            3: date(fy_year, 3, 31),
            4: date(fy_year, 6, 30),
        }
        resolved = mapping.get(quarter)
        if resolved is not None:
            iso = resolved.isoformat()
            return iso, iso

    match = CALENDAR_QUARTER_RE.search(label)
    if match:
        quarter = int(match.group(1))
        year = int(match.group(2))
        month = quarter * 3
        resolved = date(year, month, calendar.monthrange(year, month)[1])
        iso = resolved.isoformat()
        return iso, iso

    match = FY_RE.search(label)
    if match:
        fy_year = _normalize_year(match.group(1))
        iso = date(fy_year, 6, 30).isoformat()
        return iso, iso

    if re.search(r"\bcurrent quarter\b", label, re.IGNORECASE) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(doc_date or "")):
        resolved = _quarter_end_for_doc_date(date.fromisoformat(str(doc_date)))
        iso = resolved.isoformat()
        return iso, iso

    if re.search(r"\b(?:previous|prior) quarter\b", label, re.IGNORECASE) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}", str(doc_date or "")
    ):
        resolved = _quarter_end_for_doc_date(date.fromisoformat(str(doc_date)), previous=True)
        iso = resolved.isoformat()
        return iso, iso

    if allow_doc_date_fallback and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(doc_date or "")):
        return str(doc_date), str(doc_date)
    return "", ""


def normalize_period_row(
    row: MutableMapping[str, object],
    *,
    resolver: PeriodResolver | None = None,
    allow_doc_date_fallback: bool = True,
) -> MutableMapping[str, object]:
    """Fill missing normalized period fields in place without overwriting explicit values."""
    label = _normalize_text(row.get("statement_period") or row.get("period"))
    if label:
        row["statement_period"] = str(row.get("statement_period", "")).strip() or canonicalize_period_label(label)
        row["period"] = str(row.get("period", "")).strip() or str(row.get("statement_period", "")).strip()

    existing_end = _normalize_text(row.get("statement_period_end") or row.get("period_end"))
    if existing_end:
        return row

    doc_date = _normalize_text(row.get("doc_date"))
    if not doc_date:
        file_hint = _normalize_text(row.get("file") or row.get("source_file") or row.get("pdf_path"))
        m = ISO_DATE_RE.search(file_hint)
        if m:
            doc_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    active_resolver = resolver or (lambda value, doc_date, allow_fallback: normalize_period_label(value, doc_date, allow_fallback))
    period_end, sort_date = active_resolver(label, doc_date, allow_doc_date_fallback)
    if period_end:
        row["statement_period_end"] = period_end
        row.setdefault("period_end", period_end)
    if sort_date and not str(row.get("statement_period_sort", "")).strip():
        row["statement_period_sort"] = sort_date
    return row


def normalize_period_rows(
    rows: List[MutableMapping[str, object]],
    *,
    resolver: PeriodResolver | None = None,
    allow_doc_date_fallback: bool = True,
) -> None:
    """Normalize period labels across a batch of extracted rows."""
    for row in rows:
        normalize_period_row(row, resolver=resolver, allow_doc_date_fallback=allow_doc_date_fallback)
