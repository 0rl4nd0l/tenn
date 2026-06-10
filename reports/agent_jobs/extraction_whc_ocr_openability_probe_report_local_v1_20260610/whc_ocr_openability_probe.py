#!/usr/bin/env python3
"""Report-local WHC OCR/openability probe.

This harness records provenance-only evidence for the exact WHC 2022 annual
report parser/openability gap. It never writes parser cache and never emits
accepted canonical metrics.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


JOB_ID = "extraction_whc_ocr_openability_probe_report_local_v1_20260610"
TICKER = "WHC"
DOCUMENT_ID = "9640d9f1-a45b-492d-8df5-9bad0f46431c"
DOCUMENT_TITLE = "2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf"
DEFAULT_SOURCE_PDF = Path(
    "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/"
    "2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf"
)
DEFAULT_CACHE_JSON = Path(
    "/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/financial-engine_v2/data/"
    "reports/extraction_cache/docling_extract/"
    "c6d4c5ceed51f73dfdc64480700dd460e5aed818dd35e85c37b0c5d9157f9a3d-"
    "2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf.pymupdf.json"
)
DEFAULT_SOURCE_DIAGNOSTIC = Path(
    "/home/l4nd0/tenn-whc-selected-statement-table-diagnostic-v1-20260610/reports/"
    "agent_jobs/extraction_whc_selected_statement_table_diagnostic_v1_20260610/"
    "source_pdf_diagnostic.json"
)
REPORT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = REPORT_ROOT / "whc_ocr_openability_probe.json"
APPROVED_PAGES = {56, 57, 58, 60, 61}
STATEMENT_TABLE_PAGES = {57, 58, 60}

STATEMENT_PATTERNS = {
    "income_statement": re.compile(
        r"statement\s+of\s+(?:comprehensive\s+)?income", re.IGNORECASE
    ),
    "balance_sheet": re.compile(
        r"statement\s+of\s+financial\s+position", re.IGNORECASE
    ),
    "cashflow_statement": re.compile(
        r"statement\s+of\s+cash\s+flows?", re.IGNORECASE
    ),
    "notes": re.compile(r"notes?\s+to\s+the\s+consolidated", re.IGNORECASE),
}
PERIOD_PATTERN = re.compile(
    r"(For the year ended\s+30\s+June\s+2022|As at\s+30\s+June\s+2022)",
    re.IGNORECASE,
)
SCALE_PATTERN = re.compile(
    r"(\$[\s']*000|nearest\s+thousand|rounded\s+to\s+the\s+nearest\s+thousand)",
    re.IGNORECASE,
)
ROW_PATTERNS = [
    re.compile(r"\bRevenue\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bProfit/\(loss\).*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bFinance expense\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bNet finance expense\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bNet profit/\(loss\).*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bCash and cash equivalents\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bInterest-bearing liabilities\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bTotal liabilities\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bNet assets\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bTotal equity\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bNet cash from operating activities\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bPurchase of property, plant and equipment\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bNet cash used in investing activities\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
    re.compile(r"\bNet cash used in financing activities\b.*?\(?-?\d[\d,]*(?:\.\d+)?\)?", re.IGNORECASE),
]


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    """Tiny subprocess wrapper so tests can inject mocked OCR command results."""

    def run(self, args: list[str], *, timeout: int = 120) -> CommandResult:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_pages(raw: str) -> list[int]:
    pages = [int(part.strip()) for part in raw.split(",") if part.strip()]
    assert_approved_pages(pages)
    return pages


def assert_approved_pages(pages: list[int]) -> None:
    unapproved = sorted({page for page in pages if page not in APPROVED_PAGES})
    if unapproved:
        raise ValueError(
            f"unapproved WHC OCR page(s): {unapproved}; approved={sorted(APPROVED_PAGES)}"
        )


def ensure_report_local_path(path: Path, report_root: Path = REPORT_ROOT) -> Path:
    resolved = path.expanduser().resolve()
    root = report_root.expanduser().resolve()
    resolved.relative_to(root)
    return resolved


def write_report_local_json(
    path: Path, payload: dict[str, Any], report_root: Path = REPORT_ROOT
) -> None:
    safe_path = ensure_report_local_path(path, report_root)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def flatten_cells(rows: list[Any]) -> list[str]:
    cells: list[str] = []
    for row in rows or []:
        if isinstance(row, list):
            cells.extend(str(cell or "") for cell in row)
        else:
            cells.append(str(row or ""))
    return cells


def page_cache_summary(cache_doc: dict[str, Any], pages: list[int]) -> dict[str, Any]:
    table_pages: dict[int, list[dict[str, Any]]] = {page: [] for page in pages}
    sections_by_page: dict[int, list[str]] = {page: [] for page in pages}

    for section in cache_doc.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        page = int(section.get("page") or 0)
        if page in sections_by_page:
            text = str(section.get("text") or "").strip()
            if text:
                sections_by_page[page].append(text)

    for table in cache_doc.get("tables", []) or []:
        if not isinstance(table, dict):
            continue
        page = int(table.get("page_number") or 0)
        if page not in table_pages:
            continue
        cells = flatten_cells(table.get("rows") or [])
        nonempty = [cell for cell in cells if cell.strip()]
        table_pages[page].append(
            {
                "caption": str(table.get("caption") or ""),
                "headers": [str(item or "") for item in table.get("headers", [])],
                "cell_count": len(cells),
                "nonempty_cell_count": len(nonempty),
                "sample_nonempty_cells": nonempty[:8],
            }
        )

    per_page = []
    for page in pages:
        tables = table_pages[page]
        nonempty_cells = sum(int(item["nonempty_cell_count"]) for item in tables)
        cell_count = sum(int(item["cell_count"]) for item in tables)
        page_text = "\n".join(sections_by_page[page])
        table_text = "\n".join(
            "\n".join(table["sample_nonempty_cells"]) + "\n" + table["caption"]
            for table in tables
        )
        per_page.append(
            {
                "page": page,
                "section_count": len(sections_by_page[page]),
                "section_samples": sections_by_page[page][:5],
                "table_count": len(tables),
                "table_cell_count": cell_count,
                "table_nonempty_cell_count": nonempty_cells,
                "statement_keyword_present": any(
                    pattern.search(page_text + "\n" + table_text)
                    for pattern in STATEMENT_PATTERNS.values()
                ),
                "scale_keyword_present": bool(SCALE_PATTERN.search(page_text + "\n" + table_text)),
                "tables": tables,
            }
        )

    total_tables = sum(int(item["table_count"]) for item in per_page)
    total_nonempty_cells = sum(int(item["table_nonempty_cell_count"]) for item in per_page)
    return {
        "extraction_method": cache_doc.get("extraction_method"),
        "page_count": cache_doc.get("page_count"),
        "source_pdf_page_count": cache_doc.get("source_pdf_page_count"),
        "tables_present_on_statement_pages": total_tables > 0,
        "statement_page_table_count": total_tables,
        "statement_page_nonempty_cell_count": total_nonempty_cells,
        "statement_cells_preserved": total_nonempty_cells > 0,
        "gap_classification": (
            "parser_openability_or_ocr_gap"
            if total_tables > 0 and total_nonempty_cells == 0
            else "DATA_MISSING"
        ),
        "per_page": per_page,
    }


def classify_statement(text: str) -> str | None:
    for label, pattern in STATEMENT_PATTERNS.items():
        if pattern.search(text):
            return label
    return None


def parse_row_candidates(text: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        for pattern in ROW_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            cell_text = match.group(0).strip()
            if cell_text in seen:
                continue
            seen.add(cell_text)
            candidates.append({"source_text": cell_text})
    return candidates


def parse_ocr_text(page: int, text: str, *, source: str) -> dict[str, Any]:
    period_matches = [match.group(1) for match in PERIOD_PATTERN.finditer(text)]
    scale_matches = [match.group(1) for match in SCALE_PATTERN.finditer(text)]
    statement = classify_statement(text)
    row_candidates = parse_row_candidates(text)
    return {
        "page": page,
        "source": source,
        "statement_label": statement,
        "statement_evidence_found": statement is not None,
        "period_phrases": sorted(set(period_matches)),
        "scale_phrases": sorted(set(scale_matches)),
        "row_candidates": row_candidates,
        "row_candidate_count": len(row_candidates),
        "verdict": "PROVENANCE_CAPTURED" if statement or row_candidates else "DATA_MISSING",
    }


def ocr_records_from_source_diagnostic(path: Path, pages: list[int]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    diagnostic = load_json(path)
    records: list[dict[str, Any]] = []
    for item in diagnostic.get("source_statement_evidence", []) or []:
        if not isinstance(item, dict):
            continue
        page = int(item.get("pdf_page") or 0)
        if page not in pages:
            continue
        text_parts = [
            str(item.get("statement") or ""),
            str(item.get("period") or ""),
            str(item.get("scale_evidence") or ""),
        ]
        text_parts.extend(str(row) for row in item.get("rows", []) or [])
        text = "\n".join(part for part in text_parts if part)
        parsed = parse_ocr_text(page, text, source="saved_source_pdf_diagnostic")
        parsed["report_page"] = item.get("report_page")
        parsed["source_type"] = item.get("type") or "statement_or_note"
        records.append(parsed)
    return records


def run_ocr_for_pages(
    pdf_path: Path,
    pages: list[int],
    runner: CommandRunner | None = None,
) -> list[dict[str, Any]]:
    assert_approved_pages(pages)
    runner = runner or CommandRunner()
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="whc-ocr-openability-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        for page in pages:
            prefix = tmp_root / f"page_{page}"
            render = runner.run(
                [
                    "pdftoppm",
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    "-r",
                    "200",
                    "-png",
                    str(pdf_path),
                    str(prefix),
                ],
                timeout=120,
            )
            if render.returncode != 0:
                records.append(
                    {
                        "page": page,
                        "source": "live_ocr",
                        "statement_evidence_found": False,
                        "verdict": "DATA_MISSING",
                        "error": "pdftoppm_failed",
                        "stderr": render.stderr.strip()[:500],
                    }
                )
                continue
            images = sorted(tmp_root.glob(f"page_{page}-*.png"))
            if not images:
                records.append(
                    {
                        "page": page,
                        "source": "live_ocr",
                        "statement_evidence_found": False,
                        "verdict": "DATA_MISSING",
                        "error": "rendered_image_missing",
                    }
                )
                continue
            ocr = runner.run(["tesseract", str(images[0]), "stdout"], timeout=120)
            if ocr.returncode != 0:
                records.append(
                    {
                        "page": page,
                        "source": "live_ocr",
                        "statement_evidence_found": False,
                        "verdict": "DATA_MISSING",
                        "error": "tesseract_failed",
                        "stderr": ocr.stderr.strip()[:500],
                    }
                )
                continue
            records.append(parse_ocr_text(page, ocr.stdout, source="live_ocr"))
    return records


def build_probe_payload(
    *,
    source_pdf: Path,
    cache_json: Path,
    source_diagnostic: Path,
    pages: list[int],
    mode: str,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    assert_approved_pages(pages)
    cache_pages = [page for page in pages if page in STATEMENT_TABLE_PAGES]
    cache_gap = (
        page_cache_summary(load_json(cache_json), cache_pages)
        if cache_json.exists()
        else {"gap_classification": "DATA_MISSING", "cache_path_missing": str(cache_json)}
    )
    if mode == "saved-evidence":
        ocr_records = ocr_records_from_source_diagnostic(source_diagnostic, pages)
    elif mode == "run-ocr":
        ocr_records = run_ocr_for_pages(source_pdf, pages, runner=runner)
    else:
        raise ValueError(f"unsupported mode: {mode}")

    statement_pages_found = [
        record.get("page")
        for record in ocr_records
        if record.get("statement_evidence_found") or record.get("row_candidate_count", 0) > 0
    ]
    scale_pages_found = [
        record.get("page") for record in ocr_records if record.get("scale_phrases")
    ]
    evidence_found = bool(statement_pages_found)
    cache_cells_missing = (
        cache_gap.get("tables_present_on_statement_pages") is True
        and cache_gap.get("statement_cells_preserved") is False
    )

    return {
        "job_id": JOB_ID,
        "provenance_only": True,
        "not_an_extraction_result": True,
        "canonical_output_changed": False,
        "parser_cache_written": False,
        "source_pdf_written": False,
        "ticker": TICKER,
        "document_id": DOCUMENT_ID,
        "document_title": DOCUMENT_TITLE,
        "source_pdf": str(source_pdf),
        "mode": mode,
        "approved_pages": pages,
        "statement_table_cache_pages": cache_pages,
        "cache_json": str(cache_json),
        "source_diagnostic": str(source_diagnostic),
        "cache_gap": cache_gap,
        "ocr_statement_records": ocr_records,
        "summary": {
            "ocr_or_saved_statement_pages_with_evidence": statement_pages_found,
            "ocr_or_saved_scale_pages_with_evidence": scale_pages_found,
            "source_statement_evidence_found": evidence_found,
            "cache_tables_present_but_cells_missing": cache_cells_missing,
            "classification": (
                "ocr_openability_provenance_gap"
                if evidence_found and cache_cells_missing
                else "DATA_MISSING"
            ),
            "canonical_repair_ready": False,
            "why_not_canonical_ready": (
                "Report-local OCR/source evidence is not fed into selected statement "
                "tables, row_refs, metric_source_scales, or canonical extraction gates."
            ),
        },
        "forbidden_actions_preserved": [
            "no extraction run",
            "no count sample",
            "no parser cache write",
            "no canonical metric output",
            "no source PDF mutation",
            "no DB/Qdrant/Redis/news/memory mutation",
            "no prompt/gold/schema/runtime/model/GPU mutation",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["saved-evidence", "run-ocr"], default="saved-evidence")
    parser.add_argument("--source-pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--cache-json", type=Path, default=DEFAULT_CACHE_JSON)
    parser.add_argument("--source-diagnostic", type=Path, default=DEFAULT_SOURCE_DIAGNOSTIC)
    parser.add_argument("--pages", default="56,57,58,60,61")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pages = parse_pages(args.pages)
    payload = build_probe_payload(
        source_pdf=args.source_pdf,
        cache_json=args.cache_json,
        source_diagnostic=args.source_diagnostic,
        pages=pages,
        mode=args.mode,
    )
    write_report_local_json(args.output, payload)
    print(json.dumps({"ok": True, "output": str(ensure_report_local_path(args.output))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
