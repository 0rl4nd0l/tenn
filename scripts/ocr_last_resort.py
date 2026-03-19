#!/usr/bin/env python3
"""OCR last-resort helpers with fail-closed behavior."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

NUMERIC_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")

MIN_TEXT_CHARS = 120
MIN_CHARS_PER_LINE = 12.0


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def is_pdftoppm_available() -> bool:
    return shutil.which("pdftoppm") is not None


def should_trigger_ocr(
    page_text: str,
    *,
    line_count: int,
    table_extraction_failed: bool,
) -> Tuple[bool, List[str]]:
    text = str(page_text or "")
    char_count = len(text.strip())
    density = float(char_count / max(1, int(line_count or 0)))

    reasons: List[str] = []
    if char_count < MIN_TEXT_CHARS:
        reasons.append("near_empty_text")
    if density < MIN_CHARS_PER_LINE:
        reasons.append("low_character_density")
    if table_extraction_failed and (char_count < (MIN_TEXT_CHARS * 2) or density < (MIN_CHARS_PER_LINE * 1.5)):
        reasons.append("table_extraction_failed")

    return len(reasons) > 0, reasons


def _render_pdf_page_to_png(pdf_path: Path, page_number: int, out_png: Path, dpi: int = 250) -> None:
    cmd = [
        "pdftoppm",
        "-png",
        "-singlefile",
        "-f",
        str(int(page_number)),
        "-l",
        str(int(page_number)),
        "-r",
        str(int(dpi)),
        str(pdf_path),
        str(out_png.with_suffix("")),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _run_tesseract_stdout(image_path: Path, lang: str = "eng", psm: int = 6) -> str:
    cmd = ["tesseract", str(image_path), "stdout", "-l", str(lang), "--psm", str(int(psm))]
    cp = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return str(cp.stdout or "")


def extract_ocr_candidates_for_page(
    pdf_path: Path,
    *,
    page_number: int,
    period_end: str,
    period_type: str,
    scope: str,
    statement_type: str,
    source_kind: str,
) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    stats = {
        "dependency_missing": 0,
        "pages_ocr_attempted": 0,
        "pages_ocr_succeeded": 0,
        "rows_emitted": 0,
    }

    if not is_tesseract_available() or not is_pdftoppm_available():
        stats["dependency_missing"] = 1
        return [], stats

    rows: List[Dict[str, object]] = []
    with tempfile.TemporaryDirectory() as td:
        img_path = Path(td) / f"ocr_p{int(page_number)}.png"
        try:
            stats["pages_ocr_attempted"] += 1
            _render_pdf_page_to_png(pdf_path, int(page_number), img_path)
            text = _run_tesseract_stdout(img_path)
            stats["pages_ocr_succeeded"] += 1
        except Exception:
            return [], stats

    for line in str(text).splitlines():
        ln = line.strip()
        if not ln:
            continue
        if not NUMERIC_RE.search(ln):
            continue
        rows.append(
            {
                "file": str(pdf_path),
                "metric": "",
                "metric_base": "",
                "row_label": ln,
                "line": ln,
                "raw_value": "",
                "value": "",
                "value_type": "amount",
                "currency": "UNKNOWN",
                "statement_scope": scope,
                "statement_type": scope,
                "statement_family": statement_type,
                "statement_period": period_type,
                "period": period_type,
                "statement_period_end": period_end,
                "source_mode": "ocr",
                "inside_table": False,
                "canonical_confidence_score": 0,
                "confidence": 1.0,
                "page_number": int(page_number),
                "table_page": int(page_number),
                "source_kind": source_kind,
                "ocr_candidate": 1,
            }
        )
    stats["rows_emitted"] = int(len(rows))
    return rows, stats


def collect_ocr_candidates_for_pdf(
    pdf_path: Path,
    *,
    pages: Sequence[int],
    prepared_pages: Dict[int, List[Dict[str, object]]],
    source_kind: str,
    table_failed_pages: Iterable[int] | None = None,
    period_end_hint: str = "",
    period_type_hint: str = "",
    scope_hint: str = "consolidated_statement",
    statement_type_hint: str = "cash_flow",
) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    table_failed = {int(p) for p in (table_failed_pages or [])}

    all_rows: List[Dict[str, object]] = []
    stats = {
        "pages_considered": 0,
        "pages_triggered": 0,
        "dependency_missing": 0,
        "pages_ocr_attempted": 0,
        "pages_ocr_succeeded": 0,
        "rows_emitted": 0,
    }

    for page in sorted({int(p) for p in pages if int(p) > 0}):
        page_lines = prepared_pages.get(page, [])
        page_text = "\n".join(str(r.get("text", "")) for r in page_lines if str(r.get("text", "")).strip())
        stats["pages_considered"] += 1
        trigger, _reasons = should_trigger_ocr(
            page_text,
            line_count=len(page_lines),
            table_extraction_failed=(page in table_failed),
        )
        if not trigger:
            continue
        stats["pages_triggered"] += 1

        rows, page_stats = extract_ocr_candidates_for_page(
            pdf_path,
            page_number=page,
            period_end=period_end_hint,
            period_type=period_type_hint,
            scope=scope_hint,
            statement_type=statement_type_hint,
            source_kind=source_kind,
        )
        for key in ("dependency_missing", "pages_ocr_attempted", "pages_ocr_succeeded", "rows_emitted"):
            stats[key] += int(page_stats.get(key, 0) or 0)
        all_rows.extend(rows)

    return all_rows, stats
