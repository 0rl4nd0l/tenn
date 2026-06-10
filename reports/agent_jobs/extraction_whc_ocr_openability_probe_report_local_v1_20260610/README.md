# WHC OCR Openability Probe, Report-Local

State: DONE

This job implements a report-local diagnostic harness for WHC document
`9640d9f1-a45b-492d-8df5-9bad0f46431c`.

The harness is provenance-only. It does not modify parser cache, canonical
output, source PDFs, extraction services, DB, Qdrant, Redis, news, memory,
prompts, gold labels, schema, runtime config, model config, or GPU config.

## Result

The report-local sidecar was generated from saved WHC source evidence and the
saved PyMuPDF cache. It classifies the exact WHC document as an
`ocr_openability_provenance_gap`.

Key result:

- Saved source/OCR evidence finds statement evidence on pages 57, 58, 60, and
  61.
- Saved parser cache has statement-page table geometry on pages 57, 58, and 60.
- Saved parser cache has zero nonempty statement-page table cells.
- The sidecar is marked `provenance_only=true`,
  `not_an_extraction_result=true`, `canonical_output_changed=false`, and
  `parser_cache_written=false`.

No canonical metric output was emitted and no parser/runtime files changed.

## Validation

Focused mocked tests passed: 8 tests.

Full validation results are in `validation.json`.
