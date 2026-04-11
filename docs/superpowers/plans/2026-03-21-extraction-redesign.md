# Extraction Redesign — Full Docling Multi-Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken single-pass LLM extraction pipeline with a 4-pass docling-based pipeline that achieves reliable, verifiable financial metric extraction from ASX announcements.

**Architecture:** docling extracts table structure from PDFs (cached to disk); Pass 1 classifies period/scale/currency; Pass 2 locates financial tables deterministically; Pass 3a/3b extract metrics and narrative via targeted LLM calls; Pass 4 reconciles across sources; a validation gate blocks bad data before DB upsert.

**Tech Stack:** Python 3.11+, docling (already in requirements.txt), PyMuPDF 1.24.10 (`fitz`), Qwen2.5-32B-Instruct via llamacpp (port 8001), SQLAlchemy, pytest

**Spec:** `docs/superpowers/specs/2026-03-21-extraction-redesign.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/services/docling_extract.py` | **Create** | PDF → structured output (tables + sections), with cache and PyMuPDF fallback |
| `backend/app/services/structured_chunking.py` | **Create** | Chunk prose sections only (not tables) for Qdrant embedding |
| `backend/app/services/multipass_extraction.py` | **Create** | 4-pass orchestration: classify → locate → extract → reconcile → validate |
| `backend/app/services/extraction.py` | **Delete** (after Task 1 guard update) | Old monolithic LLM extraction — replaced by multipass |
| `backend/app/services/text_extract.py` | **Delete** (after docling_extract is live) | Old PyMuPDF flat-text extractor — replaced by docling_extract |
| `backend/app/services/chunking.py` | **Delete** (after structured_chunking is live) | Old fixed-size chunker — replaced by structured_chunking |
| `backend/app/services/pipeline.py` | **Modify** | `process_document()` delegates to `run_multipass_extraction()` |
| `backend/tests/test_extraction_capability_guards.py` | **Modify** | Guard A+C updated; Guards F/G/H added |
| `backend/tests/test_multipass_extraction.py` | **Create** | Unit tests for all 4 passes + validation gate |
| `backend/tests/test_extraction_eval.py` | **Create** | Eval harness (unit mode: mocked LLM; live_eval: real LLM + accuracy gate) |
| `backend/tests/eval_fixtures/` | **Create** | Ground truth JSON files for verified documents |
| `backend/tests/eval_config.json` | **Create** | Regression gate accuracy thresholds |

---

## Task 1: Update Guards A+C, add Guards F/G/H

**Files:**
- Modify: `backend/tests/test_extraction_capability_guards.py`

Guard A currently imports `app.services.extraction` which will be deleted. Update it to verify `multipass_extraction` declares all metric fields. Guard C is fine (still checks `_upsert_financial_rows` in `pipeline.py`). Add Guards F, G, H.

- [ ] **Step 1: Update Guard A** — change import target and assertion

In `test_extraction_capability_guards.py`, replace the entire `test_extraction_prompt_declares_cashflow_metrics` function:

```python
def test_extraction_prompt_declares_cashflow_metrics():
    """
    Pass 3a in multipass_extraction must declare all 10 metric fields
    in its per-table extraction schema. Replaces the old extraction.py guard.

    If this fails: a metric was dropped from METRIC_SCHEMA in
    multipass_extraction.py. Restore it and update _upsert_financial_rows.
    """
    from app.services.multipass_extraction import METRIC_FIELDS

    required = {
        "revenue", "ebit", "np_attributable",
        "operating_cf", "investing_cf", "financing_cf",
        "capex", "cash_end", "net_debt", "shares_outstanding",
    }
    missing = required - set(METRIC_FIELDS)
    assert not missing, (
        f"multipass_extraction.METRIC_FIELDS is missing: {sorted(missing)}\n"
        "Restore the field in METRIC_FIELDS and in _upsert_financial_rows."
    )
```

- [ ] **Step 2: Add Guards F, G, H** — append to end of the file:

```python
# ---------------------------------------------------------------------------
# Guard F — docling_extract module is present and importable
# ---------------------------------------------------------------------------

def test_docling_extract_module_importable():
    """
    services/docling_extract.py must exist and be importable.
    If this fails: the module was deleted or has a syntax error.
    Fix: restore docling_extract.py and verify `from app.services.docling_extract import extract_structured`.
    """
    try:
        from app.services.docling_extract import extract_structured  # noqa: F401
    except ImportError as e:
        raise AssertionError(
            f"Cannot import extract_structured from docling_extract: {e}\n"
            "Ensure docling_extract.py exists in app/services/."
        ) from e


# ---------------------------------------------------------------------------
# Guard G — Validation gate rejects missing period_end
# ---------------------------------------------------------------------------

def test_validation_gate_rejects_missing_period_end():
    """
    _validate_gate() must return status='failed' when period_end is None.
    If this fails: the gate was weakened and bad extractions will reach the DB.
    """
    from app.services.multipass_extraction import _validate_gate

    payload = {
        "period_type": "H",
        "period_end": None,
        "metrics": {"operating_cf": 1000, "revenue": 2000, "cash_end": 500},
        "confidence_metrics": 0.9,
    }
    status, error = _validate_gate(payload)
    assert status == "failed", f"Expected 'failed', got '{status}'"
    assert error is not None


# ---------------------------------------------------------------------------
# Guard H — Validation gate rejects fewer than 3 non-null metrics
# ---------------------------------------------------------------------------

def test_validation_gate_rejects_insufficient_metrics():
    """
    _validate_gate() must return status='failed' when fewer than 3 metrics are non-null.
    If this fails: sparse extractions will pollute the financial history table.
    """
    from app.services.multipass_extraction import _validate_gate

    payload = {
        "period_type": "H",
        "period_end": "2024-12-31",
        "metrics": {"operating_cf": 1000, "revenue": None, "cash_end": None,
                    "ebit": None, "np_attributable": None, "investing_cf": None,
                    "financing_cf": None, "capex": None, "net_debt": None,
                    "shares_outstanding": None},
        "confidence_metrics": 0.9,
    }
    status, error = _validate_gate(payload)
    assert status == "failed", f"Expected 'failed', got '{status}'"
```

- [ ] **Step 3: Run guards (expect F/G/H to fail — multipass_extraction doesn't exist yet)**

```bash
cd financial-engine_v2
export PATH="$PWD/.venv/bin:$PATH"
pytest backend/tests/test_extraction_capability_guards.py -v 2>&1 | tail -30
```

Expected: Guard A PASSES (once multipass_extraction.py exists with METRIC_FIELDS — it doesn't yet, so it fails for now, that's fine), Guards F/G/H FAIL with ImportError. This is correct TDD state.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_extraction_capability_guards.py
git commit -m "test(guards): update Guard A for multipass_extraction; add Guards F/G/H"
```

---

## Task 2: Create `docling_extract.py`

**Files:**
- Create: `backend/app/services/docling_extract.py`

This is the new PDF extraction layer. It replaces `text_extract.py`. It produces structured output (tables as lists of row dicts, sections as text blocks) and caches results to `{pdf_path}.docling.json`.

`★ Insight ─────────────────────────────────────`
docling's `DocumentConverter` is the main entry point. It returns a `DoclingDocument` with `.tables` (list of `TableItem`) and `.texts` (list of `TextItem`). Each `TableItem` has `.export_to_dataframe()` which gives you a proper pandas DataFrame with row/column structure preserved. This is what makes docling dramatically better than PyMuPDF for financial tables.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write the failing Guard F test run**

```bash
cd financial-engine_v2
pytest backend/tests/test_extraction_capability_guards.py::test_docling_extract_module_importable -v
```
Expected: FAIL with ImportError. Confirms the guard is working.

- [ ] **Step 2: Create `docling_extract.py`**

```python
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

import fitz  # PyMuPDF — fallback only

logger = logging.getLogger(__name__)

DOCLING_TIMEOUT_SECONDS = 120


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
            return _load_cache(cache_path)
        except Exception as e:
            logger.warning("docling cache corrupt, re-extracting: %s", e)

    try:
        result = _run_docling_with_timeout(pdf_path)
        _save_cache(cache_path, result)
        return result
    except Exception as e:
        logger.warning("docling failed (%s), falling back to PyMuPDF: %s", type(e).__name__, e)
        return _pymupdf_fallback(pdf_path)


def _run_docling_with_timeout(pdf_path: str) -> StructuredDocument:
    """Run docling with SIGALRM timeout. Raises on timeout or failure."""
    def _timeout_handler(signum, frame):
        raise TimeoutError(f"docling exceeded {DOCLING_TIMEOUT_SECONDS}s on {pdf_path}")

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(DOCLING_TIMEOUT_SECONDS)
    try:
        return _run_docling(pdf_path)
    finally:
        signal.alarm(0)


def _run_docling(pdf_path: str) -> StructuredDocument:
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    tables: list[DoclingTable] = []
    for table_item in doc.tables:
        try:
            df = table_item.export_to_dataframe()
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
    )
```

- [ ] **Step 3: Run Guard F**

```bash
cd financial-engine_v2
pytest backend/tests/test_extraction_capability_guards.py::test_docling_extract_module_importable -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/docling_extract.py
git commit -m "feat(extraction): add docling_extract.py with table preservation and cache"
```

---

## Task 3: Create `structured_chunking.py`

**Files:**
- Create: `backend/app/services/structured_chunking.py`

Chunks prose sections only. Tables go to the metric extraction path, not Qdrant.

- [ ] **Step 1: Create `structured_chunking.py`**

```python
"""
structured_chunking.py — Prose-section chunking for Qdrant embedding.

Tables are excluded — they go to the metric extraction path.
Only non-table text sections are chunked here.
"""
from __future__ import annotations

from app.services.docling_extract import StructuredDocument

MAX_CHARS = 4500
OVERLAP_CHARS = 200


def chunk_prose_sections(doc: StructuredDocument, max_chars: int = MAX_CHARS) -> list[str]:
    """
    Returns a list of text chunks from the document's prose sections.
    Tables are excluded. Chunks respect max_chars with simple overlap.
    """
    prose = " ".join(
        s["text"] for s in doc.sections
        if s.get("text", "").strip()
    ).strip()

    if not prose:
        return []

    chunks = []
    start = 0
    while start < len(prose):
        end = min(start + max_chars, len(prose))
        chunks.append(prose[start:end])
        start = end - OVERLAP_CHARS if end < len(prose) else end

    return [c for c in chunks if c.strip()]
```

- [ ] **Step 2: Quick import smoke test**

```bash
cd financial-engine_v2
python -c "from app.services.structured_chunking import chunk_prose_sections; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/structured_chunking.py
git commit -m "feat(extraction): add structured_chunking.py for prose-only section chunking"
```

---

## Task 4: Create `multipass_extraction.py` skeleton + Pass 1 (Classifier)

**Files:**
- Create: `backend/app/services/multipass_extraction.py`
- Create: `backend/tests/test_multipass_extraction.py` (Pass 1 tests)

`★ Insight ─────────────────────────────────────`
**Pass 1 is the load-bearing foundation for everything else.** If the classifier gets the scale wrong ("millions" vs "thousands"), every subsequent numeric extraction will be off by 1000×. That's why Pass 1 aborts the entire extraction on low confidence — a wrong scale is worse than no data.

**Temperature 0 is mandatory** for all extraction LLM calls. Financial extraction must be deterministic — any sampling introduces non-reproducible errors. JSON mode (`response_format: {"type": "json_object"}`) enforces valid JSON output.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write failing tests for Pass 1**

Create `backend/tests/test_multipass_extraction.py`:

```python
"""
Unit tests for the 4-pass multipass extraction pipeline.
LLM calls are mocked — these test logic, not model quality.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Pass 1 — Document Classifier
# ---------------------------------------------------------------------------

def test_pass1_extracts_period_from_appendix_4d():
    """Classifier must identify half-year period from Appendix 4D heading."""
    from app.services.multipass_extraction import _run_pass1_classifier

    mock_response = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_response):
        result = _run_pass1_classifier(
            title="Appendix 4D Half Year Report",
            first_page_text="For the half year ended 31 December 2024. All figures in AUD thousands.",
            llm_client=None,
        )

    assert result["report_type"] == "H"
    assert result["period_end"] == "2024-12-31"
    assert result["scale"] == "thousands"
    assert result["classifier_confidence"] >= 0.9


def test_pass1_returns_low_confidence_on_empty_input():
    """Classifier must return low confidence when given no meaningful text."""
    from app.services.multipass_extraction import _run_pass1_classifier

    mock_response = {
        "report_type": None,
        "period_end": None,
        "currency": "AUD",
        "scale": "unknown",
        "classifier_confidence": 0.1,
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_response):
        result = _run_pass1_classifier(title="", first_page_text="", llm_client=None)

    assert result["classifier_confidence"] < 0.6
```

- [ ] **Step 2: Run tests (expect FAIL — module doesn't exist yet)**

```bash
cd financial-engine_v2
pytest backend/tests/test_multipass_extraction.py -v 2>&1 | tail -20
```
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Create `multipass_extraction.py` with Pass 1**

```python
"""
multipass_extraction.py — 4-pass financial metric extraction pipeline.

Passes:
  1. Document Classifier (LLM): period, scale, currency
  2. Table Locator (deterministic): label tables by financial statement type
  3a. Metric Extractor (LLM): extract numbers from labelled tables
  3b. Narrative Extractor (LLM): extract risk/guidance from prose
  4. Reconciler (deterministic): merge, resolve conflicts, build final payload

Entry point: run_multipass_extraction(pdf_path, doc_metadata, llm_client)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = "docling_multipass_v1"

# All 10 metric field names — used by Guard A and _upsert_financial_rows
METRIC_FIELDS = [
    "revenue", "ebit", "np_attributable",
    "operating_cf", "investing_cf", "financing_cf",
    "capex", "cash_end", "net_debt", "shares_outstanding",
]

# Source priority for reconciliation (index 0 = highest priority)
SOURCE_PRIORITY = ["income_statement", "cashflow_statement", "balance_sheet", "highlights"]

SCALE_MULTIPLIERS = {
    "thousands": 1_000,
    "millions": 1_000_000,
    "billions": 1_000_000_000,
    "units": 1,
    "unknown": 1,
}


@dataclass
class MultipassResult:
    status: str            # "ok" | "ok_low_confidence" | "failed"
    payload: dict          # matches _upsert_financial_rows contract
    sections: list[dict]   # prose sections for Qdrant chunking
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Pass 1 — Document Classifier
# ---------------------------------------------------------------------------

_PASS1_PROMPT = """You are a financial document classifier. Output ONLY valid JSON.

Given the document title and first-page text, extract:
- report_type: one of "A" (annual), "H" (half-year), "Q" (quarterly), or null
- period_end: the period end date as "YYYY-MM-DD", or null
- currency: three-letter currency code (e.g. "AUD"), or null
- scale: one of "thousands", "millions", "billions", "units", or "unknown"
- classifier_confidence: float 0.0-1.0 (how confident you are in the above)

Schema:
{
  "report_type": "A|H|Q|null",
  "period_end": "YYYY-MM-DD|null",
  "currency": "AUD|USD|...|null",
  "scale": "thousands|millions|billions|units|unknown",
  "classifier_confidence": 0.0
}

Title: {title}
First page text (first 1500 chars):
{first_page_text}
"""


def _run_pass1_classifier(
    title: str,
    first_page_text: str,
    llm_client,
) -> dict:
    """
    Pass 1: classify document type, period, currency, and scale.
    Returns dict with keys: report_type, period_end, currency, scale, classifier_confidence.
    """
    prompt = _PASS1_PROMPT.format(
        title=(title or "")[:200],
        first_page_text=(first_page_text or "")[:1500],
    )
    result = _llm_json_call(prompt, llm_client, max_tokens=256)
    # Normalise
    result.setdefault("report_type", None)
    result.setdefault("period_end", None)
    result.setdefault("currency", "AUD")
    result.setdefault("scale", "unknown")
    result.setdefault("classifier_confidence", 0.0)
    return result


# ---------------------------------------------------------------------------
# Pass 2 — Table Locator (deterministic)
# ---------------------------------------------------------------------------

_TABLE_KEYWORDS: dict[str, list[str]] = {
    "cashflow_statement": [
        "cash flow", "cash from operations", "financing activities",
        "investing activities", "net cash", "cash at end",
    ],
    "income_statement": [
        "revenue", "profit", "earnings before", "ebit", "net profit",
        "profit after tax", "income statement", "statement of profit",
    ],
    "balance_sheet": [
        "total assets", "shareholders equity", "net assets", "total liabilities",
        "balance sheet", "statement of financial position",
    ],
    "highlights": [
        "highlights", "key metrics", "summary", "at a glance", "key financials",
    ],
}


def _run_pass2_locator(tables) -> dict[str, Any]:
    """
    Pass 2: score each DoclingTable against keyword map. Returns labelled dict.
    Tables are matched to statement type by caption + first column text.
    Unmatched tables go to 'unmatched' list.
    """
    from app.services.docling_extract import DoclingTable

    labelled: dict[str, Any] = {k: None for k in _TABLE_KEYWORDS}
    labelled["unmatched"] = []

    def _score(table: DoclingTable, keywords: list[str]) -> int:
        text = (table.caption + " " + " ".join(
            row[0] for row in table.rows[:5] if row
        )).lower()
        return sum(1 for kw in keywords if kw in text)

    # Score each table against each statement type
    scored: list[tuple[str, int, Any]] = []
    for table in tables:
        best_label = None
        best_score = 0
        for label, keywords in _TABLE_KEYWORDS.items():
            score = _score(table, keywords)
            if score > best_score:
                best_score = score
                best_label = label
        if best_label and best_score > 0:
            scored.append((best_label, best_score, table))
        else:
            labelled["unmatched"].append(table)

    # For each label, keep the highest-scoring table (page order as tiebreak)
    for label in _TABLE_KEYWORDS:
        candidates = [(s, t) for (lbl, s, t) in scored if lbl == label]
        if candidates:
            # highest score; page order tiebreak (later page = more authoritative)
            labelled[label] = max(candidates, key=lambda x: (x[0], x[1].page_number))[1]

    return labelled


# ---------------------------------------------------------------------------
# Pass 3a — Per-Table Metric Extractor (LLM)
# ---------------------------------------------------------------------------

_PASS3A_PROMPT = """You are a financial metric extractor. Output ONLY valid JSON.

Document metadata:
- Period: {period_type} ending {period_end}
- Currency: {currency}
- Scale: {scale} (ALL output values must be multiplied by the scale factor)
  - thousands → multiply by 1,000
  - millions → multiply by 1,000,000

Table type: {table_type}
Table (markdown):
{table_markdown}

Extract ONLY these metrics relevant to {table_type}:
{metric_list}

Rules:
- Values in parentheses like (412) mean NEGATIVE: output -412000 (if scale=thousands)
- null if the metric is not in this table
- period_col: which column header represents the current period

Schema:
{{
{metric_schema}
  "period_col": "string|null",
  "pass3_confidence": 0.0,
  "row_refs": {{}}
}}
"""

_METRIC_SCHEMA_BY_TABLE = {
    "cashflow_statement": ["operating_cf", "investing_cf", "financing_cf", "cash_end"],
    "income_statement": ["revenue", "ebit", "np_attributable"],
    "balance_sheet": ["net_debt", "shares_outstanding"],
    "highlights": METRIC_FIELDS,  # highlights may have any metric
}


def _table_to_markdown(table) -> str:
    """Convert DoclingTable rows to markdown string."""
    if not table or not table.rows:
        return ""
    lines = []
    for i, row in enumerate(table.rows[:30]):  # cap at 30 rows
        line = " | ".join(str(c) for c in row)
        lines.append(line)
        if i == 0:
            lines.append(" | ".join("---" for _ in row))
    return "\n".join(lines)


def _run_pass3a_metric_extractor(
    labelled_tables: dict[str, Any],
    pass1_result: dict,
    llm_client,
) -> list[dict]:
    """
    Pass 3a: one LLM call per labelled table. Returns list of extraction dicts,
    each tagged with its source table type.
    """
    results = []
    scale = pass1_result.get("scale", "unknown")
    multiplier = SCALE_MULTIPLIERS.get(scale, 1)

    for table_type, table in labelled_tables.items():
        if table_type == "unmatched" or table is None:
            continue
        metrics = _METRIC_SCHEMA_BY_TABLE.get(table_type, METRIC_FIELDS)
        metric_schema = "\n".join(f'  "{m}": "number|null",' for m in metrics)
        markdown = _table_to_markdown(table)
        if not markdown:
            continue

        prompt = _PASS3A_PROMPT.format(
            period_type=pass1_result.get("report_type", "?"),
            period_end=pass1_result.get("period_end", "?"),
            currency=pass1_result.get("currency", "AUD"),
            scale=scale,
            table_type=table_type,
            table_markdown=markdown,
            metric_list=", ".join(metrics),
            metric_schema=metric_schema,
        )

        try:
            raw = _llm_json_call(prompt, llm_client, max_tokens=512)
        except Exception as e:
            logger.warning("Pass 3a failed for %s: %s — retrying with truncated table", table_type, e)
            try:
                truncated_prompt = _PASS3A_PROMPT.format(
                    period_type=pass1_result.get("report_type", "?"),
                    period_end=pass1_result.get("period_end", "?"),
                    currency=pass1_result.get("currency", "AUD"),
                    scale=scale,
                    table_type=table_type,
                    table_markdown=_table_to_markdown_truncated(table, max_rows=20),
                    metric_list=", ".join(metrics),
                    metric_schema=metric_schema,
                )
                raw = _llm_json_call(truncated_prompt, llm_client, max_tokens=512)
            except Exception as e2:
                logger.error("Pass 3a retry also failed for %s: %s", table_type, e2)
                continue

        # Apply scale multiplier to all numeric values
        out = {"_source": table_type}
        for m in metrics:
            val = raw.get(m)
            if val is not None:
                try:
                    out[m] = float(val) * multiplier
                except (TypeError, ValueError):
                    out[m] = None
            else:
                out[m] = None
        out["pass3_confidence"] = float(raw.get("pass3_confidence", 0.5))
        out["row_refs"] = raw.get("row_refs", {})
        results.append(out)

    return results


def _table_to_markdown_truncated(table, max_rows: int = 20) -> str:
    """Truncated version for retry."""
    if not table or not table.rows:
        return ""
    rows = table.rows[:max_rows]
    lines = []
    for i, row in enumerate(rows):
        line = " | ".join(str(c) for c in row)
        lines.append(line)
        if i == 0:
            lines.append(" | ".join("---" for _ in row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pass 3b — Narrative Extractor (LLM)
# ---------------------------------------------------------------------------

_PASS3B_PROMPT = """You are a financial narrative extractor. Output ONLY valid JSON.

From the document text below, extract:
- risk_summary: 1-2 sentence summary of key risks (null if none mentioned)
- risk_bullets: list of specific risk items (null if none)
- guidance_summary: management outlook/guidance summary (null if not present)
- material_changes: any material changes to business or financial position (null if none)
- confidence_narrative: float 0-1 (confidence in extraction quality)

Schema:
{
  "risk_summary": "string|null",
  "risk_bullets": ["string"]|null,
  "guidance_summary": "string|null",
  "material_changes": "string|null",
  "confidence_narrative": 0.0
}

Document text (first 4000 chars of prose):
{prose_text}
"""


def _run_pass3b_narrative_extractor(sections: list[dict], llm_client) -> dict:
    """
    Pass 3b: extract risk/guidance narrative from prose sections.
    Returns dict with narrative fields. All fields null on failure.
    """
    null_result = {
        "risk_summary": None, "risk_bullets": None,
        "guidance_summary": None, "material_changes": None,
        "confidence_narrative": 0.0,
    }

    prose = " ".join(s["text"] for s in sections if s.get("text", "").strip())[:4000]
    if not prose:
        return null_result

    prompt = _PASS3B_PROMPT.format(prose_text=prose)
    try:
        raw = _llm_json_call(prompt, llm_client, max_tokens=512)
        return {
            "risk_summary": raw.get("risk_summary"),
            "risk_bullets": raw.get("risk_bullets"),
            "guidance_summary": raw.get("guidance_summary"),
            "material_changes": raw.get("material_changes"),
            "confidence_narrative": float(raw.get("confidence_narrative", 0.5)),
        }
    except Exception as e:
        logger.warning("Pass 3b narrative extraction failed: %s", e)
        return null_result


# ---------------------------------------------------------------------------
# Pass 4 — Reconciler (deterministic)
# ---------------------------------------------------------------------------

def _run_pass4_reconciler(
    pass3a_results: list[dict],
    pass3b_result: dict,
    pass1_result: dict,
) -> dict:
    """
    Pass 4: merge all Pass 3a results into one canonical payload.
    Source priority: income_statement > cashflow_statement > balance_sheet > highlights.
    Returns dict matching _upsert_financial_rows contract.
    """
    merged_metrics: dict[str, Any] = {m: None for m in METRIC_FIELDS}
    provenance: dict[str, str] = {}
    confidences: list[float] = []
    n_contributed: dict[str, int] = {}

    # Sort by priority
    ordered = sorted(
        pass3a_results,
        key=lambda r: SOURCE_PRIORITY.index(r.get("_source", "highlights"))
        if r.get("_source") in SOURCE_PRIORITY else len(SOURCE_PRIORITY),
    )

    # Lower priority first — higher priority overwrites
    for extraction in reversed(ordered):
        source = extraction.get("_source", "unknown")
        conf = extraction.get("pass3_confidence", 0.5)
        confidences.append(conf)
        contributed = 0
        for m in METRIC_FIELDS:
            if m in extraction and extraction[m] is not None:
                merged_metrics[m] = extraction[m]
                provenance[m] = f"{source}:{extraction.get('row_refs', {}).get(m, 'unknown')}"
                contributed += 1
        n_contributed[source] = contributed

    # Weighted average confidence
    metric_confidence = (
        sum(c * n_contributed.get(r.get("_source", ""), 1) for c, r in zip(confidences, ordered))
        / max(sum(n_contributed.values()), 1)
        if confidences else 0.0
    )

    return {
        "period_type": pass1_result.get("report_type"),
        "period_end": pass1_result.get("period_end"),
        "metrics": merged_metrics,
        "confidence_metrics": round(metric_confidence, 3),
        "provenance": provenance,
        **pass3b_result,  # risk_summary, risk_bullets, guidance_summary, material_changes, confidence_narrative
    }


# ---------------------------------------------------------------------------
# Validation Gate
# ---------------------------------------------------------------------------

SANITY_CAP = 500_000_000_000  # $500B


def _validate_gate(payload: dict) -> tuple[str, Optional[str]]:
    """
    Validate the reconciled payload before DB upsert.
    Returns (status, error). status is one of: "ok", "ok_low_confidence", "failed".
    """
    from dateutil import parser as dtparser

    # Hard blocks
    if not payload.get("period_end"):
        return "failed", "validation_gate:missing_period_end"

    try:
        dtparser.parse(str(payload["period_end"]))
    except Exception:
        return "failed", "validation_gate:invalid_period_end"

    if payload.get("period_type") not in ("A", "H", "Q"):
        return "failed", f"validation_gate:invalid_period_type:{payload.get('period_type')}"

    metrics = payload.get("metrics", {})
    non_null = [v for v in metrics.values() if v is not None]
    if len(non_null) < 3:
        return "failed", f"validation_gate:insufficient_metrics:{len(non_null)}"

    for m, v in metrics.items():
        if v is not None and abs(v) > SANITY_CAP:
            return "failed", f"validation_gate:sanity_cap_exceeded:{m}={v}"

    confidence = payload.get("confidence_metrics", 0.0)
    if confidence < 0.60:
        return "failed", f"validation_gate:low_confidence:{confidence}"

    # Soft warning
    if confidence < 0.70:
        return "ok_low_confidence", None

    return "ok", None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_multipass_extraction(
    pdf_path: str,
    doc_metadata: dict,
    llm_client,
) -> MultipassResult:
    """
    Orchestrate all 4 passes and return a MultipassResult.
    doc_metadata: {"document_id": str, "ticker": str, "title": str}
    """
    from app.services.docling_extract import extract_structured

    null_payload = {m: None for m in METRIC_FIELDS}
    null_payload.update({
        "period_type": None, "period_end": None, "confidence_metrics": 0.0,
        "risk_summary": None, "risk_bullets": None, "guidance_summary": None,
        "material_changes": None, "confidence_narrative": 0.0, "provenance": {},
    })

    # Extract structured document
    try:
        structured_doc = extract_structured(pdf_path)
    except Exception as e:
        logger.error("docling_extract failed for %s: %s", pdf_path, e)
        return MultipassResult(status="failed", payload=null_payload, sections=[], error=str(e))

    # Pass 1: Classify
    first_page_text = " ".join(
        s["text"] for s in structured_doc.sections[:5]
    )[:1500]
    title = doc_metadata.get("title", "")

    try:
        pass1 = _run_pass1_classifier(title, first_page_text, llm_client)
    except Exception as e:
        logger.error("Pass 1 failed: %s", e)
        return MultipassResult(status="failed", payload=null_payload,
                               sections=structured_doc.sections, error=f"pass1:{e}")

    if pass1.get("classifier_confidence", 0) < 0.60:
        return MultipassResult(
            status="failed", payload=null_payload,
            sections=structured_doc.sections,
            error=f"classifier_low_confidence:{pass1.get('classifier_confidence')}",
        )

    # Pass 2: Locate tables
    labelled = _run_pass2_locator(structured_doc.tables)

    # Pass 3a: Extract metrics
    pass3a_results = _run_pass3a_metric_extractor(labelled, pass1, llm_client)

    # Pass 3b: Extract narrative
    pass3b_result = _run_pass3b_narrative_extractor(structured_doc.sections, llm_client)

    # Pass 4: Reconcile
    payload = _run_pass4_reconciler(pass3a_results, pass3b_result, pass1)

    # Flatten metrics into payload for _upsert_financial_rows compat
    for m in METRIC_FIELDS:
        payload[m] = payload["metrics"].get(m)

    # Validate
    status, error = _validate_gate(payload)

    return MultipassResult(
        status=status,
        payload=payload,
        sections=structured_doc.sections,
        error=error,
    )


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _llm_json_call(prompt: str, llm_client, max_tokens: int = 512) -> dict:
    """
    Call the LLM with JSON mode enforced. Returns parsed dict.
    Raises on invalid JSON or connection failure.
    """
    from app.services.llm import generate_json
    metadata = {"task_type": "reasoning", "component": "multipass_extraction"}
    result = generate_json(prompt, metadata=metadata, client=llm_client)
    if not isinstance(result, dict):
        raise ValueError(f"LLM returned non-dict: {type(result)}")
    return result
```

- [ ] **Step 4: Run Pass 1 tests**

```bash
cd financial-engine_v2
pytest backend/tests/test_multipass_extraction.py -v -k "pass1" 2>&1 | tail -20
```
Expected: PASS (both Pass 1 tests).

- [ ] **Step 5: Run Guards A+F**

```bash
pytest backend/tests/test_extraction_capability_guards.py::test_extraction_prompt_declares_cashflow_metrics backend/tests/test_extraction_capability_guards.py::test_docling_extract_module_importable -v
```
Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/multipass_extraction.py backend/tests/test_multipass_extraction.py
git commit -m "feat(extraction): multipass_extraction.py — Pass 1 classifier + all pass skeletons"
```

---

## Task 5: Unit tests for Pass 2 (Table Locator) and Pass 3 logic

**Files:**
- Modify: `backend/tests/test_multipass_extraction.py`

- [ ] **Step 1: Add Pass 2, Pass 3a, Pass 3b, Pass 4 unit tests** — append to `test_multipass_extraction.py`:

```python
# ---------------------------------------------------------------------------
# Pass 2 — Table Locator
# ---------------------------------------------------------------------------

def test_pass2_labels_cashflow_table_by_caption():
    """Table locator must assign a table with 'cash flow' caption to cashflow_statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cashflow_table = DoclingTable(
        page_number=3,
        caption="Consolidated Statement of Cash Flows",
        rows=[["Row", "Current", "Prior"], ["Net cash from operations", "3,241", "2,876"]],
        headers=["Row", "Current", "Prior"],
    )
    result = _run_pass2_locator([cashflow_table])
    assert result["cashflow_statement"] is cashflow_table
    assert result["income_statement"] is None


def test_pass2_higher_score_wins_on_conflict():
    """When two tables match the same type, the one with more keyword matches wins."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weak = DoclingTable(page_number=1, caption="cash",
                        rows=[["cash flow", "100"]], headers=[])
    strong = DoclingTable(page_number=3, caption="Cash Flow Statement — Financing Activities",
                          rows=[["net cash from operations", "1000"],
                                ["financing activities", "200"]], headers=[])
    result = _run_pass2_locator([weak, strong])
    assert result["cashflow_statement"] is strong


# ---------------------------------------------------------------------------
# Pass 3a — Scale normalisation and negative values
# ---------------------------------------------------------------------------

def test_pass3a_applies_thousands_multiplier():
    """Metric values must be multiplied by 1000 when scale=thousands."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None, "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.95, "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000  # multiplied by 1000


def test_pass3a_negative_values_preserved():
    """Negative values (already negative from LLM) must remain negative after scaling."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flow",
        rows=[["", "H1"], ["Investing activities", "(412)"]],
        headers=[],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": None, "investing_cf": -412,
        "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.9, "row_refs": {},
    }
    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["investing_cf"] == -412_000


# ---------------------------------------------------------------------------
# Pass 3b — Narrative extractor
# ---------------------------------------------------------------------------

def test_pass3b_returns_null_on_empty_sections():
    """Narrative extractor must return all-null dict when sections are empty."""
    from app.services.multipass_extraction import _run_pass3b_narrative_extractor

    result = _run_pass3b_narrative_extractor(sections=[], llm_client=None)
    assert result["risk_summary"] is None
    assert result["guidance_summary"] is None
    assert result["confidence_narrative"] == 0.0


# ---------------------------------------------------------------------------
# Pass 4 — Reconciler
# ---------------------------------------------------------------------------

def test_pass4_merges_non_overlapping_metrics():
    """Reconciler must combine metrics from different table sources."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {"_source": "cashflow_statement", "operating_cf": 3_241_000, "investing_cf": -412_000,
         "financing_cf": None, "cash_end": None, "pass3_confidence": 0.9, "row_refs": {}},
        {"_source": "income_statement", "revenue": 27_841_000_000, "ebit": 9_100_000_000,
         "np_attributable": None, "pass3_confidence": 0.88, "row_refs": {}},
    ]
    pass3b = {"risk_summary": None, "risk_bullets": None,
              "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.0}
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert result["metrics"]["operating_cf"] == 3_241_000
    assert result["metrics"]["revenue"] == 27_841_000_000
    assert result["period_end"] == "2024-12-31"


def test_pass4_higher_priority_source_wins():
    """income_statement must override highlights when both provide revenue."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {"_source": "highlights", "revenue": 45_200_000, "pass3_confidence": 0.7, "row_refs": {}},
        {"_source": "income_statement", "revenue": 45_192_000, "pass3_confidence": 0.92, "row_refs": {}},
    ]
    pass3b = {"risk_summary": None, "risk_bullets": None,
              "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.0}
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)
    assert result["metrics"]["revenue"] == 45_192_000  # income_statement wins
```

- [ ] **Step 2: Run all unit tests**

```bash
cd financial-engine_v2
pytest backend/tests/test_multipass_extraction.py -v 2>&1 | tail -30
```
Expected: All tests PASS.

- [ ] **Step 3: Run all capability guards**

```bash
pytest backend/tests/test_extraction_capability_guards.py -v
```
Expected: Guards A, B, C, D, F PASS. Guard E fails (known — cashflow layout modules missing from branch). Guards G, H PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_multipass_extraction.py
git commit -m "test(extraction): unit tests for all 4 passes — table locator, scale, negatives, reconciler"
```

---

## Task 6: Modify `pipeline.py` — delegate to `run_multipass_extraction()`

**Files:**
- Modify: `backend/app/services/pipeline.py`

`★ Insight ─────────────────────────────────────`
**We're replacing only one logical block in `process_document()`** — the section from `text = extract_text_from_pdf(...)` through `_upsert_financial_rows(...)`. Everything else (Qdrant embed path, ExtractionRun write, error handling structure) stays. This is minimal-diff discipline: change only what must change.

**The `EXTRACTOR_VERSION` import path changes** — it used to come from `extraction.py` (now deleted). It's now defined in `multipass_extraction.py`. The import at the top of `pipeline.py` must be updated.

### Implementation addendum: pre-extraction administrative title gate

Live backend behavior now includes a title-only skip gate in `pipeline.process_document()` before `run_method_isolated_extraction()`.

Purpose:

- prevent clearly administrative ASX paperwork from consuming GPU extraction time during backfills
- preserve the normal extraction path for everything else

Rules:

- use a narrow skip list of known non-financial administrative announcement titles
- do not use an allow list of "approved" financial titles
- do not read the PDF to make the skip decision
- never skip structurally financial documents such as `annual`, `half_year`, `4C`, `4D`, or `4E`

Examples of skipped titles:

- substantial holder / substantial holding notices
- director's interest notices
- cessation of securities
- unquoted securities

Operational result:

- matched documents are recorded as `skipped_extraction`
- GPU extraction is not invoked
- downstream chunking / embedding / persistence behavior remains unchanged for documents that still proceed
`─────────────────────────────────────────────────`

- [ ] **Step 1: Update imports in `pipeline.py`**

At the top of `pipeline.py`, replace:
```python
from app.services.extraction import build_prompt, EXTRACTOR_VERSION
from app.services.text_extract import extract_text_from_pdf
from app.services.chunking import simple_chunk
```
with:
```python
from app.services.multipass_extraction import run_multipass_extraction, EXTRACTOR_VERSION
from app.services.structured_chunking import chunk_prose_sections
```

- [ ] **Step 2: Replace the extraction block in `process_document()`**

Find the block starting at `text = extract_text_from_pdf(...)` and ending at `if status == "ok": _upsert_financial_rows(...)`.

Replace with:

```python
        # --- New multi-pass extraction ---
        multipass_result = None
        sections_for_chunks = []

        if settings.enable_extraction:
            try:
                doc_metadata = {
                    "document_id": str(doc.document_id),
                    "ticker": str(doc.ticker or ""),
                    "title": str(doc.title or ""),
                }
                multipass_result = run_multipass_extraction(
                    _resolve_pdf_path(doc.pdf_path),
                    doc_metadata,
                    ollama_client,
                )
                sections_for_chunks = multipass_result.sections
                status = multipass_result.status
                error = multipass_result.error
                structured = multipass_result.payload
                confidence = structured.get("confidence_metrics")
                extraction_model_name = "qwen2.5-32b-instruct"
            except Exception as exc:
                status = "failed"
                error = str(exc)
                structured = {"error": error}
                sections_for_chunks = []
        else:
            structured = {"status": "skipped_extraction"}
            status = "skipped"
            error = None

        # --- Use structured sections for prose chunking (not raw text) ---
        from app.services.docling_extract import StructuredDocument
        _doc_for_chunks = StructuredDocument(sections=sections_for_chunks)
        chunks = chunk_prose_sections(_doc_for_chunks)
        chunks_created = len(chunks)
```

Then ensure the Qdrant embed block uses `chunks` (unchanged — it already does), and keep the `ExtractionRun` write and `_upsert_financial_rows` call unchanged.

- [ ] **Step 3: Run the capability guard for pipeline upsert (Guard C)**

```bash
cd financial-engine_v2
pytest backend/tests/test_extraction_capability_guards.py::test_pipeline_upsert_field_list_includes_cashflow_fields -v
```
Expected: PASS (Guard C checks `_upsert_financial_rows` source, which is unchanged).

- [ ] **Step 4: Run full test suite**

```bash
pytest backend/tests/ -v --tb=short 2>&1 | tail -40
```
Expected: All previously passing tests still pass. Guards G+H pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline.py
git commit -m "feat(pipeline): delegate process_document to run_multipass_extraction"
```

---

## Task 7: Create eval harness

**Files:**
- Create: `backend/tests/eval_config.json`
- Create: `backend/tests/eval_fixtures/.gitkeep`
- Create: `backend/tests/test_extraction_eval.py`

- [ ] **Step 1: Create `eval_config.json`**

```json
{
  "_comment": "Accuracy thresholds for live_eval regression gate. Apply to pytest -m live_eval runs only.",
  "min_accuracy_overall": 0.85,
  "min_accuracy_per_metric": {
    "operating_cf": 0.90,
    "revenue": 0.90,
    "period_end": 1.00
  },
  "warn_threshold": 0.80,
  "tolerances": {
    "revenue": 0.005,
    "ebit": 0.005,
    "np_attributable": 0.005,
    "operating_cf": 0.01,
    "investing_cf": 0.01,
    "financing_cf": 0.01,
    "cash_end": 0.001,
    "net_debt": 0.001,
    "capex": 0.02,
    "shares_outstanding": 0.0001
  }
}
```

- [ ] **Step 2: Create `test_extraction_eval.py`**

```python
"""
Eval harness for multipass extraction accuracy.

TWO MODES:
  Unit mode (default, no marker): loads fixtures + cached docling JSON.
      LLM calls mocked. Tests pipeline structure and schema only.
      Does NOT assert accuracy thresholds.

  Live eval mode (pytest -m live_eval): runs full pipeline against real LLM.
      Asserts per-metric accuracy >= thresholds in eval_config.json.
      Run manually before merging any extraction changes.
      Requires: llamacpp running on port 8001, eval_fixtures/*.json present.
"""
import json
import math
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "eval_fixtures"
CONFIG_PATH = Path(__file__).parent / "eval_config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def load_fixtures() -> list[dict]:
    if not FIXTURES_DIR.exists():
        return []
    return [
        json.loads(f.read_text())
        for f in sorted(FIXTURES_DIR.glob("*.json"))
        if f.name != ".gitkeep"
    ]


def metric_matches(extracted: float | None, expected: float | None,
                   tolerance: float) -> bool:
    """Returns True if extracted is within tolerance of expected."""
    if expected is None:
        return extracted is None  # null expected → must be null
    if extracted is None:
        return False  # value expected → must not be null
    if expected == 0:
        return abs(extracted) < 1  # near-zero
    return abs((extracted - expected) / expected) <= tolerance


# ---------------------------------------------------------------------------
# Unit mode: schema and structure tests (no real LLM)
# ---------------------------------------------------------------------------

def test_eval_config_exists_and_valid():
    """eval_config.json must exist and contain required keys."""
    config = load_config()
    assert "min_accuracy_overall" in config
    assert "min_accuracy_per_metric" in config
    assert "tolerances" in config
    assert config["min_accuracy_overall"] >= 0.5


def test_multipass_result_has_expected_keys():
    """MultipassResult payload must contain all METRIC_FIELDS + narrative fields."""
    from app.services.multipass_extraction import (
        MultipassResult, METRIC_FIELDS, _run_pass4_reconciler, _run_pass3b_narrative_extractor
    )

    mock_pass3a = [
        {"_source": "cashflow_statement", "operating_cf": 1_000_000, "investing_cf": None,
         "financing_cf": None, "cash_end": 500_000, "pass3_confidence": 0.9, "row_refs": {}}
    ]
    mock_pass3b = {
        "risk_summary": "Test risk", "risk_bullets": ["Risk 1"],
        "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.7
    }
    mock_pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(mock_pass3a, mock_pass3b, mock_pass1)

    assert "period_type" in payload
    assert "period_end" in payload
    assert "confidence_metrics" in payload
    assert "metrics" in payload
    assert all(m in payload["metrics"] for m in METRIC_FIELDS)
    assert "risk_summary" in payload
    assert "guidance_summary" in payload


def test_metric_match_within_tolerance():
    """Tolerance function must correctly identify acceptable values."""
    assert metric_matches(3_241_000, 3_241_000, 0.01)       # exact
    assert metric_matches(3_208_590, 3_241_000, 0.01)        # within 1%
    assert not metric_matches(2_900_000, 3_241_000, 0.01)    # outside 1%
    assert metric_matches(None, None, 0.01)                   # both null OK
    assert not metric_matches(None, 3_241_000, 0.01)          # missing value


# ---------------------------------------------------------------------------
# Live eval mode: accuracy regression gate (requires real LLM + fixtures)
# ---------------------------------------------------------------------------

@pytest.mark.live_eval
def test_live_eval_accuracy_against_fixtures():
    """
    Run the full pipeline against each fixture and assert accuracy >= thresholds.
    Requires: llamacpp on port 8001, eval_fixtures/*.json with pdf_filename present.
    """
    import httpx
    from app.services.multipass_extraction import run_multipass_extraction

    config = load_config()
    fixtures = load_fixtures()

    if not fixtures:
        pytest.skip("No eval fixtures found in eval_fixtures/. Add fixtures first.")

    tolerances = config["tolerances"]
    per_metric_results: dict[str, list[bool]] = {}
    overall_results: list[bool] = []

    llm_client = httpx.Client(base_url="http://127.0.0.1:8001/v1", timeout=60.0)

    for fixture in fixtures:
        pdf_path = str(
            Path(__file__).parent.parent.parent
            / "data" / fixture["ticker"] / fixture["pdf_filename"]
        )
        if not Path(pdf_path).exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        doc_metadata = {
            "document_id": fixture["document_id"],
            "ticker": fixture["ticker"],
            "title": fixture.get("pdf_filename", ""),
        }
        result = run_multipass_extraction(pdf_path, doc_metadata, llm_client)

        for metric, expected_val in fixture["metrics"].items():
            tol = tolerances.get(metric, 0.01)
            extracted_val = result.payload.get("metrics", {}).get(metric)
            match = metric_matches(extracted_val, expected_val, tol)
            per_metric_results.setdefault(metric, []).append(match)
            overall_results.append(match)

        # Check expected nulls
        for null_metric in fixture.get("expected_nulls", []):
            val = result.payload.get("metrics", {}).get(null_metric)
            per_metric_results.setdefault(null_metric, []).append(val is None)
            overall_results.append(val is None)

    # Assert overall accuracy
    overall_acc = sum(overall_results) / len(overall_results) if overall_results else 0
    assert overall_acc >= config["min_accuracy_overall"], (
        f"Overall accuracy {overall_acc:.1%} below threshold {config['min_accuracy_overall']:.1%}"
    )

    # Assert per-metric accuracy
    for metric, min_acc in config["min_accuracy_per_metric"].items():
        if metric not in per_metric_results:
            continue
        acc = sum(per_metric_results[metric]) / len(per_metric_results[metric])
        assert acc >= min_acc, (
            f"{metric} accuracy {acc:.1%} below threshold {min_acc:.1%}"
        )
```

- [ ] **Step 3: Create fixtures placeholder and run unit tests**

```bash
mkdir -p financial-engine_v2/backend/tests/eval_fixtures
touch financial-engine_v2/backend/tests/eval_fixtures/.gitkeep

cd financial-engine_v2
pytest backend/tests/test_extraction_eval.py -v -k "not live_eval" 2>&1 | tail -20
```
Expected: All unit-mode tests PASS.

- [ ] **Step 4: Run full test suite one final time**

```bash
pytest backend/tests/ -v --tb=short -k "not live_eval" 2>&1 | tail -50
```
Expected: All tests pass except Guard E (known — cashflow layout modules missing from branch).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/eval_config.json backend/tests/eval_fixtures/ backend/tests/test_extraction_eval.py
git commit -m "feat(eval): eval harness — config, fixture dir, test_extraction_eval.py (unit + live_eval modes)"
```

---

## Task 8: Delete replaced modules and do final cleanup

**Files:**
- Delete: `backend/app/services/extraction.py`
- Delete: `backend/app/services/text_extract.py`
- Delete: `backend/app/services/chunking.py`

- [ ] **Step 1: Verify nothing else imports the old modules**

```bash
cd financial-engine_v2
grep -r "from app.services.extraction import\|from app.services.text_extract\|from app.services.chunking" backend/ --include="*.py"
```
Expected: no output. If any imports remain, update them before deleting.

- [ ] **Step 2: Delete old modules**

```bash
rm financial-engine_v2/backend/app/services/extraction.py
rm financial-engine_v2/backend/app/services/text_extract.py
rm financial-engine_v2/backend/app/services/chunking.py
```

- [ ] **Step 3: Run full test suite**

```bash
cd financial-engine_v2
pytest backend/tests/ -v --tb=short -k "not live_eval" 2>&1 | tail -50
```
Expected: All tests pass except Guard E. Guard A now imports from `multipass_extraction` successfully.

- [ ] **Step 4: Lint**

```bash
python -m ruff check backend/ --select=E,F,W 2>&1 | head -30
```
Expected: No errors (or only pre-existing ones).

- [ ] **Step 5: Milestone commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
milestone(extraction): docling multi-pass extraction pipeline complete

Working:
- docling_extract.py: PDF → structured tables + sections, with cache and PyMuPDF fallback
- structured_chunking.py: prose-only section chunking for Qdrant
- multipass_extraction.py: 4-pass pipeline (classify → locate → extract → reconcile → validate)
- pipeline.py: process_document delegates to run_multipass_extraction
- Capability guards A+C updated, F/G/H new — all pass
- Unit tests: all 4 passes covered
- Eval harness: unit + live_eval modes

Tested:
- pytest backend/tests/ -k 'not live_eval' — all pass except Guard E (known branch issue)
- ruff check backend/ — clean
EOF
)"
```

---

## Next: Seed Eval Fixtures (Manual Step)

Before running the live eval gate, you must create at least 5 hand-verified fixture files.

**For each fixture PDF:**

1. Open the PDF and read the actual values
2. Create `backend/tests/eval_fixtures/{ticker}_{period}.json`:

```json
{
  "document_id": "paste-from-DB-or-generate-uuid",
  "ticker": "BHP",
  "pdf_filename": "bhp_4d_dec2024.pdf",
  "period_type": "H",
  "period_end": "2024-12-31",
  "verified_by": "l4nd0",
  "verified_at": "2026-03-21",
  "metrics": {
    "revenue": 27841000000,
    "operating_cf": 8210000000,
    "investing_cf": -3400000000
  },
  "expected_nulls": ["net_debt", "ebit"]
}
```

3. Run live eval to measure baseline:

```bash
cd financial-engine_v2
pytest backend/tests/test_extraction_eval.py -m live_eval -v
```

---

## Verification Checklist

Before declaring done:

- [ ] `pytest backend/tests/ -k "not live_eval"` — all pass except Guard E
- [ ] `python -m ruff check backend/` — clean
- [ ] Guard A passes (imports `multipass_extraction.METRIC_FIELDS`)
- [ ] Guard F passes (`docling_extract` importable)
- [ ] Guards G+H pass (validation gate rejects bad payloads)
- [ ] `process_document()` uses `run_multipass_extraction` not `build_prompt`
- [ ] `EXTRACTOR_VERSION = "docling_multipass_v1"` in `multipass_extraction.py`
- [ ] Docling cache created at `{pdf_path}.docling.json` on first run
- [ ] Old modules (`extraction.py`, `text_extract.py`, `chunking.py`) deleted
- [ ] Milestone commit created
