---
type: report
title: Phase 01 Extraction Truth Prototype Report
created: 2026-04-15
tags:
  - extraction
  - eval
  - verification
  - backend-authority
  - prototype
related:
  - '[[phase-01-baseline]]'
---

# Phase 01 Prototype Report

## Outcome

Phase 01 reached a backend-first runnable prototype without introducing any parallel truth path. The proof loop reused the existing `POST /api/extraction-eval/real-gold`, `scripts/run_real_extraction_eval.py`, `/api/extraction-review/*`, and verification UI surfaces, so backend APIs remained the only authority for extraction truth, confidence, provenance, and review state.

The limited proof run refreshed the canonical `reports/` artifacts at `2026-04-15T09:19:20.683353Z`, and persisted backend-owned review sessions remained available for direct operator review. Cockpit stayed in its client/orchestration role only.

## What Worked

### Canonical backend loop

- `curl -sS http://127.0.0.1:8000/api/health` returned `{"status":"ok"}` before the proof run.
- Because port `8000` was already occupied by an existing direct `uvicorn` backend, the live proof evals were sent to the already-running canonical backend on `http://127.0.0.1:8010` to avoid disrupting the bound port.
- `scripts/run_real_extraction_eval.py --limit 1` completed and refreshed the backend-authored summary and JSON artifacts under `reports/`.
- `/tmp/host-backend-8010-w2.log` captured `POST /api/extraction-eval/real-gold HTTP/1.1` with `200 OK` for the limited direct API proof.

### Backend-owned reviewability

- Backend review session `real-gold-review-5d191fa46c` persisted for BHP FY25 with `actual_method=pymupdf`.
- Backend review session `real-gold-review-7e1633778a` persisted for MIN H1 FY26 with `actual_method=docling_gpu`.
- The selected `operating_cf` item inside `real-gold-review-5d191fa46c` exposes backend-authored review evidence:
  - `confidence_metrics=0.926`
  - `evidence_reference=cashflow_statement:page_83:Net operating cash flows`
  - `matched_text=Net operating cash flows`
  - `image_url=/api/extraction-review/snippets/f57ce5e2caa25e09_snippet.png`

### Automated coverage already in place for the prototype

- `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py`
- `financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py`
- `pnpm exec playwright test tests/verification.spec.ts --reporter=line`

## Documents Evaluated

### Limited proof run

The refreshed `reports/extraction_real_eval_results.json` contains one evaluated document:

| Document | Ticker | Period | Trust outcome | Review status |
| --- | --- | --- | --- | --- |
| `2021-08-17_preliminary-final-report_37ba70c7-2724-4142-83a9-b55106f78907.pdf` | `BHP` | `A 2021-06-30` | `quarantine` | `review_reason=reviewable_parser_error` |

This document was quarantined because the extraction recorded `docling failed: Pipeline StandardPdfPipeline failed`, which cascaded into context mismatches for `period_type`, `period_end`, `currency`, and `scale`.

### Reviewable documents proven through persisted backend sessions

| Session | Document | Ticker | Status | Actual method |
| --- | --- | --- | --- | --- |
| `real-gold-review-5d191fa46c` | `2025-08-19_bhp-appendix-4e-and-2025-annual-report_60ba7318-bae4-4bb7-952b-ccd01b59e0d7.pdf` | `BHP` | `reviewable` | `pymupdf` |
| `real-gold-review-7e1633778a` | `2026-02-20_fy26-half-year-financial-report-and-appendix-4d_47d18a8c-280f-4672-82fb-a07648e1a4fb.pdf` | `MIN` | `reviewable` | `docling_gpu` |

## Quarantined Gaps For Later Phases

- The limited one-document proof run refreshed `reports/extraction_real_eval_results.json` with `review_session_id=real-gold-review-75a9e99289`, but that session file was not present under `financial-engine_v2/reports/extraction_review/sessions/` during this checkpoint. The prototype therefore proves reviewability through the separately persisted BHP FY25 and MIN FY26 sessions above, while the parser-error path remains quarantined for later hardening.
- The playbook references `docs/ops/extraction-truth/phase-01-baseline.md`, and the prior baseline content is present in git history (`3f6e77c`), but that file is absent from the current checkout. This report preserves the required `[[phase-01-baseline]]` linkage and treats the missing worktree copy as a documentation follow-up, not a new authority path.

## Artifact Links

- [Real-gold summary](../../../reports/extraction_real_eval_summary.md)
- [Real-gold results JSON](../../../reports/extraction_real_eval_results.json)
- [BHP FY25 review session](../../../financial-engine_v2/reports/extraction_review/sessions/real-gold-review-5d191fa46c.json)
- [MIN FY26 H1 review session](../../../financial-engine_v2/reports/extraction_review/sessions/real-gold-review-7e1633778a.json)
- Phase 01 baseline reference: `git show 3f6e77c:docs/ops/extraction-truth/phase-01-baseline.md`

## Contract Note

This checkpoint stays inside the [[phase-01-baseline]] boundary:

- backend APIs remain the only authority for extraction truth, confidence, provenance, and review state
- Cockpit displays and orchestrates only
- no alternate financial store, client-side extraction logic, or parallel review workflow was introduced
