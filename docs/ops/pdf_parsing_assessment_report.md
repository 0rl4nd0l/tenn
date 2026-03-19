# PDF Data Parsing System — Full Assessment Report

**Date:** 2026-03-01  
**Scope:** Existing PDF parsing pipeline only; no architecture redesign.

---

## 1. System Map

### 1.1 Two distinct PDF-related systems

| System | Purpose | Entrypoints | Text extraction |
|--------|--------|-------------|-----------------|
| **Backend ingestion (financial-engine_v2)** | ASX announcements: discover → download PDF → extract text → chunk → embed → optional LLM extraction | API backfill, Celery `download_pdf` / `process_document`, `pipeline.process_document()` | PyMuPDF (`fitz`) in `app.services.text_extract` |
| **Financial metrics extraction (scripts)** | Batch extract structured financial metrics from PDFs on disk | CLI `scripts/extract_financial_metrics.py` | `pdftotext` (poppler-utils) |

This assessment focuses on **both**, with the **financial metrics script** as the primary “PDF data parsing” pipeline (structured output); the backend is “PDF text extraction + chunking” for RAG.

---

### 1.2 Entrypoints and responsibilities

| Entrypoint | Location | What it does |
|------------|----------|--------------|
| **extract_financial_metrics.py** (CLI) | `scripts/extract_financial_metrics.py` | `main()`: finds PDFs under `--pdf-dir`, runs table-first extraction per PDF, writes CSV/JSON/SQLite (canonical, context, rejected, blocks, high-confidence). Default strict mode uses `extract_table_metrics()` only. |
| **process_document(document_id)** | `financial-engine_v2/backend/app/services/pipeline.py` (L584) | Resolves `doc.pdf_path`, calls `extract_text_from_pdf()`, chunks with `simple_chunk()`, embeds (if enabled), upserts Qdrant, optionally runs LLM extraction and upserts financial/risk rows. |
| **download_pdf(document_id)** (Celery) | `financial-engine_v2/worker/worker_app/tasks.py` (L27) | Calls `download_pdf_for_document(db, document_id)` from `app.services.pipeline`. |
| **download_pdf_for_document(db, document_id)** | `financial-engine_v2/backend/app/services/pipeline.py` (L498) | Downloads PDF from `doc.source_url`, validates `%PDF`, writes to `doc.pdf_path`, sets `doc.pdf_sha256`. |
| **pdf_rag.build_index(root)** | `scripts/pdf_rag.py` | Builds a text index from PDFs under a root dir using `pdftotext`; used for RAG/search over PDFs (separate from backend RAG). |

---

### 1.3 Call flow — financial metrics extraction (scripts)

```
main() [extract_financial_metrics.py L4226]
  → find_pdfs(pdf_dir)                    # sorted *.pdf under dir
  → for each pdf:
       (strict mode)
       → classify_pdf_source_kind(pdf)
       → extract_table_metrics(pdf, ...)   # L3048
            → _prepare_bbox_pages(pdf)     # L2041: parse_bbox_layout_lines() → XML parse → by_page
            → segment_statement_blocks(pdf, by_page)  # L2110: detect_table_regions, classify scope
            → extract_metrics_from_blocks(pdf, blocks, by_page)  # L2312: numeric tokens, columns, periods
            → split_rows_by_scope(rows)     # canonical vs context vs rejected
       (non-strict: extract_pdf_text → line-by-line parse_line + continuation stitch)
  → dedupe, score_confidence, annotate_integrity_metadata
  → write_csv / write_json / store_metrics_sqlite / store_statement_integrity_sqlite
```

**Key modules:**

- **Text/bbox extraction:** `extract_pdf_text()` (subprocess `pdftotext -layout`), `parse_bbox_layout_lines()` (subprocess `pdftotext -bbox-layout`, then XML parse).
- **Table detection:** `detect_table_regions()`, `segment_statement_blocks()`, `classify_statement_scope()`.
- **Metric parsing:** `extract_metrics_from_blocks()`, `parse_line()`, `parse_numeric_word_token()`, `apply_unit_multiplier()`, `infer_unit_multiplier()`.
- **Output:** `write_csv()` (fixed field list L4136), `write_json()`, `store_metrics_sqlite()` (schema at L1366), `split_rows_by_scope()`, `dedupe()`.

---

### 1.4 Call flow — backend document processing

```
process_document(document_id) [pipeline.py L584]
  → _resolve_pdf_path(doc.pdf_path)        # relative under settings.docs_root
  → extract_text_from_pdf(pdf_path)        # text_extract.py: fitz.open → page.get_text("text")
  → simple_chunk(text, max_chars=4500)
  → [if enable_embeddings] _embed_chunks(chunks) → ollama_embed → upsert_points
  → [if enable_extraction] ollama_generate_json → _upsert_financial_rows
  → ExtractionRun written (status ok/failed)
```

---

### 1.5 Component → file → responsibility

| Component | File path | Responsibility |
|-----------|-----------|----------------|
| PDF text extraction (backend) | `financial-engine_v2/backend/app/services/text_extract.py` | `extract_text_from_pdf(pdf_path)`: PyMuPDF, concatenate page text. |
| PDF path resolution | `financial-engine_v2/backend/app/services/pipeline.py` | `_resolve_pdf_path()`, `_doc_path()`, `_canonical_doc_pdf_path()`, `_ensure_document_pdf_path()`. |
| Download + validate PDF | `financial-engine_v2/backend/app/services/pipeline.py` | `download_pdf_for_document()`, `_extract_pdf_url_from_html()`, write bytes, SHA256. |
| Chunking | `financial-engine_v2/backend/app/services/chunking.py` | `simple_chunk(text, max_chars=4500)` (fixed-size, no sentence boundary). |
| Financial metrics CLI | `scripts/extract_financial_metrics.py` | Full pipeline: find PDFs, bbox/text extraction, block segmentation, metric extraction, CSV/JSON/SQLite. |
| Bbox layout parsing | `scripts/extract_financial_metrics.py` | `parse_bbox_layout_lines()`: pdftotext -bbox-layout, XML, line/word bboxes. |
| Table/block segmentation | `scripts/extract_financial_metrics.py` | `segment_statement_blocks()`, `detect_table_regions()`, `classify_statement_scope()`. |
| Metric parsing (line) | `scripts/extract_financial_metrics.py` | `parse_line()`, NUM_RE/PCT_RE, METRIC_PATTERNS, period detection. |
| Metric parsing (blocks) | `scripts/extract_financial_metrics.py` | `extract_metrics_from_blocks()`, column/period alignment, `apply_unit_multiplier()`. |
| PDF RAG index | `scripts/pdf_rag.py` | `extract_pdf_text()` (pdftotext), `chunk_text()`, `build_index()`. |
| OCR last-resort | `scripts/ocr_last_resort.py` | Tesseract + pdftoppm; used by `section_capture_layer.py`, **not** by `extract_financial_metrics.py`. |

---

### 1.6 Dependencies (PDF parsing)

| Dependency | Used by | Purpose |
|------------|---------|---------|
| **poppler-utils** (pdftotext) | `extract_financial_metrics.py`, `pdf_rag.py` | Text extraction `-layout` and `-bbox-layout` (XML). |
| **pymupdf** (fitz) | Backend `text_extract.py`, pipeline; `update_ticker_financials.py`, cockpit tools, resource_library_workflow, announcement_importance | Open PDF, `page.get_text("text")`. |
| **lxml / xml.etree** | `extract_financial_metrics.py` | Parse pdftotext bbox XML. |
| **tesseract + pdftoppm** | `ocr_last_resort.py` (section_capture_layer) | OCR for scanned pages; optional, not in main metrics script. |

---

## 2. How to Run (as-is)

### 2.1 Financial metrics extraction (scripts)

**Requirements:** `pdftotext` on PATH (e.g. `sudo apt install -y poppler-utils`), Python 3.

```bash
# From repo root
python3 scripts/extract_financial_metrics.py --pdf-dir /path/to/pdfs \
  --out-csv reports/financial_metrics.csv \
  --out-json reports/financial_metrics.json \
  --no-sqlite
```

- **Strict (default):** table-first only; `extract_table_metrics()` per PDF; no line-by-line narrative parsing.
- **With narrative:** `--allow-narrative` (less strict).
- **Timeouts:** `--pdftotext-timeout-sec` (default 180).
- **High-confidence outputs:** `--min-confidence`, `--out-high-csv`, `--out-high-json`.

### 2.2 Backend document processing

Requires backend env (Postgres, config, optional Ollama/Qdrant). PDF must already be on disk at `doc.pdf_path` (after download).

- **Sync:** Call `pipeline.process_document(document_id)` (e.g. via API backfill with `task_mode=sync`).
- **Celery:** Enqueue `download_pdf` then `process_document` for a document.

### 2.3 Tests (no PDFs required)

```bash
python3 scripts/test_pdf_financial_tools.py
# 116 tests (mocked pdftotext); all pass.
```

---

## 3. Correctness Findings

### 3.1 Parsed output shape

- **Canonical rows:** List of dicts; each row has `file`, `line_no`, `metric`, `metric_base`, `metric_variant`, `metric_alias`, `value_type`, `raw_value`, `value`, `currency`, `period`, `statement_period`, `statement_period_end`, `balance_position`, `balance_date`, integrity fields, `confidence`, `line`, `row_label`, `inside_table`, statement scope/title/family, `block_id`, `table_id`, `table_page`, `page_number`, `note_number`, `source_mode`, `canonical_confidence_score`. See `write_csv()` field list (L4136) and SQLite schema (L1366).
- **Outputs:** CSV (canonical), JSON (canonical, context, rejected, blocks), optional SQLite (metrics + statement integrity tables), high-confidence CSV/JSON.

### 3.2 Run on sample PDF

- **Input:** `reports/sample_pdf_for_analysis/sample_financial.pdf` (1 page: “Consolidated statement of comprehensive income”, “Revenue 73.671 million FY25 70.0 million FY24”, “Net profit after tax 18.2m 17.1m”).
- **Result:** 2 canonical rows (revenue, net_income); 2 context rows; 1 statement block; high-confidence count 2.
- **Snippets:**
  - Revenue: `metric=revenue`, `raw_value=73.671`, `value=73.671`, `period=FY25`, `statement_period_end=2025-12-31`.
  - Net income: `metric=net_income`, `raw_value=18.2m`, `value=18200000`, `period=FY25`.

### 3.3 Accuracy / completeness

- **Revenue row:** Value is `73.671`; “million” is on the same line but not included in the numeric token used for this row, so the row is **not** scaled by 1e6. So **accuracy issue:** when number and unit suffix (“million”) are in separate bbox words or columns, the parsed value can remain unscaled.
- **Net income:** “18.2m” parsed correctly as 18,200,000.
- **Stability:** Three consecutive runs produced identical CSV (deterministic).

### 3.4 Parsing failure patterns (reproduction)

| Pattern | Observation | Reproduction |
|--------|-------------|--------------|
| Scanned PDF (no text layer) | No bbox/text; empty or near-empty; script reports “No metric candidates found. PDFs may be scanned images (OCR needed)”. | Use a PDF that is image-only. |
| Unit suffix in separate cell | Value may be unscaled (e.g. “73.671” + “million” in next column → value 73.671). | Table layout with number and “million” in different columns. |
| Multi-column tables | Layout-dependent; column detection is bbox-based; wrong column alignment can misassign periods or values. | Complex multi-period tables. |
| Encrypted / password PDF | Not explicitly handled; pdftotext/fitz will fail with library-specific errors. | Open a password-protected PDF. |
| Corrupt / invalid PDF | pdftotext returns non-zero; subprocess raises; script catches and adds context row with `parse_failed` / `table_parse_failed`. | Truncated or invalid file. |

---

## 4. Failure Mode Matrix

| Stage | Failure mode | Detection | Current handling | Recommended minimal fix |
|-------|--------------|-----------|------------------|--------------------------|
| **Metrics script: open PDF** | Corrupt / invalid file | `pdftotext` fails (subprocess) | Exception in strict path; caught in main loop; context row with `table_parse_failed` / `parse_failed`; stderr printed. | Add explicit check for `%PDF` magic before calling pdftotext; return structured failure reason. |
| **Metrics script: open PDF** | Encrypted / password | pdftotext fails | Same as above; message may be generic. | Classify error string (e.g. “password”) and set `context_reason=encrypted_pdf`. |
| **Metrics script: open PDF** | Scanned (no text) | Empty or near-empty bbox/text | No metrics; final message “PDFs may be scanned images (OCR needed)”. | Optionally run OCR last-resort (e.g. from `ocr_last_resort`) when bbox line count &lt; threshold and document in scope. |
| **Metrics script: extraction** | Timeout (large/slow PDF) | `subprocess.TimeoutExpired` | `PDFParseTimeoutError`; context row `pdftotext_timeout`; continue to next PDF. | Keep; optionally make timeout configurable per file size. |
| **Metrics script: write** | Partial write / disk full | IOError on write_csv/write_json/sqlite | Uncaught; process exits. | Wrap writes in try/except; log and re-raise or append to error list. |
| **Backend: extract_text_from_pdf** | Missing file / bad path | fitz.open() raises | No try/except in `process_document`; exception propagates; no ExtractionRun with status failed. | Wrap `extract_text_from_pdf` in try/except in `process_document`; on exception set status= failed, error= str(exc), classify with `classify_extraction_failure()`, commit ExtractionRun, then re-raise or return error payload. |
| **Backend: extract_text_from_pdf** | Corrupt PDF | fitz raises | Same as above. | Same as above. |
| **Backend: extract_text_from_pdf** | Encrypted PDF | fitz may raise or return empty | Same as above. | Same as above. |
| **Backend: download** | Not a PDF | Response !startswith(b'%PDF') | `ValueError` after HTML fallback; caught by caller; document fails. | Already handled. |
| **Backend: download** | Very large PDF | No size limit | Download runs to completion; may OOM or stall. | Optional max size check before or after download; reject or skip with marker. |

---

## 5. Performance Report

### 5.1 Timing (single small PDF)

- **File:** `reports/sample_pdf_for_analysis/sample_financial.pdf` (1 page, ~3 lines of text).
- **Command:** `python3 scripts/extract_financial_metrics.py --pdf-dir reports/sample_pdf_for_analysis --out-csv ... --no-sqlite`
- **Elapsed:** ~0.11 s wall.
- **User time:** ~0.10 s; CPU ~99%.
- **Peak RSS:** ~29 MB.

### 5.2 Bottlenecks (from code and single run)

- **Subprocess:** Two `pdftotext` calls per PDF in strict mode (`-layout` not used in strict path; only `-bbox-layout` via `_prepare_bbox_pages`). So one subprocess per PDF for bbox; XML parse and Python processing dominate for small PDFs.
- **Regex / Python:** Many regex passes (NUM_RE, period detection, metric patterns, section classification); CPU-bound.
- **No parallelism:** PDFs processed sequentially in `main()`.

### 5.3 Profiling

- No cProfile/py-spy run was performed. Recommended: `python3 -m cProfile -o profile.stats scripts/extract_financial_metrics.py --pdf-dir <dir> --no-sqlite` then inspect; or run under py-spy to see hotspots (likely `parse_bbox_layout_lines`, XML parse, `extract_metrics_from_blocks`).

### 5.4 Prioritized performance improvements (minimal, safe)

1. **Reuse bbox XML for same file:** If the same PDF is ever processed twice in one run, cache `parse_bbox_layout_lines` result by path (or hash). **Impact:** Low unless duplicate paths; **risk:** Low.
2. **Single pdftotext invocation:** Strict path only needs bbox layout; ensure no redundant `extract_pdf_text` call in the strict loop (confirmed: strict branch does not call `extract_pdf_text`). **Impact:** N/A; **risk:** N/A.
3. **Batch or pool PDFs:** Process PDFs in a small process pool to use multiple cores; keep output order deterministic if needed. **Impact:** Higher for many PDFs; **risk:** Medium (shared state, ordering).
4. **Lazy or streaming XML parse:** If pdftotext output is large, parse in a streaming way to reduce memory. **Impact:** Medium for very large PDFs; **risk:** Low.
5. **Timeout per PDF:** Already present (`--pdftotext-timeout-sec`); consider per-page or adaptive timeout for very large page counts. **Impact:** Reliability; **risk:** Low.

---

## 6. Validation Spec

### 6.1 Intended schema (inferred from code)

- **Canonical row fields:** See `write_csv()` in `scripts/extract_financial_metrics.py` (L4136): `file`, `line_no`, `metric`, `metric_base`, `metric_variant`, `metric_alias`, `value_type`, `raw_value`, `value`, `currency`, `period`, `statement_period`, `statement_period_end`, `balance_position`, `balance_date`, integrity fields, `confidence`, `line`, `row_label`, `inside_table`, statement scope/title/family/reason, `block_id`, `table_id`, `table_page`, `page_number`, `note_number`, `source_mode`, `canonical_confidence_score`.
- **SQLite:** `financial_metrics` table (L1366): same logical fields with `metric_row_id` PK, `value_num` for numeric value, `period_sort_date` / `period_sort_key`, `company`, `doc_type`, `doc_date` (from path/metadata).

### 6.2 Validation rules (enforce without changing architecture)

- **Type checks:** `value_type` in `{"amount", "percent", "text"}`; `value` numeric when `value_type` is amount/percent; `line_no` / `page_number` / `table_page` non-negative integers.
- **Numeric sanity:** For `value_type == "amount"`, `value` finite; optional bounds (e.g. |value| &lt; 1e18) to catch obvious parsing errors.
- **Required fields:** `file`, `metric`, `value_type` non-empty for canonical rows; `period` or `statement_period_end` present when metric is period-specific.
- **Confidence:** `confidence` in [0, 1]; `canonical_confidence_score` integer in allowed range (e.g. 0–4 if that’s the max).

### 6.3 Where to implement

- **Option A:** New function `validate_canonical_row(row) -> list[str]` in `scripts/extract_financial_metrics.py` returning list of error messages; call before or after `write_csv` / `store_metrics_sqlite`, or in a separate validation script that reads CSV/JSON.
- **Option B:** Standalone script that reads `--out-json` and prints validation errors (no change to extraction path).
- **Option C:** In `write_csv` or `store_metrics_sqlite`: optional validation gate; log and optionally skip invalid rows.

Recommended: **Option A + unit tests** that assert `validate_canonical_row` rejects bad rows and accepts good ones. Exact file: `scripts/extract_financial_metrics.py` (add function and optionally call from `main()` before writing).

---

## 7. Test Plan + Repro Pack

### 7.1 Existing tests

- **scripts/test_pdf_financial_tools.py:** 116 tests; load `extract_financial_metrics` and `pdf_rag` as modules; mock subprocess/timeouts; cover `parse_line`, period inference, confidence, classification, bbox parsing timeout, `split_rows_by_scope`, RAG index skip of unreadable PDF. **Gaps:** No real PDF on disk; no integration test that runs `main()` end-to-end with a small PDF; no validation tests for output schema.

### 7.2 Minimal added tests (without major refactor)

- **Integration:** One test that runs `extract_financial_metrics.main()` (or the extraction path) with a small fixture PDF in `reports/sample_pdf_for_analysis/` and asserts at least one canonical row and that output files exist. Requires fixture PDF committed or generated in setUp (e.g. with fitz from backend venv).
- **Validation:** Unit tests for `validate_canonical_row()`: valid row passes; missing `metric`, invalid `value_type`, negative `value` for amount, or `confidence` &gt; 1 fail.

### 7.3 One-command reproducible run

```bash
# 1) Create venv (optional; for consistent deps)
python3 -m venv .venv && . .venv/bin/activate

# 2) System dependency
sudo apt install -y poppler-utils   # pdftotext

# 3) Sample PDF (optional; use existing or create with backend venv)
financial-engine_v2/.venv/bin/python -c "
import fitz
from pathlib import Path
Path('reports/sample_pdf_for_analysis').mkdir(parents=True, exist_ok=True)
doc = fitz.open()
p = doc.new_page(595, 842)
p.insert_text((72, 72), 'Consolidated statement of comprehensive income', fontsize=12)
p.insert_text((72, 100), 'Revenue 73.671 million FY25', fontsize=10)
doc.save('reports/sample_pdf_for_analysis/sample_financial.pdf')
doc.close()
"

# 4) Run extraction
python3 scripts/extract_financial_metrics.py \
  --pdf-dir reports/sample_pdf_for_analysis \
  --out-csv reports/sample_pdf_for_analysis/out.csv \
  --out-json reports/sample_pdf_for_analysis/out.json \
  --no-sqlite

# 5) Run tests
python3 scripts/test_pdf_financial_tools.py
```

### 7.4 Patch: optional validation function and single test

See **Section 8** for a minimal validation function and one test addition; apply only if desired.

---

## 8. Minimal Change Recommendations (ranked)

| # | Recommendation | File(s) | Change | Why | Risk |
|---|----------------|---------|--------|-----|------|
| 1 | **Catch extraction exception in process_document** | `financial-engine_v2/backend/app/services/pipeline.py` | Wrap `extract_text_from_pdf(...)` in try/except. On exception: set status= failed, error= str(exc), classify with `classify_extraction_failure(error)`, create and commit `ExtractionRun`, then re-raise or return error dict so caller can continue with next document. | Ensures ExtractionRun is written and failure is classified even when PDF is missing/corrupt/encrypted; avoids unhandled exception and no DB record. | Low; behavior change only on exception path. |
| 2 | **Validate canonical rows before write** | `scripts/extract_financial_metrics.py` | Add `validate_canonical_row(row) -> list[str]` (type, required fields, numeric sanity, confidence range). Call before `write_csv`/`store_metrics_sqlite` or in a small validation script. Add unit tests. | Catches schema/type errors and obviously wrong values before persistence. | Low. |
| 3 | **Structured failure for encrypt/corrupt in metrics script** | `scripts/extract_financial_metrics.py` | In the except block that builds `_build_parse_failure_context_row`, inspect exception message; if "password" or "encrypted", set `reason=encrypted_pdf`; if "corrupt" or "invalid", set `reason=corrupted_pdf`. | Better observability and downstream handling. | Low. |
| 4 | **Check %PDF before pdftotext** | `scripts/extract_financial_metrics.py` | Before calling `parse_bbox_layout_lines`/`extract_pdf_text`, open file and read first 8 bytes; if not startswith(b'%PDF'), add context row with reason=not_pdf and skip pdftotext. | Fails fast and avoids confusing pdftotext errors. | Low. |
| 5 | **Optional OCR when bbox is empty** | `scripts/extract_financial_metrics.py` | If `_prepare_bbox_pages` returns empty and env or flag allows, call `ocr_last_resort.collect_ocr_candidates_for_pdf` for selected pages and merge into context/canonical path (with source_mode=ocr). | Improves coverage for scanned PDFs without changing default behavior. | Medium; new dependency on ocr_last_resort and tesseract availability. |

---

### Optional patch: validation function + one test

**File: `scripts/extract_financial_metrics.py`**

Add after `score_confidence` (e.g. after L4222):

```python
def validate_canonical_row(row: Dict[str, object]) -> List[str]:
    errors: List[str] = []
    if not str(row.get("file", "")).strip():
        errors.append("missing file")
    if not str(row.get("metric", "")).strip():
        errors.append("missing metric")
    vt = str(row.get("value_type", ""))
    if vt not in ("amount", "percent", "text"):
        errors.append(f"invalid value_type: {vt!r}")
    try:
        c = float(row.get("confidence", 0))
        if not (0 <= c <= 1):
            errors.append(f"confidence out of range: {c}")
    except (TypeError, ValueError):
        errors.append("invalid confidence")
    if vt in ("amount", "percent"):
        try:
            v = float(row.get("value", 0))
            if not abs(v) < 1e18:
                errors.append("value overflow")
        except (TypeError, ValueError):
            errors.append("invalid value for amount/percent")
    return errors
```

**File: `scripts/test_pdf_financial_tools.py`**

Add a test that imports and calls `validate_canonical_row` with a valid row (empty errors) and with invalid rows (e.g. missing metric, invalid value_type) and asserts non-empty errors.

---

*End of report.*
