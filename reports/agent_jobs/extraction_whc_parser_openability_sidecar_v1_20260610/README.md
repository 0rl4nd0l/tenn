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
- Refined classification so mixed scale-note pages with non-statement parser
  noise do not mask empty OCR statement-page parser cells.
- Refined OCR row candidates so note references and comparative columns are
  preserved separately, while the first high-quality financial amount is tagged
  as `candidate_value_text`.
- The diagnostic payload does not emit accepted metrics or normalized values.
- Diagnostic rows are not routed into `StructuredDocument.tables`,
  `multipass_extraction.py`, selected tables, row refs, metric source scales, or
  canonical validation gates.

## Validation

- Task card validate: passed.
- Registry read-only: `ok=true`, `active_jobs=[]`.
- Focused pytest: `25 passed in 0.30s`.
- `py_compile`: passed.
- `ruff`: passed.
- Exact WHC source smoke: `ocr_openability_provenance_gap`, statement pages
  57/58/60, scale pages 57/58/61, parser statement-page table count 10, parser
  statement-page nonempty cell count 0.
- Exact WHC row candidates now preserve current-period values including revenue
  `4,920,102`, operating cash flow `2,529,823`, cash `1,215,460`, and capex
  `(124,210)` without canonical promotion.
- JSON validation: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed.
- Code review: no critical findings, warnings, or suggestions.

## Remaining Risk

This is real parser-code progress, but it is not WHC canonical extraction yet.
The next slice can consume the preserved diagnostics into a selected-table
integration path with negative controls. Canonical WHC metrics must still remain
fail-closed until page/table/header/row/period/scale provenance is bound.

## Next Recommended Task

Use the opt-in openability diagnostics on the exact WHC document, then implement
one selected-table integration slice only if the diagnostic output proves page,
table/header, row, period, and scale provenance can be bound without changing
canonical contracts or loosening validation gates.
