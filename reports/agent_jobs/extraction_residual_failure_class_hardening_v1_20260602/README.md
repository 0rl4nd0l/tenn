# Extraction Residual Failure Class Hardening V1

Audit-first hardening for the four residual bounded-sample failures from commit
`32e39089527137a1197a5a169ab1e8699c9155a8`.

## Outcome

- CRS base-metals exploration update: now excluded by title-only source
  classification before sample/runtime selection.
- WBC FY2023 notable-items pre-results notice: now excluded by title-only and
  text-backed source classification before sample/runtime selection.
- ABE 2022 annual report: raw-dollar scale detection now recognizes late formal
  cash-flow statement tables with `2022 $` / `2021 $` headers and
  `CASH FLOWS FROMOPERATING ACTIVITIES` row context as `units`.
- AZJ half-year FY2023 results: remains a real results-release coverage gap.
  The deterministic diagnostics show the source is eligible and has a `$m`
  performance table, but the prior runtime emitted only `np_attributable`.

No full extraction, broad backfill, random sample, source-PDF edit, service
restart, DB/Qdrant/news/memory mutation, prompt change, or gold-label change was
run.

## Validation Summary

- `test_multipass_extraction.py -k "late_raw_dollar_cashflow_statement_detects_units_scale or source_document_classifier"`: 33 passed, 189 deselected.
- `test_broad_extraction_test.py`: 6 passed.
- Full touched `test_multipass_extraction.py`: 222 passed.
- Further lint/compile/diff/JSON/task-card validation is recorded in
  `validation.json`.
