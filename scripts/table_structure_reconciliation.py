#!/usr/bin/env python3
"""Small table-shape repairs for extracted financial tables."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import pandas as pd  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency in tests
    pd = None


YEAR_COLUMN_RE = re.compile(
    r"\b(?:20\d{2}|FY\s*[-/]?\s*\d{2,4}|H[12]\s*(?:FY\s*)?[-/]?\s*\d{2,4}|Q[1-4]\s*(?:FY\s*)?[-/]?\s*\d{2,4})\b",
    re.IGNORECASE,
)
NUMERIC_CELL_RE = re.compile(r"^\(?-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)?$")


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _row_attr(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


def _normalize_identity_metric(metric: object) -> str:
    value = _normalize_text(metric).lower()
    if not value:
        return value
    if "revenue" in value:
        return "revenue"
    if "profit" in value:
        return "profit"
    if "cash" in value:
        return "cashflow"
    return value


def _normalize_identity_period(value: object) -> Optional[object]:
    if not value:
        return value
    if isinstance(value, datetime):
        return value.replace(day=1)
    if isinstance(value, date):
        return value.replace(day=1)
    text = _normalize_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text).replace(day=1).isoformat()
        except ValueError:
            return text
    return text


def compute_table_identity(rows: Sequence[Any]) -> Optional[Tuple[object, object, Tuple[str, ...]]]:
    if not rows:
        return None

    metrics = sorted(
        {
            _normalize_identity_metric(_row_attr(row, "metric"))
            for row in rows
            if _normalize_identity_metric(_row_attr(row, "metric"))
        }
    )

    period = _normalize_identity_period(_row_attr(rows[0], "period"))
    statement = _row_attr(rows[0], "statement_type")

    return (
        statement,
        period,
        tuple(metrics[:5]),
    )


def detect_year_columns(columns: Sequence[object]) -> List[int]:
    """Identify likely date/year value columns from a table header row."""
    indices: List[int] = []
    for idx, column in enumerate(columns):
        if YEAR_COLUMN_RE.search(_normalize_text(column)):
            indices.append(idx)
    return indices


def repair_column_shifts(rows: Sequence[Sequence[object]], year_columns: Sequence[int]) -> Tuple[List[List[object]], int]:
    """Shift numeric/date cells left inside detected year columns when a leading gap is obvious."""
    if not year_columns:
        return [list(row) for row in rows], 0

    repaired_rows: List[List[object]] = []
    repaired_count = 0
    year_column_positions = list(year_columns)

    for row in rows:
        row_values = list(row)
        segment = [row_values[idx] if idx < len(row_values) else "" for idx in year_column_positions]
        first_filled = next((idx for idx, value in enumerate(segment) if _normalize_text(value)), None)
        if first_filled in {None, 0}:
            repaired_rows.append(row_values)
            continue

        shifted_segment = segment[first_filled:] + [""] * first_filled
        if not any(
            NUMERIC_CELL_RE.match(_normalize_text(value)) or YEAR_COLUMN_RE.search(_normalize_text(value))
            for value in shifted_segment[:-first_filled or None]
        ):
            repaired_rows.append(row_values)
            continue

        for pos, column_idx in enumerate(year_column_positions):
            if column_idx < len(row_values):
                row_values[column_idx] = shifted_segment[pos]
        repaired_rows.append(row_values)
        repaired_count += 1

    return repaired_rows, repaired_count


def reconcile_table_dataframe(df: object) -> Tuple[object, Dict[str, object]]:
    """Apply lightweight year-column detection and left-shift repair to a dataframe."""
    if pd is None or not hasattr(df, "columns") or not hasattr(df, "values"):
        return df, {"year_columns": [], "repaired_rows": 0, "tsr_tables_processed": 1}

    year_columns = detect_year_columns(list(df.columns))
    raw_values = df.values
    if hasattr(raw_values, "tolist"):
        rows = raw_values.tolist()
    else:
        rows = [list(row) for row in list(raw_values)]
    repaired_rows, repaired_count = repair_column_shifts(rows, year_columns)
    if repaired_count <= 0:
        return df, {"year_columns": year_columns, "repaired_rows": 0, "tsr_tables_processed": 1}

    repaired_df = pd.DataFrame(repaired_rows, columns=df.columns)
    return repaired_df, {"year_columns": year_columns, "repaired_rows": repaired_count, "tsr_tables_processed": 1}
