# Extraction Redesign — Full Docling Multi-Pass

**Date:** 2026-03-21
**Status:** Approved (v2 — reviewer issues resolved)
**Branch:** cloud/session-20260319
**Goal:** Reliable, verifiable financial metric extraction from ASX announcements using fully local inference.

---

## Problem Statement

The existing extraction pipeline produces inconsistent results — metrics are sometimes null, sometimes wrong — across ASX periodic reports. Root causes:

1. **Text layer loss:** PyMuPDF `get_text("text")` flattens table structure. Row labels and values are separated; column alignment (current vs prior period) is lost. The LLM cannot reliably reconstruct 2D table structure from a 1D string.
2. **Monolithic prompt:** A single LLM call receives up to 18,000 chars of undifferentiated text and must simultaneously classify the document, locate financial tables, extract metrics, and normalise scale. Each task contaminates the others.
3. **No validation gate:** Any JSON the LLM returns is written to `asx_periodic_financials`, including hallucinated values, wrong-scale numbers, and null-filled rows.
4. **No eval harness:** No mechanism to measure whether extraction is correct or to prevent regressions.

---

## Chosen Approach

**Full docling multi-pass extraction** — highest accuracy ceiling. Uses docling's trained layout model to recover table structure, then applies a 4-pass pipeline of narrow, verifiable steps. Two passes use LLM (classifier + per-table extractor); two are deterministic (table locator + reconciler). A separate narrative extraction call handles risk/guidance fields.

---

## Architecture

### Pipeline overview

```
PDF (on disk)
  → [CHANGED] docling Structured Extraction
      → tables: [DataFrame…]
      → sections: [{heading, text}…]
      → cached to {pdf_path}.docling.json (alongside PDF)
  → [NEW] Pass 1: Document Classifier (LLM ~2s)
      → { report_type, period_end, currency, scale, classifier_confidence }
      → ABORT if classifier_confidence < 0.60
  → [NEW] Pass 2: Table Locator (deterministic <50ms)
      → { cashflow_statement: table_N, income_statement: table_M, … }
      → FALLBACK to PyMuPDF page.find_tables() if zero tables found
  → [NEW] Pass 3a: Per-Table Metric Extractor (LLM ~4–8s per table)
      → { metric: value, row_ref, col_ref, pass3_confidence } per table
  → [NEW] Pass 3b: Narrative Extractor (LLM ~2s on prose sections)
      → { risk_summary, risk_bullets, guidance_summary, material_changes, confidence_narrative }
  → [NEW] Pass 4: Reconciler (deterministic <10ms)
      → canonical combined payload matching _upsert_financial_rows contract
  → [NEW] Validation Gate
      → hard block on metric_confidence < 0.60, missing period_end, <3 metrics
      → soft warn on metric_confidence 0.60–0.70
  → [MODIFIED] _upsert_financial_rows — same signature, same DB schema, new data source
  → [UNCHANGED] Prose Chunks → Qdrant (sections only, not tables)
```

### What changes vs what stays

| Component | Status | Notes |
|-----------|--------|-------|
| `services/text_extract.py` | **Replaced** | → `services/docling_extract.py` |
| `services/chunking.py` | **Replaced** | → `services/structured_chunking.py` (prose sections only) |
| `services/extraction.py` | **Replaced** | → `services/multipass_extraction.py` (4-pass + narrative) |
| `services/pipeline.py` | **Modified** | `process_document()` delegates to `run_multipass_extraction()`; validation gate before upsert |
| `tests/test_extraction_capability_guards.py` | **Modified** | Guards A and C updated; Guards F/G/H added (see Tests section) |
| `requirements.txt` | **Modified** | No new deps needed (docling already present; PyMuPDF fallback already present) |
| DB schema | **Unchanged** | `asx_periodic_financials` + `asx_risk_notes` columns unchanged |
| Qdrant / embeddings | **Unchanged** | Prose sections still chunked + embedded |
| API routes | **Unchanged** | `/api/financials`, `/api/risk` unchanged |

---

## Pass Designs

### Pass 1 — Document Classifier (LLM)

**Input:** document title + first-page text (≤1500 chars)
**Model:** Qwen2.5-32B-Instruct via llamacpp (port 8001), temperature 0, JSON mode, max 256 tokens
**Output:**
```json
{
  "report_type": "H",
  "period_end": "2024-12-31",
  "currency": "AUD",
  "scale": "thousands",
  "classifier_confidence": 0.97
}
```
**Abort condition:** If `classifier_confidence < 0.60`, abort extraction. Write `ExtractionRun(status="failed", error="classifier_low_confidence")`. Do not proceed to Passes 2–4.

Note: `classifier_confidence` is a distinct field from `metric_confidence` (produced by Pass 3/4). They measure different things and are never compared against the same threshold.

---

### Pass 2 — Table Locator (deterministic)

**Input:** List of docling `TableItem` objects with page positions and captions
**Method:** Score each table against a keyword map by proximity to nearest heading. Ties resolved by page order (later = more authoritative for cashflow statements).
**Keyword map:**
```yaml
cashflow_statement: ["cash flow", "cash from operations", "financing activities"]
income_statement:   ["revenue", "profit", "earnings before"]
balance_sheet:      ["total assets", "shareholders equity", "net assets"]
highlights:         ["highlights", "key metrics", "summary"]
```
**Output:** `{ cashflow_statement: table_N, income_statement: table_M, highlights: table_K, unmatched: [...] }`

**Fallback (zero financial tables found):** Use `PyMuPDF page.find_tables()` (available in PyMuPDF ≥ 1.23.0; repo has 1.24.10). This is a rule-based table extractor built into PyMuPDF — no new dependency needed. Rows returned as plain text rows. If still zero tables found, write `status="failed", error="no_financial_tables"`.

---

### Pass 3a — Per-Table Metric Extractor (LLM)

**Input per call:** Single labelled table as markdown grid + Pass 1 metadata (period, scale, currency) + narrow schema for that table type
**Model:** Qwen2.5-32B-Instruct, temperature 0, JSON mode, max 512 tokens
**Scale normalisation:** LLM receives explicit scale context ("figures in thousands") and must output raw values already multiplied. Example: scale=thousands, cell=3241 → output 3241000.
**Negative value handling:** LLM instructed to treat parenthesised values `(412)` as negative `-412`.
**Output per table:**
```json
{
  "operating_cf": 3241000,
  "investing_cf": -412000,
  "financing_cf": -900000,
  "cash_end": 4100000,
  "period_col": "Current",
  "pass3_confidence": 0.95,
  "row_refs": {
    "operating_cf": "Net cash from operations",
    "cash_end": "Cash end of period"
  }
}
```
**Retry:** If LLM returns invalid JSON, retry once with table truncated to first 20 rows. If still fails, skip that table; other tables still processed.

---

### Pass 3b — Narrative Extractor (LLM)

**Purpose:** Extract the risk/guidance narrative fields required by `_upsert_financial_rows` and `asx_risk_notes`. Runs on prose sections (not tables), using the first 4000 chars of non-table text.
**Model:** Qwen2.5-32B-Instruct, temperature 0, JSON mode, max 512 tokens
**Output:**
```json
{
  "risk_summary": "string or null",
  "risk_bullets": ["string", "..."] ,
  "guidance_summary": "string or null",
  "material_changes": "string or null",
  "confidence_narrative": 0.82
}
```
This output feeds directly into the `asx_risk_notes` upsert. If this pass fails, narrative fields are set to null — metric extraction is not blocked.

---

### Pass 4 — Reconciler (deterministic)

**Input:** All Pass 3a outputs + Pass 3b output + Pass 1 metadata
**Metric conflict resolution:** Source priority `income_statement > cashflow_statement > balance_sheet > highlights`. Higher-priority source wins; discrepancy logged to `provenance_json`.
**`metric_confidence`:** Weighted average of `pass3_confidence` across all tables, weighted by number of metrics each table contributed.
**Output shape** (matches existing `_upsert_financial_rows` contract exactly):
```json
{
  "period_type": "H",
  "period_end": "2024-12-31",
  "metrics": {
    "revenue": 27841000000,
    "ebit": null,
    "np_attributable": null,
    "operating_cf": 8210000000,
    "investing_cf": -3400000000,
    "financing_cf": -5100000000,
    "capex": -3200000000,
    "cash_end": 4920000000,
    "net_debt": null,
    "shares_outstanding": 5068000000
  },
  "confidence_metrics": 0.91,
  "risk_summary": "...",
  "risk_bullets": ["..."],
  "guidance_summary": "...",
  "material_changes": "...",
  "confidence_narrative": 0.82,
  "provenance": {
    "revenue": "income_statement:row1:col_current",
    "operating_cf": "cashflow_statement:row3:col_current"
  }
}
```
The `provenance` field is written to `asx_risk_notes.provenance_json` (added as an optional column; requires a small migration if not present, or stored in the existing `structured_json` on `ExtractionRun`).

---

## Validation Gate

Enforced after Pass 4, before DB upsert. Uses `metric_confidence` (from Pass 3/4), **not** `classifier_confidence` (from Pass 1).

**Hard block** — write `status="failed"`, no upsert — if any:

| Check | Condition |
|-------|-----------|
| Period end present | `period_end` is non-null and parseable as ISO date |
| Period type valid | `period_type` ∈ {A, H, Q} |
| Minimum metric coverage | At least 3 of 10 metrics non-null |
| Sanity cap | No metric value exceeds ±$500B |
| Metric confidence | `metric_confidence` < 0.60 |

**Soft warning** (`status="ok_low_confidence"`): `metric_confidence` between 0.60–0.70 → upsert proceeds, row flagged. API returns `low_confidence: true`.

**Confidence field summary (disambiguation):**
- `classifier_confidence` — Pass 1 output. Hard abort < 0.60. Measures how well the document type/period was identified.
- `metric_confidence` — Pass 3/4 output. Validation gate threshold 0.60. Measures how confidently individual metrics were extracted from tables.

---

## `pipeline.py` Modification Detail

`process_document()` currently calls:
```python
text = extract_text_from_pdf(pdf_path)
chunks = simple_chunk(text)
prompt = build_prompt(text)
structured = generate_json(prompt, metadata, client)
_upsert_financial_rows(db, doc, structured)
```

After modification, `process_document()` calls:
```python
result = run_multipass_extraction(pdf_path, doc_metadata, llm_client)
# result matches existing _upsert_financial_rows contract
if result.status == "ok":
    _upsert_financial_rows(db, doc, result.payload)
# chunking for Qdrant uses structured sections, not raw text:
chunks = chunk_prose_sections(result.sections)
_embed_chunks(chunks, doc, qdrant_client)
```

`run_multipass_extraction()` is the new entry point in `multipass_extraction.py`. It encapsulates all 4 passes + validation gate, returns a `MultipassResult(status, payload, sections, error)`.

`EXTRACTOR_VERSION` moves from `extraction.py` to `multipass_extraction.py` as `"docling_multipass_v1"`.

`_upsert_financial_rows` signature is unchanged. The `result.payload` dict it receives matches the same key contract as the current LLM JSON response.

---

## Docling Cache

docling is slow (~30–90s/doc). Cache output to disk alongside the PDF.

- **Cache path:** `{pdf_path}.docling.json` — same directory and basename as the PDF, with `.docling.json` appended. Uses `_resolve_pdf_path(doc.pdf_path)` convention already established in `pipeline.py`.
- **Cache key:** Check if `{pdf_path}.docling.json` exists and was created after the PDF's mtime.
- **Invalidation:** If PDF is re-fetched (SHA256 changes), the new file replaces the old one, cache becomes stale by mtime and docling re-runs.
- **Benefit:** Re-extraction (prompt iteration, model upgrade) pays only ~17–27s LLM cost, not docling cost.

---

## Failure Taxonomy

| Failure | Strategy | DB status |
|---------|----------|-----------|
| docling hard fail (image PDF) | Fallback to PyMuPDF plain text, cap confidence at 0.5 | `ok_low_confidence` |
| docling timeout (>120s) | Kill process, log | `failed` |
| Pass 1 `classifier_confidence` < 0.60 | Abort all passes | `failed` |
| Pass 2 zero financial tables | PyMuPDF `find_tables()` fallback, then fail | `failed` |
| Pass 3a invalid JSON (after retry) | Skip that table, continue others | partial → validation gate decides |
| Pass 3b fails | Narrative fields set to null; metric extraction continues | — |
| Validation gate hard fail | No upsert; `structured_json` on ExtractionRun saved for debug | `failed` |

---

## Eval Harness

### Ground truth format

One JSON fixture per verified document, stored in `financial-engine_v2/backend/tests/eval_fixtures/`:

```json
{
  "document_id": "abc123...",
  "ticker": "BHP",
  "pdf_filename": "bhp_4d_dec2024.pdf",
  "period_type": "H",
  "period_end": "2024-12-31",
  "verified_by": "l4nd0",
  "verified_at": "2026-03-21",
  "metrics": {
    "revenue": 27841000000,
    "operating_cf": 8210000000
  },
  "expected_nulls": ["net_debt"]
}
```

### Tolerance by metric

| Metric | Tolerance | Rationale |
|--------|-----------|-----------|
| Revenue, EBIT, NP | ±0.5% | Section-to-section rounding |
| Cash flows | ±1% | Aggregated row rounding |
| Cash end, Net debt | ±0.1% | Balance sheet precision |
| Shares outstanding | ±0.01% | Always precise |
| Capex | ±2% | Often aggregated differently |
| Period end | Exact | No tolerance |

### Test modes

`test_extraction_eval.py` has two clearly scoped modes:

1. **Unit mode (default `pytest`):** Loads fixtures + cached docling JSON. LLM calls are mocked with pre-canned responses. Tests pipeline structure, output schema, and reconciler logic. Does NOT assert accuracy thresholds — those require a real LLM.

2. **Live eval mode (`pytest -m live_eval`):** Runs full pipeline against real Qwen2.5-32B-Instruct. Asserts per-metric accuracy ≥ thresholds in `eval_config.json`. This is the regression gate that blocks accuracy regressions. Must be run manually before merging extraction changes.

### Regression gate (`eval_config.json`)

```json
{
  "min_accuracy_overall": 0.85,
  "min_accuracy_per_metric": {
    "operating_cf": 0.90,
    "revenue": 0.90,
    "period_end": 1.00
  },
  "warn_threshold": 0.80
}
```

### Bootstrap plan

- **Phase 1 (now):** 5–10 hand-verified PDFs. Mix: 2× Appendix 4D, 2× Appendix 4C, 2× annual reports, 1× scanned
- **Phase 2 (post-fix):** Spot-check 20% of 50-doc run, add failures as fixtures. Target: 30 fixtures across 10+ tickers
- **Phase 3 (continuous):** Any new extraction bug → add PDF as fixture before fixing

---

## Test Suite

### Guards — `test_extraction_capability_guards.py`

| Guard | Status | What it tests |
|-------|--------|---------------|
| A | **Updated** | `multipass_extraction.py` declares all 10 metric fields in its Pass 3 schema (replaces test that imported deleted `extraction.py`) |
| B | Unchanged | DB model has all cashflow columns |
| C | **Updated** | `_upsert_financial_rows` in `pipeline.py` still iterates over all 10 fields (function unchanged; import path verified) |
| D | Unchanged | Backend does not depend on camelot |
| E | Unchanged (currently failing) | Cashflow layout modules present on disk; fixed by `git merge main` |
| F | **New** | `services/docling_extract` importable without error |
| G | **New** | Validation gate raises on missing `period_end` |
| H | **New** | Validation gate raises on < 3 non-null metrics |

### New unit tests — `test_multipass_extraction.py`

- Pass 1: classifier returns correct period/scale from fixture text samples
- Pass 2: table locator correctly labels tables by keyword proximity
- Pass 2: source priority conflict resolution — higher-priority wins
- Pass 3a: scale normalisation (thousands × 1000, millions × 1,000,000)
- Pass 3a: negative value handling — `(412)` → `-412`
- Pass 3b: narrative extractor returns null gracefully on empty sections
- Pass 4: reconciler merges non-overlapping metrics from two tables
- Pass 4: reconciler applies source priority on metric conflict

### New eval tests — `test_extraction_eval.py`

- Unit mode: schema validation, reconciler logic (mocked LLM — no accuracy assertions)
- Live eval mode (`-m live_eval`): full pipeline, real LLM, accuracy regression gate

### Existing (unchanged)

- `test_rag_payload_guardrails.py` — Qdrant payload validation
- `test_embeddings_local_point_id_compat.py` — vector ID format

---

## Model

**Qwen2.5-32B-Instruct** via llamacpp on port 8001.
- JSON mode enforced (`response_format: json_object`)
- Temperature 0
- Max tokens: 256 (Pass 1), 512 (Pass 3a + 3b)
- No streaming — wait for full JSON before parsing

---

## Files Changed

| File | Change |
|------|--------|
| `services/text_extract.py` | Replaced by `services/docling_extract.py` |
| `services/chunking.py` | Replaced by `services/structured_chunking.py` |
| `services/extraction.py` | Replaced by `services/multipass_extraction.py` |
| `services/pipeline.py` | Modified — `process_document()` delegates to `run_multipass_extraction()` |
| `tests/test_extraction_capability_guards.py` | Guards A+C updated; Guards F/G/H added |
| `tests/test_multipass_extraction.py` | New — unit tests for all passes |
| `tests/test_extraction_eval.py` | New — eval harness (unit + live eval modes) |
| `tests/eval_fixtures/` | New directory — ground truth JSON fixtures |
| `tests/eval_config.json` | New — live eval regression gate thresholds |

**No new Python dependencies required.** docling already in `requirements.txt`. PyMuPDF already present (1.24.10, supports `find_tables()`).

---

## Out of Scope

- DB schema changes — `asx_periodic_financials` + `asx_risk_notes` unchanged. `provenance_json` stored on existing `ExtractionRun.structured_json` if column not present.
- API changes — `/api/financials`, `/api/risk` unchanged
- Qdrant/embeddings changes — prose section chunking + embedding unchanged
- Celery/async pipeline changes — extraction layer is sync; Celery wraps it unchanged
- OCR for scanned PDFs — PyMuPDF plain text fallback is sufficient for now
