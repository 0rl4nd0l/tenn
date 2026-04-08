# PDF Extraction Pipeline — Entry Points and Module Structure Audit

**Date:** 2026-04-02
**Task:** 052d1157689d (subtask of 460f9a44359a)
**Scope:** Trace PDF extraction entry points, map module structure, document execution paths from input to output.

---

## 1. Entry Points

The PDF extraction pipeline has **four entry point tiers**: CLI runners, API routes, Celery worker tasks, and direct service calls.

### 1.1 CLI Runners (Top-Level)

| File | Role |
|------|------|
| `run.py` (repo root) | Delegates to `financial-engine_v2/run.py` |
| `financial-engine_v2/run.py` | Orchestrator — dispatches `scripts/full_history_ticker_sync.py` and/or `scripts/daily_marketindex_action.py` based on `CONFIG["workflow"]` |

`run.py` sets `TASK_MODE=sync` by default, meaning pipeline functions execute inline (no Celery).

### 1.2 API Routes (FastAPI)

**File:** `financial-engine_v2/backend/app/api/routes.py`

| Route | Method | Function | Description |
|-------|--------|----------|-------------|
| `/backfill/asx20` | POST | `backfill_asx20()` | Backfills all ASX20 tickers |
| `/backfill/ticker/{ticker}` | POST | `backfill_ticker()` | Backfills a single ticker |
| `/process/document/{document_id}` | POST | `process_single_document()` | Re-processes one document |
| `/process/ticker/{ticker}` | POST | `process_unextracted_for_ticker()` | Processes all un-extracted docs for a ticker |

Each route checks `settings.task_mode`:
- `sync` → calls `run_pipeline_sync()` / `process_document()` directly
- `celery` → dispatches via `celery.send_task()` to queue `"ingest"`

### 1.3 Celery Worker Tasks

**File:** `financial-engine_v2/backend/app/worker_tasks.py`

| Task Name | Function | Delegates To |
|-----------|----------|-------------|
| `backfill_ticker` | `backfill_ticker()` | `pipeline_service.run_pipeline_sync()` |
| `download_pdf` | `download_pdf()` | `pipeline.download_pdf_for_document()` |
| `process_document` | `process_document()` | `pipeline.process_document()` |
| `llm_generate_json` | `llm_generate_json_task()` | `llm.generate_json()` |
| `llm_embed_texts` | `llm_embed_texts_task()` | `llm.embed_texts()` |

### 1.4 Pipeline Service (Orchestration Layer)

**File:** `financial-engine_v2/backend/app/services/pipeline_service.py`

- `PipelineJobSpec` — frozen dataclass defining a pipeline job (ticker, years, process_documents, mode)
- `PipelineResult` — TypedDict for pipeline output metrics
- `run_pipeline_sync(spec)` — main sync orchestrator:
  1. Calls `pipeline.discover_and_insert_documents()`
  2. Iterates over discovered document IDs
  3. For each: `download_pdf_for_document()` then `process_document()`
  4. Runs `classify_documents_and_materialize()` for importance scoring

---

## 2. Core Pipeline Module

**File:** `financial-engine_v2/backend/app/services/pipeline.py` (~1050 lines)

### 2.1 Key Functions

| Function | Line | Role |
|----------|------|------|
| `discover_and_insert_documents()` | ~704 | Discovers documents via ASXProvider + MarketIndexProvider, filters quarantine rules, inserts into DB |
| `insert_discovered_documents()` | ~514 | Batch-inserts discovered docs into `documents` table (race-safe with IntegrityError fallback) |
| `download_pdf_for_document()` | ~751 | Downloads PDF from source URL, validates `%PDF` header, writes to disk, computes SHA256 |
| `process_document()` | ~853 | **Core extraction orchestrator** — runs multipass extraction, chunks prose, embeds, upserts to Qdrant and Postgres |
| `_upsert_financial_rows()` | ~795 | Upserts into `asx_periodic_financials` and `asx_risk_notes` tables |
| `_embed_chunks()` | ~193 | Embeds text chunks with optional in-memory cache |

### 2.2 Helper Functions

| Function | Role |
|----------|------|
| `_match_document_quarantine_reason()` | Filters documents by configurable quarantine rules |
| `classify_extraction_failure()` | Categorizes failures into taxonomy (ocr, timeout, json, network, corrupted, unknown) |
| `_extract_pdf_url_from_html()` | Resolves actual PDF URL from HTML landing pages |
| `_resolve_pdf_path()` | Normalizes relative paths against `settings.docs_root` |
| `_normalize_source_url()` | URL canonicalization for deduplication |

---

## 3. PDF Structure Extraction Module

**File:** `financial-engine_v2/backend/app/services/docling_extract.py` (~449 lines)

### 3.1 Data Structures

| Class | Description |
|-------|-------------|
| `DoclingTable` | One financial table: page_number, caption, rows (list of list of str), headers |
| `StructuredDocument` | Full PDF output: tables, sections, extraction_method, page_count, docling_version |

### 3.2 Entry Point

```
extract_structured(pdf_path, backend="") → StructuredDocument
```

Backend selection (env `EXTRACTION_BACKEND` or kwarg):
- `"docling"` (project default) — IBM Docling with TableFormer
- `"pymupdf"` — PyMuPDF `find_tables()`, fast (~1-25s), fallback/override

### 3.3 Execution Flow

```
extract_structured()
  ├─ Check cache ({pdf_path}.{backend}.json)
  │   ├─ Cache hit + valid → return cached StructuredDocument
  │   └─ Cache hit + garbled tables → fall through to PyMuPDF
  ├─ backend == "docling"?
  │   ├─ _get_page_count_fast() → adaptive timeout
  │   ├─ _run_docling_with_timeout() → SIGALRM-guarded docling
  │   │   └─ _run_docling() → DocumentConverter → tables + sections
  │   ├─ _has_garbled_tables()? → fall back to PyMuPDF
  │   └─ _save_cache()
  └─ backend == "pymupdf"
      ├─ _extract_pymupdf()
      │   ├─ For each page: get_text("dict") → heading detection
      │   ├─ For each page: find_tables() → DoclingTable objects
      │   ├─ Merge split tables across page breaks (matching headers)
      │   └─ _has_garbled_tables() → mark as "pymupdf_degraded" if garbled
      └─ _save_cache()
```

### 3.4 Quality Guards

- `_is_garbled()` — detects font-encoding garbling (fixed ASCII offset from PDF font subsetting)
- `_has_garbled_tables()` — samples table cells; if >=2 garbled → triggers PyMuPDF fallback
- Cross-page table merging — continuation tables (same headers, next page, no caption) are merged

---

## 4. Multipass Extraction Module

**File:** `financial-engine_v2/backend/app/services/multipass_extraction.py` (~1548 lines)

### 4.1 Entry Point

```
run_multipass_extraction(pdf_path, doc_metadata, llm_client, skip_narrative=False) → MultipassResult
```

### 4.2 Four-Pass Architecture

```
Pass 1: Document Classifier (LLM)
  → report_type (A/H/Q), period_end, currency, scale, confidence
  → Scale override from table headers (_detect_scale_from_tables)

Pass 2: Table Locator (deterministic)
  → Labels each DoclingTable as: cashflow_statement, income_statement,
    balance_sheet, share_capital, highlights, or unmatched
  → Keyword scoring + header bonus + disqualification rules
  → Merges split CF tables (Appendix 5B) into synthetic table

Pass 3a: Metric Extractor (LLM, per table, parallel)
  → One LLM call per labelled table
  → Extracts: revenue, ebit, np_attributable, operating_cf, investing_cf,
    financing_cf, capex, cash_end, net_debt, shares_outstanding
  → Applies scale multiplier (except shares_outstanding)
  → Row filtering for large tables (>20 rows) to reduce tokens

Pass 3b: Narrative Extractor (LLM)
  → risk_summary, risk_bullets, guidance_summary, material_changes
  → Skippable via skip_narrative=True or EXTRACTION_SKIP_NARRATIVE=1

Pass 4: Reconciler (deterministic)
  → Merges all Pass 3a results by source priority:
    income_statement > cashflow_statement > balance_sheet > share_capital > highlights
  → Derives net_debt from total_debt - cash_end if not directly extracted
  → Prose fallback for shares_outstanding (regex patterns on note sections)
  → Scale validation (under/over-scaled detection)
  → Validation gate: period_end required, >=3 non-null metrics, confidence >=0.60
```

### 4.3 Key Functions

| Function | Pass | Type | Role |
|----------|------|------|------|
| `_run_pass1_classifier()` | 1 | LLM | Classifies document metadata |
| `_detect_scale_from_tables()` | 1 | Deterministic | Scans table headers for $'000, millions, etc. |
| `_run_pass2_locator()` | 2 | Deterministic | Scores and labels tables by statement type |
| `_merge_cf_tables()` | 2 | Deterministic | Merges split cashflow tables |
| `_run_pass3a_metric_extractor()` | 3a | LLM | Parallel metric extraction per table |
| `_extract_single_table()` | 3a | LLM | Single table extraction with scale multiplier |
| `_filter_table_rows()` | 3a | Deterministic | Row filtering for token reduction |
| `_run_pass3b_narrative_extractor()` | 3b | LLM | Risk/guidance narrative extraction |
| `_extract_shares_from_prose()` | 4 | Deterministic | Regex-based shares_outstanding fallback |
| `_run_pass4_reconciler()` | 4 | Deterministic | Merges, validates, builds final payload |
| `_validate_scale()` | 4 | Deterministic | Under/over-scale detection |
| `_validate_gate()` | 4 | Deterministic | Final quality gate before DB upsert |
| `_llm_json_call()` | Helper | LLM | Unified LLM caller (Anthropic SDK or OpenAI-compat) |

### 4.4 Constants

- `EXTRACTOR_VERSION = "docling_multipass_v1"` — stored in ExtractionRun
- `PROMPT_HASH` — SHA256 of all prompt templates (first 16 chars)
- `SANITY_CAP = 500_000_000_000` ($500B) — maximum plausible metric value
- `METRIC_FIELDS` — 10 canonical metrics
- `SOURCE_PRIORITY` — income_statement > cashflow_statement > balance_sheet > share_capital > highlights

---

## 5. Complete Execution Path: Input → Output

```
[External trigger: API route, CLI runner, or Celery task]
    │
    ▼
run_pipeline_sync(PipelineJobSpec)              [pipeline_service.py]
    │
    ├─ discover_and_insert_documents()          [pipeline.py:704]
    │   ├─ ASXProvider().discover()              ASX API discovery
    │   ├─ MarketIndexProvider().discover()      MarketIndex fallback
    │   ├─ Quarantine filtering
    │   └─ insert_discovered_documents()         DB: documents table
    │
    ├─ For each document_id:
    │   ├─ download_pdf_for_document()           [pipeline.py:751]
    │   │   ├─ HTTP download (httpx + scrapling fallback)
    │   │   ├─ %PDF header validation
    │   │   ├─ HTML→PDF URL resolution if needed
    │   │   └─ write_bytes() + sha256_file()     Disk + DB update
    │   │
    │   └─ process_document()                    [pipeline.py:853]
    │       │
    │       ├─ [if ENABLE_EXTRACTION]
    │       │   └─ run_multipass_extraction()     [multipass_extraction.py:1357]
    │       │       ├─ extract_structured()       [docling_extract.py:236]
    │       │       │   ├─ Cache check
    │       │       │   ├─ PyMuPDF or Docling extraction
    │       │       │   └─ → StructuredDocument (tables + sections)
    │       │       │
    │       │       ├─ Pass 1: _run_pass1_classifier()     LLM → period, scale, currency
    │       │       ├─ _detect_scale_from_tables()          Table header override
    │       │       ├─ Pass 2: _run_pass2_locator()         Keyword scoring → labelled tables
    │       │       ├─ Pass 3a: _run_pass3a_metric_extractor()  Parallel LLM → metrics
    │       │       ├─ Pass 3b: _run_pass3b_narrative_extractor()  LLM → risk/guidance
    │       │       ├─ Pass 4: _run_pass4_reconciler()      Merge + validate
    │       │       └─ → MultipassResult(status, payload, sections)
    │       │
    │       ├─ chunk_prose_sections()             [structured_chunking.py]
    │       │   └─ StructuredDocument.sections → text chunks (2000 char, 150 overlap)
    │       │
    │       ├─ [if ENABLE_EMBEDDINGS]
    │       │   └─ _embed_chunks()                [pipeline.py:193]
    │       │       └─ embed_texts() via Ollama (nomic-embed-text)
    │       │
    │       ├─ [if ENABLE_QDRANT]
    │       │   ├─ ensure_collection()
    │       │   ├─ validate_payload() per point
    │       │   ├─ delete_points_for_document()   Idempotent re-index
    │       │   └─ upsert_points()                Qdrant vector store
    │       │
    │       ├─ ExtractionRun record               DB: extraction_runs table
    │       ├─ [if status ok/ok_low_confidence]
    │       │   └─ _upsert_financial_rows()       DB: asx_periodic_financials + asx_risk_notes
    │       └─ db.commit()                        Atomic: ExtractionRun + financials
    │
    └─ classify_documents_and_materialize()       Importance scoring

OUTPUT:
  ├─ Postgres: documents, extraction_runs, asx_periodic_financials, asx_risk_notes
  ├─ Qdrant: asx_docs collection (prose chunk vectors)
  ├─ Disk: PDF files under DOCS_ROOT/{ticker}/
  └─ Disk: Extraction cache ({pdf}.pymupdf.json or {pdf}.docling.json)
```

---

## 6. Supporting Modules

| Module | File | Role |
|--------|------|------|
| `llm.py` | `backend/app/services/llm.py` | Unified LLM interface: `generate_json()`, `embed_texts()`, routing |
| `structured_chunking.py` | `backend/app/services/structured_chunking.py` | Prose section chunker (excludes tables, 2000 char chunks) |
| `embeddings.py` | `backend/app/services/embeddings.py` | Qdrant collection management, upsert, validation |
| `storage.py` | `backend/app/services/storage.py` | `write_bytes()`, `sha256_file()`, `ensure_dir()` |
| `llamacpp_runtime.py` | `backend/app/services/llamacpp_runtime.py` | llama.cpp JSON generation, control char sanitization |
| `validation/extraction_schemas.py` | `backend/app/services/validation/` | Pandera extraction output schema |
| `celery_app.py` | `backend/app/celery_app.py` | Celery broker config (Redis) |

---

## 7. Configuration Surface

| Env Var | Default | Effect |
|---------|---------|--------|
| `ENABLE_EXTRACTION` | `false` | Enables multipass LLM extraction |
| `ENABLE_EMBEDDINGS` | `false` | Enables Ollama embedding |
| `ENABLE_QDRANT` | `false` | Enables Qdrant vector upsert |
| `EXTRACTION_BACKEND` | `docling` | `pymupdf` or `docling` |
| `EXTRACTION_PARALLEL` | `1` | Parallel Pass 3a table extractions |
| `EXTRACTION_FILTER_ROWS` | `1` | Row filtering for large tables |
| `EXTRACTION_SKIP_NARRATIVE` | `` | Skip Pass 3b narrative extraction |
| `EXTRACTION_SKIP_REDUNDANT` | `1` | Skip highlights when IS+CF present |
| `TASK_MODE` | `sync` | `sync` or `celery` |
| `LLAMACPP_URL` | `http://127.0.0.1:8001` | LLM endpoint for extraction |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Embedding endpoint |
