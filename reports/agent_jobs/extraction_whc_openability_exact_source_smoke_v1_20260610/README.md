# WHC Openability Exact-Source Smoke

State: DONE

This report records one exact-source local smoke of the opt-in parser
openability diagnostics added in
`extraction_whc_parser_openability_sidecar_v1_20260610`.

The smoke is constrained to the exact WHC document
`9640d9f1-a45b-492d-8df5-9bad0f46431c`, a report-local temporary data root, and
report-local JSON output.

## Result

The smoke proves the production parser diagnostic now captures the WHC
openability gap without canonical output changes:

- Classification: `ocr_openability_provenance_gap`
- OCR statement pages with evidence: 57, 58, 60
- OCR scale pages with evidence: 57, 58, 61
- Parser statement-page table count: 10
- Parser statement-page nonempty cell count: 0
- `feeds_canonical_output=false`
- `canonical_output_changed=false`
- No accepted metrics or normalized values were emitted.

## Boundary

This is still not a canonical WHC extraction fix. It proves the parser layer can
preserve the missing source evidence. A separate selected-table integration task
is required before any WHC canonical metrics can be accepted.
