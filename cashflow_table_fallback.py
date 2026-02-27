#!/usr/bin/env python3
"""Camelot lattice fallback for cashflow table row recovery.

This module is intentionally narrow:
- cashflow pages only (caller enforces section gating)
- lattice flavor only
- returns row-like payloads for downstream phrase-anchored mapping
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


NUMERIC_TOKEN_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?%?")


def _read_tables_lattice(pdf_path: str, page_number: int):
    try:
        import camelot  # type: ignore
    except Exception:
        return [], {"error": "camelot_import_failed"}
    meta: Dict[str, object] = {}
    try:
        tables = list(camelot.read_pdf(pdf_path, pages=str(int(page_number)), flavor="lattice"))
    except Exception as exc:
        tables = []
        meta["lattice_error"] = f"camelot_read_failed:{type(exc).__name__}"
    if tables:
        meta["flavor"] = "lattice"
        return tables, meta

    # Stream is more tolerant for text-heavy/non-ruled tables; use it as a
    # fallback when lattice detects nothing.
    try:
        tables = list(camelot.read_pdf(pdf_path, pages=str(int(page_number)), flavor="stream"))
    except Exception as exc:
        meta["stream_error"] = f"camelot_read_failed:{type(exc).__name__}"
        return [], meta
    if tables:
        meta["flavor"] = "stream"
        return tables, meta
    meta["flavor"] = "none"
    return [], meta


def _norm_text(value: object) -> str:
    return str(value or "").strip()


def _extract_numeric_tokens_from_cells(cells: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for cell in cells:
        for tok in NUMERIC_TOKEN_RE.findall(cell or ""):
            t = str(tok).strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return out


def extract_cashflow_table_rows_with_camelot_with_stats(
    pdf_path: str,
    page_number: int,
) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    tables, meta = _read_tables_lattice(pdf_path, page_number)
    flavor = str(meta.get("flavor", "lattice")).strip().lower() or "lattice"
    rows: List[Dict[str, object]] = []
    if not tables:
        return rows, {
            "pages_scanned": 1,
            "tables_found": 0,
            "errors": 1 if any(k.endswith("_error") for k in meta.keys()) else 0,
        }

    for table_idx, table in enumerate(tables):
        df = getattr(table, "df", None)
        if df is None:
            continue
        try:
            iter_rows = df.iterrows()
        except Exception:
            continue
        for row_idx, row in iter_rows:
            cells = [_norm_text(v) for v in list(row.values)]
            if not cells:
                continue
            raw_label = cells[0] if cells else ""
            if not raw_label:
                # fallback: first non-empty cell as label
                for c in cells:
                    if c:
                        raw_label = c
                        break
            if not raw_label:
                continue
            numeric_tokens = _extract_numeric_tokens_from_cells(cells[1:] if len(cells) > 1 else cells)
            rows.append(
                {
                    "raw_label": raw_label,
                    "numeric_tokens": numeric_tokens,
                    "page_number": int(page_number),
                    "source": f"camelot_{flavor}",
                    "table_id": f"camelot:{flavor}:p{int(page_number)}:t{int(table_idx)}",
                    "table_row_idx": int(row_idx),
                }
            )

    return rows, {
        "pages_scanned": 1,
        "tables_found": int(len(tables)),
        "errors": 0,
    }


def extract_cashflow_table_rows_with_camelot(
    pdf_path: str,
    page_number: int,
) -> List[Dict[str, object]]:
    rows, _ = extract_cashflow_table_rows_with_camelot_with_stats(pdf_path, page_number)
    return rows
