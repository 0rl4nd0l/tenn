# Extraction CTM The Year Ended Period-End Detection V1

## Result

Implemented the bounded detector fix for CTM Docling text where the explicit
year is split as `202 5`.

The change:

- allows typed source period-end dates to match OCR/docling-spaced year digits;
- normalizes the matched date before `parse_period_end()`;
- prevents annual `year ended` matching inside `half year ended`;
- leaves loose dates, ambiguous multiple typed dates, validation gates, prompts,
  metric extraction, source PDFs, schema, and datastore writes unchanged.

## Evidence

Runtime run `fbd99043-fd40-46f3-beaa-847e8348060c` failed because
`source_period_end_evidence.reason` was `not_detected`. Inspecting the live
Docling cache showed explicit text:

`the year ended 31 December 202 5`

After the fix, the same cached early text detects:

`period_type=A`, `period_end=2025-12-31`, `reason=year_ended_explicit_date`.

## Validation

- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py` passed.
- Focused detector + CTM multipass regressions passed: `3 passed`.
- Live Docling-cache detector probe returned `period_type=A`, `period_end=2025-12-31`.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q` passed: `163 passed`.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_capability_guards.py -q` passed: `24 passed`.
- Targeted Ruff passed.
- Post-change review found no blocking findings.

## Remaining Work

Runtime CTM rerun has not been repeated after this second detector fix. Next
safe step is a bounded CTM-only runtime rerun through the backend route after
fresh registry, GPU, backend, worker, source-row, and queue gates pass.

