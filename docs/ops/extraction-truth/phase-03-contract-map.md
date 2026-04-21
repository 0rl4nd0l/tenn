---
type: reference
tags: [cockpit, verification, backend-authority]
---

# Phase 03: Review and Verification Data Contract Map

This document maps every operator-visible state in the review and verification
surfaces to the backend field that owns it, flags where the current contract is
inconsistent, and records which surfaces are safe to extend.

---

## 1. Backend Endpoints and Their Purposes

| Endpoint | Owner file | Purpose |
|----------|-----------|---------|
| `GET /api/context/verification` | `backend/app/api/context.py:568` | Lists extraction failures + low-confidence financials for triage |
| `GET /api/extraction-review/runs` | `backend/app/api/extraction_review.py:52` | Lists recent runs eligible for review (ok, ok_low_confidence, parser_error) |
| `POST /api/extraction-review/session` | `backend/app/api/extraction_review.py:37` | Creates a review session from document_ids + run_ids |
| `GET /api/extraction-review/session/{id}` | `backend/app/api/extraction_review.py:62` | Loads a review session with items, snippets, and metadata |
| `POST /api/extraction-review/session/{id}/decision` | `backend/app/api/extraction_review.py:72` | Persists operator decision (approved / wrong / abstain) |
| `GET /api/extraction-review/errors` | `backend/app/api/extraction_review.py:95` | Returns the wrong-queue (metrics marked wrong by operators) |
| `GET /api/extraction-review/run/{run_id}` | `backend/app/api/extraction_review.py:100` | Run-level status and metrics summary |
| `GET /api/extraction-review/snippets/{image}` | `backend/app/api/extraction_review.py:110` | Serves snippet PNG artifacts |

Integration clients:
- **Python Cockpit TUI**: `financial-engine_v2/cockpit/integrations/backend_api.py` — wraps all endpoints above
- **Next.js Cockpit UI**: `cockpit-ui/components/cockpit/verification/` — calls the same endpoints via `apiFetch`

---

## 2. Operator-Visible State → Backend Field Mapping

### 2a. Run Status (shown in review run list)

| UI label | Backend field | Source table/model | Notes |
|----------|-------------|-------------------|-------|
| Run status badge | `extraction_runs.status` | `ExtractionRun` | Values: `ok`, `ok_low_confidence`, `failed`, `parser_error` |
| Confidence score | `extraction_runs.confidence_overall` | `ExtractionRun` | Float 0–1; set by pipeline_stages.py at persist time |
| Method (requested) | `payload._method_provenance.requested_method` | `ExtractionRun.payload` JSON | Extracted in `list_review_runs` |
| Method (actual) | `payload._method_provenance.actual_method` | `ExtractionRun.payload` JSON | Extracted in `list_review_runs` |
| Metrics count | `extraction_review.list_review_runs` computed | Counted from payload | Stored as `metrics_count` in run summary |

### 2b. Per-Metric Review Item (shown in review session)

| UI label | Backend field | Source | Notes |
|----------|-------------|--------|-------|
| Extracted value | `review_item.extracted_value` | `build_review_item()` | From `asx_periodic_financials` |
| Period type / end | `review_item.period_type`, `period_end` | `asx_periodic_financials` | |
| Provenance status | `review_item.provenance_status` | `provenance.from_extraction_provenance()` | Values: `confirmed`, `inferred`, `speculative`, `missing` |
| Page number | `review_item.page_number` | Provenance / snippet | Nullable |
| Snippet image | `review_item.snippet.image_url` → `/api/extraction-review/snippets/{name}` | `build_metric_snippet()` | PNG crop from PDF; falls back to text-only |
| Snippet kind | `review_item.snippet.kind` | `build_metric_snippet()` | `line_crop`, `page_crop`, `text_only` |
| Evidence quality | `review_item.snippet.evidence_quality` | `_evidence_quality_for_snippet()` | `strong`, `weak`, `none` |
| Evidence text | `review_item.evidence_text` / `snippet.matched_text` | Provenance | Text extracted from PDF at provenance location |
| Review status | `review_item.review_status` | `VALID_REVIEW_STATUSES` | `approved`, `wrong`, `abstain`, `pending` |
| Reviewer note | `review_item.reviewer_note` | Operator input | Stored in session file |
| Expected value | `review_item.expected_value` | Operator input or gold fixture | Stored in session file |

### 2c. Low-Confidence Financials (shown in verification triage)

| UI label | Backend field | Source | Notes |
|----------|-------------|--------|-------|
| Confidence score | `asx_periodic_financials.confidence_metrics` | `asx_periodic_financials` table | Float 0–1; set by multipass_extraction.py |
| Threshold filter | `low_confidence_threshold` query param | `GET /api/context/verification` | Default 0.40 |

### 2d. Gold Eval Trust Outcomes (shown in gold-eval tab)

| UI label | Backend field | Source | Notes |
|----------|-------------|--------|-------|
| Trust outcome badge | `RealGoldEvalDocument.trust_outcome` | `POST /api/extraction-eval/real-gold` | `trusted`, `abstain`, `quarantine` |
| Expected trust | `RealGoldEvalDocument.expected_trust` | Gold fixture | Set in fixture YAML |
| Trust distribution | `RealGoldEvalResponse.summary.trust_distribution` | Computed by eval endpoint | Counted per trust_outcome value |
| Method provenance | `RealGoldEvalDocument.method_provenance` | `ExtractionRun.payload._method_provenance` | Mirrors `ProcessDocumentResponse.method_provenance` |

---

## 3. Trust Vocabulary (Authoritative — Backend-Owned)

All trust and status semantics are defined and computed in the backend. The UI
**must not** recompute, reclassify, or override these values.

| Term | Layer | Meaning |
|------|-------|---------|
| `ok` | `extraction_runs.status` | Extraction succeeded with normal confidence |
| `ok_low_confidence` | `extraction_runs.status` | Extraction succeeded but confidence_overall < threshold |
| `failed` | `extraction_runs.status` | Extraction failed; no metrics stored |
| `parser_error` | `extraction_runs.status` | LLM returned unparseable output |
| `trusted` | gold eval trust_outcome | All key metrics correct, context valid |
| `abstain` | gold eval trust_outcome | Fixture marked as not expected to extract |
| `quarantine` | gold eval trust_outcome | Metrics wrong or context mismatch |
| `approved` | review_item.review_status | Operator confirmed extracted value is correct |
| `wrong` | review_item.review_status | Operator flagged extracted value as incorrect |
| `abstain` | review_item.review_status | Operator skipped (unsure) |
| `pending` | review_item.review_status | Not yet reviewed |
| `confirmed` | provenance_status | Value location verified in source document |
| `inferred` | provenance_status | Location derived from surrounding context |
| `speculative` | provenance_status | Location not verifiable |
| `missing` | provenance_status | No provenance data available |

---

## 4. Identified Inconsistencies

### INCONSISTENCY-1: Two confidence fields with different semantics

- `extraction_runs.confidence_overall` — run-level aggregate float, set at persist time
- `asx_periodic_financials.confidence_metrics` — row-level metric confidence float, set per-metric by multipass_extraction.py

**Problem:** The verification triage (`GET /api/context/verification`) filters on
`confidence_metrics` (row-level). The review run list uses `confidence_overall`
(run-level). An operator looking at a low-confidence row in the triage view cannot
directly link it to the review run that produced it — the two confidence values come
from different tables and may differ.

**Resolution needed:** The review session's `confidence` field at line 693 of
`extraction_review.py` already bridges this (`confidence=payload.get("confidence_metrics")`),
but the run-list endpoint exposes only `confidence_overall`. The triage and run-list
views should expose the same confidence field or explicitly label them differently.

### INCONSISTENCY-2: `abstain` used in two distinct vocabularies

- In gold eval: `trust_outcome = 'abstain'` means "fixture not expected to have this metric"
- In review decisions: `review_status = 'abstain'` means "operator was unsure"

**Problem:** The UI renders both as "unsure" (see `utils.ts:113`), which is correct
for review decisions but misleading for gold eval trust outcomes. A gold eval
`abstain` is a fixture-level policy decision, not reviewer uncertainty.

**Resolution needed:** Gold eval `abstain` should be displayed with a label like
"not expected" rather than "unsure" to avoid operator confusion.

### INCONSISTENCY-3: Python Cockpit TUI and Next.js Cockpit UI are parallel surfaces

Both the TUI (`screens.py`) and the web UI (`verification-screen.tsx`) implement
the full review workflow independently. State is not shared. An operator who
reviews items in the TUI will not see those decisions in the web UI (sessions are
persisted to disk by session_id, so both can load the same session file — but they
are not coordinated in real time).

**Acceptable limitation** for now: the session file is the coordination point.

### INCONSISTENCY-4: `review_item.confidence_metrics` field name inconsistency

In `build_review_item()` at `extraction_review.py:749`, the field is returned as
`"confidence_metrics"` (matching the DB column name). In `list_review_runs()` at
line 615, the corresponding run-level field is `"confidence_overall"`. Downstream
consumers must know which field to read depending on context.

---

## 5. Safe Extension Points

The following backend locations can be extended without breaking existing consumers:

| Location | What can be added |
|----------|------------------|
| `list_review_runs()` response dict | New read-only display fields (e.g. ticker, title) — already partially present |
| `build_review_item()` response dict | New display-only fields from provenance or payload |
| `GET /api/context/verification` response | New top-level keys alongside `extraction_failures` and `low_confidence_financials` |
| `create_review_session()` / session payload | New metadata fields; existing consumers ignore unknown keys |

---

## 6. Files Surveyed

- `financial-engine_v2/backend/app/api/context.py` — `/api/context/verification`
- `financial-engine_v2/backend/app/api/extraction_review.py` — all `/api/extraction-review/*` routes
- `financial-engine_v2/backend/app/services/extraction_review.py` — service layer: sessions, items, snippets, wrong queue
- `financial-engine_v2/backend/app/models/extractions.py` — `ExtractionRun` model (`confidence_overall`)
- `financial-engine_v2/backend/app/models/asx_financials.py` — `ASXPeriodicFinancials` (`confidence_metrics`)
- `financial-engine_v2/cockpit/integrations/backend_api.py` — Python TUI client
- `financial-engine_v2/cockpit/ui/screens.py` — Python TUI `ReviewScreen`
- `cockpit-ui/components/cockpit/verification/types.ts` — TypeScript type contract
- `cockpit-ui/components/cockpit/verification/utils.ts` — status → badge mapping
- `cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx` — review tab UI
- `cockpit-ui/components/cockpit/verification/tabs/gold-eval-tab-panel.tsx` — gold eval tab UI
