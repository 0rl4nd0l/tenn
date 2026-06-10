# WHC Parser Openability Diagnostic Sidecar

State: DONE_WITH_RISK

This job adds one bounded production-facing diagnostic path in
`docling_extract.py` so WHC-style parser/openability failures can preserve
statement-page OCR/text/table-cell provenance without changing canonical
extraction output.

The task is not allowed to run extraction, count samples, backfills, service
routes, or mutate DB/Qdrant/Redis/news/memory/source PDFs/prompts/gold/schema/
runtime/model/GPU config.

## Evidence

- PR #340 remains the report-local evidence packet.
- WHC exact document `9640d9f1-a45b-492d-8df5-9bad0f46431c` has saved
  statement/scale source evidence, but the saved PyMuPDF parser cache has
  statement-page table geometry with zero nonempty statement cells.

## Current Intent

Implemented an opt-in provenance-only diagnostic sidecar. Default parser
behavior and canonical extraction output remain unchanged.

## Files Changed

- `docs/agent_tasks/extraction_whc_parser_openability_sidecar_v1_20260610.md`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/tests/test_docling_extract.py`
- This report directory.

## Result

- Added `StructuredDocument.parser_diagnostics`.
- Added opt-in `openability_diagnostics` parameters to `extract_structured`.
- Added `parser_diagnostics["openability"]` with provenance-only OCR/text/table
  diagnostics.
- The diagnostic payload records statement labels, source period phrases, scale
  phrases, and source row text only.
- The diagnostic payload does not emit accepted metrics or normalized values.
- Diagnostic rows are not routed into `StructuredDocument.tables`,
  `multipass_extraction.py`, selected tables, row refs, metric source scales, or
  canonical validation gates.

## Validation

- Task card validate: passed.
- Registry read-only: `ok=true`, `active_jobs=[]`.
- Focused pytest: `22 passed in 0.27s`.
- `py_compile`: passed.
- `ruff`: passed.
- JSON validation: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed.
- Code review: no critical findings, warnings, or suggestions.

## Remaining Risk

This is real parser-code progress, but it is not WHC canonical extraction yet.
The next slice must consume the preserved diagnostics into a selected-table
integration path with negative controls before canonical WHC metrics can be
accepted.

## Next Recommended Task

Use the opt-in openability diagnostics on the exact WHC document, then implement
one selected-table integration slice only if the diagnostic output proves page,
table/header, row, period, and scale provenance can be bound without changing
canonical contracts or loosening validation gates.
