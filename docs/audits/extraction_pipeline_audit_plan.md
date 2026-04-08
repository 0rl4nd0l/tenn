# Extraction Pipeline & Financial Metric Database — Audit Plan

**Date:** 2026-04-02
**Scope:** PDF extraction pipeline + financial metric database only
**Method:** Trace execution paths, run available tests, report confirmed findings with file/function citations
**Branch:** agent/manager-5768a36d

---

## Pipeline Architecture Summary

```
ASX Provider (PDF download + SHA256)
  |
  v
Document row (documents table)
  |
  v
docling_extract.py::extract_structured()  -- PDF -> tables + prose sections
  |
  +---> structured_chunking.py  -- prose -> Qdrant embeddings
  |
  +---> multipass_extraction.py::run_multipass_extraction()  -- 4-pass LLM pipeline
          |
          Pass 1: _run_pass1_classifier()     [LLM] period_end, currency, scale
          Pass 2: _run_pass2_locator()         [deterministic] table labelling
          Pass 3a: _run_pass3a_metric_extractor() [LLM] 10 financial metrics
          Pass 3b: _run_pass3b_narrative_extractor() [LLM] risk/guidance (optional)
          Pass 4: _run_pass4_reconciler()      [deterministic] merge + scale
          |
          v
pipeline.py::_upsert_financial_rows()  -- atomic write to DB
  |
  +---> asx_periodic_financials (10 metrics per row)
  +---> asx_risk_notes (narrative data)
  +---> extraction_runs (provenance tracking)
```

---

## Decomposed Audit Tasks

### Task 1 — PDF Extraction Module Audit
**Target files:**
- `financial-engine_v2/backend/app/services/docling_extract.py`

**Checkpoints:**
1. Trace `extract_structured()` entry point — verify Docling vs PyMuPDF backend selection logic
2. Audit fallback chain: Docling timeout -> PyMuPDF -> garbled detection handling
3. Verify cache implementation (`{pdf_path}.docling.json` / `.pymupdf.json`) — check mtime validation, version pinning
4. Audit timeout configuration: adaptive 4s/page, 300s cap — verify enforcement
5. Check error handling: what happens when both backends fail?
6. Verify `StructuredDocument` output contract: tables + sections structure

**Test file:** `tests/test_docling_extract.py`

---

### Task 2 — Multipass Extraction Pipeline Audit
**Target files:**
- `financial-engine_v2/backend/app/services/multipass_extraction.py`

**Checkpoints:**
1. Trace `run_multipass_extraction()` orchestrator — verify pass ordering and data flow
2. **Pass 1 (classifier):** Audit LLM prompt for period_end/currency/scale extraction. Check confidence threshold (0.60) enforcement
3. **Pass 2 (locator):** Audit keyword-based table classification — verify score tiebreaking, Appendix 5B merge logic, disqualifier rules
4. **Pass 3a (metric extractor):** Audit LLM prompt for 10-metric extraction. Verify `METRIC_FIELDS` contract: `[revenue, ebit, np_attributable, operating_cf, investing_cf, financing_cf, capex, cash_end, net_debt, shares_outstanding]`
5. **Pass 3b (narrative):** Verify skip logic via `EXTRACTION_SKIP_NARRATIVE` env flag
6. **Pass 4 (reconciler):** Audit scale multiplication, source priority resolution, period_start derivation, conflict handling
7. Audit `_detect_scale_from_tables()` — verify pattern matching for $'000, $M, billions
8. Verify `MultipassResult` status enum: `ok | ok_low_confidence | failed`
9. Check shares_outstanding handling — must be count (not monetary-scaled)

**Test file:** `tests/test_multipass_extraction.py`

---

### Task 3 — Pipeline Orchestration Audit
**Target files:**
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/app/services/pipeline_service.py`

**Checkpoints:**
1. Trace `process_document(document_id)` end-to-end — verify call sequence: extraction -> chunking -> embedding -> DB write
2. Audit `_upsert_financial_rows()` — verify atomic transaction (ExtractionRun + financials in same commit)
3. Verify SHA256 deduplication — does re-processing the same PDF skip or overwrite?
4. Check error propagation: if extraction fails, are partial results written?
5. Verify `PipelineJobSpec` construction in `pipeline_service.py` for backfill workflows
6. Audit Celery task wiring in `worker_tasks.py` — verify sync vs. async mode (`TASK_MODE`)

**Test files:** integration tests if available

---

### Task 4 — Database Model & Schema Audit
**Target files:**
- `financial-engine_v2/backend/app/models/asx_financials.py`
- `financial-engine_v2/backend/app/models/extractions.py`
- `financial-engine_v2/backend/app/models/documents.py`
- `financial-engine_v2/backend/app/services/validation/extraction_schemas.py`

**Checkpoints:**
1. Verify `ASXPeriodicFinancial` composite primary key: `(ticker, period_end)` — check if period_type is part of PK or just a column
2. Audit all 10 metric column types — are they Numeric with sufficient precision for financial data?
3. Verify `ExtractionRun` status enum matches multipass pipeline outputs
4. Audit `extraction_schemas.py` — verify schema validation runs before DB upsert (not after)
5. Check `confidence_metrics` JSON field — what structure is enforced?
6. Verify `source_document_id` FK relationship between financials and documents
7. Check for missing indexes on query-hot columns (ticker, period_end, status)
8. Verify `ASXRiskNote` relationship to `ASXPeriodicFinancial` — is it 1:1 or 1:N?

---

### Task 5 — Extraction Eval Harness Audit
**Target files:**
- `financial-engine_v2/backend/tests/test_extraction_eval.py`
- `financial-engine_v2/backend/tests/eval_config.json`
- `financial-engine_v2/backend/tests/eval_fixtures/*.json`

**Checkpoints:**
1. Verify eval_config.json thresholds: `min_accuracy_overall: 0.85`, per-metric tolerances
2. Count fixtures and verify diversity (companies, sectors, report formats)
3. Audit `metric_matches()` — tolerance comparison logic, handling of expected nulls
4. Verify unit mode tests (mocked LLM) vs live_eval mode distinction
5. Check if fixture expected values have source verification notes
6. Run unit-mode eval tests — capture pass/fail results

---

### Task 6 — Capability Guard & Compliance Tests
**Target files:**
- `financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
- `financial-engine_v2/backend/tests/test_extraction_llm_separation.py`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py`

**Checkpoints:**
1. Run all capability guard tests — verify prompt declares cashflow metrics, model has cashflow columns, etc.
2. Run LLM separation tests — verify extraction and embedding use separate LLM endpoints
3. Run compliance tests — no fallback in embedding context, no sqlite3 in runtime, no random UUIDs
4. Document any failures with root cause

---

### Task 7 — Test Execution (all extraction-related suites)
**Target:** Run and capture results from:
```bash
pytest financial-engine_v2/backend/tests/test_docling_extract.py -v
pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -v
pytest financial-engine_v2/backend/tests/test_extraction_eval.py -v
pytest financial-engine_v2/backend/tests/test_extraction_capability_guards.py -v
pytest financial-engine_v2/backend/tests/test_extraction_llm_separation.py -v
pytest financial-engine_v2/backend/tests/test_financial_metrics.py -v
pytest financial-engine_v2/backend/tests/test_prose_shares_extraction.py -v
pytest financial-engine_v2/backend/tests/test_periodic_snapshot_export.py -v
```

**Checkpoints:**
1. Capture pass/fail/skip counts per suite
2. Document any test failures with error messages
3. Note tests that require live LLM (marked `live_eval`) — expected to skip in offline mode
4. Calculate test coverage percentage for extraction modules

---

### Task 8 — Configuration & Environment Audit
**Target files:**
- `financial-engine_v2/backend/app/core/config.py`
- `financial-engine_v2/backend/app/config/model_routing.yaml`

**Checkpoints:**
1. Audit `Settings` pydantic model — verify extraction-related env vars have sane defaults
2. Verify `EXTRACTION_BACKEND` default matches project requirement (docling as default per project memory)
3. Check model_routing.yaml — verify extraction routes to correct model
4. Audit timeout settings — are they configurable via env?
5. Check for any hardcoded secrets or credentials in config

---

### Task 9 — Error Handling & Silent Failure Audit
**Target:** Cross-cutting concern across all extraction modules

**Checkpoints:**
1. Identify all try/except blocks in extraction pipeline — verify none silently swallow errors
2. Check `ExtractionRun.status = "failed"` paths — is the error message preserved?
3. Verify `ok_low_confidence` status handling — does downstream code treat it differently from `ok`?
4. Audit logging coverage — are extraction failures logged at ERROR level?
5. Check if failed extractions leave orphaned state (partial DB writes, dangling files)

---

### Task 10 — Provenance & Traceability Audit
**Target files:**
- `financial-engine_v2/backend/app/models/extractions.py`
- `financial-engine_v2/scripts/inspect_extraction_provenance.py`

**Checkpoints:**
1. Verify `ExtractionRun` stores: run_id, document_id, extractor_version, prompt_hash, status, confidence, structured_json
2. Audit `extractor_version` — is `"docling_multipass_v1"` updated when pipeline changes?
3. Verify provenance CLI (`inspect_extraction_provenance.py`) can reconstruct extraction lineage
4. Check `prompt_hash` — is it actually computed from the prompt sent to LLM?

---

### Task 11 — Compile Findings Report
**Deliverable:** `docs/audits/extraction_pipeline_audit_findings.md`

**Structure:**
1. Executive summary
2. Findings by severity (CRITICAL / HIGH / MEDIUM / LOW)
3. Each finding: description, file:line citation, evidence (test output or code excerpt), recommended fix
4. Test results summary table
5. Coverage gaps identified

---

## Execution Order

```
Phase 1 (parallel): Tasks 1, 2, 4 — read core modules
Phase 2 (parallel): Tasks 3, 5, 6, 8 — orchestration + tests + config
Phase 3 (sequential): Task 7 — run all tests, capture results
Phase 4 (parallel): Tasks 9, 10 — cross-cutting audits
Phase 5 (sequential): Task 11 — compile findings
```

## Files In Scope (confirmed existing)

| File | Role |
|------|------|
| `backend/app/services/docling_extract.py` | PDF -> structured tables + sections |
| `backend/app/services/multipass_extraction.py` | 4-pass LLM metric extraction |
| `backend/app/services/pipeline.py` | Orchestration + DB upsert |
| `backend/app/services/pipeline_service.py` | Backfill job orchestration |
| `backend/app/services/structured_chunking.py` | Prose chunking for embeddings |
| `backend/app/services/validation/extraction_schemas.py` | Schema validation |
| `backend/app/models/asx_financials.py` | Financial metrics DB model |
| `backend/app/models/extractions.py` | ExtractionRun provenance model |
| `backend/app/models/documents.py` | Document registry model |
| `backend/app/worker_tasks.py` | Celery task wiring |
| `backend/app/core/config.py` | Settings/env vars |
| `backend/tests/test_docling_extract.py` | Docling extraction tests |
| `backend/tests/test_multipass_extraction.py` | Multipass pipeline tests |
| `backend/tests/test_extraction_eval.py` | Eval harness |
| `backend/tests/test_extraction_capability_guards.py` | Capability guards |
| `backend/tests/test_extraction_llm_separation.py` | LLM separation tests |
| `backend/tests/test_financial_metrics.py` | Metric validation tests |
| `backend/tests/eval_config.json` | Accuracy thresholds |
| `backend/tests/eval_fixtures/*.json` | Ground-truth fixtures |
| `scripts/inspect_extraction_provenance.py` | Provenance CLI |

## Out of Scope

- News retrieval pipeline
- Cockpit/TUI
- Embedding model selection
- Frontend/API layer (except extraction API endpoints)
- Qdrant vector operations (except as downstream of extraction)
