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


def extract_structured(pdf_path: str) -> StructuredDocument:
    """
    Main entry point. Returns StructuredDocument for the given PDF path.
    Reads from cache if fresh; runs docling otherwise.
    Falls back to PyMuPDF if docling fails or times out.
    """
    cache_path = Path(pdf_path + ".docling.json")
    pdf_mtime = os.path.getmtime(pdf_path)

    if cache_path.exists() and cache_path.stat().st_mtime > pdf_mtime:
        try:
            cached = _load_cache(cache_path)
            if cached.docling_version == DOCLING_VERSION:
                return cached
            logger.info(
                "docling version changed (%s → %s), re-extracting: %s",
                cached.docling_version,
                DOCLING_VERSION,
                cache_path,
            )
        except Exception as e:
            logger.warning("docling cache corrupt, re-extracting: %s", e)

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
        return _pymupdf_fallback(pdf_path)


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
