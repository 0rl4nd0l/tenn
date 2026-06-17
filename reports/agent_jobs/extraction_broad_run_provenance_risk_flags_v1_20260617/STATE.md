# State

## Current State

Status: `DONE_WITH_RISK`

Implemented the first bounded slice from the handoff:

- broad-run records now include compact per-metric provenance from existing extraction payload fields;
- missing per-metric provenance is explicit;
- broad-run records now include machine-readable accepted-output scale/magnitude risk flags;
- broad-run summaries roll up provenance coverage and risk-flag counts.

## Files Changed

- `docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md`
- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- `reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/*`

## Task Ledger

- Live ledger: `DATA_MISSING`
- Committed ledger: `DATA_MISSING`
- Current ledger status: `DATA_MISSING`
- Ledger update result: `DATA_MISSING`; no live or committed ledger file was available.
- Duplicate-work classification: `PROCEED_AS_NEW_WORK_WITH_REUSE`

## Implementation Notes

`financial-engine_v2/scripts/broad_extraction_test.py` now surfaces existing payload evidence only. It does not change multipass extraction, validation gates, canonical persistence, or acceptance behavior.

New broad-run record fields:

- `metric_provenance`
- `provenance_available`
- `provenance_missing`
- `provenance_audit`
- `source_provenance`
- `accepted_output_scale_magnitude_risk`
- `risk_flags`
- `scale_validation`

New summary fields:

- `provenance_coverage`
- `risk_flag_distribution`
- `risk_flagged_documents`

## Known Risk

- Some deeper table/cell fields remain `DATA_MISSING` because the final Pass 4 payload does not currently expose `table_index`, `table_caption`, `table_headers`, metric-specific `period_column`, or `value_cell_text`.
- `field_provenance.excerpt` is currently row-level text and may duplicate `row_ref`; this slice reports it honestly rather than inventing richer snippets.
- Risk flags are review-only evidence. They are not fail-closed gates.
