# PDF extraction and chunking

Current extraction pipeline for `financial-engine_v2`.

This document reflects the live backend path used by `pipeline.process_document()`.

## 1. Path resolution

PDF paths are resolved relative to `docs_root` so the same logical document layout
works across local, worker, and scripted runs.

- path resolution lives in `financial-engine_v2/backend/app/services/pipeline.py`
- relative `pdf_path` values are resolved under `docs_root`
- absolute paths are preserved
- canonical stored paths are built from ticker/date/title/document_id

Before extraction starts, `pipeline.process_document()` also checks whether the
resolved file exists. If it does not exist and the document row still has an empty
`pdf_sha256`, the backend treats that row as pending download and runs the canonical
`download_pdf_for_document()` path before attempting structured extraction. This is
not a fallback extractor or alternate source of truth; it is the normal downloader
invoked slightly later in the same backend-owned pipeline.

## 2. Current extraction stack

The backend no longer uses a single-pass flat-text extraction path as its main flow.
The live path is:

1. title-only pre-extraction gate in `pipeline.process_document()`
2. `docling_extract.extract_structured()`
3. `multipass_extraction.run_multipass_extraction()`
4. prose chunking via `structured_chunking.chunk_prose_sections()`
5. metric persistence through the pipeline upsert path

### Pre-extraction title gate

The backend now avoids GPU extraction for clearly administrative ASX filings by checking the document title before any PDF parsing or LLM work.

Current behavior:

- known non-financial admin titles are marked `skipped_extraction`
- examples include substantial holder forms, director-interest forms, and securities cessation / quotation notices
- the gate is intentionally a narrow skip list, not an allow list
- structurally financial documents (`annual`, `half_year`, `4C`, `4D`, `4E`) are never skipped by this gate
- titles that do not match a known administrative pattern continue through the normal extraction path

This guard exists to save GPU time during backfills without increasing the risk of silently dropping legitimate financial documents.

### Structured extraction

`financial-engine_v2/backend/app/services/docling_extract.py` returns a
`StructuredDocument` with:

- `tables`
- `sections`
- `extraction_method`
- `page_count`

Backend selection:

- default backend: `docling`
- fast fallback or forced mode: `EXTRACTION_BACKEND=pymupdf`

Behavior today:

- docling cache files are stored beside the PDF
- PyMuPDF fallback is used when docling fails or docling output looks garbled
- PyMuPDF can also be selected explicitly for faster/local fallback workflows

## 3. Multipass extraction

`financial-engine_v2/backend/app/services/multipass_extraction.py` implements a
4-pass extraction pipeline:

1. document classifier
2. deterministic table locator
3. metric and narrative extraction
4. deterministic reconciliation

Current extractor version:

- `EXTRACTOR_VERSION = "docling_multipass_v1"`

The pipeline targets explicit metrics only and is designed to satisfy the extraction
contract in `SYSTEM_CONTRACT.md`:

- preserve source data
- extract explicit values only
- no silent fabrication
- deterministic post-processing only

## 4. Chunking behavior

There are now two chunking paths:

- `structured_chunking.chunk_prose_sections()`
  - used for prose sections from structured PDF extraction
  - default chunk size: 2000 chars
  - overlap: 150 chars
  - excludes tables from the embedding chunk path
- `structured_chunking.simple_chunk()`
  - retained mainly for backward compatibility and commentary ingestion
  - fixed-size splitting

This means document embeddings are no longer conceptually "flat PDF text chopped into
4500-char blocks" for the primary extraction path.

## 5. Quality and guard surfaces

Important quality/verification surfaces:

- `financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
- `financial-engine_v2/backend/tests/test_extraction_eval.py`
- `financial-engine_v2/backend/tests/eval_config.json`
- `financial-engine_v2/backend/tests/eval_fixtures/`

Operational inspection tools:

- `financial-engine_v2/scripts/inspect_qdrant_collection.py`
- `financial-engine_v2/scripts/inspect_extraction_provenance.py`
- `financial-engine_v2/scripts/verify_fixture_metrics.py`

## 6. Historical note

Older docs and reports may still mention:

- `app.services.text_extract`
- `app.services.chunking`
- single-pass Ollama JSON extraction

Those references are historical and do not describe the primary runtime path today.
