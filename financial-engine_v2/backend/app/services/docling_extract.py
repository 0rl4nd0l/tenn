"""
docling_extract.py — Structured PDF extraction with table preservation and caching.

Replaces text_extract.py (flat PyMuPDF text) with docling's layout model,
which preserves 2D table structure (row labels + column values aligned).

Cache: {pdf_path}.docling.json (alongside the PDF, keyed by mtime).
Fallback: PyMuPDF flat text if docling fails (image PDFs, timeouts).
"""
from __future__ import annotations

import json
import logging
import os
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import importlib.metadata

import fitz  # PyMuPDF — fallback only

logger = logging.getLogger(__name__)

# Resolved once at import time so all cache reads/writes use the same value.
try:
    DOCLING_VERSION: str = importlib.metadata.version("docling")
except importlib.metadata.PackageNotFoundError:
    DOCLING_VERSION = "unknown"

DOCLING_TIMEOUT_SECONDS = 120
DOCLING_TIMEOUT_SECONDS_PER_PAGE = 4
DOCLING_TIMEOUT_MAX = 300


@dataclass
class DoclingTable:
    """One financial table extracted from the PDF."""
    page_number: int
    caption: str          # nearest heading text, or ""
    rows: list[list[str]] # rows[i][j] = cell text at row i, col j
    headers: list[str]    # first row, if detected as header


@dataclass
class StructuredDocument:
    """Full structured output for one PDF."""
    tables: list[DoclingTable] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)  # [{heading, text, page}]
    extraction_method: str = "docling"   # "docling" | "pymupdf_fallback"
    page_count: int = 0
    docling_version: str = ""  # populated at extraction time; used for cache invalidation


def _get_page_count_fast(pdf_path: str) -> int:
    """Return PDF page count using fitz metadata (no rendering — fast)."""
    try:
        with fitz.open(pdf_path) as doc:
            return len(doc)
    except Exception:
        return 0


def _compute_docling_timeout(page_count: int) -> int:
    """
    Adaptive timeout proportional to page count.
    Returns seconds: max(DOCLING_TIMEOUT_SECONDS, page_count * per_page) capped at DOCLING_TIMEOUT_MAX.
    """
    adaptive = page_count * DOCLING_TIMEOUT_SECONDS_PER_PAGE
    return min(DOCLING_TIMEOUT_MAX, max(DOCLING_TIMEOUT_SECONDS, adaptive))


def _extract_pymupdf(pdf_path: str) -> StructuredDocument:
    """Primary extractor using PyMuPDF find_tables() — fast, no ML models.

    Produces the same StructuredDocument as docling but in ~15-25s vs 120s+.
    Works well on native-text ASX filings.
    """
    tables: list[DoclingTable] = []
    sections: list[dict] = []

    with fitz.open(pdf_path) as doc:
        page_count = len(doc)

        for page_num_0, page in enumerate(doc):
            page_num = page_num_0 + 1

            # ── Sections: extract text blocks with heading detection ──
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            page_headings: list[tuple[float, str]] = []  # (y_pos, text)

            for block in blocks:
                if block["type"] != 0:  # text block
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    text = "".join(s["text"] for s in spans).strip()
                    if not text:
                        continue
                    # Detect heading by font size (>= 11pt) or bold
                    max_size = max(s["size"] for s in spans)
                    is_bold = any("bold" in s.get("font", "").lower() for s in spans)
                    is_heading = max_size >= 11.0 or (is_bold and max_size >= 9.5)
                    y_pos = line["bbox"][1]

                    if is_heading:
                        page_headings.append((y_pos, text))

                    sections.append({
                        "heading": is_heading,
                        "text": text,
                        "page": page_num,
                    })

            # ── Tables: extract with find_tables() ──
            try:
                tab_finder = page.find_tables()
                for tab in tab_finder.tables:
                    raw_rows = tab.extract()
                    if not raw_rows:
                        continue
                    rows_str = [[str(c or "") for c in row] for row in raw_rows]
                    headers = rows_str[0] if rows_str else []

                    # Caption: find nearest heading above the table's top edge
                    table_top_y = tab.bbox[1] if tab.bbox else 0
                    caption = ""
                    if page_headings:
                        above = [(y, t) for y, t in page_headings if y < table_top_y]
                        if above:
                            caption = above[-1][1]  # closest heading above

                    tables.append(DoclingTable(
                        page_number=page_num,
                        caption=caption,
                        rows=rows_str,
                        headers=headers,
                    ))
            except Exception as e:
                logger.debug("find_tables failed on page %d: %s", page_num, e)

    # ── Merge split tables across page breaks ──
    # If a table on page N+1 has no caption and its headers match
    # the previous table's headers, it's likely a continuation.
    merged_tables: list[DoclingTable] = []
    for table in tables:
        if (merged_tables
                and not table.caption
                and table.page_number == merged_tables[-1].page_number + 1
                and table.headers == merged_tables[-1].headers):
            # Continuation — append data rows (skip header row)
            merged_tables[-1].rows.extend(table.rows[1:])
            logger.debug(
                "Merged continuation table from page %d into page %d table",
                table.page_number, merged_tables[-1].page_number,
            )
        else:
            merged_tables.append(table)

    return StructuredDocument(
        tables=merged_tables,
        sections=sections,
        extraction_method="pymupdf",
        page_count=page_count,
        docling_version="",
    )


def extract_structured(pdf_path: str, *, backend: str = "") -> StructuredDocument:
    """
    Main entry point. Returns StructuredDocument for the given PDF path.

    backend selection (env EXTRACTION_BACKEND or kwarg):
      - "pymupdf" (default) — fast PyMuPDF find_tables(), no ML models
      - "docling" — IBM docling with TableFormer (slow, heavy, better on complex layouts)
      - "" — auto: uses pymupdf unless EXTRACTION_BACKEND=docling
    """
    chosen = backend or os.environ.get("EXTRACTION_BACKEND", "pymupdf")

    # Cache check (works for both backends)
    cache_suffix = ".docling.json" if chosen == "docling" else ".pymupdf.json"
    cache_path = Path(pdf_path + cache_suffix)
    pdf_mtime = os.path.getmtime(pdf_path)

    if cache_path.exists() and cache_path.stat().st_mtime > pdf_mtime:
        try:
            cached = _load_cache(cache_path)
            # For docling cache, validate version; pymupdf cache is always valid
            if chosen != "docling" or cached.docling_version == DOCLING_VERSION:
                logger.info("Using cached %s extraction for %s", cached.extraction_method, pdf_path)
                return cached
        except Exception as e:
            logger.warning("Cache corrupt, re-extracting: %s", e)

    if chosen == "docling":
        page_count = _get_page_count_fast(pdf_path)
        timeout = _compute_docling_timeout(page_count)
        if timeout != DOCLING_TIMEOUT_SECONDS:
            logger.info("docling adaptive timeout: %ds for %d-page PDF", timeout, page_count)
        try:
            result = _run_docling_with_timeout(pdf_path, timeout=timeout)
            _save_cache(cache_path, result)
            return result
        except Exception as e:
            logger.warning("docling failed (%s), falling back to PyMuPDF: %s", type(e).__name__, e)
            result = _extract_pymupdf(pdf_path)
            _save_cache(Path(pdf_path + ".pymupdf.json"), result)
            return result
    else:
        logger.info("PyMuPDF extraction: %s", pdf_path)
        result = _extract_pymupdf(pdf_path)
        _save_cache(cache_path, result)
        return result


def _run_docling_with_timeout(pdf_path: str, timeout: int = DOCLING_TIMEOUT_SECONDS) -> StructuredDocument:
    """Run docling with SIGALRM timeout. Raises on timeout or failure."""
    def _timeout_handler(signum, frame):
        raise TimeoutError(f"docling exceeded {timeout}s on {pdf_path}")

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout)
    try:
        return _run_docling(pdf_path)
    finally:
        signal.alarm(0)


def _run_docling(pdf_path: str) -> StructuredDocument:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    # Disable OCR: ASX PDFs are native-text; no OCR needed.
    pipeline_options = PdfPipelineOptions(do_ocr=False)
    converter = DocumentConverter(
        format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
    )
    result = converter.convert(pdf_path)
    doc = result.document

    tables: list[DoclingTable] = []
    for table_item in doc.tables:
        try:
            df = table_item.export_to_dataframe(doc=doc)
            rows = [list(df.columns)] + df.values.tolist()
            rows = [[str(c) for c in row] for row in rows]
            headers = rows[0] if rows else []
            caption = _extract_caption(table_item)
            page_num = getattr(table_item.prov[0], "page_no", 0) if table_item.prov else 0
            tables.append(DoclingTable(
                page_number=page_num,
                caption=caption,
                rows=rows,
                headers=headers,
            ))
        except Exception as e:
            logger.debug("Skipping malformed table: %s", e)

    sections: list[dict] = []
    for text_item in doc.texts:
        label = str(getattr(text_item, "label", "")).lower()
        text = (text_item.text or "").strip()
        if not text:
            continue
        page_num = getattr(text_item.prov[0], "page_no", 0) if text_item.prov else 0
        sections.append({
            "heading": label in ("section_header", "title", "chapter"),
            "text": text,
            "page": page_num,
        })

    page_count = len(set(s["page"] for s in sections)) or len(tables)
    return StructuredDocument(
        tables=tables,
        sections=sections,
        extraction_method="docling",
        page_count=page_count,
        docling_version=DOCLING_VERSION,
    )


def _pymupdf_fallback(pdf_path: str) -> StructuredDocument:
    """Fallback: extract flat text via PyMuPDF when docling fails."""
    sections = []
    tables = []
    try:
        with fitz.open(pdf_path) as fitz_doc:
            page_count = len(fitz_doc)
            for page_num, page in enumerate(fitz_doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    sections.append({"heading": False, "text": text, "page": page_num})
                # PyMuPDF 1.23+ table detection
                try:
                    for tab in page.find_tables():
                        rows = tab.extract()
                        if rows:
                            rows_str = [[str(c or "") for c in row] for row in rows]
                            tables.append(DoclingTable(
                                page_number=page_num,
                                caption="",
                                rows=rows_str,
                                headers=rows_str[0] if rows_str else [],
                            ))
                except Exception:
                    pass
    except Exception as e:
        logger.error("PyMuPDF fallback also failed: %s", e)
        page_count = 0

    return StructuredDocument(
        tables=tables,
        sections=sections,
        extraction_method="pymupdf_fallback",
        page_count=page_count,
        docling_version=DOCLING_VERSION,
    )


def _extract_caption(table_item) -> str:
    """Extract nearest heading/caption text for a table.
    Handles both .caption (str) and .captions (list) depending on docling version.
    """
    try:
        # docling >= 2.x uses .captions (list of TextItem)
        if hasattr(table_item, "captions") and table_item.captions:
            return str(table_item.captions[0].text if hasattr(table_item.captions[0], "text")
                       else table_item.captions[0])
        # older docling versions use .caption (str)
        if hasattr(table_item, "caption") and table_item.caption:
            return str(table_item.caption)
    except Exception:
        pass
    return ""


def _save_cache(cache_path: Path, doc: StructuredDocument) -> None:
    data = {
        "extraction_method": doc.extraction_method,
        "page_count": doc.page_count,
        "docling_version": doc.docling_version,
        "tables": [
            {
                "page_number": t.page_number,
                "caption": t.caption,
                "rows": t.rows,
                "headers": t.headers,
            }
            for t in doc.tables
        ],
        "sections": doc.sections,
    }
    cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _load_cache(cache_path: Path) -> StructuredDocument:
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    tables = [
        DoclingTable(
            page_number=t["page_number"],
            caption=t["caption"],
            rows=t["rows"],
            headers=t["headers"],
        )
        for t in data.get("tables", [])
    ]
    return StructuredDocument(
        tables=tables,
        sections=data.get("sections", []),
        extraction_method=data.get("extraction_method", "docling"),
        page_count=data.get("page_count", 0),
        docling_version=data.get("docling_version", ""),
    )
