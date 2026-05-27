"""
docling_extract.py — Structured PDF extraction with table preservation and caching.

Replaces text_extract.py (flat PyMuPDF text) with docling's layout model,
which preserves 2D table structure (row labels + column values aligned).

Cache: data_root/reports/extraction_cache/docling_extract/*.json, keyed by
source path and source file metadata so source PDFs remain read-only inputs.
Fallback: PyMuPDF flat text if docling fails (image PDFs, timeouts).
"""

from __future__ import annotations

import hashlib
import json
import logging
import multiprocessing as mp
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import importlib.metadata

import fitz  # PyMuPDF — fallback only

from app.core.config import settings

logger = logging.getLogger(__name__)

# Resolved once at import time so all cache reads/writes use the same value.
try:
    DOCLING_VERSION: str = importlib.metadata.version("docling")
except importlib.metadata.PackageNotFoundError:
    DOCLING_VERSION = "unknown"

DOCLING_TIMEOUT_SECONDS = 120
DOCLING_TIMEOUT_SECONDS_PER_PAGE = 6
DOCLING_TIMEOUT_MAX = 600
DOCLING_TIMEOUT_MAX_STRICT = 1200
DOCLING_LARGE_PDF_PAGE_THRESHOLD = 200
DOCLING_LARGE_PDF_SIZE_THRESHOLD_BYTES = 12 * 1024 * 1024
DOCLING_CACHE_PAGE_GAP_TOLERANCE = 2
DOCLING_PAGE_BATCH_PROFILE_PATH_ENV = "DOCLING_PAGE_BATCH_PROFILE_PATH"
DOCLING_PAGE_BATCH_PROFILE_TARGET_ENV = "DOCLING_PAGE_BATCH_PROFILE_TARGET"
DOCLING_PAGE_BATCH_PROFILE_BATCH_SIZE_ENV = "DOCLING_PAGE_BATCH_PROFILE_BATCH_SIZE"
DOCLING_PAGE_BATCH_PROFILE_DEFAULT_BATCH_SIZE = 8
DOCLING_EXTRACT_CACHE_DIR = "docling_extract"


class ExtractionTimeoutError(Exception):
    """Raised when Docling extraction exceeds the time budget."""
    pass


@dataclass
class DoclingTable:
    """One financial table extracted from the PDF."""

    page_number: int
    caption: str  # nearest heading text, or ""
    rows: list[list[str]]  # rows[i][j] = cell text at row i, col j
    headers: list[str]  # first row, if detected as header


@dataclass
class StructuredDocument:
    """Full structured output for one PDF."""

    tables: list[DoclingTable] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)  # [{heading, text, page}]
    extraction_method: str = "docling"  # "docling" | "pymupdf_fallback"
    page_count: int = 0
    source_pdf_page_count: int = 0
    docling_version: str = (
        ""  # populated at extraction time; used for cache invalidation
    )


def validate_docling_environment() -> None:
    if DOCLING_VERSION == "unknown":
        raise RuntimeError("docling environment invalid: package not installed")
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: F401
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"docling environment invalid: {exc}") from exc


def _is_garbled(text: str) -> bool:
    """Detect font-encoding garbling (e.g. +3 ASCII shift from PDF font subsetting).

    Pattern: leading non-alpha char in ASCII 33-57 followed by 3+ uppercase letters
    with no intervening space.  This is the hallmark of a PDF whose font subset
    maps glyph codepoints with a fixed offset, producing strings like
    ")LQDO GLYLGHQG" instead of "FINAL DIVIDEND".
    """
    s = text.strip()
    if len(s) < 4:
        return False
    first = s[0]
    if not (33 <= ord(first) <= 57 and not first.isalpha()):
        return False
    following = s[1:5]
    alpha_upper = [c for c in following if c.isalpha()]
    return len(alpha_upper) >= 3 and all(c.isupper() for c in alpha_upper)


def _has_garbled_tables(doc: StructuredDocument, pdf_path: str) -> bool:
    """Sample table cells from a docling result; return True if garbling detected."""
    sample_cells: list[str] = []
    for table in doc.tables[:3]:
        for row in table.rows[:5]:
            for cell in row:
                if isinstance(cell, str) and len(cell.strip()) >= 4:
                    sample_cells.append(cell.strip())
                    if len(sample_cells) >= 15:
                        break
            if len(sample_cells) >= 15:
                break

    if not sample_cells:
        return False

    garbled_count = sum(1 for c in sample_cells if _is_garbled(c))
    if garbled_count >= 2:
        logger.warning(
            "Docling output appears font-garbled for %s (%d/%d sampled cells) "
            "— falling back to PyMuPDF",
            pdf_path,
            garbled_count,
            len(sample_cells),
        )
        return True
    return False


def _get_page_count_fast(pdf_path: str) -> int:
    """Return PDF page count using fitz metadata (no rendering — fast)."""
    try:
        with fitz.open(pdf_path) as doc:
            return len(doc)
    except Exception:
        return 0


def _extract_cache_root() -> Path:
    data_root = Path(settings.data_root).expanduser().resolve()
    root = (
        data_root / "reports" / "extraction_cache" / DOCLING_EXTRACT_CACHE_DIR
    ).resolve()
    root.relative_to(data_root)
    return root


def _safe_cache_label(pdf_path: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(pdf_path).name).strip("._")
    return label[:96] or "document"


def _cache_key_material(pdf_path: str) -> str:
    source_path = Path(pdf_path).expanduser()
    resolved = str(source_path.resolve(strict=False))
    try:
        stat = source_path.stat()
    except OSError:
        return f"path={resolved}"
    return f"path={resolved}\0size={stat.st_size}\0mtime_ns={stat.st_mtime_ns}"


def _cache_path_for_pdf(pdf_path: str, cache_suffix: str) -> Path:
    if cache_suffix not in {".docling.json", ".pymupdf.json"}:
        raise ValueError(f"unsupported extraction cache suffix: {cache_suffix}")
    root = _extract_cache_root()
    digest = hashlib.sha256(_cache_key_material(pdf_path).encode("utf-8")).hexdigest()
    candidate = (
        root / f"{digest}-{_safe_cache_label(pdf_path)}{cache_suffix}"
    ).resolve()
    candidate.relative_to(root)
    return candidate


def _pymupdf_cache_path(pdf_path: str) -> Path:
    return _cache_path_for_pdf(pdf_path, ".pymupdf.json")


def _compute_docling_timeout(page_count: int, *, strict_backend: bool = False) -> int:
    """
    Adaptive timeout proportional to page count.
    Returns seconds: max(DOCLING_TIMEOUT_SECONDS, page_count * per_page) capped at
    the mode-appropriate timeout ceiling.
    """
    adaptive = page_count * DOCLING_TIMEOUT_SECONDS_PER_PAGE
    timeout_cap = DOCLING_TIMEOUT_MAX_STRICT if strict_backend else DOCLING_TIMEOUT_MAX
    return min(timeout_cap, max(DOCLING_TIMEOUT_SECONDS, adaptive))


def _docling_profile_batch_size() -> int:
    raw = str(
        os.environ.get(
            DOCLING_PAGE_BATCH_PROFILE_BATCH_SIZE_ENV,
            str(DOCLING_PAGE_BATCH_PROFILE_DEFAULT_BATCH_SIZE),
        )
        or ""
    ).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return DOCLING_PAGE_BATCH_PROFILE_DEFAULT_BATCH_SIZE
    return max(1, min(parsed, 100))


def _docling_page_batch_ranges(
    *,
    page_count: int,
    batch_size: int,
) -> list[tuple[int, int]]:
    if page_count <= 0:
        return []
    ranges: list[tuple[int, int]] = []
    start = 1
    while start <= page_count:
        end = min(page_count, start + batch_size - 1)
        ranges.append((start, end))
        start = end + 1
    return ranges


def _docling_page_batch_profile_enabled(pdf_path: str) -> bool:
    out_path = str(os.environ.get(DOCLING_PAGE_BATCH_PROFILE_PATH_ENV) or "").strip()
    if not out_path:
        return False
    target = str(os.environ.get(DOCLING_PAGE_BATCH_PROFILE_TARGET_ENV) or "").strip()
    if not target:
        return True
    pdf_name = Path(pdf_path).name
    return target in pdf_path or target == pdf_name


def _profile_docling_page_batches(
    *,
    pdf_path: str,
    converter: Any,
    page_count: int,
    batch_size: int,
) -> list[dict[str, object]]:
    ranges = _docling_page_batch_ranges(page_count=page_count, batch_size=batch_size)
    if not ranges:
        return []

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="docling-page-batch-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        with fitz.open(pdf_path) as src_doc:
            for start, end in ranges:
                batch_pdf = tmp_root / f"pages_{start:04d}_{end:04d}.pdf"
                slice_doc = fitz.open()
                try:
                    slice_doc.insert_pdf(src_doc, from_page=start - 1, to_page=end - 1)
                    slice_doc.save(str(batch_pdf))
                finally:
                    slice_doc.close()

                t0 = time.perf_counter()
                error = None
                try:
                    converter.convert(str(batch_pdf))
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)
                elapsed = time.perf_counter() - t0
                rows.append(
                    {
                        "range_start": start,
                        "range_end": end,
                        "page_count": end - start + 1,
                        "elapsed_seconds": round(elapsed, 6),
                        "error": error,
                    }
                )
                if error:
                    break

    return rows


def _write_docling_page_batch_profile(payload: dict[str, object]) -> None:
    out_path = str(os.environ.get(DOCLING_PAGE_BATCH_PROFILE_PATH_ENV) or "").strip()
    if not out_path:
        return
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _observed_page_numbers(doc: StructuredDocument) -> list[int]:
    pages = {
        int(page)
        for page in (
            [t.page_number for t in doc.tables]
            + [s.get("page", 0) for s in doc.sections if isinstance(s, dict)]
        )
        if isinstance(page, int) and page > 0
    }
    return sorted(pages)


def _docling_cache_looks_stale(
    cached: StructuredDocument,
    *,
    pdf_path: str,
    actual_pdf_page_count: int,
) -> bool:
    """Reject obviously partial docling caches before trusting them."""
    if actual_pdf_page_count <= 0:
        return False

    cached_source_page_count = int(cached.source_pdf_page_count or 0)
    if (
        cached_source_page_count > 0
        and cached_source_page_count != actual_pdf_page_count
    ):
        logger.warning(
            "Docling cache page-count metadata mismatch for %s: cached=%d actual=%d",
            pdf_path,
            cached_source_page_count,
            actual_pdf_page_count,
        )
        return True

    observed_pages = _observed_page_numbers(cached)
    observed_max_page = observed_pages[-1] if observed_pages else 0
    cached_page_count = int(cached.page_count or 0)
    page_count_gap = actual_pdf_page_count - cached_page_count
    observed_gap = actual_pdf_page_count - observed_max_page

    if (
        cached_page_count > 0
        and observed_max_page > 0
        and page_count_gap > DOCLING_CACHE_PAGE_GAP_TOLERANCE
        and observed_gap > DOCLING_CACHE_PAGE_GAP_TOLERANCE
    ):
        logger.warning(
            "Docling cache coverage stale for %s: cached_page_count=%d observed_max_page=%d actual=%d",
            pdf_path,
            cached_page_count,
            observed_max_page,
            actual_pdf_page_count,
        )
        return True

    return False


def _should_preempt_docling_for_large_pdf(pdf_path: str, page_count: int) -> bool:
    """
    Return True when a PDF matches the known large-doc crash profile.

    This stays intentionally narrow: the only confirmed corpus failure is a 238-page,
    14.8 MB annual report that crashes docling. We require both a high page count
    and a large file size so the pre-check remains a surgical resilience guard
    instead of a policy shift away from docling.
    """
    if page_count < DOCLING_LARGE_PDF_PAGE_THRESHOLD:
        return False
    try:
        file_size = int(Path(pdf_path).stat().st_size)
    except OSError:
        return False
    return file_size >= DOCLING_LARGE_PDF_SIZE_THRESHOLD_BYTES


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
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)[
                "blocks"
            ]
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

                    sections.append(
                        {
                            "heading": is_heading,
                            "text": text,
                            "page": page_num,
                        }
                    )

            # ── Tables: extract with find_tables() ──
            try:
                tab_finder = page.find_tables()
                if not tab_finder.tables:
                    tab_finder = page.find_tables(strategy="text")
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

                    tables.append(
                        DoclingTable(
                            page_number=page_num,
                            caption=caption,
                            rows=rows_str,
                            headers=headers,
                        )
                    )
            except Exception as e:
                logger.debug("find_tables failed on page %d: %s", page_num, e)

    # ── Merge split tables across page breaks ──
    # If a table on page N+1 has no caption and its headers match
    # the previous table's headers, it's likely a continuation.
    merged_tables: list[DoclingTable] = []
    for table in tables:
        if (
            merged_tables
            and not table.caption
            and table.page_number == merged_tables[-1].page_number + 1
            and table.headers == merged_tables[-1].headers
        ):
            # Continuation — append data rows (skip header row)
            merged_tables[-1].rows.extend(table.rows[1:])
            logger.debug(
                "Merged continuation table from page %d into page %d table",
                table.page_number,
                merged_tables[-1].page_number,
            )
        else:
            merged_tables.append(table)

    result = StructuredDocument(
        tables=merged_tables,
        sections=sections,
        extraction_method="pymupdf",
        page_count=page_count,
        docling_version="",
    )

    # Quality gate: flag garbled output so downstream consumers can decide.
    # Does NOT raise — pymupdf is the last-resort backend; a degraded result
    # is better than no result.  The "pymupdf_degraded" method tag lets
    # callers distinguish clean vs. garbled output.
    if merged_tables and _has_garbled_tables(result, pdf_path):
        logger.warning(
            "PyMuPDF extraction produced garbled tables for %s — "
            "marking as pymupdf_degraded",
            pdf_path,
        )
        result.extraction_method = "pymupdf_degraded"

    return result


def extract_structured(
    pdf_path: str,
    *,
    backend: str = "",
    strict_backend: bool = False,
) -> StructuredDocument:
    """
    Main entry point. Returns StructuredDocument for the given PDF path.

    backend selection (env EXTRACTION_BACKEND or kwarg):
      - "docling" (default) — IBM docling with TableFormer (slow, heavy, better on complex layouts)
      - "pymupdf" — fast PyMuPDF find_tables(), no ML models
      - "" — auto: uses docling unless EXTRACTION_BACKEND is set
    """
    chosen = backend or os.environ.get("EXTRACTION_BACKEND", "docling")
    if chosen == "docling" and strict_backend:
        validate_docling_environment()

    # Cache check (works for both backends)
    cache_suffix = ".docling.json" if chosen == "docling" else ".pymupdf.json"
    cache_path = _cache_path_for_pdf(pdf_path, cache_suffix)
    pdf_mtime = os.path.getmtime(pdf_path)
    actual_pdf_page_count = _get_page_count_fast(pdf_path)

    if cache_path.exists() and cache_path.stat().st_mtime > pdf_mtime:
        try:
            cached = _load_cache(cache_path)
            # For docling cache, validate version; pymupdf cache is always valid
            if chosen != "docling" or cached.docling_version == DOCLING_VERSION:
                if chosen == "docling" and _docling_cache_looks_stale(
                    cached,
                    pdf_path=pdf_path,
                    actual_pdf_page_count=actual_pdf_page_count,
                ):
                    raise RuntimeError(
                        f"stale docling cache coverage for {pdf_path}"
                    )
                if chosen == "docling" and _has_garbled_tables(cached, pdf_path):
                    if strict_backend:
                        raise RuntimeError(
                            f"docling strict backend rejected garbled cached output for {pdf_path}"
                        )
                    result = _extract_pymupdf(pdf_path)
                    _save_cache(_pymupdf_cache_path(pdf_path), result)
                    return result
                logger.info(
                    "Using cached %s extraction for %s",
                    cached.extraction_method,
                    pdf_path,
                )
                return cached
        except Exception as e:
            logger.warning("Cache corrupt, re-extracting: %s", e)
            try:
                cache_path.unlink(missing_ok=True)
            except OSError as unlink_error:
                logger.warning(
                    "Failed to delete stale cache %s: %s", cache_path, unlink_error
                )

    if chosen == "docling":
        page_count = actual_pdf_page_count
        if not strict_backend and _should_preempt_docling_for_large_pdf(
            pdf_path, page_count
        ):
            logger.warning(
                "docling large-pdf precheck triggered for %s (pages=%d) — using PyMuPDF fallback",
                pdf_path,
                page_count,
            )
            result = _extract_pymupdf(pdf_path)
            _save_cache(_pymupdf_cache_path(pdf_path), result)
            return result
        timeout = _compute_docling_timeout(page_count, strict_backend=strict_backend)
        if timeout != DOCLING_TIMEOUT_SECONDS:
            logger.info(
                "docling adaptive timeout: %ds for %d-page PDF", timeout, page_count
            )
        try:
            result = _run_docling_with_timeout(pdf_path, timeout=timeout)
            _save_cache(cache_path, result)
            if _has_garbled_tables(result, pdf_path):
                if strict_backend:
                    raise RuntimeError(
                        f"docling strict backend rejected garbled output for {pdf_path}"
                    )
                logger.warning(
                    "docling output quality fallback triggered for %s; using PyMuPDF",
                    pdf_path,
                )
                result = _extract_pymupdf(pdf_path)
                _save_cache(_pymupdf_cache_path(pdf_path), result)
                return result
            return result
        except (TimeoutError, ExtractionTimeoutError) as te:
            logger.error("docling timeout for %s: %s", pdf_path, te)
            if strict_backend:
                raise RuntimeError(
                    f"docling strict backend failed: {te}"
                ) from te
            logger.warning(
                "docling timeout fallback triggered for %s; using PyMuPDF",
                pdf_path,
            )
            result = _extract_pymupdf(pdf_path)
            _save_cache(_pymupdf_cache_path(pdf_path), result)
            return result
        except Exception as e:
            logger.error("docling failed for %s: %s", pdf_path, e)
            if strict_backend:
                raise RuntimeError(f"docling strict backend failed: {e}") from e
            logger.warning(
                "docling failure fallback triggered for %s; using PyMuPDF",
                pdf_path,
            )
            result = _extract_pymupdf(pdf_path)
            _save_cache(_pymupdf_cache_path(pdf_path), result)
            return result
    else:
        logger.info("PyMuPDF extraction: %s", pdf_path)
        result = _extract_pymupdf(pdf_path)
        _save_cache(cache_path, result)
        return result


_docling_pool: Optional[ProcessPoolExecutor] = None
_docling_pool_lock = threading.Lock()


def _get_docling_pool() -> ProcessPoolExecutor:
    """Lazy-init a spawn-context process pool for Docling.

    Docling imports torch/CUDA; fork() copies CUDA state into children and
    breaks initialization. Spawn gives each worker a fresh Python interpreter.
    A single worker is sufficient — extraction is already serialized elsewhere,
    and we only need process isolation for hard wall-clock timeouts.

    Guarded by ``_docling_pool_lock`` because the now-sync FastAPI handler is
    executed on the anyio threadpool, so concurrent requests may race here.
    """
    global _docling_pool
    with _docling_pool_lock:
        if _docling_pool is None:
            ctx = mp.get_context("spawn")
            _docling_pool = ProcessPoolExecutor(max_workers=1, mp_context=ctx)
        return _docling_pool


def _reset_docling_pool() -> None:
    """Tear down the pool after a timeout so the next call respawns a clean worker.

    Note: ``shutdown(wait=False, cancel_futures=True)`` detaches the parent from
    the pool but does not ``SIGKILL`` a child that is blocked inside a CUDA
    kernel. Such a child will continue to hold VRAM until it exits on its own
    or the parent process terminates. With ``max_workers=1`` this is acceptable
    for rare timeouts; repeated pathological inputs would require direct
    ``multiprocessing.Process.terminate()`` management instead of a pool.
    """
    global _docling_pool
    with _docling_pool_lock:
        if _docling_pool is not None:
            _docling_pool.shutdown(wait=False, cancel_futures=True)
            _docling_pool = None


def _run_docling_with_timeout(
    pdf_path: str,
    timeout: float = DOCLING_TIMEOUT_SECONDS,
    *,
    runner: Optional[Callable[[str], StructuredDocument]] = None,
    executor: Optional[ProcessPoolExecutor] = None,
) -> StructuredDocument:
    """Run docling in a worker with a wall-clock timeout.

    Uses a spawn-based process pool so extraction cannot wedge the parent
    FastAPI event loop. The previous SIGALRM-based approach was main-thread-only
    and broke under FastAPI worker-thread execution.

    Args:
        pdf_path: PDF to extract.
        timeout: Seconds before ExtractionTimeoutError is raised.
        runner: Test seam; when None, ``_run_docling`` is used.
        executor: Test seam; when None, the module-level spawn pool is used.

    Raises:
        ExtractionTimeoutError: when the worker exceeds ``timeout`` seconds.
    """
    call = runner if runner is not None else _run_docling
    using_default_pool = executor is None
    pool = executor if executor is not None else _get_docling_pool()
    future = pool.submit(call, pdf_path)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError as exc:
        future.cancel()
        if using_default_pool:
            _reset_docling_pool()
        raise ExtractionTimeoutError(
            f"docling exceeded {timeout}s on {pdf_path}"
        ) from exc


def _run_docling(pdf_path: str) -> StructuredDocument:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorDevice, AcceleratorOptions
    import torch

    # Enable GPU if available
    device = AcceleratorDevice.AUTO
    if torch.cuda.is_available():
        device = AcceleratorDevice.CUDA
        logger.info("Docling using GPU (CUDA) for %s", pdf_path)
    else:
        logger.info("Docling using CPU for %s", pdf_path)

    # Disable OCR: ASX PDFs are native-text; no OCR needed.
    pipeline_options = PdfPipelineOptions(
        do_ocr=False,
        accelerator_options=AcceleratorOptions(device=device)
    )
    converter = DocumentConverter(
        format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
    )
    convert_started_at = time.perf_counter()
    try:
        result = converter.convert(pdf_path)
    except RuntimeError as e:
        if "Pipeline StandardPdfPipeline failed" in str(e):
            logger.error("Docling pipeline failed for %s: %s", pdf_path, e)
            raise
        raise
    except Exception as e:
        logger.error("Docling convert failed for %s: %s", pdf_path, e)
        raise
    convert_elapsed_seconds = time.perf_counter() - convert_started_at

    doc = result.document

    tables: list[DoclingTable] = []
    table_loop_started_at = time.perf_counter()
    for table_item in doc.tables:
        try:
            df = table_item.export_to_dataframe(doc=doc)
            rows = [list(df.columns)] + df.values.tolist()
            rows = [[str(c) for c in row] for row in rows]
            headers = rows[0] if rows else []
            caption = _extract_caption(table_item)
            page_num = (
                getattr(table_item.prov[0], "page_no", 0) if table_item.prov else 0
            )
            tables.append(
                DoclingTable(
                    page_number=page_num,
                    caption=caption,
                    rows=rows,
                    headers=headers,
                )
            )
        except Exception as e:
            logger.debug("Skipping malformed table: %s", e)
    table_loop_elapsed_seconds = time.perf_counter() - table_loop_started_at

    sections: list[dict] = []
    section_loop_started_at = time.perf_counter()
    for text_item in doc.texts:
        label = str(getattr(text_item, "label", "")).lower()
        text = (text_item.text or "").strip()
        if not text:
            continue
        page_num = getattr(text_item.prov[0], "page_no", 0) if text_item.prov else 0
        sections.append(
            {
                "heading": label in ("section_header", "title", "chapter"),
                "text": text,
                "page": page_num,
            }
        )
    section_loop_elapsed_seconds = time.perf_counter() - section_loop_started_at

    import torch
    method = "docling_gpu" if torch.cuda.is_available() else "docling_cpu"
    page_count = _get_page_count_fast(pdf_path)

    if _docling_page_batch_profile_enabled(pdf_path):
        batch_size = _docling_profile_batch_size()
        profile_payload: dict[str, object] = {
            "pdf_path": str(Path(pdf_path).resolve()),
            "batch_size": batch_size,
            "page_count": page_count,
            "docling_convert_seconds": round(convert_elapsed_seconds, 6),
            "table_loop_seconds": round(table_loop_elapsed_seconds, 6),
            "section_loop_seconds": round(section_loop_elapsed_seconds, 6),
            "parser_id": method,
            "page_batches": [],
            "page_batch_error": None,
        }
        try:
            page_batches = _profile_docling_page_batches(
                pdf_path=pdf_path,
                converter=converter,
                page_count=page_count,
                batch_size=batch_size,
            )
            profile_payload["page_batches"] = page_batches
            first_error = next(
                (
                    str(item.get("error"))
                    for item in page_batches
                    if str(item.get("error") or "").strip()
                ),
                None,
            )
            profile_payload["page_batch_error"] = first_error
        except Exception as exc:  # noqa: BLE001
            profile_payload["page_batch_error"] = str(exc)
            logger.warning("Docling page-batch profiling failed for %s: %s", pdf_path, exc)
        _write_docling_page_batch_profile(profile_payload)

    return StructuredDocument(
        tables=tables,
        sections=sections,
        extraction_method=method,
        page_count=page_count,
        source_pdf_page_count=page_count,
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
                            tables.append(
                                DoclingTable(
                                    page_number=page_num,
                                    caption="",
                                    rows=rows_str,
                                    headers=rows_str[0] if rows_str else [],
                                )
                            )
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
        source_pdf_page_count=page_count,
        docling_version=DOCLING_VERSION,
    )


def _extract_caption(table_item) -> str:
    """Extract nearest heading/caption text for a table.
    Handles both .caption (str) and .captions (list) depending on docling version.
    """
    try:
        # docling >= 2.x uses .captions (list of TextItem)
        if hasattr(table_item, "captions") and table_item.captions:
            return str(
                table_item.captions[0].text
                if hasattr(table_item.captions[0], "text")
                else table_item.captions[0]
            )
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
        "source_pdf_page_count": doc.source_pdf_page_count,
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
    cache_path.parent.mkdir(parents=True, exist_ok=True)
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
        source_pdf_page_count=data.get("source_pdf_page_count", 0),
        docling_version=data.get("docling_version", ""),
    )
