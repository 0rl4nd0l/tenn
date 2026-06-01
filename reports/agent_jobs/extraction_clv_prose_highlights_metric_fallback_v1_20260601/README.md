# Extraction CLV Prose Highlights Metric Fallback V1

Status: code fix complete; runtime canary not rerun.

## Problem

The worker-env retry accepted AAU, ATM, AM5, AQX, and CRS, then stopped at CLV
with:

`validation_gate:insufficient_metrics:0`

CLV source evidence showed explicit financial facts in prose:

- `1H revenue of $44.1 million`
- `NPAT $4.2 million`
- `Cash of $10.3 million as at 31 January 2026`

`docling_gpu` parsed that PDF as a 4-page document with zero tables, so the
table-oriented Pass 3a metric extractor produced no canonical metrics.

## Change

Added a conservative deterministic prose-highlights fallback in
`multipass_extraction.py`.

It can populate only:

- `revenue`
- `np_attributable`
- `cash_end`

Rules preserved:

- No EBITDA-to-EBIT mapping.
- No guidance/forecast values used as current-period facts.
- No inferred or substituted metrics.
- No validation gates lowered or bypassed.
- Every prose-derived metric carries `prose_highlight:page_*` provenance and a
  row reference containing the matched source phrase.

## Validation

- `financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q -k 'prose_highlight or pass4_extracts_explicit_prose_highlight_metrics'`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_capability_guards.py -q`
- `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py`

Results:

- focused prose-highlight tests: `2 passed`
- full multipass tests: `162 passed`
- pre-canary/capability guard tests: `22 passed`
- Ruff: passed

## Not Done

No runtime extraction rerun was performed after the code fix. CTM remains
unsubmitted from the bounded canary because the retry correctly hard-stopped at
CLV before this code change.

Next safe step is a fresh bounded runtime retry for CLV then CTM, with the same
backend-owned single-document route and hard-stop discipline.
