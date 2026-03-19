# PDF Extraction Audit

## Scope

Audit date: 2026-03-19 UTC

Scope covered:

- `financial-engine_v2` production ingestion pipeline
- root `scripts/` financial PDF extraction tooling
- current environment selection and validation assets

## Entry Points

### Ingestion services and workers

| Entry point | Path | Current extraction path |
| --- | --- | --- |
| Sync/celery document processing | `financial-engine_v2/backend/app/services/pipeline.py` | `extract_text_from_pdf` (PyMuPDF) -> `simple_chunk` -> `generate_json` -> `_upsert_financial_rows` -> embeddings/Qdrant |
| Celery task wrapper | `financial-engine_v2/backend/app/worker_tasks.py` | delegates to `pipeline.process_document()` |
| Legacy worker runtime | `financial-engine_v2/worker/app/tasks.py` | `extract_text_from_pdf` (PyMuPDF) -> chunking -> `ollama_generate_json` |

### Standalone scripts

| Entry point | Path | Current extraction path |
| --- | --- | --- |
| Local investment PDF preprocessing | `financial-engine_v2/scripts/preprocess_investment_pdfs.py` | PyMuPDF text or `pdftotext` text |
| Single-doc orchestration | `financial-engine_v2/scripts/extract_doc.py` | delegates to root `scripts/extract_pass_orchestrator.py` |
| Financial metrics extraction | `scripts/extract_financial_metrics.py` | `pdftotext` table/text parsing or Docling table parsing |
| Docling vs pdftotext comparison | `scripts/compare_docling_accuracy.py` | runs `extract_financial_metrics.py` twice per PDF |
| Review/audit cycle | `scripts/run_extraction_quality_cycle.sh` | canonical extraction -> quality audit -> coverage/review rebuild |
| Standalone Docling table export | `scripts/docling_export_tables.py` | direct Docling table export |
| OCR helper | `scripts/ocr_last_resort.py` | Tesseract candidate extraction helper only |

## Active Extraction Methods

| Method | Where used now | Invocation path | Dependencies | Environment | Notes |
| --- | --- | --- | --- | --- | --- |
| PyMuPDF full-text extraction | production backend, legacy worker, local preprocess, document excerpt helpers | `financial-engine_v2/backend/app/services/text_extract.py`, `financial-engine_v2/scripts/preprocess_investment_pdfs.py` | `pymupdf` | `financial-engine_v2/.venv` or whichever interpreter runs the script | Primary production text path. No OCR fallback in production pipeline. |
| `pdftotext` plain-text extraction | local preprocess, root qualitative/document helpers | `financial-engine_v2/scripts/preprocess_investment_pdfs.py`, `scripts/document_classifier.py`, `scripts/pdf_rag.py`, `scripts/build_qualitative_context_db.py` | `pdftotext` binary | main repo/runtime interpreter plus Poppler utils | Used for text comparison and several root utilities. |
| `pdftotext` bbox/layout table parsing | root financial metrics extraction | `scripts/extract_financial_metrics.py --extractor pdftotext` | `pdftotext` binary | main repo/runtime interpreter plus Poppler utils | Active canonical financial metric extractor. Uses table-first parsing plus rule-based normalization. |
| Docling table parsing | root financial metrics extraction and standalone table export | `scripts/extract_financial_metrics.py --extractor docling`, `scripts/docling_export_tables.py` | `docling`, `torch`, accelerator stack | dedicated Docling venv (`.venv-docling-gpu*` currently present; new wrapper targets `.venv_docling`) | Active only in root extraction stack, not in `financial-engine_v2` production backend. |
| LLM JSON extraction | production backend and legacy worker | `financial-engine_v2/backend/app/services/pipeline.py`, `financial-engine_v2/worker/app/tasks.py` | `httpx`, configured LLM runtime | backend runtime queues `llm_cpu` / `llm_gpu` | Structured JSON schema for core financials/risk narrative. |
| Regex/rule-based normalization | root financial metrics extraction | `scripts/extract_financial_metrics.py`, `scripts/extract_pass_orchestrator.py` | stdlib regex + local normalization modules | main repo/runtime interpreter | Active normalization/promotion layer after table parsing. |
| OCR candidate extraction | helper only | `scripts/ocr_last_resort.py` | `tesseract`, `pdftoppm` | main repo/runtime interpreter plus system binaries | Present but not wired into the primary financial extraction flow. |

## Not Active In Current Runtime

These are referenced, but not currently invoked by a live extraction path in the checked-in runtime:

- Camelot: only test/provenance references (`scripts/test_cashflow_table_fallback.py`, `scripts/provenance_contract.py`)
- Tabula: no active usage found
- PDFMiner: no active usage found
- `pytesseract`: no active usage found; OCR helper shells out to `tesseract`

## Environment Handling

### Current environments detected in code and workspace

- `financial-engine_v2/.venv`
- `financial-engine_v2/venv`
- repo root `.venv-docling-gpu`
- repo root `.venv-docling-gpu-repair`

### Current environment selection behavior

- `financial-engine_v2/scripts/run_backend.sh` and `financial-engine_v2/scripts/run_worker.sh` force `VENV_PATH=.venv`
- `financial-engine_v2/config/system.env` sets `VENV_PATH=.venv`
- `financial-engine_v2/cockpit/core/actions.py` hardcodes `.venv/bin/python`
- `financial-engine_v2/scripts/cockpit_tui.py` prefers `.venv/bin/python`, otherwise falls back to `sys.executable`
- root `scripts/runtime_python.py` resolves Docling runtime from `DOCILING_PYTHON` / `DOCLING_PYTHON`, then `.venv-docling-gpu`, else plain `python3`

### Isolation findings

- `financial-engine_v2/backend/requirements.txt` currently installs `docling` and `sentence-transformers` into the main backend environment. That means heavy Docling dependencies are not isolated from the main runtime today.
- Root Docling tooling already assumes a dedicated venv (`.venv-docling-gpu*`), but falls back to `python3` if that venv is not selected.
- No `pyproject.toml`, Poetry, or Conda environment was found in the active workspace.
- The biggest current leakage risk is direct script execution through `#!/usr/bin/env python3`, `sys.executable`, or `python3` fallback paths outside the managed `.venv`.

### New enforcement layer

- `services/extraction/docling_runner.py` introduces a subprocess-only Docling launcher.
- Default target venv: `.venv_docling`
- Behavior:
  - probes or creates `.venv_docling`
  - strips `PYTHONHOME`
  - forces `PYTHONNOUSERSITE=1`
  - injects the target venv `bin/` at the front of `PATH`
  - never imports Docling in the main process

## Existing Evaluation and Validation Logic

### Current accuracy/evaluation assets

| Asset | Path | What it measures |
| --- | --- | --- |
| Text overlap audit | `financial-engine_v2/scripts/preprocess_investment_pdfs.py` | PyMuPDF vs `pdftotext` token-overlap Jaccard |
| Docling comparison harness | `scripts/compare_docling_accuracy.py` | `pdftotext` canonical rows vs Docling canonical rows |
| Gold scoring | `scripts/score_gold_set.py` | canonical CSV vs per-document gold JSON fields |
| Review set builder | `scripts/build_pdf_metric_review_set.py` | samples canonical rows for manual review |
| Quality audit | `scripts/audit_financial_metric_quality.py` | balance-sheet, cash-flow, retained earnings, income consistency checks |
| Review cycle orchestration | `scripts/run_extraction_quality_cycle.sh` | end-to-end extraction/audit/review artifact rebuild |

### Fixtures and datasets found

- `financial-engine_v2/scripts/test_preprocess_investment_pdfs.py` generates temporary PDFs for parser comparison tests
- `reports/pdf_metric_review_source_gated_v2_canonical/manifest.json` contains sampled parsed review items and source PDFs
- `scripts/score_gold_set.py` expects a separate gold directory of JSON files; no single checked-in production gold set was found in the current workspace

### Validation gaps

- `financial-engine_v2` production backend has no built-in ground-truth scoring for `generate_json`
- OCR helper has tests, but is not integrated into the primary financial metrics path
- Main backend text extraction has no fallback comparison against `pdftotext` or OCR
- Docling isolation exists by convention in root tooling, not by enforced boundary in the main backend runtime

## Benchmark Harness

- `scripts/benchmark_pdf_extraction.py` provides a read-only extraction registry plus a multi-method benchmark runner
- Inputs:
  - one or more `--pdf` paths, or `--pdf-dir`
  - optional `--ground-truth` JSON file/directory (defaults to `data/ground_truth/`)
  - optional `--gold-dir` legacy alias
  - optional `--docling-venv` and `--create-docling-venv`
- Outputs:
  - structured JSON report
  - per-document, per-method runtime
  - per-document, per-method extraction completeness
  - per-method failure rate summary
  - per-metric deterministic scoring when ground truth is present
  - `DATA_MISSING` when no matching ground truth exists

## Evaluation Methodology

### Canonical metric schema

Current scorer normalizes both prediction and ground truth onto:

- `revenue`
- `ebitda`
- `net_income`
- `assets`
- `liabilities`

Alias examples are normalized into those keys (`total_revenue` / `sales` -> `revenue`, `npat` -> `net_income`, `total_assets` -> `assets`, etc.).

### Scoring definitions

Implemented in `services/evaluation/scorer.py`:

- `EXACT_MATCH`: predicted value equals ground-truth value exactly
- `TOLERANCE_MATCH`: absolute error is within `±2%` of ground-truth value
- `MISSING`: no predicted value for a ground-truth metric key
- `INCORRECT`: predicted value exists but is outside `±2%` tolerance

Aggregate fields:

- `accuracy`: `(EXACT_MATCH + TOLERANCE_MATCH) / total_ground_truth_metrics`
- `completeness`: `(total_ground_truth_metrics - MISSING) / total_ground_truth_metrics`
- `exact_match_rate`: `EXACT_MATCH / total_ground_truth_metrics`
- `tolerance_match_rate`: `TOLERANCE_MATCH / total_ground_truth_metrics`

### Ground truth format and loading

Ground truth is external JSON only, loaded via `services/evaluation/ground_truth_loader.py`.

Accepted document shape:

```json
{
  "pdf": "sample.pdf",
  "metrics": {
    "revenue": 123456000,
    "ebitda": 45678000,
    "net_income": 12345000
  }
}
```

Partial metrics are valid; omitted keys are not scored for that document.

### Draft generation flow

`scripts/generate_ground_truth.py`:

- runs selected callable extraction methods per PDF
- chooses best-available method deterministically by:
  - successful run status
  - canonical metric coverage count/rate
  - runtime tie-breaker
- emits draft records with `status = REQUIRES_REVIEW`
- does not claim label correctness

### Method ranking interpretation

`benchmark_pdf_extraction.py` now emits method comparison output:

- `methods[]`: per-method `accuracy`, `completeness`, `latency`
- `ranking[]`: sorted by
  1. accuracy (descending)
  2. completeness (descending)
  3. latency (ascending)

When no ground truth is available, accuracy remains zero and ranking falls back to completeness/latency tie behavior, with document-level score status marked `DATA_MISSING`.

## Routing Strategy

### Additive routing components

- `services/extraction/pdf_classifier.py`
- `services/extraction/router.py`
- `scripts/run_batch_benchmark.py`
- `scripts/run_routed_extraction.py`

These are additive orchestration utilities and do not modify extraction method internals.

### Deterministic routing policy

Default route:

- `financial_metrics_pdftotext`

Docling override conditions:

- Docling metric coverage exceeds pdftotext coverage (when both method results are available)
- rejected rows exceed threshold
- inferred table complexity exceeds threshold
- inferred table density exceeds threshold
- `docling_row_count_before_filtering` exceeds pdftotext canonical row count

Special-case rule:

- `appendix_report` remains pinned to `financial_metrics_pdftotext`

### Lightweight classifier outputs

`pdf_classifier` emits:

- `document_type`
- `complexity_score`
- `table_density`

Inputs come from existing diagnostics only (`context_rows`, `rejected_rows`, table counts, statement type counts, canonical row counts).

### Batch and routed execution

`run_batch_benchmark.py`:

- executes the existing benchmark across a PDF directory
- aggregates per-method accuracy/completeness/latency
- simulates routing on benchmark outputs
- reports:
  - `full_benchmark_accuracy`
  - `routed_accuracy`
  - `compute_reduction` (Docling-run reduction)

`run_routed_extraction.py`:

- performs pdftotext-only probe per PDF
- routes deterministically
- runs only the selected extractor for final metrics
- outputs selected method, metrics, and routing reason per document

### Tradeoffs

- Benefits:
  - lower Docling execution volume on simple PDFs
  - deterministic and auditable routing behavior
  - no extraction logic changes required
- Costs:
  - routing quality depends on diagnostic signal quality
  - conservative defaults can under-route complex PDFs if diagnostics are weak
  - routed mode may sacrifice oracle (full benchmark) accuracy on edge cases

## Coverage by Document Type

| Document type | Current method coverage |
| --- | --- |
| ASX announcements and periodic PDFs in `financial-engine_v2` | PyMuPDF full text + LLM JSON extraction |
| Annual / half-year / quarterly appendix reports in root extraction stack | `pdftotext` table parsing and Docling table parsing |
| Local investment methodology/reference PDFs | PyMuPDF or `pdftotext` text extraction only |
| Scanned / near-empty text PDFs | OCR helper exists, but only as manual/helper path |

## CPU vs GPU Observations

- PyMuPDF, `pdftotext`, regex normalization, and OCR helper are CPU paths
- `financial-engine_v2` LLM extraction is queue-routed (`llm_cpu` / `llm_gpu`) but still depends on external model runtimes
- Docling is the only explicit GPU-capable PDF parser in the checked-in code; it also supports CPU fallback
- Current inefficiency: backend main environment includes heavy Docling dependencies even though production extraction does not invoke Docling there

## Failure Modes Seen in Code

- Table misreads:
  - Docling fallback policy exists because table coverage can be weak or incomplete
  - `pdftotext` table parsing can timeout or fail on malformed layouts
- Numeric parsing errors:
  - root extractor has extensive normalization and reconciliation logic because raw table values need scaling/sign repair
- OCR fallback reliability:
  - OCR is fail-closed and dependency-gated, but not integrated into the main path
- Inconsistent formatting across PDFs:
  - root extractor contains large rule/heuristic layers for period labels, scope inference, and statement classification
- Backend production path:
  - PyMuPDF text extraction has no fallback if the text layer is missing or poor
  - LLM JSON extraction has failure taxonomy but no checked-in gold scoring

## Expected Accuracy Ranking From Code Paths

This ordering is based on implementation depth and validation surfaces in the codebase, not on observed benchmark results:

1. Structured financial table extraction with canonical normalization:
   - `scripts/extract_financial_metrics.py --extractor docling`
   - `scripts/extract_financial_metrics.py --extractor pdftotext`
2. Full-text extraction plus fixed-schema LLM JSON:
   - `financial-engine_v2/backend/app/services/pipeline.py`
   - `financial-engine_v2/worker/app/tasks.py`
3. OCR candidate generation:
   - `scripts/ocr_last_resort.py`

Text-only extractors (`PyMuPDF` / plain `pdftotext`) are best treated as upstream parsing layers rather than direct metric extractors.

## Strengths and Weaknesses Summary

### PyMuPDF production path

Strengths:

- simple shared backend path
- low overhead
- deterministic

Weaknesses:

- no OCR fallback
- no built-in extraction accuracy scoring
- depends on LLM step for structured metrics

### Root `pdftotext` financial extraction

Strengths:

- strongest checked-in validation surface
- canonical normalization and audit tooling already exist
- direct metric rows instead of free-form text

Weaknesses:

- depends on Poppler binaries
- formatting-sensitive
- OCR not integrated into main flow

### Root Docling financial extraction

Strengths:

- layout/table-aware parser
- existing comparison and fallback diagnostics
- GPU-capable

Weaknesses:

- heavy dependency stack
- current isolation is convention-based without a single enforced wrapper in legacy tooling
- runtime drift across `.venv-docling-gpu*` and fallback `python3`

### Backend LLM JSON extraction

Strengths:

- production-ready downstream shape
- directly populates normalized financial/risk tables

Weaknesses:

- no checked-in gold-set comparison
- result quality is tied to upstream text quality and live model behavior

### OCR helper

Strengths:

- explicit fail-closed behavior
- useful for scanned PDFs

Weaknesses:

- not part of the primary extraction path
- usually lacks metric labeling without a downstream reconciliation step
